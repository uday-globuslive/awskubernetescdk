# Chapter 13: Developer Tools & CI/CD
## CodeCommit, CodeBuild, CodeDeploy, CodePipeline & GitHub Actions

---

## 13.1 AWS CI/CD Overview

```
┌──────────────────────────────────────────────────────────────┐
│               AWS DEVELOPER TOOLS (CODE*)                    │
│                                                              │
│  CodeCommit  →  CodeBuild  →  CodeDeploy                     │
│  (Source)        (Build)       (Deploy)                      │
│                                                              │
│  └──────────── CodePipeline ──────────────┘                  │
│              (Orchestrates all stages)                       │
│                                                              │
│  OR use GitHub/GitLab as source instead of CodeCommit        │
└──────────────────────────────────────────────────────────────┘
```

---

## 13.2 CodeCommit

CodeCommit is a fully managed Git service. It's compatible with all Git commands.

```bash
# Create repository
aws codecommit create-repository \
  --repository-name myapp \
  --repository-description "Main application repository"

# Clone (using HTTPS + credential helper, or SSH)
git clone https://git-codecommit.us-east-1.amazonaws.com/v1/repos/myapp

# Configure credential helper for HTTPS
git config --global credential.helper '!aws codecommit credential-helper $@'
git config --global credential.UseHttpPath true

# Create branch
aws codecommit create-branch \
  --repository-name myapp \
  --branch-name feature/new-api \
  --commit-id main

# Create pull request
aws codecommit create-pull-request \
  --title "Add new API endpoints" \
  --description "Adds CRUD endpoints for orders" \
  --targets repositoryName=myapp,sourceReference=feature/new-api,destinationReference=main
```

---

## 13.3 CodeBuild

CodeBuild runs build commands in a managed Docker container. Defined by `buildspec.yml`.

### buildspec.yml

```yaml
# buildspec.yml (placed in root of your repository)
version: 0.2

env:
  variables:
    ENVIRONMENT: "production"
  parameter-store:
    DB_PASSWORD: "/myapp/prod/db-password"
  secrets-manager:
    JWT_SECRET: "myapp/prod/jwt-secret:jwt_secret"

phases:
  install:
    runtime-versions:
      python: 3.11
    commands:
      - pip install --upgrade pip
      - pip install -r requirements.txt

  pre_build:
    commands:
      - echo "Running tests..."
      - pytest tests/ --tb=short --junitxml=test-results.xml
      - echo "Logging into ECR..."
      - aws ecr get-login-password --region $AWS_DEFAULT_REGION |
          docker login --username AWS --password-stdin $ECR_REGISTRY

  build:
    commands:
      - echo "Building Docker image..."
      - docker build -t $ECR_REGISTRY/$ECR_REPO:$CODEBUILD_RESOLVED_SOURCE_VERSION .
      - docker tag $ECR_REGISTRY/$ECR_REPO:$CODEBUILD_RESOLVED_SOURCE_VERSION \
          $ECR_REGISTRY/$ECR_REPO:latest

  post_build:
    commands:
      - echo "Pushing image to ECR..."
      - docker push $ECR_REGISTRY/$ECR_REPO:$CODEBUILD_RESOLVED_SOURCE_VERSION
      - docker push $ECR_REGISTRY/$ECR_REPO:latest
      - echo "Writing image definition for CodeDeploy..."
      - printf '[{"name":"myapp","imageUri":"%s"}]' \
          $ECR_REGISTRY/$ECR_REPO:$CODEBUILD_RESOLVED_SOURCE_VERSION > imagedefinitions.json

reports:
  pytest-reports:
    files:
      - test-results.xml
    file-format: JUNITXML

artifacts:
  files:
    - imagedefinitions.json
    - appspec.yml
    - taskdef.json
```

```bash
# Create CodeBuild project
aws codebuild create-project \
  --name myapp-build \
  --source '{"type": "CODECOMMIT", "location": "https://git-codecommit.us-east-1.amazonaws.com/v1/repos/myapp"}' \
  --environment '{
    "type": "LINUX_CONTAINER",
    "image": "aws/codebuild/standard:7.0",
    "computeType": "BUILD_GENERAL1_SMALL",
    "privilegedMode": true,
    "environmentVariables": [
      {"name": "ECR_REGISTRY", "value": "123456789012.dkr.ecr.us-east-1.amazonaws.com"},
      {"name": "ECR_REPO", "value": "myapp"}
    ]
  }' \
  --artifacts '{"type": "S3", "location": "myapp-build-artifacts"}' \
  --service-role arn:aws:iam::123456789012:role/codebuild-role

# Start build manually
aws codebuild start-build --project-name myapp-build

# View build logs
aws codebuild batch-get-builds \
  --ids <build-id> \
  --query "builds[0].phases[*].[phaseType,phaseStatus,durationInSeconds]"
```

---

## 13.4 CodeDeploy

CodeDeploy automates deployments to EC2 instances, Lambda functions, and ECS services.

### Deployment Strategies

```
┌──────────────────────────────────────────────────────────┐
│              CODEDEPLOY STRATEGIES                       │
├────────────────────────┬─────────────────────────────────┤
│ In-Place (EC2)         │ Stop app, deploy new version,   │
│                        │ restart. Downtime during deploy  │
├────────────────────────┼─────────────────────────────────┤
│ Rolling                │ Deploy to % of instances at a   │
│                        │ time. Some old, some new running │
├────────────────────────┼─────────────────────────────────┤
│ Blue/Green             │ New fleet created, traffic       │
│                        │ switched all at once. Old fleet  │
│                        │ kept for rollback                │
├────────────────────────┼─────────────────────────────────┤
│ Canary (Lambda/ECS)    │ Shift 10% traffic → wait →      │
│                        │ shift 100% (or rollback on err)  │
├────────────────────────┼─────────────────────────────────┤
│ Linear (Lambda/ECS)    │ Shift 10% every N minutes until │
│                        │ 100%                            │
└────────────────────────┴─────────────────────────────────┘
```

### appspec.yml (ECS)

```yaml
# appspec.yml — ECS Blue/Green deployment
version: 0.0
Resources:
  - TargetService:
      Type: AWS::ECS::Service
      Properties:
        TaskDefinition: <TASK_DEFINITION>
        LoadBalancerInfo:
          ContainerName: myapp
          ContainerPort: 8000

Hooks:
  - BeforeInstall: "arn:aws:lambda:...:function:pre-deploy-check"
  - AfterInstall: "arn:aws:lambda:...:function:post-deploy-validation"
  - AfterAllowTestTraffic: "arn:aws:lambda:...:function:integration-tests"
  - BeforeAllowTraffic: "arn:aws:lambda:...:function:smoke-test"
  - AfterAllowTraffic: "arn:aws:lambda:...:function:cleanup"
```

```bash
# Create deployment group for ECS
aws deploy create-deployment-group \
  --application-name myapp \
  --deployment-group-name myapp-prod \
  --deployment-config-name CodeDeployDefault.ECSCanary10Percent5Minutes \
  --ecs-services clusterName=myapp-cluster,serviceName=myapp-service \
  --load-balancer-info '{
    "targetGroupPairInfoList": [
      {
        "targetGroups": [
          {"name": "myapp-blue-tg"},
          {"name": "myapp-green-tg"}
        ],
        "prodTrafficRoute": {"listenerArns": ["arn:aws:elasticloadbalancing:...:listener/..."]},
        "testTrafficRoute": {"listenerArns": ["arn:aws:elasticloadbalancing:...:listener/..."]}
      }
    ]
  }' \
  --service-role-arn arn:aws:iam::123456789012:role/codedeploy-role

# Create deployment
aws deploy create-deployment \
  --application-name myapp \
  --deployment-group-name myapp-prod \
  --revision '{"revisionType": "S3", "s3Location": {"bucket": "myapp-artifacts", "key": "appspec.zip", "bundleType": "zip"}}'
```

---

## 13.5 CodePipeline

CodePipeline orchestrates the full CI/CD workflow.

```
Source Stage          Build Stage          Deploy Stage
─────────────         ───────────          ────────────
CodeCommit push    →  CodeBuild build  →   CodeDeploy
(or GitHub)           (test + package)     ECS blue/green
```

```bash
# Create pipeline (JSON definition)
aws codepipeline create-pipeline --pipeline '{
  "name": "myapp-pipeline",
  "roleArn": "arn:aws:iam::123456789012:role/codepipeline-role",
  "artifactStore": {
    "type": "S3",
    "location": "myapp-pipeline-artifacts"
  },
  "stages": [
    {
      "name": "Source",
      "actions": [{
        "name": "Source",
        "actionTypeId": {
          "category": "Source",
          "owner": "AWS",
          "provider": "CodeCommit",
          "version": "1"
        },
        "configuration": {
          "RepositoryName": "myapp",
          "BranchName": "main",
          "PollForSourceChanges": "false"
        },
        "outputArtifacts": [{"name": "SourceOutput"}]
      }]
    },
    {
      "name": "Build",
      "actions": [{
        "name": "Build",
        "actionTypeId": {
          "category": "Build",
          "owner": "AWS",
          "provider": "CodeBuild",
          "version": "1"
        },
        "configuration": {"ProjectName": "myapp-build"},
        "inputArtifacts": [{"name": "SourceOutput"}],
        "outputArtifacts": [{"name": "BuildOutput"}]
      }]
    },
    {
      "name": "Deploy",
      "actions": [{
        "name": "Deploy",
        "actionTypeId": {
          "category": "Deploy",
          "owner": "AWS",
          "provider": "CodeDeployToECS",
          "version": "1"
        },
        "configuration": {
          "ApplicationName": "myapp",
          "DeploymentGroupName": "myapp-prod",
          "TaskDefinitionTemplateArtifact": "BuildOutput",
          "AppSpecTemplateArtifact": "BuildOutput",
          "Image1ArtifactName": "BuildOutput",
          "Image1ContainerName": "IMAGE1_NAME"
        },
        "inputArtifacts": [{"name": "BuildOutput"}]
      }]
    }
  ]
}'
```

---

## 13.6 GitHub Actions for AWS (OIDC — No Access Keys)

```yaml
# .github/workflows/deploy.yml
name: Deploy to ECS

on:
  push:
    branches: [main]

permissions:
  id-token: write    # Required for OIDC
  contents: read

jobs:
  deploy:
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Configure AWS credentials (OIDC — no stored secrets)
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::123456789012:role/github-actions-deploy
          aws-region: us-east-1

      - name: Login to ECR
        id: login-ecr
        uses: aws-actions/amazon-ecr-login@v2

      - name: Run tests
        run: |
          pip install -r requirements.txt
          pytest tests/ --tb=short

      - name: Build and push Docker image
        id: build-image
        env:
          ECR_REGISTRY: ${{ steps.login-ecr.outputs.registry }}
          ECR_REPO: myapp
          IMAGE_TAG: ${{ github.sha }}
        run: |
          docker build -t $ECR_REGISTRY/$ECR_REPO:$IMAGE_TAG .
          docker push $ECR_REGISTRY/$ECR_REPO:$IMAGE_TAG
          echo "image=$ECR_REGISTRY/$ECR_REPO:$IMAGE_TAG" >> $GITHUB_OUTPUT

      - name: Render ECS task definition
        id: task-def
        uses: aws-actions/amazon-ecs-render-task-definition@v1
        with:
          task-definition: task-definition.json
          container-name: myapp
          image: ${{ steps.build-image.outputs.image }}

      - name: Deploy to ECS
        uses: aws-actions/amazon-ecs-deploy-task-definition@v1
        with:
          task-definition: ${{ steps.task-def.outputs.task-definition }}
          service: myapp-service
          cluster: myapp-cluster
          wait-for-service-stability: true
          codedeploy-appspec: appspec.yml
          codedeploy-application: myapp
          codedeploy-deployment-group: myapp-prod
```

```bash
# Create IAM role for GitHub Actions OIDC
# (No long-lived access keys — GitHub exchanges JWT for temp AWS credentials)

# 1. Create OIDC identity provider
aws iam create-open-id-connect-provider \
  --url https://token.actions.githubusercontent.com \
  --client-id-list sts.amazonaws.com \
  --thumbprint-list 6938fd4d98bab03faadb97b34396831e3780aea1

# 2. Create role with trust policy
aws iam create-role \
  --role-name github-actions-deploy \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::123456789012:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
        },
        "StringLike": {
          "token.actions.githubusercontent.com:sub": "repo:myorg/myapp:ref:refs/heads/main"
        }
      }
    }]
  }'
```

---

## 13.7 Interview Questions

**Q: What is the difference between CodeDeploy strategies — rolling, blue/green, canary?**
> Rolling: deploy to N instances at a time, so during deployment some instances run old code and some run new. Good for reducing risk but introduces a mixed-version state. Blue/Green: create a completely new environment (green), test it, then switch all traffic at once. Old environment (blue) stays running for instant rollback. Zero downtime. Canary: shift a small percentage (e.g., 10%) of traffic to new version, monitor errors/latency for N minutes, then complete the shift. Automated rollback if alarms fire. Best for production Lambda/ECS where gradual validation is needed.

**Q: Why use OIDC instead of IAM access keys in GitHub Actions?**
> Access keys are long-lived credentials — if exposed in a log, an attack, or accidental commit, they remain valid until manually rotated. OIDC (OpenID Connect) issues short-lived temporary credentials per workflow run. GitHub provides a JWT token, AWS validates it against the OIDC provider, and issues temporary STS credentials that expire after 1 hour. No secrets to store, no rotation needed, and the trust policy can restrict to specific repos and branches, making blast radius minimal.

**Q: What is CodePipeline and how does it differ from GitHub Actions?**
> CodePipeline is a fully managed AWS orchestration service that chains source, build, test, and deploy stages using AWS-native tools (CodeCommit, CodeBuild, CodeDeploy). It triggers on source changes, tracks artifacts in S3, and has native integration with ECS blue/green, Lambda, CloudFormation, and approval gates. GitHub Actions is a more general-purpose CI/CD platform that works with any cloud. For pure AWS workloads, CodePipeline integrates more natively; for multi-cloud or GitHub-centric teams, GitHub Actions with OIDC is commonly preferred.
