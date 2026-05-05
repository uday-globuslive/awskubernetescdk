# Chapter 12: Cost Management & Governance
## Cost Explorer, Budgets, Savings Plans, Organizations & Compliance

---

## 12.1 AWS Cost Management Overview

```
┌────────────────────────────────────────────────────────────────────┐
│               AWS COST MANAGEMENT TOOLS                            │
├──────────────────────┬─────────────────────────────────────────────┤
│ Cost Explorer        │ Visualize, analyze, forecast spending       │
│ AWS Budgets          │ Alerts when costs exceed thresholds         │
│ Cost & Usage Report  │ Most detailed billing data (per-hour CSV)   │
│ Savings Plans        │ Commit to usage for up to 66% discount      │
│ Reserved Instances   │ EC2/RDS/ElastiCache 1-3yr commitment        │
│ Spot Instances       │ Spare capacity at 70-90% discount           │
├──────────────────────┼─────────────────────────────────────────────┤
│ AWS Organizations    │ Multi-account structure, consolidated billing│
│ Control Tower        │ Landing zone, guardrails, account vending   │
│ Service Control Pol. │ Permission guardrails across accounts       │
│ Trusted Advisor      │ Best practices checks across 5 categories   │
│ Compute Optimizer    │ EC2/Lambda/EBS rightsizing recommendations  │
│ Cost Allocation Tags │ Attribute costs to teams/projects/services  │
└──────────────────────┴─────────────────────────────────────────────┘
```

---

## 12.2 Cost Explorer

```bash
# Get monthly costs by service (last 6 months)
aws ce get-cost-and-usage \
  --time-period Start=2024-08-01,End=2025-02-01 \
  --granularity MONTHLY \
  --metrics "BlendedCost" "UnblendedCost" "UsageQuantity" \
  --group-by Type=DIMENSION,Key=SERVICE

# Get costs by tag (e.g., all resources tagged Environment=prod)
aws ce get-cost-and-usage \
  --time-period Start=2025-01-01,End=2025-02-01 \
  --granularity DAILY \
  --metrics "BlendedCost" \
  --filter '{
    "Tags": {
      "Key": "Environment",
      "Values": ["prod"],
      "MatchOptions": ["EQUALS"]
    }
  }' \
  --group-by Type=DIMENSION,Key=SERVICE

# Cost forecast for next 3 months
aws ce get-cost-forecast \
  --time-period Start=2025-02-01,End=2025-05-01 \
  --metric BLENDED_COST \
  --granularity MONTHLY \
  --prediction-interval-level 95   # 95% confidence interval

# Rightsizing recommendations
aws ce get-rightsizing-recommendation \
  --service EC2 \
  --configuration RecommendationTarget=SAME_INSTANCE_FAMILY,BenefitsConsidered=true \
  --page-size 10

# Cost anomaly detection
aws ce create-anomaly-detector \
  --anomaly-detector '{
    "DimensionKey": "SERVICE",
    "MonitorType": "DIMENSIONAL"
  }'

aws ce create-anomaly-subscription \
  --anomaly-subscription '{
    "MonitorArnList": ["arn:aws:ce::123:anomalymonitor/abc"],
    "Threshold": 50,
    "Frequency": "DAILY",
    "SubscriptionName": "cost-spike-alert",
    "Subscribers": [
      {"Address": "arn:aws:sns:us-east-1:123:cost-alerts", "Type": "SNS"}
    ]
  }'
```

---

## 12.3 AWS Budgets

```bash
# Create monthly cost budget with alert
aws budgets create-budget \
  --account-id 123456789012 \
  --budget '{
    "BudgetName": "monthly-infrastructure-budget",
    "BudgetLimit": {"Amount": "10000", "Unit": "USD"},
    "TimeUnit": "MONTHLY",
    "BudgetType": "COST",
    "CostFilters": {
      "TagKey$Environment": ["prod"]
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
        {"SubscriptionType": "EMAIL", "Address": "ops-team@company.com"},
        {"SubscriptionType": "SNS", "Address": "arn:aws:sns:us-east-1:123:cost-alerts"}
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
        {"SubscriptionType": "EMAIL", "Address": "finance@company.com"}
      ]
    }
  ]'

# Budget action — auto stop EC2 instances when budget exceeded
aws budgets create-budget-action \
  --account-id 123456789012 \
  --budget-name monthly-infrastructure-budget \
  --notification-type ACTUAL \
  --action-type STOP_EC2_INSTANCES \
  --action-threshold '{"ActionThresholdValue": 95, "ActionThresholdType": "PERCENTAGE"}' \
  --definition '{
    "IamActionDefinition": {
      "PolicyArn": "arn:aws:iam::123:policy/StopEC2Policy",
      "Roles": ["arn:aws:iam::123:role/BudgetRole"]
    }
  }' \
  --execution-role-arn arn:aws:iam::123:role/BudgetActionRole \
  --approval-model AUTOMATIC
```

---

## 12.4 Savings Plans vs Reserved Instances

```
┌────────────────────────────────────────────────────────────────────────────┐
│                    SAVINGS PLANS vs RESERVED INSTANCES                     │
├─────────────────────────┬────────────────────────────────────────────────── │
│ SAVINGS PLANS                                                               │
├─────────────────────────┬────────────────────────────────────────────────── │
│ Compute Savings Plans   │ Most flexible — any EC2, Fargate, Lambda         │
│                         │ Up to 66% discount, auto-applies to all regions  │
│ EC2 Instance SP         │ Locked to instance family+region                 │
│                         │ Up to 72% discount, more flexible than RI        │
│ SageMaker SP            │ Committed SageMaker spend, up to 64%             │
├─────────────────────────┴────────────────────────────────────────────────── │
│ RESERVED INSTANCES                                                          │
├─────────────────────────┬────────────────────────────────────────────────── │
│ Standard RI             │ Locked to specific instance type/region/OS       │
│                         │ Up to 72% discount, can sell on RI Marketplace  │
│ Convertible RI          │ Change instance type/OS within commitment        │
│                         │ Up to 54% discount                               │
│ Scheduled RI            │ Specific time windows (deprecated)               │
├─────────────────────────┴────────────────────────────────────────────────── │
│ PAYMENT OPTIONS (both SP and RI):                                           │
│   All Upfront:           Maximum discount (~10% extra over No Upfront)     │
│   Partial Upfront:       Medium discount                                    │
│   No Upfront:            Minimum discount, monthly billing                  │
└────────────────────────────────────────────────────────────────────────────┘

Decision guide:
  Predictable EC2 workloads → EC2 Instance Savings Plans (max discount + flexibility)
  Mix of EC2 + Fargate + Lambda → Compute Savings Plans
  Specific instance families locked in → Standard RI (+ Marketplace option)
  RDS/ElastiCache/Redshift → Reserved Instances only (no SP)
```

```bash
# View Savings Plans recommendations
aws savingsplans describe-savings-plans-purchase-recommendations \
  --savings-plans-type COMPUTE_SP \
  --term-in-years ONE_YEAR \
  --payment-option NO_UPFRONT \
  --lookback-period-in-days THIRTY_DAYS

# Purchase Savings Plan (1-year, no upfront, $100/hr commitment)
aws savingsplans create-savings-plan \
  --savings-plan-offering-id <from-describe-offerings> \
  --commitment 100.0 \
  --tags Business=platform

# View Spot Instance savings and interruption rates by region/AZ
aws ec2 describe-spot-price-history \
  --instance-types m5.xlarge \
  --product-descriptions "Linux/UNIX" \
  --start-time $(date -u +"%Y-%m-%dT%H:%M:%SZ") \
  --region us-east-1
```

---

## 12.5 AWS Organizations

```bash
# Create organization
aws organizations create-organization --feature-set ALL

# Create organizational units (OUs)
ROOT_ID=$(aws organizations list-roots --query "Roots[0].Id" --output text)

aws organizations create-organizational-unit \
  --parent-id $ROOT_ID \
  --name Production

aws organizations create-organizational-unit \
  --parent-id $ROOT_ID \
  --name Sandbox

# Create account within org
aws organizations create-account \
  --email prod-account@company.com \
  --account-name "prod-workloads" \
  --role-name OrganizationAccountAccessRole

# Move account to OU
PROD_OU_ID=$(aws organizations list-organizational-units-for-parent \
  --parent-id $ROOT_ID \
  --query "OrganizationalUnits[?Name=='Production'].Id" --output text)

aws organizations move-account \
  --account-id 999888777666 \
  --source-parent-id $ROOT_ID \
  --destination-parent-id $PROD_OU_ID

# Enable services for entire org
aws organizations enable-aws-service-access \
  --service-principal cloudtrail.amazonaws.com

aws organizations enable-aws-service-access \
  --service-principal config.amazonaws.com

aws organizations enable-aws-service-access \
  --service-principal securityhub.amazonaws.com
```

### Service Control Policies (SCPs)

SCPs are permission guardrails — they define the maximum permissions available, but do NOT grant permissions. IAM policies still needed.

```bash
# Create SCP to prevent disabling CloudTrail
aws organizations create-policy \
  --name deny-cloudtrail-disable \
  --description "Prevent disabling CloudTrail across organization" \
  --content '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Sid": "DenyCloudTrailChanges",
        "Effect": "Deny",
        "Action": [
          "cloudtrail:DeleteTrail",
          "cloudtrail:StopLogging",
          "cloudtrail:UpdateTrail",
          "cloudtrail:PutEventSelectors"
        ],
        "Resource": "*"
      }
    ]
  }' \
  --type SERVICE_CONTROL_POLICY

# Create SCP to restrict to approved regions
aws organizations create-policy \
  --name approved-regions-only \
  --content '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Sid": "DenyNonApprovedRegions",
        "Effect": "Deny",
        "NotAction": [
          "iam:*", "organizations:*", "route53:*", "sts:*",
          "cloudfront:*", "waf:*", "support:*", "trustedadvisor:*"
        ],
        "Resource": "*",
        "Condition": {
          "StringNotIn": {
            "aws:RequestedRegion": ["us-east-1", "us-west-2", "eu-west-1"]
          }
        }
      }
    ]
  }' \
  --type SERVICE_CONTROL_POLICY

# Attach SCP to OU
aws organizations attach-policy \
  --policy-id p-abc123 \
  --target-id $PROD_OU_ID
```

---

## 12.6 AWS Control Tower

Control Tower automates the setup of a multi-account AWS environment with security guardrails.

```
Control Tower Components:
  Landing Zone:        Multi-account environment with pre-configured security baseline
  Account Factory:     Automated account provisioning (vends accounts from template)
  Guardrails:          Preventive (SCPs) and Detective (Config rules) controls
  Log Archive account: Centralized CloudTrail and Config logs
  Audit account:       Security tool aggregation (Security Hub, GuardDuty)

Guardrail Types:
  Strongly Recommended: e.g., Disallow public S3 buckets
  Elective:             e.g., Require S3 lifecycle for versioned buckets
  Mandatory:            e.g., Disallow changes to landing zone setup
```

```bash
# Update landing zone (via Control Tower console or API)
aws controltower list-enabled-controls \
  --scope-identifier "arn:aws:controltower:us-east-1::ou/ou-abc123"

# Enable a control (guardrail) on an OU
aws controltower enable-control \
  --control-identifier "arn:aws:controltower:us-east-1::control/AWS-GR_MFA_ENABLED_FOR_IAM_CONSOLE_ACCESS" \
  --target-identifier "arn:aws:organizations::123:ou/o-abc/ou-xyz"

# Create account via Account Factory (via CLI or ServiceCatalog)
aws servicecatalog provision-product \
  --product-id prod-xxx \
  --provisioning-artifact-id pa-xxx \
  --provisioned-product-name "prod-new-service" \
  --provisioning-parameters '[
    {"Key": "AccountEmail", "Value": "new-service@company.com"},
    {"Key": "AccountName", "Value": "prod-new-service"},
    {"Key": "OUName", "Value": "Production"},
    {"Key": "IamUserAccessToBilling", "Value": "ALLOW"}
  ]'
```

---

## 12.7 Trusted Advisor

```
Trusted Advisor Check Categories:
  ┌──────────────────────────────────────────────────────────────────────┐
  │ COST OPTIMIZATION                                                    │
  │   • Idle EC2 instances (< 10% CPU for 14+ days)                     │
  │   • Underutilized EBS volumes                                        │
  │   • Unassociated Elastic IPs                                         │
  │   • RDS DB instances not Multi-AZ (for RI opportunity)              │
  │   • Reserved Instance optimization                                   │
  ├──────────────────────────────────────────────────────────────────────┤
  │ SECURITY                                                             │
  │   • S3 bucket permissions (open access)                             │
  │   • Security groups allowing unrestricted access                    │
  │   • IAM root account MFA                                            │
  │   • CloudTrail logging not enabled                                  │
  │   • Exposed access keys in code repositories                        │
  ├──────────────────────────────────────────────────────────────────────┤
  │ FAULT TOLERANCE                                                      │
  │   • EC2 instances in single AZ                                      │
  │   • ELB without healthy instances                                   │
  │   • RDS without Multi-AZ or automated backups                      │
  │   • EBS volumes without snapshots                                   │
  ├──────────────────────────────────────────────────────────────────────┤
  │ PERFORMANCE                                                          │
  │   • EC2 instances with high utilization                             │
  │   • CloudFront not using latest protocol                            │
  │   • Large EBS volumes                                               │
  ├──────────────────────────────────────────────────────────────────────┤
  │ SERVICE LIMITS (now Service Quotas)                                  │
  │   • EC2 on-demand limits                                            │
  │   • EIP addresses per region                                        │
  │   • VPC limits                                                      │
  └──────────────────────────────────────────────────────────────────────┘

Note: Full checks require Business/Enterprise Support plan.
```

```bash
# List Trusted Advisor checks
aws support describe-trusted-advisor-checks --language en

# Get check results
aws support describe-trusted-advisor-check-result \
  --check-id Pfx0RwqBli \   # Underutilized EC2 ID
  --language en

# Refresh checks
aws support refresh-trusted-advisor-check --check-id Pfx0RwqBli

# Get summary of all checks
aws support describe-trusted-advisor-checks-summary
```

---

## 12.8 Cost Allocation Tags

```bash
# Activate cost allocation tags in Billing console
aws ce list-cost-allocation-tags --type UserDefined --status Inactive

aws ce update-cost-allocation-tags-status \
  --cost-allocation-tags-status '[
    {"TagKey": "Environment", "Status": "Active"},
    {"TagKey": "Service", "Status": "Active"},
    {"TagKey": "Owner", "Status": "Active"},
    {"TagKey": "Project", "Status": "Active"},
    {"TagKey": "CostCenter", "Status": "Active"}
  ]'

# Enforce tagging via AWS Config rule
aws configservice put-config-rule \
  --config-rule '{
    "ConfigRuleName": "required-tags-all-resources",
    "Source": {"Owner": "AWS", "SourceIdentifier": "REQUIRED_TAGS"},
    "InputParameters": "{\"tag1Key\":\"Environment\",\"tag2Key\":\"Owner\",\"tag3Key\":\"Project\"}",
    "Scope": {
      "ComplianceResourceTypes": [
        "AWS::EC2::Instance",
        "AWS::RDS::DBInstance",
        "AWS::Lambda::Function",
        "AWS::S3::Bucket",
        "AWS::ECS::Service"
      ]
    }
  }'

# Tag resources with AWS Resource Tagging API (bulk tagging)
aws resourcegroupstaggingapi tag-resources \
  --resource-arn-list \
    "arn:aws:ec2:us-east-1:123:instance/i-0abc" \
    "arn:aws:rds:us-east-1:123:db:prod-db" \
  --tags Environment=prod,Owner=platform-team,Project=e-commerce
```

---

## 12.9 AWS Compute Optimizer

```bash
# Opt in to Compute Optimizer
aws compute-optimizer update-enrollment-status --status Active

# Get EC2 recommendations
aws compute-optimizer get-ec2-instance-recommendations \
  --instance-arns arn:aws:ec2:us-east-1:123:instance/i-0abc \
  --filters Name=Finding,Values=OVER_PROVISIONED

# Get Lambda recommendations
aws compute-optimizer get-lambda-function-recommendations \
  --filters Name=Finding,Values=OVER_PROVISIONED,MEMORY_UNDER_PROVISIONED

# Get EBS volume recommendations
aws compute-optimizer get-ebs-volume-recommendations \
  --volume-arns arn:aws:ec2:us-east-1:123:volume/vol-0abc \
  --filters Name=Finding,Values=NOT_OPTIMIZED

# Export recommendations to S3
aws compute-optimizer export-ec2-instance-recommendations \
  --s3-destination-config bucket=my-optimizer-reports,keyPrefix=ec2 \
  --fields Finding,RecommendationOptions,UtilizationMetrics
```

---

## 12.10 Interview Q&A

**Q: What is the difference between Savings Plans and Reserved Instances?**
A: Savings Plans offer commitment to a $/hour spend level in exchange for discounts — more flexible because they apply automatically to any eligible usage. Compute Savings Plans cover EC2 (any family/region/OS), Fargate, and Lambda (up to 66% off). EC2 Instance Savings Plans offer up to 72% but only for specific instance families in a region. Reserved Instances are capacity commitments — locked to specific instance type, OS, and region (Standard RI) or convertible within constraints (Convertible RI). Use Savings Plans for general-purpose discounts; use RIs for RDS, ElastiCache, Redshift, and Elasticsearch (no Savings Plans for these).

**Q: What are Service Control Policies and how do they differ from IAM policies?**
A: SCPs are Organization-level permission boundaries applied to OUs or accounts. They define the MAXIMUM permissions available — even if an IAM policy grants full access, the SCP can restrict it. SCPs do NOT grant permissions (you still need IAM policies). SCPs apply to all principals (users, roles) in the account except the management account itself. Use for: preventing disabling security services, restricting to approved regions, preventing data egress, compliance guardrails across all accounts.

**Q: How do you identify cost savings opportunities in AWS?**
A: Multiple approaches: (1) Cost Explorer rightsizing — shows underutilized instances; (2) Compute Optimizer — ML-based recommendations for EC2, Lambda, EBS; (3) Trusted Advisor — idle resources, unattached EBS/EIP; (4) Cost Anomaly Detection — alerts on unexpected spikes; (5) Reserved Instance/Savings Plans recommendations in Cost Explorer — shows break-even analysis; (6) S3 Storage Lens — identify underused buckets and storage class optimization opportunities; (7) Data Transfer costs — use VPC endpoints to eliminate NAT GW/Internet egress costs.

**Q: What is AWS Control Tower and when would you use it?**
A: Control Tower automates the creation of a secure, multi-account AWS environment (called a Landing Zone). It creates a Log Archive account (centralized CloudTrail/Config), Audit account (Security Hub/GuardDuty), and Account Vending Machine via Service Catalog. Use it when: setting up a new organization from scratch, needing automated account provisioning with pre-configured security, requiring guardrails enforced at scale. It uses SCPs (preventive guardrails) and Config rules (detective guardrails). Control Tower simplifies what would otherwise take weeks of manual configuration.

**Q: What is the AWS Cost and Usage Report and how is it different from Cost Explorer?**
A: The Cost and Usage Report (CUR) is the most comprehensive billing data available — hourly or daily CSV files delivered to S3 with line-item pricing per resource, including Reserved Instance amortization, blended/unblended costs, and all tags. Query it with Athena for custom analysis. Cost Explorer is a visualization tool with pre-built graphs, 12-month history, 3-month forecasts, and an API for programmatic access. CUR is for deep analysis and custom dashboards; Cost Explorer is for quick visualizations and standard reports.

**Q: How do cost allocation tags work and what are the types?**
A: Cost allocation tags appear in billing reports and Cost Explorer to attribute costs to business dimensions. Two types: (1) AWS-generated tags — automatically generated by AWS (e.g., aws:createdBy), prefix "aws:"; (2) User-defined tags — tags you apply to resources (e.g., Environment, Project, Owner). Both must be activated in the Billing console before they appear in reports. Best practice: enforce tagging through Config rules, AWS Tag Policies in Organizations, and require tags for all resources via SCPs. Start tagging immediately — you can't backfill historical costs.
