# CloudFormation Chapter 9: CI/CD Deployment Pipelines
## CodePipeline, GitHub Actions, and Automated Infrastructure Deployment

---

## 9.1 CloudFormation Deployment Pipeline

```yaml
# pipeline.yaml — CloudFormation CI/CD pipeline
AWSTemplateFormatVersion: '2010-09-09'
Description: CI/CD pipeline for CloudFormation deployments with safety checks

Parameters:
  GitHubOwner:
    Type: String
  GitHubRepo:
    Type: String
  GitHubBranch:
    Type: String
    Default: main
  GitHubConnectionArn:
    Type: String
    Description: CodeStar Connections ARN for GitHub

Resources:
  # ── S3 Artifacts Bucket ───────────────────────────────
  ArtifactsBucket:
    Type: AWS::S3::Bucket
    Properties:
      BucketEncryption:
        ServerSideEncryptionConfiguration:
          - ServerSideEncryptionByDefault:
              SSEAlgorithm: AES256
      VersioningConfiguration:
        Status: Enabled
      LifecycleConfiguration:
        Rules:
          - Id: delete-old-artifacts
            Status: Enabled
            ExpirationInDays: 30

  # ── CodeBuild — Validate and Package Templates ────────
  ValidateProject:
    Type: AWS::CodeBuild::Project
    Properties:
      Name: !Sub '${AWS::StackName}-validate'
      ServiceRole: !GetAtt CodeBuildRole.Arn
      Environment:
        Type: LINUX_CONTAINER
        ComputeType: BUILD_GENERAL1_SMALL
        Image: aws/codebuild/standard:7.0
      Source:
        Type: CODEPIPELINE
        BuildSpec: |
          version: 0.2
          phases:
            install:
              commands:
                - pip install cfn-lint cfn-nag
                - curl -Lo /usr/local/bin/cfn-guard \
                    https://github.com/aws-cloudformation/cloudformation-guard/releases/latest/download/cfn-guard-v3-x86_64-unknown-linux-musl.tar.gz
                - tar -xzf /dev/stdin <<< "$(cat /usr/local/bin/cfn-guard)" -C /usr/local/bin
            build:
              commands:
                # Lint templates
                - cfn-lint templates/*.yaml
                
                # Security checks
                - cfn_nag_scan --input-path templates/ --deny-list-path deny-list.yaml
                
                # Policy validation
                - cfn-guard validate -d templates/ -r guard-rules/security.guard
                - cfn-guard validate -d templates/ -r guard-rules/tagging.guard
                
                # Package templates (resolve local file references)
                - aws cloudformation package \
                    --template-file templates/root-stack.yaml \
                    --s3-bucket $ARTIFACTS_BUCKET \
                    --output-template-file packaged-template.yaml
          artifacts:
            files:
              - packaged-template.yaml
              - parameters/**
      Artifacts:
        Type: CODEPIPELINE
      EnvironmentVariables:
        - Name: ARTIFACTS_BUCKET
          Value: !Ref ArtifactsBucket

  # ── CodeBuild — Deploy to Staging ────────────────────
  DeployStagingProject:
    Type: AWS::CodeBuild::Project
    Properties:
      Name: !Sub '${AWS::StackName}-deploy-staging'
      ServiceRole: !GetAtt CodeBuildRole.Arn
      Environment:
        Type: LINUX_CONTAINER
        ComputeType: BUILD_GENERAL1_SMALL
        Image: aws/codebuild/standard:7.0
      Source:
        Type: CODEPIPELINE
        BuildSpec: |
          version: 0.2
          phases:
            build:
              commands:
                # Create or update change set
                - |
                  aws cloudformation deploy \
                    --template-file packaged-template.yaml \
                    --stack-name staging-infrastructure \
                    --parameter-overrides $(cat parameters/staging.json | jq -r '.[] | "\(.ParameterKey)=\(.ParameterValue)"') \
                    --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM CAPABILITY_AUTO_EXPAND \
                    --no-fail-on-empty-changeset \
                    --tags Environment=staging Project=myapp
                
                # Wait for stack to stabilize
                - aws cloudformation wait stack-update-complete \
                    --stack-name staging-infrastructure || \
                  aws cloudformation wait stack-create-complete \
                    --stack-name staging-infrastructure
                
                # Export stack outputs for integration tests
                - aws cloudformation describe-stacks \
                    --stack-name staging-infrastructure \
                    --query "Stacks[0].Outputs" > stack-outputs.json
          artifacts:
            files:
              - stack-outputs.json
      Artifacts:
        Type: CODEPIPELINE

  # ── CodePipeline ──────────────────────────────────────
  InfrastructurePipeline:
    Type: AWS::CodePipeline::Pipeline
    Properties:
      Name: !Sub '${AWS::StackName}-pipeline'
      RoleArn: !GetAtt CodePipelineRole.Arn
      ArtifactStore:
        Type: S3
        Location: !Ref ArtifactsBucket
      Stages:
        # Stage 1: Pull source from GitHub
        - Name: Source
          Actions:
            - Name: GitHub
              ActionTypeId:
                Category: Source
                Owner: AWS
                Provider: CodeStarSourceConnection
                Version: "1"
              Configuration:
                ConnectionArn: !Ref GitHubConnectionArn
                FullRepositoryId: !Sub '${GitHubOwner}/${GitHubRepo}'
                BranchName: !Ref GitHubBranch
                DetectChanges: true
              OutputArtifacts:
                - Name: SourceCode

        # Stage 2: Validate and package
        - Name: Validate
          Actions:
            - Name: ValidateTemplates
              ActionTypeId:
                Category: Build
                Owner: AWS
                Provider: CodeBuild
                Version: "1"
              Configuration:
                ProjectName: !Ref ValidateProject
              InputArtifacts:
                - Name: SourceCode
              OutputArtifacts:
                - Name: PackagedTemplates

        # Stage 3: Deploy to staging
        - Name: DeployStaging
          Actions:
            - Name: DeployToStaging
              ActionTypeId:
                Category: Build
                Owner: AWS
                Provider: CodeBuild
                Version: "1"
              Configuration:
                ProjectName: !Ref DeployStagingProject
              InputArtifacts:
                - Name: PackagedTemplates
              OutputArtifacts:
                - Name: StagingOutputs

        # Stage 4: Run integration tests
        - Name: IntegrationTests
          Actions:
            - Name: RunTests
              ActionTypeId:
                Category: Build
                Owner: AWS
                Provider: CodeBuild
                Version: "1"
              Configuration:
                ProjectName: !Ref IntegrationTestProject
              InputArtifacts:
                - Name: StagingOutputs

        # Stage 5: Manual approval for production
        - Name: ApproveProduction
          Actions:
            - Name: ManualApproval
              ActionTypeId:
                Category: Approval
                Owner: AWS
                Provider: Manual
                Version: "1"
              Configuration:
                NotificationArn: !Ref ApprovalNotificationTopic
                CustomData: "Review staging environment before deploying to production"
                ExternalEntityLink: !Sub 'https://${StagingApiEndpoint}'

        # Stage 6: Deploy to production with change set preview
        - Name: DeployProduction
          Actions:
            - Name: CreateChangeSet
              ActionTypeId:
                Category: Deploy
                Owner: AWS
                Provider: CloudFormation
                Version: "1"
              Configuration:
                ActionMode: CHANGE_SET_REPLACE
                StackName: prod-infrastructure
                ChangeSetName: prod-update
                TemplatePath: PackagedTemplates::packaged-template.yaml
                ParameterOverrides: !Sub |
                  {
                    "Environment": "prod",
                    "ProjectName": "${GitHubRepo}"
                  }
                Capabilities: CAPABILITY_IAM,CAPABILITY_NAMED_IAM,CAPABILITY_AUTO_EXPAND
                RoleArn: !GetAtt CloudFormationDeployRole.Arn
              InputArtifacts:
                - Name: PackagedTemplates
              RunOrder: 1
            
            - Name: ExecuteChangeSet
              ActionTypeId:
                Category: Deploy
                Owner: AWS
                Provider: CloudFormation
                Version: "1"
              Configuration:
                ActionMode: CHANGE_SET_EXECUTE
                StackName: prod-infrastructure
                ChangeSetName: prod-update
              RunOrder: 2
```

---

## 9.2 GitHub Actions — CloudFormation Deployment

```yaml
# .github/workflows/cloudformation-deploy.yml
name: Deploy Infrastructure

on:
  push:
    branches: [main]
    paths:
      - 'infrastructure/**'
      - '.github/workflows/cloudformation-deploy.yml'
  pull_request:
    branches: [main]
    paths:
      - 'infrastructure/**'

permissions:
  id-token: write
  contents: read
  pull-requests: write

env:
  AWS_REGION: us-east-1
  ARTIFACTS_BUCKET: my-cfn-artifacts-bucket

jobs:
  validate:
    name: Validate Templates
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Python for cfn-lint
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install tools
        run: |
          pip install cfn-lint
          curl -Lo cfn-guard.tar.gz https://github.com/aws-cloudformation/cloudformation-guard/releases/latest/download/cfn-guard-v3-x86_64-unknown-linux-musl.tar.gz
          tar -xzf cfn-guard.tar.gz -C /usr/local/bin/
      
      - name: Lint CloudFormation templates
        run: cfn-lint infrastructure/**/*.yaml
      
      - name: Guard policy validation
        run: cfn-guard validate -d infrastructure/ -r guard-rules/

  plan:
    name: Plan Changes
    needs: validate
    runs-on: ubuntu-latest
    if: github.event_name == 'pull_request'
    steps:
      - uses: actions/checkout@v4
      
      - name: Configure AWS credentials (OIDC)
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::${{ secrets.AWS_ACCOUNT_ID }}:role/GitHubActionsInfraRole
          aws-region: ${{ env.AWS_REGION }}
      
      - name: Package templates
        run: |
          aws cloudformation package \
            --template-file infrastructure/root-stack.yaml \
            --s3-bucket $ARTIFACTS_BUCKET \
            --output-template-file packaged.yaml
      
      - name: Create change set (plan)
        id: changeset
        run: |
          CHANGE_SET_NAME="pr-${{ github.event.pull_request.number }}-$(date +%s)"
          
          aws cloudformation create-change-set \
            --stack-name staging-infrastructure \
            --change-set-name $CHANGE_SET_NAME \
            --template-body file://packaged.yaml \
            --parameters file://infrastructure/parameters/staging.json \
            --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM CAPABILITY_AUTO_EXPAND \
            --change-set-type UPDATE || \
          aws cloudformation create-change-set \
            --stack-name staging-infrastructure \
            --change-set-name $CHANGE_SET_NAME \
            --template-body file://packaged.yaml \
            --parameters file://infrastructure/parameters/staging.json \
            --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM CAPABILITY_AUTO_EXPAND \
            --change-set-type CREATE
          
          # Wait for change set
          aws cloudformation wait change-set-create-complete \
            --stack-name staging-infrastructure \
            --change-set-name $CHANGE_SET_NAME
          
          # Get changes
          CHANGES=$(aws cloudformation describe-change-set \
            --stack-name staging-infrastructure \
            --change-set-name $CHANGE_SET_NAME \
            --query "Changes[*].{Action:ResourceChange.Action,Resource:ResourceChange.LogicalResourceId,Type:ResourceChange.ResourceType,Replace:ResourceChange.Replacement}" \
            --output table)
          
          echo "changes<<EOF" >> $GITHUB_OUTPUT
          echo "$CHANGES" >> $GITHUB_OUTPUT
          echo "EOF" >> $GITHUB_OUTPUT
          echo "change_set_name=$CHANGE_SET_NAME" >> $GITHUB_OUTPUT
      
      - name: Comment PR with changes
        uses: actions/github-script@v7
        with:
          script: |
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: `## CloudFormation Changes Preview\n\`\`\`\n${{ steps.changeset.outputs.changes }}\n\`\`\``
            })

  deploy-staging:
    name: Deploy to Staging
    needs: validate
    runs-on: ubuntu-latest
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    environment: staging
    steps:
      - uses: actions/checkout@v4
      
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::${{ secrets.AWS_ACCOUNT_ID }}:role/GitHubActionsInfraRole
          aws-region: ${{ env.AWS_REGION }}
      
      - name: Deploy to staging
        run: |
          aws cloudformation deploy \
            --template-file infrastructure/root-stack.yaml \
            --stack-name staging-infrastructure \
            --parameter-overrides \
              Environment=staging \
              ProjectName=myapp \
            --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM CAPABILITY_AUTO_EXPAND \
            --no-fail-on-empty-changeset

  deploy-prod:
    name: Deploy to Production
    needs: deploy-staging
    runs-on: ubuntu-latest
    environment: production    # Requires manual approval in GitHub
    steps:
      - uses: actions/checkout@v4
      
      - name: Configure AWS credentials (prod account)
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::${{ secrets.PROD_AWS_ACCOUNT_ID }}:role/GitHubActionsInfraRole
          aws-region: ${{ env.AWS_REGION }}
      
      - name: Deploy to production
        run: |
          aws cloudformation deploy \
            --template-file infrastructure/root-stack.yaml \
            --stack-name prod-infrastructure \
            --parameter-overrides \
              Environment=prod \
              ProjectName=myapp \
            --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM CAPABILITY_AUTO_EXPAND \
            --no-fail-on-empty-changeset
```

---

## 9.3 Interview Q&A

**Q: What is the `aws cloudformation deploy` command and how does it differ from `create-stack`/`update-stack`?**
A: `aws cloudformation deploy` is a higher-level convenience command that: (1) creates the stack if it doesn't exist (no need to check first); (2) creates a Change Set and executes it for updates; (3) `--no-fail-on-empty-changeset` skips execution if no changes (idempotent); (4) handles both CREATE and UPDATE in a single command. It's suitable for CI/CD. Use `create-stack`/`update-stack` when you need more granular control (custom rollback triggers, specific update policies, notification ARNs on create vs update).

**Q: How do you safely deploy CloudFormation to production without downtime?**
A: (1) Use Change Sets to preview changes before applying; (2) Use Rollback triggers (CloudWatch alarms that trigger auto-rollback if alarms fire after deployment); (3) Set `--disable-rollback false` (default) so failed deployments roll back; (4) Test in staging first with identical parameters; (5) Use `MinimumHealthyPercent: 100` in ECS UpdatePolicy; (6) Add `DependsOn` to ensure correct ordering; (7) For database changes, use DeletionPolicy/UpdateReplacePolicy to protect data; (8) Monitor CloudWatch dashboards during deployment.

**Q: How do you add rollback triggers to a CloudFormation deployment?**
A: Rollback triggers are CloudWatch alarms added via `--rollback-configuration`. If any alarm fires within the monitoring window after deployment, CloudFormation automatically rolls back. Example: `aws cloudformation deploy ... --rollback-configuration RollbackTriggers=[{Arn=arn:alarm,Type=AWS::CloudWatch::Alarm}],MonitoringTimeInMinutes=5`. The alarm should monitor application-level metrics (5xx error rate, Lambda errors, ECS task health). This is distinct from the deployment circuit breaker (which monitors task startup) — rollback triggers monitor post-deployment application behavior.
