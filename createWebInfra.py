#!/usr/bin/env python3

import boto3
from pprint import pprint
from botocore.exceptions import ClientError

# ============================================================
# ClientFinder for creating EC2 and ELB Client with default region ca-central-1
# ============================================================

class ClientFinder:
    def __init__(self, client_name, region):
        self._client = boto3.client(client_name, region_name=region)

    def get_client(self):
        return self._client


class AWSClient(ClientFinder):
    def __init__(self, client_name, region='ca-central-1'):
        super().__init__(client_name, region)


# ============================================================
# EC2 class for creating EC2 instance with generic functions
# ============================================================

class EC2:
    def __init__(self, client):
        self._client = client

    def create_key_pair(self, key_name):
        kp_describe = self._client.describe_key_pairs()
        keypairs = kp_describe.get('KeyPairs')
        for keypair in keypairs:
            if key_name == keypair['KeyName']:
                return keypair
        kp_response = self._client.create_key_pair(KeyName=key_name,
                                     TagSpecifications=[{'ResourceType': 'key-pair',
                                                         'Tags': [{'Key': 'name', 'Value': 'hello-world-service'}]
                                                         }])
        print("Private Key:", kp_response['KeyMaterial'])
        return kp_response

    def create_security_group(self, group_name, description, vpc_id):
        return self._client.create_security_group(
            GroupName=group_name,
            Description=description,
            VpcId=vpc_id,
            TagSpecifications=[{'ResourceType': 'security-group',
                                'Tags': [{'Key': 'name', 'Value': 'hello-world-service'},
                                         {'Key': 'Name', 'Value': group_name}]}]
        )

    def add_inbound_rule_to_sg_for_ec2(self, security_group_id):
        self._client.authorize_security_group_ingress(
            GroupId=security_group_id,
            IpPermissions=[
                {
                    'IpProtocol': 'tcp',
                    'FromPort': 22,
                    'ToPort': 22,
                    'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
                }
            ]
        )

    def add_inbound_rule_to_sg_for_lb(self, sg_id):
            self._client.authorize_security_group_ingress(
                GroupId=sg_id,
                IpPermissions=[
                    {
                        'IpProtocol': 'tcp',
                        'FromPort': 80,
                        'ToPort': 80,
                        'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
                    },
                    {
                        'IpProtocol': 'tcp',
                        'FromPort': 22,
                        'ToPort': 22,
                        'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
                    }
                ]
            )

    def add_inbound_rule_to_ec2_for_lb(self, security_group_id_ec2, security_group_id_lb):
        self._client.authorize_security_group_ingress(
            GroupId=security_group_id_ec2,
            IpPermissions=[
                {
                    'IpProtocol': 'tcp',
                    'FromPort': 80,
                    'ToPort': 80,
                    'UserIdGroupPairs': [{'GroupId': security_group_id_lb}]
                }
            ]
        )

    def launch_ec2_instance(self, image_id, key_name, min_count, max_count, security_group_id, subnet_id, user_data):

        return self._client.run_instances(
            ImageId=image_id,
            KeyName=key_name,
            MinCount=min_count,
            MaxCount=max_count,
            InstanceType='t2.micro',
            SecurityGroupIds=[security_group_id],
            SubnetId=subnet_id,
            UserData=user_data,
            TagSpecifications=[{'ResourceType': 'instance',
                                'Tags': [{'Key': 'Name', 'Value': 'hello-world-server'},
                                         {'Key': 'name', 'Value': 'hello-world-service'}]
                                }]
        )

    def stop_instance(self, instance_id):
        return self._client.stop_instances(InstanceIds=[instance_id])

    def terminate_instance(self, instance_id):
        return self._client.terminate_instances(InstanceIds=[instance_id])

# ============================================================
# END OF EC2 CLASS
# ============================================================

# ============================================================
# VPC class for creating EC2 instance with generic functions
# ============================================================

class VPC:
    def __init__(self, client):
        self.client = client

    def create_vpc(self, name):
        return self.client.create_vpc(CidrBlock='10.0.0.0/16',
                                      TagSpecifications=[{'ResourceType': 'vpc',
                                                          'Tags': [{'Key': 'name', 'Value': 'hello-world-service'},
                                                                   {'Key': 'Name', 'Value': name}, ]
                                                          }]
                                      )

    def add_name_tag(self, r_id, resource_name):
        return self.client.create_tags(Resources=[r_id], Tags=[{'Key': 'Name', 'Value': resource_name}])

    def create_internet_gateway(self):
        return self.client.create_internet_gateway(
            TagSpecifications=[{'ResourceType': 'internet-gateway',
                                'Tags': [{'Key': 'name','Value': 'hello-world-service'},
                                         {'Key': 'Name','Value': 'WebInfra_IGW'},]
                }]
        )

    def attach_igw_to_vpc(self, vpc_id, igw_id):
        return self.client.attach_internet_gateway(InternetGatewayId=igw_id, VpcId=vpc_id)

    def create_subnet(self, vpc_id, cidr_block, availability_zone, name):
        return self.client.create_subnet(VpcId=vpc_id, CidrBlock=cidr_block,AvailabilityZone=availability_zone,
                                         TagSpecifications=[{'ResourceType': 'subnet',
                                                             'Tags': [{'Key': 'name', 'Value': 'hello-world-service'},
                                                                      {'Key': 'Name', 'Value': name}, ]
                                                             }]
                                         )

    def create_public_route_table(self, vpc_id):
        return self.client.create_route_table(VpcId=vpc_id,
                                              TagSpecifications=[{'ResourceType': 'route-table',
                                                                  'Tags': [
                                                                      {'Key': 'name', 'Value': 'hello-world-service'},
                                                                      {'Key': 'Name', 'Value': 'WebInfra_Route_table'}, ]
                                                                  }]
                                              )

    def create_igw_route_to_public_route_table(self, rtb_id, igw_id):
        return self.client.create_route(RouteTableId=rtb_id, GatewayId=igw_id, DestinationCidrBlock='0.0.0.0/0')

    def associate_subnet_with_route_table(self, subnet_id, rtb_id):
        return self.client.associate_route_table(SubnetId=subnet_id, RouteTableId=rtb_id)

    def allow_auto_assign_ip_addresses_for_subnet(self, subnet_id):
        return self.client.modify_subnet_attribute(SubnetId=subnet_id, MapPublicIpOnLaunch={'Value': True})

# ============================================================
# END OF VPC CLASS
# ============================================================

# ============================================================
# DELETING AWS INFRASTRUCTURE
# ============================================================

def deletingInfrastructure(aws):
    ec2_client = AWSClient('ec2').get_client()
    if aws.get('elb_response'):
        elb_client = AWSClient('elbv2').get_client()
        elb_client.delete_load_balancer(LoadBalancerArn=aws.get('lb_arn'))
        if aws.get('target_arn'):
            elb_client.deregister_targets(TargetGroupArn=aws.get('target_arn'),
                                          Targets=[{'Id': aws.get('instanceId')}])
            elb_client.delete_target_group(TargetGroupArn=aws.get('target_arn'))
            pprint("Load Balancer Target Group deleted")
        pprint("Load Balancer deleted")

    if aws.get('instances'):
        ec2_client.terminate_instances(InstanceIds=[aws.get('instanceId')])
        ec2_waiter = ec2_client.get_waiter('instance_terminated')
        pprint("Waiting for EC2 Instance get Terminated")
        ec2_waiter.wait(InstanceIds=[aws.get('instanceId')])
        ec2_client.delete_key_pair(KeyName='WebInfra-KeyPair')
        pprint("EC2 Instance Terminated")

    if aws.get('vpc_response'):
        if aws.get('subnet1'):
            ec2_client.delete_subnet(SubnetId=aws.get('subnet1'))
        if aws.get('subnet2'):
            ec2_client.delete_subnet(SubnetId=aws.get('subnet2'))
        if aws.get('security_group_ec2'):
            ec2_client.delete_security_group(GroupId=aws.get('security_group_ec2'))
        if aws.get('security_group_lb'):
            ec2_client.delete_security_group(GroupId=aws.get('security_group_lb'))
        if aws.get('IGW'):
            ec2_client.detach_internet_gateway(InternetGatewayId=aws.get('IGW'), VpcId=aws.get('VpcId'))
            ec2_client.delete_internet_gateway(InternetGatewayId=aws.get('IGW'))
        if aws.get('route'):
            ec2_client.delete_route_table(RouteTableId=aws.get('route'))
        ec2_client.delete_vpc(VpcId=aws.get('VpcId'))
        pprint("VPC Deleted")


# ============================================================
# START OF MAIN CLASS
# ============================================================

def main(ec2_ami_id, vpc_name, kp_name):

    # Collecting all necessary objects to delete later if any error occurred
    aws_infrastructure = {}
    try:
        # Create a VPC
        ec2_client = AWSClient('ec2').get_client()
        vpc = VPC(ec2_client)

        vpc_response = vpc.create_vpc(vpc_name)
        aws_infrastructure['vpc_response'] = vpc_response

        vpc_id = vpc_response['Vpc']['VpcId']
        aws_infrastructure['VpcId'] = vpc_id

        # Wait till VPC is available
        vpc_waiter = ec2_client.get_waiter('vpc_available')
        pprint("Waiting for VPC to be available")
        vpc_waiter.wait(VpcIds=[vpc_id])
        pprint("VPC is available now")

        pprint('Added ' + vpc_name + ' to ' + vpc_id)

        # Create an Internet Gateway
        igw_response = vpc.create_internet_gateway()

        # Attach Internet Gateway to VPC
        igw_id = igw_response['InternetGateway']['InternetGatewayId']
        aws_infrastructure['IGW'] = igw_id
        vpc.attach_igw_to_vpc(vpc_id, igw_id)

        # Create public subnet 1
        public_subnet1_response = vpc.create_subnet(vpc_id, '10.0.1.0/24', 'ca-central-1a', 'Public_subnet1_WebInfra')

        # Create public subnet 2
        public_subnet2_response = vpc.create_subnet(vpc_id, '10.0.2.0/24', 'ca-central-1b', 'Public_subnet2_WebInfra')

        public_subnet1_id = public_subnet1_response['Subnet']['SubnetId']
        aws_infrastructure['subnet1'] = public_subnet1_id
        public_subnet2_id = public_subnet2_response['Subnet']['SubnetId']
        aws_infrastructure['subnet2'] = public_subnet2_id

        print('Subnet 1 created for VPC', vpc_id, ':', str(public_subnet1_response))
        print('Subnet 2 created for VPC', vpc_id, ':', str(public_subnet2_response))

        # Add name tag to Public Subnet
        vpc.add_name_tag(public_subnet1_id, 'WebInfra-Public-Subnet1')
        vpc.add_name_tag(public_subnet2_id, 'WebInfra-Public-Subnet2')

        # Create a public route table
        public_route_table_response = vpc.create_public_route_table(vpc_id)

        route_id = public_route_table_response['RouteTable']['RouteTableId']
        aws_infrastructure['route'] = route_id

        # Adding the IGW to public route table
        vpc.create_igw_route_to_public_route_table(route_id, igw_id)

        # Associate Public Subnet 1 with Route Table
        vpc.associate_subnet_with_route_table(public_subnet1_id, route_id)

        # Associate Public Subnet 2 with Route Table
        vpc.associate_subnet_with_route_table(public_subnet2_id, route_id)

        # Allow auto-assign public ip addresses for subnet 1
        vpc.allow_auto_assign_ip_addresses_for_subnet(public_subnet1_id)

        # Allow auto-assign public ip addresses for subnet 2
        vpc.allow_auto_assign_ip_addresses_for_subnet(public_subnet2_id)

        # EC2 Instance creation
        ec2 = EC2(ec2_client)

        # Create a key pair
        ec2.create_key_pair(kp_name)

        # Create a Security Group
        public_security_group_name = 'WebInfra-Public-SG'
        public_security_group_description = 'Public Security Group for Public Subnet Internet Access'
        public_security_group_response = ec2.create_security_group(public_security_group_name,
                                                                   public_security_group_description, vpc_id)

        public_security_group_id = public_security_group_response['GroupId']
        aws_infrastructure['security_group_ec2'] = public_security_group_id

        # Add Public Access to Security Group
        ec2.add_inbound_rule_to_sg_for_ec2(public_security_group_id)

        # Create a Security Group for Load Balancer
        public_security_group_lb_name = 'WebInfra-LB-Public-SG'
        public_security_group_lb_description = 'Public Security Group for Load Balancer'
        public_security_group_lb_response = ec2.create_security_group(public_security_group_lb_name,
                                                                      public_security_group_lb_description, vpc_id)

        public_security_group_lb_id = public_security_group_lb_response['GroupId']
        aws_infrastructure['security_group_lb'] = public_security_group_lb_id

        # Add Public Access to Security Group for LB
        ec2.add_inbound_rule_to_sg_for_lb(public_security_group_lb_id)

        # Only Load Balancer can access the infrastructure by security group
        ec2.add_inbound_rule_to_ec2_for_lb(public_security_group_id, public_security_group_lb_id)

        user_data = """#!/bin/bash 
                        yum update -y 
                        yum install nginx -y 
                        service nginx start 
                        service nginx enable 
                        echo "<html><body><center><h1>HTTP 200 - Hello World</h1></center></body></html>" > /usr/share/nginx/html/index.html 
                        service nginx restart """

        # Launch a public EC2 Instance
        instances = ec2.launch_ec2_instance(ec2_ami_id, kp_name, 1, 1, public_security_group_id, public_subnet1_id,
                                            user_data)

        aws_infrastructure['instances'] = instances
        instance_id = instances['Instances'][0]['InstanceId']
        aws_infrastructure['instanceId'] = instance_id

        # Wait till EC2 Instance is available
        ec2_waiter = ec2_client.get_waiter('instance_running')
        pprint("Waiting for EC2 instance to be in running state")
        ec2_waiter.wait(InstanceIds=[instance_id])
        pprint("EC2 instance is running")

        # Creating Elastic Load Balancer
        elb_client = AWSClient('elbv2').get_client()

        elb_response = elb_client.create_load_balancer(Name="elbHelloService", Type='application',
                                                       Subnets=[public_subnet1_id, public_subnet2_id],
                                                       SecurityGroups=[public_security_group_lb_id],
                                                       Tags=[{'Key': 'name', 'Value': 'hello-world-service'}],
                                                       Scheme='internet-facing',
                                                       IpAddressType='ipv4')

        aws_infrastructure['elb_response'] = elb_response
        elb_arn = elb_response['LoadBalancers'][0]['LoadBalancerArn']
        aws_infrastructure['lb_arn'] = elb_arn
        DNS_NAME = elb_response['LoadBalancers'][0]['DNSName']

        target_name = 'lb-' + vpc_id.split('-')[1]
        target_response = elb_client.create_target_group(Name=target_name, Protocol='HTTP', Port=80,
                                                         VpcId=vpc_id)

        target_arn = target_response['TargetGroups'][0]['TargetGroupArn']
        aws_infrastructure['target_arn'] = target_arn

        elb_client.register_targets(TargetGroupArn=target_arn,
                                    Targets=[{'Id': instance_id, 'Port': 80}])

        elb_client.create_listener(LoadBalancerArn=elb_arn, Protocol='HTTP', Port=80,
                                   DefaultActions=[{'Type': 'forward', 'ForwardConfig':
                                       {'TargetGroups': [{'TargetGroupArn': target_arn}]}}])

        # Wait till ELB is available
        elb_waiter = elb_client.get_waiter('load_balancer_available')
        pprint("Waiting for Load Balancer to be active")
        elb_waiter.wait(LoadBalancerArns=[elb_arn])
        pprint("Load Balancer is active now")

        print("==================SUCCESS===========================")
        print("Application created and available at ", DNS_NAME)
        print("==================SUCCESS===========================")

    except (ClientError, Exception) as error:
        print("Something went Wrong....................................................")
        print(error)
        print("==================DELETING AWS INFRASTRUCTURE===========================")
        deletingInfrastructure(aws_infrastructure)
        print("AWS INFRASTRUCTURE DELETED")
        print("==================DELETING AWS INFRASTRUCTURE===========================")
    else:
        pprint("AWS INFRASTRUCTURE CREATED")


if __name__ == '__main__':
    # Variables
    ec2_ami_id = 'ami-0269a0d783544d806'
    vpc_name = 'WebInfra-VPC'
    kp_name = 'WebInfra-KeyPair'

    main(ec2_ami_id, vpc_name, kp_name)
