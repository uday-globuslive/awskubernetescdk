
content = r"""# Chapter 1: AWS Fundamentals & Global Infrastructure
## (Explained From Absolute Zero — Simple, Clear, Deep)

---

## 1.1 What is AWS? — The Lemonade Stand Analogy

Imagine you want to sell lemonade. Before you can sell even one glass, you need:
- A **table** to run your stand on (this is like a server — a computer that runs your app)
- A **refrigerator** to store lemons (this is storage — where your files and data live)
- A **cash register** to track sales (this is a database — organized records)
- A **building** to operate from (this is a data center — the building that houses all the computers)

**Now here is the problem with owning all of this yourself:**
- Buying a table, fridge, register, and building costs THOUSANDS of dollars upfront
- You need to maintain everything yourself (fix when broken, replace when old)
- If one day your lemonade goes viral and a thousand customers show up, you only have one table — you cannot serve them all
- If there is a power outage in your building, your whole stand shuts down

**What if you could just RENT everything?**
- Pay $0.01/hour for a table when you use it, turn it off when you sleep
- Need 100 tables for a rush? Get them instantly, pay only for the time you used them
- Building maintenance, power, cooling — all handled by the owner
- Your building has backup power — if one generator fails, another kicks in

**That is EXACTLY what AWS (Amazon Web Services) does.**

AWS is owned by Amazon. They have built **enormous buildings full of computers** all around the world. These buildings are called **data centers**. AWS lets you:
- **Rent** their computers (EC2 instances)
- **Rent** their storage (S3 buckets)
- **Rent** their databases (RDS, DynamoDB)
- **Use** hundreds of other pre-built services
- Pay **only for what you use**, by the second or hour
- **Scale up in seconds** if you suddenly need more

### Before AWS vs After AWS

| Challenge | Old Way (Buy Your Own Servers) | AWS Way (Rent from AWS) |
|-----------|-------------------------------|------------------------|
| Getting started | Order servers → wait 4-6 weeks → set up in data center | Click a button → ready in 60 seconds |
| Upfront cost | $10,000 to $500,000 for hardware | $0 upfront |
| Ongoing cost | Pay 100% even when idle at night | Pay only when running |
| Traffic spike | Can only handle what you planned for | Auto-scale to 10x traffic in minutes |
| Server failure | Your website goes down until you fix it | AWS moves you to another server automatically |
| Going global | Build data centers in each country (millions of dollars) | Tick a checkbox to deploy in Tokyo, London, Sydney |
| Security of building | Hire guards, install cameras, manage badge access | AWS handles all physical security 24/7/365 |

### The Concept of "The Cloud"

People use the word "cloud" to mean: **computers you access over the internet that you do not own or maintain yourself**. The cloud is just other people's computers that you rent.

AWS is the biggest and most popular cloud provider. Microsoft Azure and Google Cloud Platform (GCP) are the other major ones.

### Why SysOps Engineers Need to Know AWS Deeply

As an AWS SysOps Administrator, your job is to:
- **Deploy** applications on AWS infrastructure
- **Monitor** those applications (are they healthy? slow? down?)
- **Secure** them (lock doors, encrypt data)
- **Automate** operations (let computers do repetitive work)
- **Optimize costs** (pay only for what you need)
- **Ensure reliability** (keep apps running even when things break)

This certification proves you can do all of that.

---

## 1.2 AWS Global Infrastructure — Where AWS Lives in the World

### The Three Layers of AWS Physical Infrastructure

AWS's physical infrastructure is organized in three layers, from largest to smallest:

```
LAYER 1: REGIONS (33+ around the world)
  A geographic area — like a city or country
  Example: "Northern Virginia, USA" = us-east-1

LAYER 2: AVAILABILITY ZONES (3-6 per Region)
  Individual buildings (data centers) within the Region
  Example: us-east-1a, us-east-1b, us-east-1c

LAYER 3: EDGE LOCATIONS (450+ worldwide)
  Small distribution points for fast content delivery
  In cities that do not have full Regions yet
```

Think of it as a **grocery store chain**:
- **Region** = A city where the chain operates (Seattle, Chicago, Miami)
- **Availability Zone** = Individual store locations within that city (downtown, north side, south side)
- **Edge Location** = Small convenience store kiosks throughout the city for quick access

### AWS Regions — The Big Geographic Zones

An AWS **Region** is a distinct geographic area in the world where AWS operates multiple data centers.

**What makes a Region special:**
- Each Region is **completely independent** from all other Regions
- Data you put in a Region **stays in that Region** — it does not automatically go anywhere else
- AWS currently operates **33+ Regions** and keeps adding more
- Not all AWS services are available in all Regions (new services launch in us-east-1 first)

```
World map of major AWS Regions (simplified):

North America:
  us-east-1      → Northern Virginia (oldest, most services, often cheapest)
  us-east-2      → Ohio
  us-west-1      → Northern California
  us-west-2      → Oregon
  ca-central-1   → Canada (Montreal)

South America:
  sa-east-1      → São Paulo, Brazil

Europe:
  eu-west-1      → Ireland (most popular EU Region)
  eu-west-2      → London
  eu-central-1   → Frankfurt, Germany
  eu-south-1     → Milan
  eu-north-1     → Stockholm

Asia Pacific:
  ap-northeast-1 → Tokyo, Japan
  ap-northeast-2 → Seoul, South Korea
  ap-southeast-1 → Singapore
  ap-southeast-2 → Sydney, Australia
  ap-south-1     → Mumbai, India

Middle East / Africa:
  me-south-1     → Bahrain
  af-south-1     → Cape Town, South Africa
```

**How to choose the right Region for your application:**

Ask yourself these 4 questions, in this order:

**Question 1: Are there any legal requirements about where data must be stored?**
- GDPR (European Union law): Data about EU citizens may need to stay in the EU
- Some governments require their data to stay within their country's borders
- Healthcare companies (HIPAA) may have specific requirements
- If yes → your Region is already decided by law

**Question 2: Where are most of your users?**
- If your users are in Japan → choose ap-northeast-1 (Tokyo) for low latency
- If your users are in the US East → choose us-east-1 (Virginia)
- Closer Region = faster website response = happier users

**Question 3: Does the AWS service you need exist in your preferred Region?**
- New services launch in us-east-1 first, then slowly roll out to other Regions
- Check the AWS Regional Services list before committing to a Region
- If a service you need is not available in your preferred Region, choose the nearest one that has it

**Question 4: What are the costs in different Regions?**
- The same EC2 instance type can cost 10-20% more in some Regions
- us-east-1 is generally the cheapest
- eu-west-1 (Ireland) is generally cheaper than eu-central-1 (Frankfurt)
- Optimize cost only after satisfying questions 1-3

**Exam tip: Most questions that ask "which Region should you use" have compliance or latency as the key factor, not cost.**

### Availability Zones — The Individual Buildings

Each AWS Region contains **2 to 6 Availability Zones**. Most Regions have 3.

**What is an Availability Zone exactly?**
- One or more **physical data center buildings**
- Located in different parts of the Region (different neighborhoods, different flood plains)
- Each has **completely independent infrastructure**: its own power supply, its own cooling systems, its own network connections
- Connected to other AZs in the same Region by **private fiber optic cables** that are extremely fast (less than 1 millisecond round-trip time)

**Why are they physically separated?**

If all your servers were in one building and that building caught fire, everything is gone. But if your servers are split across buildings that are miles apart:
- Fire at Building A → Buildings B and C keep running
- Flood at Building B → Buildings A and C keep running
- Power outage at Building C → Buildings A and B keep running

**The AZ naming convention:**
```
Region:  us-east-1 (Northern Virginia)
AZs:     us-east-1a
         us-east-1b
         us-east-1c
         us-east-1d  (some Regions have 4-6 AZs)
         us-east-1e
         us-east-1f
```

**Important nuance:** The letter suffixes (a, b, c) are randomized per AWS account. Your "us-east-1a" and your coworker's "us-east-1a" might be different physical data centers. AWS does this for load distribution.

**The golden rule of SysOps architecture:**

```
WRONG (Single AZ — fragile):
    AZ-a: [Web Servers] [Database] [Cache]
    AZ-b: (empty)
    AZ-c: (empty)
    
    → AZ-a has an outage → TOTAL DOWNTIME

RIGHT (Multi-AZ — resilient):
    AZ-a: [Web Server 1] [DB Primary]  [Cache Primary]
    AZ-b: [Web Server 2] [DB Standby]  [Cache Replica]
    AZ-c: [Web Server 3] [DB Read Rep] [Nothing or more cache]
    
    → AZ-a has an outage → AZ-b and AZ-c serve all traffic, users notice nothing
```

**Key exam rule: Any question asking about high availability or fault tolerance expects you to deploy across MULTIPLE AZs.**

### Edge Locations — Fast Delivery Points

Even with 33 Regions, there are many cities in the world far from any Region. A user in Lagos, Nigeria (no AWS Region nearby) accessing your website in Ireland (eu-west-1) would experience high latency.

**Edge Locations** solve this problem by caching (storing a copy of) your content in cities close to users.

```
Without Edge Locations (CDN):
  User in Sydney → (internet) → Server in Virginia → (internet) → Sydney
  Latency: ~180ms per request
  Every time the user loads an image: 180ms wait

With CloudFront Edge Locations:
  First request:
    User in Sydney → Sydney Edge Location (cache miss) 
    → Virginia server (fetch origin content)
    → Store in Sydney Edge Location cache
  All future requests:
    User in Sydney → Sydney Edge Location (cache HIT)
    Latency: ~5ms (serving from Sydney, not Virginia!)
```

**What gets cached at Edge Locations:**
- Static website files (HTML, CSS, JavaScript, images, fonts)
- Videos and media
- Software downloads
- API responses (if you configure caching)

**Edge Location services:**
| Service | Purpose |
|---------|---------|
| CloudFront | CDN — delivers your web content fast to users worldwide |
| Route 53 | DNS — resolves domain names like amazon.com to IP addresses |
| AWS Shield | DDoS protection — stops attack traffic at the edge |
| AWS WAF | Web Application Firewall — filters malicious requests before they reach your servers |

**Numbers to remember for exam:**
- 450+ Edge Locations and Regional Edge Caches globally
- CloudFront serves from the nearest Edge Location
- Free Tier: 1TB data transfer via CloudFront per month for 12 months

### Special Infrastructure Types

**Local Zones:**
- Mini-versions of AWS Regions placed in specific metro areas (Los Angeles, Chicago, Dallas, etc.)
- For workloads that need **single-digit millisecond latency** to a specific city
- Use case: Video game servers, real-time video editing, live streaming, financial trading

**AWS Wavelength:**
- AWS compute embedded directly inside telecom providers' 5G networks
- Your application runs inside the 5G network itself
- Latency: under 10ms for mobile users
- Use case: Real-time mobile gaming, autonomous vehicle data processing, AR/VR

**AWS Outposts:**
- AWS ships a physical rack of servers to YOUR data center
- You get all AWS services running in your own building
- Use case: Strict data residency laws, manufacturing plants with local compute needs, ultra-low latency to on-premises systems

---

## 1.3 Shared Responsibility Model — Who Does What

This is one of the most heavily tested concepts in the exam. Get this wrong and you get exam questions wrong. Understand it deeply.

### The Core Idea

AWS provides infrastructure. You use that infrastructure to build your application. Security responsibilities are split between AWS and you. The split depends on **how much of the infrastructure you manage yourself**.

### The Hotel Room Analogy (Very Important)

Imagine staying at a hotel:

**Hotel's Responsibilities (= AWS):**
- Building the hotel structure, walls, roof (physical data center)
- Installing locks on your room door (the lock mechanism exists and works)
- Providing security guards at the hotel entrance (physical security)
- Maintaining the electrical and plumbing systems (power and networking)
- Replacing a broken door lock if it fails (hardware replacement)

**Your Responsibilities as a Guest (= You, the AWS Customer):**
- **Actually locking your door** when you leave (configuring security groups, enabling encryption)
- **Who you give your room key to** (IAM — who has access to your AWS resources)
- **What you bring into the room** (your data, your application code)
- **Not leaving valuables in plain sight** (not storing passwords in plain text, encrypting sensitive data)
- **Following hotel rules** (compliance with applicable laws)

The hotel (AWS) cannot control whether you lock your door. They gave you a door with a working lock. Using it is your job.

### The Full Model

```
┌────────────────────────────────────────────────────────────────┐
│               CUSTOMER — Security IN the Cloud                 │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  Your DATA — you must protect it, encrypt it, back it up      │
│                                                                │
│  Your APPLICATIONS — you write secure code, patch your apps    │
│                                                                │
│  OPERATING SYSTEM (on EC2) — patching Linux/Windows is YOURS  │
│                                                                │
│  NETWORK CONFIGURATION — Security Groups, NACLs (your rules)  │
│                                                                │
│  IAM — who can access your account, what they can do          │
│                                                                │
│  ENCRYPTION — you must enable and manage encryption           │
│                                                                │
├────────────────────────────────────────────────────────────────┤
│                  AWS — Security OF the Cloud                   │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  PHYSICAL DATA CENTERS — guards, biometric access, cameras    │
│                                                                │
│  HARDWARE — servers, networking equipment, storage drives      │
│                                                                │
│  HYPERVISOR — the software layer that creates virtual machines │
│                                                                │
│  GLOBAL INFRASTRUCTURE — Regions, AZs, Edge Locations         │
│                                                                │
│  MANAGED SERVICES infrastructure (Lambda runtime, RDS engine)  │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

### How Responsibility Shifts with Service Type

This is critical: **the more "managed" a service is, the more AWS takes on and the less you have to do.**

```
SPECTRUM OF RESPONSIBILITY:

                     YOU MANAGE MORE
                          ↑
EC2 (IaaS — Infrastructure as a Service)
  AWS gives you: a virtual machine, hardware, hypervisor
  YOU manage: OS, OS patches, runtime (Python, Java), app code, data, 
              security groups, network config, encryption
              
              ↓ MORE MANAGED
              
Elastic Beanstalk / ECS (PaaS — Platform as a Service)
  AWS manages: hardware, OS, OS patches, runtime
  YOU manage: app code, app configuration, data, encryption

              ↓ EVEN MORE MANAGED
              
Lambda / DynamoDB / SQS / S3 (Serverless / SaaS-like)
  AWS manages: hardware, OS, patches, runtime, scaling
  YOU manage: your code/queries/data, IAM permissions, encryption config

                          ↓
                     AWS MANAGES MORE
```

### Concrete Exam Examples

**Scenario 1:** You launch an EC2 instance with Amazon Linux 2. A critical kernel vulnerability (CVE) is published.
- **Who patches it?** → **YOU** — the OS is inside your virtual machine. AWS only manages the hypervisor underneath.
- How to fix: AWS Systems Manager Patch Manager, or manually `sudo yum update -y`

**Scenario 2:** An RDS (managed database) instance is running MySQL 8.0. A security patch is released for MySQL 8.0.
- **Who patches the MySQL engine?** → **AWS** — for managed services, AWS patches the database engine
- **Who is responsible for the DATA stored in the database?** → **YOU** — always

**Scenario 3:** Someone gains access to your AWS root account because you had no MFA enabled.
- **Whose fault?** → **YOURS** — enabling MFA on your account is YOUR responsibility

**Scenario 4:** An AWS data center's power supply fails and hardware is damaged.
- **Whose fault?** → **AWS** — physical infrastructure is their responsibility
- **What should you have done?** → Deploy in multiple AZs so a single AZ failure does not bring you down

**Quick reference for exam questions:**

| Item | Responsible Party |
|------|------------------|
| Physical data center security | AWS |
| Hardware failure and replacement | AWS |
| Hypervisor security | AWS |
| Global network infrastructure | AWS |
| EC2 operating system patching | Customer |
| EC2 application patching | Customer |
| IAM user management | Customer |
| Enabling S3 bucket encryption | Customer |
| Enabling EBS volume encryption | Customer |
| Security group configuration | Customer |
| NACL configuration | Customer |
| RDS MySQL engine patching | AWS |
| RDS database data backup | Both (AWS automates, you configure retention) |
| CloudTrail enabling | Customer (but tampering with it is your fault) |

---

## 1.4 AWS Organizations and Multi-Account Strategy

### Why One Account Is Never Enough

Imagine a construction company with 200 workers, 50 projects, and 10 departments — all sharing one office with one keycard. Anyone can walk into any room. Mistakes in one room affect every other room. Costs are impossible to track per project.

That is what having one AWS account for your entire company looks like.

**Problems with a single AWS account:**
- Developer testing something accidentally deletes production data
- Security incident in one team's resources can spread to others
- Impossible to attribute costs to specific projects or teams
- No way to enforce different security rules for production vs development
- Compliance: auditors cannot tell which charges belong to which project

**Solution: AWS Organizations — a family of accounts with centralized management**

### Understanding AWS Organizations

AWS Organizations lets you create a **family of related AWS accounts** under one management structure. You get:

1. **Centralized billing** — one monthly bill for all accounts, but broken down per account
2. **Organizational Units (OUs)** — like folders to group related accounts
3. **Service Control Policies (SCPs)** — permission guardrails that apply to entire account groups
4. **Volume discounts** — AWS gives better prices when all accounts' usage is combined

```
Example company: AcmeCorp with 200 engineers

AWS Organization Structure:

Root (Management Account — only used for billing and org management)
│
├── Security OU
│   ├── log-archive account ← all CloudTrail/Config logs go here
│   └── security-audit account ← read-only access for compliance team
│
├── Infrastructure OU
│   └── shared-services account ← Transit Gateway, DNS, shared tools
│
├── Workloads OU
│   ├── Production OU
│   │   ├── prod-frontend account
│   │   ├── prod-backend account
│   │   └── prod-database account
│   │
│   └── Non-Production OU
│       ├── staging account
│       └── dev account
│
└── Sandbox OU
    └── sandbox account ← engineers experiment freely here, deleted monthly
```

**Key principle:** The Management Account (Root) should only be used for organizational management and billing. Do NOT run production workloads in it.

### Service Control Policies (SCPs) — The Permission Guardrails

An SCP is a permission policy you attach to an OU or account that acts like a **maximum permissions boundary**. It does NOT grant permissions — it only LIMITS them.

**Analogy:** A speed limiter on a company car.
- The driver can go as fast as they want within the limit
- But the car physically cannot exceed 80mph
- Even if the driver (IAM admin) wants to go 100mph, the limiter (SCP) stops them

**Critical rule:** SCPs work as a filter. For an action to be allowed:
- The SCP must ALLOW it (or not deny it)
- AND the IAM policy must ALLOW it
- Both conditions must be true. Either one blocking = action denied.

**Example SCPs you should know:**

SCP 1 — Prevent disabling CloudTrail (audit logs):
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Deny",
    "Action": [
      "cloudtrail:StopLogging",
      "cloudtrail:DeleteTrail",
      "cloudtrail:UpdateTrail"
    ],
    "Resource": "*"
  }]
}
```

SCP 2 — Restrict to approved regions only:
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Deny",
    "Action": "*",
    "Resource": "*",
    "Condition": {
      "StringNotEquals": {
        "aws:RequestedRegion": ["us-east-1", "us-west-2", "eu-west-1"]
      }
    }
  }]
}
```

SCP 3 — Prevent expensive GPU instances in dev:
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Deny",
    "Action": "ec2:RunInstances",
    "Resource": "arn:aws:ec2:*:*:instance/*",
    "Condition": {
      "StringLike": {
        "ec2:InstanceType": ["p3.*", "p4.*", "g4.*", "g5.*"]
      }
    }
  }]
}
```

### Hands-On: Setting Up a Multi-Account Foundation

```bash
# ─── STEP 1: Enable AWS Organizations ────────────────────────────
# Run this from your management (root) account
aws organizations create-organization --feature-set ALL

# ─── STEP 2: Get the Root ID ──────────────────────────────────────
ROOT_ID=$(aws organizations list-roots \
  --query 'Roots[0].Id' --output text)
echo "Root ID is: $ROOT_ID"

# ─── STEP 3: Create Organizational Units ─────────────────────────
# Security OU
SECURITY_OU=$(aws organizations create-organizational-unit \
  --parent-id $ROOT_ID --name "Security" \
  --query 'OrganizationalUnit.Id' --output text)

# Infrastructure OU
INFRA_OU=$(aws organizations create-organizational-unit \
  --parent-id $ROOT_ID --name "Infrastructure" \
  --query 'OrganizationalUnit.Id' --output text)

# Workloads OU
WORKLOADS_OU=$(aws organizations create-organizational-unit \
  --parent-id $ROOT_ID --name "Workloads" \
  --query 'OrganizationalUnit.Id' --output text)

# Sandbox OU
SANDBOX_OU=$(aws organizations create-organizational-unit \
  --parent-id $ROOT_ID --name "Sandbox" \
  --query 'OrganizationalUnit.Id' --output text)

# Sub-OUs under Workloads
PROD_OU=$(aws organizations create-organizational-unit \
  --parent-id $WORKLOADS_OU --name "Production" \
  --query 'OrganizationalUnit.Id' --output text)

NONPROD_OU=$(aws organizations create-organizational-unit \
  --parent-id $WORKLOADS_OU --name "NonProduction" \
  --query 'OrganizationalUnit.Id' --output text)

echo "All OUs created successfully"

# ─── STEP 4: Create Member Accounts ──────────────────────────────
# NOTE: account creation is asynchronous — use describe-create-account-status to check

aws organizations create-account \
  --email log-archive@company.com \
  --account-name "log-archive"

aws organizations create-account \
  --email prod-app@company.com \
  --account-name "production-app"

aws organizations create-account \
  --email dev-app@company.com \
  --account-name "development-app"

aws organizations create-account \
  --email sandbox@company.com \
  --account-name "sandbox"

# ─── STEP 5: Create SCP to Protect CloudTrail ────────────────────
cat > /tmp/protect-cloudtrail.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DenyCloudTrailChanges",
      "Effect": "Deny",
      "Action": [
        "cloudtrail:StopLogging",
        "cloudtrail:DeleteTrail",
        "cloudtrail:UpdateTrail",
        "cloudtrail:PutEventSelectors",
        "cloudtrail:RemoveTags"
      ],
      "Resource": "*"
    }
  ]
}
EOF

PROTECT_CT_POLICY=$(aws organizations create-policy \
  --name "ProtectCloudTrail" \
  --description "Prevent disabling audit logs in all accounts" \
  --type SERVICE_CONTROL_POLICY \
  --content file:///tmp/protect-cloudtrail.json \
  --query 'Policy.PolicySummary.Id' --output text)

# Apply to Production and NonProduction OUs
aws organizations attach-policy \
  --policy-id $PROTECT_CT_POLICY --target-id $PROD_OU
aws organizations attach-policy \
  --policy-id $PROTECT_CT_POLICY --target-id $NONPROD_OU

echo "SCP applied to Production and NonProduction OUs"

# ─── STEP 6: Create SCP to restrict regions ──────────────────────
cat > /tmp/restrict-regions.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DenyNonApprovedRegions",
      "Effect": "Deny",
      "Action": "*",
      "Resource": "*",
      "Condition": {
        "StringNotEquals": {
          "aws:RequestedRegion": ["us-east-1", "us-west-2", "eu-west-1"]
        }
      }
    }
  ]
}
EOF

REGION_POLICY=$(aws organizations create-policy \
  --name "RestrictToApprovedRegions" \
  --description "Only allow us-east-1, us-west-2, eu-west-1" \
  --type SERVICE_CONTROL_POLICY \
  --content file:///tmp/restrict-regions.json \
  --query 'Policy.PolicySummary.Id' --output text)

# Apply to the Root (affects ALL accounts)
aws organizations attach-policy \
  --policy-id $REGION_POLICY --target-id $ROOT_ID

echo "Region restriction SCP applied to all accounts"

# ─── STEP 7: Set up Budget Alerts ────────────────────────────────
MY_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)

aws budgets create-budget \
  --account-id $MY_ACCOUNT \
  --budget '{
    "BudgetName": "Monthly-500-Alert",
    "BudgetLimit": {"Amount": "500", "Unit": "USD"},
    "TimeUnit": "MONTHLY",
    "BudgetType": "COST"
  }' \
  --notifications-with-subscribers '[
    {
      "Notification": {
        "NotificationType": "ACTUAL",
        "ComparisonOperator": "GREATER_THAN",
        "Threshold": 80,
        "ThresholdType": "PERCENTAGE"
      },
      "Subscribers": [{"SubscriptionType": "EMAIL", "Address": "billing@company.com"}]
    },
    {
      "Notification": {
        "NotificationType": "ACTUAL",
        "ComparisonOperator": "GREATER_THAN",
        "Threshold": 100,
        "ThresholdType": "PERCENTAGE"
      },
      "Subscribers": [{"SubscriptionType": "EMAIL", "Address": "billing@company.com"}]
    }
  ]'

echo "Budget alert created — emails at 80% and 100% of $500 limit"
```

---

## 1.5 AWS Support Plans — Choosing the Right Level of Help

### The 5 Support Tiers Explained Simply

Think of AWS support like healthcare options:
- **Basic** = Free health information on Wikipedia. No doctor access.
- **Developer** = A nurse you can email during business hours
- **Business** = Your own doctor available 24/7 by phone
- **Enterprise On-Ramp** = Specialist with priority scheduling, 30-min emergency response
- **Enterprise** = Personal medical team on call 24/7, 15-min emergency response

### Comparison Table

| Feature | Basic (Free) | Developer ($29/mo) | Business ($100/mo) | Ent. On-Ramp ($5,500/mo) | Enterprise ($15,000/mo) |
|---------|-------------|-------------------|-------------------|--------------------------|------------------------|
| Technical support | Docs only | Email business hrs | 24/7 phone + chat | 24/7 phone + chat | 24/7 phone + chat |
| General guidance | — | 1 business day | 24 hours | 24 hours | 24 hours |
| System impaired | — | 12 business hours | 12 hours | 12 hours | 12 hours |
| Production down | — | — | **4 hours** | 4 hours | 4 hours |
| Production critical | — | — | **1 hour** | **30 minutes** | **15 minutes** |
| Business critical down | — | — | — | 30 minutes | **15 minutes** |
| Trusted Advisor | 7 checks | 7 checks | ALL checks | ALL checks | ALL checks |
| Technical Account Mgr | No | No | No | Pool TAM | Dedicated TAM |
| Well-Architected reviews | No | No | No | No | Yes |
| AWS Health — Org view | No | No | Yes | Yes | Yes |

### The Exam Pattern

Questions will describe a scenario and ask which plan is needed:

- "Need phone support 24/7" → minimum **Business**
- "Need 1-hour response for production issues" → minimum **Business**
- "Need 30-minute response" → minimum **Enterprise On-Ramp**
- "Need 15-minute response" → **Enterprise only**
- "Need a dedicated Technical Account Manager" → **Enterprise only**
- "Cost-conscious, just need access to all Trusted Advisor checks" → **Business**

### AWS Trusted Advisor — Your Free Robot Advisor

Trusted Advisor continuously scans your AWS account and gives you recommendations in 5 categories:

```
1. COST OPTIMIZATION — Finding money being wasted
   Examples of what it flags:
   - EC2 instances with < 10% CPU utilization for 14 days (idle servers)
   - Unassociated Elastic IP addresses ($0.005/hour when not attached to running instance)
   - Underutilized EBS volumes (provisioned but barely used)
   - Old EC2 snapshots (you forgot to delete)
   - Reserved Instance recommendations (potential savings)

2. SECURITY — Finding dangerous configurations
   Examples:
   - S3 buckets with public read or write access
   - IAM users with no MFA enabled
   - Security groups allowing unrestricted (0.0.0.0/0) access to critical ports
   - Root account has been used recently (risky!)
   - IAM users with access keys but no recent usage

3. PERFORMANCE — Finding bottlenecks
   Examples:
   - EC2 instances with consistently high (> 90%) CPU utilization
   - CloudFront header forwarding suboptimal configuration
   - High utilization EBS volumes approaching IOPS limits

4. FAULT TOLERANCE — Finding single points of failure
   Examples:
   - EC2 instances NOT in Auto Scaling Groups
   - Load balancers with instances only in one AZ
   - RDS instances NOT configured for Multi-AZ
   - EBS volumes with no recent snapshots (no backup!)
   - Route 53 record sets without health checks

5. SERVICE LIMITS (now called "Service Quotas")
   Examples:
   - You have used 80% of your EC2 instance limit in a region
   - DynamoDB table throughput approaching limit
   - IAM roles approaching the per-account limit
```

**Important:** Basic and Developer plans only get 7 basic checks (some Security + Service Limits). The **Business plan is required for ALL Trusted Advisor checks**.

---

## 1.6 AWS Pricing Models — Understanding How You Pay

### Model 1: On-Demand Pricing

**The concept:** You use it, you pay for it. By the second or hour. No commitment.

**Analogy:** Paying for electricity — you pay for every kilowatt-hour you actually use.

**Best for:**
- Development and testing (use it now, stop when done)
- Workloads that run less than a year
- Applications with unpredictable traffic patterns
- New applications where you do not know usage patterns yet

**Pricing example:**
```
EC2 instance: m5.xlarge in us-east-1
On-Demand price: $0.192/hour

If you run it:
  - 1 hour:      $0.192
  - 1 day:       $0.192 × 24 = $4.61
  - 1 month:     $0.192 × 730 = $140.16
  - 1 year:      $0.192 × 8,760 = $1,681.92
```

### Model 2: Reserved Instances (RIs) — Commitment = Savings

**The concept:** You promise to use a specific instance type for 1 or 3 years. In exchange, AWS gives you a big discount.

**Analogy:** Annual vs monthly gym membership. Monthly costs $80/visit-equivalent. Annual costs $20/visit-equivalent because you committed.

**Types of Reserved Instances:**

| RI Type | Flexibility | Discount | When to Use |
|---------|------------|---------|------------|
| Standard RI | Fixed instance type, size, region | Up to 72% off | Stable predictable workloads you will definitely run for 1-3 years |
| Convertible RI | Can change instance type/family | Up to 66% off | When you are unsure which instance family you will need long-term |

**Payment options:**

| Payment | Description | Discount Level |
|---------|-------------|---------------|
| All Upfront | Pay entire 1-year or 3-year cost now | Highest discount |
| Partial Upfront | Pay some upfront, rest monthly | Medium discount |
| No Upfront | Pay monthly (like a lease) | Lowest discount (but still beats On-Demand) |

**Example calculation:**
```
m5.xlarge:
  On-Demand:    $0.192/hour × 8,760 hr/yr = $1,682/year
  RI 1-yr All:  $0.076/hour equivalent    =   $666/year  (60% savings!)
  RI 3-yr All:  $0.046/hour equivalent    =   $403/year  (76% savings!)
```

**When RIs make sense:**
- Running a production database that will be on 24/7 for years → Standard RI 3-year
- Running web servers for a long-term app → Standard RI 1-year
- Not sure of exact instance type → Convertible RI

### Model 3: Savings Plans — Flexible Commitment

**The concept:** You commit to spending a certain dollar amount per hour on compute. AWS gives you a discount. The difference from RIs: you can use the commitment on different instance types.

**Analogy:** A prepaid data plan. You pay $50/month for data. It does not matter if you use it on your phone, tablet, or hotspot — the $50 covers all of them.

**Two types:**

1. **Compute Savings Plans:**
   - Applies to: EC2 (any type, region), Lambda, Fargate
   - Discount: up to 66%
   - Most flexible: change instance type, family, region, OS

2. **EC2 Instance Savings Plans:**
   - Applies to: Specific EC2 instance family in one region
   - Discount: up to 72% (higher than Compute SP)
   - Less flexible: locked to instance family and region

**Exam tip:** When a question asks about committing to a dollar amount of compute spend for flexibility across instance types → Savings Plans. When locked to specific instance type/region/OS → Reserved Instances.

### Model 4: Spot Instances — Auction-Style, Huge Discounts

**The concept:** AWS has servers sitting idle. Instead of wasting them, they rent them at a huge discount. But they can take them back with 2 minutes notice if they need the capacity for On-Demand or Reserved customers.

**Analogy:** "Last-minute hotel deals" — 80% off a room, but the hotel reserves the right to cancel your booking if a VIP customer needs the room.

**The catch:** Your workload can be interrupted without warning (2-minute notice). If this happens:
- For EC2 Spot: instance is terminated (or stopped, depending on your setting)
- You must design your application to handle interruptions gracefully

**Discounts:** Up to 90% off On-Demand prices. Prices fluctuate based on supply and demand.

```
m5.xlarge pricing comparison:
  On-Demand:   $0.192/hour
  Spot (typical): $0.025/hour   ← 87% cheaper!
  
  Annual cost if running 24/7:
    On-Demand: $1,682/year
    Spot:      $219/year    ← Save $1,463/year per instance!
```

**When to use Spot Instances (workloads that tolerate interruption):**
- Big data analysis (Spark/EMR jobs)
- Batch processing (image processing, video transcoding)
- Machine learning training jobs
- Web crawling and scraping
- CI/CD build systems (Jenkins agents)
- Stateless, fault-tolerant applications

**NEVER use Spot for:**
- Production databases
- Web servers (without careful architecture)
- Any workload that must keep running and cannot be interrupted

**Spot Fleet:** A collection of Spot + On-Demand instances. You specify your target capacity and price limits. If Spot gets interrupted, the Fleet can automatically launch On-Demand instances to maintain capacity. This is the recommended pattern for Spot.

### Free Tier — Getting Started at Zero Cost

AWS offers free usage tiers for new and existing accounts:

```
ALWAYS FREE (no time limit, works forever):
  Lambda:        1,000,000 requests/month FREE
                 400,000 GB-seconds compute FREE
  DynamoDB:      25 GB storage FREE
                 25 WCU + 25 RCU (enough for ~200 million requests/month)
  CloudWatch:    10 custom metrics FREE
                 10 alarms FREE
                 1,000,000 API requests FREE
  SNS:           1,000,000 publishes FREE
  SQS:           1,000,000 requests FREE
  AWS Glue:      1,000,000 objects stored in Data Catalog FREE
  Cognito:       50,000 Monthly Active Users FREE

12-MONTH FREE TIER (new accounts only, first 12 months):
  EC2:           750 hours/month t2.micro or t3.micro FREE
  S3:            5 GB standard storage FREE
                 20,000 GET requests + 2,000 PUT requests FREE
  RDS:           750 hours/month db.t2.micro or db.t3.micro FREE
                 20 GB database storage FREE
                 20 GB automated backups FREE
  CloudFront:    1 TB data transfer out FREE
                 10,000,000 HTTP/HTTPS requests FREE
  EBS:           30 GB SSD (gp2/gp3) storage FREE
  Elastic LB:    750 hours FREE (Classic LB)
  ElastiCache:   750 hours cache.t2.micro FREE
```

### Cost Monitoring Commands

```bash
# Check your current month's costs
aws ce get-cost-and-usage \
  --time-period Start=2025-01-01,End=2025-02-01 \
  --granularity MONTHLY \
  --metrics "BlendedCost" "UnblendedCost" "UsageQuantity" \
  --group-by Type=DIMENSION,Key=SERVICE

# Forecast this month's total
aws ce get-cost-forecast \
  --time-period Start=2025-01-15,End=2025-02-01 \
  --granularity MONTHLY \
  --metric BLENDED_COST

# Show top 5 most expensive services
aws ce get-cost-and-usage \
  --time-period Start=2025-01-01,End=2025-02-01 \
  --granularity MONTHLY \
  --metrics "BlendedCost" \
  --group-by Type=DIMENSION,Key=SERVICE \
  --query 'ResultsByTime[0].Groups | sort_by(@, &Metrics.BlendedCost.Amount) | reverse(@) | [:5].[Keys[0], Metrics.BlendedCost.Amount]' \
  --output table
```

---

## 1.7 AWS Well-Architected Framework — The 6 Pillars

AWS created this framework as a set of best practices for building applications in the cloud. Think of these as the "building codes" for cloud architecture — you would not build a house without following safety codes, and you should not build AWS applications without following these principles.

### Pillar 1: Operational Excellence

**Question to ask yourself:** "Can my team operate this system efficiently, and can we improve it over time?"

**What it means in practice:**
- Write runbooks (step-by-step guides for common tasks and incidents)
- Everything is automated (no manual clicking in the console for production changes)
- Small, frequent, reversible changes (not monthly big-bang deployments that are scary to roll back)
- Learn from every incident (post-mortems, blameless reviews)
- Monitor everything to understand what "normal" looks like

**Real example of good vs bad:**

Bad Operational Excellence:
```
- Developer SSH's into production server and manually edits config files
- Nobody documented how to restart the application
- When the server crashes at 3am, nobody knows what to do
- After fixing it, nobody asks "why did this happen?" or "how do we prevent it?"
```

Good Operational Excellence:
```
- All infrastructure is in CloudFormation templates (Infrastructure as Code)
- Config changes go through Git → CI/CD pipeline → CloudFormation update
- Runbook in Confluence: "If web server is down, do steps 1, 2, 3"
- 3am crash: On-call engineer follows runbook, system back up in 10 minutes
- Post-incident review: "Root cause was missing health check. Fix: add health check to ALB."
- CloudWatch dashboard always shows the current health of all systems
```

**Key AWS services for this pillar:**
- CloudFormation (infrastructure as code)
- Systems Manager (run commands, manage configs)
- CloudWatch (monitoring and dashboards)
- EventBridge (automate responses to events)

### Pillar 2: Security

**Question to ask yourself:** "Is my data and systems protected against threats, from outside AND inside my organization?"

**Security is not optional — it is the foundation of everything.**

The 5 security principles:
1. **Strong identity** — everyone must authenticate (MFA required), least privilege always
2. **Traceability** — log EVERYTHING (CloudTrail on, every API call recorded)
3. **Security at every layer** — not just at the network edge, but at every component
4. **Automate security** — not annual audits, but continuous automated scanning
5. **Protect data** — classify it, encrypt it, control who can access it

**Real example of good vs bad:**

Bad Security:
```
- Root account used for daily work (if compromised, attacker has total control)
- One IAM user "admin" shared by entire team (cannot audit who did what)
- S3 bucket for internal files left public (exposed to internet)
- No CloudTrail enabled (no record of who deleted that database)
- EC2 instances have no patches applied for 8 months
```

Good Security:
```
- Root account locked away, MFA required, never used except for billing
- Each person has their own IAM user with only the permissions they need
- All S3 buckets have Block Public Access enabled by default
- CloudTrail enabled in all regions, logs stored in separate security account
- AWS Systems Manager Patch Manager patches EC2 instances weekly
- GuardDuty enabled — detects suspicious activity automatically
```

**Key AWS services for this pillar:**
- IAM (identity and access management)
- KMS (encryption key management)
- CloudTrail (audit logging)
- GuardDuty (threat detection)
- Security Hub (centralized security dashboard)
- AWS Config (compliance checking)

### Pillar 3: Reliability

**Question to ask yourself:** "Does my system keep working even when individual parts fail? Can it recover automatically?"

**The fundamental truth: Everything will fail eventually.** Disks fail, servers crash, network hiccups happen, entire data centers lose power. Reliable systems are designed assuming failure WILL happen, not if.

The 3 reliability principles:
1. **Automatically recover from failure** — use health checks, auto-scaling, Multi-AZ
2. **Test recovery procedures** — do not assume your backup works; test restoring it quarterly
3. **Scale horizontally** — 10 small servers instead of 1 big server (if one of 10 fails, you lose 10% capacity; if the 1 big server fails, you lose 100%)

**Real example:**

Not Reliable:
```
- Website runs on one EC2 instance in one AZ
- Database is single-instance RDS with no Multi-AZ
- No backups configured
- Nobody has tested restoring the database in 2 years
→ AZ goes down → website and database both gone → lost all recent data
```

Reliable:
```
- Website runs on an Auto Scaling Group with 4 EC2 instances across 3 AZs
- Database is Aurora Multi-AZ with automatic failover in 30 seconds
- Daily automated backups with 35-day retention, monthly restore tests
- ALB health checks every 30 seconds — unhealthy instances replaced automatically
→ AZ goes down → load balancer routes to other 2 AZs → users unaffected
```

**Key AWS services for this pillar:**
- Auto Scaling Groups (automatic capacity management)
- Elastic Load Balancing (distribute traffic, health checks)
- Multi-AZ RDS / Aurora (database high availability)
- AWS Backup (centralized backup management)
- Route 53 (health check-based DNS failover)

### Pillar 4: Performance Efficiency

**Question to ask yourself:** "Am I using the right tools and the right size for my workload? Can I serve more users without buying more servers?"

**The core problem:** IT teams often over-provision ("buy big to be safe") which wastes money, or under-provision (things go slow when traffic increases). The cloud lets you match capacity to actual demand.

The 5 performance principles:
1. **Democratize advanced technologies** — use managed services instead of building yourself
2. **Go global in minutes** — deploy in 5 Regions with same template
3. **Use serverless** — no servers to manage, auto-scales to zero when not needed
4. **Experiment more often** — easy to try new instance types or architectures
5. **Use mechanical sympathy** — know your data access patterns and choose matching storage

**Choosing the right EC2 instance type:**

```
General Purpose (t3, m6i, m7g):
  → Web servers, small databases, dev/test
  → Balanced CPU, memory, network

Compute Optimized (c6i, c7g):
  → High-performance web servers, batch processing, video encoding
  → High CPU relative to memory

Memory Optimized (r6i, x2idn):
  → Large in-memory databases (Redis, SAP HANA), real-time big data
  → Very high RAM relative to CPU

Storage Optimized (i4i, d3en):
  → NoSQL databases, data warehouses, distributed file systems
  → Very high sequential read/write to local NVMe SSDs

Accelerated Computing (p4, g5, inf2):
  → Machine learning training and inference
  → GPU workloads, graphics rendering
```

**Key AWS services for this pillar:**
- CloudFront (CDN — cache content at edge for fast global delivery)
- ElastiCache (in-memory caching — reduce database load)
- Auto Scaling (scale based on actual demand metrics)
- Amazon Aurora (5x faster than standard MySQL)
- AWS Compute Optimizer (recommendations for right-sizing)

### Pillar 5: Cost Optimization

**Question to ask yourself:** "Am I spending only what I need to? Am I getting the best value for every dollar?"

**The cloud makes waste easy.** It is very easy to spin up an instance and forget it is running. Or to provision 10x more than you need "just in case." Cost Optimization is about running lean.

The 5 cost principles:
1. **Implement cloud financial management** — track costs, create accountability
2. **Adopt a consumption model** — pay only for what you use, stop paying when done
3. **Measure overall efficiency** — cost per transaction, not just total cost
4. **Stop spending on undifferentiated heavy lifting** — use managed services
5. **Analyze and attribute expenditure** — which team/app/feature costs what

**Quick wins for cost optimization:**

```bash
# Find idle EC2 instances (low CPU)
aws cloudwatch get-metric-statistics \
  --namespace AWS/EC2 \
  --metric-name CPUUtilization \
  --dimensions Name=InstanceId,Value=i-0123456789abcdef0 \
  --start-time 2025-01-01T00:00:00 \
  --end-time 2025-01-08T00:00:00 \
  --period 604800 \
  --statistics Average
# If average CPU < 10% for 7 days → consider downsizing or deleting

# Find unattached EBS volumes (paying for storage with nothing using it)
aws ec2 describe-volumes \
  --filters Name=status,Values=available \
  --query 'Volumes[*].[VolumeId,Size,CreateTime]' \
  --output table
# "available" status = NOT attached to any instance = pure waste

# Find unused Elastic IPs (costs $0.005/hr = $3.65/month per idle IP)
aws ec2 describe-addresses \
  --query 'Addresses[?AssociationId==`null`].[PublicIp,AllocationId]' \
  --output table
```

**Key AWS services for this pillar:**
- AWS Cost Explorer (visualize and analyze costs)
- AWS Budgets (set alerts when spending exceeds thresholds)
- Trusted Advisor (identifies waste automatically)
- Compute Optimizer (right-sizing recommendations)
- S3 Intelligent-Tiering (automatically moves data to cheaper storage class)

### Pillar 6: Sustainability (Added November 2021)

**Question to ask yourself:** "Am I minimizing my environmental impact while getting the work done?"

AWS's data centers are moving to 100% renewable energy. You can help by:
- Right-sizing (not running oversized instances that waste electricity)
- Using managed services (AWS optimizes them more efficiently than DIY)
- Choosing Regions with high renewable energy (eu-west-1 Ireland, eu-north-1 Stockholm)
- Deleting unused resources (zombie servers waste power and cooling 24/7)
- Using Graviton (ARM-based) instances (up to 60% less energy than x86 equivalent)

---

## 1.8 Real-World Project: Multi-Account AWS Foundation

### Scenario

You are joining AcmeCorp as their first AWS SysOps engineer. Currently, the whole engineering team shares one AWS account, total chaos. You need to set up a proper multi-account structure in one day.

### The Architecture

```
Management Account (org management only — no workloads)
│
├── Security OU (cannot be modified by any other team)
│   ├── log-archive — CloudTrail, Config, ALB logs from all accounts
│   └── security-audit — Read-only access for compliance + security team
│
├── Platform OU
│   └── shared-services — Transit Gateway, Route 53 Resolver, Shared VPCs
│
├── Workloads OU
│   ├── Production OU
│   │   ├── prod-web — web tier
│   │   └── prod-data — databases and storage
│   └── NonProduction OU
│       ├── staging — mirrors prod, used for final testing
│       └── dev — developers build and test here
│
└── Sandbox OU
    └── sandbox — free experimentation, auto-cleanup weekly
```

### Implementation Script

```bash
#!/bin/bash
# setup_aws_organization.sh
# Run this from the management account

set -e  # stop on any error

echo "=== Setting up AWS Organization Foundation ==="

# Enable Organizations
aws organizations create-organization --feature-set ALL
ROOT_ID=$(aws organizations list-roots --query 'Roots[0].Id' --output text)
echo "Root ID: $ROOT_ID"

# Create main OUs
create_ou() {
  local parent=$1 name=$2
  aws organizations create-organizational-unit \
    --parent-id "$parent" --name "$name" \
    --query 'OrganizationalUnit.Id' --output text
}

SECURITY_OU=$(create_ou $ROOT_ID "Security")
PLATFORM_OU=$(create_ou $ROOT_ID "Platform")
WORKLOADS_OU=$(create_ou $ROOT_ID "Workloads")
SANDBOX_OU=$(create_ou $ROOT_ID "Sandbox")
PROD_OU=$(create_ou $WORKLOADS_OU "Production")
NONPROD_OU=$(create_ou $WORKLOADS_OU "NonProduction")

echo "OUs created"

# Create accounts
create_account() {
  local email=$1 name=$2
  aws organizations create-account \
    --email "$email" --account-name "$name" \
    --iam-user-access-to-billing ALLOW \
    --query 'CreateAccountStatus.Id' --output text
}

create_account "log-archive@acme.com" "log-archive"
create_account "security-audit@acme.com" "security-audit"
create_account "shared-services@acme.com" "shared-services"
create_account "prod-web@acme.com" "prod-web"
create_account "prod-data@acme.com" "prod-data"
create_account "staging@acme.com" "staging"
create_account "dev@acme.com" "dev"
create_account "sandbox@acme.com" "sandbox"

echo "All accounts created (creation may take a few minutes)"

# SCP 1: Protect audit logs (attach to ALL OUs except Security)
cat > /tmp/scp_protect_logs.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Deny",
    "Action": [
      "cloudtrail:StopLogging", "cloudtrail:DeleteTrail",
      "config:DeleteConfigRule", "config:StopConfigurationRecorder"
    ],
    "Resource": "*"
  }]
}
EOF

PROTECT_LOGS=$(aws organizations create-policy \
  --name "ProtectAuditLogs" --type SERVICE_CONTROL_POLICY \
  --content file:///tmp/scp_protect_logs.json \
  --query 'Policy.PolicySummary.Id' --output text)

for OU in $PROD_OU $NONPROD_OU $PLATFORM_OU $SANDBOX_OU; do
  aws organizations attach-policy --policy-id $PROTECT_LOGS --target-id $OU
done

# SCP 2: Restrict regions (only allow 3 regions)
cat > /tmp/scp_regions.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Deny",
    "Action": "*",
    "Resource": "*",
    "Condition": {
      "StringNotEquals": {
        "aws:RequestedRegion": ["us-east-1", "us-west-2", "eu-west-1"]
      },
      "ArnNotLike": {
        "aws:PrincipalARN": "arn:aws:iam::*:role/AWSControlTowerExecution"
      }
    }
  }]
}
EOF

REGION_SCP=$(aws organizations create-policy \
  --name "RestrictRegions" --type SERVICE_CONTROL_POLICY \
  --content file:///tmp/scp_regions.json \
  --query 'Policy.PolicySummary.Id' --output text)

aws organizations attach-policy --policy-id $REGION_SCP --target-id $ROOT_ID

echo "=== Foundation Setup Complete ==="
echo "Next steps:"
echo "1. Move accounts into correct OUs"
echo "2. Enable CloudTrail Organization Trail"
echo "3. Enable AWS Config in all accounts"
echo "4. Enable GuardDuty with Organization delegated admin"
echo "5. Enable Security Hub with Organization delegated admin"
```

### Enabling CloudTrail for the Entire Organization

```bash
# Create an S3 bucket for organization-wide CloudTrail logs
# (run this in the log-archive account)
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

aws s3api create-bucket \
  --bucket "org-cloudtrail-logs-${ACCOUNT_ID}" \
  --region us-east-1

# Apply bucket policy to allow CloudTrail from all accounts
cat > /tmp/cloudtrail-bucket-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AWSCloudTrailAclCheck",
      "Effect": "Allow",
      "Principal": {"Service": "cloudtrail.amazonaws.com"},
      "Action": "s3:GetBucketAcl",
      "Resource": "arn:aws:s3:::org-cloudtrail-logs-${ACCOUNT_ID}"
    },
    {
      "Sid": "AWSCloudTrailWrite",
      "Effect": "Allow",
      "Principal": {"Service": "cloudtrail.amazonaws.com"},
      "Action": "s3:PutObject",
      "Resource": "arn:aws:s3:::org-cloudtrail-logs-${ACCOUNT_ID}/AWSLogs/*",
      "Condition": {
        "StringEquals": {"s3:x-amz-acl": "bucket-owner-full-control"}
      }
    }
  ]
}
EOF

aws s3api put-bucket-policy \
  --bucket "org-cloudtrail-logs-${ACCOUNT_ID}" \
  --policy file:///tmp/cloudtrail-bucket-policy.json

# Create organization trail (run from management account)
aws cloudtrail create-trail \
  --name "organization-trail" \
  --s3-bucket-name "org-cloudtrail-logs-${ACCOUNT_ID}" \
  --is-organization-trail \
  --is-multi-region-trail \
  --enable-log-file-validation \
  --include-global-service-events

aws cloudtrail start-logging --name "organization-trail"

echo "Organization-wide CloudTrail enabled — all API calls in all accounts now logged"
```

---

## 1.9 AWS Compliance and Governance Fundamentals

### Industry Regulations and AWS

Different industries have specific laws about how data must be stored, protected, and audited. As a SysOps engineer, you need to understand which regulations apply to your company and how to use AWS to meet them.

| Regulation | Industry | Key Requirements | AWS Tools That Help |
|-----------|---------|-----------------|-------------------|
| **HIPAA** | Healthcare (US) | Encrypt PHI (Protected Health Info), audit all access, Business Associate Agreements | KMS, CloudTrail, CloudWatch, RDS encryption |
| **PCI-DSS** | Payment/Finance | Encrypt cardholder data, network segmentation, regular vulnerability scans | KMS, VPC, Security Hub, Inspector |
| **GDPR** | Any company with EU customers | Data minimization, right to be forgotten, data breach notification in 72 hours | S3 Object Expiry, DynamoDB TTL, CloudTrail |
| **SOX** | Public companies (US) | Financial data integrity, audit trails, internal controls | CloudTrail, Config, Organizations |
| **FedRAMP** | US Government | NIST-based security controls | GovCloud regions, compliance certifications |
| **ISO 27001** | Any industry | Information security management system | AWS Artifact (download cert), Config rules |

### The Key Compliance Tools

**AWS Artifact:**
- A self-service portal where you can download AWS's own compliance certifications
- Download: ISO 27001 cert, SOC 2 reports, PCI-DSS attestation, HIPAA BAA
- Free to use
- Access: console.aws.amazon.com/artifact

**AWS Config:**
- Continuously records the configuration of all your AWS resources
- Checks them against rules (managed rules from AWS or custom rules you write)
- Tells you if anything becomes non-compliant
- Keeps a history of every configuration change (who changed what, when)

```bash
# Enable Config to start recording all resources
aws configservice put-configuration-recorder \
  --configuration-recorder '{
    "name": "default",
    "roleARN": "arn:aws:iam::123456789012:role/AWSConfigRole",
    "recordingGroup": {
      "allSupported": true,
      "includeGlobalResourceTypes": true
    }
  }'

aws configservice start-configuration-recorder \
  --configuration-recorder-name default

# Add a compliance rule: all S3 buckets must have encryption enabled
aws configservice put-config-rule \
  --config-rule '{
    "ConfigRuleName": "s3-bucket-server-side-encryption-enabled",
    "Source": {
      "Owner": "AWS",
      "SourceIdentifier": "S3_BUCKET_SERVER_SIDE_ENCRYPTION_ENABLED"
    }
  }'

# Check compliance status
aws configservice describe-compliance-by-config-rule \
  --config-rule-names s3-bucket-server-side-encryption-enabled
```

**AWS Audit Manager:**
- Automates collection of evidence for audits
- Maps your AWS resource configurations to compliance frameworks (PCI-DSS, HIPAA, SOX)
- Generates audit-ready reports
- Saves weeks of manual evidence collection work

**AWS Security Hub:**
- Aggregates findings from GuardDuty, Inspector, Macie, Config, IAM Access Analyzer
- One dashboard showing your entire security posture
- Standards checks: CIS AWS Foundations Benchmark, PCI-DSS, AWS Foundational Security Best Practices

---

## 1.10 Practice Questions

**Q1:** A healthcare startup is building a patient records application. Which factor should drive the AWS Region selection decision FIRST?

- A) Choose us-east-1 because it has the most services available
- B) Choose the Region where engineering team is located for low-latency development
- C) Choose a Region in the same country/jurisdiction where HIPAA compliance and data residency requirements mandate patient data must stay
- D) Choose the cheapest Region to minimize startup costs

**Answer: C**

Explanation: HIPAA (and similar healthcare regulations in other countries) may mandate that patient health information stays within specific geographic boundaries. This is a hard legal requirement that overrides convenience and cost. After satisfying compliance, then consider latency (where are the patients located?) and cost.

---

**Q2:** A company runs a critical e-commerce website on a single EC2 instance in us-east-1a. During a major sale event, the AZ experiences a network issue and the website is down for 2 hours, costing $500,000 in lost sales. What architectural change prevents this?

- A) Upgrade to a larger EC2 instance type (from m5.large to m5.4xlarge)
- B) Enable detailed monitoring on the EC2 instance
- C) Deploy at least 2 EC2 instances across multiple AZs behind an Application Load Balancer, configured with health checks
- D) Enable EC2 Auto Recovery to restart the instance automatically

**Answer: C**

Explanation: AZ failures are a real risk (rare but they happen). The solution is geographic distribution. An ALB distributes traffic across multiple AZs — when one AZ fails, the ALB automatically stops sending traffic there and uses the other AZs. EC2 Auto Recovery (D) only helps when the underlying hardware fails within the same AZ, not when the entire AZ is unreachable.

---

**Q3:** Your company runs EC2 instances for a web application. AWS announces a critical security vulnerability in the underlying hardware (Spectre/Meltdown class). Your EC2 instances also run Amazon Linux 2 with an outdated kernel that has a separate software vulnerability. Under the Shared Responsibility Model, which of the following is TRUE?

- A) AWS is responsible for both — hardware vulnerabilities and OS vulnerabilities on EC2
- B) You are responsible for both
- C) AWS patches the hardware vulnerability; you are responsible for patching the Amazon Linux 2 kernel
- D) Amazon Linux 2 patches automatically, so neither party needs to act

**Answer: C**

Explanation: Hardware vulnerabilities (Spectre, Meltdown) are AWS's responsibility — they patch the underlying hypervisor and physical hardware. However, the operating system running inside your EC2 virtual machine is 100% your responsibility. You must patch Amazon Linux 2 using `yum update` or AWS Systems Manager Patch Manager. Amazon Linux 2 does NOT auto-patch itself unless you configure SSM Patch Manager.

---

**Q4:** Which AWS support plan is the MINIMUM required to receive all Trusted Advisor checks AND 24/7 phone-based technical support?

- A) Basic
- B) Developer
- C) Business
- D) Enterprise On-Ramp

**Answer: C**

Explanation: The Business plan (starting at $100/month or 3% of monthly AWS spend, whichever is higher) provides: ALL Trusted Advisor checks, 24/7 phone + chat support, and 1-hour response time for production system failures. Basic and Developer plans only provide 7 basic Trusted Advisor checks. Developer plan does not include 24/7 phone support.

---

**Q5:** A SysOps engineer applies an SCP to the Production OU that contains:
```json
{
  "Effect": "Deny",
  "Action": "ec2:TerminateInstances",
  "Resource": "*",
  "Condition": {"StringEquals": {"aws:ResourceTag/Environment": "production"}}
}
```
The production account administrator (with AdministratorAccess IAM policy) tries to terminate an EC2 instance tagged `Environment: production`. What happens?

- A) The termination succeeds because AdministratorAccess overrides SCPs
- B) The termination succeeds because tags can be removed before terminating
- C) The termination is denied — SCPs override even AdministratorAccess
- D) The termination is denied only for the root user, not IAM administrators

**Answer: C**

Explanation: Service Control Policies are HIGHER than IAM policies in the permission hierarchy. Even an IAM user with AdministratorAccess (which normally allows all actions) CANNOT perform actions denied by an SCP. The SCP is a hard ceiling that nobody inside the account can override — not even the root user of that account (they would need to modify the SCP from the management account). This is the entire point of SCPs — they are organizational guardrails that individual account admins cannot bypass.

---

## Chapter 1 Summary

| Concept | What to Remember |
|---------|-----------------|
| **AWS** | Rent computers/storage/databases over internet; pay only for usage; scale instantly |
| **Regions** | 33+ geographic areas worldwide; data stays in chosen region; choose based on compliance → latency → services → cost |
| **Availability Zones** | 2-6 physical buildings per Region; isolated power/cooling/networking; ALWAYS deploy across 2+ AZs |
| **Edge Locations** | 450+ CloudFront cache points; serve content from city nearest user; 5ms vs 200ms latency |
| **Shared Responsibility** | AWS = physical security + hardware + hypervisor; YOU = OS patches + data encryption + IAM + security groups |
| **AWS Organizations** | Manage multiple accounts; OUs = folders; SCPs = permission ceiling that overrides even Admin access |
| **Support Plans** | Business plan minimum for all Trusted Advisor + 24/7 phone; Enterprise for 15-min critical response + TAM |
| **On-Demand** | Pay per hour/second; no commitment; most expensive but most flexible |
| **Reserved Instances** | 1-3 year commitment to instance type; up to 72% discount; for steady predictable workloads |
| **Savings Plans** | Commit $/hour on any compute; up to 66% off; more flexible than RIs |
| **Spot Instances** | Up to 90% off; can be interrupted with 2-min notice; for batch/flexible workloads ONLY |
| **Well-Architected** | 6 pillars: Operational Excellence, Security, Reliability, Performance Efficiency, Cost Optimization, Sustainability |
| **Trusted Advisor** | Free robot scanning your account for waste, security holes, performance issues, fault tolerance gaps; ALL checks require Business plan |
"""

with open(r"e:\fastapi\aws-admin\01_AWS_Fundamentals_Global_Infrastructure.md", "w", encoding="utf-8") as f:
    f.write(content)

print(f"Written {len(content.splitlines())} lines")
