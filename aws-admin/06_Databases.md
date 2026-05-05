# Chapter 6: Databases — RDS, Aurora, DynamoDB, ElastiCache & Redshift
## Managed Database Services on AWS

---

## 6.1 Database Services Overview

```
┌────────────────────────────────────────────────────────────────┐
│                   AWS DATABASE SERVICES                        │
├──────────────────────┬─────────────────────────────────────────┤
│ RELATIONAL (SQL)     │ RDS (MySQL, PostgreSQL, MariaDB,         │
│                      │ Oracle, SQL Server)                     │
│                      │ Aurora (MySQL/PostgreSQL-compatible)     │
│                      │ Redshift (data warehouse)               │
├──────────────────────┼─────────────────────────────────────────┤
│ NON-RELATIONAL       │ DynamoDB (key-value + document)         │
│ (NoSQL)              │ DocumentDB (MongoDB-compatible)         │
│                      │ Neptune (graph database)                │
│                      │ Keyspaces (Cassandra-compatible)        │
├──────────────────────┼─────────────────────────────────────────┤
│ IN-MEMORY CACHE      │ ElastiCache (Redis or Memcached)        │
│                      │ MemoryDB for Redis                      │
├──────────────────────┼─────────────────────────────────────────┤
│ TIME SERIES          │ Timestream                              │
├──────────────────────┼─────────────────────────────────────────┤
│ LEDGER               │ QLDB (immutable transaction log)        │
└──────────────────────┴─────────────────────────────────────────┘
```

---

## 6.2 RDS — Relational Database Service

RDS is managed SQL databases — AWS handles patching, backups, failover.

### Supported Engines

- **PostgreSQL** (most popular for new projects)
- **MySQL / MariaDB**
- **Oracle** (bring your own license or license included)
- **SQL Server** (license included or BYOL)
- **Aurora** (MySQL or PostgreSQL compatible, AWS-built)

### Key Features

```
┌──────────────────────────────────────────────────────────┐
│                   RDS KEY FEATURES                       │
│                                                          │
│  Automated Backups      → daily snapshots + transaction  │
│                           logs, restore to any point    │
│                           in time (PITR)                │
│                                                          │
│  Multi-AZ Deployment    → synchronous standby in        │
│                           another AZ, auto-failover     │
│                           (~30–60s downtime)            │
│                                                          │
│  Read Replicas          → async copy for read scaling   │
│                           up to 15 replicas             │
│                           can promote to standalone     │
│                                                          │
│  Encryption             → at rest (KMS) and in transit  │
│                           (SSL/TLS)                     │
│                                                          │
│  Maintenance Window     → controlled patch window       │
└──────────────────────────────────────────────────────────┘
```

### Creating an RDS Instance

```bash
# Create DB subnet group (spans at least 2 AZs)
aws rds create-db-subnet-group \
  --db-subnet-group-name my-db-subnet-group \
  --db-subnet-group-description "DB subnet group" \
  --subnet-ids subnet-0abc subnet-0def

# Create PostgreSQL instance
aws rds create-db-instance \
  --db-instance-identifier my-postgres \
  --db-instance-class db.t3.medium \
  --engine postgres \
  --engine-version 15.4 \
  --master-username admin \
  --master-user-password "SecurePass123!" \
  --allocated-storage 20 \
  --storage-type gp3 \
  --storage-encrypted \
  --db-subnet-group-name my-db-subnet-group \
  --vpc-security-group-ids sg-0abc123 \
  --backup-retention-period 7 \
  --preferred-backup-window "03:00-04:00" \
  --preferred-maintenance-window "Mon:04:00-Mon:05:00" \
  --multi-az \
  --deletion-protection \
  --tags Key=Environment,Value=prod

# Create read replica
aws rds create-db-instance-read-replica \
  --db-instance-identifier my-postgres-replica \
  --source-db-instance-identifier my-postgres \
  --db-instance-class db.t3.medium

# Take manual snapshot
aws rds create-db-snapshot \
  --db-instance-identifier my-postgres \
  --db-snapshot-identifier my-postgres-snapshot-2024-01-15

# Restore from snapshot
aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier my-postgres-restored \
  --db-snapshot-identifier my-postgres-snapshot-2024-01-15

# Point-in-time restore (to a specific second)
aws rds restore-db-instance-to-point-in-time \
  --source-db-instance-identifier my-postgres \
  --target-db-instance-identifier my-postgres-pitr \
  --restore-time 2024-01-15T12:30:00Z
```

### Connecting to RDS

```python
# In Python (FastAPI / Django)
import psycopg2

conn = psycopg2.connect(
    host="my-postgres.abc123.us-east-1.rds.amazonaws.com",
    port=5432,
    database="myapp",
    user="admin",
    password="SecurePass123!",    # Store in Secrets Manager in production!
    sslmode="require"             # Always use SSL
)

# Better: use Secrets Manager to retrieve password
import boto3, json

def get_db_credentials():
    client = boto3.client("secretsmanager", region_name="us-east-1")
    secret = client.get_secret_value(SecretId="myapp/db/credentials")
    return json.loads(secret["SecretString"])

creds = get_db_credentials()
# creds = {"host": "...", "port": 5432, "username": "admin", "password": "..."}
```

### Multi-AZ vs Read Replicas

```
Multi-AZ:
┌──────────────────────────────────────────────────────┐
│  Primary (AZ-1a) ──sync──► Standby (AZ-1b)          │
│                                                      │
│  Purpose: HIGH AVAILABILITY (not read scaling)       │
│  Failover: automatic, ~30-60 seconds                 │
│  Same endpoint URL — DNS flips automatically         │
│  Standby cannot be read from                         │
└──────────────────────────────────────────────────────┘

Read Replicas:
┌──────────────────────────────────────────────────────┐
│  Primary ──async──► Replica 1 (same AZ)              │
│           ──async──► Replica 2 (different AZ)        │
│           ──async──► Replica 3 (different region)    │
│                                                      │
│  Purpose: READ SCALING                               │
│  Each replica has its own DNS endpoint               │
│  Application must route reads to replica endpoint    │
│  Can promote replica to standalone DB                │
└──────────────────────────────────────────────────────┘
```

---

## 6.3 Aurora — AWS's Cloud-Native Database

Aurora is purpose-built for the cloud — 5× faster than MySQL, 3× faster than PostgreSQL, automatically replicates to 6 copies across 3 AZs.

```
┌──────────────────────────────────────────────────────────┐
│               AURORA ARCHITECTURE                        │
│                                                          │
│  Writer Instance ──────────────────────────────┐         │
│  (one primary)                                 │         │
│                                                │         │
│  Reader Instance 1  Reader Instance 2  ...     │         │
│  (up to 15 readers)                            │         │
│                                                │         │
│         Shared Cluster Volume (6 copies)        │         │
│  ┌─── AZ-1 ──┐  ┌─── AZ-2 ──┐  ┌─── AZ-3 ──┐ │         │
│  │  2 copies │  │  2 copies │  │  2 copies │ │         │
│  └───────────┘  └───────────┘  └───────────┘ │         │
└──────────────────────────────────────────────────────────┘
```

**Aurora Serverless v2:** Automatically scales capacity from minimum to maximum instantly — no pre-provisioned instances. Pay per ACU-second. Ideal for unpredictable workloads.

```bash
# Create Aurora PostgreSQL cluster
aws rds create-db-cluster \
  --db-cluster-identifier my-aurora-cluster \
  --engine aurora-postgresql \
  --engine-version 15.4 \
  --master-username admin \
  --master-user-password "SecurePass123!" \
  --db-subnet-group-name my-db-subnet-group \
  --vpc-security-group-ids sg-0abc123 \
  --storage-encrypted \
  --backup-retention-period 7

# Add a writer instance to the cluster
aws rds create-db-instance \
  --db-instance-identifier my-aurora-writer \
  --db-instance-class db.r6g.large \
  --engine aurora-postgresql \
  --db-cluster-identifier my-aurora-cluster

# Add a reader instance
aws rds create-db-instance \
  --db-instance-identifier my-aurora-reader-1 \
  --db-instance-class db.r6g.large \
  --engine aurora-postgresql \
  --db-cluster-identifier my-aurora-cluster

# Aurora has two endpoints:
# Writer: my-aurora-cluster.cluster-abc.us-east-1.rds.amazonaws.com
# Reader: my-aurora-cluster.cluster-ro-abc.us-east-1.rds.amazonaws.com
```

---

## 6.4 DynamoDB — NoSQL Key-Value + Document DB

DynamoDB is a fully managed, serverless NoSQL database. Single-digit millisecond latency at any scale.

### Core Concepts

```
┌──────────────────────────────────────────────────────────┐
│               DYNAMODB CONCEPTS                          │
│                                                          │
│  Table       → Collection of items (like a table/coll.) │
│  Item        → A single record (like a row/document)    │
│  Attribute   → Field within an item                     │
│                                                          │
│  Primary Key: TWO options:                               │
│    Partition Key only (simple PK)                        │
│    Partition Key + Sort Key (composite PK)               │
│                                                          │
│  Access Patterns:                                        │
│    GetItem     → get by exact PK                        │
│    Query       → get all items with same PK             │
│    Scan        → scan entire table (avoid in prod!)     │
│    BatchGet    → multiple GetItem in one call           │
│                                                          │
│  GSI (Global Secondary Index) → query on non-PK fields  │
│  LSI (Local Secondary Index)  → sort on different attr  │
└──────────────────────────────────────────────────────────┘
```

### Creating a DynamoDB Table

```bash
# Users table with email as partition key
aws dynamodb create-table \
  --table-name users \
  --attribute-definitions \
    AttributeName=user_id,AttributeType=S \
    AttributeName=email,AttributeType=S \
  --key-schema \
    AttributeName=user_id,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --global-secondary-indexes '[{
    "IndexName": "email-index",
    "KeySchema": [{"AttributeName": "email", "KeyType": "HASH"}],
    "Projection": {"ProjectionType": "ALL"}
  }]' \
  --tags Key=Environment,Value=prod

# Orders table with composite key
aws dynamodb create-table \
  --table-name orders \
  --attribute-definitions \
    AttributeName=user_id,AttributeType=S \
    AttributeName=order_id,AttributeType=S \
    AttributeName=created_at,AttributeType=S \
  --key-schema \
    AttributeName=user_id,KeyType=HASH \
    AttributeName=order_id,KeyType=RANGE \
  --billing-mode PAY_PER_REQUEST \
  --local-secondary-indexes '[{
    "IndexName": "created-at-index",
    "KeySchema": [
      {"AttributeName": "user_id", "KeyType": "HASH"},
      {"AttributeName": "created_at", "KeyType": "RANGE"}
    ],
    "Projection": {"ProjectionType": "ALL"}
  }]'
```

### DynamoDB CRUD in Python

```python
import boto3
from boto3.dynamodb.conditions import Key, Attr

dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
table = dynamodb.Table("users")


# ── PUT (create or replace) ────────────────────────────────────
table.put_item(Item={
    "user_id": "user-123",
    "email": "john@example.com",
    "name": "John Doe",
    "age": 30,
    "active": True
})

# ── GET ────────────────────────────────────────────────────────
response = table.get_item(Key={"user_id": "user-123"})
user = response.get("Item")

# ── UPDATE (atomic update) ────────────────────────────────────
table.update_item(
    Key={"user_id": "user-123"},
    UpdateExpression="SET #n = :name, age = :age ADD login_count :one",
    ExpressionAttributeNames={"#n": "name"},  # 'name' is reserved word
    ExpressionAttributeValues={
        ":name": "John Smith",
        ":age": 31,
        ":one": 1
    }
)

# ── DELETE ────────────────────────────────────────────────────
table.delete_item(
    Key={"user_id": "user-123"},
    ConditionExpression="attribute_exists(user_id)"  # Safety check
)

# ── QUERY (efficient — uses index) ────────────────────────────
# All orders for a user, sorted by date (on orders table)
orders_table = dynamodb.Table("orders")
response = orders_table.query(
    KeyConditionExpression=Key("user_id").eq("user-123"),
    ScanIndexForward=False,  # Newest first
    Limit=10
)
orders = response["Items"]

# Query GSI (by email)
response = table.query(
    IndexName="email-index",
    KeyConditionExpression=Key("email").eq("john@example.com")
)

# ── SCAN (avoid in prod — reads entire table) ─────────────────
response = table.scan(
    FilterExpression=Attr("age").gt(25) & Attr("active").eq(True)
)

# ── BATCH WRITE ────────────────────────────────────────────────
with table.batch_writer() as batch:
    for user in users_list:
        batch.put_item(Item=user)
```

### DynamoDB Best Practices

```
Design for your access patterns FIRST:
1. Identify all the ways your app reads/writes data
2. Design primary keys and GSIs to support those patterns
3. Denormalise data (duplicate is OK — reads are cheap)

Key best practices:
• Choose partition key with high cardinality (many unique values)
• Avoid "hot" partition keys (e.g., date as PK = all writes to one shard)
• Use on-demand billing for unpredictable traffic
• Use provisioned + Auto Scaling for steady, predictable traffic
• Enable DynamoDB Streams for change data capture
• Enable Point-in-Time Recovery (PITR)
• Use TTL to auto-expire old records (e.g., sessions, logs)
```

```bash
# Enable TTL on a table (set 'expires_at' attribute as Unix timestamp)
aws dynamodb update-time-to-live \
  --table-name sessions \
  --time-to-live-specification Enabled=true,AttributeName=expires_at

# Enable PITR
aws dynamodb update-continuous-backups \
  --table-name users \
  --point-in-time-recovery-specification PointInTimeRecoveryEnabled=true
```

---

## 6.5 ElastiCache — In-Memory Caching

ElastiCache provides managed Redis or Memcached — for caching database results, session storage, real-time leaderboards.

```
Without Cache:                    With Cache (Cache-Aside):
──────────────                    ──────────────────────────
Request → App → DB                Request → App → Check Cache
         ↑ 50ms per query                         │
                                            Hit?  │  Miss?
                                             ↓         ↓
                                          Return    Query DB
                                          Cached    Store in
                                          Result    Cache
                                          (1ms)     (50ms, once)
```

### Redis vs Memcached

| Feature | Redis | Memcached |
|---------|-------|-----------|
| Data structures | Strings, hashes, lists, sets, sorted sets | Strings only |
| Persistence | Yes (RDB + AOF) | No |
| Replication | Yes (read replicas) | No |
| Pub/Sub | Yes | No |
| Transactions | Yes (MULTI/EXEC) | No |
| Cluster mode | Yes | Yes |
| **Choose** | **Almost always** | Simple cache, multi-threading |

### Setting Up ElastiCache Redis

```bash
# Create subnet group
aws elasticache create-cache-subnet-group \
  --cache-subnet-group-name redis-subnet-group \
  --cache-subnet-group-description "Redis subnet group" \
  --subnet-ids subnet-0abc subnet-0def

# Create Redis cluster (single node)
aws elasticache create-cache-cluster \
  --cache-cluster-id my-redis \
  --engine redis \
  --cache-node-type cache.t3.medium \
  --num-cache-nodes 1 \
  --cache-subnet-group-name redis-subnet-group \
  --security-group-ids sg-0abc123

# Create Redis with replication (prod)
aws elasticache create-replication-group \
  --replication-group-id my-redis-prod \
  --description "Production Redis" \
  --num-cache-clusters 3 \
  --cache-node-type cache.r6g.large \
  --engine redis \
  --at-rest-encryption-enabled \
  --transit-encryption-enabled \
  --auth-token "SecureAuthToken123!" \
  --cache-subnet-group-name redis-subnet-group \
  --security-group-ids sg-0abc123
```

```python
# Using Redis with FastAPI
import redis.asyncio as aioredis
import json
from fastapi import FastAPI

app = FastAPI()

# Connect (from EC2/ECS — private endpoint)
redis_client = aioredis.Redis(
    host="my-redis.abc123.cfg.use1.cache.amazonaws.com",
    port=6379,
    ssl=True,
    password="SecureAuthToken123!",
    decode_responses=True
)

# Cache-aside pattern
async def get_user(user_id: str):
    cache_key = f"user:{user_id}"
    
    # Check cache first
    cached = await redis_client.get(cache_key)
    if cached:
        return json.loads(cached)
    
    # Cache miss — query database
    user = await db.get_user(user_id)
    
    # Store in cache for 5 minutes
    await redis_client.setex(cache_key, 300, json.dumps(user))
    
    return user

# Session storage
async def create_session(user_id: str, session_token: str):
    await redis_client.setex(
        f"session:{session_token}",
        3600,    # 1 hour TTL
        user_id
    )

# Rate limiting
async def check_rate_limit(ip: str, limit: int = 100):
    key = f"rate:{ip}:{int(time.time() // 60)}"  # Per minute
    count = await redis_client.incr(key)
    await redis_client.expire(key, 60)
    return count <= limit
```

---

## 6.6 Redshift — Data Warehouse

Redshift is for analytics and reporting on large datasets (petabytes). Not for transactional (OLTP) workloads.

```
OLTP vs OLAP:
┌──────────────────────────────────────────────────────────┐
│  OLTP (RDS/Aurora)        OLAP (Redshift)                │
│  ────────────────          ──────────────                │
│  Many small reads/writes  Few large analytical queries   │
│  Normalised data          Denormalised (star schema)     │
│  Row-based storage        Columnar storage               │
│  Milliseconds             Seconds to minutes             │
│  e.g., order creation     e.g., "total sales by region   │
│                                  for last 3 years"       │
└──────────────────────────────────────────────────────────┘
```

```bash
# Create Redshift Serverless (simplest — no cluster management)
aws redshift-serverless create-namespace \
  --namespace-name my-analytics \
  --admin-username admin \
  --admin-user-password "SecurePass123!" \
  --db-name analytics

aws redshift-serverless create-workgroup \
  --workgroup-name my-workgroup \
  --namespace-name my-analytics \
  --base-capacity 8 \   # 8 RPUs (Redshift Processing Units)
  --subnet-ids subnet-0abc subnet-0def \
  --security-group-ids sg-0abc123
```

---

## 6.7 Database Selection Guide

```
┌──────────────────────────────────────────────────────────┐
│              WHEN TO USE WHICH DATABASE                  │
├────────────────────────┬─────────────────────────────────┤
│ PostgreSQL RDS         │ General-purpose relational data  │
│                        │ Complex queries, ACID needed     │
│                        │ Team knows SQL well              │
├────────────────────────┼─────────────────────────────────┤
│ Aurora                 │ Same as RDS but need higher      │
│                        │ availability + read scaling      │
│                        │ Serverless v2 for variable load  │
├────────────────────────┼─────────────────────────────────┤
│ DynamoDB               │ Simple access patterns           │
│                        │ Massive scale, low latency       │
│                        │ Serverless / Lambda compatible   │
│                        │ Session store, shopping cart     │
├────────────────────────┼─────────────────────────────────┤
│ ElastiCache Redis      │ Caching database results         │
│                        │ Session storage                  │
│                        │ Real-time leaderboards           │
│                        │ Pub/Sub messaging                │
├────────────────────────┼─────────────────────────────────┤
│ Redshift               │ BI/analytics workloads           │
│                        │ Data warehouse, reporting        │
│                        │ S3 data lake + SQL queries       │
└────────────────────────┴─────────────────────────────────┘
```

---

## 6.8 Interview Questions

**Q: What is the difference between RDS Multi-AZ and Read Replicas?**
> Multi-AZ is for high availability — a synchronous standby in a different AZ automatically takes over if the primary fails (DNS flips in ~30-60 seconds). The standby cannot serve reads. Read Replicas are for read scaling — async copies that can serve SELECT queries, reducing load on the primary. They can also be promoted to a standalone database for disaster recovery, or used in a different region for cross-region DR.

**Q: When would you choose DynamoDB over RDS?**
> DynamoDB is ideal when: (1) access patterns are simple and well-defined (get by key, query by partition), (2) you need millisecond latency at massive scale (millions of requests/second), (3) the application is serverless and needs a DB that scales to zero, (4) you don't need complex joins or ACID transactions across many tables. RDS is better when you need complex queries, joins, ad-hoc SQL, or strong consistency across many tables.

**Q: What is ElastiCache used for?**
> Primarily for reducing database load through caching (cache-aside pattern), storing user sessions (faster than hitting DB on every request), and rate limiting. Redis specifically also supports pub/sub messaging, real-time leaderboards (sorted sets), and distributed locks. It reduces database latency from 10-50ms to under 1ms for cached data.
