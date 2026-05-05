# Chapter 8: High Availability, Reliability & Disaster Recovery

## AWS SysOps Administrator Exam Domain Coverage
- **Domain 2**: Reliability and Business Continuity (16% of exam)
- Heavily tested — HA architecture, Route 53 failover, RDS, backup strategies

---

## 8.1 Reliability Fundamentals

### Key Reliability Metrics

| Metric | Definition | Target |
|--------|-----------|--------|
| **RTO** (Recovery Time Objective) | Max acceptable downtime after failure | Minutes to hours |
| **RPO** (Recovery Point Objective) | Max acceptable data loss (time) | Seconds to hours |
| **MTTR** (Mean Time to Recovery) | Average time to restore service | Minimize |
| **MTBF** (Mean Time Between Failures) | Average time between failures | Maximize |

```
Cost vs RTO/RPO Trade-off:

        High Cost
             │
  Active-    │   ◄── Fastest recovery, most expensive
  Active     │       RTO: ~0, RPO: ~0
  Multi-     │
  Region     │
             │
  Warm       │   ◄── Pre-provisioned standby
  Standby    │       RTO: minutes, RPO: seconds
             │
  Pilot      │   ◄── Minimal resources running
  Light      │       RTO: 10s minutes, RPO: minutes
             │
  Backup &   │   ◄── Cheapest, slowest recovery
  Restore    │       RTO: hours, RPO: hours
             │
        Low Cost─────────────────────────► High Cost
```

---

## 8.2 Availability Zones — Building Fault Tolerance

### The Rule: Deploy Across Minimum 2 AZs

```
SINGLE AZ (Bad):                    MULTI-AZ (Good):
┌─────────────────┐                ┌──────┐   ┌──────┐
│    AZ-1         │                │ AZ-1 │   │ AZ-2 │
│  ┌──────────┐   │                │  EC2 │   │  EC2 │
│  │   ALB    │   │   AZ failure   │  EC2 │   │  EC2 │
│  │  EC2 x3  │   │   ───────►     │      │   │      │
│  │  RDS     │   │  FULL OUTAGE!  │  ALB │   │  ALB │
│  └──────────┘   │                │  RDS │   │  RDS │
└─────────────────┘                │      │   │Standby│
                                   └──────┘   └──────┘
                                     Partial failure = partial service
```

### Health Checks — The Foundation of HA

**ALB Health Checks:**
```bash
# Configure health check on target group
aws elbv2 modify-target-group \
  --target-group-arn arn:aws:elasticloadbalancing:... \
  --health-check-protocol HTTP \
  --health-check-path /health \
  --health-check-interval-seconds 15 \
  --healthy-threshold-count 2 \
  --unhealthy-threshold-count 3 \
  --health-check-timeout-seconds 5
```

**Application Health Endpoint:**
```python
from fastapi import FastAPI
import boto3
import psycopg2

app = FastAPI()

@app.get("/health", include_in_schema=False)
async def health_check():
    """Comprehensive health check endpoint for ALB/Route 53."""
    checks = {}
    
    # Check database connectivity
    try:
        conn = get_db_connection()
        conn.execute("SELECT 1")
        checks['database'] = 'healthy'
    except Exception as e:
        checks['database'] = f'unhealthy: {str(e)}'
    
    # Check cache connectivity
    try:
        redis_client.ping()
        checks['cache'] = 'healthy'
    except Exception as e:
        checks['cache'] = f'unhealthy: {str(e)}'
    
    # Check external dependencies
    checks['version'] = '1.2.3'
    checks['region'] = get_instance_region()
    
    # Return 200 if all critical checks pass
    if all(v == 'healthy' for k, v in checks.items() if k not in ['version', 'region']):
        return {'status': 'healthy', **checks}
    else:
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=503,
            content={'status': 'unhealthy', **checks}
        )
```

---

## 8.3 Route 53 for High Availability

### DNS-Based Failover Architecture

```
               Route 53
                  │
         ┌────────┴────────┐
         │  Failover Policy│
         └────────┬────────┘
                  │
        ┌─────────┴─────────┐
        │                   │
   PRIMARY (Active)    SECONDARY (Standby)
   us-east-1 ALB       us-west-2 ALB
   Health Check OK      (Only used if primary fails)
```

```bash
# Create health check for primary region
PRIMARY_HC=$(aws route53 create-health-check \
  --caller-reference $(date +%s) \
  --health-check-config '{
    "Type": "HTTPS",
    "FullyQualifiedDomainName": "primary-alb.us-east-1.elb.amazonaws.com",
    "Port": 443,
    "ResourcePath": "/health",
    "RequestInterval": 10,
    "FailureThreshold": 2,
    "EnableSNI": true
  }' \
  --query HealthCheck.Id --output text)

# Primary failover record
aws route53 change-resource-record-sets \
  --hosted-zone-id Z123456789 \
  --change-batch '{
    "Changes": [
      {
        "Action": "CREATE",
        "ResourceRecordSet": {
          "Name": "app.example.com",
          "Type": "A",
          "SetIdentifier": "primary-us-east-1",
          "Failover": "PRIMARY",
          "HealthCheckId": "'$PRIMARY_HC'",
          "AliasTarget": {
            "HostedZoneId": "Z35SXDOTRQ7X7K",
            "DNSName": "primary-alb.us-east-1.elb.amazonaws.com",
            "EvaluateTargetHealth": true
          }
        }
      },
      {
        "Action": "CREATE",
        "ResourceRecordSet": {
          "Name": "app.example.com",
          "Type": "A",
          "SetIdentifier": "secondary-us-west-2",
          "Failover": "SECONDARY",
          "AliasTarget": {
            "HostedZoneId": "Z1H1FL5HABSF5",
            "DNSName": "secondary-alb.us-west-2.elb.amazonaws.com",
            "EvaluateTargetHealth": true
          }
        }
      }
    ]
  }'
```

### Multi-Value Answer Routing (Client-side load balancing)
```bash
# Return multiple IPs — client picks one. If one fails, others returned.
aws route53 change-resource-record-sets \
  --hosted-zone-id Z123456789 \
  --change-batch '{
    "Changes": [
      {
        "Action": "CREATE",
        "ResourceRecordSet": {
          "Name": "api.example.com",
          "Type": "A",
          "SetIdentifier": "server-1",
          "MultiValueAnswer": true,
          "HealthCheckId": "health-check-1",
          "TTL": 30,
          "ResourceRecords": [{"Value": "10.0.1.10"}]
        }
      },
      {
        "Action": "CREATE",
        "ResourceRecordSet": {
          "Name": "api.example.com",
          "Type": "A",
          "SetIdentifier": "server-2",
          "MultiValueAnswer": true,
          "HealthCheckId": "health-check-2",
          "TTL": 30,
          "ResourceRecords": [{"Value": "10.0.2.10"}]
        }
      }
    ]
  }'
```

---

## 8.4 Elastic Load Balancer for HA

### ALB Across Multiple AZs
```
Internet
   │
   ▼
┌──────────────────────────────────────────────┐
│        Application Load Balancer             │
│  (spans multiple AZs automatically)          │
│                                              │
│  AZ-1 node         AZ-2 node     AZ-3 node  │
└──────┬─────────────────┬──────────────┬──────┘
       │                 │              │
  ┌────┴────┐       ┌────┴────┐    ┌────┴────┐
  │ Target  │       │ Target  │    │ Target  │
  │ Group   │       │ Group   │    │ Group   │
  │ (AZ-1)  │       │ (AZ-2)  │    │ (AZ-3)  │
  └─────────┘       └─────────┘    └─────────┘
```

**Cross-Zone Load Balancing:**
- **ALB**: Enabled by default (distributes to all healthy targets across all AZs)
- **NLB**: Disabled by default (enable for even distribution)

```bash
# Enable cross-zone load balancing on NLB
aws elbv2 modify-load-balancer-attributes \
  --load-balancer-arn arn:aws:elasticloadbalancing:... \
  --attributes Key=load_balancing.cross_zone.enabled,Value=true
```

### Sticky Sessions (Session Affinity)
```bash
# Enable sticky sessions with duration
aws elbv2 modify-target-group-attributes \
  --target-group-arn arn:aws:elasticloadbalancing:... \
  --attributes \
    Key=stickiness.enabled,Value=true \
    Key=stickiness.type,Value=lb_cookie \
    Key=stickiness.lb_cookie.duration_seconds,Value=86400

# ALB also supports app-based stickiness (uses your app's cookie)
aws elbv2 modify-target-group-attributes \
  --target-group-arn arn:aws:elasticloadbalancing:... \
  --attributes \
    Key=stickiness.enabled,Value=true \
    Key=stickiness.type,Value=app_cookie \
    Key=stickiness.app_cookie.cookie_name,Value=MYSESSION \
    Key=stickiness.app_cookie.duration_seconds,Value=3600
```

> **SysOps Note:** Sticky sessions reduce availability. Prefer stateless applications that store sessions in ElastiCache or DynamoDB.

---

## 8.5 Auto Scaling for Resilience

### Auto Scaling Group High Availability Settings

```bash
# ASG spanning 3 AZs with minimum 2 healthy instances
aws autoscaling create-auto-scaling-group \
  --auto-scaling-group-name web-ha-asg \
  --launch-template LaunchTemplateName=WebTemplate,Version='$Latest' \
  --min-size 2 \            # Never go below 2 (1 per AZ minimum)
  --max-size 10 \
  --desired-capacity 4 \
  --vpc-zone-identifier "subnet-az1,subnet-az2,subnet-az3" \
  --target-group-arns arn:aws:elasticloadbalancing:... \
  --health-check-type ELB \
  --health-check-grace-period 300 \
  --default-cooldown 300

# Enable Capacity Rebalancing for Spot instances
aws autoscaling update-auto-scaling-group \
  --auto-scaling-group-name web-ha-asg \
  --capacity-rebalance

# Suspend/resume processes (useful during maintenance)
aws autoscaling suspend-processes \
  --auto-scaling-group-name web-ha-asg \
  --scaling-processes Launch Terminate HealthCheck

# Resume after maintenance
aws autoscaling resume-processes \
  --auto-scaling-group-name web-ha-asg \
  --scaling-processes Launch Terminate HealthCheck
```

### Instance Warm-Up and Pre-Warming
```bash
# Set warm-up time (instance not counted as healthy until warm-up expires)
aws autoscaling modify-instance-metadata-options \
  --auto-scaling-group-name web-ha-asg \
  --default-instance-warmup 120

# Warm Pool — pre-initialized instances ready to launch faster
aws autoscaling put-warm-pool \
  --auto-scaling-group-name web-ha-asg \
  --min-size 2 \
  --pool-state Stopped \  # Or Running (faster but more costly)
  --max-group-prepared-capacity 4
```

---

## 8.6 RDS High Availability

### Multi-AZ Failover Process
```
Normal Operation:
  App → Primary RDS (AZ-1) ←synchronous replication→ Standby (AZ-2)

Failover:
  1. Primary fails (hardware, OS, network, AZ outage)
  2. AWS detects failure (health check)
  3. DNS CNAME flips to standby (~60-120 seconds)
  4. Standby becomes new primary
  5. New standby created in another AZ
  6. App reconnects using same endpoint
```

```bash
# Monitor failover with RDS events
aws rds describe-events \
  --source-identifier prod-postgres \
  --source-type db-instance \
  --event-categories failover \
  --duration 1440

# Subscribe to failover events
aws rds create-event-subscription \
  --subscription-name rds-failover-notification \
  --sns-topic-arn arn:aws:sns:us-east-1:123456789012:ops-alerts \
  --source-type db-instance \
  --event-categories availability failover failure recovery

# Test failover
aws rds reboot-db-instance \
  --db-instance-identifier prod-postgres \
  --force-failover
```

### Aurora Failover (Faster — ~30 seconds)
```bash
# Check current writer
aws rds describe-db-clusters \
  --db-cluster-identifier my-aurora \
  --query 'DBClusters[0].DBClusterMembers[?IsClusterWriter==`true`].DBInstanceIdentifier'

# Manual failover (promotes a specific replica to writer)
aws rds failover-db-cluster \
  --db-cluster-identifier my-aurora \
  --target-db-instance-identifier aurora-replica-2
```

---

## 8.7 Disaster Recovery Strategies

### DR Strategy Comparison

```
┌──────────────────────────────────────────────────────────────────┐
│                  DR STRATEGIES                                    │
│                                                                  │
│  BACKUP & RESTORE           PILOT LIGHT                         │
│  ┌─────────────┐            ┌─────────────┐                     │
│  │ Primary     │            │ Primary     │                     │
│  │ (active)    │            │ (active)    │                     │
│  └──────┬──────┘            └──────┬──────┘                     │
│         │ backup                   │ replicate data             │
│  ┌──────▼──────┐            ┌──────▼──────┐                     │
│  │ S3/Glacier  │            │ DR Region   │                     │
│  │ (data only) │            │ (data only, │                     │
│  └─────────────┘            │ minimal EC2)│                     │
│  RTO: hours                 └─────────────┘                     │
│  RPO: hours                 RTO: 10s mins                       │
│  Cost: $                    RPO: minutes                        │
│                             Cost: $$                            │
│                                                                  │
│  WARM STANDBY               ACTIVE-ACTIVE                       │
│  ┌─────────────┐            ┌─────────────┐                     │
│  │ Primary     │            │ Region A    │                     │
│  │ (active)    │            │ (active)    │                     │
│  └──────┬──────┘            └──────┬──────┘                     │
│         │ replicate                │ replicate                  │
│  ┌──────▼──────┐            ┌──────▼──────┐                     │
│  │ DR Region   │            │ Region B    │                     │
│  │ (scaled-    │            │ (active)    │                     │
│  │  down copy) │            └─────────────┘                     │
│  └─────────────┘            RTO: ~0                             │
│  RTO: minutes               RPO: ~0                             │
│  RPO: seconds               Cost: $$$$                         │
│  Cost: $$$                                                      │
└──────────────────────────────────────────────────────────────────┘
```

### Backup & Restore Strategy
```bash
# Cross-region backup strategy using AWS Backup
aws backup create-backup-plan \
  --backup-plan '{
    "BackupPlanName": "cross-region-backup",
    "Rules": [{
      "RuleName": "daily-with-cross-region",
      "TargetBackupVaultName": "primary-vault",
      "ScheduleExpression": "cron(0 5 ? * * *)",
      "StartWindowMinutes": 60,
      "CompletionWindowMinutes": 480,
      "Lifecycle": {
        "DeleteAfterDays": 30
      },
      "CopyActions": [{
        "DestinationBackupVaultArn": "arn:aws:backup:us-west-2:123456789012:backup-vault:dr-vault",
        "Lifecycle": {
          "DeleteAfterDays": 90
        }
      }]
    }]
  }'
```

### Pilot Light Implementation
```
Pilot Light = Core infrastructure running in DR region, minimal capacity
```

```python
import boto3

def activate_pilot_light_dr(scale_factor: float = 1.0):
    """Activate disaster recovery by scaling up pilot light infrastructure."""
    
    ec2 = boto3.client('ec2', region_name='us-west-2')  # DR region
    autoscaling = boto3.client('autoscaling', region_name='us-west-2')
    rds = boto3.client('rds', region_name='us-west-2')
    route53 = boto3.client('route53')
    
    print("🚨 Activating DR - Pilot Light expansion")
    
    # 1. Scale up ASG to full capacity
    autoscaling.update_auto_scaling_group(
        AutoScalingGroupName='dr-web-asg',
        MinSize=4,
        DesiredCapacity=int(8 * scale_factor),
        MaxSize=20
    )
    print("✅ Scaled up ASG in DR region")
    
    # 2. Promote read replica to primary (or promote Aurora secondary)
    rds.promote_read_replica(
        DBInstanceIdentifier='dr-postgres-replica'
    )
    print("✅ Promoting RDS read replica to primary")
    
    # 3. Update Route 53 to point to DR region
    route53.change_resource_record_sets(
        HostedZoneId='Z123456789',
        ChangeBatch={
            'Changes': [{
                'Action': 'UPSERT',
                'ResourceRecordSet': {
                    'Name': 'app.example.com',
                    'Type': 'A',
                    'SetIdentifier': 'primary-us-east-1',
                    'Failover': 'PRIMARY',
                    # Remove health check to force all traffic to DR
                    'AliasTarget': {
                        'HostedZoneId': 'Z1H1FL5HABSF5',
                        'DNSName': 'dr-alb.us-west-2.elb.amazonaws.com',
                        'EvaluateTargetHealth': True
                    }
                }
            }]
        }
    )
    print("✅ Updated Route 53 to DR region")
    
    print("⏳ Waiting for instances to become healthy...")
    # Monitor ASG, wait for instances to register with ALB
```

---

## 8.8 AWS Backup — Centralized Backup Management

```bash
# Create backup vault in DR region
aws backup create-backup-vault \
  --backup-vault-name dr-vault \
  --encryption-key-arn arn:aws:kms:us-west-2:123456789012:key/key-id \
  --region us-west-2

# Create comprehensive backup plan
aws backup create-backup-plan \
  --backup-plan '{
    "BackupPlanName": "production-backup",
    "Rules": [
      {
        "RuleName": "hourly-snapshots",
        "TargetBackupVaultName": "production-vault",
        "ScheduleExpression": "cron(0 * ? * * *)",
        "StartWindowMinutes": 60,
        "CompletionWindowMinutes": 180,
        "Lifecycle": {"DeleteAfterDays": 1}
      },
      {
        "RuleName": "daily-backups",
        "TargetBackupVaultName": "production-vault",
        "ScheduleExpression": "cron(0 5 ? * * *)",
        "Lifecycle": {
          "MoveToColdStorageAfterDays": 30,
          "DeleteAfterDays": 365
        },
        "CopyActions": [{
          "DestinationBackupVaultArn": "arn:aws:backup:us-west-2:123456789012:backup-vault:dr-vault",
          "Lifecycle": {"DeleteAfterDays": 90}
        }]
      },
      {
        "RuleName": "monthly-compliance",
        "TargetBackupVaultName": "production-vault",
        "ScheduleExpression": "cron(0 5 1 * ? *)",
        "Lifecycle": {
          "DeleteAfterDays": 2555
        }
      }
    ]
  }'

# Assign ALL production resources to backup plan (using tags)
aws backup create-backup-selection \
  --backup-plan-id $(aws backup list-backup-plans --query 'BackupPlansList[?BackupPlanName==`production-backup`].BackupPlanId' --output text) \
  --backup-selection '{
    "SelectionName": "all-production",
    "IamRoleArn": "arn:aws:iam::123456789012:role/AWSBackupDefaultServiceRole",
    "ListOfTags": [
      {"ConditionType":"STRINGEQUALS","ConditionKey":"Environment","ConditionValue":"production"}
    ]
  }'

# Test restore (critical — test regularly!)
aws backup start-restore-job \
  --recovery-point-arn arn:aws:backup:us-east-1:123456789012:recovery-point:xxx \
  --iam-role-arn arn:aws:iam::123456789012:role/AWSBackupRestoreRole \
  --resource-type RDS \
  --metadata '{
    "DBInstanceIdentifier": "restored-for-test",
    "DBInstanceClass": "db.t3.medium",
    "Engine": "postgres",
    "StorageType": "gp3",
    "MultiAZ": "false"
  }'
```

---

## 8.9 Elastic Disaster Recovery (DRS)

AWS DRS continuously replicates servers for fast DR with low RPO (~seconds):

```
On-Premises / AWS ──► Replication Agent ──► DRS Staging Area ──► Recovery Instance
                       (continuous block-level             (launched during DR)
                        replication)
```

```bash
# DRS is primarily configured via console, but key CLI operations:

# List source servers being replicated
aws drs describe-source-servers --region us-east-1

# Launch recovery instances
aws drs start-recovery \
  --source-servers '[{"sourceServerID": "s-xxx"}]' \
  --isDrill false

# Disconnect after successful recovery
aws drs disconnect-source-server --source-server-id s-xxx
```

---

## 8.10 Well-Architected Reliability Pillar

### Design Principles for Reliability

**1. Automatically recover from failure:**
```
EC2 AutoRecovery:
aws cloudwatch put-metric-alarm \
  --alarm-name "ec2-auto-recover-prod-1" \
  --namespace AWS/EC2 \
  --metric-name StatusCheckFailed_System \
  --dimensions Name=InstanceId,Value=i-xxx \
  --statistic Minimum \
  --period 60 \
  --evaluation-periods 5 \
  --threshold 1 \
  --comparison-operator GreaterThanOrEqualToThreshold \
  --alarm-actions arn:aws:automate:us-east-1:ec2:recover
```

**2. Test recovery procedures:**
```python
# Game Day automation — simulate failures
import boto3
import random

def simulate_random_failure(asg_name: str):
    """Kill a random instance in ASG to test auto-healing."""
    autoscaling = boto3.client('autoscaling')
    
    # Get running instances
    instances = autoscaling.describe_auto_scaling_groups(
        AutoScalingGroupNames=[asg_name]
    )['AutoScalingGroups'][0]['Instances']
    
    running = [i for i in instances if i['LifecycleState'] == 'InService']
    
    if running:
        victim = random.choice(running)
        print(f"🎯 Killing instance: {victim['InstanceId']}")
        
        autoscaling.terminate_instance_in_auto_scaling_group(
            InstanceId=victim['InstanceId'],
            ShouldDecrementDesiredCapacity=False
        )
        
        print("⏳ Monitor ASG — should auto-replace the instance")
```

**3. Scale horizontally to increase aggregate workload availability:**
- Prefer many small instances over few large ones
- Use ASGs with minimum 2 instances across AZs

**4. Stop guessing capacity:**
```bash
# Use scheduled scaling for known patterns + target tracking for spikes
# Predictive Scaling (ML-based)
aws autoscaling put-scaling-policy \
  --auto-scaling-group-name web-asg \
  --policy-name predictive-scaling \
  --policy-type PredictiveScaling \
  --predictive-scaling-configuration '{
    "MetricSpecifications": [{
      "TargetValue": 50.0,
      "PredefinedMetricPairSpecification": {
        "PredefinedMetricType": "ASGCPUUtilization"
      }
    }],
    "Mode": "ForecastAndScale",
    "SchedulingBufferTime": 300
  }'
```

---

## 8.11 Real-World DR Runbook

### Scenario: Region Failure Response

**Detection:**
1. AWS Health Dashboard shows regional event
2. Route 53 health checks fail for primary endpoints
3. CloudWatch alarms trigger in multiple services
4. On-call engineer receives PagerDuty alert

**Response Steps:**

```bash
#!/bin/bash
# DR Runbook: Primary region failure response
# Run from DR region (us-west-2)

PRIMARY_REGION="us-east-1"
DR_REGION="us-west-2"
HOSTED_ZONE_ID="Z123456789"

echo "🚨 DISASTER RECOVERY ACTIVATION - $(date)"

# Step 1: Confirm primary region is actually down
echo "1. Checking primary region health..."
aws route53 get-health-check-status \
  --health-check-id $PRIMARY_HEALTH_CHECK_ID

# Step 2: Promote RDS read replica
echo "2. Promoting RDS read replica to primary..."
aws rds promote-read-replica \
  --db-instance-identifier prod-postgres-replica-dr \
  --region $DR_REGION

# Wait for promotion to complete
aws rds wait db-instance-available \
  --db-instance-identifier prod-postgres-replica-dr \
  --region $DR_REGION
echo "✅ RDS promoted"

# Step 3: Update SSM parameters with new endpoints
NEW_DB_HOST=$(aws rds describe-db-instances \
  --db-instance-identifier prod-postgres-replica-dr \
  --region $DR_REGION \
  --query 'DBInstances[0].Endpoint.Address' \
  --output text)

aws ssm put-parameter \
  --name /production/db/host \
  --value $NEW_DB_HOST \
  --overwrite \
  --region $DR_REGION

# Step 4: Scale up ASG in DR region
echo "3. Scaling up ASG in DR region..."
aws autoscaling update-auto-scaling-group \
  --auto-scaling-group-name dr-web-asg \
  --min-size 4 \
  --desired-capacity 8 \
  --max-size 20 \
  --region $DR_REGION

# Step 5: Update Route 53 to force traffic to DR
echo "4. Updating Route 53..."
# (disable health check or update primary record to DR)

echo "✅ DR activation complete"
echo "⚠️  Remember to:"
echo "  - Notify stakeholders"
echo "  - Monitor DR region performance"
echo "  - Document incident timeline"
echo "  - Plan failback to primary when recovered"
```

---

## 8.12 Practice Questions (SysOps Exam Level)

**Q1:** Your company has an RTO of 1 hour and RPO of 15 minutes for their production database. The database is 500GB. Which DR strategy best meets these requirements?

**A:** **Warm Standby** or **Pilot Light with RDS Cross-Region Read Replica**:
- Create a cross-region read replica (continuously updated, RPO ~minutes)
- Keep a scaled-down but ready application stack in the DR region
- In a disaster, promote the replica and scale up app servers (~30-60 minutes)
- Cost: moderate (running replica + minimal compute in DR region)

---

**Q2:** An Auto Scaling Group has MinSize=2, MaxSize=10, DesiredCapacity=4, spread across 3 AZs. One entire AZ goes down. What happens to the instances?

**A:**
1. The 1-2 instances in the failed AZ are considered unhealthy (ELB health check fails)
2. ASG terminates them and launches replacements in the remaining 2 healthy AZs
3. If MinSize=2 and we still have 2+ instances in healthy AZs, service continues
4. ASG will try to rebalance across AZs when the failed one recovers

The application remains available because traffic is distributed across AZs via ALB.

---

**Q3:** You have a multi-region active-active setup. How do you handle database writes going to both regions without conflicts?

**A:**
- **DynamoDB Global Tables** — supports multi-region writes with last-writer-wins conflict resolution
- **Aurora Global Database** — typically one writer region, others read-only (active-passive, not active-active writes)
- **For active-active writes on relational DB**: Use different primary keys/shards per region + application-level conflict resolution

For most SysOps scenarios, active-passive (primary writer + read replicas) is recommended.

---

**Q4:** A CloudWatch alarm sends an SNS notification indicating your production RDS instance is low on storage (less than 5GB free). What immediate steps do you take?

**A:**
1. **Immediate**: Enable RDS **Storage Auto Scaling** (if not already enabled) to automatically grow storage
2. **Immediate**: Modify the RDS instance to increase storage manually: `aws rds modify-db-instance --db-instance-identifier prod-db --allocated-storage 200`
3. **RDS modifies storage online** (no downtime for most scenarios, but may impact performance)
4. **Investigation**: Check what's consuming space (large indexes, bloat, unarchived logs)
5. **Long-term**: Set CloudWatch alarm at 20% free to have more warning time

---

**Q5:** You need to ensure your static website (S3 + CloudFront) survives an entire AWS region failure. How do you architect this?

**A:**
S3 static websites are already **region-redundant within a region**, but for full regional failure:

1. **S3 CRR (Cross-Region Replication)** — replicate to a second region
2. **Route 53 with two origins**: Primary CloudFront distribution (us-east-1 S3) and Secondary (us-west-2 S3)
3. **Route 53 Failover routing** with health checks on each CloudFront distribution
4. **CloudFront itself** is a global service — it serves from edge locations, so the CDN layer is already multi-region. The origin is the single point of failure to protect.

---

## Key HA/DR Terms for Exam

| Term | Definition |
|------|-----------|
| RTO | Recovery Time Objective — max acceptable downtime |
| RPO | Recovery Point Objective — max acceptable data loss |
| Multi-AZ | Redundant deployment across 2+ AZs |
| Multi-Region | Active-active or active-passive across regions |
| Health Check | Automated test of resource/endpoint availability |
| Failover | Automatic switch to backup resource on failure |
| Read Replica | Async copy of DB for read scaling + DR |
| Cross-Region Replication | Copy data to another region (S3, RDS, Aurora, DynamoDB) |
| Aurora Global | Multi-region Aurora with <1s replication lag |
| Pilot Light | Minimal DR infrastructure always running |
| Warm Standby | Scaled-down but running copy in DR region |
| Active-Active | Both regions handling live traffic simultaneously |
| AWS Backup | Centralized managed backup service |
| DRS | AWS Elastic Disaster Recovery — continuous replication |
| Auto Recovery | EC2 automatic recover from system failure |
