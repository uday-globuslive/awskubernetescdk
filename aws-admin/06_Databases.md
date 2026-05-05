# Chapter 6: Databases — RDS, Aurora, DynamoDB & ElastiCache
## Relational Databases, NoSQL, Caching & Database Migration

---

## 6.1 AWS Database Services Overview

AWS offers managed database services covering relational, NoSQL, in-memory, time-series, graph, and ledger databases.

```
┌─────────────────────────────────────────────────────────────────────┐
│                  AWS DATABASE SERVICES MAP                          │
├─────────────────────┬───────────────────────────────────────────────┤
│ Category            │ Service                                       │
├─────────────────────┼───────────────────────────────────────────────┤
│ Relational (OLTP)   │ RDS (MySQL/PostgreSQL/SQL Server/Oracle/      │
│                     │ MariaDB), Aurora (MySQL/PostgreSQL)           │
├─────────────────────┼───────────────────────────────────────────────┤
│ Relational (OLAP)   │ Redshift (data warehouse), Aurora Parallel    │
├─────────────────────┼───────────────────────────────────────────────┤
│ NoSQL Key-Value     │ DynamoDB                                      │
├─────────────────────┼───────────────────────────────────────────────┤
│ In-Memory           │ ElastiCache (Redis, Memcached)                │
│                     │ MemoryDB for Redis (durable)                  │
├─────────────────────┼───────────────────────────────────────────────┤
│ Document            │ DocumentDB (MongoDB-compatible)               │
├─────────────────────┼───────────────────────────────────────────────┤
│ Graph               │ Neptune                                       │
├─────────────────────┼───────────────────────────────────────────────┤
│ Time-Series         │ Timestream                                    │
├─────────────────────┼───────────────────────────────────────────────┤
│ Ledger/Immutable    │ QLDB (Quantum Ledger Database)               │
├─────────────────────┼───────────────────────────────────────────────┤
│ Migration           │ DMS (Database Migration Service)              │
│                     │ SCT (Schema Conversion Tool)                  │
└─────────────────────┴───────────────────────────────────────────────┘
```

---

## 6.2 RDS — Relational Database Service

### RDS Features

```
RDS handles:
  ✓ Hardware provisioning
  ✓ Database setup and patching
  ✓ Automated backups (1-35 day retention)
  ✓ Manual snapshots (until you delete them)
  ✓ Multi-AZ failover (1-2 minutes)
  ✓ Read replicas (async replication, up to 15 in Aurora)
  ✓ Security (VPC, SG, KMS encryption, SSL/TLS)
  ✓ Monitoring (Enhanced monitoring, Performance Insights)

You manage:
  ✗ Schema design, indexing, query optimization
  ✗ Application-level configuration
```

### RDS Instance Classes

```
Instance families:
  db.t4g.*    — Burstable (test/dev, variable load, ARM)
  db.t3.*     — Burstable (test/dev, variable load, x86)
  db.m6g.*    — General purpose (ARM Graviton)
  db.m6i.*    — General purpose (x86)
  db.r6g.*    — Memory optimized (large datasets, ARM)
  db.r6i.*    — Memory optimized (large datasets, x86)
  db.x2iedn.* — Memory extreme (large in-memory workloads)

Sizes per family: .micro, .small, .medium, .large, .xlarge, .2xlarge, .4xlarge, .8xlarge, .12xlarge, .16xlarge, .24xlarge
```

### Creating an RDS Instance

```bash
# Create DB subnet group (required before creating DB)
aws rds create-db-subnet-group \
  --db-subnet-group-name prod-db-subnet-group \
  --db-subnet-group-description "Production DB subnets" \
  --subnet-ids $DB_SUB_1 $DB_SUB_2

# Create parameter group (customize DB settings)
aws rds create-db-parameter-group \
  --db-parameter-group-name prod-postgres-params \
  --db-parameter-group-family postgres15 \
  --description "Production PostgreSQL parameters"

# Tune parameters
aws rds modify-db-parameter-group \
  --db-parameter-group-name prod-postgres-params \
  --parameters '[
    {"ParameterName": "shared_preload_libraries", "ParameterValue": "pg_stat_statements", "ApplyMethod": "pending-reboot"},
    {"ParameterName": "log_min_duration_statement", "ParameterValue": "1000", "ApplyMethod": "immediate"},
    {"ParameterName": "max_connections", "ParameterValue": "200", "ApplyMethod": "pending-reboot"},
    {"ParameterName": "work_mem", "ParameterValue": "4096", "ApplyMethod": "immediate"}
  ]'

# Create Multi-AZ PostgreSQL RDS instance
aws rds create-db-instance \
  --db-instance-identifier prod-postgres \
  --db-instance-class db.r6g.xlarge \
  --engine postgres \
  --engine-version 15.4 \
  --master-username dbadmin \
  --manage-master-user-password \      # Use Secrets Manager for password
  --db-name appdb \
  --vpc-security-group-ids $DB_SG \
  --db-subnet-group-name prod-db-subnet-group \
  --db-parameter-group-name prod-postgres-params \
  --allocated-storage 100 \
  --max-allocated-storage 1000 \       # Auto-scaling up to 1TB
  --storage-type gp3 \
  --iops 3000 \
  --storage-encrypted \
  --kms-key-id arn:aws:kms:us-east-1:123:key/abc \
  --multi-az \                         # Sync standby in another AZ
  --backup-retention-period 30 \
  --preferred-backup-window "03:00-04:00" \
  --preferred-maintenance-window "sun:04:00-sun:05:00" \
  --monitoring-interval 60 \          # Enhanced monitoring every 60 seconds
  --monitoring-role-arn arn:aws:iam::123:role/RDSEnhancedMonitoring \
  --enable-performance-insights \
  --performance-insights-retention-period 731 \  # 2 years
  --deletion-protection \
  --copy-tags-to-snapshot \
  --tags Key=Name,Value=prod-postgres Key=Environment,Value=prod

# Wait for DB to be available
aws rds wait db-instance-available --db-instance-identifier prod-postgres

# Describe the created instance
aws rds describe-db-instances \
  --db-instance-identifier prod-postgres \
  --query "DBInstances[0].[DBInstanceIdentifier,DBInstanceStatus,Endpoint.Address,MultiAZ,EngineVersion]" \
  --output table
```

### RDS Read Replicas

```bash
# Create read replica (in same region)
aws rds create-db-instance-read-replica \
  --db-instance-identifier prod-postgres-replica-1 \
  --source-db-instance-identifier prod-postgres \
  --db-instance-class db.r6g.xlarge \
  --availability-zone us-east-1c \
  --publicly-accessible false \
  --enable-performance-insights

# Create cross-region read replica (for disaster recovery or global reads)
aws rds create-db-instance-read-replica \
  --db-instance-identifier prod-postgres-eu \
  --source-db-instance-identifier arn:aws:rds:us-east-1:123:db:prod-postgres \
  --db-instance-class db.r6g.large \
  --region eu-west-1 \
  --source-region us-east-1 \
  --storage-encrypted \
  --kms-key-id arn:aws:kms:eu-west-1:123:key/eu-key

# Promote replica to standalone DB (for migration or failover)
aws rds promote-read-replica \
  --db-instance-identifier prod-postgres-replica-1 \
  --backup-retention-period 7
```

### RDS Snapshots & Restore

```bash
# Manual snapshot
aws rds create-db-snapshot \
  --db-snapshot-identifier prod-postgres-snap-2025-01 \
  --db-instance-identifier prod-postgres

# Copy snapshot to another region (for DR)
aws rds copy-db-snapshot \
  --source-db-snapshot-identifier arn:aws:rds:us-east-1:123:snapshot:prod-postgres-snap-2025-01 \
  --target-db-snapshot-identifier prod-postgres-snap-2025-01-copy \
  --region eu-west-1 \
  --source-region us-east-1 \
  --kms-key-id arn:aws:kms:eu-west-1:123:key/eu-key

# Share snapshot with another account
aws rds modify-db-snapshot-attribute \
  --db-snapshot-identifier prod-postgres-snap-2025-01 \
  --attribute-name restore \
  --values-to-add 987654321098   # Other account ID

# Restore from snapshot to new instance
aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier restored-postgres \
  --db-snapshot-identifier prod-postgres-snap-2025-01 \
  --db-instance-class db.r6g.xlarge \
  --db-subnet-group-name prod-db-subnet-group \
  --vpc-security-group-ids $DB_SG

# Point-in-time restore (to any second within backup retention period)
aws rds restore-db-instance-to-point-in-time \
  --source-db-instance-identifier prod-postgres \
  --target-db-instance-identifier prod-postgres-pitr \
  --restore-time 2025-01-15T14:30:00Z \
  --db-instance-class db.r6g.xlarge
```

### RDS Proxy

RDS Proxy pools and shares DB connections, ideal for Lambda and serverless workloads:

```bash
aws rds create-db-proxy \
  --db-proxy-name prod-postgres-proxy \
  --engine-family POSTGRESQL \
  --auth '[{
    "AuthScheme": "SECRETS",
    "SecretArn": "arn:aws:secretsmanager:us-east-1:123:secret:prod-db-password",
    "IAMAuth": "REQUIRED"
  }]' \
  --role-arn arn:aws:iam::123:role/RDSProxyRole \
  --vpc-subnet-ids $PRIV_SUB_1 $PRIV_SUB_2 \
  --vpc-security-group-ids $DB_SG \
  --require-tls

# Register DB instance with proxy
aws rds register-db-proxy-targets \
  --db-proxy-name prod-postgres-proxy \
  --db-instance-identifiers prod-postgres
```

---

## 6.3 Aurora — AWS's Cloud-Native Database

Aurora is AWS-built, cloud-native relational DB with MySQL and PostgreSQL compatibility. Up to 5x faster than MySQL, 3x faster than PostgreSQL.

```
Aurora Architecture:
┌─────────────────────────────────────────────────────────────────┐
│                     Aurora Cluster                              │
│                                                                 │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│  │  Writer      │    │  Reader 1    │    │  Reader 2    │      │
│  │  (Primary)   │    │  (Replica)   │    │  (Replica)   │      │
│  └──────────────┘    └──────────────┘    └──────────────┘      │
│         │                  │                    │               │
│         └──────────────────┴────────────────────┘               │
│                            │                                    │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │        Shared Cluster Storage Volume                    │   │
│  │   6 copies across 3 AZs (2 copies per AZ)              │   │
│  │   Automatically grows 10GB → 128TB in 10GB increments  │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  Cluster endpoint (writer):  cluster.cluster-xxx.rds.amazonaws.com    │
│  Reader endpoint (any reader): cluster.cluster-ro-xxx.rds.amazonaws.com│
└─────────────────────────────────────────────────────────────────┘
```

### Creating Aurora

```bash
# Create Aurora PostgreSQL cluster
aws rds create-db-cluster \
  --db-cluster-identifier prod-aurora-cluster \
  --engine aurora-postgresql \
  --engine-version 15.4 \
  --master-username dbadmin \
  --manage-master-user-password \
  --db-subnet-group-name prod-db-subnet-group \
  --vpc-security-group-ids $DB_SG \
  --storage-encrypted \
  --kms-key-id arn:aws:kms:us-east-1:123:key/abc \
  --backup-retention-period 30 \
  --preferred-backup-window "03:00-04:00" \
  --deletion-protection \
  --enable-cloudwatch-logs-exports '["postgresql"]'

# Create primary writer instance
aws rds create-db-instance \
  --db-instance-identifier prod-aurora-writer \
  --db-instance-class db.r6g.xlarge \
  --engine aurora-postgresql \
  --db-cluster-identifier prod-aurora-cluster \
  --availability-zone us-east-1a \
  --enable-performance-insights

# Create reader instance (different AZ for HA)
aws rds create-db-instance \
  --db-instance-identifier prod-aurora-reader-1 \
  --db-instance-class db.r6g.large \
  --engine aurora-postgresql \
  --db-cluster-identifier prod-aurora-cluster \
  --availability-zone us-east-1b \
  --enable-performance-insights

# Create custom endpoint for analytics queries (route to specific readers)
aws rds create-db-cluster-endpoint \
  --db-cluster-identifier prod-aurora-cluster \
  --db-cluster-endpoint-identifier analytics-endpoint \
  --endpoint-type READER \
  --static-members prod-aurora-reader-1
```

### Aurora Serverless v2

Automatically scales capacity up and down based on application demand:

```bash
aws rds create-db-cluster \
  --db-cluster-identifier dev-aurora-serverless \
  --engine aurora-postgresql \
  --engine-version 15.4 \
  --master-username dbadmin \
  --manage-master-user-password \
  --db-subnet-group-name dev-db-subnet-group \
  --vpc-security-group-ids $DB_SG \
  --serverless-v2-scaling-configuration MinCapacity=0.5,MaxCapacity=16 \
  # MinCapacity: 0.5 ACUs minimum (can go to 0 for pause)
  # MaxCapacity: 16 ACUs maximum (1 ACU ≈ 2GB RAM)
  --storage-encrypted

aws rds create-db-instance \
  --db-instance-identifier dev-aurora-serverless-writer \
  --db-instance-class db.serverless \
  --engine aurora-postgresql \
  --db-cluster-identifier dev-aurora-serverless
```

### Aurora Global Database

Replicate Aurora across up to 5 regions with < 1 second replication lag:

```bash
# Create global cluster (from existing cluster)
aws rds create-global-cluster \
  --global-cluster-identifier my-global-db \
  --source-db-cluster-identifier arn:aws:rds:us-east-1:123:cluster:prod-aurora-cluster

# Add secondary region cluster
aws rds create-db-cluster \
  --db-cluster-identifier aurora-global-eu \
  --global-cluster-identifier my-global-db \
  --engine aurora-postgresql \
  --engine-version 15.4 \
  --db-subnet-group-name eu-db-subnet-group \
  --vpc-security-group-ids $EU_DB_SG \
  --region eu-west-1

# Failover to secondary (managed failover)
aws rds failover-global-cluster \
  --global-cluster-identifier my-global-db \
  --target-db-cluster-identifier arn:aws:rds:eu-west-1:123:cluster:aurora-global-eu \
  --allow-data-loss false
```

---

## 6.4 DynamoDB — Managed NoSQL Key-Value & Document Database

### DynamoDB Concepts

```
Key DynamoDB Concepts:
  Table → Collection of items
  Item  → Row (up to 400KB per item)
  Attribute → Column (value)

  Primary Key:
    Simple PK: Partition Key only (e.g., UserId)
    Composite PK: Partition Key + Sort Key (e.g., UserId + OrderId)

  Secondary Indexes:
    GSI: Global Secondary Index — different PK than table, own capacity
    LSI: Local Secondary Index — same PK, different sort key, must create at table creation

  Capacity Modes:
    Provisioned: Specify RCU/WCU (predictable traffic, cheaper)
    On-Demand: Auto-scales, no capacity planning (unpredictable traffic, more expensive)
    1 RCU = 1 strongly consistent read/sec (4KB) OR 2 eventually consistent
    1 WCU = 1 write/sec (1KB)
```

### Creating DynamoDB Tables

```bash
# Create orders table with composite key
aws dynamodb create-table \
  --table-name orders \
  --attribute-definitions \
    AttributeName=user_id,AttributeType=S \
    AttributeName=order_id,AttributeType=S \
    AttributeName=created_at,AttributeType=S \
    AttributeName=status,AttributeType=S \
  --key-schema \
    AttributeName=user_id,KeyType=HASH \
    AttributeName=order_id,KeyType=RANGE \
  --billing-mode PAY_PER_REQUEST \    # On-demand
  --global-secondary-indexes '[
    {
      "IndexName": "status-created-index",
      "KeySchema": [
        {"AttributeName": "status", "KeyType": "HASH"},
        {"AttributeName": "created_at", "KeyType": "RANGE"}
      ],
      "Projection": {"ProjectionType": "ALL"}
    }
  ]' \
  --sse-specification Enabled=true,SSEType=KMS,KMSMasterKeyId=alias/dynamodb-key \
  --point-in-time-recovery-specification PointInTimeRecoveryEnabled=true \
  --tags Key=Name,Value=orders Key=Environment,Value=prod

# Enable auto-scaling for provisioned table
aws application-autoscaling register-scalable-target \
  --service-namespace dynamodb \
  --resource-id "table/orders" \
  --scalable-dimension "dynamodb:table:ReadCapacityUnits" \
  --min-capacity 5 \
  --max-capacity 1000

aws application-autoscaling put-scaling-policy \
  --service-namespace dynamodb \
  --resource-id "table/orders" \
  --scalable-dimension "dynamodb:table:ReadCapacityUnits" \
  --policy-name ReadAutoScaling \
  --policy-type TargetTrackingScaling \
  --target-tracking-scaling-policy-configuration \
    "TargetValue=70.0,PredefinedMetricSpecification={PredefinedMetricType=DynamoDBReadCapacityUtilization}"
```

### DynamoDB CRUD Operations

```python
import boto3
from boto3.dynamodb.conditions import Key, Attr
from decimal import Decimal

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('orders')

# PUT item (create or full replace)
table.put_item(
    Item={
        'user_id': 'user-123',
        'order_id': 'order-456',
        'status': 'pending',
        'total': Decimal('99.95'),
        'items': [
            {'product_id': 'prod-1', 'quantity': 2, 'price': Decimal('49.95')},
            {'product_id': 'prod-2', 'quantity': 1, 'price': Decimal('0.05')}
        ],
        'created_at': '2025-01-15T10:00:00Z'
    },
    ConditionExpression=Attr('order_id').not_exists()  # Prevent overwrite
)

# GET item (by primary key — most efficient)
response = table.get_item(
    Key={'user_id': 'user-123', 'order_id': 'order-456'},
    ConsistentRead=True   # Strongly consistent read
)
item = response.get('Item')

# UPDATE item (atomic update — better than get + put)
table.update_item(
    Key={'user_id': 'user-123', 'order_id': 'order-456'},
    UpdateExpression='SET #s = :new_status, updated_at = :ts ADD version :one',
    ExpressionAttributeNames={'#s': 'status'},  # 'status' is reserved word
    ExpressionAttributeValues={
        ':new_status': 'shipped',
        ':ts': '2025-01-15T14:00:00Z',
        ':one': 1
    },
    ConditionExpression='attribute_exists(order_id) AND #s = :expected_status',
    ExpressionAttributeValues={
        ':new_status': 'shipped',
        ':ts': '2025-01-15T14:00:00Z',
        ':one': 1,
        ':expected_status': 'pending'  # Optimistic locking
    }
)

# QUERY (efficient — uses index)
# Get all orders for a user, sorted by order_id
response = table.query(
    KeyConditionExpression=Key('user_id').eq('user-123'),
    FilterExpression=Attr('status').eq('pending'),  # Applied AFTER query, before return
    ScanIndexForward=False,  # Descending order
    Limit=20
)
items = response['Items']
last_key = response.get('LastEvaluatedKey')  # Pagination token

# Continue pagination
if last_key:
    response = table.query(
        KeyConditionExpression=Key('user_id').eq('user-123'),
        ExclusiveStartKey=last_key,
        Limit=20
    )

# QUERY on GSI
response = table.query(
    IndexName='status-created-index',
    KeyConditionExpression=Key('status').eq('pending') & Key('created_at').gt('2025-01-01')
)

# SCAN (reads entire table — expensive, use sparingly)
# Use parallel scan for large tables
response = table.scan(
    FilterExpression=Attr('total').gt(Decimal('100')),
    ProjectionExpression='user_id, order_id, total',
    TotalSegments=4,    # 4 parallel workers
    Segment=0           # This worker handles segment 0
)

# BATCH operations
# Batch get (up to 100 items, from multiple tables)
response = dynamodb.batch_get_item(
    RequestItems={
        'orders': {
            'Keys': [
                {'user_id': 'user-123', 'order_id': 'order-1'},
                {'user_id': 'user-123', 'order_id': 'order-2'},
            ]
        },
        'users': {
            'Keys': [{'user_id': 'user-123'}]
        }
    }
)

# Batch write (up to 25 items)
with table.batch_writer() as batch:
    for order in orders_to_write:
        batch.put_item(Item=order)
    for order_id in orders_to_delete:
        batch.delete_item(Key={'user_id': 'user-123', 'order_id': order_id})

# TRANSACT operations (all-or-nothing, up to 100 items, max 4MB)
dynamodb.meta.client.transact_write_items(
    TransactItems=[
        {
            'Update': {
                'TableName': 'orders',
                'Key': {'user_id': 'user-123', 'order_id': 'order-456'},
                'UpdateExpression': 'SET #s = :shipped',
                'ExpressionAttributeNames': {'#s': 'status'},
                'ExpressionAttributeValues': {':shipped': 'shipped'}
            }
        },
        {
            'Update': {
                'TableName': 'inventory',
                'Key': {'product_id': 'prod-1'},
                'UpdateExpression': 'ADD stock_count :decrement',
                'ExpressionAttributeValues': {':decrement': -2},
                'ConditionExpression': 'stock_count >= :min',
                'ExpressionAttributeValues': {':decrement': -2, ':min': 2}
            }
        }
    ]
)
```

### DynamoDB Streams & TTL

```bash
# Enable DynamoDB Streams (capture changes)
aws dynamodb update-table \
  --table-name orders \
  --stream-specification StreamEnabled=true,StreamViewType=NEW_AND_OLD_IMAGES
  # ViewType options: KEYS_ONLY, NEW_IMAGE, OLD_IMAGE, NEW_AND_OLD_IMAGES

# Enable TTL (auto-delete expired items)
aws dynamodb update-time-to-live \
  --table-name sessions \
  --time-to-live-specification Enabled=true,AttributeName=expires_at
  # Store expires_at as Unix epoch timestamp, DynamoDB deletes within 48 hours

# Create Lambda trigger from DynamoDB Stream
aws lambda create-event-source-mapping \
  --function-name process-order-changes \
  --event-source-arn arn:aws:dynamodb:us-east-1:123:table/orders/stream/2025-01-01T00:00:00.000 \
  --starting-position LATEST \
  --batch-size 100 \
  --bisect-batch-on-function-error \  # Split batch on error to isolate bad records
  --destination-config '{"OnFailure": {"Destination": "arn:aws:sqs:us-east-1:123:orders-dlq"}}'
```

### DynamoDB Global Tables

```bash
# Enable global tables (multi-region active-active replication)
aws dynamodb update-table \
  --table-name orders \
  --replica-updates '[
    {"Create": {"RegionName": "eu-west-1"}},
    {"Create": {"RegionName": "ap-southeast-1"}}
  ]'
# Note: table must have on-demand billing or auto-scaling enabled
# Note: DynamoDB Streams must be enabled
```

### DAX — DynamoDB Accelerator

In-memory cache for DynamoDB — reduces read latency from milliseconds to microseconds:

```bash
# Create DAX cluster
aws dax create-cluster \
  --cluster-name prod-dax \
  --node-type dax.r6g.large \
  --replication-factor 3 \      # 3 nodes for HA
  --iam-role-arn arn:aws:iam::123:role/DAXRole \
  --subnet-group-name dax-subnet-group \
  --security-group-ids $CACHE_SG \
  --sse-specification Enabled=true

# DAX endpoint: prod-dax.abc123.dax-clusters.us-east-1.amazonaws.com:8111
# Replace boto3 DynamoDB client with DAX client (same API)
```

```python
import amazon.dax.client as dax

dax_client = dax.AmazonDaxClient(
    endpoints=['prod-dax.abc123.dax-clusters.us-east-1.amazonaws.com:8111']
)
dynamodb = boto3.resource('dynamodb', client=dax_client)
# All reads now go through DAX cache first
```

---

## 6.5 ElastiCache — Managed In-Memory Cache

### Redis vs Memcached

```
┌──────────────────────────────────────────────────────────────────┐
│              REDIS vs MEMCACHED COMPARISON                       │
├───────────────────────┬──────────────────────┬───────────────────┤
│ Feature               │ Redis                │ Memcached         │
├───────────────────────┼──────────────────────┼───────────────────┤
│ Data structures       │ Rich (str/hash/list/ │ String only       │
│                       │ set/sorted set/etc.) │                   │
├───────────────────────┼──────────────────────┼───────────────────┤
│ Persistence           │ RDB + AOF             │ None              │
├───────────────────────┼──────────────────────┼───────────────────┤
│ Pub/Sub               │ Yes                  │ No                │
├───────────────────────┼──────────────────────┼───────────────────┤
│ Lua scripting         │ Yes                  │ No                │
├───────────────────────┼──────────────────────┼───────────────────┤
│ Transactions          │ Yes (MULTI/EXEC)     │ No                │
├───────────────────────┼──────────────────────┼───────────────────┤
│ Replication/HA        │ Primary + replicas   │ None              │
├───────────────────────┼──────────────────────┼───────────────────┤
│ Cluster mode          │ Yes (sharding)       │ Yes (multi-node)  │
├───────────────────────┼──────────────────────┼───────────────────┤
│ Multi-threading       │ No (single thread)   │ Yes               │
├───────────────────────┼──────────────────────┼───────────────────┤
│ Choose when           │ Caching, sessions,   │ Simple caching,   │
│                       │ leaderboards, queues │ large objects     │
└───────────────────────┴──────────────────────┴───────────────────┘
```

### Creating ElastiCache Redis Cluster

```bash
# Create subnet group
aws elasticache create-cache-subnet-group \
  --cache-subnet-group-name prod-cache-subnet \
  --cache-subnet-group-description "Production cache subnets" \
  --subnet-ids $PRIV_SUB_1 $PRIV_SUB_2

# Create parameter group
aws elasticache create-cache-parameter-group \
  --cache-parameter-group-name prod-redis-params \
  --cache-parameter-group-family redis7 \
  --description "Production Redis parameters"

aws elasticache modify-cache-parameter-group \
  --cache-parameter-group-name prod-redis-params \
  --parameter-name-values \
    "ParameterName=maxmemory-policy,ParameterValue=allkeys-lru" \
    "ParameterName=notify-keyspace-events,ParameterValue=KEA"

# Create Redis Replication Group (primary + replicas, Multi-AZ)
aws elasticache create-replication-group \
  --replication-group-id prod-redis \
  --replication-group-description "Production Redis" \
  --cache-node-type cache.r7g.large \
  --engine redis \
  --engine-version 7.0 \
  --num-cache-clusters 3 \              # 1 primary + 2 replicas
  --automatic-failover-enabled \
  --multi-az-enabled \
  --cache-subnet-group-name prod-cache-subnet \
  --security-group-ids $CACHE_SG \
  --cache-parameter-group-name prod-redis-params \
  --at-rest-encryption-enabled \
  --kms-key-id arn:aws:kms:us-east-1:123:key/abc \
  --transit-encryption-enabled \
  --auth-token "SuperSecureTokenMin20Chars!" \
  --snapshot-retention-limit 7 \
  --snapshot-window "02:00-03:00"

# Create Redis Cluster Mode (sharded, for large datasets > single node)
aws elasticache create-replication-group \
  --replication-group-id prod-redis-cluster \
  --replication-group-description "Clustered Redis" \
  --cache-node-type cache.r7g.large \
  --engine redis \
  --num-node-groups 3 \                 # 3 shards
  --replicas-per-node-group 2 \         # 2 replicas per shard
  --cluster-mode enabled \
  --cache-subnet-group-name prod-cache-subnet \
  --security-group-ids $CACHE_SG \
  --at-rest-encryption-enabled \
  --transit-encryption-enabled
```

### ElastiCache Serverless

No capacity planning — auto-scales with demand:

```bash
aws elasticache create-serverless-cache \
  --serverless-cache-name my-serverless-redis \
  --engine redis \
  --security-group-ids $CACHE_SG \
  --subnet-ids $PRIV_SUB_1 $PRIV_SUB_2 \
  --cache-usage-limits '{
    "DataStorage": {"Maximum": 10, "Unit": "GB"},
    "ECPUPerSecond": {"Maximum": 5000}
  }'
```

### Python Redis Caching Pattern

```python
import redis
import json
import hashlib
from functools import wraps
from typing import Any, Optional

# Connect to ElastiCache Redis (with TLS + auth)
r = redis.Redis(
    host='prod-redis.abc.ng.0001.use1.cache.amazonaws.com',
    port=6379,
    ssl=True,
    password='SuperSecureTokenMin20Chars!',
    decode_responses=True
)

# ── CACHE-ASIDE PATTERN ───────────────────────────────────────
def get_user(user_id: str) -> dict:
    cache_key = f"user:{user_id}"
    
    # Try cache first
    cached = r.get(cache_key)
    if cached:
        return json.loads(cached)  # Cache hit
    
    # Cache miss — fetch from database
    user = db.query("SELECT * FROM users WHERE id = %s", user_id)
    
    # Store in cache (TTL: 1 hour)
    r.setex(cache_key, 3600, json.dumps(user))
    return user

# ── CACHE DECORATOR ───────────────────────────────────────────
def cache(ttl: int = 300, prefix: str = ""):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key from function name and args
            key_data = f"{prefix}{func.__name__}:{args}:{kwargs}"
            cache_key = hashlib.md5(key_data.encode()).hexdigest()
            
            cached = r.get(cache_key)
            if cached:
                return json.loads(cached)
            
            result = func(*args, **kwargs)
            r.setex(cache_key, ttl, json.dumps(result))
            return result
        return wrapper
    return decorator

@cache(ttl=3600, prefix="product:")
def get_product_catalog(category: str) -> list:
    return db.get_products(category)  # Expensive query

# ── SESSION STORAGE ───────────────────────────────────────────
def create_session(user_id: str, session_data: dict) -> str:
    import secrets
    session_id = secrets.token_urlsafe(32)
    session_key = f"session:{session_id}"
    r.setex(session_key, 86400, json.dumps({**session_data, 'user_id': user_id}))
    return session_id

def get_session(session_id: str) -> Optional[dict]:
    data = r.get(f"session:{session_id}")
    if data:
        r.expire(f"session:{session_id}", 86400)  # Sliding expiry
        return json.loads(data)
    return None

# ── RATE LIMITING ─────────────────────────────────────────────
def check_rate_limit(user_id: str, limit: int = 100, window: int = 3600) -> bool:
    key = f"rate:{user_id}:{window}"
    pipe = r.pipeline()
    pipe.incr(key)
    pipe.expire(key, window)
    count, _ = pipe.execute()
    return count <= limit

# ── DISTRIBUTED LOCK ──────────────────────────────────────────
import uuid
import time

class RedisLock:
    def __init__(self, redis_client, lock_name: str, timeout: int = 30):
        self.r = redis_client
        self.key = f"lock:{lock_name}"
        self.timeout = timeout
        self.token = str(uuid.uuid4())
    
    def acquire(self) -> bool:
        return bool(self.r.set(self.key, self.token, ex=self.timeout, nx=True))
    
    def release(self):
        # Lua script for atomic check-and-delete
        script = """
        if redis.call('get', KEYS[1]) == ARGV[1] then
            return redis.call('del', KEYS[1])
        else
            return 0
        end
        """
        self.r.eval(script, 1, self.key, self.token)
    
    def __enter__(self):
        if not self.acquire():
            raise RuntimeError(f"Could not acquire lock: {self.key}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()
```

---

## 6.6 Database Migration Service (DMS)

```bash
# Create replication instance
aws dms create-replication-instance \
  --replication-instance-identifier prod-dms \
  --replication-instance-class dms.r6i.large \
  --allocated-storage 100 \
  --vpc-security-group-ids $DMS_SG \
  --replication-subnet-group-identifier prod-dms-subnet-group \
  --publicly-accessible false \
  --multi-az

# Create source endpoint (on-prem MySQL)
aws dms create-endpoint \
  --endpoint-identifier source-mysql \
  --endpoint-type source \
  --engine-name mysql \
  --server-name 10.0.1.100 \
  --port 3306 \
  --database-name mydb \
  --username dbadmin \
  --password secret123

# Create target endpoint (RDS PostgreSQL)
aws dms create-endpoint \
  --endpoint-identifier target-postgres \
  --endpoint-type target \
  --engine-name postgres \
  --server-name prod-postgres.abc.us-east-1.rds.amazonaws.com \
  --port 5432 \
  --database-name appdb \
  --username dbadmin \
  --password secret456

# Create replication task (full load + CDC)
aws dms create-replication-task \
  --replication-task-identifier mysql-to-postgres-migration \
  --source-endpoint-arn arn:aws:dms:...:source-mysql \
  --target-endpoint-arn arn:aws:dms:...:target-postgres \
  --replication-instance-arn arn:aws:dms:...:prod-dms \
  --migration-type full-load-and-cdc \
  --table-mappings '{
    "rules": [{
      "rule-type": "selection",
      "rule-id": "1",
      "rule-name": "include-all",
      "object-locator": {"schema-name": "mydb", "table-name": "%"},
      "rule-action": "include"
    }]
  }'

# Start task
aws dms start-replication-task \
  --replication-task-arn arn:aws:dms:...:mysql-to-postgres-migration \
  --start-replication-task-type start-replication

# Monitor task status
aws dms describe-replication-tasks \
  --filters "Name=replication-task-id,Values=mysql-to-postgres-migration" \
  --query "ReplicationTasks[0].[Status,ReplicationTaskStats]"
```

---

## 6.7 Interview Q&A

**Q: What is the difference between RDS Multi-AZ and Read Replicas?**
A: Multi-AZ creates a synchronous standby replica in a different AZ for high availability and automatic failover (1-2 minutes). It's NOT for performance — you can't read from the standby. Read Replicas use asynchronous replication and are for read scaling — you direct read traffic to replicas to reduce primary load. Read Replicas can be promoted to standalone databases; Multi-AZ standby cannot be directly accessed.

**Q: What is Aurora and how does it differ from RDS?**
A: Aurora is AWS's cloud-native relational database compatible with MySQL and PostgreSQL. Key differences: Aurora has a shared cluster storage volume (6 copies across 3 AZs, auto-grows 10GB to 128TB), up to 15 read replicas (vs 5 for RDS), faster failover (~30 seconds vs 1-2 minutes for RDS Multi-AZ), Aurora Serverless v2 for automatic scaling, and Global Database for sub-second cross-region replication.

**Q: When would you use DynamoDB over RDS?**
A: Use DynamoDB when: you need single-digit millisecond latency at any scale; your data model fits key-value or document patterns; you need automatic scaling without capacity planning; you need multi-region active-active replication; your data has variable attributes. Use RDS when: you have complex queries with JOINs; you need ACID transactions across many entities; your team knows SQL; you have structured relational data.

**Q: What is the difference between DynamoDB provisioned and on-demand capacity?**
A: Provisioned capacity: you specify RCU/WCU upfront, cheaper if traffic is predictable, can configure auto-scaling. On-demand: automatically scales, no capacity planning, costs about 7x more per request than provisioned at full utilization. Use on-demand for new tables with unknown traffic, development, or spiky workloads; use provisioned with auto-scaling for steady production workloads.

**Q: What is DynamoDB Global Tables?**
A: Global Tables provide multi-region, multi-active (all regions accept writes) replication with automatic conflict resolution using last-writer-wins. Requires on-demand billing or auto-scaling, DynamoDB Streams must be enabled, and table names must match across regions. Ideal for applications needing low latency globally or requiring active-active DR.

**Q: What is ElastiCache and when would you use it?**
A: ElastiCache is a managed in-memory data store (Redis or Memcached). Use it to: reduce database load by caching frequently-read data; store session data for stateless applications; implement leaderboards, pub/sub, rate limiting with Redis data structures; reduce API response times. The cache-aside pattern is most common: check cache first, on miss fetch from DB and populate cache with TTL.

**Q: What is the difference between Redis and Memcached?**
A: Redis supports rich data structures (strings, hashes, lists, sets, sorted sets), persistence (RDB/AOF snapshots), replication with automatic failover, Lua scripting, and transactions. Memcached only supports simple string values, no persistence, and horizontal scaling via sharding. Choose Redis for most use cases — it's more capable. Choose Memcached if you only need simple caching and want multi-threaded performance for large object caches.

**Q: What is RDS Proxy and why would you use it?**
A: RDS Proxy sits between your application and RDS/Aurora, pooling and sharing database connections. Benefits: Lambda functions can scale to thousands without overwhelming DB with connection overhead (Lambda creates a new connection per invocation); automatic failover happens at proxy layer without app code changes; secrets managed via IAM authentication to Secrets Manager. Essential for serverless architectures using relational databases.
