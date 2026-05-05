# Chapter 11: Cost Optimization & Performance

## AWS SysOps Administrator Exam Domain Coverage
- **Domain 6**: Cost and Performance Optimization (12% of exam)
- Cost Explorer, Trusted Advisor, Savings Plans, rightsizing, performance tools

---

## 11.1 AWS Cost Management Ecosystem

```
┌────────────────────────────────────────────────────────────────┐
│               AWS COST MANAGEMENT TOOLS                        │
│                                                                │
│  VISIBILITY                CONTROL               OPTIMIZATION  │
│  ├─ Cost Explorer          ├─ Budgets            ├─ Trusted    │
│  ├─ Cost & Usage Report    ├─ Budget Actions      │  Advisor   │
│  ├─ Cost Allocation Tags   └─ Reserved Instances ├─ Compute    │
│  └─ AWS Organizations                             │  Optimizer │
│                                                   ├─ Savings   │
│                                                   │  Plans     │
│                                                   └─ Spot      │
│                                                      Instances │
└────────────────────────────────────────────────────────────────┘
```

---

## 11.2 Cost Explorer

Cost Explorer provides **visualizations and analysis** of your AWS costs.

```bash
# Get cost summary for last month (CLI)
aws ce get-cost-and-usage \
  --time-period Start=2025-04-01,End=2025-05-01 \
  --granularity MONTHLY \
  --metrics "BlendedCost" "UnblendedCost" "UsageQuantity" \
  --group-by Type=SERVICE \
  --query 'ResultsByTime[0].Groups[*].{Service:Keys[0],Cost:Metrics.BlendedCost.Amount}' \
  --output table

# Get cost by tag (must enable cost allocation tags first)
aws ce get-cost-and-usage \
  --time-period Start=2025-04-01,End=2025-05-01 \
  --granularity MONTHLY \
  --metrics "BlendedCost" \
  --group-by Type=TAG,Key=CostCenter

# Get cost forecast
aws ce get-cost-forecast \
  --time-period Start=2025-05-01,End=2025-06-01 \
  --metric BLENDED_COST \
  --granularity MONTHLY

# Get rightsizing recommendations
aws ce get-rightsizing-recommendation \
  --service AmazonEC2 \
  --configuration RecommendationTarget=CROSS_INSTANCE_FAMILY
```

### Cost Allocation Tags
```bash
# Enable cost allocation tags (must be done in management account)
aws ce create-cost-category-definition \
  --name CostByTeam \
  --rule-version CostCategoryExpression.v1 \
  --rules '[
    {
      "Value": "Platform",
      "Rule": {
        "Tags": {
          "Key": "Team",
          "Values": ["platform"],
          "MatchOptions": ["EQUALS"]
        }
      }
    },
    {
      "Value": "Application",
      "Rule": {
        "Tags": {
          "Key": "Team",
          "Values": ["app", "backend", "frontend"],
          "MatchOptions": ["EQUALS"]
        }
      }
    }
  ]'

# Activate cost allocation tags (required before they appear in reports)
# Done through AWS console: Billing → Cost allocation tags → Activate
```

---

## 11.3 AWS Budgets

Budgets let you set **cost and usage thresholds** with alerts and automated actions.

```bash
# Create monthly cost budget with alerts at 80% and 100%
aws budgets create-budget \
  --account-id 123456789012 \
  --budget '{
    "BudgetName": "monthly-total-cost",
    "BudgetLimit": {"Amount": "10000", "Unit": "USD"},
    "TimeUnit": "MONTHLY",
    "BudgetType": "COST",
    "CostFilters": {
      "LinkedAccount": ["234567890123"]
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
        {"SubscriptionType": "EMAIL", "Address": "ops@example.com"},
        {"SubscriptionType": "SNS", "Address": "arn:aws:sns:us-east-1:123456789012:cost-alerts"}
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
        {"SubscriptionType": "EMAIL", "Address": "cto@example.com"}
      ]
    }
  ]'

# Create budget with automatic action (stop EC2 instances when budget exceeded)
aws budgets create-budget-action \
  --account-id 123456789012 \
  --budget-name monthly-total-cost \
  --notification-type ACTUAL \
  --action-type STOP_EC2_INSTANCES \
  --action-threshold '{
    "ActionThresholdValue": 95,
    "ActionThresholdType": "PERCENTAGE"
  }' \
  --definition '{
    "IamActionDefinition": {
      "PolicyArn": "arn:aws:iam::aws:policy/AmazonEC2FullAccess",
      "Roles": ["arn:aws:iam::123456789012:role/BudgetActionsRole"]
    }
  }' \
  --execution-role-arn arn:aws:iam::123456789012:role/AWSBudgetsActionsWithAWSResourceControlAccess \
  --approval-model AUTO
```

---

## 11.4 Reserved Instances

Reserved Instances provide significant discounts (up to 72%) in exchange for commitment.

### RI Types Comparison

| Type | Discount | Flexibility | Notes |
|------|---------|-------------|-------|
| **Standard RI** | Up to 72% | Low (can sell on Marketplace) | Specific instance type/region |
| **Convertible RI** | Up to 66% | High (can change family/OS/tenancy) | Cannot sell on Marketplace |

### Payment Options
| Option | Upfront | Discount |
|--------|---------|---------|
| No Upfront | $0 | Lowest |
| Partial Upfront | 50% | Medium |
| All Upfront | 100% | Highest |

```bash
# Find RI recommendations from Cost Explorer
aws ce get-reservation-purchase-recommendation \
  --service AmazonEC2 \
  --term-in-years ONE_YEAR \
  --payment-option PARTIAL_UPFRONT \
  --lookback-period-in-days SIXTY_DAYS

# List active RIs
aws ec2 describe-reserved-instances \
  --filters Name=state,Values=active

# Modify RI (Standard RI — change scope or instance size within same family)
aws ec2 modify-reserved-instances \
  --reserved-instances-ids XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX \
  --target-configurations '[{
    "AvailabilityZone": "us-east-1a",
    "InstanceCount": 2,
    "InstanceType": "m5.large",
    "Platform": "Linux/UNIX"
  }]'
```

---

## 11.5 Savings Plans

Savings Plans are a **flexible pricing model** — commit to a spend amount ($/hour) for 1 or 3 years.

| Plan Type | Coverage | Flexibility |
|-----------|---------|-------------|
| **Compute Savings Plan** | EC2, Fargate, Lambda | Any instance family/size/region/OS |
| **EC2 Savings Plan** | EC2 only | Any size/OS within a specific family/region |
| **SageMaker Savings Plan** | SageMaker | Any instance type/region |

```
Example: Compute Savings Plan at $1/hour for 1 year
  → Pay $8,760 committed + remaining on-demand
  → Save ~66% on all EC2, Fargate, Lambda within commitment
  → No need to specify instance type
```

```bash
# Get Savings Plan recommendations
aws ce get-savings-plans-purchase-recommendation \
  --savings-plans-type COMPUTE_SP \
  --term-in-years ONE_YEAR \
  --payment-option PARTIAL_UPFRONT \
  --lookback-period-in-days SIXTY_DAYS

# View active Savings Plans
aws savingsplans describe-savings-plans \
  --states active

# Check Savings Plans coverage (how much spend is covered)
aws ce get-savings-plans-coverage \
  --time-period Start=2025-04-01,End=2025-05-01 \
  --granularity MONTHLY
```

---

## 11.6 Spot Instances

Spot Instances use **spare AWS capacity** at up to 90% discount — but can be interrupted with 2-minute notice.

### Spot Use Cases

```
✅ Good for Spot:               ❌ NOT good for Spot:
  - Batch processing              - Production web servers
  - Big data analytics            - Databases (stateful)
  - CI/CD pipelines               - Real-time API (unless mixed fleet)
  - ML training                   - On-premises replacement
  - Rendering                     - Any job < 2 minutes
```

### Spot Fleet Strategy
```bash
# Spot Fleet with diversified instance types (reduces interruption risk)
aws ec2 request-spot-fleet \
  --spot-fleet-request-config '{
    "TargetCapacity": 20,
    "AllocationStrategy": "diversified",
    "LaunchSpecifications": [
      {
        "InstanceType": "m5.xlarge",
        "SubnetId": "subnet-az1",
        "SpotPrice": "0.10"
      },
      {
        "InstanceType": "m5.2xlarge",
        "SubnetId": "subnet-az2",
        "SpotPrice": "0.18",
        "WeightedCapacity": 2
      },
      {
        "InstanceType": "m4.xlarge",
        "SubnetId": "subnet-az1",
        "SpotPrice": "0.10"
      }
    ],
    "IamFleetRole": "arn:aws:iam::123456789012:role/AmazonEC2SpotFleetRole"
  }'
```

### Handle Spot Interruptions
```python
import requests
import boto3
import threading

def check_spot_interruption():
    """Check for spot instance interruption notice via IMDS."""
    try:
        # IMDSv2 token
        token = requests.put(
            'http://169.254.169.254/latest/api/token',
            headers={'X-aws-ec2-metadata-token-ttl-seconds': '21600'},
            timeout=1
        ).text
        
        response = requests.get(
            'http://169.254.169.254/latest/meta-data/spot/termination-time',
            headers={'X-aws-ec2-metadata-token': token},
            timeout=1
        )
        
        if response.status_code == 200:
            # Termination notice received! 2 minutes to gracefully shutdown
            print(f"⚠️ Spot termination at: {response.text}")
            graceful_shutdown()
            return True
    except requests.exceptions.ConnectionError:
        pass
    return False

def graceful_shutdown():
    """Save state and deregister before termination."""
    # 1. Stop accepting new work
    # 2. Complete in-flight work
    # 3. Save checkpoint to S3
    # 4. Deregister from load balancer/ASG
    pass

# Poll every 5 seconds
def monitor_interruption():
    while True:
        if check_spot_interruption():
            break
        time.sleep(5)

thread = threading.Thread(target=monitor_interruption, daemon=True)
thread.start()
```

---

## 11.7 AWS Trusted Advisor

Trusted Advisor checks your account against AWS best practices across 5 categories.

### Trusted Advisor Categories

| Category | Examples |
|----------|---------|
| **Cost Optimization** | Idle EC2, unused EIPs, unattached EBS, underutilized RIs |
| **Performance** | High utilization EC2, CloudFront caching |
| **Security** | Open security groups, root MFA, exposed access keys |
| **Fault Tolerance** | RDS no backup, EC2 no Multi-AZ, VPN redundancy |
| **Service Limits** | Approaching resource limits |

```bash
# Get all Trusted Advisor checks
aws support describe-trusted-advisor-checks --language en

# Get check results (requires Business or Enterprise support)
# Check ID for "Low Utilization Amazon EC2 Instances"
aws support describe-trusted-advisor-check-result \
  --check-id Qch7DwouX1 \
  --language en

# Refresh a check
aws support refresh-trusted-advisor-check --check-id Qch7DwouX1

# Get overall summary
aws support describe-trusted-advisor-check-summaries \
  --check-ids Qch7DwouX1 1iG5NDGVre 0t121N1Ty3
```

---

## 11.8 Compute Optimizer

Compute Optimizer uses **machine learning** to analyze utilization and provide rightsizing recommendations.

```bash
# Enable Compute Optimizer
aws compute-optimizer update-enrollment-status --status Active

# Get EC2 recommendations
aws compute-optimizer get-ec2-instance-recommendations \
  --instance-arns arn:aws:ec2:us-east-1:123456789012:instance/i-xxx

# Get Auto Scaling recommendations
aws compute-optimizer get-auto-scaling-group-recommendations

# Get Lambda recommendations
aws compute-optimizer get-lambda-function-recommendations \
  --function-arns arn:aws:lambda:us-east-1:123456789012:function:MyFunction

# Export recommendations to S3
aws compute-optimizer export-ec2-instance-recommendations \
  --s3-destination-config bucket=my-cost-bucket,keyPrefix=optimizer/
```

### Understanding Recommendations
```
Current: m5.xlarge (4 vCPU, 16GB)
  CPU: avg 5%, max 12%
  Memory: avg 8%, max 15%

Recommendation: t3.medium (2 vCPU, 4GB)
  Projected savings: $67/month (49%)
  Risk: Very Low
  
Action: 
  - Downsize to t3.medium (save money)
  OR
  - Move to t3a.medium (ARM, save more)
  OR  
  - Keep m5.xlarge if expecting growth
```

---

## 11.9 Storage Cost Optimization

### S3 Cost Optimization
```bash
# Enable S3 Intelligent-Tiering for unknown access patterns
aws s3api put-bucket-intelligent-tiering-configuration \
  --bucket data-lake-bucket \
  --id enable-intelligent-tiering \
  --intelligent-tiering-configuration '{
    "Id": "enable-intelligent-tiering",
    "Status": "Enabled",
    "Tierings": [
      {"Days": 90, "AccessTier": "ARCHIVE_ACCESS"},
      {"Days": 180, "AccessTier": "DEEP_ARCHIVE_ACCESS"}
    ]
  }'

# Find unused S3 objects (accessed last > 90 days)
aws s3api list-objects-v2 \
  --bucket data-lake-bucket \
  --query 'Contents[?LastModified<`2025-02-01`].[Key,Size]' \
  --output table

# Identify unattached EBS volumes (save money)
aws ec2 describe-volumes \
  --filters Name=status,Values=available \
  --query 'Volumes[*].{ID:VolumeId,Size:Size,Type:VolumeType,AZ:AvailabilityZone}' \
  --output table
```

### EBS Cost Optimization
```bash
# Downgrade gp2 → gp3 (same performance, 20% cheaper)
# gp3 allows you to independently set IOPS and throughput
VOLUMES=$(aws ec2 describe-volumes \
  --filters Name=volume-type,Values=gp2 Name=status,Values=in-use \
  --query 'Volumes[*].VolumeId' --output text)

for volume_id in $VOLUMES; do
  aws ec2 modify-volume \
    --volume-id $volume_id \
    --volume-type gp3
  echo "Converting $volume_id to gp3"
done
```

---

## 11.10 Performance Optimization

### EC2 Performance
```bash
# Enable enhanced networking (ENA)
aws ec2 modify-instance-attribute \
  --instance-id i-xxx \
  --ena-support

# Enable placement group for low latency (Cluster)
aws ec2 create-placement-group \
  --group-name low-latency-cluster \
  --strategy cluster

# Check CPU credit balance for burstable instances
aws cloudwatch get-metric-statistics \
  --namespace AWS/EC2 \
  --metric-name CPUCreditBalance \
  --dimensions Name=InstanceId,Value=i-xxx \
  --start-time $(date -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 300 \
  --statistics Average
```

### RDS Performance
```bash
# Enable Performance Insights
aws rds modify-db-instance \
  --db-instance-identifier prod-postgres \
  --enable-performance-insights \
  --performance-insights-kms-key-id alias/rds-performance-insights \
  --performance-insights-retention-period 7

# Get top SQL queries from Performance Insights
aws pi get-resource-metrics \
  --service-type RDS \
  --identifier db-xxx \
  --metric-queries '[{
    "Metric": "db.load.avg",
    "GroupBy": {
      "Group": "db.sql_tokenized",
      "Dimensions": ["db.sql_tokenized.statement"],
      "Limit": 10
    }
  }]' \
  --start-time $(date -d '1 hour ago' +%s) \
  --end-time $(date +%s) \
  --period-in-seconds 300

# Read replica for read offloading
aws rds create-db-instance-read-replica \
  --db-instance-identifier prod-postgres-replica-1 \
  --source-db-instance-identifier prod-postgres \
  --db-instance-class db.m5.large \
  --availability-zone us-east-1b \
  --publicly-accessible false
```

### CloudFront Performance
```bash
# Check cache hit ratio (aim for >80%)
aws cloudwatch get-metric-statistics \
  --namespace AWS/CloudFront \
  --metric-name CacheHitRate \
  --dimensions Name=DistributionId,Value=EDFDVBD6EXAMPLE \
  --start-time $(date -d '1 day ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 3600 \
  --statistics Average

# Optimize cache behavior for APIs
aws cloudfront create-distribution \
  --distribution-config '{
    "DefaultCacheBehavior": {
      "CachePolicyId": "658327ea-f89d-4fab-a63d-7e88639e58f6",  # CachingOptimized
      "Compress": true,
      "ViewerProtocolPolicy": "redirect-to-https"
    },
    "CacheBehaviors": [{
      "PathPattern": "/api/*",
      "CachePolicyId": "4135ea2d-6df8-44a3-9df3-4b5a84be39ad",  # CachingDisabled for API
      "OriginRequestPolicyId": "b689b0a8-53d0-40ab-baf2-68738e2966ac"
    }]
  }'
```

---

## 11.11 Lambda Cost Optimization

```python
# Lambda Power Tuning — find optimal memory size
# (Run AWS Lambda Power Tuning tool from SAR)

# Optimize Lambda with:
# 1. Right memory size (more memory = faster CPU = lower duration)
# 2. Provision concurrency for latency-sensitive functions
# 3. Reuse connections (outside handler)
# 4. Use ARM (Graviton2) — 20% cheaper

import boto3
from functools import lru_cache

# ✅ Outside handler — reused across invocations
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('products')

@lru_cache(maxsize=128)
def get_product_template(template_id: str):
    """Cache template lookups to reduce DynamoDB calls."""
    return table.get_item(Key={'id': template_id})['Item']

def lambda_handler(event, context):
    # ✅ Uses cached connection and cached results
    template = get_product_template(event['templateId'])
    return {'statusCode': 200, 'body': json.dumps(template)}
```

```bash
# Provision concurrency (avoids cold starts for critical functions)
aws lambda put-provisioned-concurrency-config \
  --function-name critical-api \
  --qualifier production \
  --provisioned-concurrent-executions 10

# Check cold start percentage
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name InitDuration \
  --dimensions Name=FunctionName,Value=critical-api \
  --start-time $(date -d '1 day ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 3600 \
  --statistics SampleCount Average
```

---

## 11.12 Real-World Project: Monthly Cost Review Automation

```python
import boto3
import json
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

ce = boto3.client('ce')
sns = boto3.client('sns')

def monthly_cost_report(event, context):
    """Generate monthly cost review and send to ops team."""
    
    today = date.today()
    first_of_month = today.replace(day=1)
    last_month_start = (first_of_month - relativedelta(months=1)).isoformat()
    first_of_month_str = first_of_month.isoformat()
    
    # Get last month's costs by service
    response = ce.get_cost_and_usage(
        TimePeriod={'Start': last_month_start, 'End': first_of_month_str},
        Granularity='MONTHLY',
        Metrics=['BlendedCost'],
        GroupBy=[{'Type': 'SERVICE'}]
    )
    
    services = response['ResultsByTime'][0]['Groups']
    total = sum(float(s['Metrics']['BlendedCost']['Amount']) for s in services)
    
    # Sort by cost
    services.sort(key=lambda x: float(x['Metrics']['BlendedCost']['Amount']), reverse=True)
    
    # Format report
    lines = [
        f"📊 AWS Monthly Cost Report — {last_month_start[:7]}",
        f"Total: ${total:.2f}",
        "",
        "Top Services:"
    ]
    
    for s in services[:10]:
        cost = float(s['Metrics']['BlendedCost']['Amount'])
        pct = (cost / total) * 100
        lines.append(f"  {s['Keys'][0]}: ${cost:.2f} ({pct:.1f}%)")
    
    # Get rightsizing recommendations
    try:
        recommendations = ce.get_rightsizing_recommendation(
            Service='AmazonEC2',
            Configuration={'RecommendationTarget': 'CROSS_INSTANCE_FAMILY'}
        )
        
        savings = recommendations.get('Summary', {}).get('EstimatedTotalMonthlySavingsAmount', '0')
        lines.append(f"\n💡 Potential rightsizing savings: ${savings}/month")
    except Exception:
        pass
    
    report = '\n'.join(lines)
    
    # Send to SNS
    sns.publish(
        TopicArn='arn:aws:sns:us-east-1:123456789012:monthly-cost-reports',
        Subject=f'AWS Cost Report — {last_month_start[:7]} — ${total:.2f}',
        Message=report
    )
    
    return {'report': report, 'total': total}
```

---

## 11.13 Practice Questions (SysOps Exam Level)

**Q1:** Your EC2 instances are running at 5% average CPU utilization. What is the most cost-effective solution?

**A:** Several options based on workload:
1. **Downsize instances** — use Compute Optimizer recommendations
2. **Move to T-class (burstable)** — t3/t3a instances for workloads with low average but occasional spikes
3. **Consolidate** — run multiple applications on fewer instances
4. **Convert to Graviton** (m6g, c6g) — same performance, 20-40% cheaper

```bash
# Get specific recommendations
aws compute-optimizer get-ec2-instance-recommendations \
  --account-ids 123456789012
```

---

**Q2:** Your S3 bill increased by 40% last month. How do you investigate?

**A:**
```bash
# 1. Check Cost Explorer with S3 feature grouping
aws ce get-cost-and-usage \
  --time-period Start=2025-04-01,End=2025-05-01 \
  --granularity MONTHLY \
  --metrics BlendedCost \
  --group-by Type=USAGE_TYPE  # Shows STANDARD-Storage, REQUESTS, etc.

# 2. Enable S3 Storage Lens for detailed analysis
aws s3control put-storage-lens-configuration \
  --config-id storage-lens-org \
  --account-id 123456789012 \
  --storage-lens-configuration '{
    "Id": "storage-lens-org",
    "IsEnabled": true,
    "AccountLevel": {
      "ActivityMetrics": {"IsEnabled": true},
      "BucketLevel": {"ActivityMetrics": {"IsEnabled": true}}
    }
  }'
```

Common causes: unexpected GetObject requests, large multipart uploads not completed, replication costs, no lifecycle policies moving old data to cheaper tiers.

---

**Q3:** Compare Reserved Instances vs Savings Plans for an organization running 100 EC2 instances across multiple regions with varied instance types.

**A:** **Savings Plans (Compute)** is better for this scenario:
- RIs are tied to specific instance families/regions — complex with 100 diverse instances
- Compute Savings Plans cover any instance type, any region, any OS, and also Fargate/Lambda
- Savings Plans auto-apply to the highest discount opportunities
- Easier management (commitment in $/hour vs specific instance quantities)

RIs are better when: predictable, specific instance types, want to sell on Marketplace.

---

**Q4:** You have unused Reserved Instances for m5.large running in us-east-1 but need m5.xlarge. Can you convert them?

**A:** Yes, but it depends on RI type:
- **Standard RI**: Cannot change instance family/size — must sell on Marketplace and buy new ones
- **Convertible RI**: Can be exchanged for different instance family, size, OS, tenancy

```bash
# Convert Convertible RI
aws ec2 create-reserved-instances-listing \
  --reserved-instances-id xxx \
  --instance-count 1 \
  --price-schedules '[{"Term": 1, "Price": 0.01}]'
  
# Actually, use the "Exchange Reserved Instances" in console for Convertible RIs
```

---

**Q5:** How do you enforce tagging requirements to ensure all resources have cost allocation tags?

**A:**
1. **SCP**: Deny creating resources without required tags
2. **AWS Config rule**: `required-tags` — detect non-compliant resources
3. **AWS Config auto-remediation**: Tag or notify on non-compliance

```bash
# SCP to require tags on EC2 launch
cat > require-tags-scp.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "RequireCostCenterTag",
    "Effect": "Deny",
    "Action": ["ec2:RunInstances", "rds:CreateDBInstance", "s3:CreateBucket"],
    "Resource": "*",
    "Condition": {
      "Null": {
        "aws:RequestTag/CostCenter": "true"
      }
    }
  }]
}
EOF

aws organizations create-policy \
  --name RequireCostCenterTag \
  --type SERVICE_CONTROL_POLICY \
  --document file://require-tags-scp.json
```

---

## Key Cost & Performance Terms for Exam

| Term | Definition |
|------|-----------|
| Cost Explorer | Visualize, analyze, forecast AWS costs |
| Cost Allocation Tags | User-defined tags for cost attribution |
| AWS Budgets | Set cost/usage thresholds with alerts and actions |
| Reserved Instances | 1 or 3 year commitment for EC2 discount |
| Convertible RI | Can exchange for different instance type/family |
| Savings Plans | Flexible commitment ($/hour) across EC2/Fargate/Lambda |
| Compute Savings Plan | Most flexible — any instance type, region, OS |
| Spot Instances | Up to 90% discount — can be interrupted |
| Spot Fleet | Collection of Spot + On-Demand instances |
| Trusted Advisor | Best practices checks across 5 categories |
| Compute Optimizer | ML-based rightsizing recommendations |
| Rightsizing | Moving to smaller/cheaper instance that meets needs |
| Graviton | AWS ARM-based processors — 20-40% cheaper |
| gp3 | Latest EBS type — cheaper than gp2, configurable IOPS |
| S3 Intelligent-Tiering | Auto-move objects between tiers based on access |
| Performance Insights | RDS query performance analysis tool |
| Enhanced Networking | Higher PPS, lower latency via ENA |
| Placement Group | Strategy for instance placement (Cluster/Spread/Partition) |
