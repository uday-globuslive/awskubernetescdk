# Chapter 11: Security Services
## KMS, Secrets Manager, WAF, Shield, GuardDuty, Security Hub & More

---

## 11.1 Security Services Overview

```
┌──────────────────────────────────────────────────────────────┐
│                  AWS SECURITY SERVICES                       │
├──────────────────────────┬───────────────────────────────────┤
│ DATA PROTECTION          │ KMS — encryption keys             │
│                          │ Secrets Manager — passwords/certs │
│                          │ Certificate Manager (ACM) — SSL   │
│                          │ Macie — PII in S3 discovery       │
├──────────────────────────┼───────────────────────────────────┤
│ NETWORK PROTECTION       │ WAF — web application firewall    │
│                          │ Shield — DDoS protection          │
│                          │ Firewall Manager — central rules  │
├──────────────────────────┼───────────────────────────────────┤
│ THREAT DETECTION         │ GuardDuty — threat intelligence   │
│                          │ Inspector — vulnerability scanning│
│                          │ Detective — security investigation│
├──────────────────────────┼───────────────────────────────────┤
│ COMPLIANCE & GOVERNANCE  │ Security Hub — central dashboard  │
│                          │ AWS Config — compliance rules     │
│                          │ Audit Manager — audit evidence    │
└──────────────────────────┴───────────────────────────────────┘
```

---

## 11.2 KMS — Key Management Service

KMS manages cryptographic keys for encrypting data.

```
┌──────────────────────────────────────────────────────────┐
│                  HOW KMS WORKS                           │
│                                                          │
│  You don't handle raw keys — KMS does                    │
│                                                          │
│  Your App                 KMS                            │
│  ─────────                ───                            │
│  "Encrypt this data" ──► KMS encrypts using CMK          │
│  "Decrypt this data" ──► KMS decrypts (checks IAM)      │
│                                                          │
│  KMS Master Key (CMK/KMS Key) never leaves KMS           │
│  You only see ciphertext                                 │
│                                                          │
│  Every AWS service (S3, EBS, RDS) can use KMS keys      │
└──────────────────────────────────────────────────────────┘
```

### Key Types

```
AWS Managed Keys:
• Automatically created by services (e.g., aws/s3, aws/rds)
• No cost, no management needed
• You can see but not control them

Customer Managed Keys (CMK):
• You create and control them
• $1/month per key
• Can define key policy (who can use/manage the key)
• Support key rotation, deletion with waiting period
• Use for compliance requirements
```

### KMS CLI

```bash
# Create a symmetric key
KEY_ID=$(aws kms create-key \
  --description "MyApp encryption key" \
  --key-usage ENCRYPT_DECRYPT \
  --query KeyMetadata.KeyId --output text)

# Create an alias for the key
aws kms create-alias \
  --alias-name alias/myapp-key \
  --target-key-id $KEY_ID

# Encrypt data
aws kms encrypt \
  --key-id alias/myapp-key \
  --plaintext "my-secret-value" \
  --query CiphertextBlob --output text | base64 --decode > encrypted.bin

# Decrypt data
aws kms decrypt \
  --ciphertext-blob fileb://encrypted.bin \
  --query Plaintext --output text | base64 --decode

# Enable automatic key rotation (every year)
aws kms enable-key-rotation --key-id $KEY_ID
```

```python
# Python: encrypt/decrypt with KMS
import boto3, base64

kms = boto3.client("kms", region_name="us-east-1")

# Encrypt
response = kms.encrypt(
    KeyId="alias/myapp-key",
    Plaintext=b"my-secret-password"
)
ciphertext = base64.b64encode(response["CiphertextBlob"]).decode()

# Decrypt
response = kms.decrypt(
    CiphertextBlob=base64.b64decode(ciphertext)
)
plaintext = response["Plaintext"].decode()
```

### Key Policy (who can use the key)

```json
{
  "Statement": [
    {
      "Sid": "Allow root full control",
      "Effect": "Allow",
      "Principal": {"AWS": "arn:aws:iam::123456789012:root"},
      "Action": "kms:*",
      "Resource": "*"
    },
    {
      "Sid": "Allow Lambda to use key for encrypt/decrypt",
      "Effect": "Allow",
      "Principal": {"AWS": "arn:aws:iam::123456789012:role/lambda-role"},
      "Action": ["kms:Encrypt", "kms:Decrypt", "kms:GenerateDataKey"],
      "Resource": "*"
    },
    {
      "Sid": "Allow RDS to use key",
      "Effect": "Allow",
      "Principal": {"Service": "rds.amazonaws.com"},
      "Action": ["kms:Encrypt", "kms:Decrypt", "kms:GenerateDataKey*"],
      "Resource": "*"
    }
  ]
}
```

---

## 11.3 Secrets Manager

Secrets Manager stores and auto-rotates database passwords, API keys, and other secrets.

```
Without Secrets Manager:          With Secrets Manager:
Hard-coded in code ❌              Retrieve at runtime ✅
In .env file on server ❌         Auto-rotated ✅
In CI/CD environment vars ❌      Encrypted with KMS ✅
Manually rotated (if ever) ❌     Audit trail in CloudTrail ✅
```

```bash
# Store a secret
aws secretsmanager create-secret \
  --name myapp/prod/db-credentials \
  --description "Production database credentials" \
  --secret-string '{
    "host": "my-db.abc123.us-east-1.rds.amazonaws.com",
    "port": 5432,
    "username": "admin",
    "password": "SecurePass123!"
  }' \
  --kms-key-id alias/myapp-key

# Retrieve secret
aws secretsmanager get-secret-value \
  --secret-id myapp/prod/db-credentials \
  --query SecretString --output text

# Update secret (new password after rotation)
aws secretsmanager update-secret \
  --secret-id myapp/prod/db-credentials \
  --secret-string '{"password": "NewSecurePass456!"}'

# Enable automatic rotation (Lambda function rotates DB password)
aws secretsmanager rotate-secret \
  --secret-id myapp/prod/db-credentials \
  --rotation-lambda-arn arn:aws:lambda:...:function:rotate-db-secret \
  --rotation-rules AutomaticallyAfterDays=30
```

```python
# Retrieve secrets in Python
import boto3, json

def get_secret(secret_name: str) -> dict:
    client = boto3.client("secretsmanager", region_name="us-east-1")
    response = client.get_secret_value(SecretId=secret_name)
    return json.loads(response["SecretString"])

# Use at startup (cache in memory — don't call on every request)
db_creds = get_secret("myapp/prod/db-credentials")
DB_URL = f"postgresql://{db_creds['username']}:{db_creds['password']}@{db_creds['host']}/{db_creds['dbname']}"
```

### Parameter Store vs Secrets Manager

```
┌──────────────────────────────────────────────────────────┐
│      SECRETS MANAGER vs PARAMETER STORE (SSM)           │
├────────────────────────┬─────────────────────────────────┤
│ Secrets Manager        │ Parameter Store                  │
├────────────────────────┼─────────────────────────────────┤
│ Auto rotation          │ No auto rotation                 │
│ $0.40/secret/month     │ Free (standard tier)             │
│ Purpose-built secrets  │ Config + non-sensitive data     │
│ Cross-account access   │ Within account only              │
│ Use for DB passwords,  │ Use for feature flags, URLs,    │
│ API keys, certs        │ config values, non-secrets      │
└────────────────────────┴─────────────────────────────────┘
```

```bash
# Parameter Store
aws ssm put-parameter \
  --name "/myapp/prod/api-url" \
  --value "https://api.example.com" \
  --type String

aws ssm put-parameter \
  --name "/myapp/prod/db-password" \
  --value "SecurePass123!" \
  --type SecureString \
  --key-id alias/myapp-key

aws ssm get-parameter \
  --name "/myapp/prod/db-password" \
  --with-decryption \
  --query Parameter.Value
```

---

## 11.4 WAF — Web Application Firewall

WAF protects web applications from common exploits (SQL injection, XSS, DDoS at Layer 7).

```
Internet → CloudFront / ALB / API Gateway
                │
              WAF Rules:
                │ ✅ Allow legitimate traffic
                │ ❌ Block: SQL injection
                │ ❌ Block: XSS attempts
                │ ❌ Block: Bad bots
                │ ❌ Block: Specific countries
                │ ❌ Rate limit: > 1000 req/5min from one IP
                ▼
           Your Application
```

```bash
# Create WAF WebACL
aws wafv2 create-web-acl \
  --name MyAppWAF \
  --scope CLOUDFRONT \
  --region us-east-1 \
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
      "Name": "RateLimitRule",
      "Priority": 2,
      "Action": {"Block": {}},
      "VisibilityConfig": {
        "SampledRequestsEnabled": true,
        "CloudWatchMetricsEnabled": true,
        "MetricName": "RateLimit"
      },
      "Statement": {
        "RateBasedStatement": {
          "Limit": 1000,
          "AggregateKeyType": "IP"
        }
      }
    }
  ]' \
  --visibility-config SampledRequestsEnabled=true,CloudWatchMetricsEnabled=true,MetricName=MyAppWAF
```

### AWS Managed Rule Groups

```
AWSManagedRulesCommonRuleSet        → General protection (XSS, SQLi, etc.)
AWSManagedRulesAmazonIpReputationList → Known bad IPs
AWSManagedRulesAnonymousIpList      → Tor exits, VPNs, proxies
AWSManagedRulesSQLiRuleSet          → SQL injection specifically
AWSManagedRulesLinuxRuleSet         → Linux-specific attacks
AWSManagedRulesBotControlRuleSet    → Bot traffic filtering
```

---

## 11.5 Shield — DDoS Protection

```
┌──────────────────────────────────────────────────────────┐
│              AWS SHIELD TIERS                            │
├────────────────────────┬─────────────────────────────────┤
│ Shield Standard        │ Free, automatic                  │
│                        │ Layer 3/4 DDoS protection        │
│                        │ Covers EC2, ELB, CloudFront,    │
│                        │ Route53 automatically            │
├────────────────────────┼─────────────────────────────────┤
│ Shield Advanced        │ $3000/month (+ data transfer)   │
│                        │ Layer 7 protection               │
│                        │ 24/7 DDoS Response Team (DRT)   │
│                        │ Financial protection (no bill   │
│                        │ spike from DDoS scaling costs)  │
│                        │ Real-time attack visibility      │
│                        │ For: financial, gaming, media   │
└────────────────────────┴─────────────────────────────────┘
```

---

## 11.6 GuardDuty — Threat Detection

GuardDuty uses ML to detect suspicious activity by analysing CloudTrail, VPC Flow Logs, DNS logs, and more.

```
GuardDuty detects:
• Compromised EC2 instance making DNS calls to known malware domains
• Unusual API calls from unexpected geographic locations
• IAM credentials used from a Tor exit node
• S3 data exfiltration patterns
• EC2 instance scanning ports (possible attacker)
• Root account usage
```

```bash
# Enable GuardDuty (one command — it starts analysing immediately)
aws guardduty create-detector \
  --enable \
  --finding-publishing-frequency FIFTEEN_MINUTES

# List findings
aws guardduty list-findings \
  --detector-id <detector-id>

# Get finding details
aws guardduty get-findings \
  --detector-id <detector-id> \
  --finding-ids <finding-id>

# Archive a finding (acknowledge and dismiss)
aws guardduty archive-findings \
  --detector-id <detector-id> \
  --finding-ids <finding-id>
```

---

## 11.7 Security Hub

Security Hub aggregates security findings from GuardDuty, Inspector, Macie, WAF, Config, and third-party tools into one dashboard with a security score.

```bash
# Enable Security Hub
aws securityhub enable-security-hub \
  --enable-default-standards    # CIS AWS Foundations, FSBP

# Get security score
aws securityhub describe-hub

# List findings (all services, filtered by severity)
aws securityhub get-findings \
  --filters '{
    "SeverityLabel": [{"Value": "CRITICAL", "Comparison": "EQUALS"}],
    "RecordState": [{"Value": "ACTIVE", "Comparison": "EQUALS"}]
  }' \
  --query "Findings[*].[Title,SeverityLabel,ProductName]"
```

---

## 11.8 ACM — Certificate Manager

Free SSL/TLS certificates for your domains, auto-renewed.

```bash
# Request a certificate
aws acm request-certificate \
  --domain-name "*.myapp.com" \
  --validation-method DNS \
  --subject-alternative-names "myapp.com" \
  --region us-east-1   # Must be us-east-1 for CloudFront

# After DNS validation, attach to ALB via console or:
aws elbv2 add-listener-certificates \
  --listener-arn arn:aws:elasticloadbalancing:...:listener/... \
  --certificates CertificateArn=arn:aws:acm:...:certificate/...
```

---

## 11.9 Security Best Practices Summary

```
┌────────────────────────────────────────────────────────────┐
│              AWS SECURITY CHECKLIST                        │
├────────────────────────────────────────────────────────────┤
│ Identity                                                   │
│ ✅ Root account MFA enabled, access keys deleted           │
│ ✅ All IAM users have MFA                                  │
│ ✅ Use roles, not access keys for applications             │
│ ✅ Least privilege IAM policies                           │
│ ✅ Regular access key rotation or use OIDC               │
├────────────────────────────────────────────────────────────┤
│ Data                                                       │
│ ✅ S3 Block Public Access enabled on all buckets          │
│ ✅ S3 encryption at rest (SSE-KMS or SSE-S3)             │
│ ✅ RDS encrypted at rest, SSL in transit                 │
│ ✅ Secrets in Secrets Manager, not code or env vars      │
│ ✅ EBS volumes encrypted                                 │
├────────────────────────────────────────────────────────────┤
│ Network                                                    │
│ ✅ Resources in private subnets, not public               │
│ ✅ Security groups: least privilege (no 0.0.0.0/0 on DB) │
│ ✅ WAF on public-facing APIs / CloudFront distributions   │
│ ✅ VPC Flow Logs enabled                                 │
├────────────────────────────────────────────────────────────┤
│ Detection                                                  │
│ ✅ GuardDuty enabled in all regions                      │
│ ✅ CloudTrail enabled (multi-region)                     │
│ ✅ Security Hub enabled with standards                   │
│ ✅ Config rules for compliance monitoring                 │
│ ✅ CloudWatch alarms on security metrics                  │
└────────────────────────────────────────────────────────────┘
```

---

## 11.10 Interview Questions

**Q: How do you securely store database passwords in AWS?**
> Use AWS Secrets Manager. Store the DB credentials as a JSON secret encrypted with a KMS key. Grant only the Lambda/EC2 role `secretsmanager:GetSecretValue` permission on that specific secret ARN. Retrieve the secret at application startup (not on every request) and cache it. Enable automatic rotation so Secrets Manager periodically changes the password without any manual work. Never hard-code passwords or store them in environment variables.

**Q: What is the difference between WAF and Shield?**
> WAF (Web Application Firewall) operates at Layer 7 (HTTP) — it inspects request content and can block SQL injection, XSS, bad bots, and rate-limit specific IPs. Shield operates at Layer 3/4 (network) and protects against volumetric DDoS attacks (SYN floods, UDP amplification). They're complementary: Shield stops the traffic flood, WAF filters what gets through. Shield Standard is free and automatic; WAF requires configuration.

**Q: How does GuardDuty work without agents?**
> GuardDuty analyses existing AWS data sources — CloudTrail API logs, VPC Flow Logs, DNS query logs, and S3 access logs. It doesn't need agents on your instances. It uses ML models and threat intelligence feeds (known malicious IPs, domains) to identify anomalies. A single API call enables it region-wide. It's entirely passive — it only reads logs, never touches your resources.
