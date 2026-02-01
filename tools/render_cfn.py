import json, os

DESIGN_PATH = "design/design.json"
OUT_PATH = "cfn/main.yaml"
os.makedirs("cfn", exist_ok=True)

with open(DESIGN_PATH, encoding="utf-8") as f:
    d = json.load(f)

# ここが必ず web.instances を拾うように強制
web = d.get("web", {})
# 保険：web.instances が無い場合、EC2.instances も拾う
if "instances" not in web and isinstance(d.get("EC2"), dict) and "instances" in d["EC2"]:
    web["instances"] = d["EC2"]["instances"]

instances_raw = web.get("instances", 1)

try:
    instances = int(instances_raw)
except Exception:
    # もし "2台" みたいな文字列が来ても数字だけ拾う
    import re
    m = re.search(r"\d+", str(instances_raw))
    instances = int(m.group(0)) if m else 1

instances = max(1, min(instances, 2))  # デモなので 1〜2 台に制限
instance_type = web.get("instanceType", "t3.micro")

print(f"generated: {OUT_PATH} (instances = {instances})")

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

  PublicSubnet2:
    Type: AWS::EC2::Subnet
    Properties:
      VpcId: !Ref VPC
      CidrBlock: !Ref PublicSubnet2Cidr
      AvailabilityZone: !Ref Az2
      MapPublicIpOnLaunch: true

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
      SecurityGroupIds: [!Ref WebSecurityGroup]
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
      SecurityGroupIds: [!Ref WebSecurityGroup]
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
  Web1PublicIp:
    Value: !GetAtt WebInstance1.PublicIp
"""

if instances >= 2:
    outputs += """
  Web2PublicIp:
    Value: !GetAtt WebInstance2.PublicIp
"""

with open(OUT_PATH, "w", encoding="utf-8", newline="\n") as f:
    f.write(base + extra + outputs)
