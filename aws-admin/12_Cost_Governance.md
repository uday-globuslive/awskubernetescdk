# Chapter 12: Cost Management & Governance
## Cost Explorer, Budgets, Organizations, Control Tower & Trusted Advisor

---

## 12.1 Cost Management Overview

```
┌──────────────────────────────────────────────────────────────┐
│              AWS COST MANAGEMENT TOOLKIT                     │
├──────────────────────────┬───────────────────────────────────┤
│ VISIBILITY               │ Cost Explorer — analyse spending  │
│                          │ Cost & Usage Report — raw data    │
│                          │ Billing Console — current month   │
├──────────────────────────┼───────────────────────────────────┤
│ ALERTS & CONTROL         │ Budgets — spending thresholds     │
│                          │ Savings Plans — commit & save     │
│                          │ Reserved Instances — EC2/RDS save │
├──────────────────────────┼───────────────────────────────────┤
│ GOVERNANCE               │ Organizations — multi-account     │
│                          │ Control Tower — landing zone      │
│                          │ Service Control Policies (SCPs)   │
├──────────────────────────┼───────────────────────────────────┤
│ RECOMMENDATIONS          │ Trusted Advisor — best practices  │
│                          │ Compute Optimizer — right-sizing  │
└──────────────────────────┴───────────────────────────────────┘
```

---

## 12.2 Cost Explorer

Cost Explorer provides a visual interface to analyse historical AWS spending.

```bash
# Get costs last 7 days, grouped by service
aws ce get-cost-and-usage \
  --time-period Start=2024-01-01,End=2024-01-08 \
  --granularity DAILY \
  --metrics BlendedCost UnblendedCost UsageQuantity \
  --group-by Type=DIMENSION,Key=SERVICE \
  --query "ResultsByTime[*].Groups[*].[Keys[0],Metrics.BlendedCost.Amount]"

# Get cost forecast for next 30 days
aws ce get-cost-forecast \
  --time-period Start=$(date +%Y-%m-%d),End=$(date -d '+30 days' +%Y-%m-%d) \
  --metric BLENDED_COST \
  --granularity MONTHLY

# Filter by tag (requires cost allocation tags enabled)
aws ce get-cost-and-usage \
  --time-period Start=2024-01-01,End=2024-02-01 \
  --granularity MONTHLY \
  --metrics BlendedCost \
  --filter '{
    "Tags": {
      "Key": "Environment",
      "Values": ["prod"],
      "MatchOptions": ["EQUALS"]
    }
  }'

# Identify top 5 cost-driving resources
aws ce get-cost-and-usage \
  --time-period Start=2024-01-01,End=2024-02-01 \
  --granularity MONTHLY \
  --metrics BlendedCost \
  --group-by Type=DIMENSION,Key=SERVICE \
  --query "sort_by(ResultsByTime[0].Groups, &Metrics.BlendedCost.Amount)[-5:]"
```

---

## 12.3 AWS Budgets

Budgets set spending thresholds and send alerts (or trigger auto-actions) when costs approach limits.

```bash
# Create monthly cost budget with 80% and 100% alerts
aws budgets create-budget \
  --account-id 123456789012 \
  --budget '{
    "BudgetName": "monthly-prod-budget",
    "BudgetLimit": {"Amount": "1000", "Unit": "USD"},
    "TimeUnit": "MONTHLY",
    "BudgetType": "COST",
    "CostFilters": {
      "TagKeyValue": ["user:Environment$prod"]
    }
  }' \
  --notifications-with-subscribers '[
    {
      "Notification": {
        "NotificationType": "ACTUAL",
        "ComparisonOperator": "GREATER_THAN",
        "Threshold": 80,
        "ThresholdType": "PERCENTAGE"
      },
      "Subscribers": [
        {"SubscriptionType": "EMAIL", "Address": "admin@myapp.com"},
        {"SubscriptionType": "SNS", "Address": "arn:aws:sns:...:ops-alerts"}
      ]
    },
    {
      "Notification": {
        "NotificationType": "FORECASTED",
        "ComparisonOperator": "GREATER_THAN",
        "Threshold": 100,
        "ThresholdType": "PERCENTAGE"
      },
      "Subscribers": [
        {"SubscriptionType": "EMAIL", "Address": "admin@myapp.com"}
      ]
    }
  ]'
```

---

## 12.4 Savings Plans & Reserved Instances

```
┌──────────────────────────────────────────────────────────────┐
│              COMMITMENT DISCOUNTS                            │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  On-Demand: pay per second, no commitment                   │
│  Savings Plans / Reserved Instances: commit 1-3 years       │
│  → Save 30-72% depending on commitment type                 │
│                                                              │
├───────────────────────┬──────────────────────────────────────┤
│ Savings Plans         │ Reserved Instances                   │
├───────────────────────┼──────────────────────────────────────┤
│ Flexible — applies to │ Specific — tied to instance type,  │
│ any instance family   │ region, OS, tenancy                 │
│ in chosen region      │                                      │
│                       │                                      │
│ Compute SP:           │ Standard RI: max savings,           │
│ Any instance + Lambda │ can't change instance type          │
│ + Fargate             │                                      │
│                       │ Convertible RI: can exchange,       │
│ EC2 Instance SP:      │ slightly less savings               │
│ Specific family in    │                                      │
│ region                │ EC2, RDS, ElastiCache, Redshift     │
│                       │ OpenSearch, DynamoDB                 │
└───────────────────────┴──────────────────────────────────────┘
```

```bash
# Purchase a 1-year Compute Savings Plan (no upfront)
aws savingsplans create-savings-plan \
  --savings-plan-offering-id <offering-id> \
  --commitment 10.0 \
  --payment-option NO_UPFRONT

# View Savings Plan recommendations
aws ce get-savings-plans-purchase-recommendation \
  --savings-plans-type COMPUTE_SP \
  --term-in-years ONE_YEAR \
  --payment-option NO_UPFRONT \
  --lookback-period-in-days THIRTY_DAYS
```

---

## 12.5 AWS Organizations

Organizations lets you manage multiple AWS accounts under one umbrella with consolidated billing and governance.

```
┌──────────────────────────────────────────────────────────┐
│                ORGANIZATIONS HIERARCHY                   │
│                                                          │
│  Root                                                    │
│  ├── Management Account (billing & governance)          │
│  │                                                       │
│  ├── OU: Production                                      │
│  │   ├── Account: prod-us-east                          │
│  │   └── Account: prod-eu-west                          │
│  │                                                       │
│  ├── OU: Non-Production                                  │
│  │   ├── Account: staging                               │
│  │   └── Account: dev                                   │
│  │                                                       │
│  └── OU: Shared Services                                 │
│      ├── Account: network (Transit Gateway, DNS)        │
│      └── Account: security (GuardDuty, Security Hub)   │
└──────────────────────────────────────────────────────────┘
```

```bash
# Create organisation
aws organizations create-organization --feature-set ALL

# Create OU
aws organizations create-organizational-unit \
  --parent-id r-xxxx \
  --name Production

# Create new account
aws organizations create-account \
  --email prod-us@myapp.com \
  --account-name "prod-us-east"

# Move account to OU
aws organizations move-account \
  --account-id 111122223333 \
  --source-parent-id r-xxxx \
  --destination-parent-id ou-xxxx-yyyy
```

### Service Control Policies (SCPs)

SCPs restrict what IAM policies in member accounts can allow. They're the ceiling, not the floor.

```json
// SCP: Deny any actions outside approved regions
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DenyNonApprovedRegions",
      "Effect": "Deny",
      "NotAction": [
        "cloudfront:*",
        "iam:*",
        "route53:*",
        "support:*"
      ],
      "Resource": "*",
      "Condition": {
        "StringNotIn": {
          "aws:RequestedRegion": ["us-east-1", "us-west-2", "eu-west-1"]
        }
      }
    }
  ]
}
```

```json
// SCP: Prevent disabling security services
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DenySecurityServiceChanges",
      "Effect": "Deny",
      "Action": [
        "cloudtrail:StopLogging",
        "cloudtrail:DeleteTrail",
        "guardduty:DeleteDetector",
        "guardduty:DisassociateFromMasterAccount",
        "config:DeleteConfigRule",
        "config:StopConfigurationRecorder"
      ],
      "Resource": "*"
    }
  ]
}
```

```bash
# Create SCP
aws organizations create-policy \
  --name "DenyNonApprovedRegions" \
  --type SERVICE_CONTROL_POLICY \
  --content file://scp-regions.json

# Attach SCP to OU
aws organizations attach-policy \
  --policy-id p-xxxx \
  --target-id ou-xxxx-yyyy
```

---

## 12.6 Control Tower

Control Tower sets up a well-architected multi-account environment ("landing zone") with guardrails (preventive SCPs + detective Config rules).

```
Control Tower automates:
• Multi-account structure (log archive account, audit account)
• Baseline security (CloudTrail, Config in all accounts)
• SSO (IAM Identity Center) for account access
• Guardrails:
  - Preventive: backed by SCPs (e.g., "Disallow public S3 buckets")
  - Detective: backed by Config rules (e.g., "Alert on unencrypted RDS")
```

---

## 12.7 Trusted Advisor

Trusted Advisor analyses your account and gives recommendations in 5 categories.

```
┌──────────────────────────────────────────────────────────┐
│               TRUSTED ADVISOR CATEGORIES                 │
├──────────────────────────────────────────────────────────┤
│ Cost Optimisation                                        │
│ • Idle EC2 instances                                    │
│ • Underutilised EBS volumes                             │
│ • Unassociated Elastic IPs                              │
│ • Old snapshots, S3 lifecycle not configured            │
├──────────────────────────────────────────────────────────┤
│ Performance                                              │
│ • EC2 over-utilised (needs upsize)                      │
│ • CloudFront not using HTTP/2                           │
│ • EC2 with high network traffic                         │
├──────────────────────────────────────────────────────────┤
│ Security                                                 │
│ • Root account without MFA ← always check this         │
│ • IAM access keys not rotated                           │
│ • Security groups with unrestricted access              │
│ • S3 bucket permissions too open                        │
├──────────────────────────────────────────────────────────┤
│ Fault Tolerance                                          │
│ • EC2 instances not in multiple AZs                     │
│ • RDS not multi-AZ                                      │
│ • No Auto Scaling configured                            │
│ • No recent EBS snapshots                               │
├──────────────────────────────────────────────────────────┤
│ Service Limits                                          │
│ • VPCs approaching limit                                │
│ • EC2 instances near limit                              │
└──────────────────────────────────────────────────────────┘
```

```bash
# List Trusted Advisor checks
aws support describe-trusted-advisor-checks \
  --language en \
  --query "checks[*].[id,name,category]"

# Refresh and get results for a specific check
CHECK_ID="Qch7DwouX1"  # Security Groups unrestricted access
aws support refresh-trusted-advisor-check --check-id $CHECK_ID
aws support describe-trusted-advisor-check-result \
  --check-id $CHECK_ID \
  --language en
```

---

## 12.8 Cost Optimisation Strategies

```
┌──────────────────────────────────────────────────────────────┐
│              COST OPTIMISATION QUICK WINS                    │
├──────────────────────────────────────────────────────────────┤
│ Compute                                                      │
│ • Use Graviton (ARM) instances — 20% cheaper for same perf  │
│ • Spot Instances for stateless, fault-tolerant workloads    │
│   (savings: 60-90% vs on-demand)                            │
│ • Auto Scaling — don't run at peak capacity 24/7            │
│ • Right-size: use Compute Optimizer recommendations          │
│ • Lambda: right-size memory (use Lambda Power Tuning tool)  │
├──────────────────────────────────────────────────────────────┤
│ Storage                                                      │
│ • S3 lifecycle policies: move to IA, then Glacier           │
│ • S3 Intelligent-Tiering for unpredictable access patterns  │
│ • Delete unattached EBS volumes and old snapshots           │
│ • EBS gp3 over gp2 (same performance, 20% cheaper)         │
├──────────────────────────────────────────────────────────────┤
│ Networking                                                   │
│ • Data transfer is expensive — keep traffic within region   │
│ • VPC Endpoints: avoid NAT Gateway data processing fees     │
│   for S3/DynamoDB (can save hundreds/month)                 │
│ • CloudFront reduces origin data transfer costs             │
├──────────────────────────────────────────────────────────────┤
│ Database                                                     │
│ • Aurora Serverless v2 for variable workloads               │
│ • DynamoDB on-demand for unpredictable traffic              │
│ • Reserved DB instances for steady-state databases          │
│ • ElastiCache reduces expensive DB read load                │
└──────────────────────────────────────────────────────────────┘
```

---

## 12.9 Cost Allocation Tags

Tags applied to resources flow through to the Cost Explorer, enabling per-team/environment billing.

```bash
# Tag resources
aws ec2 create-tags \
  --resources i-0abc123 \
  --tags Key=Environment,Value=prod \
         Key=Team,Value=platform \
         Key=Project,Value=myapp \
         Key=CostCenter,Value=engineering

# Enable cost allocation tags (in Billing console or CLI)
aws ce create-cost-category-definition \
  --name "Environment" \
  --rule-version CostCategoryExpression.v1 \
  --rules '[
    {"Value": "Production", "Rule": {"Tags": {"Key": "Environment", "Values": ["prod"]}}},
    {"Value": "Staging", "Rule": {"Tags": {"Key": "Environment", "Values": ["staging"]}}},
    {"Value": "Development", "Rule": {"Tags": {"Key": "Environment", "Values": ["dev"]}}}
  ]'
```

---

## 12.10 Interview Questions

**Q: How do you reduce AWS costs in production?**
> Start with visibility: tag everything, enable Cost Explorer, look for top spenders. Quick wins: (1) delete idle EC2 instances and unattached EBS volumes (Trusted Advisor flags these); (2) add S3 lifecycle policies to move old objects to Glacier; (3) switch EBS volumes from gp2 to gp3; (4) use VPC endpoints for S3/DynamoDB to avoid NAT Gateway charges. For sustained savings: purchase Savings Plans for steady-state compute, use Spot Instances for batch jobs, right-size with Compute Optimizer.

**Q: What are Service Control Policies and when would you use them?**
> SCPs are organisation-level policies that set the maximum permissions allowed in member accounts — even if a member account's admin grants full access, the SCP can restrict it. Common uses: (1) restrict services to approved regions only; (2) prevent disabling security services like CloudTrail or GuardDuty; (3) prevent creation of IAM admin users; (4) enforce encryption requirements. SCPs don't grant permissions — they only restrict. The management account is never affected by SCPs.

**Q: What is the difference between consolidated billing and Organizations?**
> Consolidated billing is just one benefit of Organizations — all member account charges roll up to the management account for a single bill. But Organizations also provides governance (SCPs, tag policies), account provisioning automation, Control Tower for landing zones, and integration with services like Security Hub, GuardDuty, and Config to centrally manage security across accounts. The billing benefit also enables volume discounts: S3 requests across all accounts are combined for tier pricing.
