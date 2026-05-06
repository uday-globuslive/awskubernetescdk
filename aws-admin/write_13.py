
content = r"""# Chapter 13: Migration & Hybrid Cloud
## (Moving to AWS and Connecting Your On-Premises World)

---

## 13.1 Why Migrate to AWS?

### The Business Case for Cloud Migration

Organizations migrate to AWS for multiple reasons:

```
Current State (On-Premises Data Center):
  - Hardware purchase: $500,000 every 3-5 years
  - Facility cost: $200,000/year (power, cooling, space)
  - Operations team: 10 engineers just to maintain servers
  - Time to provision new servers: 6-12 weeks
  - Disaster recovery: Second data center = double the cost
  - Utilization: Servers run at 8% average utilization (92% waste!)

After Migration to AWS:
  - No hardware purchase
  - No facility cost
  - Operations team focuses on innovation, not maintenance
  - Time to provision new servers: minutes
  - Disaster recovery: Built-in with Multi-AZ and Cross-Region replication
  - Utilization: Pay only for what you use
  
But migration is complex — you need a strategy!
```

---

## 13.2 The 7 Rs of Migration (Migration Strategies)

The "7 Rs" framework helps you decide HOW to migrate each application:

### Strategy 1: RETIRE — Just Turn It Off

```
"We have 500 applications. Let's inventory them — how many are actually used?"

Typical finding: 20-30% of applications can be decommissioned
  - Legacy apps nobody uses anymore
  - Redundant apps (3 different expense tracking systems)
  - Replaced apps (old CRM replaced by Salesforce)

Action: Shut down. Don't migrate.
Cost: $0. Savings: Eliminate licensing, maintenance, security patching.
When to use: Application is no longer used or needed
```

### Strategy 2: RETAIN — Leave It Alone (For Now)

```
"This application can't be migrated yet"
Reasons:
  - Recently purchased expensive 3-year license
  - Requires hardware not available in cloud (special GPU, exotic OS)
  - Regulatory requirement to keep on-premises
  - Highly complex, risky to migrate now

Action: Keep on-premises. Revisit in 1-2 years.
When to use: Too risky, too costly, or not valuable enough to migrate now
```

### Strategy 3: REHOST — "Lift and Shift"

```
"Move the application to AWS exactly as it is — no code changes"

Example:
  Before: Your application runs on 3 physical servers in your data center
  After: Your application runs on 3 EC2 instances in AWS

Tools: AWS Application Migration Service (MGN), CloudEndure
Time to migrate: Fastest (days to weeks per application)
Cost savings: 30% from infrastructure savings
Risk: Lowest (no code changes)

When to use: 
  - Large migration (hundreds of apps, limited time)
  - Application is stable and not being actively developed
  - Just need to close the data center
  
Analogy: Moving to a new house — you pack everything exactly as it is
and put it in the new house, same arrangement
```

### Strategy 4: REPLATFORM — "Lift, Tinker, and Shift"

```
"Make small optimizations without changing the core architecture"

Examples:
  - Oracle Database → Amazon RDS for Oracle (no more database patching)
  - Java app on Tomcat → AWS Elastic Beanstalk (no more server management)
  - Self-managed MySQL → Amazon Aurora MySQL (better performance, HA)
  - On-prem backup → AWS Backup (eliminate backup infrastructure)

No code changes, just platform changes
Time to migrate: Weeks per application
Cost savings: 50%+ from eliminating management overhead
Risk: Low

When to use:
  - Want managed service benefits without rewriting code
  - Happy with the architecture, just want less management overhead
```

### Strategy 5: REPURCHASE — "Move to SaaS"

```
"Replace with a commercial off-the-shelf cloud product"

Examples:
  - Self-hosted CRM → Salesforce
  - Self-hosted email (Exchange) → Microsoft 365 or Google Workspace
  - Self-hosted HR system → Workday
  - Self-hosted LMS → Canvas or Coursera
  - Self-hosted video conferencing → Zoom

You lose customization but gain:
  - Vendor maintains everything
  - Automatic feature updates
  - No infrastructure to manage

Time to migrate: Weeks-months (data migration + training)
When to use: Best-of-breed SaaS product exists for this use case
```

### Strategy 6: REFACTOR / RE-ARCHITECT — "Rethink and Redesign"

```
"Fully redesign the application to be cloud-native"

Example:
  Before: Monolithic application deployed on large servers
  After: Microservices deployed as Lambda functions and containers
  
  Before: File uploads stored on local disk, single server
  After: Files stored in S3, application is stateless

Before: Batch processing job runs every night
After: Event-driven processing with SQS + Lambda (real-time)

This is the MOST WORK but provides the MOST BENEFIT

Time to migrate: Months to years per application
Cost savings: 70%+ from cloud-native optimization
Risk: High (significant code changes)

When to use:
  - Application has poor performance that needs to be fixed
  - Application needs to scale massively (current architecture can't)
  - Significant business value justifies the investment
  - Greenfield opportunity (rewriting legacy system anyway)
```

### Strategy 7: RELOCATE — "Move Hypervisor to Cloud"

```
"Move VMware VMs from on-premises VMware to VMware Cloud on AWS"

This is for organizations deeply invested in VMware:
  - Move VMware workloads without converting to EC2
  - Familiar VMware tools and operations
  - Bridge to eventually migrating to native AWS services

When to use: VMware-heavy environments, need rapid migration of many VMs
```

### 7 Rs Summary Table

| Strategy | Code Changes | Speed | Cost Savings | Best For |
|---------- |-------------|-------|-------------|---------|
| Retire | N/A | Immediate | 100% eliminated | Unused apps |
| Retain | None | No migration | None now | Too complex/risky |
| Rehost | None | Fastest | 30% | Close DC fast |
| Replatform | Minimal | Fast | 50% | Managed services |
| Repurchase | None | Medium | Varies | SaaS available |
| Refactor | Significant | Slowest | 70%+ | Scalability needed |
| Relocate | None | Fast | 20% | VMware environments |

---

## 13.3 AWS Migration Hub

**Migration Hub** is a central place to track migration progress across multiple AWS services and tools.

```bash
# Register your application in Migration Hub
aws migrationhub describe-migration-task \
  --progress-update-stream "CloudEndure" \
  --migration-task-name "web-app-server-01"

# Import discovery data from Application Discovery Service
aws migrationhubstrategy start-assessment \
  --data-collection-details file://discovery-data.json
```

---

## 13.4 AWS Application Discovery Service

Before migrating, you need to understand what you have. **Application Discovery Service** automatically discovers:
- Server inventory (CPU, RAM, disk, OS)
- Running processes and installed software
- Network connections between servers
- Utilization metrics (actual CPU/memory usage)

This data helps you:
- Right-size EC2 instances for migration
- Understand application dependencies
- Prioritize migration order

```bash
# Discovery Agent (install on each on-premises server)
# Collects: CPU/RAM, processes, network connections, performance metrics
# Reports to: AWS Application Discovery Service

# Discovery Connector (VMware vCenter agentless)
# No agent install needed! Just connect to vCenter
# Collects: VM inventory and performance from vCenter

# View discovered servers
aws discovery describe-agents \
  --query 'agentsInfo[*].[agentId,hostName,osName,agentType,agentNetworkInfoList[0].ipAddress]' \
  --output table

# Start data collection
aws discovery start-data-collection-by-agent-ids \
  --agent-ids agent-123 agent-456

# Export collected data to S3 for analysis
aws discovery start-export-task \
  --export-data-format CSV \
  --query '[exportId]'
```

---

## 13.5 AWS DMS — Database Migration Service

### What is DMS?

**DMS (Database Migration Service)** migrates databases to AWS with minimal downtime. Key feature: **continuous replication** — it keeps the source and target databases in sync while you switch over.

### DMS Migration Patterns

**Homogeneous migration (same database engine):**
```
On-premises MySQL → Amazon Aurora MySQL
On-premises PostgreSQL → Amazon RDS PostgreSQL
No schema conversion needed (same SQL dialect)
```

**Heterogeneous migration (different engines):**
```
Oracle → Aurora PostgreSQL (use Schema Conversion Tool first)
SQL Server → Amazon Aurora MySQL
Sybase → Amazon Aurora MySQL
Requires Schema Conversion Tool (SCT) to convert stored procedures, 
views, and database objects
```

### DMS Migration Process

```
Phase 1: Full Load
  DMS copies ALL existing data from source to target
  Source continues serving production traffic (reads and writes)
  
Phase 2: Ongoing Replication (CDC — Change Data Capture)
  DMS captures every INSERT, UPDATE, DELETE on source
  Applies changes to target in near-real-time
  Target stays in sync with source
  
Phase 3: Cutover
  Your application health: source and target are in sync (lag: seconds)
  Stop application writes to source
  Wait for final replication to complete
  Redirect application to target database
  Total downtime: minutes or seconds!
```

```bash
# Create DMS replication instance
aws dms create-replication-instance \
  --replication-instance-identifier prod-migration-instance \
  --replication-instance-class dms.r5.large \
  --allocated-storage 100 \
  --multi-az false \
  --publicly-accessible false

# Create source endpoint (on-premises MySQL)
aws dms create-endpoint \
  --endpoint-identifier source-mysql \
  --endpoint-type source \
  --engine-name mysql \
  --username admin \
  --password 'SecureP@ssword' \
  --server-name 192.168.1.50 \
  --port 3306 \
  --database-name production_db

# Create target endpoint (Aurora MySQL)
aws dms create-endpoint \
  --endpoint-identifier target-aurora \
  --endpoint-type target \
  --engine-name aurora \
  --username admin \
  --password 'SecureP@ssword' \
  --server-name production-cluster.cluster-abc123.us-east-1.rds.amazonaws.com \
  --port 3306

# Test connectivity
aws dms test-connection \
  --replication-instance-arn arn:aws:dms:us-east-1:123456789012:rep:prod-migration-instance \
  --endpoint-arn arn:aws:dms:us-east-1:123456789012:endpoint:source-mysql

# Create migration task (full load + ongoing replication)
aws dms create-replication-task \
  --replication-task-identifier prod-migration-task \
  --source-endpoint-arn arn:aws:dms:... \
  --target-endpoint-arn arn:aws:dms:... \
  --replication-instance-arn arn:aws:dms:... \
  --migration-type full-load-and-cdc \
  --table-mappings '{
    "rules": [{
      "rule-type": "selection",
      "rule-id": "1",
      "rule-name": "include-all-tables",
      "object-locator": {"schema-name": "production_db", "table-name": "%"},
      "rule-action": "include"
    }]
  }' \
  --replication-task-settings '{
    "TargetMetadata": {"TargetSchema": "", "SupportLobs": true},
    "FullLoadSettings": {"TargetTablePrepMode": "DO_NOTHING"},
    "Logging": {"EnableLogging": true}
  }'

# Start the migration
aws dms start-replication-task \
  --replication-task-arn arn:aws:dms:... \
  --start-replication-task-type start-replication

# Monitor progress
aws dms describe-replication-tasks \
  --filters Name=replication-task-id,Values=prod-migration-task \
  --query 'ReplicationTasks[0].[Status,TableStatistics]'
```

---

## 13.6 AWS DataSync — File and Object Data Transfer

**DataSync** moves large amounts of data (files) between on-premises storage and AWS storage services.

```
Supported source/destination:
  On-premises NFS → Amazon S3
  On-premises SMB (Windows) → Amazon EFS
  On-premises HDFS (Hadoop) → Amazon S3
  Amazon S3 ↔ Amazon EFS (between AWS services)
  Amazon S3 ↔ Amazon FSx
  
Performance: Up to 10 Gbps
Automatic: Checksum verification, data integrity checks
Scheduling: One-time or recurring transfers
Cost: $0.0125 per GB transferred
```

```bash
# Create DataSync agent (install on-premises)
# Then register it
aws datasync create-agent \
  --activation-key XXXXX-XXXXX-XXXXX \
  --agent-name on-prem-agent \
  --tags Key=Environment,Value=production

# Create source location (on-prem NFS)
aws datasync create-location-nfs \
  --server-hostname 192.168.1.100 \
  --subdirectory /data/exports \
  --on-prem-config AgentArns=arn:aws:datasync:us-east-1:123456789012:agent/agent-abc

# Create destination location (S3)
aws datasync create-location-s3 \
  --s3-bucket-arn arn:aws:s3:::my-migration-bucket \
  --subdirectory /migrated-data \
  --s3-config BucketAccessRoleArn=arn:aws:iam::123456789012:role/DataSyncRole

# Create and start transfer task
aws datasync create-task \
  --source-location-arn arn:aws:datasync:...location-nfs... \
  --destination-location-arn arn:aws:datasync:...location-s3... \
  --name prod-data-migration \
  --options VerifyMode=ONLY_FILES_TRANSFERRED,LogLevel=TRANSFER

aws datasync start-task-execution \
  --task-arn arn:aws:datasync:...task...
```

---

## 13.7 AWS Snow Family — Physical Data Transfer

### When Network Transfer is Too Slow

```
Problem: You have 100 TB of data to migrate.

Network speed: 1 Gbps dedicated line
Transfer rate: 1 Gbps = 125 MB/second
Time to transfer 100 TB: 100,000 GB ÷ 0.125 GB/s = 800,000 seconds = 9.2 days

But:
  - Your line isn't always at 100% capacity
  - Network interruptions require retransmission
  - Business operations are also using the network
  
Reality: 100 TB over 1 Gbps takes 4-6 weeks in practice.

Solution: Ship data physically!
  AWS ships you a device, you copy data to it, ship it back.
  AWS imports data to S3.
  
Transfer via 10 Gbps device: 100 TB in 2-3 days of actual copy time
Shipping: 1-2 days each way
Total: 1 week vs 4-6 weeks over the network!
```

### Snow Device Comparison

| Device | Storage | Use Case | Data Transfer Direction |
|--------|---------|---------|------------------------|
| Snowcone | 8-14 TB | Edge computing, small migrations | Both ways |
| Snowball Edge Storage | 80 TB usable | Large migrations, offline regions | Both ways |
| Snowball Edge Compute | 42 TB + GPU/compute | Edge computing, ML inference | Both ways |
| Snowmobile | Up to 100 PB | Exabyte-scale data center migration | AWS import only |

```bash
# Request a Snowball Edge device
aws snowball create-job \
  --job-type IMPORT \
  --resources '{
    "S3Resources": [{
      "BucketArn": "arn:aws:s3:::migration-target-bucket"
    }]
  }' \
  --description "Data center migration - Batch 1" \
  --address-id ADID-XXXXXXXXXXXXXXXXXXXXXXXXXX \
  --kms-key-arn arn:aws:kms:us-east-1:123456789012:key/abc123 \
  --role-arn arn:aws:iam::123456789012:role/SnowballRole \
  --snowball-capacity-preference T80

# After device arrives: use Snowball client to copy data
# snowball cp -r /data/exports s3://migration-target-bucket/data/
# Ship device back to AWS — data is imported to S3
```

---

## 13.8 Hybrid Connectivity — Connecting On-Premises to AWS

### Option 1: AWS Direct Connect

```
On-Premises Data Center
         │
         │ Dedicated private fiber (1 Gbps or 10 Gbps)
         │ NOT going through the public internet
         ▼
  AWS Direct Connect Location (carrier hotel / colocation facility)
         │
         │ AWS backbone network
         ▼
       AWS VPC
       
Benefits:
  - Consistent network performance (no internet congestion)
  - Lower data transfer costs ($0.02/GB vs $0.09/GB internet)
  - More secure (not traversing public internet)
  - Required for compliance (HIPAA, PCI, financial regulations)
  
Downside:
  - Expensive to set up: $1,000-$10,000/month + partner fees
  - Takes weeks to provision the physical connection
  - Single point of failure — need redundant connections
  
Use when: Consistent performance, compliance requirements, large data transfer volumes
```

### Option 2: AWS Site-to-Site VPN

```
On-Premises Data Center
         │
         │ Encrypted VPN tunnel over the public internet (IPsec)
         ▼
  AWS Virtual Private Gateway (attached to your VPC)
         │
         ▼
       AWS VPC
       
Benefits:
  - Quick to set up (minutes, not weeks)
  - Low cost ($0.05/hour per VPN connection)
  - Works over existing internet connection
  - Highly available (two tunnels per connection)
  
Downside:
  - Uses public internet (variable performance)
  - Limited bandwidth (typically 1.25 Gbps max per tunnel)
  
Use when: Quick connectivity, small traffic volume, backup for Direct Connect
```

### Direct Connect vs VPN Comparison

| Feature | Direct Connect | Site-to-Site VPN |
|---------|---------------|-----------------|
| Network path | Private (not internet) | Public internet (encrypted) |
| Setup time | Weeks | Minutes |
| Cost | $1,000+/month | $0.05/hour (~$36/month) |
| Bandwidth | 1 Gbps or 10 Gbps | Up to 1.25 Gbps per tunnel |
| Consistency | Predictable performance | Variable (internet dependent) |
| Best for | Production, compliance | Quick setup, backup connection |

---

## 13.9 AWS Outposts — AWS in Your Data Center

**Outposts** brings AWS infrastructure physically into your own data center.

**Why would you want this?**
- Applications with ultra-low latency requirements (manufacturing automation, real-time trading)
- Data residency requirements (data must stay in your building)
- Applications that must stay on-premises but want cloud-native APIs

**What you get:**
- Actual AWS rack installed in your data center
- Runs genuine AWS services (EC2, EBS, RDS, ECS, EKS)
- Managed by AWS (patched, maintained remotely)
- Connected to your AWS Region via Direct Connect

```
Your Data Center
┌──────────────────────────────────────┐
│                                      │
│   ┌────────────────────┐             │
│   │   AWS Outposts     │             │
│   │   (Physical rack)  │             │
│   │                    │             │
│   │  EC2 instances     │             │
│   │  EBS volumes       │             │
│   │  Local load balancer│            │
│   └────────────────────┘             │
│                │                     │
│                │ Direct Connect       │
└───────────────────────────────────── ┘
                 │
                 ▼
            AWS Region
         (management plane,
          additional services)
```

---

## 13.10 Practice Questions

**Q1:** Your company is migrating 300 applications to AWS. Business leadership says the data center lease expires in 6 months. Which migration strategy maximizes the number of apps migrated within 6 months?

- A) Refactor all applications to be cloud-native
- B) Rehost (lift-and-shift) all applications using AWS Application Migration Service
- C) Replatform each application to use managed services
- D) Retire all applications and rebuild from scratch

**Answer: B**

Explanation: When time is the constraint (data center closing in 6 months), Rehost (lift-and-shift) is the right strategy. It requires no code changes, can be automated with AWS Application Migration Service (MGN), and can migrate servers quickly. After migration, you can optimize over time (replatform, refactor individual apps). Refactoring (A) takes months per application — you'd migrate maybe 10-20 apps in 6 months, not 300. The principle: "Migrate first, optimize later."

---

**Q2:** You need to migrate a 5 TB Oracle database to Amazon Aurora PostgreSQL. The migration must have minimal downtime (less than 30 minutes). What is the correct approach?

- A) Take a database backup, transfer to AWS, restore to Aurora
- B) Use AWS SCT (Schema Conversion Tool) to convert schema, then DMS with full load + CDC for minimal cutover downtime
- C) Use Snowball Edge to transfer the database
- D) Manually recreate all tables in Aurora and insert data

**Answer: B**

Explanation: Oracle → Aurora PostgreSQL is a heterogeneous migration (different SQL dialects). The correct process: (1) Use AWS Schema Conversion Tool (SCT) to convert Oracle stored procedures, triggers, and schema to PostgreSQL. (2) Use DMS for full load (initial data copy while production continues running on Oracle). (3) Enable CDC (Change Data Capture) to replicate ongoing changes. (4) When lag is near-zero, cutover: stop writes to Oracle, wait for final sync, redirect app to Aurora. Cutover takes minutes. Backup/restore (A) requires extended downtime equal to backup + transfer + restore time (many hours for 5 TB).

---

**Q3:** Your company has 200 TB of video files on-premises that need to be migrated to S3. Your internet connection is 1 Gbps. What is the FASTEST way to migrate this data?

- A) Upload directly to S3 via the internet
- B) Use AWS DataSync over the internet
- C) Use AWS Snowball Edge devices to physically transfer the data
- D) Use AWS Direct Connect

**Answer: C**

Explanation: 200 TB over 1 Gbps would take over 18 days of continuous upload (and real networks are never 100% utilized, so realistically 4-8 weeks). AWS Snowball Edge devices can transfer 100 TB to the device in 2-3 days per device. With 3 Snowball devices in parallel, you could move all 200 TB in about a week. Direct Connect (D) could increase bandwidth but takes weeks to provision and is costly. DataSync (B) still uses your internet connection — same bandwidth limitation.

---

**Q4:** Which AWS migration strategy is most appropriate for an application that needs to scale to 10x current load, but the monolithic architecture cannot handle this?

- A) Rehost — lift and shift to EC2
- B) Replatform — move to Elastic Beanstalk
- C) Refactor — redesign as microservices/serverless
- D) Retain — keep on-premises

**Answer: C**

Explanation: If the root problem is that the architecture cannot scale, a lift-and-shift (A) or replatform (B) won't solve the scalability problem — you're just moving the same architecture to AWS. The problem is architectural, so the solution is architectural: Refactoring into microservices or serverless components allows each component to scale independently. This is the most work but the only option that actually solves the stated problem (10x scale). "Rehost first, refactor later" is valid for most apps, but not when the current architecture fundamentally cannot meet requirements.

---

**Q5:** You need consistent, private network connectivity between your on-premises data center and AWS VPC for compliance reasons. The connection must not traverse the public internet. What should you use?

- A) AWS Site-to-Site VPN
- B) AWS Direct Connect
- C) AWS Transit Gateway
- D) NAT Gateway

**Answer: B**

Explanation: AWS Direct Connect provides a private, dedicated network connection between your data center and AWS that does NOT traverse the public internet. This satisfies compliance requirements that mandate data not travel over public networks. VPN (A) encrypts traffic but still routes it over the public internet — the traffic is encrypted but IS traversing the internet, which some compliance requirements prohibit. Transit Gateway (C) connects VPCs to each other and to VPN/Direct Connect but is not itself the connectivity solution.

---

## Chapter 13 Summary

| Strategy/Service | Purpose | Key Fact |
|-----------------|---------|----------|
| Retire | Remove unused apps | 20-30% of apps can typically be retired |
| Retain | Keep on-premises | Too complex or costly to migrate now |
| Rehost | Lift-and-shift | No code changes; fastest migration |
| Replatform | Small optimizations | Managed services; no code changes |
| Repurchase | SaaS replacement | Replace custom app with commercial SaaS |
| Refactor | Cloud-native redesign | Most work; best long-term benefits |
| Migration Hub | Track migration progress | Central dashboard for all migrations |
| App Discovery Service | Inventory on-prem | Discovers servers, dependencies, utilization |
| DMS | Database migration | Full load + CDC for minimal downtime |
| DataSync | File data migration | Up to 10 Gbps; integrity checking |
| Snowball Edge | Physical data transfer | 80 TB per device; faster than network for large data |
| Direct Connect | Private dedicated network | Not internet; compliance; consistent performance |
| Site-to-Site VPN | Encrypted internet tunnel | Quick setup; variable performance |
| Outposts | AWS in your DC | Low latency; data residency requirements |
"""

with open(r"e:\fastapi\aws-admin\13_Migration_HybridCloud.md", "w", encoding="utf-8") as f:
    f.write(content)

print(f"Written {len(content.splitlines())} lines")
