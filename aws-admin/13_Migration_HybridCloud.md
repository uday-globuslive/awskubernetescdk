# Chapter 13: Migration & Hybrid Cloud

## AWS SysOps Administrator Exam Domain Coverage
- **Domain 3**: Deployment, Provisioning, and Automation (18%)
- Migration strategies, DMS, DataSync, Snowball, Direct Connect, VPN

---

## 13.1 AWS Migration Framework

### The 7 Rs of Migration (Modernization Strategies)

| Strategy | Definition | Effort | When to Use |
|----------|-----------|--------|-------------|
| **Rehost** (Lift & Shift) | Move as-is to cloud (EC2) | Low | Fast migration, tight timeline |
| **Replatform** (Lift, Tinker, Shift) | Minor cloud optimizations | Medium | RDS instead of EC2+MySQL |
| **Repurchase** | Replace with SaaS | Low | Move CRM to Salesforce |
| **Refactor/Re-architect** | Redesign for cloud-native | High | Microservices, serverless |
| **Retire** | Decommission | None | 20-30% of apps are unused |
| **Retain** | Keep on-premises | None | Compliance, latency |
| **Relocate** | Move to AWS without change | Low | VMware Cloud on AWS |

### Migration Process Phases
```
ASSESS → MOBILIZE → MIGRATE & MODERNIZE

ASSESS:
  - Application Discovery Service (automated discovery)
  - Migration Evaluator (business case)
  - Migration Hub (track progress)

MOBILIZE:
  - Migration Readiness Assessment
  - Landing Zone setup (AWS Control Tower)
  - Pilot migrations

MIGRATE:
  - Wave-based migration
  - Cut-over and validation
  - Decommission source
```

---

## 13.2 AWS Application Discovery Service

ADS discovers your on-premises infrastructure before migration:

```bash
# Install Discovery Agent on on-premises servers (Linux)
curl -O https://s3.us-west-2.amazonaws.com/aws-discovery-agent.us-west-2/linux/latest/aws-discovery-agent.tar.gz
tar -xzf aws-discovery-agent.tar.gz
sudo ./install -r us-east-1 -k ACCESS_KEY -s SECRET_KEY

# Or use agentless discovery (vCenter VMware environments)
# Deploy Discovery Connector OVA to vCenter

# Start data collection
aws discovery start-data-collection-by-agent-ids \
  --agent-ids agent-id-1 agent-id-2

# Get discovered servers
aws discovery describe-configurations \
  --configuration-type SERVER

# Export discovery data for analysis
aws discovery create-export-task \
  --export-data-format CSV \
  --start-time $(date -d '7 days ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ)
```

---

## 13.3 AWS Migration Hub

Centralized tracking for migrations:

```bash
# List migrations being tracked
aws migrationhub describe-migration-task \
  --progress-update-stream APPLICATION_DISCOVERY_SERVICE \
  --migration-task-name my-app-migration

# Associate source server with migration task
aws migrationhub associate-discovered-resource \
  --progress-update-stream APPLICATION_DISCOVERY_SERVICE \
  --migration-task-name my-app-migration \
  --discovered-resource ConfigurationId=server-id,Description=WebServer

# Notify task state change
aws migrationhub notify-migration-task-state \
  --progress-update-stream APPLICATION_DISCOVERY_SERVICE \
  --migration-task-name my-app-migration \
  --task '{"Status":"IN_PROGRESS","StatusDetail":"Launching EC2 instances"}' \
  --update-date-time $(date -u +%Y-%m-%dT%H:%M:%SZ)
```

---

## 13.4 AWS Database Migration Service (DMS)

DMS migrates databases to AWS with **minimal downtime** using full load + CDC (Change Data Capture).

### DMS Migration Process
```
Source DB                DMS Replication Instance        Target DB
(on-premises)                                            (AWS RDS)
    │                           │                            │
    ├──── Full Load ────────────►────── Load data ──────────►│
    │     (initial copy)        │      to target             │
    │                           │                            │
    └──── CDC (ongoing) ────────►────── Apply changes ───────►│
          (ongoing replication)         continuously
    
Cut-over: 
  1. Verify target data matches source
  2. Stop writes to source
  3. Let CDC drain
  4. Switch application connection strings
  5. Decommission source
```

### DMS Setup
```bash
# Create replication instance
aws dms create-replication-instance \
  --replication-instance-identifier production-migration \
  --replication-instance-class dms.r5.large \
  --allocated-storage 100 \
  --vpc-security-group-ids sg-dms \
  --replication-subnet-group-identifier dms-subnet-group \
  --multi-az \
  --publicly-accessible false

# Create source endpoint (PostgreSQL on-premises)
aws dms create-endpoint \
  --endpoint-identifier source-postgres \
  --endpoint-type source \
  --engine-name postgres \
  --server-name 192.168.1.100 \
  --port 5432 \
  --database-name production \
  --username migration_user \
  --password 'MigrationPass123!' \
  --ssl-mode verify-full

# Create target endpoint (Aurora PostgreSQL)
aws dms create-endpoint \
  --endpoint-identifier target-aurora \
  --endpoint-type target \
  --engine-name aurora-postgresql \
  --server-name aurora-cluster.cluster-xxx.us-east-1.rds.amazonaws.com \
  --port 5432 \
  --database-name production \
  --username admin \
  --password 'AuroraPass123!'

# Test connections
aws dms test-connection \
  --replication-instance-arn arn:aws:dms:... \
  --endpoint-arn arn:aws:dms:...source-arn

# Create and start migration task
aws dms create-replication-task \
  --replication-task-identifier full-load-and-cdc \
  --source-endpoint-arn arn:aws:dms:...source-arn \
  --target-endpoint-arn arn:aws:dms:...target-arn \
  --replication-instance-arn arn:aws:dms:...instance-arn \
  --migration-type full-load-and-cdc \
  --table-mappings '{
    "rules": [{
      "rule-type": "selection",
      "rule-id": "1",
      "rule-name": "include-all",
      "object-locator": {"schema-name": "%", "table-name": "%"},
      "rule-action": "include"
    }]
  }' \
  --replication-task-settings '{
    "TargetMetadata": {"TargetSchema": "", "SupportLobs": true},
    "FullLoadSettings": {"TargetTablePrepMode": "DO_NOTHING"},
    "Logging": {"EnableLogging": true}
  }'

aws dms start-replication-task \
  --replication-task-arn arn:aws:dms:...task-arn \
  --start-replication-task-type start-replication

# Monitor replication lag
aws dms describe-replication-tasks \
  --filters Name=replication-task-arn,Values=arn:aws:dms:...task-arn \
  --query 'ReplicationTasks[0].{Status:Status,ReplicationLag:ReplicationTaskStats.AppliedLatency}'
```

### AWS Schema Conversion Tool (SCT)
For **heterogeneous migrations** (different DB engines):
- Oracle → Aurora PostgreSQL
- SQL Server → Aurora MySQL
- Teradata → Amazon Redshift

SCT converts schema, stored procedures, and identifies manual conversion tasks (runs as desktop app, no CLI).

---

## 13.5 AWS DataSync

DataSync moves **large amounts of data** between on-premises and AWS storage:

```
On-premises NAS/NFS ──► DataSync Agent ──► DataSync Service ──► S3/EFS/FSx
                        (VM on-premises)    (in AWS)
```

```bash
# Create DataSync S3 location
aws datasync create-location-s3 \
  --s3-bucket-arn arn:aws:s3:::destination-bucket \
  --s3-config BucketAccessRoleArn=arn:aws:iam::123456789012:role/DataSyncRole \
  --s3-storage-class STANDARD

# Create DataSync NFS location (on-premises)
aws datasync create-location-nfs \
  --server-hostname 192.168.1.50 \
  --subdirectory /exports/data \
  --on-prem-config AgentArns=arn:aws:datasync:...:agent/agent-id \
  --mount-options Version=NFS4_0

# Create and start task
aws datasync create-task \
  --source-location-arn arn:aws:datasync:...nfs-location \
  --destination-location-arn arn:aws:datasync:...s3-location \
  --name migrate-nas-to-s3 \
  --options '{
    "VerifyMode": "ONLY_FILES_TRANSFERRED",
    "TransferMode": "CHANGED",
    "LogLevel": "TRANSFER",
    "TaskQueueing": "ENABLED"
  }' \
  --schedule ScheduleExpression='cron(0 2 * * ? *)'  # Daily sync at 2 AM

aws datasync start-task-execution \
  --task-arn arn:aws:datasync:...task-arn

# Monitor transfer
aws datasync describe-task-execution \
  --task-execution-arn arn:aws:datasync:...execution-arn \
  --query '{Status:Status,BytesTransferred:BytesTransferred,FilesTransferred:FilesTransferred}'
```

---

## 13.6 AWS Snow Family

For migrating **large datasets** where network transfer is impractical.

### When to Use Snowball
```
Calculate transfer time: 10TB at 1Gbps = 10TB / (1Gbps / 8 bits) = ~22 hours
                         100TB at 1Gbps = ~9 days
                         1PB at 1Gbps = 90+ days → USE SNOWBALL

Rule of thumb: > 1 week to transfer → consider Snowball
```

| Device | Storage | Compute | Use Case |
|--------|---------|---------|---------|
| **Snowcone** | 8TB HDD, 14TB SSD | 4 vCPU | Small migrations, edge |
| **Snowball Edge Storage Optimized** | 80TB | 40 vCPU | Large data migrations |
| **Snowball Edge Compute Optimized** | 28TB | 52 vCPU, GPU option | Edge computing |
| **Snowmobile** | 100PB | — | Exabyte-scale migrations |

```bash
# Order a Snowball job
aws snowball create-job \
  --job-type IMPORT \
  --resources '{
    "S3Resources": [{
      "BucketArn": "arn:aws:s3:::destination-bucket",
      "KeyRange": {}
    }]
  }' \
  --description "Datacenter migration Phase 1" \
  --address-id address-id \
  --kms-key-arn arn:aws:kms:us-east-1:123456789012:key/key-id \
  --role-arn arn:aws:iam::123456789012:role/SnowballRole \
  --snowball-type EDGE_STORAGE_OPTIMIZED \
  --shipping-option SECOND_DAY

# Check job status
aws snowball describe-job --job-id job-id

# After device arrives, use Snowball Client to transfer:
# snowball start --ip DEVICE_IP --manifest manifest.bin --unlock-code CODE
# snowball cp /local/data s3://destination-bucket/
# snowball stop
```

---

## 13.7 AWS Transfer Family

Managed SFTP, FTPS, and FTP server with S3 or EFS backend:

```bash
# Create SFTP server backed by S3
aws transfer create-server \
  --protocols SFTP \
  --identity-provider-type SERVICE_MANAGED \
  --endpoint-type PUBLIC \
  --logging-role arn:aws:iam::123456789012:role/TransferLoggingRole \
  --tags Key=Environment,Value=production

# Create user
aws transfer create-user \
  --server-id server-id \
  --user-name sftp-user \
  --role arn:aws:iam::123456789012:role/TransferUserRole \
  --home-directory /my-bucket/sftp-user \
  --home-directory-type LOGICAL \
  --home-directory-mappings '[{
    "Entry": "/",
    "Target": "/my-bucket/uploads/sftp-user"
  }]' \
  --ssh-public-key-body "ssh-rsa AAAAB3NzaC1yc2EAAAA..."
```

---

## 13.8 Storage Gateway

Hybrid storage service connecting on-premises to AWS cloud storage.

### Gateway Types

| Type | Function | Use Case |
|------|---------|---------|
| **S3 File Gateway** | NFS/SMB mount that stores in S3 | Backup files to S3 |
| **Volume Gateway - Cached** | iSCSI volumes, data in S3, cache on-premises | Cloud-backed storage |
| **Volume Gateway - Stored** | Full volumes on-premises, async backup to S3 | Local storage + backup |
| **Tape Gateway** | Virtual tape library backed by S3/Glacier | Replace physical tape |

```bash
# Activate Storage Gateway (after deploying VM/hardware appliance)
aws storagegateway activate-gateway \
  --activation-key ACTIVATION_KEY \
  --gateway-name prod-file-gateway \
  --gateway-region us-east-1 \
  --gateway-type FILE_S3

# Create S3 file share
aws storagegateway create-s3-file-share \
  --client-token $(date +%s) \
  --gateway-arn arn:aws:storagegateway:...gateway-arn \
  --role arn:aws:iam::123456789012:role/StorageGatewayRole \
  --location-arn arn:aws:s3:::my-storage-bucket \
  --default-storage-class S3_STANDARD_IA \
  --object-acl bucket-owner-full-control \
  --client-list '["0.0.0.0/0"]' \
  --nfs-file-share-defaults FileMode=0666,DirectoryMode=0777

# Refresh cache (after direct S3 uploads)
aws storagegateway refresh-cache \
  --file-share-arn arn:aws:storagegateway:...:share/share-id
```

---

## 13.9 Direct Connect

Dedicated private network connection from on-premises to AWS.

### Direct Connect Setup
```
On-Premises Router ──► Direct Connect Location ──► AWS Region
                        (co-location facility)
```

### Virtual Interfaces (VIFs)

| VIF Type | Connects To | Use Case |
|---------|------------|---------|
| **Public VIF** | AWS public endpoints | S3, DynamoDB, CloudFront |
| **Private VIF** | VPC via VGW | EC2, RDS, private resources |
| **Transit VIF** | Transit Gateway | Multiple VPCs |

```bash
# Create Direct Connect connection (ordered through AWS Console)
# After physical connection established:

# Create private virtual interface
aws directconnect create-private-virtual-interface \
  --connection-id dxcon-xxx \
  --new-private-virtual-interface '{
    "virtualInterfaceName": "prod-private-vif",
    "vlan": 100,
    "asn": 65000,
    "authKey": "bgp-auth-key",
    "amazonAddress": "169.254.1.1/30",
    "customerAddress": "169.254.1.2/30",
    "virtualGatewayId": "vgw-xxx"
  }'

# Check VIF status
aws directconnect describe-virtual-interfaces --connection-id dxcon-xxx

# Create Link Aggregation Group (LAG) for redundancy
aws directconnect create-lag \
  --number-of-connections 2 \
  --location EQUINIX-SV \
  --bandwidth 1Gbps \
  --lag-name production-lag
```

### HA Architecture for Direct Connect
```
Best Practice: DX + VPN for redundancy

    On-Premises
         │
    ┌────┴──────────┐
    │               │
   DX (primary)   Site-to-Site VPN (backup)
    │               │
    └────┬──────────┘
         │
      AWS VPC
      
OR: Two DX connections from different providers
OR: Two DX in different locations (LAG)
```

---

## 13.10 Site-to-Site VPN

Encrypted IPSec tunnel over the internet connecting on-premises to AWS VPC.

```bash
# Create Customer Gateway (represents on-premises router)
aws ec2 create-customer-gateway \
  --type ipsec.1 \
  --bgp-asn 65000 \
  --public-ip 203.0.113.10 \  # Your on-premises router's public IP
  --device-name on-prem-router

# Create Virtual Private Gateway and attach to VPC
aws ec2 create-vpn-gateway --type ipsec.1 --amazon-side-asn 64512

aws ec2 attach-vpn-gateway \
  --vpn-gateway-id vgw-xxx \
  --vpc-id vpc-xxx

# Create VPN connection
aws ec2 create-vpn-connection \
  --type ipsec.1 \
  --customer-gateway-id cgw-xxx \
  --vpn-gateway-id vgw-xxx \
  --options '{
    "StaticRoutesOnly": false,
    "TunnelOptions": [
      {
        "TunnelInsideCidr": "169.254.1.0/30",
        "PreSharedKey": "strong-pre-shared-key-1"
      },
      {
        "TunnelInsideCidr": "169.254.2.0/30",
        "PreSharedKey": "strong-pre-shared-key-2"
      }
    ]
  }'

# Download VPN configuration for on-premises router
aws ec2 describe-vpn-connections \
  --vpn-connection-ids vpn-xxx \
  --query 'VpnConnections[0].CustomerGatewayConfiguration'

# Enable route propagation on VPC route tables
aws ec2 enable-vgw-route-propagation \
  --gateway-id vgw-xxx \
  --route-table-id rtb-xxx
```

---

## 13.11 AWS Control Tower (Landing Zone)

Control Tower automates **multi-account setup** with security guardrails:

```
Management Account
    │
    ├── Log Archive Account (centralized logging)
    │
    ├── Audit Account (security tooling)
    │
    └── Organizational Units (OUs)
        ├── Security OU
        ├── Infrastructure OU
        │   ├── Production Account
        │   └── Staging Account
        └── Sandbox OU
            └── Developer Accounts (per team)
```

```bash
# Control Tower setup is done via console, but you can manage accounts via CLI:

# Create new account in org with Control Tower controls
aws organizations create-account \
  --email new-team@example.com \
  --account-name NewTeamAccount

# Apply guardrails (done via Control Tower console or API)
aws controltower enable-control \
  --control-identifier arn:aws:controltower:us-east-1::control/STRONGLY_RECOMMENDED \
  --target-identifier arn:aws:organizations::123456789012:ou/o-xxx/ou-xxx
```

---

## 13.12 Real-World Project: Lift & Shift Migration

### Migration Plan: 3-Tier Web App
```
On-Premises → AWS (Lift & Shift → Replatform in Phase 2)

Phase 1: Lift & Shift
  Web Servers (Apache) → EC2 (same config, Auto Scaling)
  App Servers (Tomcat) → EC2 (same config, Auto Scaling)
  Database (MySQL)     → RDS MySQL Multi-AZ (managed)
  Files (NFS)          → Amazon EFS

Phase 2: Replatform (later)
  EC2 Web → S3 + CloudFront (static frontend)
  EC2 App → ECS Fargate
  MySQL   → Aurora MySQL
```

### Migration Script
```python
import boto3
import json

ec2 = boto3.client('ec2')
ssm = boto3.client('ssm')

def create_migration_ami(source_instance_id: str, name: str) -> str:
    """Create AMI from on-premises server (after install of SSM agent)."""
    
    response = ec2.create_image(
        InstanceId=source_instance_id,
        Name=f'migration-{name}-{datetime.now().strftime("%Y%m%d")}',
        Description=f'Migration AMI for {name}',
        NoReboot=False
    )
    
    ami_id = response['ImageId']
    
    # Wait for AMI to be available
    waiter = ec2.get_waiter('image_available')
    waiter.wait(ImageIds=[ami_id])
    
    return ami_id

def validate_migration(source_host: str, target_instance_id: str, checks: list):
    """Run validation checks after migration."""
    
    for check in checks:
        response = ssm.send_command(
            InstanceIds=[target_instance_id],
            DocumentName='AWS-RunShellScript',
            Parameters={'commands': [check['command']]}
        )
        
        # Wait for result and compare
        # ... (poll command invocation for result)
        
        print(f"Check '{check['name']}': ...")

# Migration validation checks
checks = [
    {'name': 'app-health', 'command': 'curl -f http://localhost/health'},
    {'name': 'db-connectivity', 'command': 'mysql -h $DB_HOST -u $DB_USER -p$DB_PASS -e "SELECT 1"'},
    {'name': 'disk-space', 'command': 'df -h / | awk "NR==2 {if ($5+0 > 80) exit 1}"'},
]
```

---

## 13.13 Practice Questions (SysOps Exam Level)

**Q1:** You need to migrate 200TB of data from on-premises to S3. The connection is 100Mbps. What is the fastest approach?

**A:** Network transfer time: 200TB / (100Mbps/8) = 200TB / 12.5MB/s = ~185 days.

**Use AWS Snowball Edge Storage Optimized:**
- 80TB per device → order 3 devices
- Typical turn-around: 1-2 weeks total
- Data transferred is encrypted at 256-bit AES
- Final delivery via AWS network from Snowball facility

For ongoing replication after initial migration, use **DataSync over Direct Connect or VPN**.

---

**Q2:** A company uses Oracle database on-premises and wants to move to Aurora PostgreSQL. What AWS services help with this?

**A:**
1. **AWS Schema Conversion Tool (SCT)** — converts Oracle schema, views, stored procedures to PostgreSQL-compatible syntax; identifies items requiring manual conversion
2. **AWS DMS** — migrates the actual data (full load + CDC for minimal downtime)
3. **DMS Fleet Advisor** — assess database fleet compatibility

Process:
1. SCT converts schema → apply to Aurora PostgreSQL
2. DMS full load → copies existing data
3. DMS CDC → keeps in sync while application tested
4. Cut-over: stop Oracle writes, wait for CDC to catch up, switch connection string

---

**Q3:** How does AWS Direct Connect differ from Site-to-Site VPN?

**A:**

| | Direct Connect | Site-to-Site VPN |
|---|---|---|
| Connection | Dedicated private fiber | Encrypted IPSec over internet |
| Bandwidth | 1Gbps to 100Gbps | Up to 1.25Gbps |
| Latency | Consistent, low | Variable (internet) |
| Setup time | Weeks/months | Minutes/hours |
| Cost | Port fee + data transfer | Per VPN connection/hour |
| Encryption | Not by default (add MACsec) | AES-256 always encrypted |
| Availability | Physical redundancy needed | Dual tunnels by default |

**Best practice**: Use both — DX for primary, VPN as failover.

---

**Q4:** During DMS migration, you notice the replication lag keeps increasing. What should you investigate?

**A:**
1. **Replication instance size** — upgrade to larger instance (DMS is CPU/memory intensive)
2. **Target DB bottleneck** — check RDS CloudWatch metrics (CPU, storage I/O, connections)
3. **LOB columns** — large objects slow CDC significantly; consider table-specific settings
4. **Index on target** — CDC inserts are faster without indexes; add indexes after full load
5. **Network bandwidth** — between replication instance and source/target
6. **Parallel full load** — increase parallel threads for tables

```bash
# Increase parallel load threads
# In task settings: "FullLoadSettings": {"MaxFullLoadSubTasks": 8}
```

---

**Q5:** Your company has Direct Connect with a single 1Gbps connection. What is the best way to improve availability?

**A:**
1. **Add a second DX connection** from a different DX location/provider (most reliable)
2. **Create a Link Aggregation Group (LAG)** — multiple connections in same location (protects against port failure, not location failure)
3. **DX + VPN backup** — cheapest HA option (VPN activates on DX failure via BGP)

For **maximum HA (99.99% SLA)**: Two connections at two different Direct Connect locations, each with redundant physical ports.

---

## Key Migration Terms for Exam

| Term | Definition |
|------|-----------|
| 7 Rs | Rehost, Replatform, Repurchase, Refactor, Retire, Retain, Relocate |
| Lift & Shift | Move application to EC2 without changes (Rehost) |
| Application Discovery Service | Discover on-premises servers/dependencies |
| Migration Hub | Track migrations across services |
| DMS | Database Migration Service — migrate DBs with CDC |
| CDC | Change Data Capture — stream ongoing changes to target |
| SCT | Schema Conversion Tool — convert between DB engines |
| DataSync | Transfer large datasets between on-premises and AWS |
| Snowball Edge | Physical device for offline large-scale data transfer |
| Snowmobile | Truck-based transfer for exabyte-scale (100PB) |
| Transfer Family | Managed SFTP/FTPS/FTP server backed by S3/EFS |
| Storage Gateway | Hybrid storage connecting on-premises to S3/Glacier |
| Direct Connect | Dedicated private fiber connection to AWS |
| VIF | Virtual Interface — logical connection on DX (Public/Private/Transit) |
| VGW | Virtual Private Gateway — AWS side of VPN/DX |
| CGW | Customer Gateway — on-premises router config |
| Site-to-Site VPN | IPSec encrypted tunnel over internet |
| Control Tower | Automated multi-account setup with guardrails |
| Landing Zone | Well-architected multi-account AWS environment |
