# vpn_ondemand

<!--- These are examples. See https://shields.io for others or to customize this set of shields. You might want to include dependencies, project status and licence info here --->
![Twitter Follow](https://img.shields.io/twitter/follow/adityawasudeo?style=social)

vpn_ondemand is a utility that allows you to spin up an openVPN instance in any AWS region and
connect to it in a few minutes.

It's especially useful if you're a TV show/Movie fan (or live with one) and want to check out
Netlix/Amazon Prime catalogs from other countries. Also comes in handy for bypassing those
annoying Youtube geo-gating rules some publishers like to use.

VPNs run on AWS Linux containers so you only pay for what you use and are more private than third party
services. 

## Prerequisites

vpn_ondemand has been tested on Mac and Linux but it *should* work on Windows as well, there's
nothing OS specific 

Before you begin, ensure you have met the following requirements:
<!--- These are just example requirements. Add, duplicate or remove as required --->
* `Python3`. You may want to use a Virtual Environment
* Install `Docker` and configure it. [Instructions](https://docs.docker.com/get-docker/)
* Sign up for `AWS` and create an IAM user following these [instructions](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/get-set-up-for-amazon-ecs.html).
* Install `aws-cli` and configure it with your IAM access credentials. [Instructions](https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html)
* Install `boto3`. [Instructions](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/quickstart.html#installation)

## Installing vpn-ondemand

Clone the Github repository:
```
git clone https://github.com/adityawasudeo/vpn_ondemand.git
```

Generate vpn keys:
```
cd vpn_ondemand/keys/
./generate_keys.sh
```

Build the docker image
``` 
cd ../vpn/
docker-compose up
```

Create an AWS ECR repository by following the instructions [here](https://docs.aws.amazon.com/AmazonECR/latest/userguide/repository-create.html). Note down the repository name which you create. You will push the docker image to this repository and use it to spin up containers in the regions you want a VPN

Tag your docker image with the repository you just created and push it
```
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <your
repository name>
docker tag vpn_vpn:latest <your repository name>
docker push <your repository name>
```
Almost done! Now use the helper script to spin up your VPN container in any region you want. The
list of available AWS regions is [here](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Concepts.RegionsAndAvailabilityZones.html)

Every region has a code. For example Mumbai is ap-south-1, Tokyo is ap-northeast-1. Identify the
code of the region where you want a VPN.

```
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
```

```
cd ../aws/
python3 initialize_ecs.py <repository name> <region code> 
```
The script will spin up your containers and generate a config file and vpn keys in the
`client_keys/` directory.

To stop the VPN 
```
python3 initialize_ecs.py <region code> stop
``` 

## Logging into the VPN

Import the config and keys in the client_keys/ directory into any VPN client. I have tested with
with Tunnelblick on Mac and OpenVPN on Android. 

## Wishlist/Roadmap/Coming soon (hopefully)
* Web frontend to make spinning up spinning down VPNs easy
* Multi-user support

## Contact

@adityawasudeo on Twitter

## License

This project uses the following license: [BSD 2-Clause License](https://choosealicense.com/licenses/bsd-2-clause/).
