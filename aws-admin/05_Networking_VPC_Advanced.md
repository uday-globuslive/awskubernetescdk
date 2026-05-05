# Chapter 5: Networking — VPC, Route 53, CloudFront & Advanced Networking

## AWS SysOps Administrator Exam Domain Coverage
- **Domain 5**: Networking and Content Delivery (18% of exam — highest weight!)
- Expect 8-12 questions on VPC, Route 53, CloudFront topics

---

## 5.1 VPC Fundamentals

A **Virtual Private Cloud (VPC)** is your own logically isolated section of the AWS cloud where you can launch AWS resources in a virtual network that you define.

### Default vs Custom VPC

| Feature | Default VPC | Custom VPC |
|---------|------------|-----------|
| Created by | AWS automatically | You create it |
| CIDR | 172.31.0.0/16 | You choose (e.g., 10.0.0.0/16) |
| Subnets | One public per AZ, auto-created | You create public/private |
| Internet access | All subnets have IGW and public IPs | Controlled by you |
| Use for | Dev/test only | Production workloads |

### VPC Core Components
```
┌─────────────────────── VPC (10.0.0.0/16) ──────────────────────────┐
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                    Availability Zone A                       │    │
│  │  ┌─────────────────────────┐ ┌─────────────────────────┐    │    │
│  │  │  PUBLIC SUBNET          │ │  PRIVATE SUBNET          │    │    │
│  │  │  10.0.1.0/24           │ │  10.0.11.0/24           │    │    │
│  │  │                        │ │                          │    │    │
│  │  │  EC2 (web)  NAT GW     │ │  EC2 (app)  RDS         │    │    │
│  │  └────────────────────────┘ └──────────────────────────┘    │    │
│  └─────────────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                    Availability Zone B                       │    │
│  │  ┌─────────────────────────┐ ┌─────────────────────────┐    │    │
│  │  │  PUBLIC SUBNET          │ │  PRIVATE SUBNET          │    │    │
│  │  │  10.0.2.0/24           │ │  10.0.12.0/24           │    │    │
│  │  └────────────────────────┘ └──────────────────────────┘    │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                      │
│  Internet Gateway (IGW)  ← makes it a public subnet when route exists│
│  VPC Router (implicit)   ← routes between subnets                   │
│  Route Tables            ← per-subnet routing rules                 │
│  NACLs                   ← subnet-level stateless firewall          │
│  Security Groups         ← instance-level stateful firewall         │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 5.2 Subnets & CIDR Planning

### CIDR Notation Refresher
```
10.0.0.0/16  → 65,534 usable IP addresses
10.0.0.0/24  → 251 usable (AWS reserves 5 per subnet)
10.0.0.0/28  → 11 usable (minimum subnet size)

AWS reserves 5 IPs per subnet:
  10.0.1.0   — Network address
  10.0.1.1   — VPC router
  10.0.1.2   — DNS server
  10.0.1.3   — Future use
  10.0.1.255 — Broadcast (not used in VPC, still reserved)
```

### Three-Tier Network Design
```
CIDR: 10.0.0.0/16

Public Subnets (Load Balancers, NAT Gateways, Bastion):
  AZ-a: 10.0.0.0/24   (251 IPs)
  AZ-b: 10.0.1.0/24   (251 IPs)
  AZ-c: 10.0.2.0/24   (251 IPs)

Private App Subnets (EC2, ECS, Lambda):
  AZ-a: 10.0.10.0/23  (507 IPs)
  AZ-b: 10.0.12.0/23  (507 IPs)
  AZ-c: 10.0.14.0/23  (507 IPs)

Private DB Subnets (RDS, ElastiCache):
  AZ-a: 10.0.20.0/24  (251 IPs)
  AZ-b: 10.0.21.0/24  (251 IPs)
  AZ-c: 10.0.22.0/24  (251 IPs)
```

```bash
# Create VPC
VPC_ID=$(aws ec2 create-vpc \
  --cidr-block 10.0.0.0/16 \
  --tag-specifications 'ResourceType=vpc,Tags=[{Key=Name,Value=production-vpc}]' \
  --query Vpc.VpcId --output text)

# Enable DNS hostnames
aws ec2 modify-vpc-attribute \
  --vpc-id $VPC_ID \
  --enable-dns-hostnames '{"Value":true}'

# Create subnets
aws ec2 create-subnet \
  --vpc-id $VPC_ID \
  --cidr-block 10.0.0.0/24 \
  --availability-zone us-east-1a \
  --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=public-a},{Key=Tier,Value=public}]'

# Enable auto-assign public IP on public subnets
aws ec2 modify-subnet-attribute \
  --subnet-id subnet-public-a \
  --map-public-ip-on-launch
```

---

## 5.3 Internet Gateway & NAT Gateway

### Internet Gateway (IGW)
- One IGW per VPC (highly available, no bandwidth limit)
- Required for internet traffic in public subnets
- Provides Network Address Translation for public IPs

```bash
# Create and attach IGW
IGW_ID=$(aws ec2 create-internet-gateway --query InternetGateway.InternetGatewayId --output text)
aws ec2 attach-internet-gateway --internet-gateway-id $IGW_ID --vpc-id $VPC_ID

# Update public subnet route table
aws ec2 create-route \
  --route-table-id rtb-public \
  --destination-cidr-block 0.0.0.0/0 \
  --gateway-id $IGW_ID
```

### NAT Gateway
Allows private subnet resources to access internet (outbound only).

```
Private EC2 ──► NAT Gateway ──► Internet Gateway ──► Internet
(10.0.10.x)   (10.0.0.x, EIP)   (VPC edge)
```

```bash
# Allocate EIP for NAT Gateway
EIP=$(aws ec2 allocate-address --domain vpc --query AllocationId --output text)

# Create NAT Gateway (must be in PUBLIC subnet)
NAT_GW=$(aws ec2 create-nat-gateway \
  --subnet-id subnet-public-a \
  --allocation-id $EIP \
  --tag-specifications 'ResourceType=natGateway,Tags=[{Key=Name,Value=nat-az-a}]' \
  --query NatGateway.NatGatewayId --output text)

# Wait for NAT GW to be available
aws ec2 wait nat-gateway-available --nat-gateway-ids $NAT_GW

# Add route in private subnet route table
aws ec2 create-route \
  --route-table-id rtb-private-a \
  --destination-cidr-block 0.0.0.0/0 \
  --nat-gateway-id $NAT_GW
```

**NAT Gateway cost consideration:**
- ~$45/month per AZ + data processing
- For DR/dev environments, use NAT Instance (t3.nano) to save cost
- For HA: one NAT GW per AZ (each private subnet routes to its AZ's NAT GW)

### NAT Gateway vs NAT Instance
| Feature | NAT Gateway | NAT Instance |
|---------|------------|-------------|
| Availability | Highly available (managed) | You manage HA |
| Bandwidth | Up to 100 Gbps | Depends on instance type |
| Cost | Higher | Lower (instance cost) |
| Security Groups | Cannot apply | Can apply |
| Maintenance | AWS managed | You patch/maintain |
| Use for | Production | Dev/cost optimization |

---

## 5.4 Security Groups vs Network ACLs

This is one of the most tested topics on SysOps!

### Security Groups (Stateful)
- Applied at the **ENI/instance level**
- **Stateful** — if traffic is allowed in, the response is automatically allowed out
- Only **Allow** rules (cannot create explicit Deny)
- Supports referencing other security groups (e.g., allow from ALB SG)

### Network ACLs (NACLs) (Stateless)
- Applied at the **subnet level**
- **Stateless** — must create inbound AND outbound rules explicitly
- Supports both **Allow and Deny** rules
- Rules evaluated in order (lowest number first); first match wins
- Default NACL: allows all traffic in/out

### Comparison Table

| Feature | Security Group | NACL |
|---------|---------------|------|
| Level | Instance (ENI) | Subnet |
| State | Stateful | Stateless |
| Rules | Allow only | Allow and Deny |
| Rule evaluation | All rules evaluated | Rules evaluated in order (lowest first) |
| Return traffic | Automatically allowed | Must explicitly allow |
| Default | Deny all inbound, allow all outbound | Allow all (default NACL) |

### NACL Best Practice Example
```
NACL for Web Tier (Public Subnet):

INBOUND:
Rule 100: ALLOW TCP 80 from 0.0.0.0/0     (HTTP)
Rule 110: ALLOW TCP 443 from 0.0.0.0/0    (HTTPS)
Rule 120: ALLOW TCP 1024-65535 from 0.0.0.0/0  (Ephemeral ports - responses)
Rule 200: DENY ALL from 192.168.0.0/16    (Block specific bad network)
Rule *:   DENY ALL                         (Implicit deny)

OUTBOUND:
Rule 100: ALLOW TCP 80 to 0.0.0.0/0       (HTTP outbound)
Rule 110: ALLOW TCP 443 to 0.0.0.0/0      (HTTPS outbound)
Rule 120: ALLOW TCP 1024-65535 to 0.0.0.0/0  (Ephemeral ports - responses to clients)
Rule 130: ALLOW TCP 5432 to 10.0.20.0/24  (DB access)
Rule *:   DENY ALL
```

```bash
# Create NACL
NACL=$(aws ec2 create-network-acl --vpc-id $VPC_ID --query NetworkAcl.NetworkAclId --output text)

# Add inbound rule
aws ec2 create-network-acl-entry \
  --network-acl-id $NACL \
  --rule-number 100 \
  --protocol tcp \
  --port-range From=443,To=443 \
  --ingress \
  --cidr-block 0.0.0.0/0 \
  --rule-action allow

# Associate NACL with subnet
aws ec2 replace-network-acl-association \
  --association-id aclassoc-xxx \
  --network-acl-id $NACL
```

---

## 5.5 VPC Flow Logs

VPC Flow Logs capture IP traffic information for VPC, subnet, or ENI.

```bash
# Enable VPC Flow Logs to CloudWatch Logs
aws ec2 create-flow-logs \
  --resource-type VPC \
  --resource-ids $VPC_ID \
  --traffic-type ALL \
  --log-destination-type cloud-watch-logs \
  --log-group-name /aws/vpc/flowlogs \
  --deliver-logs-permission-arn arn:aws:iam::123456789012:role/FlowLogsRole

# Enable to S3 (cheaper, use Athena for analysis)
aws ec2 create-flow-logs \
  --resource-type VPC \
  --resource-ids $VPC_ID \
  --traffic-type REJECT \
  --log-destination-type s3 \
  --log-destination arn:aws:s3:::my-flow-logs-bucket \
  --log-format '${version} ${account-id} ${interface-id} ${srcaddr} ${dstaddr} ${srcport} ${dstport} ${protocol} ${packets} ${bytes} ${start} ${end} ${action} ${log-status}'
```

**Flow Log Format:**
```
version account-id interface-id srcaddr dstaddr srcport dstport protocol packets bytes start end action log-status

Example:
2 123456789012 eni-abc123 10.0.1.5 10.0.2.3 54321 443 6 10 840 1620000000 1620000060 ACCEPT OK
```

**Analyzing Flow Logs with CloudWatch Insights:**
```bash
# Find rejected traffic (security analysis)
aws logs start-query \
  --log-group-name /aws/vpc/flowlogs \
  --start-time $(date -d '1 hour ago' +%s) \
  --end-time $(date +%s) \
  --query-string 'fields @timestamp, srcAddr, dstAddr, dstPort, action
    | filter action = "REJECT"
    | stats count(*) as rejectCount by srcAddr, dstPort
    | sort rejectCount desc
    | limit 20'
```

---

## 5.6 VPC Endpoints

VPC Endpoints allow private connection to AWS services **without internet or NAT Gateway**.

### Gateway Endpoints (Free)
For S3 and DynamoDB:
```bash
# Create S3 gateway endpoint
aws ec2 create-vpc-endpoint \
  --vpc-id $VPC_ID \
  --service-name com.amazonaws.us-east-1.s3 \
  --route-table-ids rtb-private-a rtb-private-b \
  --vpc-endpoint-type Gateway

# Add resource policy to restrict to specific bucket
aws ec2 modify-vpc-endpoint \
  --vpc-endpoint-id vpce-0123456789abcdef0 \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": "*",
      "Action": ["s3:GetObject","s3:PutObject"],
      "Resource": "arn:aws:s3:::my-allowed-bucket/*"
    }]
  }'
```

### Interface Endpoints (PrivateLink — paid)
For other AWS services (SSM, KMS, ECR, Secrets Manager, etc.):
```bash
# Create SSM interface endpoint (needed for Session Manager in private VPC)
aws ec2 create-vpc-endpoint \
  --vpc-id $VPC_ID \
  --vpc-endpoint-type Interface \
  --service-name com.amazonaws.us-east-1.ssm \
  --subnet-ids subnet-private-a subnet-private-b \
  --security-group-ids sg-endpoint-sg \
  --private-dns-enabled

# For full SSM Session Manager, need 3 endpoints:
# com.amazonaws.us-east-1.ssm
# com.amazonaws.us-east-1.ssmmessages
# com.amazonaws.us-east-1.ec2messages

# For ECR (private container image pulls):
# com.amazonaws.us-east-1.ecr.dkr
# com.amazonaws.us-east-1.ecr.api
# com.amazonaws.us-east-1.s3 (gateway endpoint for layer downloads)
```

**Cost Consideration:** Interface endpoints cost ~$7.30/month per endpoint per AZ. Enable only what you need.

---

## 5.7 VPC Peering

VPC Peering creates a private connection between two VPCs (same account, cross-account, or cross-region).

```
VPC A (10.0.0.0/16) ←──── VPC Peering ────► VPC B (10.1.0.0/16)
```

**Key Limitations:**
- **No transitive peering** — A↔B and B↔C does NOT allow A↔C
- No overlapping CIDRs
- No edge-to-edge routing (can't use VPN/IGW through peer)
- Max 125 peering connections per VPC

```bash
# Request peering connection
PEERING_ID=$(aws ec2 create-vpc-peering-connection \
  --vpc-id vpc-A \
  --peer-vpc-id vpc-B \
  --peer-region us-west-2 \
  --query VpcPeeringConnection.VpcPeeringConnectionId \
  --output text)

# Accept peering (from the peer VPC's account/region)
aws ec2 accept-vpc-peering-connection \
  --vpc-peering-connection-id $PEERING_ID

# Add routes in BOTH VPCs
aws ec2 create-route \
  --route-table-id rtb-vpc-a \
  --destination-cidr-block 10.1.0.0/16 \
  --vpc-peering-connection-id $PEERING_ID

aws ec2 create-route \
  --route-table-id rtb-vpc-b \
  --destination-cidr-block 10.0.0.0/16 \
  --vpc-peering-connection-id $PEERING_ID
```

---

## 5.8 AWS Transit Gateway

Transit Gateway is a **regional router** that connects VPCs and on-premises networks in a hub-and-spoke model — solving VPC Peering's transitive routing limitation.

```
                    ┌──────────────────┐
                    │  Transit Gateway │
                    │   (Hub)          │
                    └────────┬─────────┘
          ┌──────────────────┼──────────────────┐
          │                  │                  │
    ┌─────┴─────┐      ┌─────┴─────┐      ┌─────┴─────┐
    │  VPC A    │      │  VPC B    │      │  VPC C    │
    │ (10.0/16) │      │ (10.1/16) │      │ (10.2/16) │
    └───────────┘      └───────────┘      └───────────┘
          │
    ┌─────┴─────┐
    │  On-Prem  │
    │ (VPN/DX)  │
    └───────────┘
```

```bash
# Create Transit Gateway
TGW=$(aws ec2 create-transit-gateway \
  --description "Central Hub TGW" \
  --options '{
    "AmazonSideAsn": 64512,
    "AutoAcceptSharedAttachments": "disable",
    "DefaultRouteTableAssociation": "enable",
    "DefaultRouteTablePropagation": "enable",
    "VpnEcmpSupport": "enable",
    "DnsSupport": "enable"
  }' \
  --query TransitGateway.TransitGatewayId \
  --output text)

# Attach VPC to TGW
aws ec2 create-transit-gateway-vpc-attachment \
  --transit-gateway-id $TGW \
  --vpc-id vpc-A \
  --subnet-ids subnet-a1 subnet-a2

# Add routes pointing to TGW
aws ec2 create-route \
  --route-table-id rtb-private-a \
  --destination-cidr-block 10.1.0.0/16 \
  --transit-gateway-id $TGW
```

**Transit Gateway vs VPC Peering:**
| Feature | VPC Peering | Transit Gateway |
|---------|------------|----------------|
| Transitive routing | No | Yes |
| Max connections | 125/VPC | Thousands |
| Routing | Per-VPC routes | Centralized route tables |
| Cost | Free | ~$0.05/attachment-hour + data |
| On-premises | Separate VPN/DX per VPC | Single VPN/DX |
| Use for | Simple 2-3 VPC setups | Large multi-VPC environments |

---

## 5.9 AWS Direct Connect & VPN

### Site-to-Site VPN
- Encrypted IPsec tunnel over internet
- Two tunnels per connection (redundancy)
- Up to 1.25 Gbps per tunnel
- Takes minutes to set up

```bash
# Create VGW (Virtual Private Gateway) - attach to VPC
VGW=$(aws ec2 create-vpn-gateway \
  --type ipsec.1 \
  --amazon-side-asn 64512 \
  --query VpnGateway.VpnGatewayId \
  --output text)
aws ec2 attach-vpn-gateway --vpn-gateway-id $VGW --vpc-id $VPC_ID

# Create Customer Gateway (your on-prem device)
CGW=$(aws ec2 create-customer-gateway \
  --type ipsec.1 \
  --public-ip 203.0.113.100 \
  --bgp-asn 65000 \
  --query CustomerGateway.CustomerGatewayId \
  --output text)

# Create VPN connection
aws ec2 create-vpn-connection \
  --type ipsec.1 \
  --customer-gateway-id $CGW \
  --vpn-gateway-id $VGW \
  --options '{"StaticRoutesOnly":false}'
```

### AWS Direct Connect
- Dedicated private connection from on-premises to AWS (1/10/100 Gbps)
- More reliable, lower latency, higher bandwidth than VPN
- Takes weeks to provision

```
On-Premises         AWS Direct Connect      AWS
Data Center ──►   Location (Partner)  ──►  Region
(Customer Router)  (DX Port)               (VGW)
```

**Connection options:**
1. **Dedicated Connection**: 1/10/100 Gbps directly from AWS
2. **Hosted Connection**: Through partner (50 Mbps to 10 Gbps)

**DX + VPN for HA:**
```
Primary path:  On-Premises ──► Direct Connect ──► VPC
Backup path:   On-Premises ──► Site-to-Site VPN ──► VPC
```

---

## 5.10 Amazon Route 53

Route 53 is AWS's managed **DNS service** and **health check** service.

### Record Types
| Record | Purpose | Example |
|--------|---------|---------|
| **A** | Domain → IPv4 | `example.com → 1.2.3.4` |
| **AAAA** | Domain → IPv6 | `example.com → 2001:db8::1` |
| **CNAME** | Alias to another hostname | `www.example.com → example.com` |
| **Alias** | AWS-specific; points to AWS resources | `example.com → my-alb.amazonaws.com` |
| **MX** | Mail exchange | `example.com → mail.example.com (priority 10)` |
| **TXT** | Text records | SPF, DKIM, domain verification |
| **NS** | Name server records | Delegate subdomain |
| **SOA** | Start of authority | Zone metadata |

**CNAME vs Alias:**
- CNAME cannot be at **zone apex** (root domain) — e.g., `example.com` 
- Alias records CAN be at zone apex and support routing to: ALB, NLB, CloudFront, S3, Elastic Beanstalk, API Gateway
- Alias records are free; CNAME queries are charged

```bash
# Create hosted zone
aws route53 create-hosted-zone \
  --name example.com \
  --caller-reference $(date +%s)

# Create A record
aws route53 change-resource-record-sets \
  --hosted-zone-id Z123456789 \
  --change-batch '{
    "Changes": [{
      "Action": "CREATE",
      "ResourceRecordSet": {
        "Name": "api.example.com",
        "Type": "A",
        "AliasTarget": {
          "HostedZoneId": "Z35SXDOTRQ7X7K",
          "DNSName": "my-alb-123456.us-east-1.elb.amazonaws.com",
          "EvaluateTargetHealth": true
        }
      }
    }]
  }'
```

### Routing Policies

```
┌──────────────────────────────────────────────────────────────┐
│                    ROUTE 53 ROUTING POLICIES                  │
│                                                              │
│  SIMPLE        — one resource, no health checks              │
│                  example.com → 1.2.3.4                       │
│                                                              │
│  WEIGHTED      — split traffic by weight (A/B testing)       │
│                  90% → server A, 10% → server B             │
│                                                              │
│  LATENCY       — route to lowest latency region              │
│                  US users → us-east-1, EU users → eu-west-1 │
│                                                              │
│  FAILOVER      — primary/secondary with health checks        │
│                  primary DOWN? → route to secondary          │
│                                                              │
│  GEOLOCATION   — by user's country/continent                 │
│                  US users → US servers (compliance)          │
│                                                              │
│  GEOPROXIMITY  — by location, with bias (Traffic Flow)       │
│                  Route more/less traffic based on region size │
│                                                              │
│  MULTIVALUE    — return up to 8 healthy IPs                  │
│                  Client-side load balancing with health checks│
│                                                              │
│  IP-BASED      — by IP prefix/CIDR (fine-grained routing)   │
└──────────────────────────────────────────────────────────────┘
```

### Failover Routing with Health Checks
```bash
# Create health check
HEALTH_CHECK=$(aws route53 create-health-check \
  --caller-reference $(date +%s) \
  --health-check-config '{
    "Type": "HTTPS",
    "FullyQualifiedDomainName": "app.example.com",
    "Port": 443,
    "ResourcePath": "/health",
    "RequestInterval": 30,
    "FailureThreshold": 3,
    "EnableSNI": true
  }' \
  --query HealthCheck.Id --output text)

# Create primary record (with health check)
aws route53 change-resource-record-sets \
  --hosted-zone-id Z123456789 \
  --change-batch '{
    "Changes": [{
      "Action": "CREATE",
      "ResourceRecordSet": {
        "Name": "app.example.com",
        "Type": "A",
        "SetIdentifier": "primary",
        "Failover": "PRIMARY",
        "HealthCheckId": "'$HEALTH_CHECK'",
        "AliasTarget": {
          "HostedZoneId": "Z35SXDOTRQ7X7K",
          "DNSName": "primary-alb.us-east-1.elb.amazonaws.com",
          "EvaluateTargetHealth": true
        }
      }
    }]
  }'
```

---

## 5.11 Amazon CloudFront

CloudFront is a **Content Delivery Network (CDN)** that delivers content via edge locations worldwide.

### How CloudFront Works
```
User (London) → CloudFront Edge Location (London) → Check cache
                                                      │
                                          Cache HIT: serve from edge
                                                      │
                                          Cache MISS: fetch from Origin
                                                       ↓
                                                Origin (us-east-1 S3/ALB)
```

### CloudFront Distribution Setup
```bash
# Create CloudFront distribution for S3 static website
aws cloudfront create-distribution \
  --distribution-config '{
    "CallerReference": "'$(date +%s)'",
    "Origins": {
      "Quantity": 1,
      "Items": [{
        "Id": "S3Origin",
        "DomainName": "my-website.s3.us-east-1.amazonaws.com",
        "S3OriginConfig": {"OriginAccessIdentity": ""},
        "OriginAccessControlId": "oac-id"
      }]
    },
    "DefaultCacheBehavior": {
      "TargetOriginId": "S3Origin",
      "ViewerProtocolPolicy": "redirect-to-https",
      "CachePolicyId": "658327ea-f89d-4fab-a63d-7e88639e58f6",
      "ResponseHeadersPolicyId": "67f7725c-6f97-4210-82d7-5512b31e9d03",
      "Compress": true
    },
    "ViewerCertificate": {
      "AcmCertificateArn": "arn:aws:acm:us-east-1:123456789012:certificate/xxx",
      "SslSupportMethod": "sni-only",
      "MinimumProtocolVersion": "TLSv1.2_2021"
    },
    "PriceClass": "PriceClass_100",
    "Enabled": true,
    "HttpVersion": "http2and3",
    "DefaultRootObject": "index.html",
    "Aliases": {"Quantity": 1, "Items": ["www.example.com"]}
  }'
```

### Cache Control
```bash
# Invalidate specific files (after deployment)
aws cloudfront create-invalidation \
  --distribution-id E1234567890 \
  --paths "/index.html" "/app.js" "/css/*"

# Invalidate all (use sparingly — charged after 1000 paths/month)
aws cloudfront create-invalidation \
  --distribution-id E1234567890 \
  --paths "/*"
```

### Origin Access Control (OAC) — Secure S3 Origin
```json
// S3 Bucket Policy for CloudFront OAC (modern approach, replaces OAI)
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "cloudfront.amazonaws.com"
      },
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::my-website-bucket/*",
      "Condition": {
        "StringEquals": {
          "AWS:SourceArn": "arn:aws:cloudfront::123456789012:distribution/E1234567890"
        }
      }
    }
  ]
}
```

### CloudFront Security Features
```
┌──────────────────── CloudFront Security ────────────────────┐
│                                                              │
│  WAF (Web Application Firewall)                              │
│  ├── Block SQL injection, XSS attacks                       │
│  ├── Rate limiting (DDoS protection)                        │
│  └── Geo-blocking                                           │
│                                                              │
│  AWS Shield Standard (free) — basic DDoS protection         │
│  AWS Shield Advanced ($3,000/mo) — DDoS cost protection     │
│                                                              │
│  Signed URLs / Signed Cookies                               │
│  └── Restrict content to authenticated users                │
│                                                              │
│  Field-Level Encryption                                     │
│  └── Encrypt specific POST fields (credit cards, SSNs)     │
│                                                              │
│  Geo Restriction                                            │
│  └── Allow/block by country                                 │
└──────────────────────────────────────────────────────────────┘
```

---

## 5.12 AWS Global Accelerator

Global Accelerator routes traffic through **AWS's private global backbone** rather than the public internet.

```
User (Tokyo) → AWS Edge (Tokyo) → AWS Global Network → us-east-1 ALB
              (instead of: Tokyo → Internet → us-east-1)
```

**CloudFront vs Global Accelerator:**
| Feature | CloudFront | Global Accelerator |
|---------|-----------|-------------------|
| Protocol | HTTP/HTTPS | TCP/UDP/HTTP |
| Caching | Yes | No |
| Use case | Static content, websites | APIs, gaming, IoT, non-HTTP |
| IP | Dynamic | Static (2 Anycast IPs) |
| Health checks | Via origin | Built-in multi-region failover |

---

## 5.13 Real-World Project: Secure Multi-Tier VPC

### CloudFormation Template
```yaml
AWSTemplateFormatVersion: '2010-09-09'
Description: Production-grade 3-tier VPC

Parameters:
  Environment:
    Type: String
    Default: production

Resources:
  VPC:
    Type: AWS::EC2::VPC
    Properties:
      CidrBlock: 10.0.0.0/16
      EnableDnsHostnames: true
      EnableDnsSupport: true
      Tags:
        - Key: Name
          Value: !Sub ${Environment}-vpc

  # Public Subnets
  PublicSubnetA:
    Type: AWS::EC2::Subnet
    Properties:
      VpcId: !Ref VPC
      CidrBlock: 10.0.0.0/24
      AvailabilityZone: !Select [0, !GetAZs '']
      MapPublicIpOnLaunch: true
      Tags:
        - Key: Name
          Value: !Sub ${Environment}-public-a
        - Key: kubernetes.io/role/elb
          Value: '1'

  # Private App Subnets
  PrivateSubnetA:
    Type: AWS::EC2::Subnet
    Properties:
      VpcId: !Ref VPC
      CidrBlock: 10.0.10.0/23
      AvailabilityZone: !Select [0, !GetAZs '']
      Tags:
        - Key: Name
          Value: !Sub ${Environment}-private-app-a

  # Internet Gateway
  IGW:
    Type: AWS::EC2::InternetGateway
  IGWAttachment:
    Type: AWS::EC2::VPCGatewayAttachment
    Properties:
      VpcId: !Ref VPC
      InternetGatewayId: !Ref IGW

  # NAT Gateway
  NatEIP:
    Type: AWS::EC2::EIP
    DependsOn: IGWAttachment
    Properties:
      Domain: vpc

  NatGatewayA:
    Type: AWS::EC2::NatGateway
    Properties:
      SubnetId: !Ref PublicSubnetA
      AllocationId: !GetAtt NatEIP.AllocationId
      Tags:
        - Key: Name
          Value: !Sub ${Environment}-nat-a

  # Route Tables
  PublicRouteTable:
    Type: AWS::EC2::RouteTable
    Properties:
      VpcId: !Ref VPC

  PublicRoute:
    Type: AWS::EC2::Route
    DependsOn: IGWAttachment
    Properties:
      RouteTableId: !Ref PublicRouteTable
      DestinationCidrBlock: 0.0.0.0/0
      GatewayId: !Ref IGW

  PrivateRouteTableA:
    Type: AWS::EC2::RouteTable
    Properties:
      VpcId: !Ref VPC

  PrivateRouteA:
    Type: AWS::EC2::Route
    Properties:
      RouteTableId: !Ref PrivateRouteTableA
      DestinationCidrBlock: 0.0.0.0/0
      NatGatewayId: !Ref NatGatewayA

  # S3 Gateway Endpoint (free)
  S3GatewayEndpoint:
    Type: AWS::EC2::VPCEndpoint
    Properties:
      VpcId: !Ref VPC
      ServiceName: !Sub com.amazonaws.${AWS::Region}.s3
      VpcEndpointType: Gateway
      RouteTableIds:
        - !Ref PrivateRouteTableA

  # VPC Flow Logs
  FlowLogGroup:
    Type: AWS::Logs::LogGroup
    Properties:
      LogGroupName: !Sub /aws/vpc/${Environment}-flowlogs
      RetentionInDays: 90

  FlowLogs:
    Type: AWS::EC2::FlowLog
    Properties:
      ResourceId: !Ref VPC
      ResourceType: VPC
      TrafficType: ALL
      LogDestinationType: cloud-watch-logs
      LogGroupName: !Ref FlowLogGroup
      DeliverLogsPermissionArn: !GetAtt FlowLogsRole.Arn
```

---

## 5.14 Practice Questions (SysOps Exam Level)

**Q1:** A web application in a private subnet cannot connect to the internet to download software updates. The public subnet has a NAT Gateway. What is likely the issue?

**A:** The **private subnet's route table** is missing a route to the NAT Gateway. Add:
- Destination: `0.0.0.0/0` 
- Target: The NAT Gateway ID

Also verify: NAT Gateway is in **public** subnet (not private), and the public subnet route table has `0.0.0.0/0 → IGW`.

---

**Q2:** You need to block a specific IP range (200.0.0.0/8) from accessing your web servers. Security groups cannot create deny rules. What do you use?

**A:** **Network ACL (NACL)** — supports explicit Deny rules at the subnet level. Add a NACL inbound rule with lowest rule number to `DENY 200.0.0.0/8`. Must also maintain stateless outbound rules for ephemeral ports.

---

**Q3:** Your application needs to access S3 from EC2 instances in a private subnet without internet or NAT charges. What is the solution?

**A:** Create an **S3 VPC Gateway Endpoint** — free, routes S3 traffic through the VPC private network. Update the private subnet route table to route `com.amazonaws.region.s3` to the gateway endpoint. No data transfer charges.

---

**Q4:** You have 5 VPCs that need to communicate with each other and with on-premises. VPC Peering requires 10 peering connections. What is the better solution?

**A:** **AWS Transit Gateway** — acts as a central hub. 5 attachments connect all 5 VPCs plus on-premises VPN. Transitive routing is handled by TGW route tables. Much more manageable than 10 peering connections (full mesh).

---

**Q5:** Route 53 should route users to the nearest healthy endpoint. What routing policy do you use?

**A:** **Latency-based routing** combined with **health checks**. Latency routing sends users to the region with lowest latency. With health checks enabled, if that region is unhealthy, Route 53 fails over to the next-lowest-latency healthy region.

For stricter geographic routing (compliance), use **Geolocation routing**.

---

## Key Networking Terms for Exam

| Term | Definition |
|------|-----------|
| VPC | Virtual Private Cloud — isolated network in AWS |
| CIDR | IP address range notation (e.g., 10.0.0.0/16) |
| Subnet | Segment of VPC in a specific AZ |
| IGW | Internet Gateway — enables internet access |
| NAT GW | Allows private instances outbound internet (no inbound) |
| Security Group | Stateful instance-level firewall (Allow only) |
| NACL | Stateless subnet-level firewall (Allow + Deny) |
| Route Table | Rules directing network traffic |
| VPC Endpoint | Private connection to AWS services (no internet) |
| VPC Peering | Private connection between 2 VPCs (no transitive) |
| Transit Gateway | Hub connecting many VPCs and on-premises |
| Direct Connect | Dedicated private line to AWS |
| VPN | Encrypted IPsec tunnel over internet |
| Route 53 | AWS DNS service + health checks |
| CloudFront | CDN — global content delivery via edge locations |
| ALB | Application Load Balancer — Layer 7 routing |
| NLB | Network Load Balancer — Layer 4, extreme performance |
