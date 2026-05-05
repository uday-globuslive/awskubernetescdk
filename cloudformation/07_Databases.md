# CloudFormation Chapter 7: Database Templates
## RDS, Aurora, DynamoDB, and ElastiCache CloudFormation Resources

---

## 7.1 Aurora PostgreSQL Cluster

```yaml
AWSTemplateFormatVersion: '2010-09-09'
Description: Aurora PostgreSQL cluster with Multi-AZ and auto-scaling

Parameters:
  Environment:
    Type: String
    AllowedValues: [dev, staging, prod]
  
  DBMasterPassword:
    Type: String
    NoEcho: true
    MinLength: 12

  DBInstanceClass:
    Type: String
    Default: db.r6g.medium
    AllowedValues: [db.t4g.medium, db.r6g.medium, db.r6g.large, db.r6g.xlarge, db.r6g.2xlarge]

Conditions:
  IsProd: !Equals [!Ref Environment, prod]

Resources:
  # ── KMS Key for RDS Encryption ────────────────────────
  DBKMSKey:
    Type: AWS::KMS::Key
    Properties:
      Description: KMS key for Aurora encryption
      EnableKeyRotation: true
      KeyPolicy:
        Version: '2012-10-17'
        Statement:
          - Effect: Allow
            Principal:
              AWS: !Sub 'arn:aws:iam::${AWS::AccountId}:root'
            Action: 'kms:*'
            Resource: '*'
          - Effect: Allow
            Principal:
              Service: rds.amazonaws.com
            Action:
              - kms:GenerateDataKey
              - kms:Decrypt
            Resource: '*'

  DBKMSAlias:
    Type: AWS::KMS::Alias
    Properties:
      AliasName: !Sub 'alias/${AWS::StackName}-db'
      TargetKeyId: !Ref DBKMSKey

  # ── DB Security Group ─────────────────────────────────
  DBSecurityGroup:
    Type: AWS::EC2::SecurityGroup
    Properties:
      GroupDescription: Aurora database security group
      VpcId: !ImportValue 'network-stack-VpcId'
      SecurityGroupIngress:
        - IpProtocol: tcp
          FromPort: 5432
          ToPort: 5432
          SourceSecurityGroupId: !ImportValue 'app-stack-AppSecurityGroupId'
          Description: PostgreSQL access from app tier
      Tags:
        - Key: Name
          Value: !Sub '${AWS::StackName}-db-sg'

  # ── DB Parameter Group ────────────────────────────────
  DBParameterGroup:
    Type: AWS::RDS::DBClusterParameterGroup
    Properties:
      DBClusterParameterGroupName: !Sub '${AWS::StackName}-aurora-pg15'
      Description: Aurora PostgreSQL 15 parameter group
      Family: aurora-postgresql15
      Parameters:
        shared_buffers: "262144"           # 256MB (in 8KB pages)
        work_mem: "65536"                  # 64MB per sort/hash
        max_connections: "200"
        effective_cache_size: "786432"     # 768MB
        log_min_duration_statement: "1000" # Log queries > 1s
        log_lock_waits: "on"
        wal_level: logical                 # Enable logical replication
        rds.log_retention_period: "10080"  # 7 days in minutes

  # ── DB Subnet Group ───────────────────────────────────
  DBSubnetGroup:
    Type: AWS::RDS::DBSubnetGroup
    Properties:
      DBSubnetGroupName: !Sub '${AWS::StackName}-subnet-group'
      DBSubnetGroupDescription: DB subnet group for Aurora
      SubnetIds: !Split [',', !ImportValue 'network-stack-DBSubnets']

  # ── Aurora Cluster ────────────────────────────────────
  AuroraCluster:
    Type: AWS::RDS::DBCluster
    DeletionPolicy: Snapshot    # Take final snapshot before deletion
    UpdateReplacePolicy: Snapshot
    Properties:
      DBClusterIdentifier: !Sub '${AWS::StackName}-aurora'
      Engine: aurora-postgresql
      EngineVersion: "15.4"
      DatabaseName: appdb
      MasterUsername: dbadmin
      ManageMasterUserPassword: true    # AWS manages rotation in Secrets Manager
      # MasterUserPassword: !Ref DBMasterPassword  # Alternative: manual password
      DBClusterParameterGroupName: !Ref DBParameterGroup
      DBSubnetGroupName: !Ref DBSubnetGroup
      VpcSecurityGroupIds:
        - !Ref DBSecurityGroup
      StorageEncrypted: true
      KmsKeyId: !GetAtt DBKMSKey.Arn
      BackupRetentionPeriod: !If [IsProd, 35, 7]
      PreferredBackupWindow: "02:00-03:00"
      PreferredMaintenanceWindow: "sun:04:00-sun:05:00"
      DeletionProtection: !If [IsProd, true, false]
      EnableCloudwatchLogsExports:
        - postgresql
        - upgrade
      EnableIAMDatabaseAuthentication: true    # Login with IAM credentials
      CopyTagsToSnapshot: true
      ServerlessV2ScalingConfiguration: !If
        - IsProd
        - !Ref AWS::NoValue
        - MinCapacity: 0.5    # For non-prod, use Serverless v2
          MaxCapacity: 8.0

  # ── Primary Instance ──────────────────────────────────
  AuroraPrimaryInstance:
    Type: AWS::RDS::DBInstance
    Properties:
      DBInstanceIdentifier: !Sub '${AWS::StackName}-aurora-primary'
      DBClusterIdentifier: !Ref AuroraCluster
      DBInstanceClass: !If [IsProd, !Ref DBInstanceClass, db.serverless]
      Engine: aurora-postgresql
      AutoMinorVersionUpgrade: true
      PubliclyAccessible: false
      MonitoringInterval: !If [IsProd, 60, 0]    # Enhanced monitoring (every 60s)
      MonitoringRoleArn: !If
        - IsProd
        - !GetAtt RDSMonitoringRole.Arn
        - !Ref AWS::NoValue
      EnablePerformanceInsights: !If [IsProd, true, false]
      PerformanceInsightsRetentionPeriod: !If [IsProd, 7, !Ref AWS::NoValue]
      PerformanceInsightsKMSKeyId: !If [IsProd, !Ref DBKMSKey, !Ref AWS::NoValue]

  # ── Read Replica ──────────────────────────────────────
  AuroraReadReplica:
    Type: AWS::RDS::DBInstance
    Condition: IsProd
    Properties:
      DBInstanceIdentifier: !Sub '${AWS::StackName}-aurora-reader'
      DBClusterIdentifier: !Ref AuroraCluster
      DBInstanceClass: !Ref DBInstanceClass
      Engine: aurora-postgresql
      AutoMinorVersionUpgrade: true
      PubliclyAccessible: false

  # ── RDS Proxy (connection pooling) ───────────────────
  RDSProxy:
    Type: AWS::RDS::DBProxy
    Condition: IsProd
    Properties:
      DBProxyName: !Sub '${AWS::StackName}-proxy'
      EngineFamily: POSTGRESQL
      RoleArn: !GetAtt RDSProxyRole.Arn
      Auth:
        - AuthScheme: SECRETS
          SecretArn: !GetAtt AuroraCluster.MasterUserSecret.SecretArn
          IAMAuth: REQUIRED
      VpcSubnetIds: !Split [',', !ImportValue 'network-stack-PrivateSubnets']
      VpcSecurityGroupIds:
        - !Ref DBSecurityGroup
      MaxConnectionsPercent: 90
      MaxIdleConnectionsPercent: 50
      ConnectionBorrowTimeout: 120
      RequireTLS: true

  RDSProxyTargetGroup:
    Type: AWS::RDS::DBProxyTargetGroup
    Condition: IsProd
    DependsOn: RDSProxy
    Properties:
      DBProxyName: !Ref RDSProxy
      TargetGroupName: default
      DBClusterIdentifiers:
        - !Ref AuroraCluster
      ConnectionPoolConfigurationInfo:
        MaxConnectionsPercent: 90
        MaxIdleConnectionsPercent: 50
```

---

## 7.2 DynamoDB Table

```yaml
  # ── DynamoDB Table ─────────────────────────────────────
  OrdersTable:
    Type: AWS::DynamoDB::Table
    DeletionPolicy: Retain
    Properties:
      TableName: !Sub '${AWS::StackName}-orders'
      BillingMode: PAY_PER_REQUEST    # Serverless, no capacity planning
      PointInTimeRecoverySpecification:
        PointInTimeRecoveryEnabled: true    # 35-day PITR
      SSESpecification:
        SSEEnabled: true
        SSEType: KMS
        KMSMasterKeyId: !GetAtt DBKMSKey.Arn
      StreamSpecification:
        StreamViewType: NEW_AND_OLD_IMAGES   # For Lambda triggers
      TimeToLiveSpecification:
        AttributeName: expires_at
        Enabled: true
      AttributeDefinitions:
        - AttributeName: pk          # Partition key: "ORDER#orderId" or "USER#userId"
          AttributeType: S
        - AttributeName: sk          # Sort key: "ORDER#orderId" or "ITEM#itemId"
          AttributeType: S
        - AttributeName: gsi1pk      # GSI: status + date
          AttributeType: S
        - AttributeName: gsi1sk
          AttributeType: S
        - AttributeName: user_id     # GSI: query by user
          AttributeType: S
      KeySchema:
        - AttributeName: pk
          KeyType: HASH
        - AttributeName: sk
          KeyType: RANGE
      GlobalSecondaryIndexes:
        - IndexName: gsi1-status-date
          KeySchema:
            - AttributeName: gsi1pk
              KeyType: HASH
            - AttributeName: gsi1sk
              KeyType: RANGE
          Projection:
            ProjectionType: ALL
        - IndexName: gsi2-user-orders
          KeySchema:
            - AttributeName: user_id
              KeyType: HASH
            - AttributeName: pk
              KeyType: RANGE
          Projection:
            ProjectionType: INCLUDE
            NonKeyAttributes:
              - status
              - total_amount
              - created_at
      Tags:
        - Key: Environment
          Value: !Ref Environment

  # ── DynamoDB Auto Scaling (if using PROVISIONED mode) ─
  # Uncomment if switching to PROVISIONED for predictable workloads
  # TableReadScalingTarget:
  #   Type: AWS::ApplicationAutoScaling::ScalableTarget
  #   Properties:
  #     ServiceNamespace: dynamodb
  #     ResourceId: !Sub 'table/${OrdersTable}'
  #     ScalableDimension: dynamodb:table:ReadCapacityUnits
  #     MinCapacity: 5
  #     MaxCapacity: 1000
```

---

## 7.3 ElastiCache Redis

```yaml
  # ── ElastiCache Security Group ────────────────────────
  CacheSecurityGroup:
    Type: AWS::EC2::SecurityGroup
    Properties:
      GroupDescription: ElastiCache Redis security group
      VpcId: !ImportValue 'network-stack-VpcId'
      SecurityGroupIngress:
        - IpProtocol: tcp
          FromPort: 6379
          ToPort: 6379
          SourceSecurityGroupId: !ImportValue 'app-stack-AppSecurityGroupId'
          Description: Redis from app tier

  # ── Cache Subnet Group ────────────────────────────────
  CacheSubnetGroup:
    Type: AWS::ElastiCache::SubnetGroup
    Properties:
      CacheSubnetGroupName: !Sub '${AWS::StackName}-cache-subnet'
      Description: Subnet group for ElastiCache
      SubnetIds: !Split [',', !ImportValue 'network-stack-PrivateSubnets']

  # ── Redis Parameter Group ─────────────────────────────
  CacheParameterGroup:
    Type: AWS::ElastiCache::ParameterGroup
    Properties:
      CacheParameterGroupFamily: redis7
      Description: Redis 7 parameter group
      Properties:
        maxmemory-policy: allkeys-lru      # Evict LRU keys when full
        activerehashing: "yes"
        notify-keyspace-events: "Ex"       # Keyspace events for TTL expiry
        timeout: "300"                     # Close idle connections after 5 min

  # ── Redis Replication Group ───────────────────────────
  RedisCluster:
    Type: AWS::ElastiCache::ReplicationGroup
    Properties:
      ReplicationGroupId: !Sub '${AWS::StackName}-redis'
      ReplicationGroupDescription: Redis cluster for caching and sessions
      Engine: redis
      EngineVersion: "7.1"
      CacheNodeType: !If [IsProd, cache.r7g.medium, cache.t4g.micro]
      NumCacheClusters: !If [IsProd, 3, 1]    # Multi-AZ for prod
      CacheParameterGroupName: !Ref CacheParameterGroup
      CacheSubnetGroupName: !Ref CacheSubnetGroup
      SecurityGroupIds:
        - !Ref CacheSecurityGroup
      MultiAZEnabled: !If [IsProd, true, false]
      AutomaticFailoverEnabled: !If [IsProd, true, false]
      AtRestEncryptionEnabled: true
      TransitEncryptionEnabled: true
      TransitEncryptionMode: required
      AuthToken: !If
        - IsProd
        - !Sub '{{resolve:secretsmanager:${AWS::StackName}/redis-auth-token}}'
        - !Ref AWS::NoValue
      SnapshotRetentionLimit: !If [IsProd, 7, 1]
      SnapshotWindow: "03:00-04:00"
      PreferredMaintenanceWindow: "sun:05:00-sun:06:00"
      Tags:
        - Key: Environment
          Value: !Ref Environment

Outputs:
  AuroraClusterEndpoint:
    Value: !GetAtt AuroraCluster.Endpoint.Address
    Export:
      Name: !Sub '${AWS::StackName}-DBEndpoint'

  AuroraReaderEndpoint:
    Value: !GetAtt AuroraCluster.ReadEndpoint.Address
    Export:
      Name: !Sub '${AWS::StackName}-DBReaderEndpoint'

  RDSProxyEndpoint:
    Condition: IsProd
    Value: !GetAtt RDSProxy.Endpoint
    Export:
      Name: !Sub '${AWS::StackName}-DBProxyEndpoint'

  OrdersTableName:
    Value: !Ref OrdersTable
    Export:
      Name: !Sub '${AWS::StackName}-OrdersTableName'

  RedisPrimaryEndpoint:
    Value: !GetAtt RedisCluster.PrimaryEndPoint.Address
    Export:
      Name: !Sub '${AWS::StackName}-RedisEndpoint'
```

---

## 7.4 Interview Q&A

**Q: What is `ManageMasterUserPassword` in Aurora and why use it?**
A: When `ManageMasterUserPassword: true`, AWS automatically creates and manages the master user password in AWS Secrets Manager, including auto-rotation every 7 days by default. This means: no need to pass a password as a parameter (no risk of it being logged), automatic rotation reduces credential exposure, the secret ARN is available as `!GetAtt AuroraCluster.MasterUserSecret.SecretArn`. Use this for new Aurora/RDS clusters instead of `MasterUserPassword` parameter with `NoEcho`.

**Q: What is the DynamoDB single-table design and why would you use it in CloudFormation?**
A: Single-table design stores multiple entity types in one DynamoDB table using generic PK/SK naming (pk, sk) with prefixes like "USER#userId" or "ORDER#orderId". In CloudFormation, this means one table handles all data access patterns. Benefits: fewer DynamoDB tables to manage, atomic transactions across entity types, fewer API calls for related data. The GSIs enable different access patterns without relying on table scans. Define GSI projections carefully — `KEYS_ONLY` and `INCLUDE` are cheaper than `ALL` (which duplicates data in GSIs).

**Q: What is DeletionPolicy: Snapshot vs Retain for RDS?**
A: `DeletionPolicy: Snapshot` takes a final DB snapshot before deleting the stack — you can restore from it later. The snapshot persists and incurs storage costs. `DeletionPolicy: Retain` skips deletion and leaves the DB running (costs continue). `Delete` immediately destroys the DB with no recovery option. For production RDS/Aurora, always use `Snapshot` — it protects against accidental stack deletion while eventually allowing cost cleanup (delete the snapshot when no longer needed). Also set `DeletionProtection: true` on the Aurora cluster as a defense-in-depth measure.
