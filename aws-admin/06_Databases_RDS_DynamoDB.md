# Chapter 6: Databases — RDS, Aurora, DynamoDB & ElastiCache

## AWS SysOps Administrator Exam Domain Coverage
- **Domain 2**: Reliability and Business Continuity (RDS Multi-AZ, backup, failover)
- **Domain 3**: Deployment, Provisioning (DB provisioning, migration)
- **Domain 6**: Cost Optimization (Reserved instances, right-sizing)

---

## 6.1 Database Services Overview

```
┌─────────────────────────────────────────────────────────────┐
│              AWS DATABASE SERVICE SELECTION                  │
│                                                             │
│  Relational (SQL)     Key-Value / Wide Column               │
│  ├── RDS              ├── DynamoDB (NoSQL, serverless)      │
│  └── Aurora           └── ElastiCache (Redis/Memcached)    │
│                                                             │
│  Document             Graph                                 │
│  └── DocumentDB       └── Neptune                          │
│     (MongoDB-compat)                                        │
│                                                             │
│  Time Series          Ledger                                │
│  └── Timestream       └── QLDB (immutable history)         │
│                                                             │
│  Data Warehouse       Search                                │
│  └── Redshift         └── OpenSearch Service               │
└─────────────────────────────────────────────────────────────┘
```

**Choosing the right database:**
| Need | Service |
|------|---------|
| Traditional app, SQL, structured data | RDS (MySQL, PostgreSQL, Oracle, SQL Server) |
| MySQL/PostgreSQL with 5x performance | Aurora |
| Serverless, NoSQL, millisecond latency, auto-scale | DynamoDB |
| Caching, sessions, real-time leaderboards | ElastiCache (Redis) |
| Data warehousing, analytics | Redshift |
| MongoDB-compatible | DocumentDB |
| Social networks, recommendations (graph) | Neptune |

---

## 6.2 Amazon RDS Deep Dive

RDS provides **managed relational databases** — AWS handles hardware, OS, DB engine patching, backups, and failover.

### Supported Engines
- MySQL (up to v8.0)
- PostgreSQL (up to v16)
- MariaDB
- Oracle Database
- Microsoft SQL Server
- DB2

### RDS Instance Classes
| Class | Purpose |
|-------|---------|
| **db.t3/t4g** | Dev/test, low traffic (burstable) |
| **db.m5/m6i/m6g** | General purpose production |
| **db.r5/r6i/r6g** | Memory-optimized (large DBs, caching) |
| **db.x1e/x2g** | Large in-memory workloads (SAP HANA) |

```bash
# Create RDS PostgreSQL instance
aws rds create-db-instance \
  --db-instance-identifier prod-postgres \
  --db-instance-class db.r6g.xlarge \
  --engine postgres \
  --engine-version 15.3 \
  --master-username dbadmin \
  --master-user-password "$(openssl rand -base64 20)" \
  --allocated-storage 100 \
  --max-allocated-storage 1000 \  # Enable auto-scaling up to 1 TB
  --storage-type gp3 \
  --iops 3000 \
  --vpc-security-group-ids sg-db-sg \
  --db-subnet-group-name db-subnet-group \
  --multi-az \
  --backup-retention-period 7 \
  --preferred-backup-window "02:00-03:00" \
  --preferred-maintenance-window "Mon:03:00-Mon:04:00" \
  --storage-encrypted \
  --kms-key-id arn:aws:kms:us-east-1:123456789012:key/key-id \
  --deletion-protection \
  --enable-performance-insights \
  --performance-insights-retention-period 7 \
  --enable-cloudwatch-logs-exports postgresql \
  --tags Key=Environment,Value=production
```

### RDS Multi-AZ

Multi-AZ provides **high availability** and **automatic failover**:

```
Primary (AZ-1)          Standby (AZ-2)
┌─────────────┐         ┌─────────────┐
│  RDS DB     │◄──────►│  RDS Sync   │
│  (Active)   │ Sync    │  Standby    │
│  Reads+     │  Repl.  │  (Passive)  │
│  Writes     │         │             │
└─────────────┘         └─────────────┘
       │                       │
   DNS endpoint         (NOT accessible
  (same always)          to reads by default)
```

**Failover behavior:**
1. AWS detects primary failure
2. DNS flips to standby (60-120 seconds)
3. Application reconnects to same endpoint URL
4. Standby becomes new primary; new standby created in original AZ

```bash
# Test failover (for testing purposes)
aws rds reboot-db-instance \
  --db-instance-identifier prod-postgres \
  --force-failover

# Monitor failover events
aws rds describe-events \
  --source-identifier prod-postgres \
  --source-type db-instance \
  --duration 60
```

**Multi-AZ vs Read Replicas — Key Exam Distinction:**
| Feature | Multi-AZ | Read Replica |
|---------|---------|-------------|
| Purpose | High Availability / Failover | Performance / Scale reads |
| Replication | Synchronous | Asynchronous |
| Readable | No (standby) | Yes |
| Cross-region | No (same region) | Yes |
| Automatic failover | Yes | No (manual promotion) |
| Improves write performance | No | No |

### Read Replicas
```bash
# Create read replica (same or different region)
aws rds create-db-instance-read-replica \
  --db-instance-identifier prod-postgres-replica-1 \
  --source-db-instance-identifier prod-postgres \
  --db-instance-class db.r6g.large \
  --availability-zone us-east-1b \
  --multi-az false

# Create cross-region read replica (for DR)
aws rds create-db-instance-read-replica \
  --db-instance-identifier prod-postgres-replica-dr \
  --source-db-instance-identifier arn:aws:rds:us-east-1:123456789012:db:prod-postgres \
  --db-instance-class db.r6g.large \
  --region us-west-2

# Promote read replica to standalone DB (manual failover)
aws rds promote-read-replica \
  --db-instance-identifier prod-postgres-replica-dr
```

---

## 6.3 RDS Backups & Restoration

### Automated Backups
- Taken **daily** during backup window
- **Transaction logs** backed up every 5 minutes
- Enables **Point-in-Time Recovery (PITR)** — restore to any second within retention period
- Retention: 1-35 days (0 = disabled)
- Stored in S3 (no extra charge for storage up to 100% of DB size)

### Manual Snapshots
- Taken by user on-demand
- Persist until explicitly deleted
- Can be copied to another region for DR
- Can be shared with other AWS accounts

```bash
# Create manual snapshot
aws rds create-db-snapshot \
  --db-instance-identifier prod-postgres \
  --db-snapshot-identifier prod-postgres-before-migration-$(date +%Y%m%d)

# Restore from automated backup (PITR)
aws rds restore-db-instance-to-point-in-time \
  --source-db-instance-identifier prod-postgres \
  --target-db-instance-identifier prod-postgres-restored \
  --restore-time 2025-05-01T14:30:00Z \
  --db-instance-class db.r6g.xlarge \
  --multi-az

# Restore from snapshot
aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier prod-postgres-from-snap \
  --db-snapshot-identifier prod-postgres-before-migration-20250101 \
  --db-instance-class db.r6g.xlarge

# Copy snapshot to another region (for DR)
aws rds copy-db-snapshot \
  --source-db-snapshot-identifier arn:aws:rds:us-east-1:123456789012:snapshot:prod-postgres-snap \
  --target-db-snapshot-identifier prod-postgres-dr \
  --region us-west-2 \
  --kms-key-id arn:aws:kms:us-west-2:123456789012:key/dr-key-id
```

---

## 6.4 RDS Security

### Encryption
- Enable encryption **at creation** (cannot enable on running unencrypted DB)
- Uses KMS CMK
- Encrypted at rest: data, automated backups, snapshots, read replicas, logs

**To encrypt an existing unencrypted RDS instance:**
1. Create snapshot of unencrypted DB
2. Copy snapshot with encryption enabled
3. Restore from encrypted snapshot
4. Update application connection string
5. Delete old unencrypted instance

```bash
# Copy unencrypted snapshot and encrypt it
aws rds copy-db-snapshot \
  --source-db-snapshot-identifier unencrypted-snap \
  --target-db-snapshot-identifier encrypted-snap \
  --kms-key-id arn:aws:kms:us-east-1:123456789012:key/key-id
```

### SSL/TLS in Transit
```python
# Connect to RDS PostgreSQL with SSL
import psycopg2
import ssl

conn = psycopg2.connect(
    host='prod-postgres.xxxx.us-east-1.rds.amazonaws.com',
    database='myapp',
    user='app_user',
    password=get_secret('prod/postgres/password'),
    sslmode='require',
    sslrootcert='/path/to/us-east-1-bundle.pem'
)
```

### RDS IAM Authentication
```bash
# Generate auth token (valid for 15 minutes)
TOKEN=$(aws rds generate-db-auth-token \
  --hostname prod-postgres.xxxx.us-east-1.rds.amazonaws.com \
  --port 5432 \
  --region us-east-1 \
  --username app_user)

# Connect using token as password
psql "host=prod-postgres.xxxx.us-east-1.rds.amazonaws.com \
  port=5432 \
  dbname=myapp \
  user=app_user \
  password=$TOKEN \
  sslmode=require"
```

### Secrets Manager for RDS Credentials
```bash
# Create secret with automatic rotation
aws secretsmanager create-secret \
  --name prod/postgres/masterpassword \
  --secret-string '{"username":"dbadmin","password":"InitialPass123!","host":"prod-postgres.xxxx.rds.amazonaws.com","port":5432,"dbname":"myapp"}'

# Enable automatic rotation (every 30 days)
aws secretsmanager rotate-secret \
  --secret-id prod/postgres/masterpassword \
  --rotation-lambda-arn arn:aws:lambda:us-east-1:123456789012:function:SecretsManagerRDSPostgreSQL \
  --rotation-rules AutomaticallyAfterDays=30
```

---

## 6.5 Amazon Aurora

Aurora is AWS's cloud-native relational database, compatible with MySQL and PostgreSQL but designed from scratch for the cloud. Delivers **5x MySQL** and **3x PostgreSQL** performance.

### Aurora Architecture
```
┌─────────────────────────────────────────────────────────────┐
│                  AURORA CLUSTER                              │
│                                                             │
│  Writer Endpoint         Reader Endpoint                    │
│       │                       │                             │
│  ┌────▼────┐            ┌─────▼─────┐                      │
│  │ Primary │            │  Reader 1 │ (Aurora Replica)      │
│  │ Instance│            │  Reader 2 │ (up to 15 replicas)   │
│  └─────────┘            └───────────┘                      │
│       │                       │                             │
│       └──────────┬────────────┘                             │
│                  ▼                                          │
│  ┌────────────────────────────────────────┐                 │
│  │         SHARED STORAGE VOLUME          │                 │
│  │  (6 copies across 3 AZs — durable!)   │                 │
│  │  Auto-grows in 10 GB increments        │                 │
│  │  Up to 128 TB                          │                 │
│  └────────────────────────────────────────┘                 │
└─────────────────────────────────────────────────────────────┘
```

### Aurora vs RDS

| Feature | RDS | Aurora |
|---------|-----|--------|
| Storage | EBS (replicate with replication) | Shared storage with 6 copies |
| Read Replicas | Up to 5 | Up to 15 (sub-10ms lag) |
| Failover time | 1-2 minutes | ~30 seconds |
| Backtrack | No | Yes (go back in time, no restore needed) |
| Global Database | No | Yes (5 secondary regions) |
| Serverless | No | Yes (Aurora Serverless v2) |
| Performance | Standard | 5x MySQL, 3x PostgreSQL |

### Aurora Serverless v2
```bash
# Create Aurora Serverless v2 (auto-scales compute)
aws rds create-db-cluster \
  --db-cluster-identifier my-aurora-serverless \
  --engine aurora-postgresql \
  --engine-version 15.3 \
  --master-username dbadmin \
  --master-user-password "SecurePass123!" \
  --serverless-v2-scaling-configuration MinCapacity=0.5,MaxCapacity=32 \
  --vpc-security-group-ids sg-db-sg \
  --db-subnet-group-name aurora-subnet-group \
  --storage-encrypted \
  --deletion-protection

# Add serverless writer instance
aws rds create-db-instance \
  --db-instance-identifier my-aurora-writer \
  --db-cluster-identifier my-aurora-serverless \
  --db-instance-class db.serverless \
  --engine aurora-postgresql
```

### Aurora Global Database
```bash
# Create global cluster (primary region)
aws rds create-global-cluster \
  --global-cluster-identifier my-global-db \
  --engine aurora-postgresql \
  --engine-version 15.3 \
  --storage-encrypted \
  --deletion-protection

# Add secondary region
aws rds create-db-cluster \
  --global-cluster-identifier my-global-db \
  --db-cluster-identifier my-aurora-secondary \
  --engine aurora-postgresql \
  --region us-west-2 \
  --db-subnet-group-name aurora-subnet-group-west \
  --vpc-security-group-ids sg-db-west

# Failover (promote secondary to primary — RTO < 1 minute)
aws rds failover-global-cluster \
  --global-cluster-identifier my-global-db \
  --target-db-cluster-identifier arn:aws:rds:us-west-2:123456789012:cluster:my-aurora-secondary
```

---

## 6.6 Amazon DynamoDB

DynamoDB is a **fully managed, serverless, NoSQL database** designed for single-digit millisecond performance at any scale.

### DynamoDB Key Concepts
```
┌─────────────────────────────────────────────────────────────┐
│                    DYNAMODB TABLE                            │
│                                                             │
│  Partition Key (PK) — required, determines partition        │
│  Sort Key (SK)      — optional, enables range queries       │
│                                                             │
│  Example: E-commerce orders table                          │
│  PK: customerId, SK: orderId                                │
│                                                             │
│  ┌──────────────┬──────────────┬────────────────────────┐  │
│  │ customerId   │ orderId      │ attributes...           │  │
│  ├──────────────┼──────────────┼────────────────────────┤  │
│  │ CUST001      │ ORD-001-2025 │ {status, total, items} │  │
│  │ CUST001      │ ORD-002-2025 │ {status, total, items} │  │
│  │ CUST002      │ ORD-003-2025 │ {status, total, items} │  │
│  └──────────────┴──────────────┴────────────────────────┘  │
│                                                             │
│  Query by PK: Get all orders for CUST001                   │
│  GetItem by PK+SK: Get specific order                      │
│  Scan: Full table scan (expensive — avoid!)                 │
└─────────────────────────────────────────────────────────────┘
```

### DynamoDB Capacity Modes

| Mode | Description | Best For |
|------|-------------|---------|
| **Provisioned** | Set RCU/WCU; auto-scaling available | Predictable, steady traffic |
| **On-Demand** | Pay per request; no capacity planning | Variable, unpredictable traffic |

```bash
# Create DynamoDB table (On-Demand mode)
aws dynamodb create-table \
  --table-name Orders \
  --attribute-definitions \
    AttributeName=customerId,AttributeType=S \
    AttributeName=orderId,AttributeType=S \
    AttributeName=orderDate,AttributeType=S \
  --key-schema \
    AttributeName=customerId,KeyType=HASH \
    AttributeName=orderId,KeyType=RANGE \
  --billing-mode PAY_PER_REQUEST \
  --global-secondary-indexes '[{
    "IndexName": "OrdersByDate",
    "KeySchema": [
      {"AttributeName":"customerId","KeyType":"HASH"},
      {"AttributeName":"orderDate","KeyType":"RANGE"}
    ],
    "Projection": {"ProjectionType":"ALL"}
  }]' \
  --sse-specification Enabled=true,SSEType=KMS,KMSMasterKeyId=arn:aws:kms:... \
  --stream-specification StreamEnabled=true,StreamViewType=NEW_AND_OLD_IMAGES \
  --point-in-time-recovery-specification PointInTimeRecoveryEnabled=true \
  --deletion-protection-enabled \
  --tags Key=Environment,Value=production
```

### DynamoDB CRUD Operations
```python
import boto3
from boto3.dynamodb.conditions import Key, Attr
from decimal import Decimal

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = dynamodb.Table('Orders')

# PutItem
table.put_item(
    Item={
        'customerId': 'CUST001',
        'orderId': 'ORD-001-2025',
        'orderDate': '2025-05-01',
        'status': 'PENDING',
        'total': Decimal('99.99'),
        'items': [
            {'productId': 'PROD001', 'qty': 2, 'price': Decimal('49.99')}
        ]
    },
    ConditionExpression='attribute_not_exists(orderId)'  # Prevents overwrite
)

# GetItem
response = table.get_item(
    Key={
        'customerId': 'CUST001',
        'orderId': 'ORD-001-2025'
    },
    ConsistentRead=True  # Strongly consistent read
)
order = response.get('Item')

# Query — all orders for a customer
response = table.query(
    KeyConditionExpression=Key('customerId').eq('CUST001'),
    FilterExpression=Attr('status').eq('PENDING'),
    ScanIndexForward=False,  # Descending order by SK
    Limit=10
)

# UpdateItem — conditional update
table.update_item(
    Key={'customerId': 'CUST001', 'orderId': 'ORD-001-2025'},
    UpdateExpression='SET #s = :new_status, updatedAt = :ts',
    ConditionExpression='#s = :current_status',
    ExpressionAttributeNames={'#s': 'status'},
    ExpressionAttributeValues={
        ':new_status': 'SHIPPED',
        ':current_status': 'PENDING',
        ':ts': '2025-05-02T10:00:00Z'
    }
)

# TransactWrite — atomic multi-table operations
dynamodb.meta.client.transact_write_items(
    TransactItems=[
        {
            'Update': {
                'TableName': 'Orders',
                'Key': {'customerId': {'S': 'CUST001'}, 'orderId': {'S': 'ORD-001'}},
                'UpdateExpression': 'SET #s = :shipped',
                'ExpressionAttributeNames': {'#s': 'status'},
                'ExpressionAttributeValues': {':shipped': {'S': 'SHIPPED'}}
            }
        },
        {
            'Put': {
                'TableName': 'Shipments',
                'Item': {'shipmentId': {'S': 'SHIP-001'}, 'orderId': {'S': 'ORD-001'}},
                'ConditionExpression': 'attribute_not_exists(shipmentId)'
            }
        }
    ]
)
```

### DynamoDB Global Tables
```bash
# Create Global Table (Multi-Region, Multi-Active)
aws dynamodb create-table \
  --table-name GlobalOrders \
  --attribute-definitions AttributeName=pk,AttributeType=S AttributeName=sk,AttributeType=S \
  --key-schema AttributeName=pk,KeyType=HASH AttributeName=sk,KeyType=RANGE \
  --billing-mode PAY_PER_REQUEST \
  --table-class STANDARD \
  --region us-east-1

# Add replica to another region
aws dynamodb update-table \
  --table-name GlobalOrders \
  --replica-updates '[{"Create":{"RegionName":"eu-west-1"}},{"Create":{"RegionName":"ap-southeast-1"}}]' \
  --region us-east-1
```

### DynamoDB Best Practices for SysOps
1. **Design for single-table** — fewer tables = less cost and complexity
2. **Choose a good partition key** — high cardinality prevents hot partitions
3. **Use On-Demand** for unpredictable workloads; Provisioned for stable
4. **Enable PITR** for all production tables
5. **Use TTL** to automatically expire old items (no cost for deletion)
6. **Avoid scans** — always query via partition key or GSI

```bash
# Enable TTL to auto-expire items
aws dynamodb update-time-to-live \
  --table-name Sessions \
  --time-to-live-specification Enabled=true,AttributeName=expiresAt
```

---

## 6.7 Amazon ElastiCache

ElastiCache provides managed **in-memory caching** to reduce database load and improve application performance.

### Redis vs Memcached

| Feature | Redis | Memcached |
|---------|-------|----------|
| Persistence | Yes (RDB/AOF) | No |
| Data structures | Strings, Lists, Sets, Sorted Sets, Hashes | Strings only |
| Replication | Yes (cluster, replica) | No |
| Pub/Sub | Yes | No |
| Lua scripting | Yes | No |
| Multi-thread | No (single-threaded) | Yes |
| Backup/restore | Yes | No |
| Use case | Caching + sessions + queues + pub-sub | Simple caching |

**Always choose Redis** unless you need extreme multi-threaded performance with simple key-value.

### ElastiCache Redis Setup
```bash
# Create Redis cluster (Cluster Mode Disabled — simple)
aws elasticache create-replication-group \
  --replication-group-id prod-redis \
  --replication-group-description "Production Redis cluster" \
  --num-cache-clusters 2 \
  --cache-node-type cache.r6g.large \
  --engine redis \
  --engine-version 7.0 \
  --cache-subnet-group-name redis-subnet-group \
  --security-group-ids sg-redis-sg \
  --at-rest-encryption-enabled \
  --transit-encryption-enabled \
  --auth-token "YourStrongAuthToken123!" \
  --automatic-failover-enabled \
  --multi-az-enabled \
  --snapshot-retention-limit 7 \
  --preferred-snapshot-window "03:00-04:00"
```

### Common Caching Patterns
```python
import redis
import json
from datetime import timedelta

r = redis.Redis(
    host='prod-redis.xxxxx.ng.0001.use1.cache.amazonaws.com',
    port=6380,
    ssl=True,
    password='YourStrongAuthToken123!',
    decode_responses=True
)

# Cache-Aside (Lazy Loading) — most common
def get_user(user_id: str):
    cache_key = f"user:{user_id}"
    
    # Try cache first
    cached = r.get(cache_key)
    if cached:
        return json.loads(cached)
    
    # Cache miss — fetch from DB
    user = db.query(f"SELECT * FROM users WHERE id = '{user_id}'")
    
    # Store in cache with TTL
    r.setex(cache_key, timedelta(hours=1), json.dumps(user))
    
    return user

# Write-Through — update cache on every write
def update_user(user_id: str, data: dict):
    # Update DB
    db.execute("UPDATE users SET name = %s WHERE id = %s", (data['name'], user_id))
    
    # Update cache immediately
    cache_key = f"user:{user_id}"
    r.setex(cache_key, timedelta(hours=1), json.dumps(data))

# Session management
def create_session(user_id: str, session_data: dict) -> str:
    import secrets
    session_id = secrets.token_urlsafe(32)
    r.setex(
        f"session:{session_id}",
        timedelta(hours=24),
        json.dumps({**session_data, 'userId': user_id})
    )
    return session_id

def get_session(session_id: str) -> dict:
    data = r.get(f"session:{session_id}")
    return json.loads(data) if data else None

# Distributed lock (prevent race conditions)
def acquire_lock(resource: str, ttl_seconds: int = 30) -> bool:
    lock_key = f"lock:{resource}"
    # SET NX (set if not exists) + EX (expire)
    return r.set(lock_key, '1', nx=True, ex=ttl_seconds)

def release_lock(resource: str):
    r.delete(f"lock:{resource}")
```

---

## 6.8 RDS Proxy

RDS Proxy manages connection pooling between applications and RDS/Aurora:

```
Lambda (100 concurrent) ──► RDS Proxy ──► RDS (10 DB connections)
(100 connections)           (pools)       (not overwhelmed)
```

**Benefits:**
- Reduces DB connections (critical for Lambda)
- Faster failover (RDS Proxy maintains connections during failover)
- IAM authentication support
- Secrets Manager integration

```bash
# Create RDS Proxy
aws rds create-db-proxy \
  --db-proxy-name prod-postgres-proxy \
  --engine-family POSTGRESQL \
  --auth '[{
    "AuthScheme": "SECRETS",
    "SecretArn": "arn:aws:secretsmanager:us-east-1:123456789012:secret:prod/postgres/password",
    "IAMAuth": "REQUIRED"
  }]' \
  --role-arn arn:aws:iam::123456789012:role/RDSProxyRole \
  --vpc-subnet-ids subnet-private-a subnet-private-b subnet-private-c \
  --vpc-security-group-ids sg-db-sg \
  --require-tls

# Register target (the RDS instance)
aws rds register-db-proxy-targets \
  --db-proxy-name prod-postgres-proxy \
  --db-instance-identifiers prod-postgres
```

---

## 6.9 Real-World Project: Highly Available Database Architecture

### Architecture for SaaS Application

```
┌─────────────────── us-east-1 ─────────────────────┐
│                                                    │
│  App Tier (ECS Fargate)                           │
│  ↓                                                │
│  RDS Proxy (connection pooling)                   │
│  ↓                                                │
│  Aurora PostgreSQL Cluster                        │
│  ├── Writer (db.r6g.2xlarge) - AZ-a              │
│  ├── Reader 1 (db.r6g.xlarge) - AZ-b             │
│  └── Reader 2 (db.r6g.xlarge) - AZ-c             │
│                                                    │
│  ElastiCache Redis (cache.r6g.large)              │
│  ├── Primary - AZ-a                               │
│  └── Replica - AZ-b                               │
│                                                    │
│  DynamoDB (sessions, events, feature flags)       │
└────────────────────────────────────────────────────┘
                        ↕ (Aurora Global)
┌─────────────────── us-west-2 ─────────────────────┐
│  Aurora Secondary Cluster (read-only unless failed)│
└────────────────────────────────────────────────────┘
```

### CloudFormation Template (Aurora)
```yaml
AuroraCluster:
  Type: AWS::RDS::DBCluster
  DeletionPolicy: Snapshot
  UpdateReplacePolicy: Snapshot
  Properties:
    Engine: aurora-postgresql
    EngineVersion: '15.3'
    MasterUsername: dbadmin
    ManageMasterUserPassword: true    # Automatic Secrets Manager rotation
    DatabaseName: appdb
    DBSubnetGroupName: !Ref DBSubnetGroup
    VpcSecurityGroupIds:
      - !Ref DBSecurityGroup
    StorageEncrypted: true
    KmsKeyId: !Ref DBKey
    BackupRetentionPeriod: 14
    DeletionProtection: true
    EnableCloudwatchLogsExports:
      - postgresql
    ServerlessV2ScalingConfiguration:
      MinCapacity: 0.5
      MaxCapacity: 16
    Tags:
      - Key: Environment
        Value: production

AuroraWriterInstance:
  Type: AWS::RDS::DBInstance
  Properties:
    DBClusterIdentifier: !Ref AuroraCluster
    DBInstanceClass: db.serverless
    Engine: aurora-postgresql
    PerformanceInsightsEnabled: true
    PerformanceInsightsRetentionPeriod: 7
    EnablePerformanceInsights: true
    AutoMinorVersionUpgrade: true
    Tags:
      - Key: Role
        Value: writer
```

---

## 6.10 Practice Questions (SysOps Exam Level)

**Q1:** Your RDS MySQL database is experiencing slow read performance due to high read traffic. The write traffic is normal. What is the BEST solution?

**A:** Create **Read Replicas** — up to 5 for MySQL. Configure the application to send read queries to the read replica endpoint and write queries to the primary endpoint. Use Route 53 weighted routing or application-level connection management to distribute read load.

---

**Q2:** An RDS instance is in the us-east-1 region. A disaster strikes the entire region. What should you have set up in advance for recovery?

**A:**
1. **Cross-region Read Replica** in us-west-2 (or another region)
2. **Automated backup copy** to another region
3. In a disaster: promote the cross-region replica to a standalone DB (takes some time for the promotion)
4. Update application connection strings (or use Route 53 failover)

The cross-region replica allows RPO of minutes (replication lag). RTO = time to promote + application switchover.

---

**Q3:** A DynamoDB table has hot partitions because all writes go to the same partition key (like `date=2025-05-01`). How do you fix this?

**A:**
1. **Add a random suffix/prefix** to partition key: `2025-05-01#1`, `2025-05-01#2`, ..., `2025-05-01#10`
2. Distribute writes evenly across the shards
3. On read: query all 10 shards and aggregate
4. Or redesign the data model to use a better high-cardinality partition key (e.g., userId, itemId)

---

**Q4:** An application uses ElastiCache Redis for session management. A Redis node fails. What happens to user sessions?

**A:**
- With **Cluster Mode Disabled, Multi-AZ**: automatic failover to replica within seconds. Session data is preserved (asynchronous replication — small window of data loss possible).
- With **Cluster Mode Enabled**: only the affected shard's data is impacted.
- For critical session data: use **AOF persistence** (append-only file) with Redis to reduce data loss, or store sessions in DynamoDB instead.

---

**Q5:** You need to encrypt an existing unencrypted RDS database. The database is currently live. What is the process with minimum downtime?

**A:**
1. Create an encrypted **read replica** of the unencrypted DB
2. Wait for replica to be in sync (monitoring replication lag)
3. During a maintenance window: promote the encrypted read replica
4. Update application connection string to new endpoint
5. Verify application connects successfully
6. Delete old unencrypted instance

**Note:** You cannot enable encryption on a running unencrypted DB. The snapshot copy + restore approach also works but has more downtime.

---

## Key Database Terms for Exam

| Term | Definition |
|------|-----------|
| RDS | Managed relational DB (MySQL, PostgreSQL, Oracle, SQL Server) |
| Multi-AZ | HA with synchronous standby for automatic failover |
| Read Replica | Asynchronous copy for read scaling |
| PITR | Point-in-Time Recovery — restore to any second |
| Aurora | AWS cloud-native DB, 5x MySQL, 3x PostgreSQL performance |
| Aurora Serverless v2 | Auto-scales Aurora compute capacity |
| Aurora Global | Multi-region Aurora with <1s replication lag |
| DynamoDB | Serverless NoSQL DB, millisecond at any scale |
| GSI | Global Secondary Index — additional access pattern |
| RCU | Read Capacity Unit — 4 KB strongly consistent read |
| WCU | Write Capacity Unit — 1 KB write |
| PITR | DynamoDB Point-in-Time Recovery |
| TTL | Time-to-Live — auto-expire DynamoDB items |
| ElastiCache | Managed in-memory caching (Redis, Memcached) |
| RDS Proxy | Connection pooling for RDS/Aurora |
| Backtrack | Aurora feature: undo DB changes without restore |
