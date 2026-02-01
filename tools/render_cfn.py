import json

with open("design/design.json", encoding="utf-8") as f:
    d = json.load(f)

instances = int(d.get("web", {}).get("instances", 1))
instance_type = d.get("web", {}).get("instanceType", "t3.micro")

# まずは既存の cfn/main.yaml をそのまま使い、
# "EC2の台数" だけを実現するために、WebInstanceを2台まで生成する簡易版。
# （この後 ALB 追加のタイミングで本格化します）

# 既存テンプレの「土台＋WebInstance1台」版をベースにしつつ、
# instances=2のときは WebInstance2 を追加する。

base = f"""AWSTemplateFormatVersion: "2010-09-09"
Description: "ai-iac-demo: VPC baseline + EC2 (nginx) generated from design.json"

Parameters:
  VpcCidr:
    Type: String
    Default: 10.0.0.0/16
  PublicSubnet1Cidr:
    Type: String
    Default: 10.0.1.0/24
  PublicSubnet2Cidr:
    Type: String
    Default: 10.0.2.0/24
  Az1:
    Type: AWS::EC2::AvailabilityZone::Name
    Default: ap-northeast-1a
  Az2:
    Type: AWS::EC2::AvailabilityZone::Name
    Default: ap-northeast-1c
  InstanceType:
    Type: String
    Default: {instance_type}

Resources:
  VPC:
    Type: AWS::EC2::VPC
    Properties:
      CidrBlock: !Ref VpcCidr
      EnableDnsSupport: true
      EnableDnsHostnames: true
      Tags:
        - Key: Name
          Value: ai-iac-demo-vpc

  InternetGateway:
    Type: AWS::EC2::InternetGateway
    Properties:
      Tags:
        - Key: Name
          Value: ai-iac-demo-igw

  AttachGateway:
    Type: AWS::EC2::VPCGatewayAttachment
    Properties:
      VpcId: !Ref VPC
      InternetGatewayId: !Ref InternetGateway

  PublicRouteTable:
    Type: AWS::EC2::RouteTable
    Properties:
      VpcId: !Ref VPC
      Tags:
        - Key: Name
          Value: ai-iac-demo-public-rt

  PublicDefaultRoute:
    Type: AWS::EC2::Route
    DependsOn: AttachGateway
    Properties:
      RouteTableId: !Ref PublicRouteTable
      DestinationCidrBlock: 0.0.0.0/0
      GatewayId: !Ref InternetGateway

  PublicSubnet1:
    Type: AWS::EC2::Subnet
    Properties:
      VpcId: !Ref VPC
      CidrBlock: !Ref PublicSubnet1Cidr
      AvailabilityZone: !Ref Az1
      MapPublicIpOnLaunch: true
      Tags:
        - Key: Name
          Value: ai-iac-demo-public-1

  PublicSubnet2:
    Type: AWS::EC2::Subnet
    Properties:
      VpcId: !Ref VPC
      CidrBlock: !Ref PublicSubnet2Cidr
      AvailabilityZone: !Ref Az2
      MapPublicIpOnLaunch: true
      Tags:
        - Key: Name
          Value: ai-iac-demo-public-2

  PublicSubnet1RouteTableAssociation:
    Type: AWS::EC2::SubnetRouteTableAssociation
    Properties:
      SubnetId: !Ref PublicSubnet1
      RouteTableId: !Ref PublicRouteTable

  PublicSubnet2RouteTableAssociation:
    Type: AWS::EC2::SubnetRouteTableAssociation
    Properties:
      SubnetId: !Ref PublicSubnet2
      RouteTableId: !Ref PublicRouteTable

  WebSecurityGroup:
    Type: AWS::EC2::SecurityGroup
    Properties:
      GroupDescription: Allow HTTP
      VpcId: !Ref VPC
      SecurityGroupIngress:
        - IpProtocol: tcp
          FromPort: 80
          ToPort: 80
          CidrIp: 0.0.0.0/0

  WebInstance1:
    Type: AWS::EC2::Instance
    Properties:
      InstanceType: !Ref InstanceType
      SubnetId: !Ref PublicSubnet1
      SecurityGroupIds:
        - !Ref WebSecurityGroup
      ImageId: !Sub "{{{{resolve:ssm:/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-6.1-x86_64}}}}"
      UserData:
        Fn::Base64: !Sub |
          #!/bin/bash
          set -eux
          dnf -y update
          dnf -y install nginx
          systemctl enable nginx
          echo "Hello from web-1 $(hostname)" > /usr/share/nginx/html/index.html
          systemctl start nginx
      Tags:
        - Key: Name
          Value: ai-iac-demo-web-1
"""

extra = ""
if instances >= 2:
    extra = """
  WebInstance2:
    Type: AWS::EC2::Instance
    Properties:
      InstanceType: !Ref InstanceType
      SubnetId: !Ref PublicSubnet2
      SecurityGroupIds:
        - !Ref WebSecurityGroup
      ImageId: !Sub "{{resolve:ssm:/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-6.1-x86_64}}"
      UserData:
        Fn::Base64: !Sub |
          #!/bin/bash
          set -eux
          dnf -y update
          dnf -y install nginx
          systemctl enable nginx
          echo "Hello from web-2 $(hostname)" > /usr/share/nginx/html/index.html
          systemctl start nginx
      Tags:
        - Key: Name
          Value: ai-iac-demo-web-2
"""

outputs = """
Outputs:
  VpcId:
    Value: !Ref VPC
  Web1PublicIp:
    Value: !GetAtt WebInstance1.PublicIp
"""

if instances >= 2:
    outputs += """
  Web2PublicIp:
    Value: !GetAtt WebInstance2.PublicIp
"""

with open("cfn/main.yaml", "w", encoding="utf-8") as f:
    f.write(base + extra + outputs)

print("generated: cfn/main.yaml (instances =", instances, ")")
