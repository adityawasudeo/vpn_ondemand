# helper script to initialize an ECS cluster in an AWS location using the vpn-ondemand container.
# Run this after you push the docker image to ECS

import sys,boto3,time
import botocore.exceptions

SERVICE_NAME = 'vpn-ondemand'

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

def createCluster(clientObj):
    # check if the cluster already exists
    response = clientObj.describe_clusters(
                        clusters=[SERVICE_NAME],
                    )
    if len(response['clusters']) > 0:
        return (response['clusters'][0]['clusterArn'],
    response['clusters'][0]['runningTasksCount'])

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

def registerContainerInstance(clientObj,security_group_id):
    response =  clientObj.run_instances(
                ImageId = 'ami-0520a52c94745d2e9',
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
    while True:
        network_iface = clientObj.describe_network_interfaces()
        for iface in network_iface['NetworkInterfaces']:
            if iface['Attachment']['InstanceId'] == instanceId:
                if 'Association' in iface.keys():
                    return iface['Association']['PublicIp']
                else:
                    time.sleep(5)

def getContainerIPAddr(clientObj):
    network_iface = clientObj.describe_network_interfaces()
    for iface in network_iface['NetworkInterfaces']:
        group_list = iface['Groups']
        for group in group_list:
            if group['GroupName'] == SERVICE_NAME:
                return iface['Association']['PublicIp']

    return None

if len(sys.argv) != 3:
    print("Usage: ./initialize_ecs <ecs repository name> <aws region name>")
    exit(0)

repo_name = sys.argv[1]
region = sys.argv[2]
clientObj = boto3.client('ecs',region_name=region)
ec2ClientObj = boto3.client('ec2',region_name=region)

taskARN = createECSTaskDefinition(clientObj,repo_name)
(clusterARN,registeredContainers) = createCluster(clientObj)
serviceARN = createService(clientObj,taskARN,clusterARN)


securityGroupId = createSecurityGroup(ec2ClientObj)
ipAddr = None
if registeredContainers > 0:
    ipAddr = getContainerIPAddr(ec2ClientObj)

if ipAddr is None:
    ipAddr = registerContainerInstance(ec2ClientObj,securityGroupId)

print(ipAddr)
