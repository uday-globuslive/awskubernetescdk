# Chapter 4: Storage — S3, EBS, EFS, Glacier & More
## Object, Block, and File Storage Services

---

## 4.1 Storage Types Overview

```
┌──────────────────────────────────────────────────────────┐
│                AWS STORAGE CATEGORIES                    │
├──────────────┬──────────────────┬────────────────────────┤
│ OBJECT       │ BLOCK            │ FILE                   │
│ ────────     │ ─────            │ ────                   │
│ S3           │ EBS              │ EFS (Linux)             │
│ S3 Glacier   │ EC2 Instance     │ FSx for Windows         │
│              │ Store            │ FSx for Lustre          │
│ Flat storage │ Like a hard disk │ Like a network drive    │
│ Access via   │ Attached to      │ Mounted by multiple     │
│ HTTP API     │ ONE instance     │ instances simultaneously│
│ Unlimited    │ Single AZ        │ Multi-AZ                │
│ capacity     │ High IOPS        │ Shared access           │
└──────────────┴──────────────────┴────────────────────────┘
```

---

## 4.2 S3 — Simple Storage Service

S3 stores **objects** (files) in **buckets**. Infinitely scalable, 99.999999999% (11 9s) durability.

### Core Concepts

```
Bucket → like a top-level folder (name must be globally unique)
Object → file stored in a bucket
Key    → full path of the object (e.g., "images/2024/photo.jpg")
Value  → the content (bytes)

Object size: 0 bytes to 5 TB
Bucket: unlimited objects
```

### S3 CLI Essentials

```bash
# Create bucket
aws s3 mb s3://my-unique-bucket-name --region us-east-1

# List buckets
aws s3 ls

# List objects
aws s3 ls s3://my-bucket/
aws s3 ls s3://my-bucket/images/ --recursive

# Upload file
aws s3 cp local-file.txt s3://my-bucket/path/file.txt

# Upload entire folder
aws s3 sync ./dist s3://my-bucket/website/

# Download
aws s3 cp s3://my-bucket/file.txt ./local-file.txt

# Delete object
aws s3 rm s3://my-bucket/file.txt

# Delete bucket (must be empty first, or use --force)
aws s3 rb s3://my-bucket --force

# Generate presigned URL (temporary access, no auth needed)
aws s3 presign s3://my-bucket/private-file.pdf --expires-in 3600
```

### S3 Storage Classes

```
┌───────────────────────────────────────────────────────────────┐
│                   S3 STORAGE CLASSES                          │
├─────────────────────┬────────────┬──────────────┬────────────┤
│ Class               │ Retrieval  │ Min Duration │ Use Case   │
├─────────────────────┼────────────┼──────────────┼────────────┤
│ Standard            │ ms         │ None         │ Frequent   │
│                     │            │              │ access     │
├─────────────────────┼────────────┼──────────────┼────────────┤
│ Standard-IA         │ ms         │ 30 days      │ Infrequent │
│ (Infrequent Access) │            │              │ access     │
├─────────────────────┼────────────┼──────────────┼────────────┤
│ One Zone-IA         │ ms         │ 30 days      │ Infrequent,│
│                     │            │              │ single AZ  │
├─────────────────────┼────────────┼──────────────┼────────────┤
│ Intelligent-Tiering │ ms-hrs     │ None         │ Unknown    │
│                     │            │              │ patterns   │
├─────────────────────┼────────────┼──────────────┼────────────┤
│ Glacier Instant     │ ms         │ 90 days      │ Archive,   │
│ Retrieval           │            │              │ rare access│
├─────────────────────┼────────────┼──────────────┼────────────┤
│ Glacier Flexible    │ min–hrs    │ 90 days      │ Archives   │
│ Retrieval           │            │              │            │
├─────────────────────┼────────────┼──────────────┼────────────┤
│ Glacier Deep        │ 12–48 hrs  │ 180 days     │ Long-term  │
│ Archive             │            │              │ compliance │
└─────────────────────┴────────────┴──────────────┴────────────┘
```

### S3 Lifecycle Policies

Automatically transition objects between storage classes or delete them.

```json
// lifecycle.json
{
  "Rules": [
    {
      "ID": "move-to-ia-then-glacier",
      "Status": "Enabled",
      "Filter": {"Prefix": "logs/"},
      "Transitions": [
        {
          "Days": 30,
          "StorageClass": "STANDARD_IA"
        },
        {
          "Days": 90,
          "StorageClass": "GLACIER"
        }
      ],
      "Expiration": {
        "Days": 365
      }
    }
  ]
}
```

```bash
aws s3api put-bucket-lifecycle-configuration \
  --bucket my-bucket \
  --lifecycle-configuration file://lifecycle.json
```

### S3 Versioning

Keep multiple versions of an object. Protects against accidental deletes.

```bash
# Enable versioning
aws s3api put-bucket-versioning \
  --bucket my-bucket \
  --versioning-configuration Status=Enabled

# List versions
aws s3api list-object-versions --bucket my-bucket --prefix myfile.txt

# Restore deleted file (delete the delete marker)
aws s3api delete-object \
  --bucket my-bucket \
  --key myfile.txt \
  --version-id <delete-marker-version-id>
```

### S3 Security

```bash
# Block all public access (should be ON for most buckets)
aws s3api put-public-access-block \
  --bucket my-bucket \
  --public-access-block-configuration \
    BlockPublicAcls=true,IgnorePublicAcls=true,\
    BlockPublicPolicy=true,RestrictPublicBuckets=true

# Enable server-side encryption (default since 2023)
aws s3api put-bucket-encryption \
  --bucket my-bucket \
  --server-side-encryption-configuration '{
    "Rules": [{
      "ApplyServerSideEncryptionByDefault": {
        "SSEAlgorithm": "aws:kms",
        "KMSMasterKeyID": "arn:aws:kms:us-east-1:123456:key/abc-123"
      }
    }]
  }'

# Enable access logging
aws s3api put-bucket-logging \
  --bucket my-bucket \
  --bucket-logging-status '{
    "LoggingEnabled": {
      "TargetBucket": "my-logs-bucket",
      "TargetPrefix": "s3-access-logs/"
    }
  }'
```

### S3 Event Notifications

Trigger Lambda/SQS/SNS when objects are uploaded.

```bash
aws s3api put-bucket-notification-configuration \
  --bucket my-bucket \
  --notification-configuration '{
    "LambdaFunctionConfigurations": [{
      "LambdaFunctionArn": "arn:aws:lambda:us-east-1:123456:function:process-upload",
      "Events": ["s3:ObjectCreated:*"],
      "Filter": {
        "Key": {
          "FilterRules": [
            {"Name": "prefix", "Value": "uploads/"},
            {"Name": "suffix", "Value": ".jpg"}
          ]
        }
      }
    }]
  }'
```

### S3 as a Static Website

```bash
# Enable static website hosting
aws s3 website s3://my-bucket \
  --index-document index.html \
  --error-document error.html

# Bucket policy for public website
aws s3api put-bucket-policy --bucket my-bucket --policy '{
  "Statement": [{
    "Effect": "Allow",
    "Principal": "*",
    "Action": "s3:GetObject",
    "Resource": "arn:aws:s3:::my-bucket/*"
  }]
}'

# Sync React/Vue build to S3
aws s3 sync ./build s3://my-bucket --delete
# URL: http://my-bucket.s3-website-us-east-1.amazonaws.com
# (Use CloudFront in front for HTTPS and custom domain)
```

---

## 4.3 S3 Advanced Features

### Multipart Upload (files > 100 MB)

```python
import boto3

s3 = boto3.client("s3")

# High-level transfer (handles multipart automatically)
s3.upload_file(
    Filename="large-file.zip",
    Bucket="my-bucket",
    Key="uploads/large-file.zip",
    ExtraArgs={"StorageClass": "STANDARD_IA"},
    Config=boto3.s3.transfer.TransferConfig(
        multipart_threshold=100 * 1024 * 1024,   # 100 MB
        multipart_chunksize=50 * 1024 * 1024,    # 50 MB chunks
        max_concurrency=10,
    )
)
```

### Presigned URLs

```python
import boto3

s3 = boto3.client("s3")

# Generate upload URL (user uploads directly to S3, no server involved)
presigned_url = s3.generate_presigned_post(
    Bucket="my-bucket",
    Key="uploads/${filename}",
    Fields={"Content-Type": "image/jpeg"},
    Conditions=[
        ["content-length-range", 0, 10 * 1024 * 1024]  # Max 10 MB
    ],
    ExpiresIn=3600
)

# Generate download URL
download_url = s3.generate_presigned_url(
    "get_object",
    Params={"Bucket": "my-bucket", "Key": "private/file.pdf"},
    ExpiresIn=300  # 5 minutes
)
```

### S3 Replication

```bash
# Cross-Region Replication (CRR) — disaster recovery
# Same-Region Replication (SRR) — log aggregation

# Requires versioning enabled on both buckets
# Configure via console or JSON:
aws s3api put-bucket-replication \
  --bucket source-bucket \
  --replication-configuration '{
    "Role": "arn:aws:iam::123456:role/s3-replication-role",
    "Rules": [{
      "Status": "Enabled",
      "Destination": {
        "Bucket": "arn:aws:s3:::destination-bucket",
        "ReplicationTime": {"Status": "Enabled", "Time": {"Minutes": 15}},
        "StorageClass": "STANDARD_IA"
      }
    }]
  }'
```

---

## 4.4 EFS — Elastic File System

**EFS** is a managed **NFS file system** that can be mounted by multiple EC2 instances simultaneously — across AZs.

```
┌──────────────────────────────────────────────────────────┐
│                    EFS USE CASE                          │
│                                                          │
│  EC2 (AZ-1a)  EC2 (AZ-1a)  EC2 (AZ-1b)                 │
│      │              │              │                     │
│      └──────────────┼──────────────┘                     │
│                     │                                    │
│              ┌──────────────┐                            │
│              │     EFS      │ ← Shared file system       │
│              │  (NFS v4.1)  │   All instances see        │
│              └──────────────┘   the same files           │
│                                                          │
│  Use for: shared config, media storage, ML datasets,     │
│           WordPress uploads, CI/CD artifact storage      │
└──────────────────────────────────────────────────────────┘
```

```bash
# Create EFS file system
aws efs create-file-system \
  --performance-mode generalPurpose \
  --throughput-mode bursting \
  --encrypted \
  --tags Key=Name,Value=my-shared-fs

# Create mount targets (one per AZ)
aws efs create-mount-target \
  --file-system-id fs-0abc123 \
  --subnet-id subnet-0abc123 \
  --security-groups sg-0abc123

# Mount on EC2 (after installing amazon-efs-utils)
sudo mount -t efs fs-0abc123:/ /mnt/shared

# Or in /etc/fstab for persistent mount
# fs-0abc123:/ /mnt/shared efs defaults,_netdev 0 0
```

**EFS vs EBS:**
- EBS: one instance, block storage, high IOPS, same AZ required
- EFS: many instances, file storage, auto-scales, multi-AZ

---

## 4.5 S3 Glacier — Long-Term Archive

Glacier is ultra-cheap archival storage. Not for frequent access.

```
┌──────────────────────────────────────────────────────────┐
│              GLACIER RETRIEVAL OPTIONS                   │
├──────────────────────┬────────────┬──────────────────────┤
│ Expedited            │ 1–5 min    │ Most expensive        │
│ Standard             │ 3–5 hours  │ Default              │
│ Bulk                 │ 5–12 hours │ Cheapest             │
└──────────────────────┴────────────┴──────────────────────┘

Cost comparison (vs S3 Standard):
S3 Standard:          $0.023/GB/month
S3 Glacier Flexible:  $0.004/GB/month  (83% cheaper)
S3 Glacier Deep:      $0.00099/GB/month (96% cheaper)
```

---

## 4.6 Storage Gateway

Connects on-premises environments to AWS storage.

```
On-Premises                   AWS Cloud
────────────                  ─────────
┌──────────┐                  ┌──────────────────┐
│ Servers  │──── Storage ────►│  S3 / Glacier    │
│ Backups  │   Gateway        │  EBS snapshots   │
└──────────┘   (VM or         └──────────────────┘
               hardware)

Types:
• File Gateway   → NFS/SMB → S3 (file shares)
• Volume Gateway → iSCSI block storage → EBS snapshots
• Tape Gateway   → Virtual tape library → Glacier
```

---

## 4.7 Key S3 Interview Questions

**Q: How do you secure an S3 bucket?**
> Multiple layers: (1) Block Public Access enabled — prevents any public access regardless of ACLs/policies. (2) Bucket policy restricting access to specific IAM roles or VPC endpoints. (3) Server-side encryption at rest (SSE-KMS or SSE-S3). (4) Enable versioning to protect against accidental deletes. (5) Enable access logging to S3 Access Logs. (6) Use S3 Object Lock for compliance scenarios (WORM — Write Once Read Many).

**Q: What's the difference between S3 and EBS?**
> S3 is object storage accessed via HTTP API — unlimited scale, any number of clients, globally accessible but with higher latency. EBS is block storage — like a hard drive — attached to a single EC2 instance in the same AZ, very low latency (sub-millisecond), ideal for databases and OS volumes.

**Q: How would you host a static website cheaply on AWS?**
> Upload static files (HTML, CSS, JS) to an S3 bucket with static website hosting enabled. Put CloudFront in front for HTTPS, custom domain, and global CDN. Use Route53 for DNS. Total cost is typically cents per month. No servers needed.

**Q: What is S3 Transfer Acceleration?**
> It routes uploads through AWS CloudFront edge locations, which use optimised AWS backbone network to reach the S3 bucket — faster than the public internet for users far from the bucket's region. Useful for global file uploads. Adds ~0.04 cents/GB.
