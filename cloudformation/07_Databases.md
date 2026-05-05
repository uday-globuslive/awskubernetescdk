# Chapter 7: Databases
## RDS, DynamoDB & ElastiCache in CloudFormation

---

## 7.1 RDS — Aurora PostgreSQL

```yaml
# databases.yaml — RDS Aurora + DynamoDB + ElastiCache
AWSTemplateFormatVersion: "2010-09-09"
Description: Database layer — Aurora PostgreSQL, DynamoDB, ElastiCache Redis

Parameters:
  NetworkingStack:
    Type: String
    Description: Networking stack name for cross-stack imports

  Environment:
    Type: String
    Default: dev
    AllowedValues: [dev, staging, prod]

  DBName:
    Type: String
    Default: appdb

  DBUsername:
    Type: String
    Default: dbadmin

  DBPassword:
    Type: String
    NoEcho: true
    MinLength: 8

  DBInstanceClass:
    Type: String
    Default: db.t3.medium
    AllowedValues: [db.t3.micro, db.t3.medium, db.r6g.large, db.r6g.xlarge]

Conditions:
  IsProd: !Equals [!Ref Environment, prod]
  IsMultiAZ: !Equals [!Ref Environment, prod]

Resources:

  # ============================================================
  # SECURITY GROUP FOR RDS
  # ============================================================
  DBSecurityGroup:
    Type: AWS::EC2::SecurityGroup
    Properties:
      GroupDescription: RDS security group
      VpcId: !ImportValue
        Fn::Sub: "${NetworkingStack}-VpcId"
      Tags:
        - Key: Name
          Value: !Sub "${AWS::StackName}-db-sg"

  # Allow DB access only from application security group
  # (Add rule separately to avoid circular dependency)
  DBSecurityGroupIngress:
    Type: AWS::EC2::SecurityGroupIngress
    Properties:
      GroupId: !Ref DBSecurityGroup
      IpProtocol: tcp
      FromPort: 5432
      ToPort: 5432
      CidrIp: !ImportValue
        Fn::Sub: "${NetworkingStack}-VpcCidr"
      Description: PostgreSQL from VPC

  # ============================================================
  # RDS SUBNET GROUP
  # ============================================================
  DBSubnetGroup:
    Type: AWS::RDS::DBSubnetGroup
    Properties:
      DBSubnetGroupDescription: DB subnet group
      SubnetIds:
        - !Select
          - 0
          - !Split
            - ","
            - !ImportValue
              Fn::Sub: "${NetworkingStack}-DBSubnets"
        - !Select
          - 1
          - !Split
            - ","
            - !ImportValue
              Fn::Sub: "${NetworkingStack}-DBSubnets"
      Tags:
        - Key: Name
          Value: !Sub "${AWS::StackName}-db-subnet-group"

  # ============================================================
  # RDS PARAMETER GROUP
  # ============================================================
  DBParameterGroup:
    Type: AWS::RDS::DBParameterGroup
    Properties:
      Description: Custom PostgreSQL parameters
      Family: aurora-postgresql15
      Parameters:
        shared_preload_libraries: pg_stat_statements
        log_min_duration_statement: "1000"    # Log queries > 1s
        log_connections: "1"
        log_disconnections: "1"

  # ============================================================
  # AURORA POSTGRESQL CLUSTER
  # ============================================================
  AuroraCluster:
    Type: AWS::RDS::DBCluster
    DeletionPolicy: !If [IsProd, Snapshot, Delete]
    UpdateReplacePolicy: Snapshot
    Properties:
      DBClusterIdentifier: !Sub "${AWS::StackName}-cluster"
      Engine: aurora-postgresql
      EngineVersion: "15.3"
      DatabaseName: !Ref DBName
      MasterUsername: !Ref DBUsername
      MasterUserPassword: !Ref DBPassword
      DBSubnetGroupName: !Ref DBSubnetGroup
      VpcSecurityGroupIds:
        - !Ref DBSecurityGroup
      
      # Backup
      BackupRetentionPeriod: !If [IsProd, 7, 1]
      PreferredBackupWindow: "03:00-04:00"
      PreferredMaintenanceWindow: "sun:04:00-sun:05:00"
      
      # Encryption
      StorageEncrypted: true
      
      # Point-in-time recovery
      EnableCloudwatchLogsExports:
        - postgresql
      
      # Deletion protection
      DeletionProtection: !If [IsProd, true, false]
      
      Tags:
        - Key: Environment
          Value: !Ref Environment

  # PRIMARY INSTANCE
  AuroraPrimaryInstance:
    Type: AWS::RDS::DBInstance
    Properties:
      DBClusterIdentifier: !Ref AuroraCluster
      DBInstanceClass: !Ref DBInstanceClass
      Engine: aurora-postgresql
      DBParameterGroupName: !Ref DBParameterGroup
      AutoMinorVersionUpgrade: true
      PubliclyAccessible: false
      Tags:
        - Key: Name
          Value: !Sub "${AWS::StackName}-primary"

  # REPLICA INSTANCE (prod only)
  AuroraReplicaInstance:
    Type: AWS::RDS::DBInstance
    Condition: IsProd
    Properties:
      DBClusterIdentifier: !Ref AuroraCluster
      DBInstanceClass: !Ref DBInstanceClass
      Engine: aurora-postgresql
      AutoMinorVersionUpgrade: true
      PubliclyAccessible: false
      Tags:
        - Key: Name
          Value: !Sub "${AWS::StackName}-replica"

  # ============================================================
  # DYNAMODB TABLE
  # ============================================================
  SessionsTable:
    Type: AWS::DynamoDB::Table
    DeletionPolicy: !If [IsProd, Retain, Delete]
    Properties:
      TableName: !Sub "${AWS::StackName}-sessions"
      BillingMode: PAY_PER_REQUEST
      
      AttributeDefinitions:
        - AttributeName: sessionId
          AttributeType: S
        - AttributeName: userId
          AttributeType: S
        - AttributeName: createdAt
          AttributeType: S
      
      KeySchema:
        - AttributeName: sessionId
          KeyType: HASH
      
      GlobalSecondaryIndexes:
        - IndexName: userId-createdAt-index
          KeySchema:
            - AttributeName: userId
              KeyType: HASH
            - AttributeName: createdAt
              KeyType: RANGE
          Projection:
            ProjectionType: INCLUDE
            NonKeyAttributes:
              - sessionId
              - isValid
              - expiresAt
      
      TimeToLiveSpecification:
        AttributeName: expiresAt
        Enabled: true
      
      PointInTimeRecoverySpecification:
        PointInTimeRecoveryEnabled: !If [IsProd, true, false]
      
      SSESpecification:
        SSEEnabled: true
      
      Tags:
        - Key: Environment
          Value: !Ref Environment

  # ============================================================
  # ELASTICACHE — REDIS
  # ============================================================
  CacheSecurityGroup:
    Type: AWS::EC2::SecurityGroup
    Properties:
      GroupDescription: ElastiCache Redis security group
      VpcId: !ImportValue
        Fn::Sub: "${NetworkingStack}-VpcId"
      SecurityGroupIngress:
        - IpProtocol: tcp
          FromPort: 6379
          ToPort: 6379
          CidrIp: !ImportValue
            Fn::Sub: "${NetworkingStack}-VpcCidr"

  CacheSubnetGroup:
    Type: AWS::ElastiCache::SubnetGroup
    Properties:
      Description: ElastiCache subnet group
      SubnetIds:
        - !Select
          - 0
          - !Split
            - ","
            - !ImportValue
              Fn::Sub: "${NetworkingStack}-PrivateSubnets"
        - !Select
          - 1
          - !Split
            - ","
            - !ImportValue
              Fn::Sub: "${NetworkingStack}-PrivateSubnets"

  CacheParameterGroup:
    Type: AWS::ElastiCache::ParameterGroup
    Properties:
      Description: Redis parameters
      CacheParameterGroupFamily: redis7
      Properties:
        maxmemory-policy: allkeys-lru
        notify-keyspace-events: ""

  # REDIS REPLICATION GROUP (Multi-AZ in prod)
  RedisReplicationGroup:
    Type: AWS::ElastiCache::ReplicationGroup
    Properties:
      ReplicationGroupDescription: !Sub "${AWS::StackName} Redis cache"
      AutomaticFailoverEnabled: !If [IsProd, true, false]
      MultiAZEnabled: !If [IsProd, true, false]
      NumCacheClusters: !If [IsProd, 2, 1]
      CacheNodeType: !If [IsProd, cache.r6g.large, cache.t3.micro]
      Engine: redis
      EngineVersion: "7.0"
      CacheParameterGroupName: !Ref CacheParameterGroup
      CacheSubnetGroupName: !Ref CacheSubnetGroup
      SecurityGroupIds:
        - !Ref CacheSecurityGroup
      AtRestEncryptionEnabled: true
      TransitEncryptionEnabled: true
      Tags:
        - Key: Environment
          Value: !Ref Environment

# ============================================================
# OUTPUTS
# ============================================================
Outputs:
  DBClusterEndpoint:
    Description: Aurora cluster write endpoint
    Value: !GetAtt AuroraCluster.Endpoint.Address
    Export:
      Name: !Sub "${AWS::StackName}-DBEndpoint"

  DBClusterReadEndpoint:
    Description: Aurora cluster read endpoint
    Value: !GetAtt AuroraCluster.ReadEndpoint.Address
    Export:
      Name: !Sub "${AWS::StackName}-DBReadEndpoint"

  DBPort:
    Value: !GetAtt AuroraCluster.Endpoint.Port
    Export:
      Name: !Sub "${AWS::StackName}-DBPort"

  SessionsTableName:
    Value: !Ref SessionsTable
    Export:
      Name: !Sub "${AWS::StackName}-SessionsTable"

  RedisEndpoint:
    Value: !GetAtt RedisReplicationGroup.PrimaryEndPoint.Address
    Export:
      Name: !Sub "${AWS::StackName}-RedisEndpoint"

  RedisPort:
    Value: !GetAtt RedisReplicationGroup.PrimaryEndPoint.Port
    Export:
      Name: !Sub "${AWS::StackName}-RedisPort"
```

---

## 7.2 Deploying the Database Stack

```bash
# Deploy (dev — no read replica, minimal Redis)
aws cloudformation deploy \
  --template-file databases.yaml \
  --stack-name myapp-databases-dev \
  --parameter-overrides \
    Environment=dev \
    NetworkingStack=myapp-networking \
    DBPassword=DevPassword123! \
    DBInstanceClass=db.t3.micro \
  --capabilities CAPABILITY_IAM \
  --region us-east-1

# Deploy (prod — with replica and Multi-AZ Redis)
aws cloudformation deploy \
  --template-file databases.yaml \
  --stack-name myapp-databases-prod \
  --parameter-overrides \
    Environment=prod \
    NetworkingStack=myapp-networking-prod \
    DBPassword=ProdPassword456! \
    DBInstanceClass=db.r6g.large \
  --capabilities CAPABILITY_IAM \
  --region us-east-1

# Get DB endpoint
aws cloudformation describe-stacks \
  --stack-name myapp-databases-dev \
  --query "Stacks[0].Outputs[?OutputKey=='DBClusterEndpoint'].OutputValue" \
  --output text
```

---

## 7.3 Secrets Manager — Store DB Password in CloudFormation

```yaml
# Better approach: use Secrets Manager to auto-generate password
DBSecret:
  Type: AWS::SecretsManager::Secret
  Properties:
    Name: !Sub "${AWS::StackName}/db-credentials"
    Description: Database credentials
    GenerateSecretString:
      SecretStringTemplate: !Sub '{"username": "${DBUsername}"}'
      GenerateStringKey: password
      PasswordLength: 32
      ExcludePunctuation: true

AuroraCluster:
  Type: AWS::RDS::DBCluster
  Properties:
    MasterUsername: !Sub "{{resolve:secretsmanager:${DBSecret}:SecretString:username}}"
    MasterUserPassword: !Sub "{{resolve:secretsmanager:${DBSecret}:SecretString:password}}"

# Attach secret to RDS (enables secret rotation)
SecretAttachment:
  Type: AWS::SecretsManager::SecretTargetAttachment
  Properties:
    SecretId: !Ref DBSecret
    TargetId: !Ref AuroraCluster
    TargetType: AWS::RDS::DBCluster
```

---

## 7.4 Interview Questions

**Q: What is the difference between `DeletionPolicy: Delete` and `DeletionPolicy: Snapshot` for RDS?**
> `Delete` permanently removes the RDS instance when the stack is deleted — all data is gone, no recovery. `Snapshot` takes a final automated snapshot before deleting the instance, so you can restore the database later. For production, always use `Snapshot` combined with `DeletionProtection: true` to prevent accidental deletion. The snapshot is stored in RDS and can be used to create a new cluster. Also set `UpdateReplacePolicy: Snapshot` to snapshot the old instance when it needs to be replaced during an update.

**Q: How do you handle database passwords securely in CloudFormation?**
> Best practice: don't pass the password as a plain parameter. Instead, create a `AWS::SecretsManager::Secret` resource with `GenerateSecretString` to have Secrets Manager generate a random password. Reference it in the RDS resource using `{{resolve:secretsmanager:SecretArn:SecretString:password}}`. Then attach the secret with `SecretTargetAttachment` to enable automatic rotation. Lambda and ECS tasks retrieve the secret at runtime via `secretsmanager:GetSecretValue`, never seeing it in the template or CloudFormation console.

**Q: Why is `TimeToLiveSpecification` important for DynamoDB session tables?**
> TTL automatically deletes items when the Unix timestamp in the `expiresAt` attribute passes. Without TTL, sessions accumulate indefinitely — a table with millions of expired sessions wastes storage, increases scan costs, and degrades query performance. TTL deletions are free and happen within 48 hours of expiry. Always use TTL for anything time-bounded: sessions, cache records, one-time tokens, temporary locks. Set the attribute to a Unix epoch timestamp when writing the item.
