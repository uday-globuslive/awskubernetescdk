
content = r"""# Chapter 10: Security, Compliance & KMS
## (Protecting Everything — Encryption, Secrets, and Threat Detection)

---

## 10.1 The AWS Shared Responsibility Model (Revisited)

Security in AWS is a **shared responsibility** between AWS and you. Understanding this clearly is critical for both operating AWS and passing the exam.

```
AWS is responsible for:               You are responsible for:
  Security OF the cloud                Security IN the cloud
  
  Physical security of data centers    Your data (encryption at rest, in transit)
  Hardware (servers, network, storage) Who has access (IAM users, roles, policies)
  Hypervisor and virtualization        Network configuration (VPC, security groups, NACLs)
  Managed service patches (RDS, etc.)  OS patching on EC2 instances
  Availability zones and regions       Application-level security
  Network backbone                     Customer data compliance (HIPAA, PCI, GDPR)
```

**Key exam point:** For managed services like RDS, Lambda, S3:
- AWS patches the underlying infrastructure
- You configure access control, encryption, and backups

For unmanaged like EC2:
- AWS provides the hypervisor and hardware
- YOU patch the OS, install security software, configure firewall

---

## 10.2 AWS KMS — Key Management Service

### What is KMS?

**AWS KMS (Key Management Service)** is a fully managed service for creating and controlling cryptographic keys used to encrypt your data.

**Analogy:** Think of KMS as a secure vault that:
- Stores your encryption keys (you never see the actual key material)
- Lets you use keys to encrypt/decrypt data without giving you the key itself
- Logs every time a key is used (CloudTrail integration)
- Lets you revoke access by disabling or deleting keys

### Types of KMS Keys

**1. AWS Managed Keys (aws/servicename):**
```
Created automatically by AWS when you use encryption in a service
Examples: aws/s3, aws/rds, aws/ebs, aws/lambda

Characteristics:
  - You do NOT control these keys
  - AWS rotates them automatically every year
  - Free to use (no per-key charge)
  - You can see usage in CloudTrail but cannot disable/delete them
  
Use when: Basic encryption, no special compliance requirements
```

**2. Customer Managed Keys (CMK):**
```
You create and manage these keys

Characteristics:
  - Full control: enable/disable, schedule deletion, rotate manually or auto
  - Can define who can use and manage the key (via key policy)
  - Cost: $1/month per key + $0.03 per 10,000 API calls
  - Automatic annual rotation (you enable this)
  - Can import your own key material
  
Use when: Compliance requirements (HIPAA, PCI), need to audit key usage,
          need to revoke access by disabling key, cross-account key sharing
```

**3. External Key Store (XKS):**
```
Your own Hardware Security Module (HSM) manages the key material
KMS calls your external key manager for every crypto operation
Use when: Regulatory requirements mandate key storage outside AWS (rare)
```

### KMS Key Hierarchy

```
                     KMS CMK (Customer Master Key)
                          │
                          │ encrypts
                          ↓
                 Data Encryption Key (DEK)
                          │
                          │ encrypts
                          ↓
                     Your actual data

This is called "Envelope Encryption"

Why envelope encryption?
  - Your data might be 10 TB — you cannot encrypt 10 TB with KMS directly
    (KMS has a 4 KB limit per API call)
  - Instead: generate a DEK → encrypt your data with DEK → encrypt DEK with CMK
  - Store the encrypted DEK alongside the encrypted data
  - To decrypt: call KMS to decrypt the DEK → use DEK to decrypt data
```

### Working with KMS

```bash
# Create a Customer Managed Key (CMK)
KEY_ID=$(aws kms create-key \
  --description "Production application encryption key" \
  --key-usage ENCRYPT_DECRYPT \
  --policy '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Sid": "Enable IAM User Permissions",
        "Effect": "Allow",
        "Principal": {"AWS": "arn:aws:iam::123456789012:root"},
        "Action": "kms:*",
        "Resource": "*"
      },
      {
        "Sid": "Allow application role to use key",
        "Effect": "Allow",
        "Principal": {"AWS": "arn:aws:iam::123456789012:role/AppRole"},
        "Action": ["kms:Decrypt", "kms:DescribeKey", "kms:GenerateDataKey"],
        "Resource": "*"
      },
      {
        "Sid": "Allow key admin to manage key",
        "Effect": "Allow",
        "Principal": {"AWS": "arn:aws:iam::123456789012:role/KeyAdmin"},
        "Action": [
          "kms:Create*", "kms:Describe*", "kms:Enable*",
          "kms:List*", "kms:Put*", "kms:Update*",
          "kms:Revoke*", "kms:Disable*", "kms:Get*",
          "kms:Delete*", "kms:TagResource", "kms:UntagResource",
          "kms:ScheduleKeyDeletion", "kms:CancelKeyDeletion"
        ],
        "Resource": "*"
      }
    ]
  }' \
  --query 'KeyMetadata.KeyId' --output text)

# Create an alias (human-readable name)
aws kms create-alias \
  --alias-name alias/production-app-key \
  --target-key-id $KEY_ID

# Enable automatic key rotation (annually)
aws kms enable-key-rotation --key-id $KEY_ID

# Encrypt data directly with KMS (max 4 KB)
ENCRYPTED=$(aws kms encrypt \
  --key-id alias/production-app-key \
  --plaintext "SuperSecretData123" \
  --output text --query CiphertextBlob)

# Decrypt
aws kms decrypt \
  --ciphertext-blob $ENCRYPTED \
  --output text --query Plaintext | base64 --decode

# Generate a data key (for envelope encryption)
aws kms generate-data-key \
  --key-id alias/production-app-key \
  --key-spec AES_256
# Returns: Plaintext key (use to encrypt data) + EncryptedKeyBlob (store with data)
# Delete the Plaintext key from memory after use! Only store the encrypted key.
```

```python
import boto3
import base64
import os

kms = boto3.client('kms')

def encrypt_file(file_path, key_alias='alias/production-app-key'):
    # Generate a data encryption key (envelope encryption)
    response = kms.generate_data_key(
        KeyId=key_alias,
        KeySpec='AES_256'
    )
    
    # plaintext_key is the DEK — use it to encrypt data
    plaintext_key = response['Plaintext']
    encrypted_key = response['CiphertextBlob']
    
    # Encrypt the file with the DEK
    # (In real code, use cryptography library)
    # Here we just demonstrate the concept
    
    # IMPORTANT: Delete the plaintext key from memory after use!
    del plaintext_key
    
    # Store encrypted_key alongside encrypted file
    with open(file_path + '.key', 'wb') as f:
        f.write(encrypted_key)
    
    print(f"File encrypted. Encrypted DEK stored in {file_path}.key")

def decrypt_file(file_path):
    # Read the encrypted DEK
    with open(file_path + '.key', 'rb') as f:
        encrypted_key = f.read()
    
    # Decrypt the DEK using KMS
    response = kms.decrypt(CiphertextBlob=encrypted_key)
    plaintext_key = response['Plaintext']
    
    # Decrypt the file using the plaintext DEK
    # ... decryption logic here ...
    
    del plaintext_key  # Always clean up!
```

---

## 10.3 Secrets Manager — Managing Rotating Secrets

### What is Secrets Manager?

**Secrets Manager** is specifically designed for secrets that need to be:
- Stored securely (encrypted with KMS)
- Retrieved by applications (API call, no hardcoding)
- **Automatically rotated** (key feature vs Parameter Store)

**Secrets Manager vs SSM Parameter Store:**

| Feature | Secrets Manager | Parameter Store |
|---------|----------------|-----------------|
| Cost | $0.40/secret/month | Free (standard tier) |
| Automatic rotation | YES (native) | No |
| Cross-account access | YES | Limited |
| CloudFormation integration | YES | YES |
| Best for | Passwords, API keys needing rotation | Configuration values, non-rotating secrets |

**Example secret types:**
- Database passwords
- API keys (Stripe, Twilio, SendGrid)
- OAuth tokens
- SSH keys
- SSL certificates

```bash
# Store a database password in Secrets Manager
aws secretsmanager create-secret \
  --name /production/database/password \
  --description "Production MySQL admin password" \
  --secret-string '{
    "username": "admin",
    "password": "MySecureP@ssword123",
    "host": "production-mysql.abc123.us-east-1.rds.amazonaws.com",
    "port": 3306,
    "dbname": "appdb"
  }' \
  --kms-key-id alias/production-app-key

# Retrieve a secret
aws secretsmanager get-secret-value \
  --secret-id /production/database/password \
  --query SecretString --output text | python3 -m json.tool

# Configure automatic rotation for RDS password (Lambda rotation function)
aws secretsmanager rotate-secret \
  --secret-id /production/database/password \
  --rotation-lambda-arn arn:aws:lambda:us-east-1:123456789012:function:SecretsManagerRDSMySQLRotationSingleUser \
  --rotation-rules AutomaticallyAfterDays=30

# List all secrets
aws secretsmanager list-secrets \
  --query 'SecretList[*].[Name,LastRotatedDate,RotationEnabled]' \
  --output table
```

```python
import boto3
import json

def get_db_credentials():
    client = boto3.client('secretsmanager')
    response = client.get_secret_value(SecretId='/production/database/password')
    secret = json.loads(response['SecretString'])
    
    return {
        'host': secret['host'],
        'user': secret['username'],
        'password': secret['password'],
        'database': secret['dbname'],
        'port': secret['port']
    }

# In your application:
import pymysql

def get_db_connection():
    creds = get_db_credentials()
    return pymysql.connect(**creds)
```

---

## 10.4 AWS WAF — Web Application Firewall

### What is WAF?

**AWS WAF (Web Application Firewall)** filters incoming web requests to protect your applications from common web attacks.

**Analogy:** WAF is like a bouncer at the door of your web application. The bouncer checks every person coming in against a list of known troublemakers and rules. If someone looks suspicious (SQL injection in their request), they get turned away.

**Common attacks WAF protects against:**
- **SQL Injection:** `' OR 1=1 --` in form fields trying to manipulate database queries
- **XSS (Cross-Site Scripting):** Injecting malicious JavaScript into web pages
- **CSRF (Cross-Site Request Forgery):** Tricking users into unintended actions
- **DDoS application-layer attacks:** HTTP floods
- **Bot traffic:** Scrapers, credential stuffing, vulnerability scanners

**Where you can attach WAF:**
- Application Load Balancer (ALB)
- CloudFront distributions
- API Gateway
- AWS AppSync (GraphQL)
- Cognito User Pools

### WAF Rules and Rule Groups

```bash
# Create a WAF Web ACL with managed rule groups
aws wafv2 create-web-acl \
  --name production-web-acl \
  --scope REGIONAL \
  --default-action Allow={} \
  --rules '[
    {
      "Name": "AWSManagedRulesCommonRuleSet",
      "Priority": 1,
      "OverrideAction": {"None": {}},
      "VisibilityConfig": {
        "SampledRequestsEnabled": true,
        "CloudWatchMetricsEnabled": true,
        "MetricName": "CommonRuleSet"
      },
      "Statement": {
        "ManagedRuleGroupStatement": {
          "VendorName": "AWS",
          "Name": "AWSManagedRulesCommonRuleSet"
        }
      }
    },
    {
      "Name": "AWSManagedRulesSQLiRuleSet",
      "Priority": 2,
      "OverrideAction": {"None": {}},
      "VisibilityConfig": {
        "SampledRequestsEnabled": true,
        "CloudWatchMetricsEnabled": true,
        "MetricName": "SQLiRuleSet"
      },
      "Statement": {
        "ManagedRuleGroupStatement": {
          "VendorName": "AWS",
          "Name": "AWSManagedRulesSQLiRuleSet"
        }
      }
    },
    {
      "Name": "RateLimit",
      "Priority": 3,
      "Action": {"Block": {}},
      "VisibilityConfig": {
        "SampledRequestsEnabled": true,
        "CloudWatchMetricsEnabled": true,
        "MetricName": "RateLimit"
      },
      "Statement": {
        "RateBasedStatement": {
          "Limit": 2000,
          "AggregateKeyType": "IP"
        }
      }
    }
  ]' \
  --visibility-config SampledRequestsEnabled=true,CloudWatchMetricsEnabled=true,MetricName=WebACL \
  --region us-east-1

# Associate WAF with ALB
aws wafv2 associate-web-acl \
  --web-acl-arn arn:aws:wafv2:us-east-1:123456789012:regional/webacl/production-web-acl/xxx \
  --resource-arn arn:aws:elasticloadbalancing:us-east-1:123456789012:loadbalancer/app/my-alb/xxx
```

---

## 10.5 AWS Shield — DDoS Protection

### What is a DDoS Attack?

**DDoS (Distributed Denial of Service)** attacks flood your application with massive amounts of traffic from many sources, making it unavailable to legitimate users.

**Types:**
- **Volumetric attacks:** Flood with gigabits of traffic (network layer)
- **Protocol attacks:** Exploit weaknesses in network protocols (SYN floods)
- **Application-layer attacks:** HTTP floods targeting specific URLs

### AWS Shield Standard vs Advanced

**AWS Shield Standard (FREE, automatic):**
- Automatically enabled for ALL AWS customers
- Protects against most common DDoS attacks (Layers 3 and 4)
- Integrated with CloudFront, Route 53, ELB
- No cost, no configuration needed

**AWS Shield Advanced ($3,000/month per organization):**
- Enhanced DDoS protection for your specific resources
- 24/7 access to AWS DDoS Response Team (DRT)
- Real-time metrics and attack details
- DDoS cost protection (AWS will refund scaling costs caused by DDoS)
- Protection for: EC2, ELB, CloudFront, Route 53, Global Accelerator

**Exam tip:** Always use Shield Standard (it is free and automatic). Use Shield Advanced only for critical high-value applications or compliance requirements.

---

## 10.6 Amazon GuardDuty — Intelligent Threat Detection

### What is GuardDuty?

**GuardDuty** is a managed threat detection service that continuously monitors your AWS account for malicious activity and unauthorized behavior.

**Data sources GuardDuty analyzes:**
- VPC Flow Logs (network traffic patterns)
- CloudTrail logs (API call patterns)
- DNS query logs (unusual domain lookups)
- S3 data access logs (data exfiltration patterns)
- EKS audit logs
- Lambda network activity

**What GuardDuty detects:**
```
Account threats:
  - API calls from unusual geographic locations
  - Root account being used unexpectedly
  - Unusual volume of IAM user creation

EC2 threats:
  - Instance communicating with known malicious IP/domain
  - Cryptocurrency mining activities
  - Port scanning from your instances (your machine is compromised!)
  - Unusual outbound connections

S3 threats:
  - Public bucket policy changes
  - Unusual data access patterns (exfiltration)
  - Access from unusual geographic locations

EKS threats:
  - Privileged containers launched
  - Sensitive mounts detected
  - Suspicious network activity from pods
```

```bash
# Enable GuardDuty (one command!)
aws guardduty create-detector \
  --enable \
  --finding-publishing-frequency SIX_HOURS \
  --data-sources '{
    "S3Logs": {"Enable": true},
    "Kubernetes": {"AuditLogs": {"Enable": true}},
    "MalwareProtection": {"ScanEc2InstanceWithFindings": {"EbsVolumes": true}}
  }'

# Get the detector ID
DETECTOR_ID=$(aws guardduty list-detectors \
  --query 'DetectorIds[0]' --output text)

# List current findings (threats detected)
aws guardduty list-findings \
  --detector-id $DETECTOR_ID \
  --finding-criteria '{
    "Criterion": {
      "severity": {
        "Gte": 7
      }
    }
  }'

# Get detailed information about a finding
aws guardduty get-findings \
  --detector-id $DETECTOR_ID \
  --finding-ids finding-id-1 finding-id-2 \
  --query 'Findings[*].[Title,Severity,Description,Service.Action]'

# Auto-remediate GuardDuty findings with EventBridge + Lambda
# EventBridge rule: When GuardDuty finding severity >= 7
# Action: Lambda function that isolates the compromised instance
```

---

## 10.7 Amazon Inspector — Vulnerability Assessment

### What is Inspector?

**Amazon Inspector** is an automated vulnerability management service that:
- Scans EC2 instances for OS and software vulnerabilities (CVEs)
- Scans container images in ECR for vulnerabilities
- Scans Lambda functions for code and dependency vulnerabilities
- Assigns a risk score to help prioritize remediation

```bash
# Enable Amazon Inspector (for EC2 and ECR scanning)
aws inspector2 enable \
  --resource-types EC2 ECR LAMBDA

# List findings sorted by severity
aws inspector2 list-findings \
  --filter-criteria '{
    "findingStatus": [{
      "comparison": "EQUALS",
      "value": "ACTIVE"
    }],
    "severity": [{
      "comparison": "EQUALS",
      "value": "CRITICAL"
    }]
  }' \
  --sort-criteria field=INSPECTOR_SCORE,sortOrder=DESC \
  --query 'findings[*].[title,severity,resources[0].id,inspectorScore]' \
  --output table
```

---

## 10.8 AWS Security Hub — Central Security Dashboard

### What is Security Hub?

**Security Hub** aggregates security findings from multiple AWS security services into a single view:
- GuardDuty (threat detection)
- Inspector (vulnerability assessment)
- Config (configuration compliance)
- Macie (data security)
- IAM Access Analyzer
- Third-party tools (Splunk, PagerDuty, etc.)

Security Hub also checks your AWS environment against security standards:
- CIS AWS Foundations Benchmark
- AWS Foundational Security Best Practices
- PCI DSS
- NIST

```bash
# Enable Security Hub
aws securityhub enable-security-hub \
  --enable-default-standards \
  --control-finding-generator SECURITY_CONTROL

# Get your overall security score
aws securityhub get-findings \
  --filters '{"WorkflowStatus": [{"Value": "NEW", "Comparison": "EQUALS"}]}' \
  --sort-criteria '{"Field": "SeverityLabel", "SortOrder": "asc"}' \
  --query 'Findings[0:10].[Title,SeverityLabel,ProductName]' \
  --output table

# Subscribe to a security standard
aws securityhub batch-enable-standards \
  --standards-subscription-requests '[
    {"StandardsArn": "arn:aws:securityhub:us-east-1::standards/cis-aws-foundations-benchmark/v/1.4.0"},
    {"StandardsArn": "arn:aws:securityhub:us-east-1::standards/aws-foundational-security-best-practices/v/1.0.0"}
  ]'
```

---

## 10.9 Amazon Macie — Data Security for S3

### What is Macie?

**Macie** uses machine learning to automatically discover, classify, and protect sensitive data in S3 buckets.

**What Macie detects:**
- PII (Personally Identifiable Information): Names, addresses, SSNs, passport numbers
- Financial data: Credit card numbers, bank account numbers
- Healthcare data: Medical record numbers, drug names
- Credentials: AWS API keys, passwords in files

```bash
# Enable Macie
aws macie2 enable-macie --status ENABLED

# Create a sensitive data discovery job for all S3 buckets
aws macie2 create-classification-job \
  --job-type SCHEDULED \
  --name all-buckets-pii-scan \
  --schedule-frequency DAILY \
  --s3-job-definition '{
    "bucketDefinitions": [{
      "accountId": "123456789012",
      "buckets": ["sensitive-data-bucket-1", "customer-data-bucket"]
    }]
  }'

# Check findings (sensitive data discovered)
aws macie2 list-findings \
  --query 'findingIds[*]' | head -5
```

---

## 10.10 IAM Access Analyzer — Who Can Access What

### What is IAM Access Analyzer?

**IAM Access Analyzer** identifies resources in your account that can be accessed from outside your account (or from trusted accounts that you did not intend). It generates **findings** for:

- S3 buckets accessible from other accounts
- IAM roles assumable from other accounts
- KMS keys accessible from other accounts
- Lambda functions accessible from other accounts
- SQS queues accessible from other accounts

```bash
# Enable IAM Access Analyzer
aws accessanalyzer create-analyzer \
  --analyzer-name production-account-analyzer \
  --type ACCOUNT

# List findings (external access identified)
aws accessanalyzer list-findings \
  --analyzer-arn arn:aws:access-analyzer:us-east-1:123456789012:analyzer/production-account-analyzer \
  --filter '{"status": {"eq": ["ACTIVE"]}}' \
  --query 'findings[*].[id,resourceType,resource,action,principal]' \
  --output table

# Archive a finding if the external access is intentional
aws accessanalyzer update-findings \
  --analyzer-arn arn:aws:access-analyzer:us-east-1:123456789012:analyzer/production-account-analyzer \
  --ids ["finding-id-1"] \
  --status ARCHIVED
```

---

## 10.11 Practice Questions

**Q1:** Your application stores credit card data. To comply with PCI DSS, you must encrypt the data with a key that you control and can revoke at any time. Which KMS key type should you use?

- A) AWS Managed Key (aws/s3)
- B) Customer Managed Key (CMK) with a key policy restricting access
- C) External Key Store (XKS)
- D) Default S3 encryption key

**Answer: B**

Explanation: PCI DSS requires control over encryption keys, including the ability to revoke access. A Customer Managed Key (CMK) gives you full control: you can disable the key (immediately denying all access to encrypted data), schedule deletion, restrict usage via key policy, enable automatic rotation, and audit usage via CloudTrail. AWS Managed Keys (A) are managed by AWS — you cannot disable them or control their rotation on your schedule. External Key Store (C) is an option but is overkill and complex for PCI DSS requirements.

---

**Q2:** GuardDuty generates a HIGH severity finding: "EC2 instance i-0abc123 is communicating with a known cryptocurrency mining pool." What should you do FIRST?

- A) Terminate the instance immediately
- B) Isolate the instance by moving it to a quarantine security group with no inbound/outbound access, preserve the instance for forensic investigation
- C) Ignore it — cryptocurrency mining is not harmful
- D) Reboot the instance to stop the mining

**Answer: B**

Explanation: The correct incident response for a compromised instance is: (1) Isolate first — move to a quarantine security group that blocks all traffic (prevent lateral movement and data exfiltration). (2) Preserve — do not terminate; take a memory dump and disk snapshot for forensic investigation. (3) Investigate — determine how the compromise happened (missing patch? Stolen credentials? Open port?). (4) Remediate — after investigation, terminate the compromised instance and deploy a clean one. Terminating immediately (A) destroys forensic evidence.

---

**Q3:** Your company has an S3 bucket that stores customer PII. You need to know if the bucket is accessible from any other AWS account. Which service provides this automatically?

- A) Amazon Macie
- B) AWS Config
- C) IAM Access Analyzer
- D) CloudTrail

**Answer: C**

Explanation: IAM Access Analyzer continuously monitors resource policies and identifies resources accessible from outside your account (or outside your AWS Organization). It generates findings for S3 buckets with bucket policies allowing external access, even if the access is complex and conditional. Macie (A) discovers sensitive data IN the bucket but doesn't analyze cross-account access policies. Config (B) can check public access settings but doesn't analyze complex cross-account permission scenarios as deeply.

---

**Q4:** An application is getting SQL injection attempts. You want to block these at the network level without modifying application code. What should you use?

- A) Security Groups
- B) VPC NACLs
- C) AWS WAF with SQLi rule set
- D) Amazon Inspector

**Answer: C**

Explanation: AWS WAF with the AWSManagedRulesSQLiRuleSet inspects the content of HTTP requests (headers, body, query strings) for SQL injection patterns and blocks them before they reach your application. Security Groups and NACLs (A, B) operate at network layer (IP/port) and cannot inspect HTTP request content — they do not understand SQL injection. Inspector (D) scans your application code for vulnerabilities but does not block runtime attacks.

---

**Q5:** What is "envelope encryption" and why does AWS use it?

- A) Encrypting data in an envelope (compressed file) before sending to S3
- B) Using a Data Encryption Key (DEK) to encrypt data, then encrypting the DEK with a master key (CMK)
- C) Wrapping the KMS API call in an HTTPS envelope
- D) Encrypting the encryption key with the data

**Answer: B**

Explanation: Envelope encryption is a two-layer encryption pattern: (1) Generate a DEK (symmetric key) → (2) Encrypt your data with the DEK → (3) Encrypt the DEK with your CMK in KMS → (4) Store encrypted data + encrypted DEK together. The CMK never leaves KMS. When decrypting: KMS decrypts the DEK → you use DEK to decrypt data → delete DEK from memory. This is used because KMS has a 4 KB per-API call limit (can't encrypt large data directly), and it's more efficient to use fast symmetric encryption for large data and asymmetric/KMS for small key material.

---

## Chapter 10 Summary

| Service/Concept | Purpose | Key Fact |
|----------------|---------|----------|
| KMS CMK | Encrypt AWS data | $1/month/key; full control; audit via CloudTrail |
| KMS AWS Managed Keys | Default encryption | Free; AWS manages; limited control |
| Envelope Encryption | Large data encryption | DEK encrypts data; CMK encrypts DEK; 4KB KMS limit |
| Key Rotation | Avoid long-lived keys | CMK: enable auto-annual rotation |
| Secrets Manager | Rotating secrets | $0.40/secret; automatic rotation; RDS native support |
| Parameter Store | Configuration | Free standard tier; SecureString for secrets |
| WAF | App-layer firewall | Blocks SQLi, XSS, rate limiting; attach to ALB/CF |
| Shield Standard | DDoS protection | FREE; automatic; Layers 3 and 4 |
| Shield Advanced | Enhanced DDoS | $3,000/month; 24/7 DRT; DDoS cost protection |
| GuardDuty | Threat detection | Analyzes VPC Flow Logs + CloudTrail + DNS; ML-based |
| Inspector | Vulnerability scanning | CVE detection in EC2/ECR/Lambda |
| Security Hub | Central dashboard | Aggregates GuardDuty + Inspector + Config + Macie |
| Macie | S3 data discovery | Finds PII/financial/health data in S3 using ML |
| IAM Access Analyzer | External access | Finds resources accessible from outside your account |
"""

with open(r"e:\fastapi\aws-admin\10_Security_Compliance_KMS.md", "w", encoding="utf-8") as f:
    f.write(content)

print(f"Written {len(content.splitlines())} lines")
