# Chapter 13: Developer Tools — CodePipeline, CodeBuild, CodeDeploy & IaC
## CI/CD, Infrastructure as Code, and Developer Productivity on AWS

---

## 13.1 AWS Developer Tools Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                  AWS DEVELOPER TOOLS                                 │
├────────────────────────┬────────────────────────────────────────────┤
│ Source Control         │                                            │
│   CodeCommit           │ Managed Git repositories                  │
│   GitHub/Bitbucket     │ Third-party (natively integrated)         │
├────────────────────────┼────────────────────────────────────────────┤
│ Build                  │                                            │
│   CodeBuild            │ Managed build service (Docker-based)      │
├────────────────────────┼────────────────────────────────────────────┤
│ Deploy                 │                                            │
│   CodeDeploy           │ EC2, ECS, Lambda deployment automation    │
│   Elastic Beanstalk    │ PaaS — auto deploy + manage infra         │
├────────────────────────┼────────────────────────────────────────────┤
│ Pipeline               │                                            │
│   CodePipeline         │ Orchestrate Source→Build→Test→Deploy      │
│   GitHub Actions       │ Third-party CI/CD (OIDC auth to AWS)      │
├────────────────────────┼────────────────────────────────────────────┤
│ Infrastructure as Code │                                            │
│   CloudFormation       │ AWS native IaC (see Part 2)               │
│   CDK                  │ CloudFormation with code (see Part 2)     │
│   Terraform            │ Third-party multi-cloud IaC               │
├────────────────────────┼────────────────────────────────────────────┤
│ Tools                  │                                            │
│   Cloud9               │ Browser-based IDE                         │
│   CodeArtifact         │ Package repository (npm, Maven, pip)      │
│   CodeGuru             │ AI code review & profiling                │
│   X-Ray (Ch10)         │ Distributed tracing                       │
└────────────────────────┴────────────────────────────────────────────┘
```

---

## 13.2 CodeCommit

```bash
# Create repository
aws codecommit create-repository \
  --repository-name my-service \
  --repository-description "Backend microservice" \
  --tags Team=backend,Environment=prod

# Clone repository (HTTPS GRC — recommended)
git clone codecommit::us-east-1://my-service

# Or via HTTPS credentials helper
git config --global credential.helper '!aws codecommit credential-helper $@'
git config --global credential.UseHttpPath true
git clone https://git-codecommit.us-east-1.amazonaws.com/v1/repos/my-service

# Set up approval rules (require PR review)
aws codecommit create-approval-rule-template \
  --approval-rule-template-name require-2-approvers \
  --approval-rule-template-content '{
    "Version": "2018-11-08",
    "DestinationReferences": ["refs/heads/main"],
    "Statements": [{
      "Type": "Approvers",
      "NumberOfApprovalsNeeded": 2,
      "ApprovalPoolMembers": [
        "arn:aws:iam::123:role/developer"
      ]
    }]
  }'

# Attach approval rule template to repo
aws codecommit associate-approval-rule-template-with-repository \
  --approval-rule-template-name require-2-approvers \
  --repository-name my-service

# Create notification rule (trigger on PR events)
aws codestar-notifications create-notification-rule \
  --name pr-notifications \
  --resource arn:aws:codecommit:us-east-1:123:my-service \
  --detail-type FULL \
  --event-type-ids \
    codecommit-repository-pull-request-created \
    codecommit-repository-pull-request-merged \
    codecommit-repository-comments-on-pull-requests \
  --targets '[{"TargetType": "SNS", "TargetAddress": "arn:aws:sns:us-east-1:123:dev-notifications"}]'
```

---

## 13.3 CodeBuild

### buildspec.yml — The Build Definition

```yaml
# buildspec.yml (place at project root)
version: 0.2

env:
  variables:
    PYTHON_VERSION: "3.11"
    IMAGE_REPO_NAME: my-service
  parameter-store:
    SONAR_TOKEN: /build/sonar-token
  secrets-manager:
    DOCKER_PASSWORD: prod/docker/credentials:password

phases:
  install:
    runtime-versions:
      python: $PYTHON_VERSION
      nodejs: 18
    commands:
      - pip install poetry
      - poetry install --no-root
      - npm ci

  pre_build:
    commands:
      # Login to ECR
      - aws ecr get-login-password --region $AWS_DEFAULT_REGION | 
          docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_DEFAULT_REGION.amazonaws.com
      # Set image tags
      - COMMIT_HASH=$(echo $CODEBUILD_RESOLVED_SOURCE_VERSION | cut -c 1-8)
      - IMAGE_TAG=${COMMIT_HASH:=latest}
      - IMAGE_URI=$AWS_ACCOUNT_ID.dkr.ecr.$AWS_DEFAULT_REGION.amazonaws.com/$IMAGE_REPO_NAME:$IMAGE_TAG
      # Run tests
      - poetry run pytest tests/ --cov=src --cov-report=xml --junit-xml=test-results.xml -v

  build:
    commands:
      - docker build -t $IMAGE_REPO_NAME:latest .
      - docker tag $IMAGE_REPO_NAME:latest $IMAGE_URI
      - docker tag $IMAGE_REPO_NAME:latest $AWS_ACCOUNT_ID.dkr.ecr.$AWS_DEFAULT_REGION.amazonaws.com/$IMAGE_REPO_NAME:latest

  post_build:
    commands:
      - docker push $IMAGE_URI
      - docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_DEFAULT_REGION.amazonaws.com/$IMAGE_REPO_NAME:latest
      # Generate image definitions for ECS deployment
      - printf '[{"name":"%s","imageUri":"%s"}]' $IMAGE_REPO_NAME $IMAGE_URI > imagedefinitions.json
      # Generate imagedefinitions for CodeDeploy (blue/green)
      - printf '{"ImageURI":"%s"}' $IMAGE_URI > imageDetail.json

reports:
  test-report:
    files:
      - test-results.xml
    file-format: JUNITXML
  coverage-report:
    files:
      - coverage.xml
    file-format: COBERTURAXML

artifacts:
  files:
    - imagedefinitions.json
    - imageDetail.json
    - appspec.yaml
    - taskdef.json
  secondary-artifacts:
    SourceCode:
      files:
        - "**/*"
      base-directory: src

cache:
  paths:
    - /root/.cache/pip/**/*    # Cache pip packages
    - /root/.cache/pypoetry/** # Cache poetry packages
    - /usr/local/lib/node_modules/**/*
```

```bash
# Create CodeBuild project
aws codebuild create-project \
  --name my-service-build \
  --source '{
    "type": "CODECOMMIT",
    "location": "https://git-codecommit.us-east-1.amazonaws.com/v1/repos/my-service",
    "buildspec": "buildspec.yml"
  }' \
  --environment '{
    "type": "LINUX_CONTAINER",
    "image": "aws/codebuild/standard:7.0",
    "computeType": "BUILD_GENERAL1_MEDIUM",
    "privilegedMode": true,
    "environmentVariables": [
      {"name": "AWS_ACCOUNT_ID", "value": "123456789012"},
      {"name": "AWS_DEFAULT_REGION", "value": "us-east-1"}
    ]
  }' \
  --artifacts '{"type": "S3", "location": "my-build-artifacts", "name": "my-service"}' \
  --cache '{"type": "LOCAL", "modes": ["LOCAL_DOCKER_LAYER_CACHE", "LOCAL_SOURCE_CACHE", "LOCAL_CUSTOM_CACHE"]}' \
  --service-role arn:aws:iam::123:role/CodeBuildServiceRole \
  --logs-config '{
    "cloudWatchLogs": {
      "status": "ENABLED",
      "groupName": "/codebuild/my-service",
      "streamName": "{build_id}"
    }
  }'

# Start build manually
aws codebuild start-build \
  --project-name my-service-build \
  --source-version refs/heads/main

# Get build status
aws codebuild batch-get-builds --ids my-service-build:build-id
```

---

## 13.4 CodeDeploy

```bash
# Create CodeDeploy application
aws deploy create-application \
  --application-name my-service \
  --compute-platform ECS  # EC2/On-premises | ECS | Lambda

# Create deployment group for ECS (Blue/Green)
aws deploy create-deployment-group \
  --application-name my-service \
  --deployment-group-name prod \
  --service-role-arn arn:aws:iam::123:role/CodeDeployRole \
  --deployment-config-name CodeDeployDefault.ECSAllAtOnce \
  --blue-green-deployment-configuration '{
    "terminateBlueInstancesOnDeploymentSuccess": {
      "action": "TERMINATE",
      "terminationWaitTimeInMinutes": 60
    },
    "deploymentReadyOption": {
      "actionOnTimeout": "STOP_DEPLOYMENT",
      "waitTimeInMinutes": 30
    }
  }' \
  --ecs-services ServiceName=my-service,ClusterName=prod-cluster \
  --load-balancer-info '[{
    "targetGroupPairInfoList": [{
      "targetGroups": [
        {"name": "my-service-blue"},
        {"name": "my-service-green"}
      ],
      "prodTrafficRoute": {"listenerArns": ["arn:aws:elasticloadbalancing:us-east-1:123:listener/app/prod-alb/abc/listener-id"]},
      "testTrafficRoute": {"listenerArns": ["arn:aws:elasticloadbalancing:us-east-1:123:listener/app/prod-alb/abc/test-listener-id"]}
    }]
  }]'
```

### appspec.yaml for ECS Blue/Green

```yaml
# appspec.yaml
version: 0.0
Resources:
  - TargetService:
      Type: AWS::ECS::Service
      Properties:
        TaskDefinition: <TASK_DEFINITION>    # Placeholder filled by pipeline
        LoadBalancerInfo:
          ContainerName: "my-service"
          ContainerPort: 8000
        PlatformVersion: "LATEST"
        NetworkConfiguration:
          AwsvpcConfiguration:
            Subnets:
              - subnet-0abc123
              - subnet-0def456
            SecurityGroups:
              - sg-0abc123
            AssignPublicIp: "DISABLED"

Hooks:
  - BeforeInstall: "arn:aws:lambda:us-east-1:123:function:pre-deployment-check"
  - AfterInstall: "arn:aws:lambda:us-east-1:123:function:smoke-test"
  - AfterAllowTestTraffic: "arn:aws:lambda:us-east-1:123:function:integration-test"
  - BeforeAllowTraffic: "arn:aws:lambda:us-east-1:123:function:warm-up"
  - AfterAllowTraffic: "arn:aws:lambda:us-east-1:123:function:post-deployment-check"
```

### CodeDeploy for Lambda (traffic shifting)

```bash
# appspec.yaml for Lambda
cat > appspec.yaml << 'EOF'
version: 0.0
Resources:
  - myLambdaFunction:
      Type: AWS::Lambda::Function
      Properties:
        Name: "my-lambda"
        Alias: "live"
        CurrentVersion: "1"
        TargetVersion: "2"

Hooks:
  - BeforeAllowTraffic: "arn:aws:lambda:us-east-1:123:function:pre-traffic-hook"
  - AfterAllowTraffic: "arn:aws:lambda:us-east-1:123:function:post-traffic-hook"
EOF

# Deployment configs for Lambda
# CodeDeployDefault.LambdaAllAtOnce
# CodeDeployDefault.LambdaCanary10Percent5Minutes  — 10% for 5 min, then all
# CodeDeployDefault.LambdaLinear10PercentEvery1Minute — 10% more each minute
```

---

## 13.5 CodePipeline

```bash
# Create complete CI/CD pipeline
aws codepipeline create-pipeline \
  --pipeline '{
    "name": "my-service-pipeline",
    "roleArn": "arn:aws:iam::123:role/CodePipelineRole",
    "artifactStore": {
      "type": "S3",
      "location": "my-pipeline-artifacts"
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
            "RepositoryName": "my-service",
            "BranchName": "main",
            "DetectChanges": "true",
            "OutputArtifactFormat": "CODE_ZIP"
          },
          "outputArtifacts": [{"name": "SourceCode"}]
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
          "configuration": {
            "ProjectName": "my-service-build"
          },
          "inputArtifacts": [{"name": "SourceCode"}],
          "outputArtifacts": [{"name": "BuildOutput"}]
        }]
      },
      {
        "name": "Deploy-Staging",
        "actions": [{
          "name": "Deploy-to-Staging",
          "actionTypeId": {
            "category": "Deploy",
            "owner": "AWS",
            "provider": "ECS",
            "version": "1"
          },
          "configuration": {
            "ClusterName": "staging-cluster",
            "ServiceName": "my-service",
            "FileName": "imagedefinitions.json"
          },
          "inputArtifacts": [{"name": "BuildOutput"}]
        }]
      },
      {
        "name": "Approval",
        "actions": [{
          "name": "Manual-Approval",
          "actionTypeId": {
            "category": "Approval",
            "owner": "AWS",
            "provider": "Manual",
            "version": "1"
          },
          "configuration": {
            "NotificationArn": "arn:aws:sns:us-east-1:123:pipeline-approvals",
            "CustomData": "Approve deployment to production?",
            "ExternalEntityLink": "https://grafana.example.com/staging"
          }
        }]
      },
      {
        "name": "Deploy-Production",
        "actions": [{
          "name": "Deploy-Blue-Green",
          "actionTypeId": {
            "category": "Deploy",
            "owner": "AWS",
            "provider": "CodeDeployToECS",
            "version": "1"
          },
          "configuration": {
            "ApplicationName": "my-service",
            "DeploymentGroupName": "prod",
            "TaskDefinitionTemplateArtifact": "BuildOutput",
            "TaskDefinitionTemplatePath": "taskdef.json",
            "AppSpecTemplateArtifact": "BuildOutput",
            "AppSpecTemplatePath": "appspec.yaml",
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

## 13.6 GitHub Actions with AWS OIDC

Using OIDC (OpenID Connect) is the secure, recommended way — no long-lived AWS credentials in GitHub.

```bash
# Set up OIDC provider in AWS
aws iam create-open-id-connect-provider \
  --url https://token.actions.githubusercontent.com \
  --client-id-list sts.amazonaws.com \
  --thumbprint-list 6938fd4d98bab03faadb97b34396831e3780aea1

# Create IAM role for GitHub Actions
aws iam create-role \
  --role-name GitHubActionsDeployRole \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Federated": "arn:aws:iam::123456789012:oidc-provider/token.actions.githubusercontent.com"},
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
        },
        "StringLike": {
          "token.actions.githubusercontent.com:sub": "repo:my-org/my-service:*"
        }
      }
    }]
  }'

# Attach permissions to the role
aws iam attach-role-policy \
  --role-name GitHubActionsDeployRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonECR_FullAccess

aws iam attach-role-policy \
  --role-name GitHubActionsDeployRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonECS_FullAccess
```

```yaml
# .github/workflows/deploy.yml
name: Deploy to AWS

on:
  push:
    branches: [main]

env:
  AWS_REGION: us-east-1
  ECR_REPOSITORY: my-service
  ECS_SERVICE: my-service
  ECS_CLUSTER: prod-cluster
  CONTAINER_NAME: my-service

permissions:
  id-token: write    # Required for OIDC
  contents: read

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'
      
      - name: Install dependencies
        run: pip install -r requirements.txt
      
      - name: Run tests
        run: pytest tests/ --cov=src --cov-report=xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v4

  build-and-deploy:
    needs: test
    runs-on: ubuntu-latest
    environment: production
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Configure AWS credentials (OIDC — no secrets!)
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::123456789012:role/GitHubActionsDeployRole
          aws-region: ${{ env.AWS_REGION }}
      
      - name: Login to Amazon ECR
        id: login-ecr
        uses: aws-actions/amazon-ecr-login@v2
      
      - name: Build, tag, and push image to ECR
        id: build-image
        env:
          ECR_REGISTRY: ${{ steps.login-ecr.outputs.registry }}
          IMAGE_TAG: ${{ github.sha }}
        run: |
          docker build -t $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG .
          docker push $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG
          echo "image=$ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG" >> $GITHUB_OUTPUT
      
      - name: Download task definition
        run: |
          aws ecs describe-task-definition \
            --task-definition my-service \
            --query taskDefinition > task-definition.json
      
      - name: Update ECS task definition with new image
        id: task-def
        uses: aws-actions/amazon-ecs-render-task-definition@v1
        with:
          task-definition: task-definition.json
          container-name: ${{ env.CONTAINER_NAME }}
          image: ${{ steps.build-image.outputs.image }}
      
      - name: Deploy to ECS
        uses: aws-actions/amazon-ecs-deploy-task-definition@v1
        with:
          task-definition: ${{ steps.task-def.outputs.task-definition }}
          service: ${{ env.ECS_SERVICE }}
          cluster: ${{ env.ECS_CLUSTER }}
          wait-for-service-stability: true
          codedeploy-appspec: appspec.yaml
          codedeploy-application: my-service
          codedeploy-deployment-group: prod
```

---

## 13.7 AWS CDK Pipeline

```python
# cdk_pipeline.py — Self-mutating pipeline with CDK Pipelines
from aws_cdk import (
    Stack,
    aws_codepipeline as codepipeline,
    aws_codepipeline_actions as pipeline_actions,
    pipelines,
    Stage,
)
from constructs import Construct

class MyServiceStage(Stage):
    def __init__(self, scope: Construct, id: str, **kwargs):
        super().__init__(scope, id, **kwargs)
        # Your application stack
        MyServiceStack(self, "Service")

class PipelineStack(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs):
        super().__init__(scope, id, **kwargs)
        
        pipeline = pipelines.CodePipeline(
            self, "Pipeline",
            pipeline_name="my-service-pipeline",
            self_mutation=True,    # Pipeline updates itself on changes
            docker_enabled_for_synth=True,
            synth=pipelines.ShellStep(
                "Synth",
                input=pipelines.CodePipelineSource.git_hub(
                    "my-org/my-service",
                    "main",
                    authentication=SecretValue.secrets_manager("github-token")
                ),
                commands=[
                    "npm ci",
                    "npm run build",
                    "npx cdk synth"
                ]
            ),
            code_build_defaults=pipelines.CodeBuildOptions(
                build_environment=aws_codebuild.BuildEnvironment(
                    build_image=aws_codebuild.LinuxBuildImage.STANDARD_7_0
                )
            )
        )
        
        # Add staging environment
        staging = pipeline.add_stage(
            MyServiceStage(self, "Staging", env={"account": "123", "region": "us-east-1"}),
            post=[
                pipelines.ShellStep(
                    "IntegrationTests",
                    commands=["python -m pytest tests/integration/ -v"],
                    env_from_cfn_outputs={"ENDPOINT_URL": staging_stack.api_url}
                )
            ]
        )
        
        # Manual approval before prod
        pipeline.add_stage(
            MyServiceStage(self, "Production", env={"account": "456", "region": "us-east-1"}),
            pre=[pipelines.ManualApprovalStep("Approve-Production")]
        )
```

---

## 13.8 CodeArtifact — Private Package Registry

```bash
# Create domain and repository
aws codeartifact create-domain --domain my-company

aws codeartifact create-repository \
  --domain my-company \
  --domain-owner 123456789012 \
  --repository my-packages

# Create upstream (proxy PyPI)
aws codeartifact create-repository \
  --domain my-company \
  --repository pypi-store \
  --upstreams '[]'

aws codeartifact associate-external-connection \
  --domain my-company \
  --repository pypi-store \
  --external-connection public:pypi

aws codeartifact update-repository \
  --domain my-company \
  --repository my-packages \
  --upstreams repositoryName=pypi-store

# Login and use (pip)
aws codeartifact login \
  --tool pip \
  --repository my-packages \
  --domain my-company \
  --domain-owner 123456789012

pip install requests  # Downloads from CodeArtifact (proxied from PyPI)
pip install my-internal-package  # Uploads/downloads internal packages

# Publish package
pip install twine
python setup.py sdist bdist_wheel
twine upload --repository codeartifact dist/*
```

---

## 13.9 Interview Q&A

**Q: What is the difference between CodeDeploy deployment strategies?**
A: Three strategies: (1) In-Place — stops app on existing instances, deploys new version (downtime, rolling possible with ALB deregistration); (2) Blue/Green for EC2 — new instances created, traffic shifted via ALB, old instances terminated after stabilization; (3) Blue/Green for ECS — new task set created, traffic shifted to new containers, old task set terminated. For Lambda: AllAtOnce, Canary (e.g., 10% for 5 min then 100%), or Linear (e.g., 10% more every minute). Blue/Green for ECS/Lambda has no downtime; in-place is simpler but has risk.

**Q: Why should you use OIDC instead of IAM access keys in GitHub Actions?**
A: Long-lived IAM access keys are security risks — they can be leaked (committed to Git, logged), rotated infrequently, and hard to audit. OIDC provides short-lived tokens (15 min expiry) that are automatically refreshed per workflow run. No secret storage in GitHub is required (no AWS_ACCESS_KEY_ID/SECRET). The trust is scoped to specific repos/branches via conditions in the IAM role trust policy. OIDC eliminates the key management overhead and reduces the blast radius of credential theft.

**Q: What is CodeBuild local cache and when should you use it?**
A: Local caching (LOCAL_DOCKER_LAYER_CACHE, LOCAL_SOURCE_CACHE, LOCAL_CUSTOM_CACHE) stores build artifacts within the CodeBuild fleet. Faster than S3 cache (no round-trip), but ephemeral — lost when the build host is recycled. Use local cache for Docker layer caching (huge speedup for iterative Docker builds), source cache (skip re-downloading large codebases), and custom cache (pip/npm cache). Use S3 cache when you need cache persistence across build hosts. Combine both for maximum speed.

**Q: How does a CDK Pipeline self-mutate?**
A: CDK Pipelines has a "SelfMutation" stage that runs `cdk deploy` on the pipeline stack itself at the beginning of each pipeline run. This means changes to pipeline structure (adding stages, changing build commands) are automatically applied without manual redeployment. The pipeline essentially updates itself before processing the rest of the pipeline stages. This is powerful for infrastructure-as-code because your pipeline definition lives in the same repo as your app code.

**Q: What is the purpose of the post_build phase in buildspec.yml?**
A: post_build runs regardless of whether the build phase succeeded. Use it for: pushing Docker images (after successful build), generating deployment artifacts (imagedefinitions.json for ECS), publishing test results, sending notifications, and cleanup. Critical: Docker push happens in post_build to ensure the image is pushed even if later steps fail. The `finally` block (nested in any phase) runs unconditionally — useful for cleanup scripts.

**Q: How does CodePipeline connect to GitHub?**
A: Three options: (1) CodeStar Connections (recommended) — OAuth-based, creates an AWS resource that manages the GitHub app authorization, supports GitHub/GitHub Enterprise/Bitbucket; (2) GitHub action using personal access token stored in Secrets Manager; (3) Webhook + S3 source (legacy). CodeStar Connections is preferred because it uses the GitHub app model (no personal tokens), and the connection is an AWS resource that can be managed via IAM policies.
