# CloudFormation Chapter 4: Networking Templates
## VPC, Subnets, NAT, ALB, Security Groups — Production-Ready Patterns

---

## 4.1 Complete VPC Template

```yaml
# vpc.yaml — Production VPC with public/private/DB subnets, 3 AZs
AWSTemplateFormatVersion: '2010-09-09'
Description: Production VPC with 3-tier subnets across 3 Availability Zones

Parameters:
  ProjectName:
    Type: String
    Default: myapp
  
  VpcCidr:
    Type: String
    Default: 10.0.0.0/16
    AllowedPattern: '^(\d{1,3}\.){3}\d{1,3}\/\d{1,2}$'
  
  EnableNatGateway:
    Type: String
    AllowedValues: [true, false]
    Default: true

  NatGatewayCount:
    Type: Number
    AllowedValues: [1, 3]
    Default: 1
    Description: 1 for cost savings, 3 for high availability

Conditions:
  EnableNAT: !Equals [!Ref EnableNatGateway, true]
  HighlyAvailableNAT: !And
    - !Condition EnableNAT
    - !Equals [!Ref NatGatewayCount, 3]

Resources:
  # ── VPC ──────────────────────────────────────────────
  VPC:
    Type: AWS::EC2::VPC
    Properties:
      CidrBlock: !Ref VpcCidr
      EnableDnsHostnames: true
      EnableDnsSupport: true
      InstanceTenancy: default
      Tags:
        - Key: Name
          Value: !Sub '${ProjectName}-vpc'

  # ── Internet Gateway ──────────────────────────────────
  InternetGateway:
    Type: AWS::EC2::InternetGateway
    Properties:
      Tags:
        - Key: Name
          Value: !Sub '${ProjectName}-igw'

  VPCGatewayAttachment:
    Type: AWS::EC2::VPCGatewayAttachment
    Properties:
      VpcId: !Ref VPC
      InternetGatewayId: !Ref InternetGateway

  # ── Public Subnets ────────────────────────────────────
  PublicSubnet1:
    Type: AWS::EC2::Subnet
    Properties:
      VpcId: !Ref VPC
      CidrBlock: !Select [0, !Cidr [!Ref VpcCidr, 12, 8]]   # 10.0.0.0/24
      AvailabilityZone: !Select [0, !GetAZs '']
      MapPublicIpOnLaunch: false    # Don't auto-assign public IPs (security)
      Tags:
        - Key: Name
          Value: !Sub '${ProjectName}-public-1'
        - Key: kubernetes.io/role/elb    # For ALB auto-discovery
          Value: 1

  PublicSubnet2:
    Type: AWS::EC2::Subnet
    Properties:
      VpcId: !Ref VPC
      CidrBlock: !Select [1, !Cidr [!Ref VpcCidr, 12, 8]]   # 10.0.1.0/24
      AvailabilityZone: !Select [1, !GetAZs '']
      MapPublicIpOnLaunch: false
      Tags:
        - Key: Name
          Value: !Sub '${ProjectName}-public-2'
        - Key: kubernetes.io/role/elb
          Value: 1

  PublicSubnet3:
    Type: AWS::EC2::Subnet
    Properties:
      VpcId: !Ref VPC
      CidrBlock: !Select [2, !Cidr [!Ref VpcCidr, 12, 8]]   # 10.0.2.0/24
      AvailabilityZone: !Select [2, !GetAZs '']
      MapPublicIpOnLaunch: false
      Tags:
        - Key: Name
          Value: !Sub '${ProjectName}-public-3'
        - Key: kubernetes.io/role/elb
          Value: 1

  # ── Private (App) Subnets ─────────────────────────────
  PrivateSubnet1:
    Type: AWS::EC2::Subnet
    Properties:
      VpcId: !Ref VPC
      CidrBlock: !Select [3, !Cidr [!Ref VpcCidr, 12, 8]]   # 10.0.3.0/24
      AvailabilityZone: !Select [0, !GetAZs '']
      Tags:
        - Key: Name
          Value: !Sub '${ProjectName}-private-1'
        - Key: kubernetes.io/role/internal-elb
          Value: 1

  PrivateSubnet2:
    Type: AWS::EC2::Subnet
    Properties:
      VpcId: !Ref VPC
      CidrBlock: !Select [4, !Cidr [!Ref VpcCidr, 12, 8]]   # 10.0.4.0/24
      AvailabilityZone: !Select [1, !GetAZs '']
      Tags:
        - Key: Name
          Value: !Sub '${ProjectName}-private-2'

  PrivateSubnet3:
    Type: AWS::EC2::Subnet
    Properties:
      VpcId: !Ref VPC
      CidrBlock: !Select [5, !Cidr [!Ref VpcCidr, 12, 8]]   # 10.0.5.0/24
      AvailabilityZone: !Select [2, !GetAZs '']
      Tags:
        - Key: Name
          Value: !Sub '${ProjectName}-private-3'

  # ── Database Subnets ──────────────────────────────────
  DBSubnet1:
    Type: AWS::EC2::Subnet
    Properties:
      VpcId: !Ref VPC
      CidrBlock: !Select [6, !Cidr [!Ref VpcCidr, 12, 8]]   # 10.0.6.0/24
      AvailabilityZone: !Select [0, !GetAZs '']
      Tags:
        - Key: Name
          Value: !Sub '${ProjectName}-db-1'

  DBSubnet2:
    Type: AWS::EC2::Subnet
    Properties:
      VpcId: !Ref VPC
      CidrBlock: !Select [7, !Cidr [!Ref VpcCidr, 12, 8]]   # 10.0.7.0/24
      AvailabilityZone: !Select [1, !GetAZs '']
      Tags:
        - Key: Name
          Value: !Sub '${ProjectName}-db-2'

  DBSubnet3:
    Type: AWS::EC2::Subnet
    Properties:
      VpcId: !Ref VPC
      CidrBlock: !Select [8, !Cidr [!Ref VpcCidr, 12, 8]]   # 10.0.8.0/24
      AvailabilityZone: !Select [2, !GetAZs '']
      Tags:
        - Key: Name
          Value: !Sub '${ProjectName}-db-3'

  # ── NAT Gateways ──────────────────────────────────────
  NATEIP1:
    Type: AWS::EC2::EIP
    Condition: EnableNAT
    DependsOn: VPCGatewayAttachment
    Properties:
      Domain: vpc
      Tags:
        - Key: Name
          Value: !Sub '${ProjectName}-nat-eip-1'

  NATGateway1:
    Type: AWS::EC2::NatGateway
    Condition: EnableNAT
    Properties:
      AllocationId: !GetAtt NATEIP1.AllocationId
      SubnetId: !Ref PublicSubnet1   # NAT goes in PUBLIC subnet
      Tags:
        - Key: Name
          Value: !Sub '${ProjectName}-nat-1'

  # Optional: Additional NAT gateways for HA (AZ2 and AZ3)
  NATEIP2:
    Type: AWS::EC2::EIP
    Condition: HighlyAvailableNAT
    DependsOn: VPCGatewayAttachment
    Properties:
      Domain: vpc

  NATGateway2:
    Type: AWS::EC2::NatGateway
    Condition: HighlyAvailableNAT
    Properties:
      AllocationId: !GetAtt NATEIP2.AllocationId
      SubnetId: !Ref PublicSubnet2

  NATEIP3:
    Type: AWS::EC2::EIP
    Condition: HighlyAvailableNAT
    DependsOn: VPCGatewayAttachment
    Properties:
      Domain: vpc

  NATGateway3:
    Type: AWS::EC2::NatGateway
    Condition: HighlyAvailableNAT
    Properties:
      AllocationId: !GetAtt NATEIP3.AllocationId
      SubnetId: !Ref PublicSubnet3

  # ── Route Tables ──────────────────────────────────────
  PublicRouteTable:
    Type: AWS::EC2::RouteTable
    Properties:
      VpcId: !Ref VPC
      Tags:
        - Key: Name
          Value: !Sub '${ProjectName}-public-rt'

  PublicRoute:
    Type: AWS::EC2::Route
    DependsOn: VPCGatewayAttachment
    Properties:
      RouteTableId: !Ref PublicRouteTable
      DestinationCidrBlock: 0.0.0.0/0
      GatewayId: !Ref InternetGateway

  # Associate public subnets with public route table
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

  PublicSubnet3RouteTableAssociation:
    Type: AWS::EC2::SubnetRouteTableAssociation
    Properties:
      SubnetId: !Ref PublicSubnet3
      RouteTableId: !Ref PublicRouteTable

  # Private route tables (one per AZ for HA NAT)
  PrivateRouteTable1:
    Type: AWS::EC2::RouteTable
    Properties:
      VpcId: !Ref VPC
      Tags:
        - Key: Name
          Value: !Sub '${ProjectName}-private-rt-1'

  PrivateRoute1:
    Type: AWS::EC2::Route
    Condition: EnableNAT
    Properties:
      RouteTableId: !Ref PrivateRouteTable1
      DestinationCidrBlock: 0.0.0.0/0
      NatGatewayId: !Ref NATGateway1

  PrivateSubnet1RouteTableAssociation:
    Type: AWS::EC2::SubnetRouteTableAssociation
    Properties:
      SubnetId: !Ref PrivateSubnet1
      RouteTableId: !Ref PrivateRouteTable1

  # DB subnets get no NAT (databases shouldn't access internet)
  DBRouteTable:
    Type: AWS::EC2::RouteTable
    Properties:
      VpcId: !Ref VPC
      Tags:
        - Key: Name
          Value: !Sub '${ProjectName}-db-rt'

  DBSubnet1RouteTableAssociation:
    Type: AWS::EC2::SubnetRouteTableAssociation
    Properties:
      SubnetId: !Ref DBSubnet1
      RouteTableId: !Ref DBRouteTable

  DBSubnet2RouteTableAssociation:
    Type: AWS::EC2::SubnetRouteTableAssociation
    Properties:
      SubnetId: !Ref DBSubnet2
      RouteTableId: !Ref DBRouteTable

  DBSubnet3RouteTableAssociation:
    Type: AWS::EC2::SubnetRouteTableAssociation
    Properties:
      SubnetId: !Ref DBSubnet3
      RouteTableId: !Ref DBRouteTable

  # ── VPC Endpoints ─────────────────────────────────────
  S3GatewayEndpoint:
    Type: AWS::EC2::VPCEndpoint
    Properties:
      VpcId: !Ref VPC
      ServiceName: !Sub 'com.amazonaws.${AWS::Region}.s3'
      VpcEndpointType: Gateway
      RouteTableIds:
        - !Ref PrivateRouteTable1

  DynamoDBGatewayEndpoint:
    Type: AWS::EC2::VPCEndpoint
    Properties:
      VpcId: !Ref VPC
      ServiceName: !Sub 'com.amazonaws.${AWS::Region}.dynamodb'
      VpcEndpointType: Gateway
      RouteTableIds:
        - !Ref PrivateRouteTable1

  # SSM Interface Endpoint (for Session Manager without internet)
  SSMEndpoint:
    Type: AWS::EC2::VPCEndpoint
    Properties:
      VpcId: !Ref VPC
      ServiceName: !Sub 'com.amazonaws.${AWS::Region}.ssm'
      VpcEndpointType: Interface
      SubnetIds:
        - !Ref PrivateSubnet1
        - !Ref PrivateSubnet2
      SecurityGroupIds:
        - !Ref VPCEndpointSecurityGroup
      PrivateDnsEnabled: true

  VPCEndpointSecurityGroup:
    Type: AWS::EC2::SecurityGroup
    Properties:
      GroupDescription: VPC Endpoint Security Group
      VpcId: !Ref VPC
      SecurityGroupIngress:
        - IpProtocol: tcp
          FromPort: 443
          ToPort: 443
          CidrIp: !Ref VpcCidr
      Tags:
        - Key: Name
          Value: !Sub '${ProjectName}-vpce-sg'

  # ── DB Subnet Group ───────────────────────────────────
  DBSubnetGroup:
    Type: AWS::RDS::DBSubnetGroup
    Properties:
      DBSubnetGroupName: !Sub '${ProjectName}-db-subnet-group'
      DBSubnetGroupDescription: DB subnet group across 3 AZs
      SubnetIds:
        - !Ref DBSubnet1
        - !Ref DBSubnet2
        - !Ref DBSubnet3

  # ── Flow Logs ─────────────────────────────────────────
  VPCFlowLogRole:
    Type: AWS::IAM::Role
    Properties:
      AssumeRolePolicyDocument:
        Version: '2012-10-17'
        Statement:
          - Effect: Allow
            Principal:
              Service: vpc-flow-logs.amazonaws.com
            Action: sts:AssumeRole
      Policies:
        - PolicyName: FlowLogs
          PolicyDocument:
            Version: '2012-10-17'
            Statement:
              - Effect: Allow
                Action:
                  - logs:CreateLogGroup
                  - logs:CreateLogStream
                  - logs:PutLogEvents
                  - logs:DescribeLogGroups
                  - logs:DescribeLogStreams
                Resource: '*'

  FlowLogGroup:
    Type: AWS::Logs::LogGroup
    Properties:
      LogGroupName: !Sub '/vpc/${ProjectName}/flow-logs'
      RetentionInDays: 90

  VPCFlowLog:
    Type: AWS::EC2::FlowLog
    Properties:
      ResourceType: VPC
      ResourceId: !Ref VPC
      TrafficType: ALL
      LogDestinationType: cloud-watch-logs
      LogGroupName: !Ref FlowLogGroup
      DeliverLogsPermissionArn: !GetAtt VPCFlowLogRole.Arn
      LogFormat: '${version} ${account-id} ${interface-id} ${srcaddr} ${dstaddr} ${srcport} ${dstport} ${protocol} ${packets} ${bytes} ${start} ${end} ${action} ${log-status} ${vpc-id} ${subnet-id} ${instance-id} ${tcp-flags} ${type} ${pkt-srcaddr} ${pkt-dstaddr}'

Outputs:
  VpcId:
    Value: !Ref VPC
    Export:
      Name: !Sub '${AWS::StackName}-VpcId'
  
  PublicSubnets:
    Value: !Join [',', [!Ref PublicSubnet1, !Ref PublicSubnet2, !Ref PublicSubnet3]]
    Export:
      Name: !Sub '${AWS::StackName}-PublicSubnets'
  
  PrivateSubnets:
    Value: !Join [',', [!Ref PrivateSubnet1, !Ref PrivateSubnet2, !Ref PrivateSubnet3]]
    Export:
      Name: !Sub '${AWS::StackName}-PrivateSubnets'

  DBSubnetGroupName:
    Value: !Ref DBSubnetGroup
    Export:
      Name: !Sub '${AWS::StackName}-DBSubnetGroup'
```

---

## 4.2 Application Load Balancer Template

```yaml
  # ── ALB Security Group ────────────────────────────────
  ALBSecurityGroup:
    Type: AWS::EC2::SecurityGroup
    Properties:
      GroupDescription: ALB security group — allow HTTP/HTTPS from internet
      VpcId: !ImportValue 'network-stack-VpcId'
      SecurityGroupIngress:
        - IpProtocol: tcp
          FromPort: 80
          ToPort: 80
          CidrIp: 0.0.0.0/0
        - IpProtocol: tcp
          FromPort: 443
          ToPort: 443
          CidrIp: 0.0.0.0/0
      Tags:
        - Key: Name
          Value: !Sub '${AWS::StackName}-alb-sg'

  # ── App Security Group (allow from ALB only) ──────────
  AppSecurityGroup:
    Type: AWS::EC2::SecurityGroup
    Properties:
      GroupDescription: App servers — allow traffic from ALB only
      VpcId: !ImportValue 'network-stack-VpcId'
      SecurityGroupIngress:
        - IpProtocol: tcp
          FromPort: 8080
          ToPort: 8080
          SourceSecurityGroupId: !Ref ALBSecurityGroup    # Reference to SG
          Description: Allow from ALB
      Tags:
        - Key: Name
          Value: !Sub '${AWS::StackName}-app-sg'

  # ── Application Load Balancer ─────────────────────────
  ALB:
    Type: AWS::ElasticLoadBalancingV2::LoadBalancer
    Properties:
      Name: !Sub '${AWS::StackName}-alb'
      Type: application
      Scheme: internet-facing
      Subnets: !Split [',', !ImportValue 'network-stack-PublicSubnets']
      SecurityGroups:
        - !Ref ALBSecurityGroup
      LoadBalancerAttributes:
        - Key: idle_timeout.timeout_seconds
          Value: "60"
        - Key: routing.http.drop_invalid_header_fields.enabled
          Value: "true"
        - Key: routing.http2.enabled
          Value: "true"
        - Key: access_logs.s3.enabled
          Value: "true"
        - Key: access_logs.s3.bucket
          Value: !Ref ALBAccessLogsBucket
        - Key: deletion_protection.enabled
          Value: !If [IsProd, "true", "false"]

  # ── HTTPS Listener (redirect HTTP, forward HTTPS) ─────
  HTTPListener:
    Type: AWS::ElasticLoadBalancingV2::Listener
    Properties:
      LoadBalancerArn: !Ref ALB
      Port: 80
      Protocol: HTTP
      DefaultActions:
        - Type: redirect
          RedirectConfig:
            Protocol: HTTPS
            Port: "443"
            Host: "#{host}"
            Path: "/#{path}"
            Query: "#{query}"
            StatusCode: HTTP_301

  HTTPSListener:
    Type: AWS::ElasticLoadBalancingV2::Listener
    Properties:
      LoadBalancerArn: !Ref ALB
      Port: 443
      Protocol: HTTPS
      SslPolicy: ELBSecurityPolicy-TLS13-1-2-2021-06   # TLS 1.2/1.3 only
      Certificates:
        - CertificateArn: !Ref ACMCertificate
      DefaultActions:
        - Type: fixed-response
          FixedResponseConfig:
            StatusCode: "404"
            ContentType: application/json
            MessageBody: '{"error": "Not found"}'

  # ── Target Group ──────────────────────────────────────
  AppTargetGroup:
    Type: AWS::ElasticLoadBalancingV2::TargetGroup
    Properties:
      Name: !Sub '${AWS::StackName}-app-tg'
      Protocol: HTTP
      Port: 8080
      VpcId: !ImportValue 'network-stack-VpcId'
      TargetType: ip           # Use 'ip' for ECS Fargate, 'instance' for EC2
      HealthCheckEnabled: true
      HealthCheckPath: /health
      HealthCheckIntervalSeconds: 30
      HealthCheckTimeoutSeconds: 5
      HealthyThresholdCount: 2
      UnhealthyThresholdCount: 3
      HealthCheckProtocol: HTTP
      Matcher:
        HttpCode: "200"
      DeregistrationDelay: 30    # Wait 30s for in-flight requests to complete
      TargetGroupAttributes:
        - Key: stickiness.enabled
          Value: "false"
        - Key: load_balancing.algorithm.type
          Value: least_outstanding_requests

  # ── Listener Rules ────────────────────────────────────
  APIListenerRule:
    Type: AWS::ElasticLoadBalancingV2::ListenerRule
    Properties:
      ListenerArn: !Ref HTTPSListener
      Priority: 100
      Conditions:
        - Field: path-pattern
          PathPatternConfig:
            Values:
              - /api/*
              - /health
      Actions:
        - Type: forward
          ForwardConfig:
            TargetGroups:
              - TargetGroupArn: !Ref AppTargetGroup
                Weight: 1

  AdminListenerRule:
    Type: AWS::ElasticLoadBalancingV2::ListenerRule
    Properties:
      ListenerArn: !Ref HTTPSListener
      Priority: 200
      Conditions:
        - Field: path-pattern
          PathPatternConfig:
            Values: [/admin/*]
        - Field: source-ip
          SourceIpConfig:
            Values: ["10.0.0.0/8"]    # Only internal IPs
      Actions:
        - Type: forward
          TargetGroupArn: !Ref AdminTargetGroup
```

---

## 4.3 Interview Q&A

**Q: Why use `!Cidr` and `!Select` together for subnet CIDRs?**
A: `!Cidr` generates a list of subnets from a parent CIDR: `!Cidr [10.0.0.0/16, 12, 8]` generates 12 /24 subnets from 10.0.0.0/16. `!Select [index, list]` picks a specific one. This is dynamic — changing the VPC CIDR automatically recalculates all subnet CIDRs. Alternative: hardcode CIDRs as parameters. The `!Cidr` approach is cleaner for multi-AZ templates where you need consistent relative addressing, though hardcoded parameters are more explicit and easier to understand.

**Q: What is the difference between a Gateway endpoint and an Interface endpoint?**
A: Gateway endpoints (S3 and DynamoDB only) add route table entries that route traffic to AWS services without leaving the VPC — free to use. Interface endpoints (PrivateLink) create ENIs in your subnets with private IP addresses, available for most AWS services, cost ~$0.01/hour/AZ plus data transfer. Gateway endpoints are simpler (just route table entries), don't support security group control. Interface endpoints support security groups, work across VPC peering/Direct Connect/VPN. Use Gateway for S3/DynamoDB always; use Interface for other services when needed.

**Q: How do you configure ALB to only allow HTTPS traffic?**
A: Two steps: (1) HTTP listener (port 80) with a Redirect action to HTTPS (301 redirect) — this handles users accidentally accessing HTTP; (2) HTTPS listener (port 443) with the actual application forwarding. For the TLS policy, use `ELBSecurityPolicy-TLS13-1-2-2021-06` which supports only TLS 1.2 and 1.3 (no TLS 1.0/1.1). Also set `routing.http.drop_invalid_header_fields.enabled: true` to prevent HTTP header injection attacks. The ALB security group allows both 80 and 443 to support the redirect.
