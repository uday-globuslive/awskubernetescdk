# Chapter 4: Storage — S3, EBS, EFS, FSx & Glacier

## AWS SysOps Administrator Exam Domain Coverage
- **Domain 2**: Reliability and Business Continuity (partial — backup/DR)
- **Domain 3**: Deployment, Provisioning (partial — storage provisioning)
- **Domain 4**: Security and Compliance (S3 security)
- **Domain 6**: Cost Optimization (storage class selection)

---

## 4.1 AWS Storage Overview

```
┌─────────────────────────────────────────────────────────────┐
│                   AWS STORAGE TYPES                          │
│                                                             │
│  OBJECT STORAGE          BLOCK STORAGE     FILE STORAGE    │
│  ┌─────────────┐         ┌───────────┐    ┌────────────┐   │
│  │  Amazon S3  │         │ Amazon EBS│    │ Amazon EFS │   │
│  │             │         │           │    │            │   │
│  │ Flat, key-  │         │ Disk      │    │ NFS-based  │   │
│  │ value store │         │ volumes   │    │ shared FS  │   │
│  │ Unlimited   │         │ 1 AZ      │    │ Multi-AZ   │   │
│  │ Web-scale   │         │ attached  │    │ elastic    │   │
│  └─────────────┘         │ to EC2    │    └────────────┘   │
│                          └───────────┘                      │
│  ARCHIVE                 NFS/SMB             HYBRID         │
│  ┌─────────────┐         ┌───────────┐    ┌────────────┐   │
│  │  S3 Glacier │         │ Amazon FSx│    │  Storage   │   │
│  │             │         │           │    │  Gateway   │   │
│  │ Long-term   │         │ Windows,  │    │            │   │
│  │ archive     │         │ Lustre,   │    │ On-prem    │   │
│  │ Cheap       │         │ NetApp,   │    │ to AWS     │   │
│  └─────────────┘         │ OpenZFS   │    └────────────┘   │
│                          └───────────┘                      │
└─────────────────────────────────────────────────────────────┘
```

---

## 4.2 Amazon S3 Deep Dive

S3 is an **object storage** service offering 99.999999999% (11 nines) of durability.

### Core Concepts
- **Bucket**: Container for objects. Name is **globally unique** across all AWS.
- **Object**: File + metadata. Max size 5 TB. Upload >5 GB requires multipart upload.
- **Key**: The full path to the object (`photos/2025/vacation.jpg`)
- **S3 is NOT a filesystem** — no true folders, just key prefixes

```bash
# Create bucket (region must be specified for non us-east-1)
aws s3api create-bucket \
  --bucket my-unique-bucket-name \
  --region us-west-2 \
  --create-bucket-configuration LocationConstraint=us-west-2

# Enable versioning
aws s3api put-bucket-versioning \
  --bucket my-bucket \
  --versioning-configuration Status=Enabled

# Block all public access (recommended baseline)
aws s3api put-public-access-block \
  --bucket my-bucket \
  --public-access-block-configuration \
    BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true

# Upload with server-side encryption
aws s3 cp local-file.txt s3://my-bucket/ \
  --sse aws:kms \
  --sse-kms-key-id arn:aws:kms:us-east-1:123456789012:key/key-id

# Sync local directory to S3 (only uploads changed files)
aws s3 sync ./dist s3://my-website-bucket \
  --delete \
  --cache-control "max-age=86400"
```

### S3 Storage Classes

| Storage Class | Use Case | Min Storage | Min Duration | Retrieval | Cost |
|--------------|---------|-------------|-------------|-----------|------|
| **Standard** | Frequently accessed | None | None | Instant | $$$ |
| **Intelligent-Tiering** | Unknown/changing access | None | None | Instant | $$ + monitoring fee |
| **Standard-IA** | Infrequent but instant retrieval | 128 KB | 30 days | Instant | $$ |
| **One Zone-IA** | IA, can recreate if AZ fails | 128 KB | 30 days | Instant | $ |
| **Glacier Instant** | Archive with instant retrieval | 128 KB | 90 days | Instant (ms) | $ |
| **Glacier Flexible** | Archive, minutes-to-hours retrieval | 40 KB | 90 days | 1-12 hours | $$ |
| **Glacier Deep Archive** | Long-term archive 7-10 years | 40 KB | 180 days | 12-48 hours | Cheapest |

### S3 Lifecycle Policies
```json
{
  "Rules": [
    {
      "ID": "log-lifecycle",
      "Status": "Enabled",
      "Filter": {
        "Prefix": "logs/"
      },
      "Transitions": [
        {
          "Days": 30,
          "StorageClass": "STANDARD_IA"
        },
        {
          "Days": 90,
          "StorageClass": "GLACIER"
        },
        {
          "Days": 365,
          "StorageClass": "DEEP_ARCHIVE"
        }
      ],
      "Expiration": {
        "Days": 2555
      },
      "NoncurrentVersionTransitions": [
        {
          "NoncurrentDays": 30,
          "StorageClass": "GLACIER"
        }
      ],
      "NoncurrentVersionExpiration": {
        "NoncurrentDays": 90
      }
    }
  ]
}
```

```bash
# Apply lifecycle policy
aws s3api put-bucket-lifecycle-configuration \
  --bucket my-bucket \
  --lifecycle-configuration file://lifecycle.json
```

---

## 4.3 S3 Security

### Bucket Policy vs ACL vs Block Public Access

| Feature | Scope | When to Use |
|---------|-------|------------|
| **Block Public Access** | Bucket/Account level | ALWAYS enable unless intentional public bucket |
| **Bucket Policy** (resource-based) | Bucket level | Cross-account, IP restrictions, HTTPS enforce |
| **IAM Policy** (identity-based) | Identity level | Same-account access control |
| **ACL** (legacy) | Object/Bucket | Avoid; use bucket policies instead |

### Enforcing S3 Security Best Practices

**1. Require encrypted transport (HTTPS only):**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DenyNonHTTPS",
      "Effect": "Deny",
      "Principal": "*",
      "Action": "s3:*",
      "Resource": [
        "arn:aws:s3:::my-bucket",
        "arn:aws:s3:::my-bucket/*"
      ],
      "Condition": {
        "Bool": {"aws:SecureTransport": "false"}
      }
    }
  ]
}
```

**2. Require server-side encryption:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DenyUnencryptedPuts",
      "Effect": "Deny",
      "Principal": "*",
      "Action": "s3:PutObject",
      "Resource": "arn:aws:s3:::my-bucket/*",
      "Condition": {
        "StringNotEquals": {
          "s3:x-amz-server-side-encryption": "aws:kms"
        }
      }
    }
  ]
}
```

**3. Enable default encryption:**
```bash
aws s3api put-bucket-encryption \
  --bucket my-bucket \
  --server-side-encryption-configuration '{
    "Rules": [{
      "ApplyServerSideEncryptionByDefault": {
        "SSEAlgorithm": "aws:kms",
        "KMSMasterKeyID": "arn:aws:kms:us-east-1:123456789012:key/key-id"
      },
      "BucketKeyEnabled": true
    }]
  }'
```

### S3 Access Points
Access points simplify access control for shared buckets (e.g., multiple teams/applications sharing a data lake):

```bash
# Create access point for analytics team
aws s3control create-access-point \
  --account-id 123456789012 \
  --name analytics-ap \
  --bucket my-data-lake \
  --vpc-configuration VpcId=vpc-0123456789abcdef0

# Access point policy (restrict to specific prefix)
aws s3control put-access-point-policy \
  --account-id 123456789012 \
  --name analytics-ap \
  --policy '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"AWS": "arn:aws:iam::123456789012:role/AnalyticsRole"},
      "Action": ["s3:GetObject", "s3:ListBucket"],
      "Resource": [
        "arn:aws:s3:us-east-1:123456789012:accesspoint/analytics-ap",
        "arn:aws:s3:us-east-1:123456789012:accesspoint/analytics-ap/object/raw/*"
      ]
    }]
  }'
```

### S3 Object Lock & MFA Delete
For compliance (WORM — Write Once Read Many):

```bash
# Enable Object Lock on bucket (must be done at creation)
aws s3api create-bucket \
  --bucket compliance-bucket \
  --object-lock-enabled-for-bucket

# Set default retention (Governance or Compliance mode)
aws s3api put-object-lock-configuration \
  --bucket compliance-bucket \
  --object-lock-configuration '{
    "ObjectLockEnabled": "Enabled",
    "Rule": {
      "DefaultRetention": {
        "Mode": "COMPLIANCE",
        "Days": 365
      }
    }
  }'

# Enable MFA Delete (additional protection against delete)
aws s3api put-bucket-versioning \
  --bucket my-bucket \
  --versioning-configuration Status=Enabled,MFADelete=Enabled \
  --mfa "arn:aws:iam::123456789012:mfa/root-mfa 123456"
```

---

## 4.4 S3 Replication

### Cross-Region Replication (CRR) vs Same-Region Replication (SRR)

| Feature | CRR | SRR |
|---------|-----|-----|
| Purpose | DR, lower latency for global users | Log aggregation, dev/test copies |
| Replication | Asynchronous (near real-time) | Asynchronous |
| Versioning required | Both source and destination | Both source and destination |
| Existing objects | Not replicated by default | Not replicated by default |

```bash
# Enable CRR (source bucket must have versioning enabled)
aws s3api put-bucket-replication \
  --bucket source-bucket \
  --replication-configuration '{
    "Role": "arn:aws:iam::123456789012:role/S3ReplicationRole",
    "Rules": [
      {
        "ID": "replicate-all",
        "Status": "Enabled",
        "Filter": {},
        "Destination": {
          "Bucket": "arn:aws:s3:::destination-bucket",
          "StorageClass": "STANDARD_IA",
          "ReplicationTime": {
            "Status": "Enabled",
            "Time": {"Minutes": 15}
          },
          "Metrics": {
            "Status": "Enabled",
            "EventThreshold": {"Minutes": 15}
          }
        },
        "DeleteMarkerReplication": {"Status": "Enabled"}
      }
    ]
  }'

# Replicate existing objects (batch operation)
aws s3control create-job \
  --account-id 123456789012 \
  --operation '{"S3ReplicateObject":{}}' \
  --report '{"Bucket":"arn:aws:s3:::report-bucket","Format":"Report_CSV_20180820","Enabled":true,"ReportScope":"AllTasks"}' \
  --manifest-generator '{"S3JobManifestGenerator":{"SourceBucket":"arn:aws:s3:::source-bucket","EnableManifestOutput":false,"Filter":{"EligibleForReplication":true}}}' \
  --priority 10 \
  --role-arn arn:aws:iam::123456789012:role/BatchReplicationRole
```

---

## 4.5 S3 Performance Optimization

### Upload Optimization
- **Multipart Upload**: Required for >5 GB, recommended for >100 MB. Parallel uploads.
- **S3 Transfer Acceleration**: Route uploads via CloudFront edge locations.

```bash
# Multipart upload (Python)
import boto3
from boto3.s3.transfer import TransferConfig

s3 = boto3.client('s3')
config = TransferConfig(
    multipart_threshold=1024 * 25,      # 25 MB threshold
    max_concurrency=10,
    multipart_chunksize=1024 * 25,      # 25 MB chunks
    use_threads=True
)

s3.upload_file(
    'large-file.zip',
    'my-bucket',
    'uploads/large-file.zip',
    Config=config
)
```

### Read Optimization
- **S3 Byte-Range Fetches**: Parallelize downloads by requesting specific ranges
- **S3 Select**: Query CSV/JSON/Parquet data server-side (reduces data transfer)
- **Prefix Partitioning**: Distribute requests across multiple prefixes

```bash
# S3 Select — query CSV data without downloading entire file
aws s3api select-object-content \
  --bucket my-bucket \
  --key data/sales-2025.csv \
  --expression "SELECT * FROM s3object WHERE country = 'US' AND amount > 1000" \
  --expression-type SQL \
  --input-serialization '{"CSV":{"FileHeaderInfo":"Use"}}' \
  --output-serialization '{"CSV":{}}' \
  /tmp/result.csv
```

---

## 4.6 S3 Event Notifications & Operations

### S3 Event Notifications
```bash
# Trigger Lambda on object creation
aws s3api put-bucket-notification-configuration \
  --bucket my-bucket \
  --notification-configuration '{
    "LambdaFunctionConfigurations": [
      {
        "LambdaFunctionArn": "arn:aws:lambda:us-east-1:123456789012:function:ProcessUpload",
        "Events": ["s3:ObjectCreated:*"],
        "Filter": {
          "Key": {
            "FilterRules": [
              {"Name": "prefix", "Value": "uploads/"},
              {"Name": "suffix", "Value": ".jpg"}
            ]
          }
        }
      }
    ]
  }'
```

### S3 Batch Operations
```bash
# Run a batch job across millions of objects (e.g., encrypt all unencrypted objects)
aws s3control create-job \
  --account-id 123456789012 \
  --operation '{
    "S3PutObjectCopy": {
      "TargetBucket": "arn:aws:s3:::my-bucket",
      "StorageClass": "STANDARD",
      "NewObjectMetadata": {},
      "ServerSideEncryptionConfiguration": {
        "ServerSideEncryptionByDefault": {"SSEAlgorithm":"aws:kms"}
      }
    }
  }' \
  --manifest '{"Spec":{"Format":"S3BatchOperations_CSV_20180820","Fields":["Bucket","Key"]},"Location":{"ObjectArn":"arn:aws:s3:::manifest-bucket/manifest.csv","ETag":"xxxx"}}' \
  --priority 10 \
  --role-arn arn:aws:iam::123456789012:role/BatchOperationsRole \
  --report '{"Enabled":true,"Bucket":"arn:aws:s3:::report-bucket","ReportScope":"AllTasks","Format":"Report_CSV_20180820"}'
```

---

## 4.7 Amazon EFS — Elastic File System

EFS provides a **managed NFS (Network File System)** shared across multiple EC2 instances and containers.

### EFS vs EBS vs S3

| Feature | EFS | EBS | S3 |
|---------|-----|-----|-----|
| Type | File | Block | Object |
| Access | Multi-instance (NFS) | Single instance | Internet/API |
| AZ | Multi-AZ | Single AZ | Regional |
| Scalability | Automatic, petabyte-scale | Manual resize | Unlimited |
| Protocol | NFS v4.1 | N/A | HTTP REST |
| Use Case | Shared app data, CMS, CI/CD | OS disk, DB volumes | Static files, backups, archives |
| Cost | $$$$ | $$ | $ |

### EFS Performance Modes
| Mode | Use Case |
|------|---------|
| **General Purpose** (default) | Web serving, CMS, dev environments |
| **Max I/O** | Big data, media processing, high throughput with many clients |

### EFS Throughput Modes
| Mode | Description |
|------|-------------|
| **Bursting** | Throughput scales with storage size. 50 MiB/s per TB stored. |
| **Provisioned** | Set throughput independently of storage size |
| **Elastic** (recommended) | Auto-scales up to 3 GiB/s read, 1 GiB/s write per file system |

```bash
# Create EFS file system
aws efs create-file-system \
  --performance-mode generalPurpose \
  --throughput-mode elastic \
  --encrypted \
  --kms-key-id arn:aws:kms:us-east-1:123456789012:key/key-id \
  --tags Key=Name,Value=my-efs

# Create mount targets (one per AZ)
for subnet in subnet-aaa subnet-bbb subnet-ccc; do
  aws efs create-mount-target \
    --file-system-id fs-0123456789abcdef0 \
    --subnet-id $subnet \
    --security-groups sg-efs-sg
done

# Mount on EC2 (requires amazon-efs-utils)
sudo yum install -y amazon-efs-utils
sudo mkdir /mnt/efs
sudo mount -t efs -o tls fs-0123456789abcdef0:/ /mnt/efs

# Add to /etc/fstab for persistence
echo "fs-0123456789abcdef0:/ /mnt/efs efs _netdev,tls,iam 0 0" | sudo tee -a /etc/fstab
```

### EFS Access Points
Control access to specific directories with different POSIX permissions:
```bash
# Create access point for specific app directory
aws efs create-access-point \
  --file-system-id fs-0123456789abcdef0 \
  --posix-user Uid=1000,Gid=1000 \
  --root-directory 'Path=/app-data,CreationInfo={OwnerUid=1000,OwnerGid=1000,Permissions=755}' \
  --tags Key=Name,Value=app-access-point
```

### EFS with Lambda
```python
# Lambda function accessing EFS (requires VPC and mount target)
import os

# EFS is mounted at /mnt/efs in Lambda
EFS_MOUNT = '/mnt/efs'

def lambda_handler(event, context):
    # Read a shared model file from EFS
    model_path = os.path.join(EFS_MOUNT, 'models', 'my_model.pkl')
    
    if os.path.exists(model_path):
        with open(model_path, 'rb') as f:
            model = pickle.load(f)  # Shared across Lambda invocations
        return {'status': 'model loaded', 'size': os.path.getsize(model_path)}
    else:
        return {'status': 'model not found'}
```

---

## 4.8 Amazon FSx

FSx provides **fully managed third-party file systems**:

| FSx Type | Protocol | Use Case |
|----------|---------|---------|
| **FSx for Windows File Server** | SMB | Windows apps, Active Directory, .NET, Microsoft SQL Server |
| **FSx for Lustre** | Lustre | HPC, ML training, video processing, high-throughput |
| **FSx for NetApp ONTAP** | NFS, SMB, iSCSI | Enterprise storage, hybrid, multi-protocol |
| **FSx for OpenZFS** | NFS | Linux workloads, Oracle databases |

```bash
# Create FSx for Windows
aws fsx create-file-system \
  --file-system-type WINDOWS \
  --storage-capacity 300 \
  --subnet-ids subnet-aaa subnet-bbb \
  --windows-configuration '{
    "ActiveDirectoryId": "d-1234567890",
    "ThroughputCapacity": 32,
    "AutomaticBackupRetentionDays": 7,
    "DeploymentType": "MULTI_AZ_1",
    "PreferredSubnetId": "subnet-aaa"
  }'

# Create FSx for Lustre (linked to S3 for data repository)
aws fsx create-file-system \
  --file-system-type LUSTRE \
  --storage-capacity 1200 \
  --subnet-ids subnet-aaa \
  --lustre-configuration '{
    "ImportPath": "s3://ml-training-data",
    "ExportPath": "s3://ml-training-data/output",
    "DeploymentType": "PERSISTENT_2",
    "PerUnitStorageThroughput": 250
  }'
```

---

## 4.9 AWS Storage Gateway

Connects **on-premises applications** to AWS cloud storage:

```
On-Premises Data Center         AWS
┌──────────────────┐           ┌──────────────────────┐
│  Servers         │           │                      │
│  ┌────────────┐  │  iSCSI    │  AWS Storage         │
│  │ File GW    │──┼──────────►│  Gateway (EBS/S3/    │
│  │ (NFS/SMB)  │  │  NFS/SMB  │  Glacier)            │
│  └────────────┘  │           │                      │
│                  │           │  ┌────────────────┐  │
│  ┌────────────┐  │  iSCSI    │  │  S3 Standard   │  │
│  │ Volume GW  │──┼──────────►│  │  S3 Glacier    │  │
│  │ (iSCSI)    │  │           │  │  EBS Snapshots │  │
│  └────────────┘  │           │  └────────────────┘  │
│                  │           │                      │
│  ┌────────────┐  │  VTL      │                      │
│  │  Tape GW   │──┼──────────►│  Glacier Virtual     │
│  │ (VTL)      │  │           │  Tape Library        │
│  └────────────┘  │           └──────────────────────┘
└──────────────────┘
```

| Gateway Type | Protocol | Backs to | Use Case |
|-------------|---------|----------|---------|
| **File Gateway** | NFS, SMB | S3 | Replace on-prem NAS, migrate files to S3 |
| **Volume Gateway** | iSCSI | S3+EBS Snapshots | Block storage backup, DR |
| **Tape Gateway** | iSCSI (VTL) | S3 Glacier | Replace tape backup infrastructure |

---

## 4.10 S3 Versioning & Data Protection

### Versioning
```bash
# Enable versioning
aws s3api put-bucket-versioning \
  --bucket my-bucket \
  --versioning-configuration Status=Enabled

# List all versions of an object
aws s3api list-object-versions \
  --bucket my-bucket \
  --prefix my-file.txt

# Restore a previous version (copy to same key)
aws s3api copy-object \
  --bucket my-bucket \
  --copy-source my-bucket/my-file.txt?versionId=abc123 \
  --key my-file.txt

# Delete specific version permanently
aws s3api delete-object \
  --bucket my-bucket \
  --key my-file.txt \
  --version-id abc123
```

### Delete Markers
When versioning is enabled, deleting an object places a **delete marker** — the object still exists but is "hidden". To truly delete:
- Delete the delete marker to restore the object
- Delete all versions + markers to permanently remove

```bash
# Remove all delete markers and versions (cleanup script)
aws s3api list-object-versions \
  --bucket my-bucket \
  --query 'Versions[*].{Key:Key,VersionId:VersionId}' \
  --output json | \
  jq -r '.[] | "--bucket my-bucket --key \(.Key) --version-id \(.VersionId)"' | \
  xargs -I{} aws s3api delete-object {}
```

---

## 4.11 AWS Backup

AWS Backup is a **centralized managed backup service** for many AWS services:

Supported: EC2, EBS, EFS, FSx, RDS, Aurora, DynamoDB, DocumentDB, Neptune, S3, Storage Gateway

```bash
# Create backup vault with KMS encryption
aws backup create-backup-vault \
  --backup-vault-name production-vault \
  --encryption-key-arn arn:aws:kms:us-east-1:123456789012:key/key-id

# Create backup plan
aws backup create-backup-plan \
  --backup-plan '{
    "BackupPlanName": "daily-weekly-monthly",
    "Rules": [
      {
        "RuleName": "daily",
        "TargetBackupVaultName": "production-vault",
        "ScheduleExpression": "cron(0 5 ? * * *)",
        "StartWindowMinutes": 60,
        "CompletionWindowMinutes": 120,
        "Lifecycle": {
          "MoveToColdStorageAfterDays": 30,
          "DeleteAfterDays": 365
        },
        "CopyActions": [{
          "DestinationBackupVaultArn": "arn:aws:backup:us-west-2:123456789012:backup-vault:dr-vault",
          "Lifecycle": {"DeleteAfterDays": 365}
        }]
      },
      {
        "RuleName": "monthly",
        "TargetBackupVaultName": "production-vault",
        "ScheduleExpression": "cron(0 5 1 * ? *)",
        "Lifecycle": {
          "DeleteAfterDays": 2555
        }
      }
    ]
  }'

# Assign resources to backup plan (all resources with tag)
aws backup create-backup-selection \
  --backup-plan-id plan-id \
  --backup-selection '{
    "SelectionName": "production-resources",
    "IamRoleArn": "arn:aws:iam::123456789012:role/AWSBackupDefaultServiceRole",
    "ListOfTags": [{"ConditionType":"STRINGEQUALS","ConditionKey":"Backup","ConditionValue":"true"}]
  }'
```

---

## 4.12 Real-World Project: S3 Data Lake with Lifecycle Management

### Scenario
A media company stores 100TB+ of video content. Need to:
1. Automatically move files to cheaper storage over time
2. Secure access with encryption and per-team access points
3. Replicate to DR region
4. Enable compliance archiving (7-year retention)

### Architecture
```
Ingest → S3 Standard (0-30 days)
              ↓ (30 days)
         S3 Standard-IA (30-90 days)
              ↓ (90 days)
         S3 Glacier Instant (90-365 days)
              ↓ (365 days)
         S3 Glacier Deep Archive (1-7 years)
              ↓ (7 years)
         Deleted (expires)

Cross-Region: All objects → DR region S3 (same lifecycle)
```

### CloudFormation Template
```yaml
AWSTemplateFormatVersion: '2010-09-09'
Description: S3 Data Lake with lifecycle, replication, and security

Resources:
  DataLakeKey:
    Type: AWS::KMS::Key
    Properties:
      Description: KMS key for data lake encryption
      EnableKeyRotation: true
      KeyPolicy:
        Version: '2012-10-17'
        Statement:
          - Effect: Allow
            Principal:
              AWS: !Sub arn:aws:iam::${AWS::AccountId}:root
            Action: kms:*
            Resource: '*'

  DataLakeBucket:
    Type: AWS::S3::Bucket
    Properties:
      BucketName: !Sub company-data-lake-${AWS::AccountId}
      VersioningConfiguration:
        Status: Enabled
      BucketEncryption:
        ServerSideEncryptionConfiguration:
          - ServerSideEncryptionByDefault:
              SSEAlgorithm: aws:kms
              KMSMasterKeyID: !Ref DataLakeKey
            BucketKeyEnabled: true
      PublicAccessBlockConfiguration:
        BlockPublicAcls: true
        BlockPublicPolicy: true
        IgnorePublicAcls: true
        RestrictPublicBuckets: true
      ReplicationConfiguration:
        Role: !GetAtt ReplicationRole.Arn
        Rules:
          - Id: replicate-all
            Status: Enabled
            Destination:
              Bucket: !Sub arn:aws:s3:::company-data-lake-dr-${AWS::AccountId}
              StorageClass: STANDARD_IA
              ReplicationTime:
                Status: Enabled
                Time:
                  Minutes: 15
              Metrics:
                Status: Enabled
                EventThreshold:
                  Minutes: 15
            DeleteMarkerReplication:
              Status: Enabled
      LifecycleConfiguration:
        Rules:
          - Id: media-lifecycle
            Status: Enabled
            Transitions:
              - TransitionInDays: 30
                StorageClass: STANDARD_IA
              - TransitionInDays: 90
                StorageClass: GLACIER_IR
              - TransitionInDays: 365
                StorageClass: DEEP_ARCHIVE
            Expiration:
              Days: 2555
          - Id: expire-temp-uploads
            Status: Enabled
            Prefix: temp/
            Expiration:
              Days: 7
          - Id: abort-incomplete-multipart
            Status: Enabled
            AbortIncompleteMultipartUpload:
              DaysAfterInitiation: 7
      NotificationConfiguration:
        LambdaConfigurations:
          - Event: s3:ObjectCreated:*
            Filter:
              S3Key:
                Rules:
                  - Name: prefix
                    Value: uploads/
            Function: !GetAtt ProcessUploadFunction.Arn
      Tags:
        - Key: DataClassification
          Value: Confidential
        - Key: CostCenter
          Value: Media
```

---

## 4.13 Practice Questions (SysOps Exam Level)

**Q1:** An S3 bucket has versioning enabled. A user accidentally deletes a critical object. How do you recover it?

**A:** Deleting a versioned object places a **delete marker**. The object still exists as an older version. To recover:

```bash
# Find the delete marker
aws s3api list-object-versions \
  --bucket my-bucket \
  --prefix deleted-file.txt \
  --query 'DeleteMarkers[*].{VersionId:VersionId}'

# Remove the delete marker (restores the object)
aws s3api delete-object \
  --bucket my-bucket \
  --key deleted-file.txt \
  --version-id delete-marker-version-id
```

---

**Q2:** Your company needs to ensure that all objects in an S3 bucket are encrypted with a specific KMS key. Objects uploaded without encryption should be rejected. How do you implement this?

**A:**
1. Set **default bucket encryption** with the KMS key
2. Add a **bucket policy** that denies PUT without encryption:

```json
{
  "Sid": "DenyUnencrypted",
  "Effect": "Deny",
  "Principal": "*",
  "Action": "s3:PutObject",
  "Resource": "arn:aws:s3:::my-bucket/*",
  "Condition": {
    "StringNotEquals": {
      "s3:x-amz-server-side-encryption-aws-kms-key-id": 
        "arn:aws:kms:us-east-1:123456789012:key/specific-key-id"
    }
  }
}
```

---

**Q3:** Which S3 storage class should you use for compliance data that must be retained for 7 years but rarely accessed, and must be available within 12 hours when requested?

**A:** **S3 Glacier Deep Archive** — cheapest option, 12-48 hour retrieval, 180-day minimum retention, suitable for regulatory compliance archiving.

---

**Q4:** An application on EC2 instances in 3 different AZs needs to share a common file system. Which AWS storage service should you use?

**A:** **Amazon EFS** — provides a managed NFS share that can be mounted simultaneously by EC2 instances across multiple AZs. EBS cannot be shared across AZs (EBS Multi-Attach is single AZ and limited to io1/io2). S3 is object storage and not a filesystem.

---

**Q5:** You need to migrate 500 TB of files from an on-premises NAS to S3 over the next month. What is the fastest and most cost-effective method?

**A:**
- If network bandwidth allows: **AWS DataSync** (syncs NFS/SMB to S3 over internet/Direct Connect, up to 10x faster than manual copy)
- If network is insufficient (<1 Gbps sustained): **AWS Snowball Edge** (petabyte-scale physical device shipped to your location)
- For very large amounts (>1 PB): **AWS Snowmobile** (truck-sized exabyte device)

```bash
# DataSync agent deployed on-premises, create task
aws datasync create-task \
  --source-location-arn arn:aws:datasync:us-east-1:123456789012:location/loc-xxx \
  --destination-location-arn arn:aws:datasync:us-east-1:123456789012:location/loc-yyy \
  --name "nas-to-s3-migration" \
  --options '{"PreserveDeletedFiles":"PRESERVE","VerifyMode":"ONLY_FILES_TRANSFERRED"}'
```

---

## Key Storage Terms for Exam

| Term | Definition |
|------|-----------|
| S3 | Object storage; globally unique bucket name |
| EBS | Block storage; attached to one EC2 per AZ |
| EFS | NFS shared file system; multi-AZ, elastic |
| FSx | Managed 3rd-party file systems (Windows, Lustre) |
| S3 Glacier | Archive storage; lowest cost |
| Lifecycle Policy | Automate object transitions between storage classes |
| Versioning | Keep multiple versions of same object |
| MFA Delete | Require MFA to permanently delete objects |
| Object Lock | WORM compliance; prevent object deletion/modification |
| Replication | Async copy to another bucket (same/different region) |
| S3 Select | Query data inside objects without downloading all |
| Storage Gateway | Hybrid storage connecting on-premises to AWS |
| AWS Backup | Centralized managed backup service for AWS resources |
| DataSync | Fast data transfer between on-premises and AWS |
