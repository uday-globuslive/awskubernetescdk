# Chapter 11: Security Services — KMS, Secrets Manager, WAF, GuardDuty & More
## Encryption, Secrets Management, Threat Detection, and Security Posture

---

## 11.1 AWS Security Services Overview

```
┌────────────────────────────────────────────────────────────────────┐
│                  AWS SECURITY SERVICES                             │
├─────────────────────┬──────────────────────────────────────────────┤
│ KMS                 │ Key management, encryption at rest           │
│ ACM                 │ SSL/TLS certificate provisioning             │
│ Secrets Manager     │ Secrets rotation and storage                 │
│ SSM Parameter Store │ Configuration and secrets storage            │
├─────────────────────┼──────────────────────────────────────────────┤
│ IAM (Ch2)          │ Identity and access management               │
│ Organizations       │ Multi-account governance, SCPs               │
│ Control Tower       │ Multi-account setup automation               │
│ Macie               │ S3 sensitive data discovery (PII)            │
├─────────────────────┼──────────────────────────────────────────────┤
│ WAF                 │ Web application firewall (L7)                │
│ Shield Standard     │ DDoS protection (automatic, free)           │
│ Shield Advanced     │ Enhanced DDoS + 24/7 DRT team ($3000/mo)    │
│ Firewall Manager    │ Centralize WAF/SG/NACL management           │
├─────────────────────┼──────────────────────────────────────────────┤
│ GuardDuty           │ Threat detection, anomaly ML                 │
│ Security Hub        │ Security findings aggregation, standards     │
│ Inspector           │ Vulnerability assessment (EC2, Lambda, ECR) │
│ Detective           │ Threat investigation and visualization       │
│ CloudTrail (Ch10)  │ API audit logging                            │
│ Config (Ch10)      │ Resource compliance and change history       │
└─────────────────────┴──────────────────────────────────────────────┘
```

---

## 11.2 KMS — Key Management Service

### Key Types

```
KMS Key Types:
  Customer Managed Keys (CMK):  You create and manage, $1/month/key
  AWS Managed Keys:             AWS creates/manages per service (e.g., aws/s3), free
  AWS Owned Keys:               AWS-owned, used by some services, not visible to you

Key Material Origin:
  AWS_KMS:    KMS generates key material (default)
  EXTERNAL:   You import your own key material
  AWS_CLOUDHSM: Key material in CloudHSM cluster

Key Spec:
  SYMMETRIC_DEFAULT: AES-256-GCM (most use cases)
  RSA_2048/4096:     Asymmetric, sign/verify or encrypt/decrypt
  ECC_NIST_P256/384/521: ECDSA for signing
  HMAC_256/384/512:  Generate/verify HMAC tokens
```

### Key Management

```bash
# Create symmetric CMK
KEY_ID=$(aws kms create-key \
  --description "Production database encryption key" \
  --key-usage ENCRYPT_DECRYPT \
  --origin AWS_KMS \
  --enable-key-rotation \     # Auto-rotate annually
  --tags TagKey=Environment,TagValue=prod TagKey=Service,TagValue=database \
  --query "KeyMetadata.KeyId" --output text)

# Create key alias (human-readable name)
aws kms create-alias \
  --alias-name alias/prod-db-key \
  --target-key-id $KEY_ID

# Create key policy (grant permissions)
aws kms put-key-policy \
  --key-id $KEY_ID \
  --policy-name default \
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
        "Sid": "Allow key administration",
        "Effect": "Allow",
        "Principal": {"AWS": "arn:aws:iam::123456789012:role/KeyAdmins"},
        "Action": ["kms:Create*","kms:Describe*","kms:Enable*","kms:List*",
                   "kms:Put*","kms:Update*","kms:Revoke*","kms:Disable*",
                   "kms:Get*","kms:Delete*","kms:ScheduleKeyDeletion","kms:CancelKeyDeletion"],
        "Resource": "*"
      },
      {
        "Sid": "Allow key usage by application role",
        "Effect": "Allow",
        "Principal": {"AWS": "arn:aws:iam::123456789012:role/AppRole"},
        "Action": ["kms:Encrypt","kms:Decrypt","kms:ReEncrypt*","kms:GenerateDataKey*","kms:DescribeKey"],
        "Resource": "*",
        "Condition": {
          "StringEquals": {
            "kms:ViaService": ["rds.us-east-1.amazonaws.com", "secretsmanager.us-east-1.amazonaws.com"]
          }
        }
      }
    ]
  }'

# Encrypt data directly
aws kms encrypt \
  --key-id alias/prod-db-key \
  --plaintext "my-secret-data" \
  --encryption-context Purpose=PasswordEncryption,Service=my-app \
  --query "CiphertextBlob" --output text | base64 -d > encrypted.bin

# Decrypt
aws kms decrypt \
  --ciphertext-blob fileb://encrypted.bin \
  --encryption-context Purpose=PasswordEncryption,Service=my-app \
  --query "Plaintext" --output text | base64 -d

# Generate data key (for client-side encryption — envelope encryption)
aws kms generate-data-key \
  --key-id alias/prod-db-key \
  --key-spec AES_256 \
  --encryption-context Service=my-app
# Returns: Plaintext key (use to encrypt data, then discard)
#          CiphertextBlob (store alongside encrypted data)
```

### Envelope Encryption Pattern

```python
import boto3
import os
import json
import base64
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

kms = boto3.client('kms')
KEY_ARN = 'arn:aws:kms:us-east-1:123:key/abc-123'

def encrypt_data(plaintext: bytes, context: dict) -> dict:
    """Envelope encryption: KMS generates data key, we encrypt locally."""
    
    # Get data key from KMS
    response = kms.generate_data_key(
        KeyId=KEY_ARN,
        KeySpec='AES_256',
        EncryptionContext=context
    )
    
    plaintext_key = response['Plaintext']
    encrypted_key = response['CiphertextBlob']
    
    # Use plaintext key to encrypt data locally (faster, cheaper)
    nonce = os.urandom(12)
    aesgcm = AESGCM(plaintext_key)
    ciphertext = aesgcm.encrypt(nonce, plaintext, json.dumps(context).encode())
    
    # Discard plaintext key immediately
    del plaintext_key
    
    return {
        'encrypted_key': base64.b64encode(encrypted_key).decode(),
        'nonce': base64.b64encode(nonce).decode(),
        'ciphertext': base64.b64encode(ciphertext).decode(),
        'context': context
    }

def decrypt_data(encrypted_package: dict) -> bytes:
    """Decrypt envelope-encrypted data."""
    
    context = encrypted_package['context']
    encrypted_key = base64.b64decode(encrypted_package['encrypted_key'])
    nonce = base64.b64decode(encrypted_package['nonce'])
    ciphertext = base64.b64decode(encrypted_package['ciphertext'])
    
    # Decrypt data key with KMS
    response = kms.decrypt(
        CiphertextBlob=encrypted_key,
        EncryptionContext=context
    )
    plaintext_key = response['Plaintext']
    
    # Decrypt data locally
    aesgcm = AESGCM(plaintext_key)
    return aesgcm.decrypt(nonce, ciphertext, json.dumps(context).encode())
```

---

## 11.3 AWS Secrets Manager

Secrets Manager stores, rotates, and retrieves secrets automatically.

```bash
# Create secret (password)
aws secretsmanager create-secret \
  --name prod/database/password \
  --description "Production RDS PostgreSQL password" \
  --secret-string '{"username":"dbadmin","password":"MySecurePass123!"}' \
  --kms-key-id alias/prod-secrets-key \
  --tags Key=Environment,Value=prod Key=Service,Value=database

# Create secret (API key)
aws secretsmanager create-secret \
  --name prod/stripe/api-key \
  --secret-string "sk_live_abc123xyz"

# Get secret value
aws secretsmanager get-secret-value \
  --secret-id prod/database/password \
  --query "SecretString" --output text | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['password'])"

# Rotate secret immediately
aws secretsmanager rotate-secret \
  --secret-id prod/database/password \
  --rotation-lambda-arn arn:aws:lambda:us-east-1:123:function:rotate-db-password \
  --rotation-rules AutomaticallyAfterDays=30

# Enable automatic rotation
aws secretsmanager rotate-secret \
  --secret-id prod/database/password \
  --rotation-lambda-arn arn:aws:lambda:us-east-1:123:function:rotate-db-password \
  --rotation-rules ScheduleExpression="rate(30 days)"
```

### Python Secrets Manager Integration

```python
import boto3
import json
from functools import lru_cache
from botocore.exceptions import ClientError

secretsmanager = boto3.client('secretsmanager')

@lru_cache(maxsize=None)
def get_secret(secret_name: str) -> dict:
    """Get secret with caching (cache in Lambda execution environment)."""
    try:
        response = secretsmanager.get_secret_value(SecretId=secret_name)
        
        if 'SecretString' in response:
            return json.loads(response['SecretString'])
        else:
            # Binary secret
            return response['SecretBinary']
    
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'ResourceNotFoundException':
            raise KeyError(f"Secret {secret_name} not found")
        elif error_code == 'AccessDeniedException':
            raise PermissionError(f"No access to secret {secret_name}")
        raise

# Usage in Lambda (fast — cached after first invocation)
def get_db_connection():
    secret = get_secret('prod/database/password')
    import psycopg2
    return psycopg2.connect(
        host=os.environ['DB_HOST'],
        database='appdb',
        user=secret['username'],
        password=secret['password'],
        sslmode='require'
    )

# Auto-rotation Lambda (AWS provides templates)
def rotate_secret(event, context):
    """Lambda for custom secret rotation."""
    secret_id = event['SecretId']
    token = event['ClientRequestToken']
    step = event['Step']
    
    if step == 'createSecret':
        # Create new version of secret
        new_password = generate_secure_password()
        secretsmanager.put_secret_value(
            SecretId=secret_id,
            ClientRequestToken=token,
            SecretString=json.dumps({'username': 'dbadmin', 'password': new_password}),
            VersionStages=['AWSPENDING']
        )
    
    elif step == 'setSecret':
        # Apply new password to the database
        pending = secretsmanager.get_secret_value(
            SecretId=secret_id, VersionStage='AWSPENDING'
        )
        new_creds = json.loads(pending['SecretString'])
        update_database_password(new_creds['password'])
    
    elif step == 'testSecret':
        # Test that new credentials work
        test_login_with_new_creds(secret_id, token)
    
    elif step == 'finishSecret':
        # Mark new version as current
        metadata = secretsmanager.describe_secret(SecretId=secret_id)
        current_version = next(v for v, s in metadata['VersionIdsToStages'].items()
                               if 'AWSCURRENT' in s)
        secretsmanager.update_secret_version_stage(
            SecretId=secret_id,
            VersionStage='AWSCURRENT',
            MoveToVersionId=token,
            RemoveFromVersionId=current_version
        )
```

### Secrets Manager vs SSM Parameter Store

```
┌──────────────────────────────────────────────────────────────────┐
│           SECRETS MANAGER vs SSM PARAMETER STORE                 │
├─────────────────────┬──────────────────────┬─────────────────────┤
│ Feature             │ Secrets Manager      │ Parameter Store     │
├─────────────────────┼──────────────────────┼─────────────────────┤
│ Cost                │ $0.40/secret/month   │ Free (Standard)     │
│                     │ + $0.05/10K API calls│ $0.05/Advanced      │
├─────────────────────┼──────────────────────┼─────────────────────┤
│ Auto-rotation       │ Yes (Lambda-based)   │ No                  │
├─────────────────────┼──────────────────────┼─────────────────────┤
│ Cross-account       │ Yes                  │ No                  │
├─────────────────────┼──────────────────────┼─────────────────────┤
│ Max value size      │ 65,536 bytes         │ 4KB (Standard)      │
│                     │                      │ 8KB (Advanced)      │
├─────────────────────┼──────────────────────┼─────────────────────┤
│ Versioning          │ Yes (staging labels) │ Yes                 │
├─────────────────────┼──────────────────────┼─────────────────────┤
│ Encryption          │ KMS (required)       │ KMS (optional)      │
├─────────────────────┼──────────────────────┼─────────────────────┤
│ Best for            │ Credentials that     │ Config, non-secret  │
│                     │ need rotation        │ parameters, flags   │
└─────────────────────┴──────────────────────┴─────────────────────┘
```

```bash
# SSM Parameter Store
# Standard string (free)
aws ssm put-parameter \
  --name /prod/app/config \
  --value '{"debug": false, "max_connections": 100}' \
  --type String \
  --tags Key=Environment,Value=prod

# Secure string (encrypted with KMS, $0.05/advanced param)
aws ssm put-parameter \
  --name /prod/api/key \
  --value "my-api-key-value" \
  --type SecureString \
  --key-id alias/prod-ssm-key \
  --tier Advanced     # For > 4KB or parameter policies

# Get parameter
aws ssm get-parameter \
  --name /prod/api/key \
  --with-decryption \
  --query "Parameter.Value" --output text

# Get multiple parameters
aws ssm get-parameters-by-path \
  --path /prod/app/ \
  --with-decryption \
  --recursive
```

---

## 11.4 WAF — Web Application Firewall

WAF protects web applications from common exploits (SQLi, XSS, etc.) and blocks malicious IPs.

```bash
# Create WebACL
WEB_ACL_ID=$(aws wafv2 create-web-acl \
  --name prod-web-acl \
  --scope REGIONAL \             # CLOUDFRONT for CloudFront, REGIONAL for ALB/API GW
  --default-action Allow={} \
  --visibility-config SampledRequestsEnabled=true,CloudWatchMetricsEnabled=true,MetricName=prod-web-acl \
  --rules '[
    {
      "Name": "AWSManagedRulesCommonRuleSet",
      "Priority": 10,
      "Statement": {
        "ManagedRuleGroupStatement": {
          "VendorName": "AWS",
          "Name": "AWSManagedRulesCommonRuleSet"
        }
      },
      "OverrideAction": {"None": {}},
      "VisibilityConfig": {
        "SampledRequestsEnabled": true,
        "CloudWatchMetricsEnabled": true,
        "MetricName": "CommonRuleSet"
      }
    },
    {
      "Name": "AWSManagedRulesKnownBadInputsRuleSet",
      "Priority": 20,
      "Statement": {
        "ManagedRuleGroupStatement": {
          "VendorName": "AWS",
          "Name": "AWSManagedRulesKnownBadInputsRuleSet"
        }
      },
      "OverrideAction": {"None": {}},
      "VisibilityConfig": {
        "SampledRequestsEnabled": true,
        "CloudWatchMetricsEnabled": true,
        "MetricName": "KnownBadInputs"
      }
    },
    {
      "Name": "RateLimitRule",
      "Priority": 30,
      "Statement": {
        "RateBasedStatement": {
          "Limit": 1000,
          "AggregateKeyType": "IP",
          "ScopeDownStatement": {
            "ByteMatchStatement": {
              "SearchString": "/api/",
              "FieldToMatch": {"UriPath": {}},
              "TextTransformations": [{"Priority": 0, "Type": "NONE"}],
              "PositionalConstraint": "STARTS_WITH"
            }
          }
        }
      },
      "Action": {"Block": {}},
      "VisibilityConfig": {
        "SampledRequestsEnabled": true,
        "CloudWatchMetricsEnabled": true,
        "MetricName": "RateLimit"
      }
    },
    {
      "Name": "GeoBlockRule",
      "Priority": 40,
      "Statement": {
        "GeoMatchStatement": {
          "CountryCodes": ["KP", "IR", "CU", "SD"]
        }
      },
      "Action": {"Block": {}},
      "VisibilityConfig": {
        "SampledRequestsEnabled": true,
        "CloudWatchMetricsEnabled": true,
        "MetricName": "GeoBlock"
      }
    }
  ]' \
  --region us-east-1 \
  --query "Summary.Id" --output text)

# Associate WebACL with ALB
aws wafv2 associate-web-acl \
  --web-acl-arn arn:aws:wafv2:us-east-1:123:regional/webacl/prod-web-acl/$WEB_ACL_ID \
  --resource-arn arn:aws:elasticloadbalancing:us-east-1:123:loadbalancer/app/my-alb/abc

# Create IP set (allow/block specific IPs)
aws wafv2 create-ip-set \
  --name blocked-ips \
  --scope REGIONAL \
  --ip-address-version IPV4 \
  --addresses "203.0.113.0/24" "198.51.100.5/32"

# Add IP set rule to WebACL (block all IPs in set)
aws wafv2 update-web-acl \
  --id $WEB_ACL_ID \
  --name prod-web-acl \
  --scope REGIONAL \
  --default-action Allow={} \
  --lock-token $(aws wafv2 get-web-acl --id $WEB_ACL_ID --name prod-web-acl --scope REGIONAL --query "LockToken" --output text) \
  --rules '[{
    "Name": "BlockIPSet",
    "Priority": 5,
    "Statement": {
      "IPSetReferenceStatement": {
        "ARN": "arn:aws:wafv2:us-east-1:123:regional/ipset/blocked-ips/xyz"
      }
    },
    "Action": {"Block": {}},
    "VisibilityConfig": {
      "SampledRequestsEnabled": true,
      "CloudWatchMetricsEnabled": true,
      "MetricName": "BlockIPSet"
    }
  }]'
```

---

## 11.5 GuardDuty — Threat Detection

GuardDuty continuously analyzes CloudTrail, VPC Flow Logs, DNS logs, and more for threats.

```bash
# Enable GuardDuty
aws guardduty create-detector \
  --enable \
  --finding-publishing-frequency FIFTEEN_MINUTES \
  --data-sources '{
    "S3Logs": {"Enable": true},
    "Kubernetes": {"AuditLogs": {"Enable": true}},
    "MalwareProtection": {"ScanEc2InstanceWithFindings": {"EbsVolumes": {"Enable": true}}}
  }'

DETECTOR_ID=$(aws guardduty list-detectors --query "DetectorIds[0]" --output text)

# List findings
aws guardduty list-findings \
  --detector-id $DETECTOR_ID \
  --finding-criteria '{
    "Criterion": {
      "severity": {"Gte": 7}   # HIGH or CRITICAL severity
    }
  }'

# Get finding details
aws guardduty get-findings \
  --detector-id $DETECTOR_ID \
  --finding-ids finding-id-here

# Create suppression rule (reduce noise)
aws guardduty create-filter \
  --detector-id $DETECTOR_ID \
  --name suppress-scanner-activity \
  --action ARCHIVE \
  --finding-criteria '{
    "Criterion": {
      "type": {"Equals": ["Recon:EC2/PortProbeUnprotectedPort"]},
      "resource.instanceDetails.tags.value": {"Equals": ["scanner-ec2"]}
    }
  }'

# Enable threat intelligence feed
aws guardduty create-threat-intel-set \
  --detector-id $DETECTOR_ID \
  --name known-attackers \
  --format TXT \
  --location s3://my-threat-intel/bad-ips.txt \
  --activate
```

### GuardDuty Finding Types

```
High Severity (7-8.9):
  UnauthorizedAccess:IAMUser/ConsoleLoginSuccess.B   — console login from unusual IP
  Trojan:EC2/BlackholeTraffic                        — EC2 communicating with blackhole IP
  CryptoCurrency:EC2/BitcoinTool.B                   — cryptocurrency mining detected
  Backdoor:EC2/C&CActivity.B!DNS                     — DNS query to known C&C server

Medium Severity (4-6.9):
  UnauthorizedAccess:IAMUser/UnusualASNCaller          — unusual ASN accessing AWS API
  Recon:EC2/PortProbeUnprotectedPort                  — port scan on instance
  
Low Severity (1-3.9):
  Stealth:IAMUser/PasswordPolicyChange                — password policy weakened
```

---

## 11.6 Security Hub

Security Hub aggregates security findings from GuardDuty, Inspector, Macie, Config, and third-party tools.

```bash
# Enable Security Hub
aws securityhub enable-security-hub \
  --enable-default-standards   # Enables AWS Foundational Security Best Practices

# Enable additional standards
aws securityhub batch-enable-standards \
  --standards-subscription-requests '[
    {"StandardsArn": "arn:aws:securityhub:::ruleset/cis-aws-foundations-benchmark/v/1.2.0"},
    {"StandardsArn": "arn:aws:securityhub:us-east-1::standards/aws-foundational-security-best-practices/v/1.0.0"},
    {"StandardsArn": "arn:aws:securityhub:us-east-1::standards/pci-dss/v/3.2.1"}
  ]'

# Get findings
aws securityhub get-findings \
  --filters '{
    "SeverityLabel": [{"Value": "CRITICAL", "Comparison": "EQUALS"}],
    "RecordState": [{"Value": "ACTIVE", "Comparison": "EQUALS"}],
    "WorkflowStatus": [{"Value": "NEW", "Comparison": "EQUALS"}]
  }' \
  --sort-criteria '[{"Field": "CreatedAt", "SortOrder": "desc"}]'

# Create custom insight (saved query)
aws securityhub create-insight \
  --name "Critical Findings by Account" \
  --filters '{
    "SeverityLabel": [{"Value": "CRITICAL", "Comparison": "EQUALS"}]
  }' \
  --group-by-attribute "AwsAccountId"
```

---

## 11.7 ACM — AWS Certificate Manager

```bash
# Request public certificate (DNS validation)
CERT_ARN=$(aws acm request-certificate \
  --domain-name example.com \
  --subject-alternative-names "*.example.com" "api.example.com" \
  --validation-method DNS \
  --query "CertificateArn" --output text)

# Get CNAME records for DNS validation
aws acm describe-certificate \
  --certificate-arn $CERT_ARN \
  --query "Certificate.DomainValidationOptions[*].{Domain:DomainName,Name:ResourceRecord.Name,Value:ResourceRecord.Value,Type:ResourceRecord.Type}" \
  --output table

# Add CNAME to Route53 for automatic validation
ZONE_ID=$(aws route53 list-hosted-zones --query "HostedZones[?Name=='example.com.'].Id" --output text | cut -d'/' -f3)

aws acm describe-certificate --certificate-arn $CERT_ARN \
  --query "Certificate.DomainValidationOptions[0].ResourceRecord" | \
  python3 -c "
import json, sys, subprocess
record = json.load(sys.stdin)
change = {
  'Changes': [{
    'Action': 'UPSERT',
    'ResourceRecordSet': {
      'Name': record['Name'],
      'Type': record['Type'],
      'TTL': 300,
      'ResourceRecords': [{'Value': record['Value']}]
    }
  }]
}
print(json.dumps(change))
" | xargs -I{} aws route53 change-resource-record-sets --hosted-zone-id $ZONE_ID --change-batch '{}'

# Import private/self-signed certificate
aws acm import-certificate \
  --certificate fileb://certificate.pem \
  --private-key fileb://private-key.pem \
  --certificate-chain fileb://chain.pem
```

---

## 11.8 Amazon Macie

Macie uses ML to discover and protect sensitive data (PII, credentials) in S3.

```bash
# Enable Macie
aws macie2 enable-macie \
  --finding-publishing-frequency FIFTEEN_MINUTES \
  --status ENABLED

# Create classification job (scan S3 bucket)
aws macie2 create-classification-job \
  --name scan-prod-data-lake \
  --job-type SCHEDULED \
  --schedule-frequency DailySchedule={} \
  --s3-job-definition '{
    "bucketDefinitions": [
      {
        "accountId": "123456789012",
        "buckets": ["prod-data-lake", "user-uploads"]
      }
    ],
    "scoping": {
      "includes": {
        "and": [{
          "simpleScopeTerm": {
            "comparator": "GT",
            "key": "OBJECT_SIZE",
            "values": ["1"]
          }
        }]
      }
    }
  }' \
  --managed-data-identifier-selector ALL \
  --sampling-percentage 100

# List findings
aws macie2 list-findings \
  --finding-criteria '{
    "criterion": {
      "severity.description": {
        "eq": ["High", "Critical"]
      }
    }
  }'
```

---

## 11.9 Inspector — Vulnerability Assessment

```bash
# Enable Inspector
aws inspector2 enable \
  --resource-types EC2 LAMBDA ECR

# Get findings
aws inspector2 list-findings \
  --filter-criteria '{
    "findingStatus": [{"comparison": "EQUALS", "value": "ACTIVE"}],
    "severity": [{"comparison": "EQUALS", "value": "CRITICAL"}]
  }' \
  --sort-criteria field=SEVERITY,sortOrder=DESC

# Suppress finding (known false positive)
aws inspector2 create-filter \
  --action SUPPRESS \
  --name suppress-known-false-positive \
  --filter-criteria '{
    "cveId": [{"comparison": "EQUALS", "value": "CVE-2021-12345"}],
    "ec2InstanceTags": [{"comparison": "EQUALS", "key": "exempt-from-scan", "value": "true"}]
  }'
```

---

## 11.10 Interview Q&A

**Q: What is KMS encryption context and why use it?**
A: Encryption context is optional name-value pairs that are cryptographically bound to encrypted data. If you provide context during encryption, you MUST provide the exact same context during decryption. Benefits: adds authorization check (can't decrypt without context), makes the encryption non-portable (encrypted with "service=orders" context can only be decrypted with that context), creates audit log correlation. Example: encrypt a database field with context `{"user_id": "123"}` to prevent that ciphertext from being used for a different user's record.

**Q: What is the difference between Secrets Manager and SSM Parameter Store?**
A: Secrets Manager: $0.40/secret/month, supports automatic rotation (Lambda-based), cross-account sharing, 64KB values. Best for credentials needing auto-rotation. SSM Parameter Store: free (Standard tier), up to 4KB (8KB Advanced), no auto-rotation, simpler API. Best for configuration values, feature flags, non-rotating secrets. Use Secrets Manager for database passwords and API keys; use SSM for app configuration.

**Q: What is envelope encryption and why does AWS use it?**
A: Envelope encryption uses two keys: a data key (generated per dataset) and a master key (KMS). The data key encrypts actual data locally; KMS only encrypts/decrypts the data key. Benefits: (1) encrypt large amounts of data faster (symmetric local encryption vs KMS API calls); (2) each dataset gets unique key; (3) can re-encrypt by just re-encrypting the data key without touching the data. AWS S3, RDS, EBS all use envelope encryption.

**Q: What types of threats does GuardDuty detect?**
A: GuardDuty analyzes CloudTrail management/data events, VPC Flow Logs, DNS logs, EKS audit logs, and S3 access logs. It detects: account compromise (credential theft, unusual API calls), EC2 compromise (malware, crypto mining, C&C communication), S3 threats (unusual access patterns, data exfiltration), Kubernetes threats (privilege escalation, exposed dashboards), and malware in EBS volumes. All detection uses threat intelligence feeds and ML baselines.

**Q: What AWS managed WAF rules should you always enable?**
A: At minimum: (1) AWSManagedRulesCommonRuleSet — OWASP Top 10 (SQLi, XSS, RFI, LFI); (2) AWSManagedRulesKnownBadInputsRuleSet — known attack patterns; (3) AWSManagedRulesBotControlRuleSet — bot management; (4) Rate-based rules — DDoS mitigation. For specific stacks: AWSManagedRulesWordPressRuleSet for WordPress, AWSManagedRulesSQLiRuleSet for databases. Start in Count mode before switching to Block to avoid false positives.

**Q: What is the difference between Shield Standard and Shield Advanced?**
A: Shield Standard is automatic, free, provides protection against common L3/L4 DDoS attacks for all AWS resources. Shield Advanced ($3,000/month + data transfer fees) adds: L7 application-layer protection with WAF integration, 24/7 access to AWS DDoS Response Team (DRT), near-real-time attack visibility, cost protection (credits for scaling costs during attack), and protection for resources by IP address.

**Q: How does ACM integrate with other services?**
A: ACM certificates are natively integrated with: ALB/NLB (attach in listener configuration), CloudFront (requires us-east-1 region), API Gateway, Elastic Beanstalk, and ECS (via ALB). ACM handles automatic renewal of certificates before expiration. Public certificates are free; private certificates have an ACM Private CA fee. ACM certificates cannot be downloaded/exported (except through ACM Private CA for internal CAs).
