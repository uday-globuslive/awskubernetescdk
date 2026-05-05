# Chapter 4: Storage — S3, EBS, EFS, Glacier & Snow Family
## Object Storage, Block Storage, File Storage, Archival & Data Transfer

---

## 4.1 S3 — Simple Storage Service

S3 is AWS's core object storage service. It stores any amount of data in buckets, accessible from anywhere via HTTP/HTTPS. S3 is the backbone of many AWS services.

```
S3 Concepts:
┌──────────────────────────────────────────────────────────────────┐
│                         S3                                       │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    BUCKET (unique name globally)          │   │
│  │  my-company-backups-prod (hosted in us-east-1)           │   │
│  │                                                           │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐  │   │
│  │  │   OBJECT     │  │   OBJECT     │  │    OBJECT     │  │   │
│  │  │ Key: logs/   │  │ Key: images/ │  │ Key: backup.  │  │   │
│  │  │  app.log     │  │  logo.png    │  │  tar.gz       │  │   │
│  │  │ Size: 5.3MB  │  │ Size: 45KB   │  │ Size: 2.1GB   │  │   │
│  │  │ Metadata:... │  │ Metadata:... │  │ Metadata:...  │  │   │
│  │  └──────────────┘  └──────────────┘  └───────────────┘  │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  Object URL: https://BUCKET.s3.REGION.amazonaws.com/KEY        │
│  Object ARN: arn:aws:s3:::BUCKET/KEY                            │
└──────────────────────────────────────────────────────────────────┘

Key facts:
- Objects up to 5TB each
- Bucket names must be globally unique across all AWS accounts
- Objects stored across minimum 3 AZs (11 nines durability = 99.999999999%)
- No folder structure — key name with "/" looks like folders (just naming)
- S3 is global service but buckets are in a specific region
```

### Durability and Availability

| Class | Durability | Availability | Notes |
|-------|-----------|--------------|-------|
| Standard | 99.999999999% | 99.99% | Default for frequent access |
| Standard-IA | 99.999999999% | 99.9% | Infrequent access, min 30-day charge |
| One Zone-IA | 99.999999999% | 99.5% | Single AZ, 20% cheaper than Standard-IA |
| Glacier Instant | 99.999999999% | 99.9% | Archive, millisecond retrieval |
| Glacier Flexible | 99.999999999% | 99.99% | Archive, 1-12 hours retrieval |
| Glacier Deep Archive | 99.999999999% | 99.99% | Cheapest, 12-48 hours retrieval |
| Intelligent-Tiering | 99.999999999% | 99.9% | Auto-moves between tiers |

---

## 4.2 S3 Bucket Management

```bash
# ── BUCKET OPERATIONS ─────────────────────────────────────────
# Create bucket
aws s3api create-bucket \
  --bucket my-company-data-prod \
  --region us-east-1
  # Note: for regions other than us-east-1, add:
  # --create-bucket-configuration LocationConstraint=us-west-2

# Enable versioning (CANNOT disable once enabled, only suspend)
aws s3api put-bucket-versioning \
  --bucket my-company-data-prod \
  --versioning-configuration Status=Enabled

# Block all public access (recommended for non-static-website buckets)
aws s3api put-public-access-block \
  --bucket my-company-data-prod \
  --public-access-block-configuration \
    "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"

# Enable default server-side encryption
aws s3api put-bucket-encryption \
  --bucket my-company-data-prod \
  --server-side-encryption-configuration '{
    "Rules": [{
      "ApplyServerSideEncryptionByDefault": {
        "SSEAlgorithm": "aws:kms",
        "KMSMasterKeyID": "arn:aws:kms:us-east-1:123:key/abc123"
      },
      "BucketKeyEnabled": true
    }]
  }'

# Enable S3 access logging
aws s3api put-bucket-logging \
  --bucket my-company-data-prod \
  --bucket-logging-status '{
    "LoggingEnabled": {
      "TargetBucket": "my-access-logs-bucket",
      "TargetPrefix": "my-company-data-prod/"
    }
  }'

# Require TLS (HTTPS only) — bucket policy
aws s3api put-bucket-policy \
  --bucket my-company-data-prod \
  --policy '{
    "Version": "2012-10-17",
    "Statement": [{
      "Sid": "DenyHTTP",
      "Effect": "Deny",
      "Principal": "*",
      "Action": "s3:*",
      "Resource": [
        "arn:aws:s3:::my-company-data-prod",
        "arn:aws:s3:::my-company-data-prod/*"
      ],
      "Condition": {
        "Bool": {"aws:SecureTransport": "false"}
      }
    }]
  }'

# Enable S3 Object Lock (WORM — Write Once Read Many)
# Must be enabled at bucket creation — cannot enable later
aws s3api create-bucket \
  --bucket compliance-archive \
  --object-lock-enabled-for-bucket \
  --region us-east-1

# Set default Object Lock retention
aws s3api put-object-lock-configuration \
  --bucket compliance-archive \
  --object-lock-configuration '{
    "ObjectLockEnabled": "Enabled",
    "Rule": {
      "DefaultRetention": {
        "Mode": "COMPLIANCE",
        "Years": 7
      }
    }
  }'
```

---

## 4.3 S3 Object Operations

```bash
# ── UPLOAD / DOWNLOAD ─────────────────────────────────────────
# Upload with metadata and encryption
aws s3api put-object \
  --bucket my-bucket \
  --key data/2025/file.csv \
  --body ./file.csv \
  --server-side-encryption aws:kms \
  --metadata "created-by=pipeline,version=1.0" \
  --content-type "text/csv"

# Upload with Server-Side Encryption using bucket key
aws s3 cp file.csv s3://my-bucket/data/ \
  --sse aws:kms \
  --sse-kms-key-id alias/my-key

# Sync directory (upload changed files only)
aws s3 sync ./data/ s3://my-bucket/data/ \
  --delete \                          # Delete remote files not in local
  --exclude "*.tmp" \                 # Skip temp files
  --include "*.csv" \                 # But include CSV
  --sse aws:kms

# Download
aws s3 cp s3://my-bucket/data/file.csv ./local/

# Download all with prefix
aws s3 sync s3://my-bucket/data/ ./local-data/

# ── OBJECT METADATA ───────────────────────────────────────────
# Get object metadata (HEAD request)
aws s3api head-object \
  --bucket my-bucket \
  --key data/file.csv

# List objects with versions
aws s3api list-object-versions \
  --bucket my-bucket \
  --prefix data/ \
  --query "Versions[*].[Key,VersionId,LastModified,IsLatest]" \
  --output table

# Get specific version
aws s3api get-object \
  --bucket my-bucket \
  --key data/file.csv \
  --version-id XXXXXXXX \
  ./downloaded-old-version.csv

# Delete object (creates delete marker if versioning enabled)
aws s3 rm s3://my-bucket/data/file.csv

# Permanently delete with version ID
aws s3api delete-object \
  --bucket my-bucket \
  --key data/file.csv \
  --version-id XXXXXXXX

# ── BATCH OPERATIONS ──────────────────────────────────────────
# Generate inventory for batch operations
aws s3api put-bucket-inventory-configuration \
  --bucket my-bucket \
  --id daily-inventory \
  --inventory-configuration '{
    "Id": "daily-inventory",
    "IsEnabled": true,
    "Destination": {
      "S3BucketDestination": {
        "Bucket": "arn:aws:s3:::my-inventory-bucket",
        "Format": "CSV"
      }
    },
    "Schedule": {"Frequency": "Daily"},
    "IncludedObjectVersions": "All",
    "OptionalFields": ["Size","LastModifiedDate","ETag","StorageClass"]
  }'

# Pre-signed URL (temporary access, no credentials needed)
aws s3 presign s3://my-bucket/private/report.pdf \
  --expires-in 3600     # 1 hour

# Python: generate pre-signed URL
python3 << 'EOF'
import boto3
from botocore.config import Config

s3 = boto3.client('s3', config=Config(signature_version='s3v4'))
url = s3.generate_presigned_url(
    'get_object',
    Params={'Bucket': 'my-bucket', 'Key': 'private/report.pdf'},
    ExpiresIn=3600
)
print(url)
EOF
```

---

## 4.4 S3 Storage Classes & Lifecycle Rules

### Storage Class Decision

```
When to use each class:
┌────────────────────┬─────────────────────────────────────────────┐
│ Class              │ When to use                                 │
├────────────────────┼─────────────────────────────────────────────┤
│ Standard           │ Frequently accessed data (<30 days)         │
│ Intelligent-Tiering│ Access patterns unknown/variable            │
│ Standard-IA        │ Accessed < once/month, min 30-day billing  │
│ One Zone-IA        │ Non-critical, reproducible, min 30-day      │
│ Glacier Instant    │ Archive, retrieved < once/quarter           │
│ Glacier Flexible   │ Archive, ok with 1-12 hour retrieval        │
│ Glacier Deep       │ 7+ year compliance archive, 12-48 hour OK  │
└────────────────────┴─────────────────────────────────────────────┘

Cost comparison (per GB/month, approximate):
  Standard:           $0.023
  Standard-IA:        $0.0125  (-46%)
  One Zone-IA:        $0.01    (-57%)
  Glacier Instant:    $0.004   (-83%)
  Glacier Flexible:   $0.0036  (-84%)
  Glacier Deep:       $0.00099 (-96%)
```

### Lifecycle Rules

```bash
# Configure lifecycle rules
aws s3api put-bucket-lifecycle-configuration \
  --bucket my-company-data-prod \
  --lifecycle-configuration '{
    "Rules": [
      {
        "ID": "log-lifecycle",
        "Status": "Enabled",
        "Filter": {"Prefix": "logs/"},
        "Transitions": [
          {"Days": 30, "StorageClass": "STANDARD_IA"},
          {"Days": 90, "StorageClass": "GLACIER"},
          {"Days": 365, "StorageClass": "DEEP_ARCHIVE"}
        ],
        "Expiration": {"Days": 2557}
      },
      {
        "ID": "delete-incomplete-multipart",
        "Status": "Enabled",
        "Filter": {},
        "AbortIncompleteMultipartUpload": {"DaysAfterInitiation": 7}
      },
      {
        "ID": "clean-old-versions",
        "Status": "Enabled",
        "Filter": {"Prefix": ""},
        "NoncurrentVersionTransitions": [
          {"NoncurrentDays": 30, "StorageClass": "GLACIER"}
        ],
        "NoncurrentVersionExpiration": {"NoncurrentDays": 90}
      }
    ]
  }'

# View lifecycle rules
aws s3api get-bucket-lifecycle-configuration --bucket my-company-data-prod
```

---

## 4.5 S3 Event Notifications & Lambda Integration

```bash
# Trigger Lambda when object uploaded to S3
# First, add permission for S3 to invoke Lambda
aws lambda add-permission \
  --function-name process-upload \
  --principal s3.amazonaws.com \
  --statement-id s3-trigger \
  --action lambda:InvokeFunction \
  --source-arn arn:aws:s3:::my-bucket \
  --source-account 123456789012

# Configure event notification on bucket
aws s3api put-bucket-notification-configuration \
  --bucket my-bucket \
  --notification-configuration '{
    "LambdaFunctionConfigurations": [
      {
        "LambdaFunctionArn": "arn:aws:lambda:us-east-1:123:function:process-upload",
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
    ],
    "QueueConfigurations": [
      {
        "QueueArn": "arn:aws:sqs:us-east-1:123:processing-queue",
        "Events": ["s3:ObjectCreated:Put"],
        "Filter": {"Key": {"FilterRules": [{"Name": "prefix", "Value": "data/"}]}}
      }
    ],
    "TopicConfigurations": [
      {
        "TopicArn": "arn:aws:sns:us-east-1:123:s3-alerts",
        "Events": ["s3:ObjectRemoved:*", "s3:Replication:OperationMissedThreshold"]
      }
    ]
  }'
```

```python
# Lambda function to process S3 events
import boto3
import json
import urllib.parse

s3 = boto3.client('s3')

def handler(event, context):
    for record in event['Records']:
        bucket = record['s3']['bucket']['name']
        key = urllib.parse.unquote_plus(record['s3']['object']['key'])
        size = record['s3']['object']['size']
        event_type = record['eventName']
        
        print(f"Event: {event_type} | Bucket: {bucket} | Key: {key} | Size: {size}")
        
        if event_type.startswith('ObjectCreated'):
            # Process the uploaded file
            response = s3.get_object(Bucket=bucket, Key=key)
            content = response['Body'].read()
            
            # Do something with content...
            process_file(bucket, key, content)
    
    return {'statusCode': 200}

def process_file(bucket, key, content):
    # Example: generate thumbnail, process CSV, etc.
    pass
```

---

## 4.6 S3 Replication

### Cross-Region Replication (CRR) & Same-Region Replication (SRR)

```bash
# Enable versioning on both buckets (required for replication)
aws s3api put-bucket-versioning \
  --bucket source-bucket \
  --versioning-configuration Status=Enabled

aws s3api put-bucket-versioning \
  --bucket dest-bucket-us-west-2 \
  --versioning-configuration Status=Enabled

# Create replication role
cat > replication-trust.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "s3.amazonaws.com"},
    "Action": "sts:AssumeRole"
  }]
}
EOF

aws iam create-role \
  --role-name S3ReplicationRole \
  --assume-role-policy-document file://replication-trust.json

aws iam put-role-policy \
  --role-name S3ReplicationRole \
  --policy-name ReplicationPolicy \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Action": ["s3:GetReplicationConfiguration", "s3:ListBucket"],
        "Resource": "arn:aws:s3:::source-bucket"
      },
      {
        "Effect": "Allow",
        "Action": ["s3:GetObjectVersionForReplication", "s3:GetObjectVersionAcl", "s3:GetObjectVersionTagging"],
        "Resource": "arn:aws:s3:::source-bucket/*"
      },
      {
        "Effect": "Allow",
        "Action": ["s3:ReplicateObject", "s3:ReplicateDelete", "s3:ReplicateTags"],
        "Resource": "arn:aws:s3:::dest-bucket-us-west-2/*"
      }
    ]
  }'

# Configure replication
aws s3api put-bucket-replication \
  --bucket source-bucket \
  --replication-configuration '{
    "Role": "arn:aws:iam::123:role/S3ReplicationRole",
    "Rules": [{
      "ID": "replicate-all",
      "Status": "Enabled",
      "Filter": {},
      "DeleteMarkerReplication": {"Status": "Enabled"},
      "Destination": {
        "Bucket": "arn:aws:s3:::dest-bucket-us-west-2",
        "StorageClass": "STANDARD_IA",
        "EncryptionConfiguration": {
          "ReplicaKmsKeyID": "arn:aws:kms:us-west-2:123:key/dest-key"
        }
      }
    }]
  }'

# Check replication status
aws s3api head-object \
  --bucket source-bucket \
  --key myfile.csv \
  --query "ReplicationStatus"  # PENDING, COMPLETED, FAILED, REPLICA
```

---

## 4.7 S3 Static Website Hosting

```bash
# Enable static website hosting
aws s3api put-bucket-website \
  --bucket my-website.example.com \
  --website-configuration '{
    "IndexDocument": {"Suffix": "index.html"},
    "ErrorDocument": {"Key": "error.html"},
    "RoutingRules": [{
      "Condition": {"HttpErrorCodeReturnedEquals": "404"},
      "Redirect": {"ReplaceKeyWith": "index.html"}
    }]
  }'

# Update bucket policy for public read (for static sites only!)
aws s3api put-public-access-block \
  --bucket my-website.example.com \
  --public-access-block-configuration \
    "BlockPublicAcls=false,IgnorePublicAcls=false,BlockPublicPolicy=false,RestrictPublicBuckets=false"

aws s3api put-bucket-policy \
  --bucket my-website.example.com \
  --policy '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": "*",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::my-website.example.com/*"
    }]
  }'

# Upload site
aws s3 sync ./dist/ s3://my-website.example.com/ \
  --delete \
  --cache-control "max-age=86400" \
  --exclude "*.html"

# No-cache for HTML files
aws s3 sync ./dist/ s3://my-website.example.com/ \
  --include "*.html" \
  --cache-control "no-cache"

# Website endpoint (not HTTPS — use CloudFront for HTTPS)
echo "http://my-website.example.com.s3-website-us-east-1.amazonaws.com"
```

---

## 4.8 S3 Access Points & Multi-Region Access Points

### S3 Access Points

Access Points simplify managing access to shared datasets.

```bash
# Create access point (for specific team/application)
aws s3control create-access-point \
  --account-id 123456789012 \
  --name data-science-access \
  --bucket my-data-lake \
  --vpc-configuration VpcId=vpc-0abc123

# Set access point policy (restrict to data-science role only)
aws s3control put-access-point-policy \
  --account-id 123456789012 \
  --name data-science-access \
  --policy '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"AWS": "arn:aws:iam::123456789012:role/DataScienceRole"},
      "Action": ["s3:GetObject", "s3:PutObject"],
      "Resource": "arn:aws:s3:us-east-1:123456789012:accesspoint/data-science-access/object/*"
    }]
  }'

# Access via access point ARN
aws s3api get-object \
  --bucket arn:aws:s3:us-east-1:123456789012:accesspoint/data-science-access \
  --key data/model-training.csv \
  ./local-file.csv
```

---

## 4.9 S3 Intelligent-Tiering

```bash
# Enable Intelligent-Tiering on bucket (recommended for mixed-access datasets)
aws s3api put-bucket-intelligent-tiering-configuration \
  --bucket my-data-lake \
  --id my-tiering-config \
  --intelligent-tiering-configuration '{
    "Id": "my-tiering-config",
    "Status": "Enabled",
    "Tierings": [
      {"Days": 90, "AccessTier": "ARCHIVE_ACCESS"},
      {"Days": 180, "AccessTier": "DEEP_ARCHIVE_ACCESS"}
    ]
  }'
```

---

## 4.10 S3 Analytics & S3 Select

```bash
# S3 Select — query CSV/JSON/Parquet without downloading entire object
aws s3api select-object-content \
  --bucket my-bucket \
  --key data/users.csv \
  --expression "SELECT s.name, s.email FROM S3Object s WHERE s.age > 30" \
  --expression-type SQL \
  --input-serialization '{"CSV": {"FileHeaderInfo": "USE", "RecordDelimiter": "\n"}}' \
  --output-serialization '{"CSV": {}}' \
  output.csv

# Python: S3 Select
import boto3

s3 = boto3.client('s3')
response = s3.select_object_content(
    Bucket='my-bucket',
    Key='data/orders.csv',
    ExpressionType='SQL',
    Expression="SELECT * FROM S3Object WHERE amount > 1000",
    InputSerialization={
        'CSV': {'FileHeaderInfo': 'USE'},
        'CompressionType': 'GZIP'
    },
    OutputSerialization={'CSV': {}},
)

for event in response['Payload']:
    if 'Records' in event:
        print(event['Records']['Payload'].decode('utf-8'))
```

---

## 4.11 EBS — Extended Reference

(EBS basics in Chapter 3 — deeper topics here)

### EBS Multi-Attach (io1/io2 only)

Attach the same EBS volume to multiple EC2 instances in the same AZ:
- Limited to io1/io2 volumes
- Up to 16 Linux Nitro instances
- Cluster-aware file system required (e.g., GFS2)
- Use case: high-availability storage applications, Oracle RAC

```bash
aws ec2 create-volume \
  --availability-zone us-east-1a \
  --volume-type io2 \
  --size 100 \
  --iops 3000 \
  --multi-attach-enabled

aws ec2 attach-volume --volume-id vol-0abc --instance-id i-0001 --device /dev/xvdf
aws ec2 attach-volume --volume-id vol-0abc --instance-id i-0002 --device /dev/xvdf
```

### EBS Snapshots — Advanced

```bash
# Enable EBS snapshot archiving (cheaper storage for rarely accessed snapshots)
aws ec2 modify-snapshot-tier \
  --snapshot-id snap-0abc123 \
  --storage-tier archive

# Restore archived snapshot (takes 24-72 hours)
aws ec2 restore-snapshot-tier \
  --snapshot-id snap-0abc123 \
  --temporary-restore-days 3   # Restore temporarily for 3 days
  # Or without flag: permanent restore (moves back to standard)

# Copy snapshot to another account
aws ec2 modify-snapshot-attribute \
  --snapshot-id snap-0abc123 \
  --attribute createVolumePermission \
  --operation-type add \
  --user-ids 987654321098

# Amazon Data Lifecycle Manager (DLM) — automated snapshot policy
aws dlm create-lifecycle-policy \
  --description "Daily snapshots for prod databases" \
  --state ENABLED \
  --execution-role-arn arn:aws:iam::123:role/DLMRole \
  --policy-details '{
    "PolicyType": "EBS_SNAPSHOT_MANAGEMENT",
    "ResourceTypes": ["INSTANCE"],
    "TargetTags": [{"Key": "backup", "Value": "daily"}],
    "Schedules": [{
      "Name": "Daily snapshots",
      "CreateRule": {"Interval": 24, "IntervalUnit": "HOURS", "Times": ["03:00"]},
      "RetainRule": {"Count": 7},
      "CopyTags": true
    }]
  }'
```

---

## 4.12 EFS — Elastic File System

### EFS Performance Modes

```
Performance Modes:
  General Purpose:  Default, balanced for most workloads
  Max I/O:         Higher aggregate throughput, higher latency, for highly parallel

Throughput Modes:
  Bursting:        Throughput scales with storage size (50MB/s/TB base + burst credits)
  Provisioned:     Set throughput independent of storage size
  Elastic:         Auto-scales up/down based on actual usage (recommended)

Storage Classes:
  Standard:        Frequently accessed data
  Infrequent Access (IA): Lower cost, per-request access fee (auto-tiering available)
```

```bash
# Create EFS with lifecycle management
aws efs create-file-system \
  --performance-mode generalPurpose \
  --throughput-mode elastic \
  --encrypted \
  --kms-key-id arn:aws:kms:us-east-1:123:key/abc \
  --lifecycle-policies '[
    {"TransitionToIA": "AFTER_30_DAYS"},
    {"TransitionToPrimaryStorageClass": "AFTER_1_ACCESS"}
  ]' \
  --tags Key=Name,Value=shared-files

FS_ID=$(aws efs describe-file-systems \
  --query "FileSystems[?Name=='shared-files'].FileSystemId" --output text)

# Create mount targets in each AZ
for SUBNET in subnet-0abc subnet-0def subnet-0ghi; do
  aws efs create-mount-target \
    --file-system-id $FS_ID \
    --subnet-id $SUBNET \
    --security-groups sg-efs-0abc
done

# Create access point (application-specific entry point)
aws efs create-access-point \
  --file-system-id $FS_ID \
  --posix-user "Uid=1000,Gid=1000" \
  --root-directory-creation-info "OwnerUid=1000,OwnerGid=1000,Permissions=755" \
  --root-directory Path=/myapp \
  --tags Key=Name,Value=myapp-access-point

# Mount with EFS access point
sudo mount -t efs -o tls,accesspoint=fsap-0abc123 $FS_ID:/ /mnt/efs/myapp

# Mount EFS in container (ECS task definition)
# See Chapter 8 for ECS volume configuration
```

### EFS Backup

```bash
# Enable automatic backups
aws efs put-backup-policy \
  --file-system-id $FS_ID \
  --backup-policy Status=ENABLED

# Manual backup using AWS Backup
aws backup create-backup-vault --backup-vault-name efs-backups

aws backup start-backup-job \
  --backup-vault-name efs-backups \
  --resource-arn arn:aws:elasticfilesystem:us-east-1:123:file-system/$FS_ID \
  --iam-role-arn arn:aws:iam::123:role/AWSBackupRole
```

---

## 4.13 FSx — Managed File Systems

### FSx for Windows File Server

Fully managed Windows SMB file shares (Active Directory integration):

```bash
aws fsx create-file-system \
  --file-system-type WINDOWS \
  --storage-capacity 300 \
  --storage-type SSD \
  --subnet-ids subnet-0abc123 subnet-0def456 \
  --windows-configuration '{
    "ActiveDirectoryId": "d-0abc123",
    "ThroughputCapacity": 64,
    "WeeklyMaintenanceStartTime": "1:05:00",
    "DailyAutomaticBackupStartTime": "04:00",
    "AutomaticBackupRetentionDays": 30,
    "DeploymentType": "MULTI_AZ_1",
    "PreferredSubnetId": "subnet-0abc123"
  }'
```

### FSx for Lustre

High-performance parallel file system for HPC, machine learning:

```bash
aws fsx create-file-system \
  --file-system-type LUSTRE \
  --storage-capacity 1200 \
  --subnet-ids subnet-0abc123 \
  --lustre-configuration '{
    "ImportPath": "s3://my-data-lake/training-data/",
    "ExportPath": "s3://my-data-lake/results/",
    "ImportedFileChunkSize": 1024,
    "DeploymentType": "SCRATCH_2",
    "PerUnitStorageThroughput": 200
  }'
```

### FSx for NetApp ONTAP

```bash
aws fsx create-file-system \
  --file-system-type ONTAP \
  --storage-capacity 1024 \
  --subnet-ids subnet-0abc subnet-0def \
  --ontap-configuration '{
    "DeploymentType": "MULTI_AZ_1",
    "PreferredSubnetId": "subnet-0abc",
    "ThroughputCapacity": 256
  }'
```

---

## 4.14 S3 Glacier — Archive Storage

### Glacier Storage Classes via S3 Lifecycle (Recommended)

Use S3 lifecycle rules to automatically move data to Glacier (see section 4.4).

### Direct Glacier Vault Operations (Legacy)

```bash
# Create vault
aws glacier create-vault \
  --account-id - \
  --vault-name my-archive-vault

# Upload archive
aws glacier upload-archive \
  --account-id - \
  --vault-name my-archive-vault \
  --body ./backup.tar.gz

# List vaults
aws glacier list-vaults --account-id -

# Initiate retrieval job (Glacier Flexible — takes 1-12 hours)
aws glacier initiate-job \
  --account-id - \
  --vault-name my-archive-vault \
  --job-parameters '{
    "Type": "archive-retrieval",
    "ArchiveId": "archive-id-here",
    "Tier": "Standard",
    "Description": "Emergency retrieval"
  }'
# Tier options: Expedited (1-5 min, expensive), Standard (3-5 hr), Bulk (5-12 hr)

# Check job status
aws glacier list-jobs --account-id - --vault-name my-archive-vault

# Download when complete
aws glacier get-job-output \
  --account-id - \
  --vault-name my-archive-vault \
  --job-id job-id-here \
  ./retrieved-archive.tar.gz
```

---

## 4.15 AWS Snow Family

The Snow Family helps move large amounts of data to/from AWS when internet transfer is too slow or expensive.

```
┌────────────────────────────────────────────────────────────────────┐
│                     SNOW FAMILY COMPARISON                         │
├─────────────────┬───────────────┬──────────────────────────────────┤
│ Device          │ Storage       │ Use Cases                        │
├─────────────────┼───────────────┼──────────────────────────────────┤
│ Snowcone        │ 8TB HDD,      │ Small edge locations, IoT        │
│                 │ 14TB NVMe     │ Remote/disconnected environments │
│                 │               │ Battery-powered, 4.5 lbs        │
├─────────────────┼───────────────┼──────────────────────────────────┤
│ Snowball Edge   │ 80TB (storage)│ Data migration, edge compute     │
│ Storage         │               │ S3-compatible, NFS               │
├─────────────────┼───────────────┼──────────────────────────────────┤
│ Snowball Edge   │ 40TB usable   │ Edge ML inference, preprocessing │
│ Compute         │               │ GPU option available             │
├─────────────────┼───────────────┼──────────────────────────────────┤
│ Snowmobile      │ 100 PB        │ Exabyte-scale migration          │
│                 │               │ Literal shipping container truck │
└─────────────────┴───────────────┴──────────────────────────────────┘

Rule of thumb: If transfer > 1 week → consider Snow Family
  1Gbps internet: 1TB = 2.3 hours, 1PB = 100 days → use Snowball
```

```bash
# Order a Snowball job (via console or CLI)
aws snowball create-job \
  --job-type IMPORT \
  --resources '{
    "S3Resources": [{
      "BucketArn": "arn:aws:s3:::destination-bucket",
      "KeyRange": {}
    }]
  }' \
  --description "Data center migration batch 1" \
  --address-id address-id-from-console \
  --kms-key-arn arn:aws:kms:us-east-1:123:key/abc \
  --role-arn arn:aws:iam::123:role/SnowballRole \
  --snowball-type EDGE_STORAGE_OPTIMIZED \
  --shipping-option STANDARD

# Track job status
aws snowball describe-job --job-id JID-xxxx

# List all jobs
aws snowball list-jobs \
  --query "JobListEntries[*].[JobId,JobState,JobType,Description]" \
  --output table
```

---

## 4.16 Storage Gateway

AWS Storage Gateway connects on-premises applications to AWS storage services.

```
Gateway Types:
┌────────────────┬──────────────────────────────────────────────────┐
│ Type           │ Description                                      │
├────────────────┼──────────────────────────────────────────────────┤
│ S3 File        │ NFS/SMB interface → objects stored in S3         │
│ Gateway        │ Use for: file shares, backup targets             │
├────────────────┼──────────────────────────────────────────────────┤
│ FSx File       │ SMB interface → stored in FSx for Windows        │
│ Gateway        │ Use for: Windows file shares to cloud            │
├────────────────┼──────────────────────────────────────────────────┤
│ Volume         │ iSCSI block volumes → S3 with EBS snapshots      │
│ Gateway        │ Cached: data in S3, frequently accessed on-prem  │
│                │ Stored: all data on-prem, async backup to S3     │
├────────────────┼──────────────────────────────────────────────────┤
│ Tape           │ Virtual tape library → S3 and Glacier            │
│ Gateway        │ Use for: backup software using tape APIs         │
└────────────────┴──────────────────────────────────────────────────┘

Deployment options:
  - Virtual appliance (VMware ESXi, Hyper-V, KVM)
  - Hardware appliance (physical device)
  - EC2 instance (for testing)
```

---

## 4.17 Storage Comparison Summary

```
┌──────────────────────────────────────────────────────────────────┐
│                 AWS STORAGE SERVICES COMPARISON                  │
├──────────────┬────────────┬─────────────────────────────────────┤
│ Service      │ Type       │ Best For                            │
├──────────────┼────────────┼─────────────────────────────────────┤
│ S3           │ Object     │ Any unstructured data, backups,     │
│              │            │ static files, data lake, media      │
├──────────────┼────────────┼─────────────────────────────────────┤
│ EBS gp3      │ Block      │ EC2 OS disk, databases, apps        │
│ EBS io2      │ Block      │ High-perf databases (OLTP)          │
├──────────────┼────────────┼─────────────────────────────────────┤
│ EFS          │ File (NFS) │ Shared Linux content, CMS, DevTools │
│ FSx Windows  │ File (SMB) │ Windows shared drives, AD-joined    │
│ FSx Lustre   │ File (HPC) │ ML training, financial analytics    │
├──────────────┼────────────┼─────────────────────────────────────┤
│ Glacier      │ Archive    │ Long-term archival, compliance      │
├──────────────┼────────────┼─────────────────────────────────────┤
│ Snow Family  │ Physical   │ Large-scale data transfer           │
├──────────────┼────────────┼─────────────────────────────────────┤
│ Storage GW   │ Hybrid     │ Connect on-prem apps to cloud       │
└──────────────┴────────────┴─────────────────────────────────────┘
```

---

## 4.18 Interview Q&A

**Q: What is S3 durability and availability?**
A: S3 Standard provides 99.999999999% (11 nines) durability — meaning if you store 10 million objects, you can expect to lose one object every 10,000 years. This is achieved by storing objects across at least 3 AZs. Availability is 99.99% — meaning S3 may be unavailable for about 52 minutes per year.

**Q: What is the difference between S3 Standard-IA and S3 One Zone-IA?**
A: Both are for infrequently accessed data with the same 11 nines durability. One Zone-IA stores data in only one AZ (cheaper — saves 20%) but if that AZ is destroyed, data is lost. Standard-IA stores across 3+ AZs. Use One Zone-IA only for non-critical, reproducible data.

**Q: When would you use S3 Intelligent-Tiering?**
A: When access patterns are unpredictable or change over time. Intelligent-Tiering monitors object access and automatically moves objects to the most cost-effective tier. There is a small monthly monitoring fee per object, so it makes most sense for objects larger than 128KB that will exist for at least 30 days.

**Q: How does S3 versioning help protect against accidental deletion?**
A: With versioning enabled, deleting an object adds a "delete marker" instead of removing the object. All previous versions are preserved. To permanently delete, you must delete the specific version. This protects against accidental deletion and overwrites, and enables easy recovery of previous file versions.

**Q: What is the difference between EBS and EFS?**
A: EBS is block storage attached to a single EC2 instance in a specific AZ — like a hard drive. EFS is a network file system (NFS) accessible from multiple EC2 instances simultaneously across multiple AZs — like a shared network drive. EBS is lower latency and higher performance; EFS is more flexible for shared access. EFS is significantly more expensive per GB.

**Q: What is S3 Transfer Acceleration?**
A: S3 Transfer Acceleration enables fast uploads to S3 from all over the world by routing data through CloudFront's edge locations using optimized network paths. It's most useful when uploading large files from locations far from the S3 bucket's region. It costs extra — about $0.04–$0.08 per GB.

**Q: What is multipart upload in S3?**
A: Multipart upload allows uploading large objects in parts (5MB to 5GB each) in parallel, then S3 assembles them. Benefits: faster uploads (parallel), resume interrupted uploads, required for objects over 5GB. AWS CLI automatically uses multipart upload for objects over 8MB. Always configure lifecycle rule to abort incomplete multipart uploads after N days to avoid orphaned storage charges.

**Q: What is the difference between S3 pre-signed URLs and signed cookies?**
A: Pre-signed URLs grant temporary access to a specific S3 object — useful for allowing users to download/upload without exposing bucket credentials. Signed cookies (a CloudFront feature) grant access to multiple objects via a wildcard pattern — useful when a user should have access to many files in a private CloudFront distribution.
