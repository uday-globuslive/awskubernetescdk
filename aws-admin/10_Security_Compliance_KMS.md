# Chapter 10: Security, Compliance & KMS

## AWS SysOps Administrator Exam Domain Coverage
- **Domain 5**: Security and Compliance (16% of exam)
- KMS, Secrets Manager, WAF, GuardDuty, Security Hub, Inspector heavily tested

---

## 10.1 AWS KMS — Key Management Service

KMS is the **cryptographic foundation** of AWS security. Almost every AWS service uses KMS for encryption.

### KMS Key Types

| Key Type | Created By | Managed By | Rotation | Cost |
|----------|-----------|------------|---------|------|
| **AWS Managed Key** | AWS | AWS | Automatic (annual) | Free |
| **Customer Managed Key (CMK)** | You | You | Optional (annual) | $1/month |
| **Imported Key** | You (outside AWS) | You | Manual only | $1/month |

```
Key Hierarchy (Envelope Encryption):

  Your Data ──► Encrypted with ──► Data Key (DEK)
                                         │
                                         ▼
                                  Encrypted with ──► CMK (in KMS HSM)
                                  
  KMS never exposes the CMK — it only decrypts the DEK when authorized
```

### Creating and Using KMS Keys
```bash
# Create a CMK
aws kms create-key \
  --description "Production application encryption key" \
  --key-usage ENCRYPT_DECRYPT \
  --key-spec SYMMETRIC_DEFAULT \
  --tags TagKey=Environment,TagValue=production

# Create alias for the key
aws kms create-alias \
  --alias-name alias/production-app-key \
  --target-key-id arn:aws:kms:us-east-1:123456789012:key/key-id

# Enable automatic annual rotation
aws kms enable-key-rotation --key-id alias/production-app-key

# Encrypt data
aws kms encrypt \
  --key-id alias/production-app-key \
  --plaintext fileb://secret.txt \
  --output text \
  --query CiphertextBlob | base64 --decode > encrypted.bin

# Decrypt data
aws kms decrypt \
  --ciphertext-blob fileb://encrypted.bin \
  --output text \
  --query Plaintext | base64 --decode
```

### Key Policies — Control Who Can Use Keys
```json
{
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
      "Sid": "Allow key administrators",
      "Effect": "Allow",
      "Principal": {"AWS": ["arn:aws:iam::123456789012:role/KeyAdminRole"]},
      "Action": [
        "kms:Create*", "kms:Describe*", "kms:Enable*", "kms:List*",
        "kms:Put*", "kms:Update*", "kms:Revoke*", "kms:Disable*",
        "kms:Get*", "kms:Delete*", "kms:ScheduleKeyDeletion", "kms:CancelKeyDeletion"
      ],
      "Resource": "*"
    },
    {
      "Sid": "Allow application to use key",
      "Effect": "Allow",
      "Principal": {"AWS": ["arn:aws:iam::123456789012:role/AppRole"]},
      "Action": ["kms:Encrypt", "kms:Decrypt", "kms:ReEncrypt*", "kms:GenerateDataKey*", "kms:DescribeKey"],
      "Resource": "*"
    },
    {
      "Sid": "Allow CloudWatch Logs to use key",
      "Effect": "Allow",
      "Principal": {"Service": "logs.us-east-1.amazonaws.com"},
      "Action": ["kms:Encrypt*", "kms:Decrypt*", "kms:ReEncrypt*", "kms:GenerateDataKey*", "kms:Describe*"],
      "Resource": "*",
      "Condition": {
        "ArnLike": {
          "kms:EncryptionContext:aws:logs:arn": "arn:aws:logs:us-east-1:123456789012:*"
        }
      }
    }
  ]
}
```

### Envelope Encryption in Python
```python
import boto3
import os
from cryptography.fernet import Fernet

kms = boto3.client('kms')

def encrypt_data(plaintext: bytes, key_alias: str) -> dict:
    """Encrypt data using envelope encryption."""
    
    # Step 1: Generate a data encryption key (DEK) using KMS
    response = kms.generate_data_key(
        KeyId=f'alias/{key_alias}',
        KeySpec='AES_256'
    )
    
    plaintext_key = response['Plaintext']       # Use to encrypt
    encrypted_key = response['CiphertextBlob']  # Store this, discard plaintext_key after use
    
    # Step 2: Encrypt the data locally using the DEK (much faster than KMS for large data)
    f = Fernet(base64.urlsafe_b64encode(plaintext_key[:32]))
    encrypted_data = f.encrypt(plaintext)
    
    # Step 3: Discard plaintext DEK from memory
    del plaintext_key
    
    return {
        'encrypted_data': encrypted_data,
        'encrypted_key': encrypted_key  # Store alongside encrypted_data
    }

def decrypt_data(encrypted_data: bytes, encrypted_key: bytes) -> bytes:
    """Decrypt data using envelope encryption."""
    
    # Step 1: Decrypt the DEK using KMS
    response = kms.decrypt(CiphertextBlob=encrypted_key)
    plaintext_key = response['Plaintext']
    
    # Step 2: Decrypt the data using the DEK
    f = Fernet(base64.urlsafe_b64encode(plaintext_key[:32]))
    return f.decrypt(encrypted_data)
```

### KMS Cross-Account Access
```bash
# In Key Account: add cross-account principal to key policy
# In Consumer Account: create IAM policy to use the key
aws iam create-policy \
  --policy-name UseCrossAccountKMSKey \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Action": ["kms:Encrypt","kms:Decrypt","kms:GenerateDataKey"],
      "Resource": "arn:aws:kms:us-east-1:KEY_ACCOUNT:key/key-id"
    }]
  }'
```

---

## 10.2 Secrets Manager vs Parameter Store

| Feature | Secrets Manager | Parameter Store |
|---------|----------------|----------------|
| **Cost** | $0.40/secret/month | Free (Standard), $0.05/10k API calls (Advanced) |
| **Automatic Rotation** | Yes (Lambda-based) | No (custom Lambda needed) |
| **Cross-Account** | Yes | Limited |
| **Max Size** | 65KB | 4KB (Standard), 8KB (Advanced) |
| **Encryption** | KMS (mandatory) | KMS (optional) |
| **Best For** | DB passwords, API keys that rotate | App config, feature flags |

### Secrets Manager with Automatic Rotation
```bash
# Store a database secret
aws secretsmanager create-secret \
  --name /production/database/postgres \
  --description "Production PostgreSQL credentials" \
  --secret-string '{
    "engine": "postgres",
    "host": "prod-postgres.cluster.rds.amazonaws.com",
    "username": "admin",
    "password": "InitialPassword123!",
    "dbname": "production",
    "port": 5432
  }' \
  --kms-key-id alias/production-secrets-key

# Enable automatic rotation (every 30 days)
aws secretsmanager rotate-secret \
  --secret-id /production/database/postgres \
  --rotation-lambda-arn arn:aws:lambda:us-east-1:123456789012:function:RDSSecretRotation \
  --rotation-rules AutomaticallyAfterDays=30
```

```python
# Retrieve secrets in Python (cached for performance)
import boto3
import json
from functools import lru_cache

@lru_cache(maxsize=None)
def get_secret(secret_name: str) -> dict:
    """Retrieve and cache a secret from Secrets Manager."""
    client = boto3.client('secretsmanager')
    
    response = client.get_secret_value(SecretId=secret_name)
    
    if 'SecretString' in response:
        return json.loads(response['SecretString'])
    else:
        return json.loads(base64.b64decode(response['SecretBinary']))

# Usage
db_secret = get_secret('/production/database/postgres')
connection = psycopg2.connect(
    host=db_secret['host'],
    user=db_secret['username'],
    password=db_secret['password'],
    database=db_secret['dbname'],
    sslmode='require'
)
```

---

## 10.3 AWS Certificate Manager (ACM)

ACM provides **free SSL/TLS certificates** for use with AWS services.

```bash
# Request a public certificate
aws acm request-certificate \
  --domain-name "example.com" \
  --subject-alternative-names "*.example.com" "api.example.com" \
  --validation-method DNS

# Check validation status
aws acm describe-certificate \
  --certificate-arn arn:aws:acm:us-east-1:123456789012:certificate/xxx \
  --query 'Certificate.{Status:Status,DomainValidation:DomainValidationOptions}'

# Add ACM cert to ALB
aws elbv2 add-listener-certificates \
  --listener-arn arn:aws:elasticloadbalancing:... \
  --certificates CertificateArn=arn:aws:acm:...

# HTTPS redirect listener rule
aws elbv2 create-rule \
  --listener-arn arn:aws:elasticloadbalancing:...:listener/HTTP-80 \
  --conditions '[{"Field":"path-pattern","Values":["/*"]}]' \
  --priority 100 \
  --actions '[{
    "Type": "redirect",
    "RedirectConfig": {
      "Protocol": "HTTPS",
      "Port": "443",
      "StatusCode": "HTTP_301"
    }
  }]'
```

---

## 10.4 AWS WAF — Web Application Firewall

WAF protects web applications from common exploits (OWASP Top 10).

```
Internet → WAF (checks requests) → CloudFront/ALB/API Gateway → Application
```

### WAF Rules
```bash
# Create Web ACL with managed rules
aws wafv2 create-web-acl \
  --name production-waf \
  --scope REGIONAL \
  --default-action Allow={} \
  --rules '[
    {
      "Name": "AWSManagedRulesCommonRuleSet",
      "Priority": 10,
      "OverrideAction": {"None": {}},
      "Statement": {
        "ManagedRuleGroupStatement": {
          "VendorName": "AWS",
          "Name": "AWSManagedRulesCommonRuleSet"
        }
      },
      "VisibilityConfig": {
        "SampledRequestsEnabled": true,
        "CloudWatchMetricsEnabled": true,
        "MetricName": "CommonRuleSet"
      }
    },
    {
      "Name": "AWSManagedRulesKnownBadInputsRuleSet",
      "Priority": 20,
      "OverrideAction": {"None": {}},
      "Statement": {
        "ManagedRuleGroupStatement": {
          "VendorName": "AWS",
          "Name": "AWSManagedRulesKnownBadInputsRuleSet"
        }
      },
      "VisibilityConfig": {
        "SampledRequestsEnabled": true,
        "CloudWatchMetricsEnabled": true,
        "MetricName": "KnownBadInputs"
      }
    },
    {
      "Name": "RateLimitRule",
      "Priority": 1,
      "Action": {"Block": {}},
      "Statement": {
        "RateBasedStatement": {
          "Limit": 2000,
          "AggregateKeyType": "IP"
        }
      },
      "VisibilityConfig": {
        "SampledRequestsEnabled": true,
        "CloudWatchMetricsEnabled": true,
        "MetricName": "RateLimit"
      }
    }
  ]' \
  --visibility-config SampledRequestsEnabled=true,CloudWatchMetricsEnabled=true,MetricName=ProductionWAF \
  --region us-east-1
```

### Attach WAF to ALB
```bash
aws wafv2 associate-web-acl \
  --web-acl-arn arn:aws:wafv2:us-east-1:123456789012:regional/webacl/production-waf/xxx \
  --resource-arn arn:aws:elasticloadbalancing:us-east-1:123456789012:loadbalancer/app/prod-alb/xxx
```

---

## 10.5 AWS Shield

| Tier | Cost | Protection |
|------|------|-----------|
| **Shield Standard** | Free | Always on — protects against common DDoS at L3/L4 |
| **Shield Advanced** | $3,000/month | Enhanced DDoS protection, cost protection, 24x7 DRT access |

```bash
# Enable Shield Advanced protection on a resource
aws shield create-protection \
  --name prod-alb-protection \
  --resource-arn arn:aws:elasticloadbalancing:...

# Subscribe to Shield Advanced (account-wide)
aws shield create-subscription

# Check DDoS attack events
aws shield list-attacks \
  --start-time StartTime=$(date -d '24 hours ago' +%s)000 \
  --end-time EndTime=$(date +%s)000
```

---

## 10.6 Amazon GuardDuty

GuardDuty is an **intelligent threat detection** service that analyzes VPC Flow Logs, CloudTrail, and DNS logs.

### GuardDuty Finding Types

| Category | Examples |
|----------|---------|
| **Backdoor** | EC2 communicating with C&C server |
| **Behavior** | IAM user calling from unusual location |
| **CryptoCurrency** | EC2 mining cryptocurrency |
| **Recon** | Port scanning against your EC2 instances |
| **Stealth** | CloudTrail logging disabled |
| **Trojan** | EC2 requesting known malware domain |
| **UnauthorizedAccess** | Brute-force SSH attempt |

```bash
# Enable GuardDuty
aws guardduty create-detector \
  --enable \
  --finding-publishing-frequency FIFTEEN_MINUTES \
  --features '[
    {"Name":"EKS_AUDIT_LOGS","Status":"ENABLED"},
    {"Name":"S3_DATA_EVENTS","Status":"ENABLED"},
    {"Name":"EKS_RUNTIME_MONITORING","Status":"ENABLED"},
    {"Name":"LAMBDA_NETWORK_LOGS","Status":"ENABLED"},
    {"Name":"RDS_LOGIN_EVENTS","Status":"ENABLED"}
  ]'

# Get active findings
aws guardduty list-findings \
  --detector-id $(aws guardduty list-detectors --query 'DetectorIds[0]' --output text) \
  --finding-criteria '{
    "Criterion": {
      "severity": {"Gte": 7},
      "service.archived": {"Eq": ["false"]}
    }
  }'

# Get finding details
aws guardduty get-findings \
  --detector-id DETECTOR_ID \
  --finding-ids FINDING_ID_1 FINDING_ID_2

# Add trusted IP list (suppress findings from known IPs)
aws guardduty create-ip-set \
  --detector-id DETECTOR_ID \
  --name corporate-ips \
  --format TXT \
  --location s3://my-bucket/trusted-ips.txt \
  --activate
```

### Automated GuardDuty Response
```python
import boto3
import json

ec2 = boto3.client('ec2')
ssm = boto3.client('ssm')

def lambda_handler(event, context):
    """Auto-respond to GuardDuty findings via EventBridge."""
    
    finding = event['detail']
    severity = finding['severity']
    finding_type = finding['type']
    resource = finding.get('resource', {})
    
    print(f"GuardDuty Finding: {finding_type} (severity: {severity})")
    
    # High severity (7+) = automatic isolation
    if severity >= 7:
        instance_id = resource.get('instanceDetails', {}).get('instanceId')
        
        if instance_id and 'CryptoCurrency' in finding_type:
            # Isolate compromised instance
            isolate_instance(instance_id, finding)
    
    # Medium severity (4-6) = gather forensics
    elif severity >= 4:
        instance_id = resource.get('instanceDetails', {}).get('instanceId')
        if instance_id:
            gather_forensics(instance_id, finding)

def isolate_instance(instance_id: str, finding: dict):
    """Isolate potentially compromised EC2 instance."""
    
    # Create isolation security group (no inbound/outbound except for forensics)
    vpc_id = ec2.describe_instances(
        InstanceIds=[instance_id]
    )['Reservations'][0]['Instances'][0]['VpcId']
    
    isolation_sg = ec2.create_security_group(
        GroupName=f'ISOLATION-{instance_id}',
        Description=f'Isolation SG - GuardDuty finding: {finding["id"]}',
        VpcId=vpc_id
    )['GroupId']
    
    # Remove all existing security groups, apply isolation SG
    ec2.modify_instance_attribute(
        InstanceId=instance_id,
        Groups=[isolation_sg]
    )
    
    # Tag instance as compromised
    ec2.create_tags(
        Resources=[instance_id],
        Tags=[
            {'Key': 'SecurityStatus', 'Value': 'ISOLATED'},
            {'Key': 'GuardDutyFindingId', 'Value': finding['id']},
            {'Key': 'IsolationTimestamp', 'Value': finding['updatedAt']}
        ]
    )
    
    print(f"✅ Isolated instance {instance_id}")

def gather_forensics(instance_id: str, finding: dict):
    """Capture forensic data from instance."""
    
    # Run memory dump and network connections snapshot
    ssm.send_command(
        InstanceIds=[instance_id],
        DocumentName='AWS-RunShellScript',
        Parameters={'commands': [
            'ss -tuanp > /tmp/network_connections.txt',
            'ps auxf > /tmp/processes.txt',
            'netstat -rn > /tmp/routing_table.txt',
            f'aws s3 cp /tmp/ s3://forensics-bucket/{instance_id}/ --recursive'
        ]}
    )
```

---

## 10.7 AWS Security Hub

Security Hub **aggregates findings** from GuardDuty, Inspector, Macie, IAM Access Analyzer, and third-party tools.

```bash
# Enable Security Hub with CIS benchmark
aws securityhub enable-security-hub \
  --enable-default-standards \  # Enables CIS AWS Foundations + AWS Foundational Security
  --tags Environment=production

# Enable specific security standard
aws securityhub batch-enable-standards \
  --standards-subscription-requests \
    StandardsArn=arn:aws:securityhub:us-east-1::standards/cis-aws-foundations-benchmark/v/1.4.0
    StandardsArn=arn:aws:securityhub:us-east-1::standards/pci-dss/v/3.2.1

# Get security score
aws securityhub describe-hub --query 'HubArn'

# Get critical findings
aws securityhub get-findings \
  --filters '{
    "SeverityLabel": [{"Value":"CRITICAL","Comparison":"EQUALS"}],
    "RecordState": [{"Value":"ACTIVE","Comparison":"EQUALS"}],
    "WorkflowStatus": [{"Value":"NEW","Comparison":"EQUALS"}]
  }' \
  --max-results 20

# Aggregate findings from multiple regions
aws securityhub create-finding-aggregator \
  --region-linking-mode ALL_REGIONS  # or SPECIFIED_REGIONS
```

---

## 10.8 Amazon Inspector

Inspector performs **automated vulnerability scanning** for EC2, ECR, and Lambda.

```bash
# Enable Inspector v2
aws inspector2 enable \
  --resource-types EC2 ECR LAMBDA

# Get findings summary
aws inspector2 list-findings \
  --filter-criteria '{
    "findingStatus": [{"comparison":"EQUALS","value":"ACTIVE"}],
    "severity": [{"comparison":"EQUALS","value":"CRITICAL"}]
  }'

# Get EC2 instance coverage (which instances are being scanned)
aws inspector2 list-coverage \
  --filter-criteria '{
    "resourceType": [{"comparison":"EQUALS","value":"AWS_EC2_INSTANCE"}]
  }'
```

---

## 10.9 Amazon Macie

Macie uses ML to **discover sensitive data** (PII, credentials) in S3.

```bash
# Enable Macie
aws macie2 enable-macie

# Create a sensitive data discovery job
aws macie2 create-classification-job \
  --job-type ONE_TIME \
  --name find-sensitive-data-s3 \
  --s3-job-definition '{
    "bucketDefinitions": [{
      "accountId": "123456789012",
      "buckets": ["prod-data-lake", "user-uploads"]
    }]
  }' \
  --managed-data-identifier-ids \
    CREDIT_CARD_NUMBER \
    EMAIL_ADDRESS \
    US_SOCIAL_SECURITY_NUMBER \
    AWS_CREDENTIALS

# Get findings
aws macie2 list-findings \
  --finding-criteria '{
    "criterion": {
      "severity.description": {"eq": ["High","Critical"]}
    }
  }'
```

---

## 10.10 AWS Firewall Manager

Centrally manage WAF, Shield, Security Groups, and Network Firewall across accounts.

```bash
# Create WAF policy (deploy WAF to all ALBs across all accounts in Org)
aws fms create-policy \
  --policy '{
    "PolicyName": "org-waf-policy",
    "SecurityServicePolicyData": {
      "Type": "WAFV2",
      "ManagedServiceData": "{\"type\":\"WAFV2\",\"defaultAction\":{\"type\":\"ALLOW\"},\"preProcessRuleGroups\":[{\"managedRuleGroupIdentifier\":{\"vendorName\":\"AWS\",\"managedRuleGroupName\":\"AWSManagedRulesCommonRuleSet\"},\"overrideAction\":{\"type\":\"NONE\"},\"priority\":1}]}"
    },
    "ResourceType": "AWS::ElasticLoadBalancingV2::LoadBalancer",
    "IncludeMap": {
      "ACCOUNT": ["123456789012","234567890123"]
    },
    "RemediationEnabled": true,
    "ExcludeResourceTags": false
  }'
```

---

## 10.11 IAM Access Analyzer

Identifies resources shared with external entities (outside your AWS organization).

```bash
# Create an analyzer
aws accessanalyzer create-analyzer \
  --analyzer-name org-analyzer \
  --type ORGANIZATION \
  --archive-rules '[{
    "ruleName": "allowed-cross-account-access",
    "filter": {
      "principal.AWS": {"contains": ["arn:aws:iam::TRUSTED_ACCOUNT:root"]}
    }
  }]'

# List active findings
aws accessanalyzer list-findings \
  --analyzer-arn arn:aws:accessanalyzer:us-east-1:123456789012:analyzer/org-analyzer \
  --filter '{"status": {"eq": ["ACTIVE"]}}' \
  --query 'findings[*].{Id:id,Type:findingType,Resource:resource,Principal:principal}'

# Validate IAM policy (before deploying)
aws accessanalyzer validate-policy \
  --policy-document file://policy.json \
  --policy-type IDENTITY_POLICY
```

---

## 10.12 Real-World Project: Security Baseline Automation

### Auto-Enable Security Services on New Accounts
```python
import boto3
import json

def setup_account_security_baseline(account_id: str, region: str):
    """Enable security baseline for a new AWS account."""
    
    # Assume role in target account
    sts = boto3.client('sts')
    credentials = sts.assume_role(
        RoleArn=f'arn:aws:iam::{account_id}:role/SecuritySetupRole',
        RoleSessionName='SecurityBaseline'
    )['Credentials']
    
    session = boto3.Session(
        aws_access_key_id=credentials['AccessKeyId'],
        aws_secret_access_key=credentials['SecretAccessKey'],
        aws_session_token=credentials['SessionToken']
    )
    
    # Enable GuardDuty
    gd = session.client('guardduty', region_name=region)
    detector_id = gd.create_detector(
        Enable=True,
        FindingPublishingFrequency='FIFTEEN_MINUTES'
    )['DetectorId']
    print(f"✅ GuardDuty enabled: {detector_id}")
    
    # Enable Security Hub
    sh = session.client('securityhub', region_name=region)
    sh.enable_security_hub(EnableDefaultStandards=True)
    print("✅ Security Hub enabled")
    
    # Enable Config
    cf = session.client('config', region_name=region)
    cf.put_configuration_recorder(
        ConfigurationRecorder={
            'name': 'default',
            'roleARN': f'arn:aws:iam::{account_id}:role/AWSConfigRole',
            'recordingGroup': {'allSupported': True, 'includeGlobalResourceTypes': True}
        }
    )
    cf.start_configuration_recorder(ConfigurationRecorderName='default')
    print("✅ Config enabled")
    
    # Enable CloudTrail (multi-region)
    ct = session.client('cloudtrail', region_name=region)
    ct.create_trail(
        Name='security-trail',
        S3BucketName=f'cloudtrail-logs-{account_id}',
        IsMultiRegionTrail=True,
        IncludeGlobalServiceEvents=True,
        EnableLogFileValidation=True
    )
    ct.start_logging(Name='security-trail')
    print("✅ CloudTrail enabled")
    
    print(f"\n✅ Security baseline complete for account {account_id}")
```

---

## 10.13 Practice Questions (SysOps Exam Level)

**Q1:** An EC2 instance is reading data from an encrypted EBS volume using a CMK. The CMK is deleted. What happens to the data?

**A:** The data becomes **permanently inaccessible**. You cannot recover data encrypted with a deleted CMK — the CMK is destroyed after a 7-30 day waiting period.

**Prevention:**
```bash
# CMK has a mandatory waiting period before deletion (7-30 days)
aws kms schedule-key-deletion \
  --key-id alias/production-key \
  --pending-window-in-days 30  # Maximum — gives time to cancel

# Create CloudWatch alarm to detect accidental deletion scheduling
aws cloudwatch put-metric-alarm \
  --alarm-name kms-key-deletion-scheduled \
  --namespace CloudTrailMetrics \
  --metric-name KMSKeyPendingDeletionCount \
  --alarm-actions arn:aws:sns:...:security-critical-alerts
```

---

**Q2:** GuardDuty detects "Recon:EC2/PortProbeUnprotectedPort" on your bastion host. What should you do?

**A:**
1. **Verify**: Is the source IP your internal network or external?
2. **Immediate**: Add the source IP to NACL deny rule if external
3. **Investigate**: Check VPC Flow Logs for scope of reconnaissance
4. **Harden**: If using Session Manager, disable port 22 entirely:
   - Remove Security Group inbound rule for port 22
   - Use only Session Manager for access
5. **Archive finding** once resolved to track remediation

---

**Q3:** You need to ensure all S3 buckets in your organization never have public access enabled. What is the most comprehensive solution?

**A:** Multiple defense layers:
1. **Account-level S3 Block Public Access** (covers all buckets)
2. **SCP** denying `s3:PutBucketPublicAccessBlock` with value false
3. **AWS Config rule** `s3-bucket-public-access-prohibited`
4. **AWS Config automatic remediation** to disable public access if enabled
5. **Macie** to detect if sensitive data is exposed publicly

```bash
# Account-level block (immediate)
aws s3control put-public-access-block \
  --account-id 123456789012 \
  --public-access-block-configuration \
    BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
```

---

**Q4:** How does KMS key rotation work, and does it affect access to previously encrypted data?

**A:**
- KMS **automatic annual rotation** creates a **new backing key** but retains the old key material
- Previously encrypted data can **still be decrypted** (KMS knows which key version was used)
- New encryptions use the latest key version
- The CMK ARN and alias stay the same — no application changes needed
- For **Imported Key Material**: you must manually rotate (no automatic option)

---

**Q5:** Security Hub shows a finding: "EC2.8 - EC2 instances should use IMDSv2". There are 150 instances. How do you remediate efficiently?

**A:**
```bash
# Option 1: SSM Run Command across all instances
aws ssm send-command \
  --document-name AWS-RunShellScript \
  --parameters '{"commands":["TOKEN=$(curl -X PUT -H \"X-aws-ec2-metadata-token-ttl-seconds: 21600\" http://169.254.169.254/latest/api/token) && echo OK"]}' \
  --targets '[{"Key":"tag:Environment","Values":["production"]}]'

# Option 2: Enforce via API (the real fix)
# Get all instance IDs and enforce IMDSv2
INSTANCES=$(aws ec2 describe-instances \
  --query 'Reservations[*].Instances[*].InstanceId' \
  --output text)

for instance_id in $INSTANCES; do
  aws ec2 modify-instance-metadata-options \
    --instance-id $instance_id \
    --http-tokens required \
    --http-put-response-hop-limit 1
done

# Option 3: Config auto-remediation (best for ongoing compliance)
aws configservice put-remediation-configurations \
  --remediation-configurations '[{
    "ConfigRuleName": "ec2-imdsv2-check",
    "TargetType": "SSM_DOCUMENT",
    "TargetId": "AWS-ModifyInstanceMetadataOptions",
    "Automatic": true
  }]'
```

---

## Key Security Terms for Exam

| Term | Definition |
|------|-----------|
| KMS CMK | Customer Managed Key — you control key policy and rotation |
| Envelope Encryption | Encrypt data key with KMS, use data key to encrypt data |
| Key Rotation | Annual rotation of KMS key material (old ciphertext still works) |
| Secrets Manager | Managed secret storage with automatic rotation |
| Parameter Store | Configuration and secret storage (SecureString = encrypted) |
| ACM | AWS Certificate Manager — free SSL/TLS certs for AWS services |
| WAF | Web Application Firewall — blocks L7 attacks (SQLi, XSS, etc.) |
| Shield Standard | Free basic DDoS protection |
| Shield Advanced | $3K/month — advanced DDoS + cost protection + DRT |
| GuardDuty | ML-based threat detection analyzing VPC/CloudTrail/DNS logs |
| Security Hub | Aggregates findings from all security services |
| Inspector | Automated vulnerability scanning (EC2, ECR, Lambda) |
| Macie | ML-based sensitive data discovery in S3 |
| Access Analyzer | Finds resources exposed to external principals |
| Firewall Manager | Centrally manage WAF/Shield/SGs across Org |
| Security Group | Stateful firewall at instance/ENI level |
| NACL | Stateless firewall at subnet level |
