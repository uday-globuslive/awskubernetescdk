
content = r"""# Chapter 11: Cost & Performance Optimization
## (Spending Less While Running Faster)

---

## 11.1 AWS Pricing Fundamentals

### How AWS Bills You

AWS charges based on actual usage — no upfront costs or long-term contracts required (with pay-as-you-go). This is revolutionary compared to buying physical servers:

```
Traditional Data Center:
  - Buy servers: $10,000 each (upfront, whether you use them or not)
  - 3-year lease for data center space
  - Overprovision for peak load (most capacity sits idle)
  - Takes months to get new capacity

AWS Pay-As-You-Go:
  - Pay per second (EC2), per GB (storage), per request (Lambda)
  - No idle capacity — scale down when not needed
  - New capacity in minutes
  - Start small, grow with demand
```

**The three pricing models:**

**1. On-Demand (Pay as you go):**
- Highest per-hour rate
- No commitment
- Use for: unpredictable workloads, development, testing, new applications
- Stop billing the moment you stop the instance

**2. Reserved Instances / Savings Plans (Commit for a discount):**
- 40-70% discount vs On-Demand
- Commit to 1 or 3 years
- Use for: steady-state workloads, production databases, always-running services

**3. Spot Instances (Bid for spare capacity):**
- Up to 90% discount vs On-Demand
- AWS can interrupt with 2-minute warning
- Use for: batch processing, ML training, video rendering, CI/CD

### Understanding Your AWS Bill (The Math)

```
EC2 On-Demand Example:
  t3.medium in us-east-1 = $0.0416/hour
  Running 24/7 for 30 days = 720 hours
  Monthly cost = 720 × $0.0416 = $29.95/month

Reserved Instance (1-year, no upfront):
  t3.medium 1-year reserved = $0.0262/hour
  Monthly cost = 720 × $0.0262 = $18.86/month
  Savings = $29.95 - $18.86 = $11.09/month (37% savings)

S3 Storage Example:
  Standard storage = $0.023/GB/month
  100 GB stored = $2.30/month
  + GET requests: $0.0004 per 1,000 requests
  + PUT requests: $0.005 per 1,000 requests
  
RDS Example:
  db.t3.medium Multi-AZ = $0.136/hour
  720 hours/month = $97.92
  Storage: $0.23/GB/month × 100 GB = $23
  I/O: $0.20 per 1 million requests
  Backups: First 100% of DB storage free, then $0.095/GB

Data Transfer:
  Data IN to AWS: FREE
  Data OUT to Internet: $0.09/GB (first 10 TB/month)
  Data between AZs in same region: $0.01/GB each way
  Data between regions: varies by region pair
```

---

## 11.2 EC2 Cost Optimization Strategies

### Comparison: On-Demand vs Reserved vs Spot

```
Workload: Web application, always running, predictable load
  Recommendation: Reserved Instances (1-year, partial upfront)
  Why: 40-60% savings; workload is predictable

Workload: Development environment, used 9am-5pm weekdays
  Recommendation: On-Demand + scheduled stop/start via Lambda
  Why: Stop instances after hours → only pay 40 hours/week vs 168
  Savings: 76% vs running 24/7

Workload: Weekly batch data processing, 4 hours long
  Recommendation: Spot Instances
  Why: Can tolerate interruption; 80%+ savings; run during off-peak
  
Workload: Machine learning model training
  Recommendation: Spot Instances (p3 or g4 with Spot Fleet)
  Why: Training can be checkpointed and resumed if interrupted
  Savings: $0.27/hour vs $3.06/hour on-demand for p3.2xlarge (91% off!)
```

### Reserved Instances (RI) Types

| RI Type | Flexibility | Discount | Resellable? |
|---------|-------------|----------|-------------|
| Standard RI | Fixed instance family/size/region | 60-70% | YES (RI Marketplace) |
| Convertible RI | Can change family, OS, tenancy | 45-54% | NO |
| Scheduled RI | Specific time windows | ~5-10% | NO |

### Savings Plans

**Savings Plans** are more flexible than Reserved Instances:

| Plan Type | Commitment | Flexibility | Discount |
|-----------|------------|-------------|----------|
| Compute Savings Plan | $/hour for 1-3yr | Any instance family, region, OS, tenancy | Up to 66% |
| EC2 Instance Savings Plan | $/hour for instance family in region | Any size/OS within family | Up to 72% |
| SageMaker Savings Plan | $/hour | SageMaker usage | Up to 64% |

```bash
# See what Savings Plans would save you
aws ce get-savings-plans-purchase-recommendation \
  --savings-plans-type COMPUTE_SP \
  --term-in-years ONE_YEAR \
  --payment-option NO_UPFRONT \
  --lookback-period-in-days SIXTY_DAYS \
  --query 'SavingsPlansPurchaseRecommendation.SavingsPlansPurchaseRecommendationDetails[*].[
    SavingsPlansDetails.Type,
    SavingsPlansDetails.HourlyCommitment,
    EstimatedSavingsAmount,
    EstimatedSavingsPercentage
  ]' --output table
```

### Spot Instance Best Practices

```bash
# Launch a Spot Instance with fallback to On-Demand
aws ec2 run-instances \
  --launch-template LaunchTemplateId=lt-0abc123,Version=1 \
  --instance-market-options '{
    "MarketType": "spot",
    "SpotOptions": {
      "MaxPrice": "0.05",
      "SpotInstanceType": "one-time",
      "InstanceInterruptionBehavior": "terminate"
    }
  }'

# Use a Spot Fleet for diverse instance types (more availability)
aws ec2 request-spot-fleet \
  --spot-fleet-request-config '{
    "IamFleetRole": "arn:aws:iam::123456789012:role/AmazonEC2SpotFleetRole",
    "AllocationStrategy": "priceCapacityOptimized",
    "TargetCapacity": 10,
    "LaunchSpecifications": [
      {"InstanceType": "c5.xlarge", "ImageId": "ami-0abc123"},
      {"InstanceType": "c5a.xlarge", "ImageId": "ami-0abc123"},
      {"InstanceType": "c4.xlarge", "ImageId": "ami-0abc123"},
      {"InstanceType": "m5.xlarge", "ImageId": "ami-0abc123"}
    ]
  }'

# Handle Spot interruption gracefully in your application
# AWS sends a 2-minute warning via EC2 metadata
TERMINATION=$(curl -s http://169.254.169.254/latest/meta-data/spot/termination-time)
if [ "$TERMINATION" != "" ]; then
  echo "Spot interruption at $TERMINATION — saving checkpoint..."
  # Save work, drain queue, checkpoint state
fi
```

---

## 11.3 AWS Cost Explorer — Visualize and Analyze Spending

```bash
# Get last 3 months of spending by service
aws ce get-cost-and-usage \
  --time-period Start=2024-01-01,End=2024-04-01 \
  --granularity MONTHLY \
  --metrics BlendedCost \
  --group-by Type=DIMENSION,Key=SERVICE \
  --query 'ResultsByTime[*].[TimePeriod.Start,Groups[*].[Keys[0],Metrics.BlendedCost.Amount]]' \
  --output table

# Find your most expensive EC2 instances
aws ce get-cost-and-usage \
  --time-period Start=2024-03-01,End=2024-04-01 \
  --granularity MONTHLY \
  --metrics UsageQuantity BlendedCost \
  --filter '{
    "Dimensions": {
      "Key": "SERVICE",
      "Values": ["Amazon EC2"]
    }
  }' \
  --group-by Type=DIMENSION,Key=INSTANCE_TYPE \
  --output table
```

---

## 11.4 AWS Budgets — Prevent Surprise Bills

### What are AWS Budgets?

**AWS Budgets** lets you set spending thresholds and receive alerts when you approach or exceed them — BEFORE you get a surprise bill.

**Budget types:**
- **Cost Budget:** Alert when spending exceeds threshold
- **Usage Budget:** Alert when usage exceeds threshold (EC2 hours, data transfer GB)
- **Reservation Budget:** Track Reserved Instance utilization
- **Savings Plans Budget:** Track Savings Plans coverage

```bash
# Create a monthly budget with alerts at 80% and 100%
aws budgets create-budget \
  --account-id 123456789012 \
  --budget '{
    "BudgetName": "Monthly-Production-Budget",
    "BudgetLimit": {"Amount": "1000", "Unit": "USD"},
    "TimeUnit": "MONTHLY",
    "BudgetType": "COST",
    "CostFilters": {
      "TagKeyValue": ["user:Environment$production"]
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
      "Subscribers": [{
        "SubscriptionType": "EMAIL",
        "Address": "finops-team@company.com"
      }]
    },
    {
      "Notification": {
        "NotificationType": "FORECASTED",
        "ComparisonOperator": "GREATER_THAN",
        "Threshold": 100,
        "ThresholdType": "PERCENTAGE"
      },
      "Subscribers": [{
        "SubscriptionType": "SNS",
        "Address": "arn:aws:sns:us-east-1:123456789012:billing-alerts"
      }]
    }
  ]'
```

---

## 11.5 AWS Compute Optimizer — Right-Sizing

### What is Compute Optimizer?

**AWS Compute Optimizer** uses machine learning to analyze your EC2 instance utilization and recommends the optimal instance type.

**The Problem it Solves:**
```
Many teams overprovision "just in case":
  Running: r5.4xlarge ($1.008/hour) — 16 vCPU, 128 GB RAM
  Actual usage: 2 vCPU, 8 GB RAM (12.5% CPU, 6.25% Memory utilization)
  
  Compute Optimizer recommendation: t3.xlarge ($0.1664/hour) — 4 vCPU, 16 GB RAM
  Savings: $0.84/hour = $607/month per instance!
  
  If you have 50 such instances: $30,380/month savings!
```

```bash
# Get EC2 instance recommendations
aws compute-optimizer get-ec2-instance-recommendations \
  --account-ids 123456789012 \
  --filters Name=Finding,Values=NotOptimized \
  --query 'instanceRecommendations[*].[
    instanceArn,
    finding,
    currentInstanceType,
    recommendationOptions[0].instanceType,
    recommendationOptions[0].estimatedMonthlySavings.value
  ]' --output table

# Get Lambda function recommendations
aws compute-optimizer get-lambda-function-recommendations \
  --filters Name=Finding,Values=NotOptimized \
  --query 'lambdaFunctionRecommendations[*].[
    functionArn,
    finding,
    memorySizeRecommendationOptions[0].memorySize,
    memorySizeRecommendationOptions[0].projectedUtilizationMetrics[0].value
  ]' --output table
```

---

## 11.6 Cost Allocation Tags

### How to Understand What's Costing Money

Without tags, your AWS bill shows services (EC2, RDS, S3) but not which PROJECT or TEAM is spending what.

With **Cost Allocation Tags**, you can split your bill by:
- Team (Engineering, Marketing, Data Science)
- Project (Project-Alpha, Project-Beta)
- Environment (Production, Staging, Development)
- Customer (TenantA, TenantB for SaaS)

```bash
# Activate cost allocation tags in AWS Billing Console
aws ce create-cost-category-definition \
  --name "Team" \
  --rule-version "CostCategoryExpression.v1" \
  --rules '[
    {
      "Value": "Engineering",
      "Rule": {"Tags": {"Key": "Team", "Values": ["engineering", "eng", "backend"]}}
    },
    {
      "Value": "DataScience",
      "Rule": {"Tags": {"Key": "Team", "Values": ["data-science", "ml", "ai"]}}
    }
  ]'

# Apply cost tags consistently to all resources
aws ec2 create-tags \
  --resources i-0abc123 i-0def456 \
  --tags \
    Key=Team,Value=engineering \
    Key=Project,Value=payment-service \
    Key=Environment,Value=production \
    Key=CostCenter,Value=CC-12345

# Enforce tagging with AWS Config rule
aws configservice put-config-rule \
  --config-rule '{
    "ConfigRuleName": "required-tags",
    "Source": {
      "Owner": "AWS",
      "SourceIdentifier": "REQUIRED_TAGS"
    },
    "InputParameters": "{\"tag1Key\":\"Team\",\"tag2Key\":\"Environment\",\"tag3Key\":\"Project\"}"
  }'
```

---

## 11.7 S3 Cost Optimization

### Understanding S3 Storage Class Costs

```
Data lifecycle example: User uploads a photo:

Day 1-30:   User actively views photo
  → Use: S3 Standard ($0.023/GB/month)

Day 31-90:  User rarely accesses photo  
  → Use: S3 Standard-IA ($0.0125/GB/month)  — 46% cheaper
  Note: IA = Infrequent Access; $0.01/GB retrieval fee

Day 91-180: Photo rarely accessed
  → Use: S3 Glacier Instant Retrieval ($0.004/GB/month) — 83% cheaper
  Note: Millisecond retrieval still possible

Day 181+:   Photo archived, compliance only
  → Use: S3 Glacier Flexible Retrieval ($0.0036/GB/month)
  Note: 3-5 hours retrieval time

Day 365+:   Long-term archive
  → Use: S3 Glacier Deep Archive ($0.00099/GB/month) — 96% cheaper than Standard!
  Note: 12 hour retrieval time
```

```yaml
# S3 Lifecycle Policy — automatically move data between tiers
aws s3api put-bucket-lifecycle-configuration \
  --bucket my-application-data \
  --lifecycle-configuration '{
    "Rules": [{
      "ID": "move-to-cheaper-storage",
      "Status": "Enabled",
      "Filter": {"Prefix": "uploads/"},
      "Transitions": [
        {"Days": 30, "StorageClass": "STANDARD_IA"},
        {"Days": 90, "StorageClass": "GLACIER_IR"},
        {"Days": 365, "StorageClass": "GLACIER"}
      ],
      "Expiration": {"Days": 2555},
      "NoncurrentVersionExpiration": {"NoncurrentDays": 90}
    }]
  }'
```

---

## 11.8 Performance Optimization

### ElastiCache — Reduce Database Load

```
Problem: Every page load queries the database
  100 users/second × 5 queries each = 500 database queries/second
  Database is overloaded, slow, expensive

Solution: Cache frequently read data in ElastiCache (Redis/Memcached)
  First request: Check cache (miss) → query database → store in cache
  Next 1000 requests: Check cache (hit) → return from RAM in microseconds
  
Result: Database goes from 500 q/s to 50 q/s (90% reduction)
        Response time: 200ms → 2ms (cache hit)
```

### CloudFront — Serve Static Content Globally

```
Without CloudFront:
  User in Tokyo → travels to US-East server (150ms latency)
  
With CloudFront:
  User in Tokyo → Tokyo Edge Location (2ms latency, serving cached content)
  
Also reduces: data transfer costs (CloudFront to internet = $0.085/GB vs EC2 = $0.09/GB)
```

---

## 11.9 AWS Trusted Advisor

**Trusted Advisor** scans your AWS account and provides recommendations across 5 categories:

| Category | What It Checks |
|----------|---------------|
| Cost Optimization | Idle EC2, unused Elastic IPs, unassociated EBS volumes, underutilized RDS |
| Performance | High CPU utilization, CloudFront config, EBS throughput |
| Security | S3 bucket permissions, security group open ports, IAM root account MFA |
| Fault Tolerance | RDS backups, EC2 availability zone balance, EBS snapshots |
| Service Limits | Approaching AWS service quotas (need to request increases?) |

```bash
# Check Trusted Advisor recommendations
aws trustedadvisor list-checks \
  --language en \
  --query 'checks[?category==`cost_optimizing`].[id,name]' \
  --output table

# Get results for a specific check (Idle EC2 Instances)
aws trustedadvisor describe-check-result \
  --check-id Qch7DwouX1 \
  --language en \
  --query 'result.[status,flaggedResources[0:5]]'
```

---

## 11.10 Practice Questions

**Q1:** Your team has a batch data processing workload that runs for 6 hours every night. The job can be restarted from a checkpoint if interrupted. Which EC2 pricing option minimizes cost?

- A) On-Demand Instances
- B) Reserved Instances (1-year, all upfront)
- C) Spot Instances
- D) Dedicated Hosts

**Answer: C**

Explanation: Spot Instances provide up to 90% discount for spare EC2 capacity. This workload is perfect for Spot because: (1) It can tolerate interruptions — checkpointing means the job can resume. (2) It runs at a predictable time (nightly) which can be scheduled during off-peak hours when Spot interruption probability is lower. (3) The 6-hour runtime fits well within typical Spot availability windows. Reserved Instances (B) are for 24/7 workloads — you'd pay 24/7 for only 6 hours/day usage (very wasteful).

---

**Q2:** Your application was accidentally left running in development for a month. To prevent this in the future, what PROACTIVE measure should you implement?

- A) Check AWS Console daily for idle instances
- B) Set AWS Budgets with email alerts at 80% and 100% of monthly budget
- C) Use Trusted Advisor monthly reports
- D) Subscribe to AWS Cost Newsletter

**Answer: B**

Explanation: AWS Budgets with percentage alerts is proactive — it NOTIFIES you BEFORE you exceed your budget. Setting an alert at 80% gives you time to investigate and terminate resources before the full budget is consumed. Daily manual checking (A) is reactive and unreliable. Trusted Advisor (C) is good but not designed for immediate budget alerts. The key word is "proactive" — Budgets fire alerts in near-real-time.

---

**Q3:** AWS Compute Optimizer recommends changing your db.r5.4xlarge RDS instance (CPU: 4% avg, RAM: 15% avg) to db.r5.large. What should you do?

- A) Immediately apply the recommendation without testing
- B) Review the recommendation, test in staging with production-like load, monitor metrics after change
- C) Reject all Compute Optimizer recommendations as they are unreliable
- D) Apply only during business hours for visibility

**Answer: B**

Explanation: Compute Optimizer recommendations are valuable but should be validated before applying to production. The right process is: (1) Review the recommendation — understand WHY it was made (low utilization). (2) Test in staging — apply the smaller instance to a staging environment and run load tests. (3) Apply to production during maintenance window. (4) Monitor after change — watch CPU, RAM, I/O for 1-2 weeks. (5) Rollback if issues arise. Never apply without testing (A) — production performance could degrade during peak loads that weren't captured in the historical metrics Compute Optimizer analyzed.

---

**Q4:** Your company allocates AWS costs to different teams but your bill only shows services (EC2, RDS). How do you split costs by team?

- A) Create separate AWS accounts per team
- B) Activate cost allocation tags, apply team tags to all resources, use Cost Explorer grouped by tag
- C) Download the detailed billing CSV and parse it manually
- D) Contact AWS Support to split the bill

**Answer: B**

Explanation: Cost Allocation Tags are the AWS-native way to split costs by team/project/environment. You: (1) Apply tags like `Team=Engineering` to all resources. (2) Activate these tags as cost allocation tags in Billing Console. (3) Use Cost Explorer with "Group by" on the tag to see per-team spending. (4) Set up per-team budgets. Creating separate accounts (A) works but is expensive to manage and limits resource sharing. Tags are the recommended approach for teams sharing an account.

---

**Q5:** Which S3 storage class should you use for data that is accessed once a month, needs immediate (millisecond) retrieval when accessed, and you want to minimize cost?

- A) S3 Standard
- B) S3 Standard-Infrequent Access (S3 Standard-IA)
- C) S3 Glacier Instant Retrieval
- D) S3 Glacier Deep Archive

**Answer: C**

Explanation: S3 Glacier Instant Retrieval is designed for data accessed once a quarter (or once a month is acceptable) with millisecond retrieval. Key facts: (1) $0.004/GB/month vs Standard's $0.023/GB (83% cheaper). (2) Instant retrieval (milliseconds) unlike Flexible Retrieval (hours). (3) Per-retrieval cost of $0.03/GB, so monthly access is still cost-effective. Standard-IA (B) costs $0.0125/GB and is better for data accessed a few times per month. Glacier Deep Archive (D) has 12-hour retrieval time — doesn't meet "millisecond" requirement.

---

## Chapter 11 Summary

| Service/Concept | Purpose | Key Fact |
|----------------|---------|----------|
| On-Demand | Pay per hour/second | Most flexible; highest cost |
| Reserved Instances | 1-3 year commitment | 40-70% savings; Standard vs Convertible |
| Compute Savings Plan | Flexible RI alternative | Up to 66% off; any instance type/region |
| Spot Instances | Unused EC2 capacity | Up to 90% off; 2-min interruption warning |
| Cost Explorer | Visualize spending | Analyze by service/tag/region |
| AWS Budgets | Prevent surprise bills | Alerts at configurable thresholds |
| Compute Optimizer | Right-sizing | ML-based instance recommendations |
| Cost Allocation Tags | Split costs by team | Tag resources + activate in Billing Console |
| S3 Lifecycle Policies | Tiered storage costs | Automatically move to cheaper classes |
| Trusted Advisor | Multi-category checks | Cost + Security + Performance + Fault Tolerance |
"""

with open(r"e:\fastapi\aws-admin\11_Cost_Performance_Optimization.md", "w", encoding="utf-8") as f:
    f.write(content)

print(f"Written {len(content.splitlines())} lines")
