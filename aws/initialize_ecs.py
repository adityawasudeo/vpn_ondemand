# helper script to initialize an ECS cluster in an AWS location using the vpn-ondemand container.
# Run this after you push the docker image to ECS

import sys,boto3
import botocore.exceptions

SERVICE_NAME = 'vpn-ondemand'

def createECSTaskDefinition(clientObj, repo_name):
    # check if task definition already exists and return if it does
    try:
        response = clientObj.describe_task_definition(
                            taskDefinition='vpn-ondemand')
        if response['taskDefinition'] and response['taskDefinition']['taskDefinitionArn']:
            return response['taskDefinition']['taskDefinitionArn']
    except botocore.exceptions.ClientError:
        pass

    container_def = {
            'name'  :'vpn-ondemand',
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
                family='vpn-ondemand',
                networkMode='bridge',
                containerDefinitions = [container_def], 
                requiresCompatibilities=['EC2'])
    print(response)
    return response['taskDefinition']['taskDefinitionArn']                   

def createCluster(clientObj):
    # check if the cluster already exists
    response = clientObj.describe_clusters(
                        clusters=['vpn-ondemand'],
                    )
    if len(response['clusters']) > 0:
        return response['clusters'][0]['clusterArn']

    response = clientObj.create_cluster(clusterName='vpn-ondemand')
    print(response)
    return response['cluster']['clusterArn']

def createService(clientObj,taskARN,clusterARN):
    # check if the service already exists in the cluster
    response = clientObj.describe_services(
                    cluster=clusterARN,
                    services=[
                        'vpn-ondemand'
                    ],
                )
    if len(response['services']) > 0:
        return response['services'][0]['serviceArn']

    response = clientObj.create_service(cluster=clusterARN,
                                        serviceName='vpn-ondemand',
                                        taskDefinition=taskARN,
                                        desiredCount=1,
                                        launchType='EC2')
    print(response)
    return response['service']['serviceArn']

def createSecurityGroup(clientObj):
    # check if security group already exists. if it does, just return its id
    response = clientObj.describe_security_groups(
    Filters=[
        dict(Name='group-name', Values=['vpn-ondemand'])
        ]
    )
    if len(response['SecurityGroups']) > 0:
        return response['SecurityGroups'][0]['GroupId']

    response = clientObj.create_security_group(GroupName='vpn-ondemand',
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
                UserData="#!/bin/bash \n echo ECS_CLUSTER=" + 'vpn-ondemand' + " >> /etc/ecs/ecs.config"
        )
    print(response)
    instanceId = response['Instances'][0]['InstanceId']
    return instanceId

if len(sys.argv) != 3:
    print("Usage: ./initialize_ecs <ecs repository name> <aws region name>")
    exit(0)

repo_name = sys.argv[1]
region = sys.argv[2]
clientObj = boto3.client('ecs',region_name=region)
ec2ClientObj = boto3.client('ec2',region_name=region)

taskARN = createECSTaskDefinition(clientObj,repo_name)
clusterARN = createCluster(clientObj)
serviceARN = createService(clientObj,taskARN,clusterARN)


securityGroupId = createSecurityGroup(ec2ClientObj)
registerContainerInstance(ec2ClientObj,securityGroupId)
