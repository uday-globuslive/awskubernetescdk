
content = r"""# Chapter 4: Storage — S3, EFS, Glacier & More
## (Where Your Data Lives — Every Option Explained Clearly)

---

## 4.1 Storage Types in AWS — The Big Picture

Before diving into specific services, understand the 3 fundamental types of storage:

### Block Storage — Like a Hard Drive

**What it is:** Raw storage that the OS sees as a disk. You format it with a filesystem, then read/write individual bytes or blocks.

**Analogy:** Like the internal hard drive in your laptop. The OS treats it as a drive (C:\ on Windows, /dev/sda on Linux).

**AWS service:** EBS (Elastic Block Store)
**Used for:** OS root volumes for EC2, databases, any application that needs a local disk

### File Storage — Like a Network Drive

**What it is:** A filesystem that multiple computers can mount and use simultaneously. Looks and behaves like a folder.

**Analogy:** Like a shared network folder in a company office. Anyone with access can browse files, read, write, just like local files.

**AWS services:** EFS (Linux), FSx for Windows (Windows), FSx for Lustre (HPC)
**Used for:** Shared content repositories, home directories, media processing, web serving shared content

### Object Storage — Like Google Drive or Dropbox

**What it is:** Store files (objects) with metadata. Access via HTTP API, not traditional file operations. No folders (but can simulate with prefix paths).

**Analogy:** Like Gmail attachments or Google Drive. You upload a file, get a URL, share the URL. Simple but not for databases.

**AWS service:** S3 (Simple Storage Service)
**Used for:** Backups, static website hosting, data lakes, media files, application assets, archives

```
Quick decision guide:
  Need a disk for EC2? → EBS
  Need shared filesystem for multiple servers? → EFS (Linux) or FSx (Windows)
  Need to store files, images, backups, data? → S3
  Need to archive data cheaply for years? → S3 Glacier
```

---

## 4.2 S3 — Simple Storage Service

### What is S3? (Like a Limitless Hard Drive on the Internet)

**S3 (Simple Storage Service)** is AWS's object storage service. You store files (called **objects**) in containers (called **buckets**).

Key facts about S3:
- **Virtually unlimited storage** — no size limit on how much you store
- **Any file type** — images, videos, documents, database backups, log files, anything
- **Maximum object size: 5 TB** (use multipart upload for files over 5 GB)
- **Durability: 99.999999999% (11 nines)** — for every million files stored, you might lose 1 in a billion years
- **Availability: 99.99%** (Standard tier) — always accessible
- **Global service but regional** — buckets are created in specific regions; data does not leave that region

**Analogy:** S3 is like a massive warehouse (the bucket) where each item on the shelf (object) has a unique label (key). You can have as many items as you want. The warehouse company guarantees they will never lose your items.

### S3 Buckets and Objects

**Bucket:**
- Container for objects (like a top-level folder)
- Name must be globally unique across ALL AWS accounts worldwide
- Created in a specific region
- Name rules: lowercase, 3-63 characters, no spaces, no uppercase

**Object:**
- A file stored in S3
- Identified by: `bucket-name/key` (the "path")
- Has: data (the file content) + metadata (file type, size, custom tags)
- Has a unique URL: `https://bucket-name.s3.amazonaws.com/path/to/file.jpg`

```
Bucket: my-company-photos
Objects (keys):
  marketing/logo.png
  marketing/banner.jpg
  employees/alice/headshot.jpg
  employees/bob/headshot.jpg
  backups/2025/01/database-backup.sql.gz
```

### Creating Buckets and Uploading Objects

```bash
# Create a bucket (must be globally unique)
aws s3api create-bucket \
  --bucket my-company-assets-2025 \
  --region us-east-1

# For regions OTHER than us-east-1, must specify location constraint:
aws s3api create-bucket \
  --bucket my-company-eu-assets \
  --region eu-west-1 \
  --create-bucket-configuration LocationConstraint=eu-west-1

# Upload a file to S3
aws s3 cp local-file.jpg s3://my-company-assets-2025/images/local-file.jpg

# Upload an entire folder
aws s3 sync ./local-folder/ s3://my-company-assets-2025/folder/ \
  --exclude "*.tmp" \
  --include "*.jpg" \
  --include "*.png"

# Download from S3
aws s3 cp s3://my-company-assets-2025/images/photo.jpg ./photo.jpg

# List objects in a bucket
aws s3 ls s3://my-company-assets-2025/images/ --human-readable

# Delete an object
aws s3 rm s3://my-company-assets-2025/old-file.jpg

# Presigned URL (temporary, time-limited access link)
aws s3 presign s3://my-company-assets-2025/private-document.pdf \
  --expires-in 3600  # expires in 1 hour
```

---

## 4.3 S3 Storage Classes — Paying Only for What You Need

### The Cost vs Access Speed Trade-off

S3 offers different storage classes based on how frequently you access data:
- Data you need constantly → expensive but fast
- Data you rarely access → cheaper but slower to retrieve
- Data you keep for compliance but almost never touch → very cheap

**Think of it like parking spots:**
- **Garage right next to the office** (S3 Standard) — expensive, instant access anytime
- **Parking lot 2 blocks away** (S3-IA) — cheaper, need to walk 2 minutes
- **Remote parking with shuttle** (S3 Glacier) — very cheap, but 3-5 hours to get there
- **Long-term storage unit across town** (S3 Glacier Deep Archive) — cheapest, next day access

### All Storage Classes Explained

**S3 Standard — For Frequently Accessed Data**
```
Use when: Active data accessed multiple times per month
Cost: ~$0.023/GB/month (most expensive)
Retrieval fee: None (free to GET)
Availability: 99.99%
Durability: 99.999999999% (11 nines)

Good for:
  - Active website assets (images, CSS, JS files)
  - Application data being actively used
  - Any data you access often
```

**S3 Standard-IA (Infrequent Access) — For Less Frequent Access**
```
Use when: Data accessed maybe once a month or less
Cost: ~$0.0125/GB/month (46% cheaper than Standard)
Retrieval fee: $0.01/GB retrieved (extra charge when you access it!)
Minimum storage duration: 30 days
Minimum object size: 128 KB (smaller objects cost as if 128 KB)

Good for:
  - Monthly backups
  - Disaster recovery copies
  - Data you keep "just in case" but rarely use
```

**S3 One Zone-IA — Like IA but in One AZ**
```
Use when: Data that can be recreated if lost; infrequently accessed
Cost: ~$0.01/GB/month (57% cheaper than Standard)
Risk: Stored in ONE AZ only — if that AZ fails, data is lost!
Retrieval fee: $0.01/GB

Good for:
  - Secondary backups (you have a primary backup elsewhere)
  - Thumbnails that can be regenerated from originals
  - DO NOT use for data you cannot recreate
```

**S3 Intelligent-Tiering — Automatic Optimization**
```
Use when: Unknown or changing access patterns; you do not want to manage tiers
Cost: Small monthly monitoring fee per object ($0.0025/1,000 objects)
      Moves objects between tiers automatically based on access
      
How it works:
  Object stored in Frequent Access tier
  → Not accessed for 30 days → automatically moved to IA tier
  → Not accessed for 90 days → moved to Archive Instant Access tier
  → Not accessed for 180 days → moved to Archive Access tier
  → You access it again → immediately moved back to Frequent Access tier!
  → No retrieval fees within Intelligent-Tiering!

Good for:
  - Data lakes with unpredictable access patterns
  - Avoiding management of lifecycle rules
```

**S3 Glacier Instant Retrieval — Archive with Millisecond Access**
```
Use when: Archive data accessed maybe once per quarter
Cost: ~$0.004/GB/month (very cheap)
Retrieval: Milliseconds (same as Standard — instant!)
Retrieval fee: $0.03/GB
Minimum storage duration: 90 days

Good for:
  - Medical images that must be kept for compliance but rarely viewed
  - News media archives
  - Long-term analytics data
```

**S3 Glacier Flexible Retrieval — Very Cheap Archive**
```
Use when: Archive data, access time of hours is acceptable
Cost: ~$0.0036/GB/month
Retrieval time options:
  - Expedited: 1-5 minutes (most expensive retrieval)
  - Standard: 3-5 hours
  - Bulk: 5-12 hours (cheapest retrieval)
Minimum storage duration: 90 days

Good for:
  - Compliance archives
  - Media backup archives
  - Long-term audit trails
```

**S3 Glacier Deep Archive — The Cheapest AWS Storage**
```
Use when: Data kept for 7+ years for compliance, accessed very rarely
Cost: ~$0.00099/GB/month (less than $1 per TB per month!)
Retrieval time:
  - Standard: 12 hours
  - Bulk: 48 hours
Minimum storage duration: 180 days

Good for:
  - Healthcare records required by law for 7-10 years
  - Financial records required for SEC/SOX compliance
  - Legal holds
  - Anything you "must keep but almost never look at"
```

### S3 Lifecycle Policies — Automatic Cost Optimization

A lifecycle policy automatically moves objects between storage classes as they age. Set it once, and S3 handles the cost optimization forever.

**Example: Log file lifecycle**
```
Day 0-30:   S3 Standard (actively analyzed by teams)
Day 31-90:  S3 Standard-IA (occasionally looked up)
Day 91-365: S3 Glacier Flexible (rarely accessed, legal holds)
Day 365+:   S3 Glacier Deep Archive (7-year retention requirement)
```

```json
{
  "Rules": [
    {
      "ID": "log-file-lifecycle",
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
        },
        {
          "Days": 365,
          "StorageClass": "DEEP_ARCHIVE"
        }
      ],
      "Expiration": {
        "Days": 2555
      }
    }
  ]
}
```

```bash
aws s3api put-bucket-lifecycle-configuration \
  --bucket my-logs-bucket \
  --lifecycle-configuration file://lifecycle-policy.json
```

---

## 4.4 S3 Security — Protecting Your Data

### The Layers of S3 Security

S3 has multiple security controls. Understanding each one and how they interact is critical for the exam.

```
SECURITY LAYERS (outer to inner):

1. AWS Organizations SCPs (block entire account if needed)
2. IAM Policies (who has permission to access S3)
3. S3 Bucket Policy (resource-level: who can access this specific bucket)
4. S3 ACLs (legacy, mostly replaced by bucket policies — avoid)
5. S3 Block Public Access (overrides everything for public access)
6. Object-level controls (encryption, versioning, Object Lock)
```

### S3 Bucket Policies — The Most Important Security Control

A bucket policy is a JSON document attached to the bucket that defines who can access it and what they can do.

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
        "arn:aws:s3:::my-secure-bucket",
        "arn:aws:s3:::my-secure-bucket/*"
      ],
      "Condition": {
        "Bool": {
          "aws:SecureTransport": "false"
        }
      }
    },
    {
      "Sid": "AllowSpecificRole",
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::123456789012:role/DataProcessingRole"
      },
      "Action": ["s3:GetObject", "s3:PutObject"],
      "Resource": "arn:aws:s3:::my-secure-bucket/data/*"
    }
  ]
}
```

### S3 Block Public Access — The Safety Net

Even if someone accidentally creates a bucket policy that makes data public, Block Public Access acts as a safety override.

```bash
# Block ALL public access on a bucket (best practice for non-website buckets)
aws s3api put-public-access-block \
  --bucket my-private-bucket \
  --public-access-block-configuration \
    BlockPublicAcls=true,\
    IgnorePublicAcls=true,\
    BlockPublicPolicy=true,\
    RestrictPublicBuckets=true

# Enable account-level block public access (affects ALL buckets in account)
aws s3control put-public-access-block \
  --account-id 123456789012 \
  --public-access-block-configuration \
    BlockPublicAcls=true,\
    IgnorePublicAcls=true,\
    BlockPublicPolicy=true,\
    RestrictPublicBuckets=true
```

**Exam tip:** Block Public Access settings OVERRIDE bucket ACLs and bucket policies for public access. Even if a bucket policy says `"Principal": "*"` (public), Block Public Access will deny it.

### S3 Encryption — Protecting Data at Rest

Every S3 object should be encrypted. There are 4 encryption options:

**1. SSE-S3 (Server-Side Encryption with S3-managed keys)**
```
- AWS manages the encryption keys entirely
- AES-256 encryption
- Zero additional cost
- You have zero control over key management
- Good default for most workloads

Enable by default on bucket:
aws s3api put-bucket-encryption \
  --bucket my-bucket \
  --server-side-encryption-configuration '{
    "Rules": [{
      "ApplyServerSideEncryptionByDefault": {
        "SSEAlgorithm": "AES256"
      },
      "BucketKeyEnabled": true
    }]
  }'
```

**2. SSE-KMS (Server-Side Encryption with KMS keys)**
```
- You control the encryption key (via AWS KMS)
- Every S3 API call is logged in CloudTrail (who accessed what data when)
- Can use your own CMK (Customer Managed Key) or AWS-managed key
- Audit who accessed encrypted data
- Can revoke the key to immediately deny all access
- Small cost for KMS API calls ($0.03 per 10,000 API calls)
- Required for compliance (PCI-DSS, HIPAA, FedRAMP)

Enable SSE-KMS:
aws s3api put-bucket-encryption \
  --bucket my-bucket \
  --server-side-encryption-configuration '{
    "Rules": [{
      "ApplyServerSideEncryptionByDefault": {
        "SSEAlgorithm": "aws:kms",
        "KMSMasterKeyID": "arn:aws:kms:us-east-1:123456789012:key/abc123"
      },
      "BucketKeyEnabled": true
    }]
  }'
```

**3. SSE-C (Server-Side Encryption with Customer-provided keys)**
```
- YOU provide the encryption key with each request
- AWS uses the key to encrypt/decrypt, then discards it
- AWS never stores your key
- You must keep track of which key was used for each object
- Complex to manage — not recommended unless required
```

**4. Client-Side Encryption**
```
- You encrypt data BEFORE uploading to S3
- S3 stores already-encrypted data
- AWS never sees your unencrypted data
- Use: AWS Encryption SDK, or your own encryption
- Maximum security, maximum complexity
```

### S3 Versioning — Never Lose a File

**Versioning** keeps every version of every object. When you overwrite a file, the old version is kept. When you delete a file, a "delete marker" is added but the old versions are kept.

```bash
# Enable versioning
aws s3api put-bucket-versioning \
  --bucket my-important-bucket \
  --versioning-configuration Status=Enabled

# List all versions of an object
aws s3api list-object-versions \
  --bucket my-important-bucket \
  --prefix important-document.pdf

# Restore a previous version
aws s3api copy-object \
  --copy-source my-important-bucket/important-document.pdf?versionId=xxx \
  --bucket my-important-bucket \
  --key important-document.pdf

# Permanently delete a specific version
aws s3api delete-object \
  --bucket my-important-bucket \
  --key important-document.pdf \
  --version-id version-id-to-delete
```

**Exam tip:** Once versioning is enabled, it can be SUSPENDED but not completely disabled. Suspended versioning stops creating new versions but keeps existing versions.

### S3 MFA Delete — Extra Protection Against Accidental Deletion

When MFA Delete is enabled, deleting objects permanently or disabling versioning requires an MFA code.

```bash
# Enable MFA Delete (requires root account credentials!)
aws s3api put-bucket-versioning \
  --bucket critical-data-bucket \
  --versioning-configuration Status=Enabled,MFADelete=Enabled \
  --mfa "arn:aws:iam::123456789012:mfa/root-account-mfa-device 123456"
```

**Note:** Only the root account can enable MFA Delete. It cannot be enabled by an IAM user.

### S3 Object Lock — Write-Once-Read-Many (WORM)

Object Lock prevents objects from being deleted or modified for a specified period. Used for compliance and immutable backups.

**Two retention modes:**

**Governance mode:**
- Users with special IAM permission can override the lock
- Good for internal protection against accidental deletion
- Allows exceptions with proper authorization

**Compliance mode:**
- NO ONE can delete or modify — not even root, not even AWS Support
- Perfect for regulatory compliance (SEC Rule 17a-4, HIPAA, etc.)
- Cannot be shortened once set

```bash
# Enable Object Lock (must be done at bucket creation time!)
aws s3api create-bucket \
  --bucket immutable-compliance-bucket \
  --region us-east-1

aws s3api put-object-lock-configuration \
  --bucket immutable-compliance-bucket \
  --object-lock-configuration '{
    "ObjectLockEnabled": "Enabled",
    "Rule": {
      "DefaultRetention": {
        "Mode": "COMPLIANCE",
        "Years": 7
      }
    }
  }'

# Put an object with specific retention
aws s3api put-object \
  --bucket immutable-compliance-bucket \
  --key financial-records/2025-annual-report.pdf \
  --body ./2025-annual-report.pdf \
  --object-lock-mode COMPLIANCE \
  --object-lock-retain-until-date "2032-12-31T00:00:00Z"
```

---

## 4.5 S3 Replication — Copying Data Across Regions or Accounts

### Why Replicate?

- **Disaster Recovery:** If the primary region has a catastrophic failure, you have a copy in another region
- **Low Latency:** Serve content from the region closest to your users
- **Compliance:** Some laws require data in multiple countries
- **Backup:** Separate copy in different account for protection against account compromise

### CRR vs SRR

**CRR (Cross-Region Replication):**
- Replicates objects from a bucket in one region to a bucket in ANOTHER region
- Use for: Disaster recovery, global data distribution, latency reduction

**SRR (Same-Region Replication):**
- Replicates objects within the same region but to a different bucket
- Use for: Separating test and production environments, compliance (separate account), log aggregation

```bash
# Set up Cross-Region Replication (CRR)
# Prerequisites:
#   1. Versioning must be enabled on BOTH source and destination buckets
#   2. IAM role with permission to replicate

# Enable versioning on source
aws s3api put-bucket-versioning \
  --bucket source-bucket-us-east-1 \
  --versioning-configuration Status=Enabled

# Enable versioning on destination (in another region)
aws s3api put-bucket-versioning \
  --bucket dest-bucket-eu-west-1 \
  --region eu-west-1 \
  --versioning-configuration Status=Enabled

# Create the replication configuration
cat > /tmp/replication.json << 'EOF'
{
  "Role": "arn:aws:iam::123456789012:role/S3ReplicationRole",
  "Rules": [
    {
      "ID": "ReplicateAll",
      "Status": "Enabled",
      "Filter": {},
      "Destination": {
        "Bucket": "arn:aws:s3:::dest-bucket-eu-west-1",
        "ReplicationTime": {
          "Status": "Enabled",
          "Time": {"Minutes": 15}
        },
        "Metrics": {
          "Status": "Enabled",
          "EventThreshold": {"Minutes": 15}
        },
        "StorageClass": "STANDARD_IA"
      },
      "DeleteMarkerReplication": {"Status": "Enabled"}
    }
  ]
}
EOF

aws s3api put-bucket-replication \
  --bucket source-bucket-us-east-1 \
  --replication-configuration file:///tmp/replication.json
```

**Key facts about replication:**
- Replication is asynchronous (best-effort, usually replicates within minutes)
- Replication does NOT apply retroactively to existing objects (only new objects)
- With S3 Replication Time Control (RTC), 99.99% of objects replicate within 15 minutes (for compliance)
- Delete markers CAN be replicated (configure explicitly)
- Deletions with version ID are NOT replicated (protects against cross-region accidental deletion propagation)

---

## 4.6 S3 Features for Performance

### Multipart Upload — For Large Files

Files over 5 GB MUST use multipart upload. AWS recommends using it for files over 100 MB.

**Why multipart?**
- Upload large files in parallel chunks (faster)
- Resume interrupted uploads (resilient to network issues)
- Each part is 5 MB to 5 GB

```python
import boto3
from boto3.s3.transfer import TransferConfig

s3 = boto3.client('s3')

# Configure multipart upload thresholds
config = TransferConfig(
    multipart_threshold=1024 * 25,      # Use multipart for files > 25 MB
    max_concurrency=10,                  # Upload 10 parts simultaneously
    multipart_chunksize=1024 * 25,      # Each chunk = 25 MB
    use_threads=True
)

# Upload large file with multipart automatically
s3.upload_file(
    Filename='/path/to/large-video.mp4',
    Bucket='my-video-bucket',
    Key='videos/large-video.mp4',
    Config=config,
    ExtraArgs={
        'StorageClass': 'STANDARD',
        'ServerSideEncryption': 'aws:kms'
    }
)
```

### S3 Transfer Acceleration — Faster Uploads from Anywhere

**Problem:** Uploading large files from Tokyo to an S3 bucket in us-east-1 requires data to travel across the public internet — slow and unreliable.

**S3 Transfer Acceleration** routes uploads through the nearest CloudFront edge location (in Tokyo), then uses AWS's private backbone network to reach us-east-1 — much faster!

```bash
# Enable Transfer Acceleration on a bucket
aws s3api put-bucket-accelerate-configuration \
  --bucket my-global-uploads-bucket \
  --accelerate-configuration Status=Enabled

# Use the accelerated endpoint for uploads
aws s3 cp large-file.mp4 \
  s3://my-global-uploads-bucket/uploads/large-file.mp4 \
  --endpoint-url https://s3-accelerate.amazonaws.com

# Check if Transfer Acceleration speeds up your specific case
# AWS provides a speed comparison tool at:
# https://s3-accelerate-speedtest.s3-accelerate.amazonaws.com/en/accelerate-speed-comparsion.html
```

**Exam tip:** Transfer Acceleration = faster UPLOADS to S3. CloudFront = faster DOWNLOADS from S3. Common confusion point.

### S3 Byte-Range Fetches — Parallel Downloads

You can request specific byte ranges of an object, enabling parallel downloads of large files.

```python
import boto3
import threading
import os

s3 = boto3.client('s3')

def download_chunk(bucket, key, start, end, chunk_num, output_dir):
    # Download a specific byte range chunk of an S3 object.
    response = s3.get_object(
        Bucket=bucket,
        Key=key,
        Range=f'bytes={start}-{end}'
    )
    chunk_data = response['Body'].read()
    chunk_file = f'{output_dir}/chunk_{chunk_num:04d}'
    with open(chunk_file, 'wb') as f:
        f.write(chunk_data)

def parallel_download(bucket, key, output_file, chunk_size_mb=25):
    # Download S3 object in parallel chunks.
    # Get file size
    response = s3.head_object(Bucket=bucket, Key=key)
    total_size = response['ContentLength']
    chunk_size = chunk_size_mb * 1024 * 1024
    
    output_dir = '/tmp/chunks'
    os.makedirs(output_dir, exist_ok=True)
    
    # Create chunks
    chunks = []
    pos = 0
    chunk_num = 0
    while pos < total_size:
        end = min(pos + chunk_size - 1, total_size - 1)
        chunks.append((pos, end, chunk_num))
        pos = end + 1
        chunk_num += 1
    
    # Download all chunks in parallel
    threads = []
    for start, end, num in chunks:
        t = threading.Thread(
            target=download_chunk,
            args=(bucket, key, start, end, num, output_dir)
        )
        threads.append(t)
        t.start()
    
    for t in threads:
        t.join()
    
    # Combine chunks into final file
    with open(output_file, 'wb') as final:
        for _, _, num in sorted(chunks, key=lambda x: x[2]):
            chunk_file = f'{output_dir}/chunk_{num:04d}'
            with open(chunk_file, 'rb') as chunk:
                final.write(chunk.read())
            os.remove(chunk_file)
    
    print(f"Downloaded {output_file} ({total_size} bytes) in {len(chunks)} parallel chunks")
```

---

## 4.7 EFS — Elastic File System

### What is EFS?

**EFS (Elastic File System)** is a fully managed NFS (Network File System) that multiple EC2 instances can mount simultaneously.

**Analogy:** Imagine a network drive in a company office. You save a file to the Z:\ drive, and everyone in the office can see it immediately. EFS is that Z:\ drive, but for Linux systems in AWS, and it automatically grows and shrinks as you add or remove files.

**Key differences from EBS:**
| Feature | EBS | EFS |
|---------|-----|-----|
| Attached to | One EC2 at a time | Hundreds of EC2 simultaneously |
| OS | Linux + Windows | Linux only (NFS protocol) |
| Capacity | Fixed size you set | Automatically grows/shrinks |
| Access | Block (like hard drive) | File system (NFS) |
| Multi-AZ | No (in one AZ) | Yes (data spread across AZs) |

### EFS Storage Classes

Like S3, EFS has hot and cold tiers:

```
EFS Standard:
  - Active files accessed regularly
  - Highest performance, highest cost (~$0.30/GB/month)

EFS Standard-IA (Infrequent Access):
  - Files not accessed for 30 days automatically moved here
  - Lower cost (~$0.025/GB/month — 8x cheaper!)
  - Small retrieval fee when accessed (~$0.01/GB)

EFS One Zone:
  - Stored in ONE AZ (cheaper but less durable)
  - ~$0.16/GB/month

EFS One Zone-IA:
  - Cheapest option (~$0.0133/GB/month)
  - Good for dev/test environments
```

### Setting Up EFS

```bash
# Step 1: Create EFS filesystem
EFS_ID=$(aws efs create-file-system \
  --creation-token "my-app-efs" \
  --performance-mode generalPurpose \
  --throughput-mode bursting \
  --encrypted \
  --kms-key-id arn:aws:kms:us-east-1:123456789012:key/abc123 \
  --tags Key=Name,Value=my-app-shared-storage \
  --query 'FileSystemId' --output text)

# Step 2: Create mount targets (one per AZ for high availability)
# Each mount target gets an IP address in that AZ's subnet
aws efs create-mount-target \
  --file-system-id $EFS_ID \
  --subnet-id subnet-az1-private \
  --security-groups sg-efs-access

aws efs create-mount-target \
  --file-system-id $EFS_ID \
  --subnet-id subnet-az2-private \
  --security-groups sg-efs-access

aws efs create-mount-target \
  --file-system-id $EFS_ID \
  --subnet-id subnet-az3-private \
  --security-groups sg-efs-access

# Step 3: Mount on EC2 (run this on the EC2 instance)
# Install EFS mount helper
sudo yum install -y amazon-efs-utils

# Create mount point
sudo mkdir /mnt/efs

# Mount using EFS mount helper (handles DNS, encryption in transit)
sudo mount -t efs -o tls,iam $EFS_ID:/ /mnt/efs

# Auto-mount on reboot (/etc/fstab):
echo "$EFS_ID:/ /mnt/efs efs defaults,_netdev,tls,iam 0 0" | sudo tee -a /etc/fstab
```

### EFS Use Cases

**Good use cases:**
- **CMS (Content Management Systems):** WordPress running on multiple EC2 instances with shared media uploads
- **Container environments:** ECS or EKS containers sharing files (persistent volumes)
- **Development environments:** Multiple developers editing code on the same files
- **Web server logs:** All web servers write to same EFS for centralized log access
- **Build systems:** Build artifacts accessible by multiple build workers

**Not good for:**
- Databases (use EBS or RDS instead — databases need block storage)
- Anything needing sub-millisecond latency (use EBS on instance store)
- Windows servers (use FSx for Windows instead)

---

## 4.8 FSx — Managed File Systems

When EFS is not enough, AWS offers FSx for specific use cases:

### FSx for Windows File Server

```
What it is: Fully managed Windows-native file server (SMB protocol)
Use for: Windows applications, Active Directory integration, 
         home drives, SharePoint alternative

Key features:
  - Native Windows SMB (Server Message Block) protocol
  - Active Directory integration (domain-joined)
  - Windows ACLs and DFS namespaces
  - De-duplication, compression, encryption

Access: Windows (\\server\share) and Linux (mount CIFS)
```

### FSx for Lustre — High Performance Computing

```
What it is: High-performance parallel filesystem for HPC, ML, analytics
Use for: Machine learning training, computational finance, 
         video rendering, genome sequencing

Performance:
  - Hundreds of GB/s throughput
  - Millions of IOPS
  - Sub-millisecond latency

Integration: Seamlessly integrates with S3 (lazy loading)
             Import files from S3 on first access
             Export changed files back to S3
```

### FSx for NetApp ONTAP

```
What it is: Managed NetApp ONTAP file system
Use for: Enterprise applications using NetApp storage features,
         database storage, home directories, analytics

Key features:
  - NFS, SMB, iSCSI protocols (multi-protocol)
  - NetApp SnapMirror (built-in replication)
  - Thin provisioning, compression, deduplication
  - Works with on-premises NetApp (hybrid cloud)
```

---

## 4.9 Storage Gateway — Bridge Between On-Premises and AWS

### What Problem Does It Solve?

Your company has an on-premises data center with 500TB of data on NAS (Network Attached Storage). You want to:
- Migrate to the cloud gradually
- Keep on-premises apps running while using S3 as the backend
- Keep recently accessed data local (fast access) but archive older data to S3

**Storage Gateway** solves this with a virtual appliance (VM) you run in your data center.

### Three Types of Storage Gateway

**1. S3 File Gateway:**
```
What it does: Your on-premises apps save files to a local NFS/SMB share.
              The gateway stores them in S3 in the background.

Use case: Company's existing file server → migrate data to S3
          without changing any existing applications.

Architecture:
  On-premises app → (NFS/SMB) → Storage Gateway VM → (HTTPS) → S3
  
  Recent files cached locally (fast access)
  Older files fetched from S3 when needed
```

**2. Tape Gateway (Virtual Tape Library — VTL):**
```
What it does: Appears to your backup software as physical tape drives and library.
              Actually stores data in S3 and Glacier.

Use case: Companies using existing tape backup software (Veritas NetBackup, 
          Veeam, etc.) that cannot easily change to cloud-native backup.

Architecture:
  Backup software → (iSCSI VTL interface) → Storage Gateway → S3/Glacier
  
  Current tapes (recent) → S3
  Archived tapes → S3 Glacier
```

**3. Volume Gateway:**
```
What it does: Presents iSCSI block volumes to on-premises servers.
              Data stored in AWS with local caching.

Two modes:
  Cached volumes: Primary data in S3, frequently accessed cached locally
  Stored volumes: Primary data on-premises, asynchronously backed up to S3

Use case: On-premises servers needing additional block storage that 
          is automatically backed up to AWS.
```

---

## 4.10 AWS Backup — Centralized Backup Management

### The Problem with Manual Backups

Without central backup management:
- Different teams set up different backup policies
- Some teams forget to set up backups at all
- Auditing compliance is manual and error-prone
- No way to verify backups actually work (not tested)

**AWS Backup** provides a centralized service to:
- Create backup policies (backup plans) across multiple services
- Enforce backup requirements organization-wide via backup policies
- Monitor compliance (which resources are backed up, which are not)
- Test restores (with Restore Testing)

### Supported Services

```
Services AWS Backup can back up:
  EC2 instances (snapshots of all attached EBS volumes)
  EBS volumes
  RDS databases (and Aurora)
  DynamoDB tables
  EFS filesystems
  FSx file systems
  S3 buckets (to another location)
  DocumentDB
  Neptune
  VMware workloads (on-premises via Storage Gateway)
```

### Setting Up AWS Backup

```bash
# Create a backup vault (encrypted container for backups)
aws backup create-backup-vault \
  --backup-vault-name production-vault \
  --encryption-key-arn arn:aws:kms:us-east-1:123456789012:key/abc123

# Create a backup plan (the policy: what, when, how long to keep)
cat > /tmp/backup-plan.json << 'EOF'
{
  "BackupPlanName": "production-backup-plan",
  "Rules": [
    {
      "RuleName": "daily-backup",
      "TargetBackupVaultName": "production-vault",
      "ScheduleExpression": "cron(0 2 * * ? *)",
      "StartWindowMinutes": 60,
      "CompletionWindowMinutes": 180,
      "Lifecycle": {
        "MoveToColdStorageAfterDays": 30,
        "DeleteAfterDays": 90
      },
      "RecoveryPointTags": {
        "BackupType": "Daily",
        "Environment": "production"
      }
    },
    {
      "RuleName": "weekly-backup",
      "TargetBackupVaultName": "production-vault",
      "ScheduleExpression": "cron(0 3 ? * SUN *)",
      "Lifecycle": {
        "MoveToColdStorageAfterDays": 90,
        "DeleteAfterDays": 365
      }
    }
  ]
}
EOF

PLAN_ID=$(aws backup create-backup-plan \
  --backup-plan file:///tmp/backup-plan.json \
  --query 'BackupPlanId' --output text)

# Assign resources to the backup plan (by tag)
aws backup create-backup-selection \
  --backup-plan-id $PLAN_ID \
  --backup-selection '{
    "SelectionName": "production-resources",
    "IamRoleArn": "arn:aws:iam::123456789012:role/AWSBackupDefaultServiceRole",
    "ListOfTags": [{
      "ConditionType": "STRINGEQUALS",
      "ConditionKey": "Environment",
      "ConditionValue": "production"
    }]
  }'

echo "Backup plan created: $PLAN_ID"
echo "All resources tagged Environment=production will be backed up"
```

---

## 4.11 Real-World Project: S3 Data Lake Architecture

### Scenario

Your company collects millions of events per day from your web application. You need:
- Raw events stored cheaply
- Query capability without spinning up databases
- Automatic cost optimization as data ages
- Compliance: keep data for 7 years

### Architecture

```
Web App Events → Kinesis Firehose → S3 Raw Zone
                                         │
                              ┌──────────┼──────────┐
                              │          │           │
                           AWS Glue    Athena     Lifecycle
                         (catalog)  (queries)    (tiers)
                              │
                         S3 Processed Zone
                         (optimized Parquet format)
```

### Implementation

```bash
# Step 1: Create the data lake buckets
# Raw zone — where data lands
aws s3api create-bucket \
  --bucket company-datalake-raw-123456789012 \
  --region us-east-1

# Processed zone — cleaned, optimized data
aws s3api create-bucket \
  --bucket company-datalake-processed-123456789012 \
  --region us-east-1

# Step 2: Apply encryption to both buckets
for BUCKET in company-datalake-raw-123456789012 company-datalake-processed-123456789012; do
  aws s3api put-bucket-encryption \
    --bucket $BUCKET \
    --server-side-encryption-configuration '{
      "Rules": [{
        "ApplyServerSideEncryptionByDefault": {
          "SSEAlgorithm": "aws:kms"
        },
        "BucketKeyEnabled": true
      }]
    }'
  
  # Block public access
  aws s3api put-public-access-block \
    --bucket $BUCKET \
    --public-access-block-configuration \
      BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
  
  # Enable versioning
  aws s3api put-bucket-versioning \
    --bucket $BUCKET \
    --versioning-configuration Status=Enabled
  
  echo "Configured: $BUCKET"
done

# Step 3: Set up lifecycle policy on raw bucket
cat > /tmp/raw-lifecycle.json << 'EOF'
{
  "Rules": [
    {
      "ID": "RawDataLifecycle",
      "Status": "Enabled",
      "Filter": {"Prefix": "events/"},
      "Transitions": [
        {"Days": 30,  "StorageClass": "STANDARD_IA"},
        {"Days": 90,  "StorageClass": "GLACIER"},
        {"Days": 365, "StorageClass": "DEEP_ARCHIVE"}
      ],
      "Expiration": {"Days": 2555},
      "NoncurrentVersionTransitions": [
        {"NoncurrentDays": 30, "StorageClass": "STANDARD_IA"}
      ],
      "NoncurrentVersionExpiration": {"NoncurrentDays": 90}
    }
  ]
}
EOF

aws s3api put-bucket-lifecycle-configuration \
  --bucket company-datalake-raw-123456789012 \
  --lifecycle-configuration file:///tmp/raw-lifecycle.json

# Step 4: Create Glue database and crawler
aws glue create-database \
  --database-input '{
    "Name": "company_events",
    "Description": "Company event data lake"
  }'

# Create Glue crawler to auto-discover schema
aws glue create-crawler \
  --name events-raw-crawler \
  --role arn:aws:iam::123456789012:role/GlueCrawlerRole \
  --database-name company_events \
  --targets '{
    "S3Targets": [{
      "Path": "s3://company-datalake-raw-123456789012/events/",
      "Exclusions": ["**/_SUCCESS", "**/*.tmp"]
    }]
  }' \
  --schedule 'cron(0 1 * * ? *)'  # Run daily at 1am

# Step 5: Query with Athena
cat << 'EOF'
-- Sample Athena query to analyze events
SELECT 
  date_trunc('day', from_iso8601_timestamp(event_timestamp)) AS day,
  event_type,
  COUNT(*) AS event_count,
  COUNT(DISTINCT user_id) AS unique_users
FROM company_events.events
WHERE year = '2025' AND month = '01'
GROUP BY 1, 2
ORDER BY 1, 3 DESC;
EOF
```

---

## 4.12 Practice Questions

**Q1:** An S3 bucket has Block Public Access enabled at the bucket level. A bucket policy with `"Principal": "*"` and `"Effect": "Allow"` is attached. A user tries to access an object anonymously (without any AWS credentials). What happens?

- A) Access is allowed because the bucket policy explicitly allows public access
- B) Access is denied because Block Public Access overrides the bucket policy for public access
- C) Access depends on the object's ACL settings
- D) Access is allowed because AWS honors the most specific policy

**Answer: B**

Explanation: Block Public Access is designed to override bucket policies and ACLs for public access. It was created precisely because administrators were accidentally making buckets public via policies. Even if the bucket policy grants public access (`Principal: *`), Block Public Access will deny it. Block Public Access is the "safety net" that prevents accidental public exposure.

---

**Q2:** A company stores log files in S3. Files are actively used for the first 30 days, occasionally for 60 days after, then rarely for 1 year, then must be kept for 7 years for compliance. What lifecycle policy minimizes storage costs?

- A) Keep all logs in S3 Standard for 7 years
- B) 0-30 days Standard → 30-90 days Standard-IA → 90 days-1 year Glacier → 1-7 years Deep Archive
- C) Delete after 1 year as compliance does not require longer retention
- D) Use S3 One Zone-IA for all logs

**Answer: B**

Explanation: This lifecycle uses cheaper storage classes as data ages: Standard (frequently accessed) → Standard-IA (occasional access, 46% cheaper) → Glacier (rare access, 83% cheaper) → Deep Archive (kept for compliance, 96% cheaper than Standard). This is exactly what lifecycle policies are designed for — automatic cost optimization while meeting retention requirements.

---

**Q3:** A healthcare application on multiple EC2 instances needs a shared filesystem where all instances can read and write patient documents simultaneously. The filesystem must support POSIX permissions and be highly available. Which service should you use?

- A) S3 with a bucket policy
- B) EFS with Multiple-AZ mount targets
- C) EBS Multi-Attach volume
- D) A single large EC2 instance as an NFS server

**Answer: B**

Explanation: EFS provides a fully managed NFS filesystem that multiple EC2 instances can mount simultaneously. It is Multi-AZ (mount targets in each AZ), supports POSIX permissions (required for healthcare apps with file-level access control), and automatically scales storage capacity. EBS Multi-Attach only supports io1/io2 volumes on specific instance types with limited concurrent write access. S3 is object storage, not a filesystem. Running your own NFS server (D) is unmanaged and a single point of failure.

---

**Q4:** An S3 bucket has versioning enabled. A developer accidentally runs `aws s3 rm s3://critical-data/important-file.txt`. What actually happened to the file?

- A) The file is permanently deleted and cannot be recovered
- B) A delete marker is added; the file is not gone — it can be recovered by deleting the delete marker
- C) The file moves to the S3 Recycle Bin for 30 days
- D) The file moves to Glacier automatically

**Answer: B**

Explanation: With versioning enabled, `aws s3 rm` does NOT permanently delete — it adds a "delete marker" (a special version that hides the object). The original versions still exist in S3. To restore the file, delete the delete marker. To permanently delete a versioned object, you must specify the version ID in the delete request. This is why versioning is so important for accidental deletion protection.

---

**Q5:** Which S3 feature is MOST appropriate for storing financial records that must be retained for 7 years with no possibility of deletion or modification, even by an AWS account administrator?

- A) S3 Versioning
- B) S3 Object Lock in Compliance mode with a 7-year retention period
- C) S3 MFA Delete
- D) S3 Glacier Deep Archive storage class

**Answer: B**

Explanation: S3 Object Lock in Compliance mode creates a truly immutable object — nobody, not even root, not even AWS Support, can delete or modify the object until the retention period expires. This is the definition of WORM (Write-Once-Read-Many) storage for regulatory compliance (SEC Rule 17a-4, FINRA, HIPAA). Versioning (A) prevents accidental deletion but can be bypassed with permissions. MFA Delete (C) adds friction but an admin can still delete. Glacier Deep Archive (D) is a storage class, not a protection mechanism.

---

## Chapter 4 Summary

| Concept | Key Fact |
|---------|----------|
| S3 | Object storage; unlimited size; 11 nines durability; globally accessible |
| S3 Storage Classes | Standard (frequent) → IA (monthly) → Glacier Instant → Glacier Flexible (hours) → Deep Archive (cheapest) |
| Lifecycle Policies | Automatically move objects between classes as they age; set once, save forever |
| Block Public Access | Safety net that overrides all public access — enable on all non-website buckets |
| Versioning | Keep all versions; delete marker on rm; restore by removing marker; suspend not disable |
| Object Lock | COMPLIANCE mode = truly immutable even from root; WORM storage for regulations |
| MFA Delete | Extra protection for versioning operations; requires root + MFA code; CLI limited |
| CRR vs SRR | CRR = different region (DR); SRR = same region (compliance, aggregation) |
| EBS | Block storage for EC2; gp3 is default; io2 for high IOPS; one instance at a time |
| EFS | NFS shared filesystem for Linux; multi-AZ; multi-instance; auto-scales |
| FSx | Windows-native (SMB), Lustre (HPC/ML), NetApp (enterprise features) |
| Storage Gateway | Bridge on-premises to cloud; S3 File GW, Tape GW, Volume GW |
| AWS Backup | Centralized backup for EC2/EBS/RDS/DynamoDB/EFS; compliance reporting |
"""

with open(r"e:\fastapi\aws-admin\04_Storage_S3_EFS_Glacier.md", "w", encoding="utf-8") as f:
    f.write(content)

print(f"Written {len(content.splitlines())} lines")
