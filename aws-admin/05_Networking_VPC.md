# Chapter 5: Networking — VPC, Subnets, Route Tables & Connectivity
## Building Secure, Isolated Networks on AWS

---

## 5.1 VPC Overview

**VPC (Virtual Private Cloud)** is your own private, isolated section of the AWS cloud. Think of it as your own data centre inside AWS.

```
┌──────────────────────────────────────────────────────────────┐
│  AWS REGION (us-east-1)                                      │
│                                                              │
│  ┌─────────────────── VPC (10.0.0.0/16) ─────────────────┐  │
│  │                                                         │  │
│  │  ┌─────── AZ-1a ────────┐  ┌─────── AZ-1b ────────┐   │  │
│  │  │                      │  │                      │   │  │
│  │  │ ┌──────────────────┐ │  │ ┌──────────────────┐ │   │  │
│  │  │ │ Public Subnet    │ │  │ │ Public Subnet    │ │   │  │
│  │  │ │ 10.0.1.0/24      │ │  │ │ 10.0.2.0/24      │ │   │  │
│  │  │ │ (ALB, Bastion)   │ │  │ │ (ALB)            │ │   │  │
│  │  │ └──────────────────┘ │  │ └──────────────────┘ │   │  │
│  │  │                      │  │                      │   │  │
│  │  │ ┌──────────────────┐ │  │ ┌──────────────────┐ │   │  │
│  │  │ │ Private Subnet   │ │  │ │ Private Subnet   │ │   │  │
│  │  │ │ 10.0.11.0/24     │ │  │ │ 10.0.12.0/24     │ │   │  │
│  │  │ │ (App servers)    │ │  │ │ (App servers)    │ │   │  │
│  │  │ └──────────────────┘ │  │ └──────────────────┘ │   │  │
│  │  │                      │  │                      │   │  │
│  │  │ ┌──────────────────┐ │  │ ┌──────────────────┐ │   │  │
│  │  │ │ DB Subnet        │ │  │ │ DB Subnet        │ │   │  │
│  │  │ │ 10.0.21.0/24     │ │  │ │ 10.0.22.0/24     │ │   │  │
│  │  │ │ (RDS, DynamoDB)  │ │  │ │ (RDS replica)    │ │   │  │
│  │  │ └──────────────────┘ │  │ └──────────────────┘ │   │  │
│  │  └──────────────────────┘  └──────────────────────┘   │  │
│  └─────────────────────────────────────────────────────── ┘  │
└──────────────────────────────────────────────────────────────┘
```

---

## 5.2 CIDR Blocks

CIDR (Classless Inter-Domain Routing) notation defines IP ranges.

```
10.0.0.0/16  → 65,536 IPs   (typical VPC size)
10.0.1.0/24  → 256 IPs      (typical subnet size)
10.0.1.0/28  → 16 IPs       (small subnet)

AWS reserves 5 IPs in every subnet:
10.0.1.0   → Network address
10.0.1.1   → AWS VPC router
10.0.1.2   → AWS DNS
10.0.1.3   → Reserved for future use
10.0.1.255 → Broadcast address

So /24 gives you 256 - 5 = 251 usable IPs

Recommended VPC sizing:
/16  → dev environment (lots of room)
/20  → prod environment (4096 IPs)
/24  → per subnet
```

---

## 5.3 Creating a VPC from Scratch

```bash
# 1. Create VPC
VPC_ID=$(aws ec2 create-vpc \
  --cidr-block 10.0.0.0/16 \
  --tag-specifications 'ResourceType=vpc,Tags=[{Key=Name,Value=my-vpc}]' \
  --query Vpc.VpcId --output text)

# Enable DNS hostnames (needed for EFS, RDS endpoints, etc.)
aws ec2 modify-vpc-attribute \
  --vpc-id $VPC_ID \
  --enable-dns-hostnames

# 2. Create subnets
# Public subnet AZ-1a
aws ec2 create-subnet \
  --vpc-id $VPC_ID \
  --cidr-block 10.0.1.0/24 \
  --availability-zone us-east-1a \
  --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=public-1a}]'

# Private subnet AZ-1a
aws ec2 create-subnet \
  --vpc-id $VPC_ID \
  --cidr-block 10.0.11.0/24 \
  --availability-zone us-east-1a \
  --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=private-1a}]'

# DB subnet AZ-1a
aws ec2 create-subnet \
  --vpc-id $VPC_ID \
  --cidr-block 10.0.21.0/24 \
  --availability-zone us-east-1a \
  --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=db-1a}]'

# Repeat for AZ-1b (10.0.2.0/24, 10.0.12.0/24, 10.0.22.0/24)

# 3. Internet Gateway (allows public subnets to reach internet)
IGW_ID=$(aws ec2 create-internet-gateway \
  --query InternetGateway.InternetGatewayId --output text)
aws ec2 attach-internet-gateway \
  --internet-gateway-id $IGW_ID \
  --vpc-id $VPC_ID

# 4. Route Tables

# Public route table — route 0.0.0.0/0 to IGW
PUBLIC_RT=$(aws ec2 create-route-table \
  --vpc-id $VPC_ID \
  --query RouteTable.RouteTableId --output text)

aws ec2 create-route \
  --route-table-id $PUBLIC_RT \
  --destination-cidr-block 0.0.0.0/0 \
  --gateway-id $IGW_ID

aws ec2 associate-route-table \
  --route-table-id $PUBLIC_RT \
  --subnet-id <public-subnet-1a-id>

# Enable auto-assign public IP on public subnets
aws ec2 modify-subnet-attribute \
  --subnet-id <public-subnet-1a-id> \
  --map-public-ip-on-launch

# 5. NAT Gateway (allows private subnets to reach internet for updates, etc.)
# Create Elastic IP first
EIP=$(aws ec2 allocate-address --domain vpc --query AllocationId --output text)

NAT_ID=$(aws ec2 create-nat-gateway \
  --subnet-id <public-subnet-1a-id> \
  --allocation-id $EIP \
  --query NatGateway.NatGatewayId --output text)

# Private route table — route 0.0.0.0/0 to NAT Gateway
PRIVATE_RT=$(aws ec2 create-route-table \
  --vpc-id $VPC_ID \
  --query RouteTable.RouteTableId --output text)

aws ec2 create-route \
  --route-table-id $PRIVATE_RT \
  --destination-cidr-block 0.0.0.0/0 \
  --nat-gateway-id $NAT_ID

aws ec2 associate-route-table \
  --route-table-id $PRIVATE_RT \
  --subnet-id <private-subnet-1a-id>
```

---

## 5.4 Internet Gateway vs NAT Gateway

```
┌──────────────────────────────────────────────────────────┐
│         INTERNET GATEWAY vs NAT GATEWAY                  │
│                                                          │
│  Internet Gateway                                        │
│  ─────────────────                                       │
│  • Allows two-way traffic: IN and OUT                    │
│  • Used by PUBLIC subnets                                │
│  • One per VPC, free                                     │
│  • Instances need public IPs                             │
│                                                          │
│  NAT Gateway                                             │
│  ────────────                                            │
│  • Allows outbound only: OUT but NOT IN                  │
│  • Used by PRIVATE subnets                               │
│  • Lives in PUBLIC subnet, paid (~$0.045/hr + data)     │
│  • Instances stay private (no public IP)                 │
│  • Use case: private EC2 needs to download updates       │
│                                                          │
│  Flow for private EC2 to reach internet:                 │
│  Private EC2 → Private Subnet → Route Table →           │
│  NAT Gateway (public subnet) → IGW → Internet           │
└──────────────────────────────────────────────────────────┘
```

---

## 5.5 Security Groups vs NACLs

```
┌────────────────────────────────────────────────────────────────┐
│              SECURITY GROUPS vs NETWORK ACLs                   │
├────────────────────────┬───────────────────────────────────────┤
│ Security Group         │ NACL (Network ACL)                    │
├────────────────────────┼───────────────────────────────────────┤
│ Instance level         │ Subnet level                          │
│ Stateful               │ Stateless                             │
│ Allow rules only       │ Allow AND Deny rules                  │
│ All rules evaluated    │ Rules processed in order (low # first)│
│ Applies to instances   │ Applies to all traffic in/out subnet  │
│ No rule number         │ Rule number 100, 200, 300...          │
└────────────────────────┴───────────────────────────────────────┘

When to use NACLs:
• Block a specific IP address at network level (DDoS mitigation)
• Add extra layer of security in regulated environments
• Block specific port ranges (e.g., block all outbound 25/SMTP)

For most applications: Security Groups are sufficient.
```

```bash
# Create NACL
NACL_ID=$(aws ec2 create-network-acl \
  --vpc-id $VPC_ID \
  --query NetworkAcl.NetworkAclId --output text)

# Allow inbound HTTP (rule 100)
aws ec2 create-network-acl-entry \
  --network-acl-id $NACL_ID \
  --rule-number 100 \
  --protocol tcp \
  --rule-action allow \
  --ingress \
  --cidr-block 0.0.0.0/0 \
  --port-range From=80,To=80

# Deny specific IP (rule 50 — evaluated before 100)
aws ec2 create-network-acl-entry \
  --network-acl-id $NACL_ID \
  --rule-number 50 \
  --protocol -1 \
  --rule-action deny \
  --ingress \
  --cidr-block 203.0.113.100/32
```

---

## 5.6 VPC Peering

Connect two VPCs privately (same or different accounts/regions). Traffic never leaves AWS.

```
VPC A (10.0.0.0/16)  ←──── Peering ────►  VPC B (172.16.0.0/16)
                        (no overlapping CIDR!)
```

```bash
# Request peering (from VPC A)
PEERING_ID=$(aws ec2 create-vpc-peering-connection \
  --vpc-id vpc-A-id \
  --peer-vpc-id vpc-B-id \
  --peer-region eu-west-1 \
  --query VpcPeeringConnection.VpcPeeringConnectionId --output text)

# Accept peering (from VPC B — different terminal/profile)
aws ec2 accept-vpc-peering-connection \
  --vpc-peering-connection-id $PEERING_ID \
  --region eu-west-1

# Add routes in BOTH VPCs
aws ec2 create-route \
  --route-table-id <vpc-a-route-table> \
  --destination-cidr-block 172.16.0.0/16 \
  --vpc-peering-connection-id $PEERING_ID
```

**VPC Peering limitations:**
- Not transitive: A↔B and B↔C does NOT mean A↔C
- No overlapping CIDR blocks
- For many VPCs, use Transit Gateway instead

---

## 5.7 VPC Endpoints — Private Access to AWS Services

Access S3, DynamoDB, and other services without leaving the VPC (no NAT needed).

```
Without VPC Endpoint:                With VPC Endpoint:
Private EC2 → NAT → IGW → S3        Private EC2 → VPC Endpoint → S3
(public internet path, costs money)  (stays in AWS backbone, free for S3)
```

```bash
# Gateway Endpoint (S3 and DynamoDB — FREE)
aws ec2 create-vpc-endpoint \
  --vpc-id $VPC_ID \
  --service-name com.amazonaws.us-east-1.s3 \
  --route-table-ids <private-route-table-id>

# Interface Endpoint (other services — costs ~$0.01/hr/AZ)
aws ec2 create-vpc-endpoint \
  --vpc-id $VPC_ID \
  --vpc-endpoint-type Interface \
  --service-name com.amazonaws.us-east-1.secretsmanager \
  --subnet-ids <private-subnet-ids> \
  --security-group-ids <sg-id> \
  --private-dns-enabled
```

---

## 5.8 AWS Transit Gateway

Hub-and-spoke model for connecting many VPCs and on-premises networks.

```
Without Transit Gateway:          With Transit Gateway:
VPC-A ─── VPC-B                  VPC-A ─┐
VPC-A ─── VPC-C                  VPC-B ─┤
VPC-B ─── VPC-C     →            VPC-C ─┤── Transit Gateway ── On-premises
VPC-A ─── On-prem                VPC-D ─┤
VPC-B ─── On-prem                VPC-E ─┘

N*(N-1)/2 peerings           Just one TGW attachment per VPC
(complex mesh)               (simple hub and spoke)
```

---

## 5.9 Route53 — DNS Service

Route53 handles domain registration and DNS routing.

```bash
# List hosted zones
aws route53 list-hosted-zones

# Create A record pointing domain to ALB
aws route53 change-resource-record-sets \
  --hosted-zone-id ZONE_ID \
  --change-batch '{
    "Changes": [{
      "Action": "UPSERT",
      "ResourceRecordSet": {
        "Name": "api.myapp.com",
        "Type": "A",
        "AliasTarget": {
          "HostedZoneId": "ALB-HOSTED-ZONE-ID",
          "DNSName": "my-alb-123456.us-east-1.elb.amazonaws.com",
          "EvaluateTargetHealth": true
        }
      }
    }]
  }'
```

### Route53 Routing Policies

```
┌──────────────────────────────────────────────────────────┐
│             ROUTE53 ROUTING POLICIES                     │
├────────────────────┬─────────────────────────────────────┤
│ Simple             │ One record → one resource            │
│                    │ No health checks                     │
├────────────────────┼─────────────────────────────────────┤
│ Weighted           │ Send 90% to v1, 10% to v2            │
│                    │ Canary / blue-green deployments       │
├────────────────────┼─────────────────────────────────────┤
│ Latency-based      │ Route to lowest-latency region       │
│                    │ For multi-region apps                │
├────────────────────┼─────────────────────────────────────┤
│ Failover           │ Primary → Secondary on health fail   │
│                    │ Active-Passive DR                    │
├────────────────────┼─────────────────────────────────────┤
│ Geolocation        │ Route by user's country/continent    │
│                    │ Compliance: EU users → EU region     │
├────────────────────┼─────────────────────────────────────┤
│ Geoproximity       │ Route by geographic distance +       │
│                    │ bias (Traffic Flow required)         │
├────────────────────┼─────────────────────────────────────┤
│ Multi-value        │ Return multiple IPs, health-checked  │
│                    │ Client-side load balancing           │
└────────────────────┴─────────────────────────────────────┘
```

---

## 5.10 CloudFront — CDN

CloudFront caches content at 400+ edge locations globally.

```
User (Tokyo) ─► CloudFront Edge (Tokyo) ─► (if miss) ─► Origin (us-east-1)
                      │
                      └── Returns cached response (ms latency)
                          instead of going to origin (100ms+)

Origins: S3 bucket, ALB, EC2, API Gateway, custom HTTP server
```

```bash
# Create CloudFront distribution in front of S3 static website
aws cloudfront create-distribution \
  --distribution-config '{
    "CallerReference": "unique-string-123",
    "Origins": {
      "Quantity": 1,
      "Items": [{
        "Id": "S3Origin",
        "DomainName": "my-bucket.s3.amazonaws.com",
        "S3OriginConfig": {"OriginAccessIdentity": ""}
      }]
    },
    "DefaultCacheBehavior": {
      "TargetOriginId": "S3Origin",
      "ViewerProtocolPolicy": "redirect-to-https",
      "CachePolicyId": "658327ea-f89d-4fab-a63d-7e88639e58f6",
      "Compress": true
    },
    "Enabled": true,
    "PriceClass": "PriceClass_100",
    "ViewerCertificate": {
      "ACMCertificateArn": "arn:aws:acm:us-east-1:...:certificate/...",
      "SSLSupportMethod": "sni-only",
      "MinimumProtocolVersion": "TLSv1.2_2021"
    },
    "Aliases": {"Quantity": 1, "Items": ["www.myapp.com"]},
    "Comment": "My app CDN",
    "DefaultRootObject": "index.html"
  }'

# Invalidate cache (force CloudFront to refetch from origin)
aws cloudfront create-invalidation \
  --distribution-id E1ABCDEF123 \
  --paths "/*"
```

---

## 5.11 VPN & Direct Connect

```
┌──────────────────────────────────────────────────────────┐
│          CONNECTING ON-PREMISES TO AWS                   │
├────────────────────────┬─────────────────────────────────┤
│ Site-to-Site VPN       │ Encrypted tunnel over internet   │
│                        │ Quick to set up                  │
│                        │ ~1.25 Gbps per tunnel            │
│                        │ Cost: ~$0.05/hr + data           │
├────────────────────────┼─────────────────────────────────┤
│ AWS Direct Connect     │ Dedicated physical connection    │
│                        │ 1 Gbps or 10 Gbps               │
│                        │ Lower latency, consistent speed  │
│                        │ Takes weeks to provision         │
│                        │ Used for enterprise/compliance   │
└────────────────────────┴─────────────────────────────────┘
```

---

## 5.12 Interview Questions

**Q: What is the difference between a public and private subnet?**
> A public subnet has a route in its route table to an Internet Gateway (0.0.0.0/0 → IGW). Instances in public subnets can have public IPs and be directly reachable from the internet. A private subnet has no route to the IGW — instances cannot be reached from the internet. They can still reach the internet for outbound traffic (updates, API calls) through a NAT Gateway in a public subnet.

**Q: Why would you use a NAT Gateway vs a NAT Instance?**
> NAT Gateway is a managed AWS service — highly available, scalable (up to 100 Gbps), no patching needed, costs ~$0.045/hr. A NAT Instance is an EC2 instance you manage yourself — cheaper but you handle availability, patching, and scaling. AWS recommends NAT Gateway for production; NAT Instance is only worth it for very cost-sensitive dev environments.

**Q: What is VPC peering and what are its limitations?**
> VPC peering connects two VPCs privately without traversing the public internet. Limitations: (1) Not transitive — if A↔B and B↔C, A cannot reach C through B. (2) No overlapping CIDR blocks allowed. (3) For many VPCs, Transit Gateway is more practical. (4) One peering connection per pair of VPCs.

**Q: What is the difference between Route53 latency routing and geolocation routing?**
> Latency routing measures the actual network latency between the user and each AWS region and routes to whichever is lowest — purely performance-based. Geolocation routing routes based on the user's physical location (country or continent) regardless of latency — used for content customisation, data residency compliance, or serving different content to different regions.
