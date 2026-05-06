
content = r"""# Chapter 8: High Availability & Disaster Recovery
## (Never Go Down — Planning for Failure Before It Happens)

---

## 8.1 Why High Availability and Disaster Recovery Matter

### The Business Impact of Downtime

Before learning the technical solutions, understand WHY this matters:

```
Cost of downtime by industry (per hour):
  E-commerce (Amazon-scale): $220,000/hour
  Financial trading: $5,000,000/hour
  Healthcare: $636,000/hour
  Banking: $597,000/hour
  Small e-commerce: $2,000-$20,000/hour

Plus indirect costs:
  Customer trust lost (hard to measure but huge)
  Regulatory fines (HIPAA violation = up to $50,000/violation)
  SLA penalties (pay customers when you miss uptime targets)
  Employee productivity lost
```

**Example:** Amazon's famous 49-minute outage in 2013 cost an estimated $66,240/minute = $3,245,760 total.

This is why companies invest heavily in HA and DR. The cost of prevention is far less than the cost of the outage.

---

## 8.2 RTO and RPO — The Two Critical Metrics

### Understanding RTO (Recovery Time Objective)

**RTO (Recovery Time Objective)** = How long can your business tolerate being down?

In other words: "If our system fails right now, what is the maximum acceptable downtime?"

```
Example RTO definitions:
  Online banking: RTO = 15 minutes (customers cannot access money — very bad)
  E-commerce: RTO = 1 hour (losing orders = direct revenue loss)
  Internal HR system: RTO = 8 hours (employees can wait until morning)
  Archival reporting: RTO = 24 hours (runs weekly anyway)

More aggressive RTO = more expensive DR solution
```

### Understanding RPO (Recovery Point Objective)

**RPO (Recovery Point Objective)** = How much data can you afford to lose?

In other words: "If our system fails right now, how far back in time can we restore to?"

```
Example RPO definitions:
  Financial transactions: RPO = 0 seconds (CANNOT lose any transaction)
  E-commerce orders: RPO = 5 minutes (might lose a few orders in last 5 min)
  Product catalog: RPO = 1 hour (catalog updates happen infrequently)
  Log archives: RPO = 24 hours (OK to lose a day of logs)

More aggressive RPO = synchronous replication = more expensive
```

**Analogy:**
- **RTO** is like asking: "If our office building burns down, how quickly must we be back in a temporary office?"
- **RPO** is like asking: "How old can our most recent backup of all files be? If the backup is from last week, we lose one week of work."

```
Timeline of a disaster:

t=0   t=1   t=2   t=3   t=4   t=5   t=6   t=7   t=8
│─────│─────│─────│─────│─────│─────│─────│─────│

Last backup      Disaster   System       System
at t=2           at t=5     restored     resumed
                            at t=7       at t=8

RPO = t=5 - t=2 = 3 hours (data between backup and disaster = lost)
RTO = t=8 - t=5 = 3 hours (time from disaster to full recovery)
```

---

## 8.3 DR Strategies — Four Options From Cheap to Expensive

AWS defines four disaster recovery strategies at different cost/complexity points:

### Strategy 1: Backup and Restore (Cheapest, Slowest)

**RTO: Hours to days | RPO: Hours**

```
Normal operation:
  Production → S3 (backups stored)
  
Disaster → restore from backup → provision new infrastructure → restore data
           (hours of manual work, data loss up to last backup)

Cost: Very low — just S3 storage costs for backups
Use when: Small applications, non-critical systems, tight budget
```

**Implementation:**
```bash
# Backup strategy: automated backups to S3
# EC2: Create AMI + EBS snapshots daily
# RDS: Automated backups (free up to DB size)
# DynamoDB: On-demand backups
# S3: Cross-region replication + versioning

# Infrastructure: Store as CloudFormation or Terraform templates in S3
# On DR: aws cloudformation deploy --template-file dr-infrastructure.yaml

# Example: Restore RDS from backup in DR region
aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier restored-db \
  --db-snapshot-identifier arn:aws:rds:us-east-1:123456789012:snapshot:manual-backup-20250120 \
  --db-instance-class db.t3.medium \
  --region us-west-2
```

### Strategy 2: Pilot Light (Small Always-On)

**RTO: Minutes to hours | RPO: Minutes**

```
Normal operation:
  Primary Region (us-east-1):     Full production stack (active)
  DR Region (us-west-2):          Core only — database replication running
                                  (no app servers — pilot light only)

Disaster in us-east-1:
  1. Promote DR database replica
  2. Launch app servers in DR region (from AMI/launch template)
  3. Update DNS to point to DR region
  Time: 30-60 minutes
  Data loss: Minutes (replication lag)

Cost: Low — only paying for database replication + small core services
```

**Analogy:** Like a pilot light on a gas heater. The flame is tiny (small DB replica), but when you need heat, you turn it up quickly (scale out app servers).

```bash
# Pilot Light Setup: RDS Cross-Region Read Replica
aws rds create-db-instance-read-replica \
  --db-instance-identifier dr-mysql-replica \
  --source-db-instance-identifier arn:aws:rds:us-east-1:123456789012:db:production-mysql \
  --db-instance-class db.t3.medium \
  --region us-west-2

# DR Activation Script (run when disaster declared)
activate_pilot_light() {
  DR_REGION="us-west-2"
  
  echo "1. Promoting DR database to standalone..."
  aws rds promote-read-replica \
    --db-instance-identifier dr-mysql-replica \
    --region $DR_REGION
  
  echo "2. Waiting for promotion to complete..."
  aws rds wait db-instance-available \
    --db-instance-identifier dr-mysql-replica \
    --region $DR_REGION
  
  echo "3. Launching application servers from pre-built AMI..."
  aws autoscaling set-desired-capacity \
    --auto-scaling-group-name dr-app-asg \
    --desired-capacity 4 \
    --region $DR_REGION
  
  echo "4. Updating Route 53 DNS to DR region..."
  aws route53 change-resource-record-sets \
    --hosted-zone-id ZXXXXXXXXXXXXX \
    --change-batch '{
      "Changes": [{
        "Action": "UPSERT",
        "ResourceRecordSet": {
          "Name": "app.company.com",
          "Type": "A",
          "AliasTarget": {
            "HostedZoneId": "Z35SXDOTRQ7X7K",
            "DNSName": "dr-region-alb.us-west-2.elb.amazonaws.com",
            "EvaluateTargetHealth": true
          }
        }
      }]
    }'
    
  echo "DR activation complete. Monitor: https://app.company.com"
}
```

### Strategy 3: Warm Standby (Scaled-Down Copy Running)

**RTO: Minutes | RPO: Seconds to minutes**

```
Normal operation:
  Primary Region (us-east-1):     Full production stack (full capacity)
  DR Region (us-west-2):          Reduced capacity stack (running at min capacity)
                                  App servers: 2 instances (min)
                                  Database: Replica running
                                  Load balancer: Active (no traffic normally)

Disaster in us-east-1:
  1. Fail over Route 53 DNS to DR region (automatic or 1 click)
  2. Scale up DR ASG to full capacity
  Time: 5-10 minutes
  Data loss: Seconds (synchronous or near-synchronous replication)

Cost: Medium — running scaled-down infrastructure constantly
     ~30-50% of production cost for the DR environment
```

```bash
# Warm Standby: Keep reduced stack running in DR region
# Minimum viable infrastructure running in us-west-2:

# 2 app servers instead of production's 10
aws autoscaling update-auto-scaling-group \
  --auto-scaling-group-name dr-app-asg \
  --min-size 2 \
  --desired-capacity 2 \
  --max-size 20 \
  --region us-west-2

# Scale up on DR activation
scale_up_warm_standby() {
  aws autoscaling update-auto-scaling-group \
    --auto-scaling-group-name dr-app-asg \
    --min-size 6 \
    --desired-capacity 10 \
    --max-size 30 \
    --region us-west-2
  echo "Scaled up DR environment to full capacity"
}
```

### Strategy 4: Multi-Site Active-Active (Highest Availability)

**RTO: Near-zero | RPO: Near-zero**

```
Normal operation:
  Region us-east-1: 50% of traffic (ACTIVE)
  Region us-west-2: 50% of traffic (ACTIVE)
  
  Route 53 distributes traffic between both regions.
  Both regions have identical full-capacity infrastructure.
  Data is replicated synchronously or with near-zero lag.

Disaster in us-east-1:
  Route 53 health checks detect failure
  Automatically routes 100% traffic to us-west-2
  Time: 60 seconds (DNS TTL) to instant (with health checks)
  Data loss: Near-zero (synchronous replication)

Cost: 2x production cost (two full copies of everything running)
Use when: Zero tolerance for downtime (financial services, healthcare life support)
```

```bash
# Route 53 latency routing + health checks for multi-site active-active
# Primary region health check
aws route53 create-health-check \
  --caller-reference us-east-1-$(date +%s) \
  --health-check-config '{
    "FullyQualifiedDomainName": "app-us-east-1.company.com",
    "Port": 443,
    "Type": "HTTPS",
    "ResourcePath": "/health",
    "RequestInterval": 10,
    "FailureThreshold": 3,
    "MeasureLatency": true,
    "Regions": ["us-east-1", "eu-west-1", "ap-southeast-1"]
  }'

# Latency-based routing with failover to healthy region
aws route53 change-resource-record-sets \
  --hosted-zone-id ZXXXXXXXXXXXXX \
  --change-batch '{
    "Changes": [{
      "Action": "CREATE",
      "ResourceRecordSet": {
        "Name": "app.company.com",
        "Type": "A",
        "Region": "us-east-1",
        "SetIdentifier": "us-east-1",
        "HealthCheckId": "hc-us-east-1-id",
        "AliasTarget": {
          "HostedZoneId": "Z35SXDOTRQ7X7K",
          "DNSName": "us-east-1-alb.us-east-1.elb.amazonaws.com",
          "EvaluateTargetHealth": true
        }
      }
    }]
  }'
```

### DR Strategy Comparison

| Strategy | RTO | RPO | Cost | Complexity |
|----------|-----|-----|------|------------|
| Backup & Restore | Hours | Hours | $ | Low |
| Pilot Light | Minutes-Hours | Minutes | $$ | Medium |
| Warm Standby | Minutes | Seconds-Minutes | $$$ | Medium-High |
| Multi-Site Active-Active | Seconds | Near-zero | $$$$ | High |

---

## 8.4 Route 53 Routing Policies — Global Traffic Management

### What is Route 53?

**Route 53** is AWS's DNS service. DNS (Domain Name System) translates domain names (company.com) to IP addresses. Route 53 does much more than just DNS — it can route traffic intelligently.

### Routing Policy Types

**Simple Routing:**
```
Use: Single resource, no health checks
Example: company.com → 54.100.200.10
Result: Returns the value, no intelligence
```

**Failover Routing:**
```
Use: Active/passive DR
Primary: us-east-1 ALB (serve traffic normally)
Secondary: us-west-2 ALB (only used if primary fails health check)

Route 53 checks primary's health every 30 seconds.
If primary fails health check: Automatically routes to secondary
```

**Latency-Based Routing:**
```
Use: Multi-region, route users to lowest-latency region
Example:
  User in Tokyo → Route 53 measures latency → ap-northeast-1 is fastest → route there
  User in New York → Route 53 measures → us-east-1 is fastest → route there

"Latency" here is measured by Route 53 based on network data, not real-time measurement
```

**Geolocation Routing:**
```
Use: Route users by their geographic location (country or continent)
Example:
  Users in EU → eu-west-1 (for GDPR compliance, data stays in EU)
  Users in Asia → ap-southeast-1
  Default → us-east-1

Note: Based on WHERE the user's IP is registered, not where they actually are (VPN can trick it)
```

**Geoproximity Routing (Traffic Flow only):**
```
Use: Route traffic based on geographic location with configurable bias
Bias: +50 → attract more traffic to this region
      -50 → send traffic away from this region
Example: Gradually shift traffic from old region to new region by increasing bias
```

**Weighted Routing:**
```
Use: Distribute traffic by percentage (A/B testing, gradual deployments)
Example:
  app-v1 → weight 90 (90% of traffic)
  app-v2 → weight 10 (10% of traffic)
  
Use for canary deployments: deploy new version, send 1% traffic, monitor, increase gradually
```

**Multi-Value Answer:**
```
Use: Multiple values with health checks (simple load balancing via DNS)
Returns up to 8 healthy records
Client picks one at random
NOT a substitute for a real load balancer — just returns multiple IPs
```

```bash
# Set up Route 53 failover routing with health checks
# Step 1: Create health check for primary
PRIMARY_HC=$(aws route53 create-health-check \
  --caller-reference primary-$(date +%s) \
  --health-check-config '{
    "FullyQualifiedDomainName": "primary.company.com",
    "Port": 443,
    "Type": "HTTPS_STR_MATCH",
    "SearchString": "healthy",
    "ResourcePath": "/health",
    "RequestInterval": 30,
    "FailureThreshold": 3
  }' \
  --query 'HealthCheck.Id' --output text)

# Step 2: Create PRIMARY record
aws route53 change-resource-record-sets \
  --hosted-zone-id ZXXXXXXXXXXXXX \
  --change-batch '{
    "Changes": [{
      "Action": "CREATE",
      "ResourceRecordSet": {
        "Name": "app.company.com",
        "Type": "A",
        "Failover": "PRIMARY",
        "SetIdentifier": "primary-us-east-1",
        "HealthCheckId": "'$PRIMARY_HC'",
        "TTL": 60,
        "ResourceRecords": [{"Value": "54.100.200.10"}]
      }
    }, {
      "Action": "CREATE",
      "ResourceRecordSet": {
        "Name": "app.company.com",
        "Type": "A",
        "Failover": "SECONDARY",
        "SetIdentifier": "secondary-us-west-2",
        "TTL": 60,
        "ResourceRecords": [{"Value": "52.200.100.50"}]
      }
    }]
  }'
```

---

## 8.5 Database High Availability Patterns

### RDS Multi-AZ (Automatic Failover)

```
Normal: App → Primary RDS (AZ-1) → Standby RDS (AZ-2) [synchronous replication]
        App writes to Primary ONLY. Standby is passive — not accessible.
        
Failure of Primary (hardware, AZ outage):
  1. RDS detects failure (within seconds)
  2. Promotes standby to new primary
  3. Updates DNS endpoint to point to new primary
  4. App reconnects using same endpoint URL (no code change)
  
Failover time: 60-120 seconds
Data loss: Zero (synchronous replication)
```

### Aurora Global Database (Cross-Region DR)

```
Primary Region (us-east-1):
  Aurora Cluster → reads and writes

Secondary Region (us-west-2):
  Aurora Cluster → reads only
  Replication lag: < 1 second typically

DR scenario: Promote secondary to primary in < 1 minute
```

### DynamoDB Global Tables

```
DynamoDB Global Tables: Multi-region, multi-active
  us-east-1: reads and writes
  eu-west-1: reads and writes
  ap-southeast-1: reads and writes
  
  Data replicated to all regions in < 1 second
  If any region fails: other regions continue serving reads AND writes
  
Setup:
aws dynamodb create-global-table \
  --global-table-name global-products \
  --replication-group RegionName=us-east-1 RegionName=eu-west-1 RegionName=ap-southeast-1
```

---

## 8.6 Chaos Engineering — Testing Your HA Proactively

### What is Chaos Engineering?

**Chaos Engineering** is the practice of intentionally introducing failures into your system to verify it handles them gracefully. If you never test your DR procedures, you cannot be confident they work when you need them.

**Famous example:** Netflix's Chaos Monkey — a tool that randomly terminates EC2 instances in production. Netflix built it to force their engineers to design resilient systems. If an instance can be killed at any moment, you must design so that does not matter.

### AWS Fault Injection Simulator (FIS)

**AWS Fault Injection Simulator (FIS)** is a managed chaos engineering service that lets you run controlled fault experiments.

```bash
# Create a FIS experiment to kill random EC2 instances
cat > /tmp/fis-experiment.json << 'EOF'
{
  "description": "Test ASG auto-healing by terminating random instances",
  "actions": {
    "terminate-instances": {
      "actionId": "aws:ec2:terminate-instances",
      "parameters": {
        "count": "2"
      },
      "targets": {
        "Instances": "app-servers"
      }
    }
  },
  "targets": {
    "app-servers": {
      "resourceType": "aws:ec2:instance",
      "resourceTags": {
        "Environment": "staging",
        "Chaos": "enabled"
      },
      "selectionMode": "RANDOM",
      "filters": [{
        "path": "State.Name",
        "values": ["running"]
      }]
    }
  },
  "stopConditions": [{
    "source": "aws:cloudwatch:alarm",
    "value": "arn:aws:cloudwatch:us-east-1:123456789012:alarm:web-app-critical"
  }],
  "roleArn": "arn:aws:iam::123456789012:role/FISExperimentRole",
  "tags": {"Name": "asg-resilience-test"}
}
EOF

# Create the experiment template
aws fis create-experiment-template \
  --cli-input-json file:///tmp/fis-experiment.json

# Run the experiment
aws fis start-experiment \
  --experiment-template-id EXTxxxxxxxxxxxx
  
# Monitor: watch if ASG replaces terminated instances within 5 minutes
```

---

## 8.7 Backup Strategies — Protecting Data

### AWS Backup — The Central Backup Hub

**AWS Backup** provides centralized management of backups across multiple services. It enforces backup policies using **Backup Plans**.

```bash
# Create a backup vault (encrypted container)
aws backup create-backup-vault \
  --backup-vault-name production-backup-vault \
  --encryption-key-arn arn:aws:kms:us-east-1:123456789012:key/backup-key

# Create a backup plan
PLAN_JSON='{
  "BackupPlanName": "production-backup-plan",
  "Rules": [
    {
      "RuleName": "daily-7-day-retention",
      "TargetBackupVaultName": "production-backup-vault",
      "ScheduleExpression": "cron(0 2 * * ? *)",
      "StartWindowMinutes": 60,
      "CompletionWindowMinutes": 180,
      "Lifecycle": {
        "DeleteAfterDays": 7
      }
    },
    {
      "RuleName": "weekly-1-month-retention",
      "TargetBackupVaultName": "production-backup-vault",
      "ScheduleExpression": "cron(0 3 ? * SUN *)",
      "Lifecycle": {
        "MoveToColdStorageAfterDays": 14,
        "DeleteAfterDays": 30
      }
    },
    {
      "RuleName": "monthly-1-year-retention",
      "TargetBackupVaultName": "production-backup-vault",
      "ScheduleExpression": "cron(0 4 1 * ? *)",
      "Lifecycle": {
        "MoveToColdStorageAfterDays": 30,
        "DeleteAfterDays": 365
      }
    }
  ]
}'

PLAN_ID=$(aws backup create-backup-plan \
  --backup-plan "$PLAN_JSON" \
  --query 'BackupPlanId' --output text)

# Tag all production resources with Backup=true, then assign by tag
aws backup create-backup-selection \
  --backup-plan-id $PLAN_ID \
  --backup-selection '{
    "SelectionName": "all-production-resources",
    "IamRoleArn": "arn:aws:iam::123456789012:role/AWSBackupDefaultServiceRole",
    "ListOfTags": [{
      "ConditionType": "STRINGEQUALS",
      "ConditionKey": "Environment",
      "ConditionValue": "production"
    }]
  }'
```

### Backup Vault Lock — WORM for Backups

**Backup Vault Lock** prevents anyone from deleting backups before their retention period expires. Even root cannot delete a locked backup.

```bash
# Lock the backup vault (WORM for backups)
aws backup put-backup-vault-lock-configuration \
  --backup-vault-name production-backup-vault \
  --min-retention-days 7 \
  --max-retention-days 365 \
  --changeable-for-days 3  # Can modify within 3 days; after that — permanent!
  
# WARNING: After changeable-for-days expires, this CANNOT be undone.
# Even root cannot unlock the vault or delete backups before their retention period.
```

---

## 8.8 Practice Questions

**Q1:** Your company requires an RTO of 30 minutes and an RPO of 1 minute for a critical financial application. Which DR strategy is MOST appropriate?

- A) Backup and Restore
- B) Pilot Light
- C) Warm Standby
- D) Multi-Site Active-Active

**Answer: C**

Explanation: Warm Standby keeps a scaled-down but fully functional copy of the application running in the DR region with a database replica. RTO is 5-15 minutes (scale up the app servers + DNS failover), and RPO is seconds to minutes (near-synchronous DB replication). Backup & Restore (A) has hours RTO. Pilot Light (B) has 30-60 min RTO (need to launch app servers from scratch). Multi-Site Active-Active (D) would work but costs significantly more for requirements that can be met with Warm Standby.

---

**Q2:** You have a Route 53 weighted routing policy with two records: Record A (weight 90) and Record B (weight 10). Record A's EC2 instance is terminated. What percentage of traffic goes to Record B?

- A) 10%
- B) 50%
- C) 100%
- D) 0% (weighted routing doesn't support failover)

**Answer: C**

Explanation: Weighted routing with health checks: when a health check is configured on Record A and Record A fails, Route 53 calculates weights only from healthy records. With Record A unhealthy, only Record B (weight 10) remains healthy, so it receives 100% of traffic. Without health checks, weighted routing distributes even to unhealthy endpoints. This is why always configure health checks with weighted routing.

---

**Q3:** An RDS Multi-AZ database just completed a failover due to AZ failure. How should the application handle the failover?

- A) Update the application's database connection string with the new primary IP
- B) Reconnect to the same endpoint URL — Route 53 automatically updated it
- C) Connect to the standby's endpoint URL
- D) Wait for DBA to manually promote the standby

**Answer: B**

Explanation: RDS provides a single endpoint DNS name (e.g., mydb.cluster-xxx.us-east-1.rds.amazonaws.com) that always points to the current primary. During failover, RDS updates the DNS record to point to the promoted standby. The application uses the same endpoint URL — no configuration change needed. The application must handle the brief TCP disconnection (reconnect) but should NOT need IP address or endpoint URL changes. This is why you should never hardcode IP addresses for RDS.

---

**Q4:** What is the key difference between RTO and RPO?

- A) RTO is about cost; RPO is about time
- B) RTO is how long the system can be down; RPO is how much data can be lost
- C) RTO is for databases; RPO is for applications
- D) RTO is measured in MB; RPO is measured in seconds

**Answer: B**

Explanation: RTO (Recovery Time Objective) defines how long your business can tolerate the system being unavailable — the maximum acceptable downtime after a disaster. RPO (Recovery Point Objective) defines how much data loss is acceptable — how far back in time you can restore to. If you have hourly backups and a 4-hour RPO, you can lose up to 4 hours of data. If you need RPO = 0, you need synchronous replication.

---

**Q5:** You need to implement automated DR testing quarterly to verify your runbooks work. Which AWS service should you use to inject controlled failures?

- A) AWS Config Rules with auto-remediation
- B) AWS Fault Injection Simulator (FIS)
- C) Amazon Inspector
- D) AWS Shield

**Answer: B**

Explanation: AWS Fault Injection Simulator (FIS) is specifically designed for chaos engineering and DR testing. You create experiment templates that inject specific failures (terminate instances, inject CPU stress, add network latency, make API calls fail) in a controlled and safe way. Stop conditions automatically halt experiments if critical alarms trigger. This lets you test DR procedures quarterly without risking actual production disruption. AWS Config (A) checks compliance, not testing failures.

---

## Chapter 8 Summary

| Concept | Key Facts |
|---------|----------|
| RTO | Max acceptable downtime after disaster; lower = more expensive |
| RPO | Max acceptable data loss; 0 = synchronous replication required |
| Backup & Restore | Hours RTO/RPO; cheapest; restore from S3 backups |
| Pilot Light | Minutes RTO; DB replication running; launch app servers on DR |
| Warm Standby | Minutes RTO; scaled-down live stack in DR; scale up on activation |
| Multi-Site Active-Active | Seconds RTO; full duplicate stack; highest cost |
| Route 53 Failover | Automatic DNS failover using health checks; 60s TTL |
| Route 53 Latency | Route users to lowest-latency region |
| Route 53 Weighted | A/B testing and gradual traffic shifting |
| RDS Multi-AZ | Automatic failover; same endpoint; 60-120s failover time; 0 RPO |
| Aurora Global DB | < 1 second replication; < 1 min failover; cross-region |
| DynamoDB Global Tables | Multi-active multi-region; < 1 sec replication |
| AWS Backup | Centralized backup; cross-service; compliance reporting |
| Backup Vault Lock | WORM backups; cannot delete before retention; even root blocked |
| Chaos Engineering / FIS | Test DR by injecting real failures in controlled manner |
"""

with open(r"e:\fastapi\aws-admin\08_HighAvailability_DisasterRecovery.md", "w", encoding="utf-8") as f:
    f.write(content)

print(f"Written {len(content.splitlines())} lines")
