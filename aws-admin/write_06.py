
content = r"""# Chapter 6: Databases — RDS, Aurora, DynamoDB & ElastiCache
## (How AWS Manages Your Data — From SQL to NoSQL)

---

## 6.1 Database Types — Choosing the Right Database

### The Big Picture

Not all data is the same, and not all databases work the same way. Choosing the right database type is one of the most important architecture decisions.

**Analogy:** Think about different ways to organize information:
- A spreadsheet (SQL) is great for structured data with rows and columns — customer orders, financial records
- A filing cabinet (Document DB) is great for varied documents — customer profiles that have different fields
- A phone book (Key-Value) is great for simple lookups — "what is the session data for user 12345?"
- A social network map (Graph DB) is great for relationships — "who are friends of friends of Alice?"

### SQL vs NoSQL

**Relational (SQL) Databases:**
```
What they are: Data stored in tables with rows and columns.
               Tables are related via foreign keys.

Example - E-commerce database:
  customers table:
    id | name      | email           | created_at
    1  | Alice     | alice@email.com | 2025-01-15
    2  | Bob       | bob@email.com   | 2025-01-16

  orders table:
    id | customer_id | product     | amount | date
    1  | 1           | Laptop      | 999.99 | 2025-01-20
    2  | 1           | Mouse       | 29.99  | 2025-01-21
    3  | 2           | Keyboard    | 79.99  | 2025-01-22

  SELECT c.name, o.product, o.amount
  FROM customers c
  JOIN orders o ON c.id = o.customer_id
  WHERE c.id = 1;

Strengths:
  - ACID transactions (Atomicity, Consistency, Isolation, Durability)
  - Complex queries with JOINs across multiple tables
  - Data integrity enforced by schema
  - Mature, well-understood technology

Weaknesses:
  - Scaling horizontally (adding more servers) is complex
  - Schema changes on large tables can be slow
  - Not ideal for rapidly changing or highly varied data structures

AWS Services: RDS (MySQL, PostgreSQL, SQL Server, Oracle, MariaDB), Aurora
```

**Non-Relational (NoSQL) Databases:**
```
What they are: Data NOT stored in rigid row/column tables.
               Various models: key-value, document, graph, time-series.

Example - User session data (key-value):
  {
    "session_id": "abc123",
    "user_id": 12345,
    "cart": ["laptop", "mouse"],
    "last_active": "2025-01-20T14:30:00Z",
    "preferences": {"theme": "dark", "language": "en"}
  }

Strengths:
  - Scales horizontally easily (just add more nodes)
  - Handles highly variable data structures
  - Often extremely fast for simple lookups by key
  - Built for internet-scale (billions of records)

Weaknesses:
  - No complex JOINs across data types
  - Eventual consistency (not always immediately consistent)
  - Application must handle data relationships

AWS Services: DynamoDB (key-value + document), ElastiCache (in-memory key-value),
              DocumentDB (MongoDB-compatible), Neptune (graph), Timestream (time-series)
```

---

## 6.2 RDS — Relational Database Service

### What is RDS?

**RDS (Relational Database Service)** is AWS's managed relational database service. Instead of running MySQL or PostgreSQL on an EC2 instance yourself, RDS handles:

- Installing and configuring the database engine
- Automatic patching of the database software
- Automated backups (point-in-time recovery)
- Multi-AZ failover for high availability
- Read replicas for read scaling
- Monitoring via CloudWatch
- Storage auto-scaling

**What you still manage:**
- Database schema design
- Query optimization
- What data goes in and what queries run

**Supported engines:**
- **MySQL** (most common web app database)
- **PostgreSQL** (feature-rich, great for complex queries)
- **Oracle** (enterprise, expensive licensing)
- **SQL Server** (Microsoft, enterprise)
- **MariaDB** (MySQL fork, some extra features)
- **Amazon Aurora** (AWS's own high-performance MySQL/PostgreSQL compatible engine)

### RDS Multi-AZ — High Availability

**Multi-AZ** creates a standby database instance in a different AZ. If the primary fails, RDS automatically fails over to the standby.

```
Normal Operation:
  Your App → (writes + reads) → Primary RDS (AZ-1a)
                                    │ (synchronous replication)
                                    ↓
                              Standby RDS (AZ-1b)  ← always up-to-date copy

Failover (Primary fails):
  Your App → (connects to same DNS endpoint — no code change!) → Standby becomes new Primary
  
  Failover time: 60-120 seconds typically
  How app connects: Always use the RDS endpoint DNS name (never hardcode IP)
                    DNS automatically updates to point to new primary
```

```bash
# Create a Multi-AZ RDS instance
aws rds create-db-instance \
  --db-instance-identifier production-mysql \
  --db-instance-class db.t3.medium \
  --engine mysql \
  --engine-version 8.0.35 \
  --master-username admin \
  --master-user-password $(openssl rand -base64 32) \
  --db-name appdb \
  --allocated-storage 100 \
  --storage-type gp3 \
  --storage-encrypted \
  --kms-key-id arn:aws:kms:us-east-1:123456789012:key/abc123 \
  --vpc-security-group-ids sg-database-sg \
  --db-subnet-group-name my-db-subnet-group \
  --multi-az \
  --backup-retention-period 7 \
  --preferred-backup-window "03:00-04:00" \
  --preferred-maintenance-window "Sun:04:00-Sun:05:00" \
  --deletion-protection \
  --enable-cloudwatch-logs-exports '["error","general","slowquery"]'
  
# Key parameters explained:
# --multi-az              = create standby in another AZ (high availability)
# --storage-encrypted     = encrypt database at rest
# --backup-retention-period 7 = keep 7 days of automated backups
# --deletion-protection   = prevent accidental deletion
```

### RDS Read Replicas — Scaling Reads

**Read Replicas** are additional copies of your database that handle READ queries. Write operations still go to the primary. This offloads read-heavy workloads.

```
Without Read Replicas:
  App reads  → Primary RDS (overloaded)
  App writes → Primary RDS

With Read Replicas:
  App writes        → Primary RDS
  App reads (90%) → Read Replica 1 (can be in same or different region!)
  App reads (10%) → Read Replica 2

Use cases:
  - Analytics/reporting queries that would slow down production
  - BI tools (Tableau, Looker) running heavy aggregation queries
  - Geographic distribution (replica in different region serves local users faster)
  - Disaster recovery: Promote a read replica to standalone database
```

**Key differences: Multi-AZ vs Read Replicas**

| Feature | Multi-AZ | Read Replicas |
|---------|----------|---------------|
| Purpose | High Availability (HA) | Read Scaling + HA |
| Standby serves traffic? | NO — standby is passive | YES — actively serves reads |
| Replication | Synchronous | Asynchronous |
| Failover | Automatic (DNS update) | Manual (promote to primary) |
| Consistency | Always in sync | Small replication lag |
| Cross-region? | No (same region) | YES — can be in another region |

```bash
# Create a Read Replica
aws rds create-db-instance-read-replica \
  --db-instance-identifier production-mysql-read-1 \
  --source-db-instance-identifier production-mysql \
  --db-instance-class db.t3.medium \
  --availability-zone us-east-1b \
  --publicly-accessible false

# Create a cross-region Read Replica (in eu-west-1)
aws rds create-db-instance-read-replica \
  --db-instance-identifier production-mysql-eu \
  --source-db-instance-identifier arn:aws:rds:us-east-1:123456789012:db:production-mysql \
  --db-instance-class db.t3.medium \
  --region eu-west-1

# Promote Read Replica to standalone (for DR or region failover)
aws rds promote-read-replica \
  --db-instance-identifier production-mysql-eu
```

### RDS Backups — Point-in-Time Recovery

**Automated Backups:**
- Enabled by default (retention 1-35 days)
- Full daily backup + transaction logs every 5 minutes
- Can restore to any point in time within retention window
- Free storage up to 100% of database size

**Manual Snapshots:**
- You create them on demand
- Survive even after database is deleted
- Keep them as long as you want
- Good for: before major changes, end-of-quarter snapshots, compliance

```bash
# Create a manual snapshot
aws rds create-db-snapshot \
  --db-instance-identifier production-mysql \
  --db-snapshot-identifier before-migration-2025-01-20

# Restore from a specific point in time (within backup retention window)
aws rds restore-db-instance-to-point-in-time \
  --source-db-instance-identifier production-mysql \
  --target-db-instance-identifier production-mysql-restored \
  --restore-time "2025-01-20T10:00:00Z" \
  --db-instance-class db.t3.medium

# List available snapshots
aws rds describe-db-snapshots \
  --db-instance-identifier production-mysql \
  --query 'DBSnapshots[*].[DBSnapshotIdentifier,SnapshotCreateTime,Status]' \
  --output table
```

---

## 6.3 Aurora — AWS's High-Performance Database Engine

### What is Aurora?

**Amazon Aurora** is AWS's own database engine that is:
- Compatible with MySQL (can use MySQL drivers and tools)
- Compatible with PostgreSQL (can use PostgreSQL drivers and tools)
- 5x faster than standard MySQL
- 3x faster than standard PostgreSQL
- Costs 1/10th of commercial databases (Oracle, SQL Server)

**Key Aurora architecture facts:**
- Storage is separate from compute (shared storage cluster)
- Storage automatically grows from 10 GB to 128 TB in 10 GB increments
- Data written to 6 copies across 3 AZs (extremely durable)
- Can lose 2 copies and still write; lose 3 copies and still read
- Read replicas are faster to create (share same underlying storage)

```
Aurora Cluster:
  Writer Instance (AZ-1a) ──→ Shared Storage (6 copies, 3 AZs)
  Reader Instance (AZ-1b) ──→ (reads from shared storage, near-zero replication lag)
  Reader Instance (AZ-1c) ──→
```

### Aurora Serverless v2

**Aurora Serverless v2** automatically scales compute capacity up and down based on actual database load — in seconds, not minutes.

```
Traditional RDS/Aurora:
  You provision: db.r6g.2xlarge (8 vCPU, 64 GB RAM)
  Idle at 3am: still paying for full db.r6g.2xlarge
  Traffic spike at noon: might need MORE than db.r6g.2xlarge

Aurora Serverless v2:
  Configure: Min 0.5 ACUs, Max 128 ACUs
  (ACU = Aurora Capacity Unit; 1 ACU = ~2 GB RAM)
  3am low traffic: scales to 0.5 ACU (minimum, very cheap)
  12pm traffic spike: scales to 64 ACU in seconds (automatically)
  Charge: Per ACU-hour (only pay for what you use)
```

```bash
# Create Aurora Serverless v2 cluster
aws rds create-db-cluster \
  --db-cluster-identifier my-aurora-serverless \
  --engine aurora-mysql \
  --engine-version 8.0.mysql_aurora.3.04.1 \
  --master-username admin \
  --master-user-password SecurePassword123 \
  --db-subnet-group-name my-db-subnet-group \
  --vpc-security-group-ids sg-database-sg \
  --serverless-v2-scaling-configuration MinCapacity=0.5,MaxCapacity=32 \
  --backup-retention-period 7 \
  --deletion-protection

# Add a Serverless v2 writer instance to the cluster
aws rds create-db-instance \
  --db-instance-identifier my-aurora-serverless-writer \
  --db-cluster-identifier my-aurora-serverless \
  --db-instance-class db.serverless \
  --engine aurora-mysql
```

### Aurora Global Database — Cross-Region

**Aurora Global Database** allows one Aurora database to span multiple AWS regions:
- Primary region: read/write
- Secondary regions: read-only, with replication lag < 1 second
- If primary region fails, promote secondary to primary in under 1 minute

```bash
# Create Aurora Global Database
aws rds create-global-cluster \
  --global-cluster-identifier my-global-aurora \
  --engine aurora-mysql \
  --engine-version 8.0.mysql_aurora.3.04.1

# Add secondary region
aws rds create-db-cluster \
  --db-cluster-identifier my-aurora-secondary-eu \
  --engine aurora-mysql \
  --engine-version 8.0.mysql_aurora.3.04.1 \
  --global-cluster-identifier my-global-aurora \
  --db-subnet-group-name eu-db-subnet-group \
  --vpc-security-group-ids sg-eu-database-sg \
  --region eu-west-1
```

---

## 6.4 DynamoDB — Fully Managed NoSQL at Internet Scale

### What is DynamoDB?

**DynamoDB** is AWS's fully managed NoSQL database service. Key facts:
- Serverless: no servers to manage, no cluster to size
- Single-digit millisecond performance at any scale
- Scales to handle tens of millions of requests per second
- Used by Amazon.com for their shopping cart (handles Prime Day!)
- Supports ACID transactions (added in 2018)

**Analogy:** DynamoDB is like a massive dictionary. You look up data by a key, and you instantly get the value. The dictionary can have 1 entry or 100 billion entries — lookup speed is the same.

### DynamoDB Key Concepts

**Table:**
- Collection of items (like a table in SQL, but schema-flexible)
- Each item can have different attributes

**Item:**
- A single record (like a row in SQL)
- Must have the primary key attributes
- Can have any other attributes (schema-less!)
- Maximum item size: 400 KB

**Primary Key (required for every item):**

Option 1: **Simple Primary Key (Partition Key only)**
```
Partition Key: Must be unique for every item
Example: user_id

Table: users
{ "user_id": "u001", "name": "Alice", "email": "alice@example.com" }
{ "user_id": "u002", "name": "Bob", "email": "bob@example.com", "phone": "555-1234" }
  
Notice: Bob has a "phone" attribute Alice doesn't. DynamoDB allows this (schema-less)!
```

Option 2: **Composite Primary Key (Partition Key + Sort Key)**
```
Partition Key: Groups related items together
Sort Key: Orders items within the partition

Example: forum posts
Partition Key: forum_id (e.g., "programming-help")
Sort Key: timestamp (e.g., "2025-01-20T10:00:00Z")

Table: forum_posts
{ "forum_id": "programming-help", "timestamp": "2025-01-20T10:00:00Z", "title": "Python question", "author": "Alice" }
{ "forum_id": "programming-help", "timestamp": "2025-01-20T11:00:00Z", "title": "Java question",   "author": "Bob" }
{ "forum_id": "aws-help",         "timestamp": "2025-01-20T09:00:00Z", "title": "S3 question",    "author": "Carol" }

Query all posts in "programming-help" forum, ordered by time: Very fast!
```

### DynamoDB Read/Write Capacity

**Two capacity modes:**

**On-Demand Capacity:**
```
- Pay per request ($0.25 per million writes, $0.05 per million reads)
- No capacity planning needed
- Instantly handles any traffic spike
- Best for: Unpredictable traffic, new applications, dev/test
```

**Provisioned Capacity:**
```
- You specify Read Capacity Units (RCUs) and Write Capacity Units (WCUs)
- 1 RCU = 1 strongly consistent read per second (up to 4 KB)
           OR 2 eventually consistent reads per second
- 1 WCU = 1 write per second (up to 1 KB)
- Set min/max for auto-scaling
- Best for: Predictable, steady traffic; cost-optimized
```

### Working with DynamoDB

```bash
# Create a DynamoDB table with composite key
aws dynamodb create-table \
  --table-name forum_posts \
  --attribute-definitions \
    AttributeName=forum_id,AttributeType=S \
    AttributeName=timestamp,AttributeType=S \
  --key-schema \
    AttributeName=forum_id,KeyType=HASH \
    AttributeName=timestamp,KeyType=RANGE \
  --billing-mode PAY_PER_REQUEST \
  --sse-specification Enabled=true,SSEType=KMS \
  --tags Key=Environment,Value=production

# Insert an item
aws dynamodb put-item \
  --table-name forum_posts \
  --item '{
    "forum_id": {"S": "programming-help"},
    "timestamp": {"S": "2025-01-20T10:00:00Z"},
    "title": {"S": "How to use Python decorators?"},
    "author": {"S": "alice"},
    "content": {"S": "I do not understand decorators..."},
    "view_count": {"N": "0"},
    "tags": {"L": [{"S": "python"}, {"S": "beginner"}]}
  }'

# Get a specific item by primary key
aws dynamodb get-item \
  --table-name forum_posts \
  --key '{
    "forum_id": {"S": "programming-help"},
    "timestamp": {"S": "2025-01-20T10:00:00Z"}
  }'

# Query all posts in a forum, ordered by timestamp (most recent first)
aws dynamodb query \
  --table-name forum_posts \
  --key-condition-expression "forum_id = :fid AND #ts >= :start" \
  --expression-attribute-names '{"#ts": "timestamp"}' \
  --expression-attribute-values '{
    ":fid": {"S": "programming-help"},
    ":start": {"S": "2025-01-01T00:00:00Z"}
  }' \
  --scan-index-forward false \
  --limit 20

# Update an item (increment view count atomically)
aws dynamodb update-item \
  --table-name forum_posts \
  --key '{
    "forum_id": {"S": "programming-help"},
    "timestamp": {"S": "2025-01-20T10:00:00Z"}
  }' \
  --update-expression "SET view_count = view_count + :inc" \
  --expression-attribute-values '{":inc": {"N": "1"}}' \
  --return-values ALL_NEW
```

### DynamoDB Global Secondary Indexes (GSI)

A GSI lets you query by attributes OTHER than the primary key.

```
Problem: Our forum_posts table has primary key (forum_id, timestamp)
         We can efficiently query "all posts in forum X" 
         But what if we want "all posts by author Alice"?
         Without a GSI: must do a full table SCAN (slow, expensive!)
         With a GSI: create an index on "author"

GSI on forum_posts:
  GSI partition key: author
  GSI sort key: timestamp
  
  Now we can query: "all posts by alice, sorted by time" — fast!
```

```bash
# Add a GSI to an existing table
aws dynamodb update-table \
  --table-name forum_posts \
  --attribute-definitions \
    AttributeName=forum_id,AttributeType=S \
    AttributeName=timestamp,AttributeType=S \
    AttributeName=author,AttributeType=S \
  --global-secondary-index-updates '[{
    "Create": {
      "IndexName": "author-timestamp-index",
      "KeySchema": [
        {"AttributeName": "author", "KeyType": "HASH"},
        {"AttributeName": "timestamp", "KeyType": "RANGE"}
      ],
      "Projection": {"ProjectionType": "ALL"},
      "BillingMode": "PAY_PER_REQUEST"
    }
  }]'

# Query the GSI: all posts by alice
aws dynamodb query \
  --table-name forum_posts \
  --index-name author-timestamp-index \
  --key-condition-expression "author = :auth" \
  --expression-attribute-values '{":auth": {"S": "alice"}}'
```

### DynamoDB Streams + Lambda — Event-Driven Processing

```
Every change in DynamoDB table triggers an event:
  Insert → new item appears in stream
  Update → before and after images in stream
  Delete → deleted item in stream

Use with Lambda:
  DynamoDB → Stream → Lambda function → (send email, update cache, etc.)
```

```bash
# Enable DynamoDB Streams
aws dynamodb update-table \
  --table-name forum_posts \
  --stream-specification StreamEnabled=true,StreamViewType=NEW_AND_OLD_IMAGES
  
# Stream view types:
# KEYS_ONLY        — only primary key attributes
# NEW_IMAGE        — only the new item after change
# OLD_IMAGE        — only the old item before change
# NEW_AND_OLD_IMAGES — both before and after (most useful)
```

---

## 6.5 ElastiCache — In-Memory Caching

### What is ElastiCache and Why Do You Need It?

**ElastiCache** is a fully managed in-memory data store. It keeps data in RAM (not disk), making reads extremely fast — microseconds vs milliseconds from a database.

**The caching problem it solves:**

```
WITHOUT caching:
  1. User requests product page
  2. App queries RDS: SELECT * FROM products WHERE id=123
  3. RDS takes 20ms to query disk
  4. App formats response
  5. Returns to user
  
  With 10,000 requests/minute all requesting product 123:
  → RDS gets 10,000 identical queries/minute → overloaded!

WITH caching:
  1. User requests product page
  2. App checks ElastiCache: GET product:123
  3. Cache HIT → returns in 0.1ms (200x faster!)
  4. Returns to user
  
  Only the first request (cache miss) hits RDS.
  Next 9,999 requests served from cache.
  RDS load reduced by 99.99%!
```

### Redis vs Memcached

**Redis:**
```
Data types: Strings, hashes, lists, sets, sorted sets, bitmaps, HyperLogLog
Features:
  - Persistence (can save to disk, survive restarts)
  - Multi-AZ with automatic failover
  - Read replicas
  - Lua scripting
  - Pub/Sub messaging
  - Transactions (MULTI/EXEC)
  - Sorted sets (leaderboards, rate limiting)
  
Use for: Sessions, leaderboards, rate limiting, queues, pub/sub messaging
         Real-time analytics, recommendation engines

When to use Redis: When you need rich data structures, persistence, or HA
```

**Memcached:**
```
Data types: Simple key-value (strings only)
Features:
  - Multi-threaded (can use all CPU cores)
  - Simpler architecture
  - NO persistence (data lost on restart)
  - NO replication (if a node fails, data is gone)

Use for: Simple object caching where speed is the only requirement
         Large objects (Memcached nodes can be larger than Redis)

When to use Memcached: Pure caching, simplest possible use case, multi-threading needed
```

**Exam rule:** If the question mentions persistence, HA, complex data structures, sessions → Redis. If it's just "I need fast object cache" → could be either.

### Setting Up ElastiCache Redis

```bash
# Create a Redis replication group (Multi-AZ)
aws elasticache create-replication-group \
  --replication-group-id web-app-cache \
  --description "Session and object cache for web app" \
  --num-cache-clusters 3 \
  --cache-node-type cache.r6g.large \
  --engine redis \
  --engine-version 7.0 \
  --cache-subnet-group-name my-cache-subnet-group \
  --security-group-ids sg-cache-sg \
  --automatic-failover-enabled \
  --multi-az-enabled \
  --at-rest-encryption-enabled \
  --transit-encryption-enabled \
  --auth-token $(openssl rand -base64 32) \
  --snapshot-retention-limit 7

# The cluster will have:
# - 1 primary node (accepts writes)
# - 2 replica nodes (handle reads + automatic failover)
```

```python
import redis
import json
import time

# Connect to ElastiCache Redis cluster
r = redis.Redis(
    host='web-app-cache.abc123.ng.0001.use1.cache.amazonaws.com',
    port=6379,
    ssl=True,
    password='your-auth-token'
)

# Pattern 1: Cache-Aside (most common)
def get_product(product_id):
    cache_key = f"product:{product_id}"
    
    # Try cache first
    cached = r.get(cache_key)
    if cached:
        return json.loads(cached)  # Cache hit!
    
    # Cache miss - query database
    product = db.query("SELECT * FROM products WHERE id = %s", product_id)
    
    # Store in cache (expire after 1 hour)
    r.setex(cache_key, 3600, json.dumps(product))
    
    return product

# Pattern 2: Session storage
def save_session(session_id, user_data):
    r.setex(
        f"session:{session_id}",
        1800,  # 30 minutes TTL
        json.dumps(user_data)
    )

def get_session(session_id):
    data = r.get(f"session:{session_id}")
    if data:
        r.expire(f"session:{session_id}", 1800)  # Reset TTL on activity
        return json.loads(data)
    return None

# Pattern 3: Rate limiting
def check_rate_limit(user_id, limit=100):
    key = f"rate:{user_id}:{int(time.time() / 60)}"  # per minute
    current = r.incr(key)
    if current == 1:
        r.expire(key, 60)
    return current <= limit

# Pattern 4: Leaderboard (Redis Sorted Sets)
def update_score(player_id, score):
    r.zadd("game_leaderboard", {player_id: score})

def get_top_10():
    return r.zrevrange("game_leaderboard", 0, 9, withscores=True)

def get_player_rank(player_id):
    rank = r.zrevrank("game_leaderboard", player_id)
    score = r.zscore("game_leaderboard", player_id)
    return {"rank": rank + 1 if rank is not None else None, "score": score}
```

---

## 6.6 Other AWS Database Services

### DocumentDB (MongoDB-compatible)

```
What: Managed document database compatible with MongoDB 4.x driver and tools
Use when: Already using MongoDB, want managed service
          JSON document storage with rich querying
Key features: Up to 15 read replicas, 6-copy storage across 3 AZs
NOT: Actually running MongoDB code (reimplemented by AWS, mostly compatible)
```

### Neptune (Graph Database)

```
What: Managed graph database
Use when: Data has complex relationships
          Social networks, fraud detection, knowledge graphs,
          recommendation engines
Supports: Gremlin (TinkerPop) and SPARQL query languages
Key feature: Purpose-built for highly connected data
```

### Timestream (Time-Series Database)

```
What: Managed time-series database
Use when: IoT sensor data, application metrics, financial data
          Any data with a timestamp as primary dimension
Advantages: Automatically tiers old data to cheaper storage
            Built-in time-series functions (interpolation, smoothing, etc.)
            100x cheaper than relational databases for time-series data
```

### Amazon Keyspaces (Cassandra-compatible)

```
What: Managed Cassandra-compatible database
Use when: Already using Apache Cassandra, want managed service
          Wide-column store for large-scale, multi-region data
Key feature: Serverless, no capacity planning needed
```

---

## 6.7 Database Migration Service (DMS)

When migrating from an existing database to AWS, **DMS (Database Migration Service)** handles the data transfer.

```bash
# DMS supports:
# Source: Oracle, SQL Server, MySQL, PostgreSQL, SAP, MongoDB, and more
# Target: Same + Aurora, DynamoDB, Redshift, S3

# DMS migration types:
# Full load only: one-time migration (app downtime required)
# Full load + CDC: migrate then continuously replicate changes (minimal downtime)
# CDC only: already migrated, just replicate ongoing changes

# Create a replication instance
aws dms create-replication-instance \
  --replication-instance-identifier migration-instance \
  --replication-instance-class dms.t3.medium \
  --allocated-storage 50 \
  --vpc-security-group-ids sg-dms-sg \
  --replication-subnet-group-identifier my-dms-subnet-group \
  --engine-version 3.5.2 \
  --multi-az

# Create source endpoint (on-premises MySQL)
aws dms create-endpoint \
  --endpoint-identifier source-mysql \
  --endpoint-type source \
  --engine-name mysql \
  --username admin \
  --password SecurePassword \
  --server-name onprem-mysql.company.com \
  --port 3306

# Create target endpoint (RDS MySQL)
aws dms create-endpoint \
  --endpoint-identifier target-rds-mysql \
  --endpoint-type target \
  --engine-name mysql \
  --username admin \
  --password SecurePassword \
  --server-name production-mysql.abc123.us-east-1.rds.amazonaws.com \
  --port 3306

# Create and start the migration task
aws dms create-replication-task \
  --replication-task-identifier migrate-company-db \
  --source-endpoint-arn arn:aws:dms:us-east-1:123456789012:endpoint:SOURCE \
  --target-endpoint-arn arn:aws:dms:us-east-1:123456789012:endpoint:TARGET \
  --replication-instance-arn arn:aws:dms:us-east-1:123456789012:rep:INSTANCE \
  --migration-type full-load-and-cdc \
  --table-mappings '{
    "rules": [{
      "rule-type": "selection",
      "rule-id": "1",
      "rule-name": "include-all",
      "object-locator": {"schema-name": "appdb", "table-name": "%"},
      "rule-action": "include"
    }]
  }'
```

---

## 6.8 Practice Questions

**Q1:** Your RDS MySQL production database is experiencing slow performance due to read-heavy analytics queries from your BI team. The write operations must continue uninterrupted. What is the BEST solution?

- A) Upgrade to a larger RDS instance
- B) Create a Multi-AZ standby instance for the BI team
- C) Create one or more Read Replicas and point BI queries to them
- D) Create a new RDS instance and copy the data every night

**Answer: C**

Explanation: Read Replicas are designed specifically for read scaling. Create one or more replicas and configure your BI tools to connect to the replica endpoint instead of the primary. This offloads read queries without affecting write performance on the primary. Multi-AZ standby (B) is for high availability, not read scaling — the standby does not serve read traffic.

---

**Q2:** A DynamoDB table uses partition key "customer_id" and sort key "order_date". A query needs to find all orders for customer 12345 placed in the last 30 days, sorted by order date descending. Is this query efficient?

- A) No — DynamoDB cannot sort results
- B) No — must use a full table scan for date-based queries
- C) Yes — the query can use the primary key to efficiently fetch customer 12345's orders sorted by order_date
- D) No — must create a GSI first

**Answer: C**

Explanation: The table already has the perfect key structure for this query: (customer_id, order_date). DynamoDB can efficiently query by partition key (customer_id = 12345) and use the sort key (order_date >= last 30 days), returning results sorted by order_date. Set --scan-index-forward false for descending order. This is exactly the advantage of choosing the right primary key design up front.

---

**Q3:** What is the key difference between ElastiCache Redis and ElastiCache Memcached?

- A) Redis only supports string data types; Memcached supports complex types
- B) Redis supports persistence, replication, complex data structures; Memcached is simpler but multi-threaded
- C) Memcached supports Multi-AZ failover; Redis does not
- D) Redis is cheaper; Memcached is more expensive

**Answer: B**

Explanation: Redis offers rich data types (sorted sets, hashes, lists), persistence (can survive restarts), Multi-AZ replication with automatic failover, pub/sub, and Lua scripting. Memcached is simpler — string-only, no persistence, no replication, but is multi-threaded (can use multiple CPU cores efficiently). For most modern applications, Redis is preferred. Memcached is chosen when you specifically need multi-threaded performance for pure caching.

---

**Q4:** An application needs to store user sessions and must survive a Redis node failure without losing session data. What should you configure?

- A) Single-node Redis with scheduled snapshots
- B) Redis with Multi-AZ replication group and automatic failover enabled
- C) Memcached cluster with 3 nodes
- D) DynamoDB table for session storage

**Answer: B**

Explanation: Redis with Multi-AZ and automatic failover creates replica nodes. Session data is replicated to replica nodes. If the primary fails, a replica is promoted to primary automatically (within 60 seconds). Session data is preserved. Memcached (C) has no replication — data is lost on node failure. Single-node Redis (A) with snapshots means data loss of up to the last snapshot interval.

---

**Q5:** Your Aurora MySQL cluster is experiencing heavy read traffic and the single reader instance cannot keep up. How do you scale?

- A) Increase the instance size of the existing reader
- B) Add more Aurora Read Replica instances to the cluster (up to 15)
- C) Create a Multi-AZ deployment
- D) Enable Aurora Serverless

**Answer: B**

Explanation: Aurora supports up to 15 read replicas in a cluster. Each replica shares the same underlying Aurora storage (no data copying needed — near-zero replication lag). You can add replicas to handle more read load and distribute reads across all replicas. Aurora Auto Scaling can automatically add/remove replicas based on CPU or connection count. This is different from RDS read replicas which require data copying.

---

## Chapter 6 Summary

| Service | Type | Best For |
|---------|------|----------|
| RDS MySQL/PostgreSQL | Relational SQL | General-purpose web apps with complex queries |
| RDS Multi-AZ | HA feature | Automatic failover, no data loss |
| RDS Read Replicas | Read scaling | Offload read queries, cross-region DR |
| Aurora | High-performance SQL | 5x MySQL speed, auto-growing storage |
| Aurora Serverless v2 | Auto-scaling SQL | Variable/unpredictable database workloads |
| Aurora Global DB | Multi-region | DR with <1 second replication lag |
| DynamoDB | NoSQL key-value/document | Millions of requests/sec, serverless |
| DynamoDB On-Demand | Capacity mode | Unknown/variable workloads |
| DynamoDB Streams | Change capture | Trigger Lambda on data changes |
| ElastiCache Redis | In-memory | Sessions, leaderboards, complex caching |
| ElastiCache Memcached | Simple in-memory | Pure object caching, multi-threaded |
| DocumentDB | Document (MongoDB) | JSON documents, MongoDB migrations |
| DMS | Migration tool | Migrate any database to AWS |
"""

with open(r"e:\fastapi\aws-admin\06_Databases_RDS_DynamoDB.md", "w", encoding="utf-8") as f:
    f.write(content)

print(f"Written {len(content.splitlines())} lines")
