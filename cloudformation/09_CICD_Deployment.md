# Chapter 9: CI/CD & Deployment
## Change Sets, Rollback, Stack Policies & GitHub Actions Pipeline

---

## 9.1 Change Set Workflow

Always use change sets in production. Never run `deploy` directly on a production stack without reviewing changes first.

```bash
# STEP 1: Create a change set
aws cloudformation create-change-set \
  --stack-name myapp-prod \
  --template-body file://template.yaml \
  --change-set-name deploy-$(date +%Y%m%d-%H%M%S) \
  --parameters \
    ParameterKey=Environment,ParameterValue=prod \
    ParameterKey=ImageUri,ParameterValue=123456.dkr.ecr.us-east-1.amazonaws.com/myapp:v2.1.0 \
  --capabilities CAPABILITY_NAMED_IAM

# STEP 2: Wait for change set creation
aws cloudformation wait change-set-create-complete \
  --stack-name myapp-prod \
  --change-set-name deploy-20240115-143022

# STEP 3: Review changes
aws cloudformation describe-change-set \
  --stack-name myapp-prod \
  --change-set-name deploy-20240115-143022 \
  --query "Changes[*].[
    Type,
    ResourceChange.Action,
    ResourceChange.LogicalResourceId,
    ResourceChange.ResourceType,
    ResourceChange.Replacement
  ]" \
  --output table

# Output example:
# Type | Action | Resource ID    | Resource Type         | Replacement
# ─────|────────|────────────────|───────────────────────|────────────
# Res  | Modify | TaskDefinition | AWS::ECS::TaskDef...  | False
# Res  | Modify | ECSService     | AWS::ECS::Service     | False

# STEP 4: If Replacement=True for a critical resource, investigate before proceeding!

# STEP 5: Execute change set
aws cloudformation execute-change-set \
  --stack-name myapp-prod \
  --change-set-name deploy-20240115-143022

# STEP 6: Watch deployment
aws cloudformation describe-stack-events \
  --stack-name myapp-prod \
  --query "StackEvents[*].[Timestamp,ResourceStatus,LogicalResourceId,ResourceStatusReason]" \
  --max-items 20

# Wait for stack to stabilise
aws cloudformation wait stack-update-complete --stack-name myapp-prod
```

---

## 9.2 Rollback

```bash
# Automatic rollback happens on failure (default behaviour)
# To view what triggered the rollback:
aws cloudformation describe-stack-events \
  --stack-name myapp-prod \
  --query "StackEvents[?ResourceStatus=='UPDATE_FAILED'].[Timestamp,LogicalResourceId,ResourceStatusReason]"

# Continue rollback after a stack is stuck in UPDATE_ROLLBACK_FAILED
# (happens when rollback itself fails, e.g., a resource was manually deleted)
aws cloudformation continue-update-rollback \
  --stack-name myapp-prod

# Skip specific resources during rollback (if they can't be rolled back)
aws cloudformation continue-update-rollback \
  --stack-name myapp-prod \
  --resources-to-skip ProblematicResource1 ProblematicResource2

# Cancel an in-progress update (initiates rollback)
aws cloudformation cancel-update-stack --stack-name myapp-prod
```

### Rollback Triggers

```yaml
# Template: CloudWatch alarm-triggered rollback
# If alarm fires during deployment, CloudFormation rolls back automatically
```

```bash
# Create stack with rollback trigger
aws cloudformation create-stack \
  --stack-name myapp-prod \
  --template-body file://template.yaml \
  --rollback-configuration '{
    "RollbackTriggers": [
      {
        "Arn": "arn:aws:cloudwatch:us-east-1:123456:alarm:high-error-rate",
        "Type": "AWS::CloudWatch::Alarm"
      },
      {
        "Arn": "arn:aws:cloudwatch:us-east-1:123456:alarm:service-health",
        "Type": "AWS::CloudWatch::Alarm"
      }
    ],
    "MonitoringTimeInMinutes": 10
  }' \
  --capabilities CAPABILITY_NAMED_IAM
```

---

## 9.3 Stack Policies

Stack policies prevent specific resources from being updated or deleted during stack updates.

```json
// stack-policy.json — protect production database and IAM roles from updates
{
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": "*",
      "Action": "Update:*",
      "Resource": "*"
    },
    {
      "Effect": "Deny",
      "Principal": "*",
      "Action": ["Update:Replace", "Update:Delete"],
      "Resource": "LogicalResourceId/AuroraCluster",
      "Condition": {
        "StringEquals": {
          "ResourceType": ["AWS::RDS::DBCluster"]
        }
      }
    },
    {
      "Effect": "Deny",
      "Principal": "*",
      "Action": "Update:Delete",
      "Resource": "LogicalResourceId/AppRole"
    }
  ]
}
```

```bash
# Set stack policy during creation
aws cloudformation create-stack \
  --stack-name myapp-prod \
  --template-body file://template.yaml \
  --stack-policy-body file://stack-policy.json

# Set stack policy after creation
aws cloudformation set-stack-policy \
  --stack-name myapp-prod \
  --stack-policy-body file://stack-policy.json

# Override stack policy temporarily for a specific update
# (use --stack-policy-during-update-body with a permissive policy)
aws cloudformation update-stack \
  --stack-name myapp-prod \
  --template-body file://template.yaml \
  --stack-policy-during-update-body '{"Statement":[{"Effect":"Allow","Principal":"*","Action":"Update:*","Resource":"*"}]}'
```

---

## 9.4 Complete GitHub Actions CI/CD Pipeline

```yaml
# .github/workflows/deploy.yml
name: Deploy Infrastructure & Application

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

permissions:
  id-token: write
  contents: read
  pull-requests: write

env:
  AWS_REGION: us-east-1
  STACK_NAME: myapp-prod
  ECR_REPO: myapp

jobs:
  # ─────────────────────────────────────────────
  # JOB 1: Validate & lint templates
  # ─────────────────────────────────────────────
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install cfn-lint
        run: pip install cfn-lint

      - name: Lint CloudFormation templates
        run: |
          cfn-lint cloudformation/networking.yaml
          cfn-lint cloudformation/databases.yaml
          cfn-lint cloudformation/container-stack.yaml

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::${{ secrets.AWS_ACCOUNT_ID }}:role/github-actions-role
          aws-region: ${{ env.AWS_REGION }}

      - name: Validate templates with CloudFormation
        run: |
          for template in cloudformation/*.yaml; do
            echo "Validating $template..."
            aws cloudformation validate-template \
              --template-body file://$template
          done

  # ─────────────────────────────────────────────
  # JOB 2: Run tests and build Docker image
  # ─────────────────────────────────────────────
  build:
    needs: validate
    runs-on: ubuntu-latest
    outputs:
      image-uri: ${{ steps.build.outputs.image-uri }}

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install dependencies and test
        run: |
          pip install -r requirements.txt
          pytest tests/ --tb=short -v

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::${{ secrets.AWS_ACCOUNT_ID }}:role/github-actions-role
          aws-region: ${{ env.AWS_REGION }}

      - name: Login to ECR
        id: login-ecr
        uses: aws-actions/amazon-ecr-login@v2

      - name: Build and push Docker image
        id: build
        env:
          REGISTRY: ${{ steps.login-ecr.outputs.registry }}
          IMAGE_TAG: ${{ github.sha }}
        run: |
          IMAGE_URI=$REGISTRY/$ECR_REPO:$IMAGE_TAG
          docker build -t $IMAGE_URI .
          docker push $IMAGE_URI
          echo "image-uri=$IMAGE_URI" >> $GITHUB_OUTPUT

  # ─────────────────────────────────────────────
  # JOB 3: Create change set (on PR — review before merge)
  # ─────────────────────────────────────────────
  plan:
    needs: build
    runs-on: ubuntu-latest
    if: github.event_name == 'pull_request'

    steps:
      - uses: actions/checkout@v4

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::${{ secrets.AWS_ACCOUNT_ID }}:role/github-actions-role
          aws-region: ${{ env.AWS_REGION }}

      - name: Create change set
        id: changeset
        run: |
          CHANGE_SET_NAME="pr-${{ github.event.number }}-$(date +%s)"
          
          aws cloudformation create-change-set \
            --stack-name $STACK_NAME \
            --template-body file://cloudformation/container-stack.yaml \
            --change-set-name $CHANGE_SET_NAME \
            --parameters \
              ParameterKey=Environment,ParameterValue=prod \
              ParameterKey=ImageUri,ParameterValue=${{ needs.build.outputs.image-uri }} \
              ParameterKey=NetworkingStack,ParameterValue=myapp-networking \
            --capabilities CAPABILITY_NAMED_IAM
          
          aws cloudformation wait change-set-create-complete \
            --stack-name $STACK_NAME \
            --change-set-name $CHANGE_SET_NAME
          
          # Get changes as JSON
          CHANGES=$(aws cloudformation describe-change-set \
            --stack-name $STACK_NAME \
            --change-set-name $CHANGE_SET_NAME \
            --query "Changes[*].ResourceChange.[Action,LogicalResourceId,Replacement]" \
            --output text)
          
          echo "CHANGES<<EOF" >> $GITHUB_ENV
          echo "$CHANGES" >> $GITHUB_ENV
          echo "EOF" >> $GITHUB_ENV
          
          # Delete change set (will recreate on merge)
          aws cloudformation delete-change-set \
            --stack-name $STACK_NAME \
            --change-set-name $CHANGE_SET_NAME

      - name: Comment change set on PR
        uses: actions/github-script@v7
        with:
          script: |
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: `## CloudFormation Changes\n\`\`\`\n${process.env.CHANGES}\n\`\`\``
            })

  # ─────────────────────────────────────────────
  # JOB 4: Deploy to production (on merge to main)
  # ─────────────────────────────────────────────
  deploy:
    needs: build
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    environment: production    # Requires manual approval in GitHub

    steps:
      - uses: actions/checkout@v4

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::${{ secrets.AWS_ACCOUNT_ID }}:role/github-actions-role
          aws-region: ${{ env.AWS_REGION }}

      - name: Deploy networking stack
        run: |
          aws cloudformation deploy \
            --template-file cloudformation/networking.yaml \
            --stack-name myapp-networking \
            --parameter-overrides Environment=prod EnableNatGateway=true \
            --no-fail-on-empty-changeset

      - name: Deploy container stack
        run: |
          aws cloudformation deploy \
            --template-file cloudformation/container-stack.yaml \
            --stack-name $STACK_NAME \
            --parameter-overrides \
              Environment=prod \
              ImageUri=${{ needs.build.outputs.image-uri }} \
              NetworkingStack=myapp-networking \
            --capabilities CAPABILITY_NAMED_IAM \
            --no-fail-on-empty-changeset

      - name: Verify deployment
        run: |
          SERVICE_URL=$(aws cloudformation describe-stacks \
            --stack-name $STACK_NAME \
            --query "Stacks[0].Outputs[?OutputKey=='ServiceUrl'].OutputValue" \
            --output text)
          
          echo "Deployed to: $SERVICE_URL"
          
          # Health check
          for i in {1..5}; do
            STATUS=$(curl -s -o /dev/null -w "%{http_code}" $SERVICE_URL/health)
            if [ "$STATUS" = "200" ]; then
              echo "Health check passed!"
              exit 0
            fi
            echo "Attempt $i failed (status: $STATUS), retrying..."
            sleep 10
          done
          
          echo "Health check failed after 5 attempts"
          exit 1
```

---

## 9.5 Interview Questions

**Q: What does `--no-fail-on-empty-changeset` do in `aws cloudformation deploy`?**
> By default, `deploy` fails with an error if there are no changes to apply (the stack is already up-to-date). `--no-fail-on-empty-changeset` makes it exit with code 0 instead — so CI/CD pipelines don't fail just because nothing changed (e.g., when code changed but not the infrastructure template). This is the recommended option for deployment pipelines to make them idempotent.

**Q: How do you prevent accidentally replacing a production RDS instance during a template update?**
> Three layers of protection: (1) `DeletionPolicy: Snapshot, UpdateReplacePolicy: Snapshot` on the RDS resource — if it must be replaced, the old one is snapshotted first. (2) `DeletionProtection: true` on Aurora — prevents deletion through any means. (3) A Stack Policy that denies `Update:Replace` and `Update:Delete` actions on the RDS resource. Also, always use change sets in production — look for `Replacement: True` in the change set output before executing.

**Q: How do rollback triggers work?**
> Rollback triggers attach CloudWatch alarms to a stack update. When you execute an update, CloudFormation monitors the specified alarms for a `MonitoringTimeInMinutes` period (1-180 minutes). If any alarm enters the ALARM state during this window, CloudFormation automatically initiates a rollback, undoing all changes made during that deployment. This is powerful for production: deploy a new version, and if error rate spikes within 10 minutes, it auto-rolls back without human intervention.
