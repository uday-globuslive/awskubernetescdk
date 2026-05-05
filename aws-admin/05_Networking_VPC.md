# Chapter 5: Networking — VPC, Route53, CloudFront & Connectivity
## Virtual Private Cloud, DNS, CDN, VPN, Direct Connect & Advanced Networking

---

## 5.1 VPC Overview

Amazon Virtual Private Cloud (VPC) lets you provision an isolated section of the AWS cloud where you launch resources in a virtual network that you define. You have full control over: IP address range, subnets, route tables, security groups, NACLs, and internet connectivity.

```
VPC Architecture:
┌─────────────────────────────────────────────────────────────────────┐
│                         AWS Account                                 │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │          VPC: 10.0.0.0/16   (us-east-1)                        │ │
│  │                                                                 │ │
│  │  ┌─────────────────────────┐  ┌────────────────────────────┐  │ │
│  │  │   AZ: us-east-1a        │  │   AZ: us-east-1b           │  │ │
│  │  │                         │  │                            │  │ │
│  │  │  Public Subnet          │  │  Public Subnet             │  │ │
│  │  │  10.0.1.0/24            │  │  10.0.2.0/24               │  │ │
│  │  │  [ALB, NAT GW]          │  │  [ALB, NAT GW]             │  │ │
│  │  │                         │  │                            │  │ │
│  │  │  Private Subnet         │  │  Private Subnet            │  │ │
│  │  │  10.0.11.0/24           │  │  10.0.12.0/24              │  │ │
│  │  │  [EC2, ECS tasks]       │  │  [EC2, ECS tasks]          │  │ │
│  │  │                         │  │                            │  │ │
│  │  │  DB Subnet              │  │  DB Subnet                 │  │ │
│  │  │  10.0.21.0/24           │  │  10.0.22.0/24              │  │ │
│  │  │  [RDS, ElastiCache]     │  │  [RDS, ElastiCache]        │  │ │
│  │  └─────────────────────────┘  └────────────────────────────┘  │ │
│  │                                                                 │ │
│  │  Internet Gateway  ←──── allows public subnet → internet       │ │
│  │  NAT Gateway       ←──── allows private subnet → internet      │ │
│  └────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

### Key VPC Concepts

| Concept | Description |
|---------|-------------|
| **CIDR Block** | IP address range for VPC (e.g., 10.0.0.0/16 = 65,536 IPs) |
| **Subnet** | Subdivision of VPC's CIDR in a single AZ |
| **Internet Gateway (IGW)** | Allows VPC resources to communicate with internet |
| **NAT Gateway** | Allows private subnet resources to initiate outbound internet |
| **Route Table** | Rules for routing traffic within VPC and externally |
| **Security Group** | Stateful firewall at the instance level |
| **NACL** | Stateless firewall at the subnet level |
| **VPC Peering** | Private connection between two VPCs |
| **Transit Gateway** | Hub-and-spoke for connecting many VPCs + on-prem |
| **VPC Endpoint** | Private connectivity to AWS services (no internet) |

---

## 5.2 Creating a Production VPC

### Complete VPC Setup (CLI)

```bash
# ── CREATE VPC ────────────────────────────────────────────────
VPC_ID=$(aws ec2 create-vpc \
  --cidr-block 10.0.0.0/16 \
  --tag-specifications "ResourceType=vpc,Tags=[{Key=Name,Value=prod-vpc},{Key=Environment,Value=prod}]" \
  --query "Vpc.VpcId" --output text)

# Enable DNS hostname resolution (required for some services)
aws ec2 modify-vpc-attribute --vpc-id $VPC_ID --enable-dns-hostnames
aws ec2 modify-vpc-attribute --vpc-id $VPC_ID --enable-dns-support

# ── INTERNET GATEWAY ──────────────────────────────────────────
IGW_ID=$(aws ec2 create-internet-gateway \
  --tag-specifications "ResourceType=internet-gateway,Tags=[{Key=Name,Value=prod-igw}]" \
  --query "InternetGateway.InternetGatewayId" --output text)

aws ec2 attach-internet-gateway \
  --internet-gateway-id $IGW_ID \
  --vpc-id $VPC_ID

# ── SUBNETS ───────────────────────────────────────────────────
# Public subnets (2 AZs)
PUB_SUB_1=$(aws ec2 create-subnet \
  --vpc-id $VPC_ID \
  --cidr-block 10.0.1.0/24 \
  --availability-zone us-east-1a \
  --tag-specifications "ResourceType=subnet,Tags=[{Key=Name,Value=public-1a},{Key=Type,Value=public}]" \
  --query "Subnet.SubnetId" --output text)

PUB_SUB_2=$(aws ec2 create-subnet \
  --vpc-id $VPC_ID \
  --cidr-block 10.0.2.0/24 \
  --availability-zone us-east-1b \
  --tag-specifications "ResourceType=subnet,Tags=[{Key=Name,Value=public-1b},{Key=Type,Value=public}]" \
  --query "Subnet.SubnetId" --output text)

# Auto-assign public IP in public subnets
aws ec2 modify-subnet-attribute \
  --subnet-id $PUB_SUB_1 --map-public-ip-on-launch
aws ec2 modify-subnet-attribute \
  --subnet-id $PUB_SUB_2 --map-public-ip-on-launch

# Private subnets (2 AZs)
PRIV_SUB_1=$(aws ec2 create-subnet \
  --vpc-id $VPC_ID \
  --cidr-block 10.0.11.0/24 \
  --availability-zone us-east-1a \
  --tag-specifications "ResourceType=subnet,Tags=[{Key=Name,Value=private-1a},{Key=Type,Value=private}]" \
  --query "Subnet.SubnetId" --output text)

PRIV_SUB_2=$(aws ec2 create-subnet \
  --vpc-id $VPC_ID \
  --cidr-block 10.0.12.0/24 \
  --availability-zone us-east-1b \
  --tag-specifications "ResourceType=subnet,Tags=[{Key=Name,Value=private-1b},{Key=Type,Value=private}]" \
  --query "Subnet.SubnetId" --output text)

# DB subnets (2 AZs)
DB_SUB_1=$(aws ec2 create-subnet \
  --vpc-id $VPC_ID \
  --cidr-block 10.0.21.0/24 \
  --availability-zone us-east-1a \
  --tag-specifications "ResourceType=subnet,Tags=[{Key=Name,Value=db-1a},{Key=Type,Value=database}]" \
  --query "Subnet.SubnetId" --output text)

DB_SUB_2=$(aws ec2 create-subnet \
  --vpc-id $VPC_ID \
  --cidr-block 10.0.22.0/24 \
  --availability-zone us-east-1b \
  --tag-specifications "ResourceType=subnet,Tags=[{Key=Name,Value=db-1b},{Key=Type,Value=database}]" \
  --query "Subnet.SubnetId" --output text)

# ── NAT GATEWAYS ──────────────────────────────────────────────
# Allocate Elastic IPs for NAT Gateways
EIP_1=$(aws ec2 allocate-address --domain vpc --query "AllocationId" --output text)
EIP_2=$(aws ec2 allocate-address --domain vpc --query "AllocationId" --output text)

# Create NAT Gateways in public subnets
NAT_1=$(aws ec2 create-nat-gateway \
  --subnet-id $PUB_SUB_1 \
  --allocation-id $EIP_1 \
  --tag-specifications "ResourceType=natgateway,Tags=[{Key=Name,Value=nat-1a}]" \
  --query "NatGateway.NatGatewayId" --output text)

NAT_2=$(aws ec2 create-nat-gateway \
  --subnet-id $PUB_SUB_2 \
  --allocation-id $EIP_2 \
  --tag-specifications "ResourceType=natgateway,Tags=[{Key=Name,Value=nat-1b}]" \
  --query "NatGateway.NatGatewayId" --output text)

# Wait for NAT Gateways to be available
aws ec2 wait nat-gateway-available --nat-gateway-ids $NAT_1 $NAT_2

# ── ROUTE TABLES ──────────────────────────────────────────────
# Public route table (route all internet traffic via IGW)
PUB_RT=$(aws ec2 create-route-table \
  --vpc-id $VPC_ID \
  --tag-specifications "ResourceType=route-table,Tags=[{Key=Name,Value=public-rt}]" \
  --query "RouteTable.RouteTableId" --output text)

aws ec2 create-route \
  --route-table-id $PUB_RT \
  --destination-cidr-block 0.0.0.0/0 \
  --gateway-id $IGW_ID

aws ec2 associate-route-table --route-table-id $PUB_RT --subnet-id $PUB_SUB_1
aws ec2 associate-route-table --route-table-id $PUB_RT --subnet-id $PUB_SUB_2

# Private route tables (per AZ, different NAT GW for HA)
PRIV_RT_1=$(aws ec2 create-route-table \
  --vpc-id $VPC_ID \
  --tag-specifications "ResourceType=route-table,Tags=[{Key=Name,Value=private-rt-1a}]" \
  --query "RouteTable.RouteTableId" --output text)

aws ec2 create-route \
  --route-table-id $PRIV_RT_1 \
  --destination-cidr-block 0.0.0.0/0 \
  --nat-gateway-id $NAT_1

aws ec2 associate-route-table --route-table-id $PRIV_RT_1 --subnet-id $PRIV_SUB_1

PRIV_RT_2=$(aws ec2 create-route-table \
  --vpc-id $VPC_ID \
  --tag-specifications "ResourceType=route-table,Tags=[{Key=Name,Value=private-rt-1b}]" \
  --query "RouteTable.RouteTableId" --output text)

aws ec2 create-route \
  --route-table-id $PRIV_RT_2 \
  --destination-cidr-block 0.0.0.0/0 \
  --nat-gateway-id $NAT_2

aws ec2 associate-route-table --route-table-id $PRIV_RT_2 --subnet-id $PRIV_SUB_2

echo "VPC setup complete: $VPC_ID"
```

---

## 5.3 Security Groups vs NACLs

### Security Groups (Stateful — instance level)

```
Security Group — Key Properties:
  ✓ Stateful: return traffic automatically allowed
  ✓ Evaluate ALL rules before deciding
  ✓ Attached to ENI (network interface) — not subnet
  ✓ Only ALLOW rules (no deny — anything not allowed is denied)
  ✓ Source/destination can be: IP range, security group ID, prefix list
```

```bash
# ── SECURITY GROUP DESIGN PATTERN ────────────────────────────
# Layer 1: ALB Security Group (internet-facing)
ALB_SG=$(aws ec2 create-security-group \
  --group-name alb-sg \
  --description "Internet-facing ALB" \
  --vpc-id $VPC_ID \
  --query "GroupId" --output text)

aws ec2 authorize-security-group-ingress --group-id $ALB_SG \
  --protocol tcp --port 443 --cidr 0.0.0.0/0
aws ec2 authorize-security-group-ingress --group-id $ALB_SG \
  --protocol tcp --port 80 --cidr 0.0.0.0/0

# Layer 2: App Security Group (ONLY accept from ALB SG)
APP_SG=$(aws ec2 create-security-group \
  --group-name app-sg \
  --description "Application servers" \
  --vpc-id $VPC_ID \
  --query "GroupId" --output text)

aws ec2 authorize-security-group-ingress --group-id $APP_SG \
  --protocol tcp --port 8080 --source-group $ALB_SG

# Layer 3: DB Security Group (ONLY accept from App SG)
DB_SG=$(aws ec2 create-security-group \
  --group-name db-sg \
  --description "Database servers" \
  --vpc-id $VPC_ID \
  --query "GroupId" --output text)

aws ec2 authorize-security-group-ingress --group-id $DB_SG \
  --protocol tcp --port 5432 --source-group $APP_SG

# Layer 4: Cache Security Group (ONLY accept from App SG)
CACHE_SG=$(aws ec2 create-security-group \
  --group-name cache-sg \
  --description "ElastiCache Redis" \
  --vpc-id $VPC_ID \
  --query "GroupId" --output text)

aws ec2 authorize-security-group-ingress --group-id $CACHE_SG \
  --protocol tcp --port 6379 --source-group $APP_SG
```

### NACLs (Stateless — subnet level)

```
NACL — Key Properties:
  ✓ Stateless: must create BOTH inbound and outbound rules for each connection
  ✓ Evaluated in order (lowest rule number first)
  ✓ First match wins (unlike SGs which evaluate all rules)
  ✓ Both ALLOW and DENY rules
  ✓ Attached to subnet
  ✓ Default NACL: allows all traffic (don't modify default — create new ones)

Ephemeral ports (return traffic): TCP 1024-65535 (Linux) / 49152-65535 (Windows)
Always allow ephemeral ports in NACL outbound rules!
```

```bash
# Create NACL for private subnets (allow app traffic, deny everything else)
NACL_ID=$(aws ec2 create-network-acl \
  --vpc-id $VPC_ID \
  --tag-specifications "ResourceType=network-acl,Tags=[{Key=Name,Value=private-nacl}]" \
  --query "NetworkAcl.NetworkAclId" --output text)

# Inbound rules
# Allow HTTPS from VPC CIDR
aws ec2 create-network-acl-entry \
  --network-acl-id $NACL_ID \
  --rule-number 100 \
  --protocol tcp \
  --rule-action allow \
  --ingress \
  --cidr-block 10.0.0.0/16 \
  --port-range From=443,To=443

# Allow return traffic (ephemeral ports)
aws ec2 create-network-acl-entry \
  --network-acl-id $NACL_ID \
  --rule-number 900 \
  --protocol tcp \
  --rule-action allow \
  --ingress \
  --cidr-block 0.0.0.0/0 \
  --port-range From=1024,To=65535

# Deny everything else
aws ec2 create-network-acl-entry \
  --network-acl-id $NACL_ID \
  --rule-number 32767 \
  --protocol -1 \
  --rule-action deny \
  --ingress \
  --cidr-block 0.0.0.0/0

# Associate with subnet
aws ec2 replace-network-acl-association \
  --association-id $(aws ec2 describe-network-acls \
    --filters "Name=vpc-id,Values=$VPC_ID" \
    --query "NetworkAcls[0].Associations[0].NetworkAclAssociationId" --output text) \
  --network-acl-id $NACL_ID
```

### Security Group vs NACL Comparison

```
┌──────────────────────────────────────────────────────────────────────┐
│            SECURITY GROUP vs NACL COMPARISON                         │
├────────────────────────┬──────────────────────┬──────────────────────┤
│ Feature                │ Security Group       │ NACL                 │
├────────────────────────┼──────────────────────┼──────────────────────┤
│ Level                  │ Instance/ENI         │ Subnet               │
│ Stateful/Stateless     │ Stateful             │ Stateless            │
│ Rule evaluation        │ All rules            │ In order (first wins)│
│ Allow/Deny             │ Allow only           │ Allow AND Deny       │
│ Default                │ Deny all             │ Allow all            │
│ Return traffic         │ Auto-allowed         │ Explicit rule needed │
│ Best for               │ Fine-grained control │ Subnet-level blocks  │
└────────────────────────┴──────────────────────┴──────────────────────┘

Use both together for defense in depth:
  NACL: Block known bad IPs, enforce subnet-level rules
  Security Group: Fine-grained per-instance rules
```

---

## 5.4 VPC Flow Logs

Capture information about IP traffic going to and from network interfaces in your VPC.

```bash
# Enable VPC Flow Logs to CloudWatch Logs
aws ec2 create-flow-logs \
  --resource-type VPC \
  --resource-ids $VPC_ID \
  --traffic-type ALL \
  --log-destination-type cloud-watch-logs \
  --log-group-name /vpc/flow-logs/prod-vpc \
  --deliver-logs-permission-arn arn:aws:iam::123:role/VPCFlowLogsRole \
  --log-format '${version} ${account-id} ${interface-id} ${srcaddr} ${dstaddr} ${srcport} ${dstport} ${protocol} ${packets} ${bytes} ${windowstart} ${windowend} ${action} ${log-status}'

# Enable Flow Logs to S3 (cheaper, use Athena to query)
aws ec2 create-flow-logs \
  --resource-type VPC \
  --resource-ids $VPC_ID \
  --traffic-type ALL \
  --log-destination-type s3 \
  --log-destination arn:aws:s3:::my-flow-logs-bucket/vpc-flows/

# Query flow logs with Athena
# Create table and run:
# SELECT srcaddr, dstaddr, dstport, action, protocol, SUM(bytes) as total_bytes
# FROM flow_logs
# WHERE action='REJECT' AND dstport=22
# GROUP BY 1,2,3,4,5
# ORDER BY total_bytes DESC
# LIMIT 20

# Flow log record format:
# version  account-id  interface-id  srcaddr  dstaddr  srcport  dstport  protocol  packets  bytes  start  end  action  log-status
# 2  123456789012  eni-0abc123  10.0.1.5  203.0.113.2  443  52340  6  10  5000  1620000000  1620000060  ACCEPT  OK
```

---

## 5.5 VPC Endpoints

VPC Endpoints allow private connectivity to AWS services without going through the internet:

```
Without VPC Endpoint:
EC2 (private subnet) → NAT Gateway → Internet → S3
  Costs: NAT Gateway data processing + transfer fees

With VPC Endpoint:
EC2 (private subnet) → VPC Endpoint → S3 (stays in AWS network)
  Costs: endpoint usage charge only (or free for Gateway endpoints)
```

### Gateway Endpoints (Free — S3 and DynamoDB only)

```bash
# Create S3 Gateway Endpoint
aws ec2 create-vpc-endpoint \
  --vpc-id $VPC_ID \
  --service-name com.amazonaws.us-east-1.s3 \
  --vpc-endpoint-type Gateway \
  --route-table-ids $PRIV_RT_1 $PRIV_RT_2 \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": "*",
      "Action": ["s3:GetObject", "s3:PutObject"],
      "Resource": ["arn:aws:s3:::my-bucket/*"]
    }]
  }'

# Create DynamoDB Gateway Endpoint
aws ec2 create-vpc-endpoint \
  --vpc-id $VPC_ID \
  --service-name com.amazonaws.us-east-1.dynamodb \
  --vpc-endpoint-type Gateway \
  --route-table-ids $PRIV_RT_1 $PRIV_RT_2
```

### Interface Endpoints (PrivateLink — most services)

```bash
# Create Secrets Manager Interface Endpoint (so Lambda can access secrets privately)
aws ec2 create-vpc-endpoint \
  --vpc-id $VPC_ID \
  --service-name com.amazonaws.us-east-1.secretsmanager \
  --vpc-endpoint-type Interface \
  --subnet-ids $PRIV_SUB_1 $PRIV_SUB_2 \
  --security-group-ids $ENDPOINT_SG \
  --private-dns-enabled

# Interface endpoints for common services
SERVICES=(
  "com.amazonaws.us-east-1.secretsmanager"
  "com.amazonaws.us-east-1.ssm"
  "com.amazonaws.us-east-1.ssmmessages"
  "com.amazonaws.us-east-1.ec2messages"
  "com.amazonaws.us-east-1.ecr.api"
  "com.amazonaws.us-east-1.ecr.dkr"
  "com.amazonaws.us-east-1.logs"
  "com.amazonaws.us-east-1.monitoring"
  "com.amazonaws.us-east-1.kms"
)

for SVC in "${SERVICES[@]}"; do
  aws ec2 create-vpc-endpoint \
    --vpc-id $VPC_ID \
    --service-name $SVC \
    --vpc-endpoint-type Interface \
    --subnet-ids $PRIV_SUB_1 $PRIV_SUB_2 \
    --security-group-ids $ENDPOINT_SG \
    --private-dns-enabled
done
```

---

## 5.6 VPC Peering

Connect two VPCs as if they are on the same network. Works across accounts and regions.

```
VPC Peering Limitations:
  - No transitive peering (A-B, B-C does NOT mean A can reach C via B)
  - Cannot overlap CIDR blocks
  - One peering connection per pair of VPCs
  - Use Transit Gateway for complex hub-and-spoke topology

VPC A (10.0.0.0/16) ←──────── Peer ────────► VPC B (10.1.0.0/16)
NOT: VPC A → VPC B → VPC C   (no transitive routing)
```

```bash
# Request peering connection (from requester VPC)
PEERING_ID=$(aws ec2 create-vpc-peering-connection \
  --vpc-id vpc-requester \
  --peer-vpc-id vpc-accepter \
  --peer-owner-id 987654321098 \        # Other account (or same account)
  --peer-region us-west-2 \             # Cross-region peering
  --query "VpcPeeringConnection.VpcPeeringConnectionId" --output text)

# Accept peering (from accepter VPC — in same or other account)
aws ec2 accept-vpc-peering-connection \
  --vpc-peering-connection-id $PEERING_ID \
  --region us-west-2  # If cross-region

# Update route tables in BOTH VPCs
# In VPC A: route to VPC B's CIDR via peering
aws ec2 create-route \
  --route-table-id $VPC_A_RT \
  --destination-cidr-block 10.1.0.0/16 \
  --vpc-peering-connection-id $PEERING_ID

# In VPC B: route to VPC A's CIDR via peering
aws ec2 create-route \
  --route-table-id $VPC_B_RT \
  --destination-cidr-block 10.0.0.0/16 \
  --vpc-peering-connection-id $PEERING_ID

# Security groups: allow traffic from peer VPC CIDR
aws ec2 authorize-security-group-ingress \
  --group-id sg-in-vpc-b \
  --protocol tcp \
  --port 5432 \
  --cidr 10.0.0.0/16  # Allow from VPC A
```

---

## 5.7 Transit Gateway

Transit Gateway is a network transit hub connecting multiple VPCs and on-premises networks.

```
Without Transit Gateway (VPC Peering mesh — N*(N-1)/2 peerings):
VPC-A ──── VPC-B
  │    ╲  ╱   │
  │     \/    │
  │     /\    │
  │    /  ╲   │
VPC-C ──── VPC-D
  (6 peering connections for 4 VPCs, 45 for 10 VPCs)

With Transit Gateway:
        VPC-A
          │
VPC-C ── TGW ── VPC-B
          │
        VPC-D
        On-Prem (via VPN/Direct Connect)
  (1 attachment per VPC/on-prem)
```

```bash
# Create Transit Gateway
TGW_ID=$(aws ec2 create-transit-gateway \
  --description "Central hub for all VPCs" \
  --options '{
    "AmazonSideAsn": 64512,
    "AutoAcceptSharedAttachments": "enable",
    "DefaultRouteTableAssociation": "enable",
    "DefaultRouteTablePropagation": "enable",
    "DnsSupport": "enable",
    "VpnEcmpSupport": "enable"
  }' \
  --tag-specifications "ResourceType=transit-gateway,Tags=[{Key=Name,Value=main-tgw}]" \
  --query "TransitGateway.TransitGatewayId" --output text)

# Attach VPCs to Transit Gateway
aws ec2 create-transit-gateway-vpc-attachment \
  --transit-gateway-id $TGW_ID \
  --vpc-id vpc-0abc123 \
  --subnet-ids subnet-0abc subnet-0def \
  --tag-specifications "ResourceType=transit-gateway-attachment,Tags=[{Key=Name,Value=prod-vpc-attach}]"

aws ec2 create-transit-gateway-vpc-attachment \
  --transit-gateway-id $TGW_ID \
  --vpc-id vpc-0def456 \
  --subnet-ids subnet-0ghi subnet-0jkl \
  --tag-specifications "ResourceType=transit-gateway-attachment,Tags=[{Key=Name,Value=dev-vpc-attach}]"

# Create Transit Gateway Route Table for network segmentation
DEV_RT=$(aws ec2 create-transit-gateway-route-table \
  --transit-gateway-id $TGW_ID \
  --tag-specifications "ResourceType=transit-gateway-route-table,Tags=[{Key=Name,Value=dev-rt}]" \
  --query "TransitGatewayRouteTable.TransitGatewayRouteTableId" --output text)

# Route propagation: allow dev VPC to send routes to dev RT
aws ec2 enable-transit-gateway-route-table-propagation \
  --transit-gateway-route-table-id $DEV_RT \
  --transit-gateway-attachment-id $DEV_ATTACH_ID

# Static route (send traffic to specific attachment)
aws ec2 create-transit-gateway-route \
  --transit-gateway-route-table-id $DEV_RT \
  --destination-cidr-block 0.0.0.0/0 \
  --transit-gateway-attachment-id $PROD_VPC_ATTACH  # Route to prod for internet
```

---

## 5.8 Route53 — DNS Service

Route53 is AWS's highly available DNS service, domain registrar, and health checker.

```
DNS Record Types:
┌────────────────────────────────────────────────────────────────┐
│ A      → IPv4 address (api.example.com → 203.0.113.1)         │
│ AAAA   → IPv6 address                                         │
│ CNAME  → Canonical name (www → api.example.com)               │
│         CANNOT use CNAME for zone apex (example.com)         │
│ ALIAS  → Route53 extension, like CNAME but CAN use for apex  │
│         Points to AWS resources (ALB, CloudFront, S3, etc.)  │
│ MX     → Mail exchange records                               │
│ TXT    → Text records (SPF, DKIM, domain verification)       │
│ NS     → Name server records                                 │
│ SOA    → Start of Authority                                  │
│ CAA    → Certificate Authority Authorization                 │
│ PTR    → Reverse DNS lookup (IP to hostname)                 │
│ SRV    → Service locator records                             │
└────────────────────────────────────────────────────────────────┘
```

### Hosted Zones & Records

```bash
# Create hosted zone
aws route53 create-hosted-zone \
  --name example.com \
  --caller-reference "$(date +%s)" \
  --hosted-zone-config Comment="Production DNS"

ZONE_ID=$(aws route53 list-hosted-zones \
  --query "HostedZones[?Name=='example.com.'].Id" \
  --output text | cut -d'/' -f3)

# Create A record (alias to ALB)
aws route53 change-resource-record-sets \
  --hosted-zone-id $ZONE_ID \
  --change-batch '{
    "Changes": [{
      "Action": "CREATE",
      "ResourceRecordSet": {
        "Name": "api.example.com",
        "Type": "A",
        "AliasTarget": {
          "HostedZoneId": "Z35SXDOTRQ7X7K",
          "DNSName": "my-alb-1234567890.us-east-1.elb.amazonaws.com",
          "EvaluateTargetHealth": true
        }
      }
    }]
  }'

# Create CNAME record
aws route53 change-resource-record-sets \
  --hosted-zone-id $ZONE_ID \
  --change-batch '{
    "Changes": [{
      "Action": "CREATE",
      "ResourceRecordSet": {
        "Name": "www.example.com",
        "Type": "CNAME",
        "TTL": 300,
        "ResourceRecords": [{"Value": "api.example.com"}]
      }
    }]
  }'

# Create TXT record (domain verification)
aws route53 change-resource-record-sets \
  --hosted-zone-id $ZONE_ID \
  --change-batch '{
    "Changes": [{
      "Action": "CREATE",
      "ResourceRecordSet": {
        "Name": "example.com",
        "Type": "TXT",
        "TTL": 300,
        "ResourceRecords": [
          {"Value": "\"v=spf1 include:amazonses.com ~all\""},
          {"Value": "\"google-site-verification=abcdef12345\""}
        ]
      }
    }]
  }'
```

### Route53 Routing Policies

```
┌──────────────────────────────────────────────────────────────────┐
│                   ROUTE53 ROUTING POLICIES                       │
├──────────────────────┬───────────────────────────────────────────┤
│ Policy               │ How it works                              │
├──────────────────────┼───────────────────────────────────────────┤
│ Simple               │ Single record. Multiple IPs → random      │
│ Weighted             │ Split traffic by weight (A=70%, B=30%)    │
│ Latency              │ Route to region with lowest latency       │
│ Failover             │ Primary/secondary; switch on health check │
│ Geolocation          │ Route by user's location (country)        │
│ Geoproximity         │ Route by distance, bias regions           │
│ Multi-Value Answer   │ Up to 8 healthy records returned          │
│ IP-Based             │ Route by source IP CIDR                   │
└──────────────────────┴───────────────────────────────────────────┘
```

```bash
# Weighted routing (A/B testing or gradual migration)
# 90% traffic to v1, 10% to v2
aws route53 change-resource-record-sets \
  --hosted-zone-id $ZONE_ID \
  --change-batch '{
    "Changes": [
      {
        "Action": "CREATE",
        "ResourceRecordSet": {
          "Name": "api.example.com",
          "Type": "A",
          "SetIdentifier": "v1",
          "Weight": 90,
          "AliasTarget": {
            "HostedZoneId": "Z35SXDOTRQ7X7K",
            "DNSName": "alb-v1.us-east-1.elb.amazonaws.com",
            "EvaluateTargetHealth": true
          }
        }
      },
      {
        "Action": "CREATE",
        "ResourceRecordSet": {
          "Name": "api.example.com",
          "Type": "A",
          "SetIdentifier": "v2",
          "Weight": 10,
          "AliasTarget": {
            "HostedZoneId": "Z35SXDOTRQ7X7K",
            "DNSName": "alb-v2.us-east-1.elb.amazonaws.com",
            "EvaluateTargetHealth": true
          }
        }
      }
    ]
  }'

# Failover routing (active-passive)
# Primary (us-east-1) + Failover (us-west-2)
aws route53 change-resource-record-sets \
  --hosted-zone-id $ZONE_ID \
  --change-batch '{
    "Changes": [
      {
        "Action": "CREATE",
        "ResourceRecordSet": {
          "Name": "api.example.com",
          "Type": "A",
          "SetIdentifier": "primary",
          "Failover": "PRIMARY",
          "HealthCheckId": "health-check-id",
          "AliasTarget": {
            "HostedZoneId": "Z35SXDOTRQ7X7K",
            "DNSName": "alb-us-east-1.elb.amazonaws.com",
            "EvaluateTargetHealth": true
          }
        }
      },
      {
        "Action": "CREATE",
        "ResourceRecordSet": {
          "Name": "api.example.com",
          "Type": "A",
          "SetIdentifier": "secondary",
          "Failover": "SECONDARY",
          "AliasTarget": {
            "HostedZoneId": "Z1H1FL5HABSF5",
            "DNSName": "alb-us-west-2.elb.amazonaws.com",
            "EvaluateTargetHealth": true
          }
        }
      }
    ]
  }'
```

### Route53 Health Checks

```bash
# HTTP health check
aws route53 create-health-check \
  --caller-reference "hc-$(date +%s)" \
  --health-check-config '{
    "IPAddress": "203.0.113.1",
    "Port": 443,
    "Type": "HTTPS",
    "ResourcePath": "/health",
    "FullyQualifiedDomainName": "api.example.com",
    "RequestInterval": 30,
    "FailureThreshold": 3,
    "MeasureLatency": true,
    "Regions": ["us-east-1", "eu-west-1", "ap-southeast-1"]
  }'

# Calculated health check (healthy if X of N checks pass)
aws route53 create-health-check \
  --caller-reference "calc-hc-$(date +%s)" \
  --health-check-config '{
    "Type": "CALCULATED",
    "ChildHealthChecks": ["hc-id-1", "hc-id-2"],
    "HealthThreshold": 1
  }'

# CloudWatch alarm-based health check
aws route53 create-health-check \
  --caller-reference "cw-hc-$(date +%s)" \
  --health-check-config '{
    "Type": "CLOUDWATCH_METRIC",
    "AlarmIdentifier": {
      "Region": "us-east-1",
      "Name": "5xx-error-rate-alarm"
    },
    "InsufficientDataHealthStatus": "Unhealthy"
  }'
```

### Private Hosted Zones

```bash
# Create private hosted zone (internal DNS, not public)
aws route53 create-hosted-zone \
  --name internal.company.com \
  --caller-reference "private-$(date +%s)" \
  --hosted-zone-config Comment="Internal services",PrivateZone=true \
  --vpc VPCRegion=us-east-1,VPCId=$VPC_ID

# Internal service discovery
# database.internal.company.com → RDS endpoint
# cache.internal.company.com → ElastiCache endpoint
# api.internal.company.com → internal ALB
```

---

## 5.9 CloudFront — CDN

Amazon CloudFront caches content at 400+ edge locations worldwide, reducing latency for global users.

```
CloudFront Concepts:
  Distribution: A CloudFront deployment (HTTPS endpoint: xxxxx.cloudfront.net)
  Origin: Source of content (S3, ALB, EC2, Lambda@Edge, custom HTTP)
  Cache Behavior: Rules for caching/routing based on path patterns
  Edge Location: Where content is cached (nearest to user)
  Origin Shield: Additional caching layer between edge and origin
  TTL: How long content stays in cache
```

```bash
# Create CloudFront distribution (S3 origin)
aws cloudfront create-distribution \
  --distribution-config '{
    "CallerReference": "'$(date +%s)'",
    "Comment": "Production CDN",
    "Enabled": true,
    "HttpVersion": "http2and3",
    "PriceClass": "PriceClass_All",
    "Origins": {
      "Quantity": 1,
      "Items": [{
        "Id": "s3-origin",
        "DomainName": "my-bucket.s3.us-east-1.amazonaws.com",
        "S3OriginConfig": {"OriginAccessIdentity": ""}
      }]
    },
    "DefaultCacheBehavior": {
      "TargetOriginId": "s3-origin",
      "ViewerProtocolPolicy": "redirect-to-https",
      "CachePolicyId": "658327ea-f89d-4fab-a63d-7e88639e58f6",
      "Compress": true,
      "AllowedMethods": {
        "Quantity": 2,
        "Items": ["GET", "HEAD"]
      }
    },
    "DefaultRootObject": "index.html",
    "Aliases": {"Quantity": 1, "Items": ["www.example.com"]},
    "ViewerCertificate": {
      "ACMCertificateArn": "arn:aws:acm:us-east-1:123:certificate/abc",
      "SSLSupportMethod": "sni-only",
      "MinimumProtocolVersion": "TLSv1.2_2021"
    }
  }'

# Create Origin Access Control (replaces OAI — more secure)
aws cloudfront create-origin-access-control \
  --origin-access-control-config '{
    "Name": "s3-oac",
    "OriginAccessControlOriginType": "s3",
    "SigningBehavior": "always",
    "SigningProtocol": "sigv4"
  }'

# Invalidate cache (forces re-fetch from origin)
aws cloudfront create-invalidation \
  --distribution-id EDFDVBD6EXAMPLE \
  --paths '{"Quantity": 2, "Items": ["/index.html", "/assets/*"]}'

# Invalidate everything (be careful — costs money if over 1,000/month)
aws cloudfront create-invalidation \
  --distribution-id EDFDVBD6EXAMPLE \
  --paths '{"Quantity": 1, "Items": ["/*"]}'
```

### CloudFront Cache Behaviors

```json
{
  "CacheBehaviors": {
    "Quantity": 3,
    "Items": [
      {
        "PathPattern": "/api/*",
        "TargetOriginId": "alb-origin",
        "ViewerProtocolPolicy": "https-only",
        "CachePolicyId": "4135ea2d-6df8-44a3-9df3-4b5a84be39ad",
        "OriginRequestPolicyId": "b689b0a8-53d0-40ab-baf2-68738e2966ac",
        "Compress": true,
        "AllowedMethods": {
          "Quantity": 7,
          "Items": ["GET","HEAD","OPTIONS","PUT","PATCH","POST","DELETE"]
        }
      },
      {
        "PathPattern": "/static/*",
        "TargetOriginId": "s3-origin",
        "ViewerProtocolPolicy": "redirect-to-https",
        "CachePolicyId": "658327ea-f89d-4fab-a63d-7e88639e58f6",
        "Compress": true,
        "AllowedMethods": {
          "Quantity": 2,
          "Items": ["GET", "HEAD"]
        }
      }
    ]
  }
}
```

---

## 5.10 Site-to-Site VPN

Connect your on-premises data center to AWS VPC over encrypted internet tunnels.

```bash
# Create Customer Gateway (your on-prem router)
CGW_ID=$(aws ec2 create-customer-gateway \
  --type ipsec.1 \
  --public-ip 203.0.113.1 \     # Your on-prem router's public IP
  --bgp-asn 65000 \
  --tag-specifications "ResourceType=customer-gateway,Tags=[{Key=Name,Value=onprem-cgw}]" \
  --query "CustomerGateway.CustomerGatewayId" --output text)

# Create Virtual Private Gateway (AWS side)
VGW_ID=$(aws ec2 create-vpn-gateway \
  --type ipsec.1 \
  --amazon-side-asn 64512 \
  --tag-specifications "ResourceType=vpn-gateway,Tags=[{Key=Name,Value=vpn-gateway}]" \
  --query "VpnGateway.VpnGatewayId" --output text)

# Attach VGW to VPC
aws ec2 attach-vpn-gateway \
  --vpn-gateway-id $VGW_ID \
  --vpc-id $VPC_ID

# Create VPN connection (two IPSec tunnels for redundancy)
VPN_ID=$(aws ec2 create-vpn-connection \
  --type ipsec.1 \
  --customer-gateway-id $CGW_ID \
  --vpn-gateway-id $VGW_ID \
  --options StaticRoutesOnly=false \
  --query "VpnConnection.VpnConnectionId" --output text)

# Download VPN configuration for your router
aws ec2 describe-vpn-connections \
  --vpn-connection-ids $VPN_ID \
  --query "VpnConnections[0].CustomerGatewayConfiguration"

# Enable route propagation to VGW in route tables
aws ec2 enable-vgw-route-propagation \
  --route-table-id $PRIV_RT_1 \
  --gateway-id $VGW_ID
```

---

## 5.11 AWS Direct Connect

Dedicated private network connection from your data center to AWS. More reliable and consistent than VPN over internet.

```
Direct Connect Architecture:
┌──────────────────────┐         ┌─────────────────────────────────┐
│  Your Data Center    │         │       AWS Region                 │
│                      │         │                                  │
│  ┌──────────────┐    │         │  ┌────────────────────────────┐ │
│  │ Your Router  │    │         │  │  Virtual Private Gateway   │ │
│  └──────┬───────┘    │         │  │  or Direct Connect GW      │ │
│         │             │         │  └────────────────────────────┘ │
└─────────┼─────────────┘         │             │                    │
          │                        │             │ Private VIF        │
          │ Dedicated fiber         │             │                    │
          │ (1Gbps or 10Gbps)       │             │                    │
          │                        │  ┌──────────┴───────────────┐   │
          └────────────────────────┤  │    VPC                   │   │
                                   │  └──────────────────────────┘   │
                                   └─────────────────────────────────┘

Speeds: 50Mbps, 100Mbps, 200Mbps, 300Mbps, 400Mbps, 500Mbps,
        1Gbps, 2Gbps, 5Gbps, 10Gbps, 25Gbps, 100Gbps

VIF Types:
  Private VIF: Connect to VPC resources
  Public VIF: Connect to AWS public services (S3, DynamoDB) without internet
  Transit VIF: Connect to Transit Gateway (access multiple VPCs)
```

```bash
# Request hosted connection (via partner)
# or dedicated connection (1Gbps, 10Gbps via AWS)

# Create Private Virtual Interface
aws directconnect create-private-virtual-interface \
  --connection-id dxcon-0abc123 \
  --new-private-virtual-interface '{
    "virtualInterfaceName": "prod-vif",
    "vlan": 100,
    "asn": 65000,
    "authKey": "bgp-md5-auth-key",
    "amazonAddress": "169.254.0.1/30",
    "customerAddress": "169.254.0.2/30",
    "addressFamily": "ipv4",
    "virtualGatewayId": "'$VGW_ID'"
  }'

# Direct Connect Gateway (access VPCs in different regions)
DCGW_ID=$(aws directconnect create-direct-connect-gateway \
  --direct-connect-gateway-name main-dcgw \
  --amazon-side-asn 64512 \
  --query "directConnectGateway.directConnectGatewayId" --output text)

# Attach Transit VIF to DX Gateway for multi-VPC access
aws directconnect create-transit-virtual-interface \
  --connection-id dxcon-0abc123 \
  --new-transit-virtual-interface '{
    "virtualInterfaceName": "transit-vif",
    "vlan": 200,
    "asn": 65000,
    "directConnectGatewayId": "'$DCGW_ID'"
  }'
```

---

## 5.12 Global Accelerator

Routes traffic to the nearest healthy AWS endpoint using AWS's global backbone network.

```bash
# Create accelerator
aws globalaccelerator create-accelerator \
  --name my-global-app \
  --ip-address-type IPV4 \
  --enabled \
  --tags Key=Name,Value=my-global-app

ACCELERATOR_ARN=$(aws globalaccelerator list-accelerators \
  --query "Accelerators[?Name=='my-global-app'].AcceleratorArn" --output text)

# Create listener (port 443 TCP)
LISTENER_ARN=$(aws globalaccelerator create-listener \
  --accelerator-arn $ACCELERATOR_ARN \
  --protocol TCP \
  --port-ranges '[{"FromPort": 443, "ToPort": 443}]' \
  --client-affinity SOURCE_IP \
  --query "Listener.ListenerArn" --output text)

# Create endpoint group (us-east-1)
aws globalaccelerator create-endpoint-group \
  --listener-arn $LISTENER_ARN \
  --endpoint-group-region us-east-1 \
  --traffic-dial-percentage 100 \
  --health-check-path /health \
  --health-check-interval-seconds 10 \
  --threshold-count 3 \
  --endpoint-configurations '[
    {
      "EndpointId": "arn:aws:elasticloadbalancing:us-east-1:123:loadbalancer/app/my-alb/abc",
      "Weight": 100,
      "ClientIPPreservationEnabled": true
    }
  ]'

# Add failover endpoint group (eu-west-1)
aws globalaccelerator create-endpoint-group \
  --listener-arn $LISTENER_ARN \
  --endpoint-group-region eu-west-1 \
  --traffic-dial-percentage 0 \  # 0% normally, only used for failover
  --endpoint-configurations '[{"EndpointId": "arn:aws:...", "Weight": 100}]'
```

---

## 5.13 Interview Q&A

**Q: What is the difference between a public subnet and a private subnet?**
A: Both are subnets in a VPC. A public subnet has a route to an Internet Gateway (IGW), so instances can have public IPs and be directly accessible from the internet. A private subnet has no route to the IGW — instances can only access the internet via a NAT Gateway in a public subnet, and are not directly accessible from the internet.

**Q: What is the difference between a Security Group and a NACL?**
A: Security groups operate at the instance/ENI level and are stateful (return traffic auto-allowed), evaluate all rules, and only allow rules. NACLs operate at the subnet level, are stateless (must explicitly allow return traffic), evaluate rules in order (first match wins), and support both allow and deny rules. Security groups are the primary defense; NACLs add subnet-level protection.

**Q: What is the difference between a NAT Gateway and an Internet Gateway?**
A: An Internet Gateway allows resources in a public subnet to have two-way communication with the internet (inbound + outbound, with public IP). A NAT Gateway allows resources in a private subnet to initiate outbound internet connections (for updates, API calls) but prevents the internet from initiating inbound connections to those resources.

**Q: What is VPC peering and what are its limitations?**
A: VPC peering creates a direct private connection between two VPCs using AWS's network backbone. Limitations: no transitive peering (A→B→C doesn't work), CIDRs cannot overlap, only one peering per VPC pair. For complex multi-VPC topologies, use Transit Gateway instead.

**Q: What is the difference between CloudFront and Global Accelerator?**
A: CloudFront is a CDN — it caches content (HTTP/HTTPS) at edge locations near users, reducing load on origin. Global Accelerator uses the AWS backbone to route TCP/UDP traffic to the nearest healthy endpoint without caching. Use CloudFront for cacheable content (static files, APIs with cacheable responses); use Global Accelerator for non-cacheable requests needing consistent low latency.

**Q: What is an Alias record in Route53?**
A: An Alias record is a Route53 extension similar to CNAME but can be used for zone apex (root domain like example.com) and points directly to AWS resources (ALB, CloudFront, S3 website, another Route53 record). Unlike CNAME, Alias queries are free and Route53 automatically updates the IP if the target changes.

**Q: When would you use Direct Connect over VPN?**
A: Direct Connect is preferred when: you need consistent, predictable latency and throughput (VPN over internet varies); you transfer large amounts of data regularly (Direct Connect is cheaper per GB); you need compliance requiring dedicated private connectivity; you have high bandwidth requirements (VPN typically limited to ~1.25Gbps, Direct Connect up to 100Gbps). VPN is cheaper to set up and works well for lower bandwidth needs.

**Q: What is a VPC endpoint and when would you use it?**
A: A VPC endpoint enables private connectivity from your VPC to AWS services without going through the internet, NAT gateway, or VPN. Use it to: reduce data transfer costs (NAT charges avoided), improve security (traffic stays on AWS network), and enable private subnets to access S3/DynamoDB/other services without internet access. Gateway endpoints (S3, DynamoDB) are free; Interface endpoints (most other services) have an hourly charge.
