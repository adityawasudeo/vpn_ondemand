# vpn-ondemand AWS Lambda function. The Lambda user running this function needs the following IAM permissions:
# AWSLambdaBasicExecutionRole
# ECS Task Execution Role
# ECS Full access
# EC2 Full access

import json
import sys,boto3,time,os
import botocore.exceptions

SERVICE_NAME = 'vpn-ondemand'
CLIENT_KEY_DIR = 'client_keys'

SUPPORTED_REGIONS = [
            'us-west-1',
            'us-west-2',
            'us-east-2',
            'us-east-1',
            'af-south-1',
            'ap-east-1',
            'ap-northeast-1',
            'ap-northeast-2',
            'ap-south-1',
            'ap-southeast-1',
            'ap-southeast-2',
            'ca-central-1',
            'eu-central-1',
            'eu-north-1',
            'eu-west-1',
            'eu-west-2',
            'eu-south-1',
            'eu-west-3',
            'me-south-1',
            'sa-east-1',
            'cn-north-1',
            'cn-northwest-1',
           ]

def verifyRegion(regionInput):
    if regionInput in SUPPORTED_REGIONS: return True
    return False
    
def getAMIName(region):
    client = boto3.client('ssm',region_name=region)
    response = client.get_parameters(
                    Names = [
                        '/aws/service/ecs/optimized-ami/amazon-linux/recommended/image_id'
                    ]
                )
    return response['Parameters'][0]['Value']

def createECSTaskDefinition(clientObj, repo_name):
    # check if task definition already exists and return if it does
    try:
        response = clientObj.describe_task_definition(
                            taskDefinition=SERVICE_NAME)
        if response['taskDefinition'] and response['taskDefinition']['taskDefinitionArn']:
            return response['taskDefinition']['taskDefinitionArn']
    except botocore.exceptions.ClientError:
        pass

    container_def = {
            'name'  :SERVICE_NAME,
            'image' : repo_name,
            'cpu': 500,
            'memory': 400,
            'portMappings': [{
                    "hostPort": 1194,
                    "protocol": "udp",
                    "containerPort": 1194
                }],
             "linuxParameters": {
                    "capabilities": {
                        "add": [
                            "NET_ADMIN",
                            "MKNOD"
                         ],
                      }
                },
             "entryPoint": [
                    "/startVPN.sh"
                ],

            }
    response = clientObj.register_task_definition(
        family=SERVICE_NAME,
        networkMode='bridge',
        containerDefinitions = [container_def],
        requiresCompatibilities=['EC2'])
    print(response)
    return response['taskDefinition']['taskDefinitionArn']

def getEC2Instances(clientObj,active=0):
    containerInstanceList = clientObj.list_container_instances(cluster=SERVICE_NAME)
    if len(containerInstanceList['containerInstanceArns']) == 0: return []
    containerDetails = clientObj.describe_container_instances(cluster=SERVICE_NAME,
                                containerInstances=containerInstanceList['containerInstanceArns'])

    ec2_id_list = []
    for instance in containerDetails['containerInstances']:
        if active == 1:
            if instance['status'] != 'ACTIVE': continue
        ec2_id_list.append(instance['ec2InstanceId'])

    return ec2_id_list

def createCluster(clientObj):
    # check if the cluster already exists
    response = clientObj.describe_clusters(
                        clusters=[SERVICE_NAME],
                    )
    active_cluster_count = 0
    clusterARN = None
    for cluster in response['clusters']:
        if cluster['status'] == 'ACTIVE':
            active_cluster_count = active_cluster_count+1
            clusterARN           = cluster['clusterArn']

    if active_cluster_count > 0:
        return (clusterARN,len(getEC2Instances(clientObj,1)))

    response = clientObj.create_cluster(clusterName=SERVICE_NAME)
    print(response)
    return (response['cluster']['clusterArn'],0)

    
def createService(clientObj,taskARN,clusterARN):
    # check if the service already exists in the cluster
    response = clientObj.describe_services(
                    cluster=clusterARN,
                    services=[
                        SERVICE_NAME
                    ],
                )
    if len(response['services']) > 0:
        return response['services'][0]['serviceArn']

    response = clientObj.create_service(cluster=clusterARN,
                                        serviceName=SERVICE_NAME,
                                        taskDefinition=taskARN,
                                        desiredCount=1,
                                        launchType='EC2')
    print(response)
    return response['service']['serviceArn']

def startTask(clientObj,taskARN,clusterARN):
    while True:
        if len(getEC2Instances(clientObj)) == 0:
            print("Waiting for EC2 instance to be added to cluster....")
            time.sleep(5)
        else: break

    response = clientObj.run_task(cluster=clusterARN,
                                  launchType='EC2',
                                  taskDefinition=taskARN)
    print(response)

def createSecurityGroup(clientObj):
    # check if security group already exists. if it does, just return its id
    response = clientObj.describe_security_groups(
    Filters=[
        dict(Name='group-name', Values=[SERVICE_NAME])
        ]
    )
    if len(response['SecurityGroups']) > 0:
        return response['SecurityGroups'][0]['GroupId']

    response = clientObj.create_security_group(GroupName=SERVICE_NAME,
                                    Description = 'Security rules for openvpn containers'
                                    )
    security_group_id = response['GroupId']
    response = clientObj.authorize_security_group_ingress(
                            GroupId=security_group_id,
                            IpPermissions=[
                                {'IpProtocol': 'udp',
                                  'FromPort': 1194,
                                  'ToPort': 1194,
                                   'IpRanges': [{'CidrIp': '0.0.0.0/0'}]}
                        ])
    print(response)
    return security_group_id

def registerContainerInstance(clientObj,security_group_id,ami_name):
    response =  clientObj.run_instances(
                ImageId = ami_name,
                MinCount=1,
                MaxCount=1,
                SecurityGroupIds=[security_group_id],
                InstanceType="t2.nano",
                IamInstanceProfile={
                    "Name": "ecsInstanceRole"
                },
                UserData="#!/bin/bash \n echo ECS_CLUSTER=" + SERVICE_NAME + " >> /etc/ecs/ecs.config"
        )
    print(response)
    instanceId = response['Instances'][0]['InstanceId']
    # get public IP. need to check this in a loop because public IP is assigned a few seconds
    # after container bring up
    time.sleep(2)
    while True:
        try:
            network_iface = clientObj.describe_network_interfaces()
            for iface in network_iface['NetworkInterfaces']:
                if iface['Attachment']['InstanceId'] == instanceId:
                    if 'Association' in iface.keys():
                        return iface['Association']['PublicIp']
                    else:
                        time.sleep(5)
        except KeyError:
            time.sleep(5)
            pass

def getContainerIPAddr(clientObj,ec2ClientObj):
    ec2_instance_list = getEC2Instances(clientObj, 1)
    reservations = ec2ClientObj.describe_instances(
                        InstanceIds=ec2_instance_list).get("Reservations")
    for reservation in reservations:
        for instance in reservation['Instances']:
            return instance.get("PublicIpAddress")

    return None

def terminateInstances(clientObj,ec2ClientObj):
    ec2_instance_list = getEC2Instances(clientObj)
    if len(ec2_instance_list) == 0:
        print("No instances found. Nothing to do")
        return

    response = ec2ClientObj.terminate_instances(InstanceIds=ec2_instance_list)
    print(response)

def lambda_handler(event, context):
    keyList = event.keys()
    if 'region' not in keyList:
        return {
            'statusCode': 400,
            'body': json.dumps('No region specified')
        }
    if 'stop' not in keyList and 'repo_name' not in keyList:
        return {
            'statusCode': 400,
            'body': json.dumps('No repo specified')
        }
        
    
    #repo_name = event['repo_name']
    region    = event['region']
    
    if verifyRegion(region) == False:
        return {
            'statusCode': 400,
            'body': json.dumps("Region "+region+" does not exist or not supported")
        }
    clientObj = boto3.client('ecs',region_name=region)
    ec2ClientObj = boto3.client('ec2',region_name=region)

    if 'stop' in keyList:
        terminateInstances(clientObj,ec2ClientObj)
        return {
            'statusCode': 200,
            'body': json.dumps("Stopping VPN instances in "+region)
        }
        
    repo_name = event['repo_name']
    taskARN = createECSTaskDefinition(clientObj,repo_name)
    (clusterARN,registeredContainers) = createCluster(clientObj)
    serviceARN = createService(clientObj,taskARN,clusterARN)

    securityGroupId = createSecurityGroup(ec2ClientObj)
    ipAddr = None
    if registeredContainers > 0:
        ipAddr = getContainerIPAddr(clientObj,ec2ClientObj)

    if ipAddr is None:
        amiName = getAMIName(region)
        ipAddr = registerContainerInstance(ec2ClientObj,securityGroupId,amiName)
    
    startTask(clientObj,taskARN,clusterARN)

    return {
        'statusCode': 200,
        'body': json.dumps(ipAddr)
    }

