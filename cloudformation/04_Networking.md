# Chapter 4: Networking — Full VPC Template
## VPC, Subnets, IGW, NAT Gateway, Route Tables & Endpoints

---

## 4.1 VPC Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    VPC 10.0.0.0/16                          │
│                                                             │
│  ┌──────── AZ-a ──────────┐  ┌──────── AZ-b ──────────┐    │
│  │ Public  10.0.1.0/24    │  │ Public  10.0.2.0/24    │    │
│  │ (IGW → internet)       │  │                         │    │
│  │  ┌──────────────┐      │  │  ┌──────────────┐      │    │
│  │  │  NAT Gateway │      │  │  │  NAT Gateway │      │    │
│  │  └──────────────┘      │  │  └──────────────┘      │    │
│  ├────────────────────────┤  ├────────────────────────┤    │
│  │ Private 10.0.11.0/24   │  │ Private 10.0.12.0/24   │    │
│  │ (App tier)             │  │                         │    │
│  ├────────────────────────┤  ├────────────────────────┤    │
│  │ DB      10.0.21.0/24   │  │ DB      10.0.22.0/24   │    │
│  │ (Database tier)        │  │                         │    │
│  └────────────────────────┘  └────────────────────────┘    │
│                                                             │
│  VPC Endpoints: S3 (Gateway), DynamoDB (Gateway),           │
│                 Secrets Manager (Interface)                  │
└─────────────────────────────────────────────────────────────┘
```

---

## 4.2 Complete VPC Template

```yaml
# networking.yaml — Full VPC with 3 tiers, 2 AZs
AWSTemplateFormatVersion: "2010-09-09"
Description: Production-grade VPC with public, private, and DB subnets

Parameters:
  VpcCidr:
    Type: String
    Default: 10.0.0.0/16
    Description: CIDR block for the VPC

  Environment:
    Type: String
    Default: prod
    AllowedValues: [dev, staging, prod]

  EnableNatGateway:
    Type: String
    Default: "true"
    AllowedValues: ["true", "false"]
    Description: "Set false in dev to save NAT Gateway cost"

Conditions:
  HasNatGateway: !Equals [!Ref EnableNatGateway, "true"]

Resources:

  # ============================================================
  # VPC
  # ============================================================
  VPC:
    Type: AWS::EC2::VPC
    Properties:
      CidrBlock: !Ref VpcCidr
      EnableDnsHostnames: true
      EnableDnsSupport: true
      Tags:
        - Key: Name
          Value: !Sub "${AWS::StackName}-vpc"

  # ============================================================
  # INTERNET GATEWAY
  # ============================================================
  InternetGateway:
    Type: AWS::EC2::InternetGateway
    Properties:
      Tags:
        - Key: Name
          Value: !Sub "${AWS::StackName}-igw"

  InternetGatewayAttachment:
    Type: AWS::EC2::VPCGatewayAttachment
    Properties:
      VpcId: !Ref VPC
      InternetGatewayId: !Ref InternetGateway

  # ============================================================
  # PUBLIC SUBNETS
  # ============================================================
  PublicSubnet1:
    Type: AWS::EC2::Subnet
    Properties:
      VpcId: !Ref VPC
      CidrBlock: 10.0.1.0/24
      AvailabilityZone: !Select [0, !GetAZs ""]
      MapPublicIpOnLaunch: true
      Tags:
        - Key: Name
          Value: !Sub "${AWS::StackName}-public-1"
        - Key: Tier
          Value: public

  PublicSubnet2:
    Type: AWS::EC2::Subnet
    Properties:
      VpcId: !Ref VPC
      CidrBlock: 10.0.2.0/24
      AvailabilityZone: !Select [1, !GetAZs ""]
      MapPublicIpOnLaunch: true
      Tags:
        - Key: Name
          Value: !Sub "${AWS::StackName}-public-2"
        - Key: Tier
          Value: public

  # ============================================================
  # PRIVATE SUBNETS (APP TIER)
  # ============================================================
  PrivateSubnet1:
    Type: AWS::EC2::Subnet
    Properties:
      VpcId: !Ref VPC
      CidrBlock: 10.0.11.0/24
      AvailabilityZone: !Select [0, !GetAZs ""]
      MapPublicIpOnLaunch: false
      Tags:
        - Key: Name
          Value: !Sub "${AWS::StackName}-private-1"
        - Key: Tier
          Value: private

  PrivateSubnet2:
    Type: AWS::EC2::Subnet
    Properties:
      VpcId: !Ref VPC
      CidrBlock: 10.0.12.0/24
      AvailabilityZone: !Select [1, !GetAZs ""]
      MapPublicIpOnLaunch: false
      Tags:
        - Key: Name
          Value: !Sub "${AWS::StackName}-private-2"
        - Key: Tier
          Value: private

  # ============================================================
  # DATABASE SUBNETS
  # ============================================================
  DBSubnet1:
    Type: AWS::EC2::Subnet
    Properties:
      VpcId: !Ref VPC
      CidrBlock: 10.0.21.0/24
      AvailabilityZone: !Select [0, !GetAZs ""]
      MapPublicIpOnLaunch: false
      Tags:
        - Key: Name
          Value: !Sub "${AWS::StackName}-db-1"
        - Key: Tier
          Value: database

  DBSubnet2:
    Type: AWS::EC2::Subnet
    Properties:
      VpcId: !Ref VPC
      CidrBlock: 10.0.22.0/24
      AvailabilityZone: !Select [1, !GetAZs ""]
      MapPublicIpOnLaunch: false
      Tags:
        - Key: Name
          Value: !Sub "${AWS::StackName}-db-2"
        - Key: Tier
          Value: database

  # ============================================================
  # NAT GATEWAYS (one per AZ for HA)
  # ============================================================
  NatEIP1:
    Type: AWS::EC2::EIP
    Condition: HasNatGateway
    DependsOn: InternetGatewayAttachment
    Properties:
      Domain: vpc

  NatEIP2:
    Type: AWS::EC2::EIP
    Condition: HasNatGateway
    DependsOn: InternetGatewayAttachment
    Properties:
      Domain: vpc

  NatGateway1:
    Type: AWS::EC2::NatGateway
    Condition: HasNatGateway
    Properties:
      AllocationId: !GetAtt NatEIP1.AllocationId
      SubnetId: !Ref PublicSubnet1
      Tags:
        - Key: Name
          Value: !Sub "${AWS::StackName}-nat-1"

  NatGateway2:
    Type: AWS::EC2::NatGateway
    Condition: HasNatGateway
    Properties:
      AllocationId: !GetAtt NatEIP2.AllocationId
      SubnetId: !Ref PublicSubnet2
      Tags:
        - Key: Name
          Value: !Sub "${AWS::StackName}-nat-2"

  # ============================================================
  # ROUTE TABLES
  # ============================================================

  # Public route table — routes all internet traffic through IGW
  PublicRouteTable:
    Type: AWS::EC2::RouteTable
    Properties:
      VpcId: !Ref VPC
      Tags:
        - Key: Name
          Value: !Sub "${AWS::StackName}-public-rt"

  PublicRoute:
    Type: AWS::EC2::Route
    DependsOn: InternetGatewayAttachment
    Properties:
      RouteTableId: !Ref PublicRouteTable
      DestinationCidrBlock: 0.0.0.0/0
      GatewayId: !Ref InternetGateway

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

  # Private route tables — one per AZ, routes through NAT
  PrivateRouteTable1:
    Type: AWS::EC2::RouteTable
    Properties:
      VpcId: !Ref VPC
      Tags:
        - Key: Name
          Value: !Sub "${AWS::StackName}-private-rt-1"

  PrivateRoute1:
    Type: AWS::EC2::Route
    Condition: HasNatGateway
    Properties:
      RouteTableId: !Ref PrivateRouteTable1
      DestinationCidrBlock: 0.0.0.0/0
      NatGatewayId: !Ref NatGateway1

  PrivateSubnet1RouteTableAssociation:
    Type: AWS::EC2::SubnetRouteTableAssociation
    Properties:
      SubnetId: !Ref PrivateSubnet1
      RouteTableId: !Ref PrivateRouteTable1

  PrivateRouteTable2:
    Type: AWS::EC2::RouteTable
    Properties:
      VpcId: !Ref VPC
      Tags:
        - Key: Name
          Value: !Sub "${AWS::StackName}-private-rt-2"

  PrivateRoute2:
    Type: AWS::EC2::Route
    Condition: HasNatGateway
    Properties:
      RouteTableId: !Ref PrivateRouteTable2
      DestinationCidrBlock: 0.0.0.0/0
      NatGatewayId: !Ref NatGateway2

  PrivateSubnet2RouteTableAssociation:
    Type: AWS::EC2::SubnetRouteTableAssociation
    Properties:
      SubnetId: !Ref PrivateSubnet2
      RouteTableId: !Ref PrivateRouteTable2

  DBSubnet1RouteTableAssociation:
    Type: AWS::EC2::SubnetRouteTableAssociation
    Properties:
      SubnetId: !Ref DBSubnet1
      RouteTableId: !Ref PrivateRouteTable1

  DBSubnet2RouteTableAssociation:
    Type: AWS::EC2::SubnetRouteTableAssociation
    Properties:
      SubnetId: !Ref DBSubnet2
      RouteTableId: !Ref PrivateRouteTable2

  # ============================================================
  # VPC ENDPOINTS (avoid NAT Gateway charges for AWS services)
  # ============================================================

  # S3 Gateway Endpoint — free, routes S3 traffic within AWS
  S3GatewayEndpoint:
    Type: AWS::EC2::VPCEndpoint
    Properties:
      VpcId: !Ref VPC
      ServiceName: !Sub "com.amazonaws.${AWS::Region}.s3"
      VpcEndpointType: Gateway
      RouteTableIds:
        - !Ref PrivateRouteTable1
        - !Ref PrivateRouteTable2

  # DynamoDB Gateway Endpoint — free
  DynamoDBGatewayEndpoint:
    Type: AWS::EC2::VPCEndpoint
    Properties:
      VpcId: !Ref VPC
      ServiceName: !Sub "com.amazonaws.${AWS::Region}.dynamodb"
      VpcEndpointType: Gateway
      RouteTableIds:
        - !Ref PrivateRouteTable1
        - !Ref PrivateRouteTable2

  # Secrets Manager Interface Endpoint — allows Lambda/EC2 to
  # retrieve secrets without going through NAT
  SecretsManagerEndpointSG:
    Type: AWS::EC2::SecurityGroup
    Properties:
      GroupDescription: Security group for Secrets Manager endpoint
      VpcId: !Ref VPC
      SecurityGroupIngress:
        - IpProtocol: tcp
          FromPort: 443
          ToPort: 443
          CidrIp: !Ref VpcCidr

  SecretsManagerEndpoint:
    Type: AWS::EC2::VPCEndpoint
    Properties:
      VpcId: !Ref VPC
      ServiceName: !Sub "com.amazonaws.${AWS::Region}.secretsmanager"
      VpcEndpointType: Interface
      SubnetIds:
        - !Ref PrivateSubnet1
        - !Ref PrivateSubnet2
      SecurityGroupIds:
        - !Ref SecretsManagerEndpointSG
      PrivateDnsEnabled: true

# ============================================================
# OUTPUTS — export for use by other stacks
# ============================================================
Outputs:
  VpcId:
    Value: !Ref VPC
    Export:
      Name: !Sub "${AWS::StackName}-VpcId"

  VpcCidr:
    Value: !GetAtt VPC.CidrBlock
    Export:
      Name: !Sub "${AWS::StackName}-VpcCidr"

  PublicSubnets:
    Value: !Join [",", [!Ref PublicSubnet1, !Ref PublicSubnet2]]
    Export:
      Name: !Sub "${AWS::StackName}-PublicSubnets"

  PrivateSubnets:
    Value: !Join [",", [!Ref PrivateSubnet1, !Ref PrivateSubnet2]]
    Export:
      Name: !Sub "${AWS::StackName}-PrivateSubnets"

  DBSubnets:
    Value: !Join [",", [!Ref DBSubnet1, !Ref DBSubnet2]]
    Export:
      Name: !Sub "${AWS::StackName}-DBSubnets"

  PublicSubnet1Id:
    Value: !Ref PublicSubnet1
    Export:
      Name: !Sub "${AWS::StackName}-PublicSubnet1"

  PublicSubnet2Id:
    Value: !Ref PublicSubnet2
    Export:
      Name: !Sub "${AWS::StackName}-PublicSubnet2"

  PrivateSubnet1Id:
    Value: !Ref PrivateSubnet1
    Export:
      Name: !Sub "${AWS::StackName}-PrivateSubnet1"

  PrivateSubnet2Id:
    Value: !Ref PrivateSubnet2
    Export:
      Name: !Sub "${AWS::StackName}-PrivateSubnet2"
```

---

## 4.3 Deploying the VPC Stack

```bash
# Deploy VPC (dev — no NAT Gateway to save cost)
aws cloudformation deploy \
  --template-file networking.yaml \
  --stack-name myapp-networking \
  --parameter-overrides \
    Environment=dev \
    EnableNatGateway=false \
  --region us-east-1

# Deploy VPC (prod — with NAT Gateways in both AZs)
aws cloudformation deploy \
  --template-file networking.yaml \
  --stack-name myapp-networking-prod \
  --parameter-overrides \
    Environment=prod \
    EnableNatGateway=true \
  --region us-east-1

# Reference VPC outputs in another stack
aws cloudformation deploy \
  --template-file app-stack.yaml \
  --stack-name myapp \
  --parameter-overrides \
    NetworkingStack=myapp-networking
```

---

## 4.4 Interview Questions

**Q: Why do you need two NAT Gateways in a highly available VPC?**
> A NAT Gateway is AZ-specific. If you have one NAT Gateway in AZ-a and it fails (or AZ-a has an outage), all private subnets in AZ-b lose outbound internet access. For HA, deploy one NAT Gateway per AZ, and set each AZ's private subnet route table to use its local NAT Gateway. This adds cost (~$32/month per NAT) but eliminates the NAT as a single point of failure. In dev/staging, one NAT is acceptable.

**Q: What is the difference between a Gateway VPC Endpoint and an Interface VPC Endpoint?**
> A Gateway Endpoint (only for S3 and DynamoDB) is free and works by adding a route to your route tables that directs S3/DynamoDB traffic through AWS's private network instead of the internet — no interface is created. An Interface Endpoint (for most other services: Secrets Manager, SSM, ECR, CloudWatch, etc.) creates an ENI (Elastic Network Interface) in your subnet with a private IP, and you're billed per hour plus data processed (~$0.01/GB). Gateway endpoints are always recommended for S3/DynamoDB as they're free and reduce NAT Gateway data charges.

**Q: What is `MapPublicIpOnLaunch` and when should you set it to false?**
> `MapPublicIpOnLaunch: true` on a subnet means any EC2 instance launched in that subnet automatically gets a public IP. This is appropriate for public subnets (where you want internet-accessible instances). Set it to `false` for private and database subnets — those resources should never be directly reachable from the internet. Access them through an ALB, NAT Gateway, or bastion host instead.
