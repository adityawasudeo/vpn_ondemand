# helper script to initialize an ECS cluster in an AWS location using the vpn-ondemand container.
# Run this after you push the docker image to ECS

import sys,boto3
def createECSTaskDefinition(clientObj, repo_name):
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
    response = clientObj.create_cluster(clusterName='vpn-ondemand')
    print(response)
    return response['cluster']['clusterArn']

def createService(clientObj,taskARN,clusterARN):
    response = clientObj.create_service(cluster=clusterARN,
                                        serviceName='vpn-ondemand',
                                        taskDefinition=taskARN,
                                        desiredCount=1,
                                        launchType='EC2')
    print(response)
    return response['service']['serviceArn']

def registerContainerInstance(clientObj,clusterARN):
    response =  clientObj.run_instances(
                ImageId = 'ami-0520a52c94745d2e9',
                MinCount=1,
                MaxCount=1,
                InstanceType="t2.nano",
                IamInstanceProfile={
                    "Name": "ecsInstanceRole"
                },
                UserData="#!/bin/bash \n echo ECS_CLUSTER=" + 'vpn-ondemand' + " >> /etc/ecs/ecs.config"
        )
    print(response)

if len(sys.argv) != 3:
    print("Usage: ./initialize_ecs <ecs repository name> <aws region name>")
    exit(0)

repo_name = sys.argv[1]
region = sys.argv[2]
clientObj = boto3.client('ecs',region_name=region)
ec2ClientObj = boto3.client('ec2',region_name=region)
#taskARN = createECSTaskDefinition(clientObj,repo_name)
#clusterARN = createCluster(clientObj)
#serviceARN = createService(clientObj,taskARN,clusterARN)

taskARN = 'arn:aws:ecs:ap-south-1:457709842649:task-definition/vpn-ondemand:2'
clusterARN = 'arn:aws:ecs:ap-south-1:457709842649:cluster/vpn-ondemand'
serviceARN = 'arn:aws:ecs:ap-south-1:457709842649:service/vpn-ondemand/vpn-ondemand'

registerContainerInstance(ec2ClientObj,clusterARN)
