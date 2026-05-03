# Part II: AWS CDK (Cloud Development Kit)
## Complete Detailed Guide for Beginners

---

# Chapter 10: Introduction to AWS CDK

## 10.1 What is Infrastructure as Code (IaC)?

### The Problem with Manual Setup

Imagine setting up a website. You'd need to:
1. Create a server
2. Configure the network
3. Set up a database
4. Configure security
5. Set up backups
6. And much more...

**Traditional approach:** Click through AWS Console (web interface)
- Slow
- Error-prone
- Hard to replicate
- No version control

### The Solution: Infrastructure as Code

Write code that describes what you want, and let the computer set it up.

```
Traditional:
Developer → Clicks in AWS Console → Resources Created
(Manual, slow, error-prone)

Infrastructure as Code:
Developer → Writes Code → Runs Command → Resources Created
(Automated, fast, consistent, version-controlled)
```

### Benefits of IaC

```
┌─────────────────────────────────────────────────────────────┐
│                    INFRASTRUCTURE AS CODE                   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ✅ Version Control  - Track changes like regular code     │
│                                                             │
│  ✅ Reproducibility  - Same code = Same infrastructure     │
│                                                             │
│  ✅ Automation       - Deploy with one command             │
│                                                             │
│  ✅ Documentation    - Code IS the documentation           │
│                                                             │
│  ✅ Testing          - Test infrastructure before deploying│
│                                                             │
│  ✅ Collaboration    - Teams can work on same codebase     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 10.2 CDK vs CloudFormation vs Terraform

### Comparison Table

| Feature | AWS CDK | CloudFormation | Terraform |
|---------|---------|----------------|-----------|
| Language | Python, TypeScript, Java, C# | YAML/JSON | HCL (Terraform Language) |
| Learning Curve | Medium | High | Medium |
| Cloud Support | AWS only | AWS only | Multi-cloud |
| Abstraction Level | High | Low | Medium |
| Reusability | Excellent (constructs) | Limited | Good (modules) |
| Testing | Native | Limited | Good |

### Code Comparison - Creating an S3 Bucket

**CloudFormation (YAML):**
```yaml
Resources:
  MyBucket:
    Type: AWS::S3::Bucket
    Properties:
      BucketName: my-bucket
      VersioningConfiguration:
        Status: Enabled
      BucketEncryption:
        ServerSideEncryptionConfiguration:
          - ServerSideEncryptionByDefault:
              SSEAlgorithm: AES256
```

**Terraform (HCL):**
```hcl
resource "aws_s3_bucket" "my_bucket" {
  bucket = "my-bucket"
}

resource "aws_s3_bucket_versioning" "versioning" {
  bucket = aws_s3_bucket.my_bucket.id
  versioning_configuration {
    status = "Enabled"
  }
}
```

**AWS CDK (Python):**
```python
from aws_cdk import aws_s3 as s3

bucket = s3.Bucket(
    self, "MyBucket",
    versioned=True,
    encryption=s3.BucketEncryption.S3_MANAGED
)
```

**Winner:** CDK requires the least code and is most readable!

### When to Use Each

```
Choose CDK when:
- You know Python, TypeScript, or Java
- You're building on AWS only
- You want high-level abstractions
- You want to reuse code with constructs

Choose Terraform when:
- You need multi-cloud support
- Your team already knows HCL
- You need provider flexibility

Choose CloudFormation when:
- You need direct AWS support
- You prefer declarative YAML/JSON
- You're already using it
```

---

## 10.3 CDK Concepts: Apps, Stacks, Constructs

### The CDK Hierarchy

```
┌─────────────────────────────────────────────────┐
│                      APP                         │
│  (Your entire CDK application)                  │
│                                                  │
│    ┌─────────────────┐    ┌─────────────────┐   │
│    │     STACK 1     │    │     STACK 2     │   │
│    │ (Deployment unit)│    │ (Deployment unit)│   │
│    │                  │    │                  │   │
│    │  ┌───────────┐  │    │  ┌───────────┐  │   │
│    │  │ Construct │  │    │  │ Construct │  │   │
│    │  │ (Lambda)  │  │    │  │ (DynamoDB)│  │   │
│    │  └───────────┘  │    │  └───────────┘  │   │
│    │                  │    │                  │   │
│    │  ┌───────────┐  │    │  ┌───────────┐  │   │
│    │  │ Construct │  │    │  │ Construct │  │   │
│    │  │ (API GW)  │  │    │  │ (S3)      │  │   │
│    │  └───────────┘  │    │  └───────────┘  │   │
│    └─────────────────┘    └─────────────────┘   │
│                                                  │
└─────────────────────────────────────────────────┘
```

### Understanding Each Component

**1. App (Application)**
```python
# The root of your CDK application
# Contains one or more stacks

from aws_cdk import App

app = App()

# Add stacks to the app
WebStack(app, "WebStack")
DatabaseStack(app, "DatabaseStack")

app.synth()  # Generate CloudFormation
```

**2. Stack**
```python
# A deployment unit - resources that deploy together
# Maps to a CloudFormation stack

from aws_cdk import Stack
from constructs import Construct

class MyStack(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs):
        super().__init__(scope, id, **kwargs)
        
        # Add resources here
        # Everything in this class deploys together
```

**3. Construct**
```python
# A cloud component (Lambda, S3, DynamoDB, etc.)
# The building blocks of your infrastructure

from aws_cdk import aws_s3 as s3

# This is a construct
bucket = s3.Bucket(self, "MyBucket")
```

### Real-World Analogy

```
App = A House
├── Stack 1 = Kitchen
│   ├── Construct = Refrigerator
│   ├── Construct = Stove
│   └── Construct = Sink
│
└── Stack 2 = Bedroom
    ├── Construct = Bed
    ├── Construct = Closet
    └── Construct = Lamp
```

---

## 10.4 Installation and Prerequisites

### Step 1: Prerequisites

```bash
# You need:
# 1. Node.js (for CDK CLI)
node --version  # Should be 14.x or higher

# 2. Python 3.7+ (for Python CDK)
python --version

# 3. AWS CLI configured
aws --version
aws configure  # Enter your AWS credentials
```

### Step 2: Install CDK CLI

```bash
# Install globally with npm
npm install -g aws-cdk

# Verify installation
cdk --version
```

### Step 3: Create a New CDK Project

```bash
# Create project directory
mkdir my-cdk-project
cd my-cdk-project

# Initialize Python CDK project
cdk init app --language python

# This creates:
# ├── app.py              # Entry point
# ├── cdk.json            # CDK config
# ├── my_cdk_project/     # Your stack code
# │   ├── __init__.py
# │   └── my_cdk_project_stack.py
# ├── requirements.txt
# └── tests/              # Test files
```

### Step 4: Set Up Python Environment

```bash
# Create virtual environment
python -m venv .venv

# Activate it
# Windows:
.venv\Scripts\activate
# Mac/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Step 5: Bootstrap Your AWS Account

```bash
# First-time setup for CDK in your AWS account
# This creates an S3 bucket for CDK assets
cdk bootstrap aws://ACCOUNT_ID/REGION

# Example:
cdk bootstrap aws://123456789012/us-east-1
```

---

## 10.5 CDK CLI Commands

### Essential Commands

```bash
# See all available commands
cdk --help

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# COMMON COMMANDS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# List all stacks in the app
cdk list
# Output: MyStack

# Generate CloudFormation template (without deploying)
cdk synth
# Creates: cdk.out/MyStack.template.json

# Compare deployed stack with current code
cdk diff
# Shows what will change

# Deploy the stack to AWS
cdk deploy
# Actually creates/updates resources in AWS

# Deploy specific stack
cdk deploy MyStack

# Deploy all stacks
cdk deploy --all

# Delete the stack from AWS
cdk destroy

# Open AWS CloudFormation console
cdk console
```

### Command Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                       CDK WORKFLOW                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   cdk synth                                                 │
│       │                                                     │
│       ▼                                                     │
│   ┌───────────────────┐                                     │
│   │ Python/TypeScript │ → CloudFormation Template          │
│   │      Code         │                                     │
│   └───────────────────┘                                     │
│                                                             │
│   cdk diff                                                  │
│       │                                                     │
│       ▼                                                     │
│   ┌───────────────────┐                                     │
│   │ Compare with      │ → Shows changes                    │
│   │ deployed stack    │                                     │
│   └───────────────────┘                                     │
│                                                             │
│   cdk deploy                                                │
│       │                                                     │
│       ▼                                                     │
│   ┌───────────────────┐                                     │
│   │ CloudFormation    │ → AWS Resources Created            │
│   │ deploys template  │                                     │
│   └───────────────────┘                                     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 10.6 Your First CDK App

### Step 1: Project Structure

After `cdk init app --language python`:

```
my-first-cdk/
├── app.py                          # Entry point
├── cdk.json                        # CDK configuration
├── my_first_cdk/
│   ├── __init__.py
│   └── my_first_cdk_stack.py       # Your stack definition
├── tests/
│   └── test_my_first_cdk.py
└── requirements.txt
```

### Step 2: Understanding app.py

```python
#!/usr/bin/env python3
# app.py - The entry point for your CDK application

import aws_cdk as cdk
from my_first_cdk.my_first_cdk_stack import MyFirstCdkStack

# Create the app
app = cdk.App()

# Create stack(s)
MyFirstCdkStack(app, "MyFirstCdkStack")

# Synthesize CloudFormation template
app.synth()
```

### Step 3: Create Your First Stack

```python
# my_first_cdk/my_first_cdk_stack.py

from aws_cdk import (
    Stack,
    aws_s3 as s3,
    aws_lambda as _lambda,
    Duration,
    RemovalPolicy,
)
from constructs import Construct

class MyFirstCdkStack(Stack):
    """
    My first CDK stack - creates a simple S3 bucket
    and a Lambda function.
    """
    
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        # Create an S3 bucket
        bucket = s3.Bucket(
            self, "MyFirstBucket",
            versioned=True,                      # Enable versioning
            removal_policy=RemovalPolicy.DESTROY, # Delete when stack is deleted
            auto_delete_objects=True             # Empty bucket before deletion
        )
        
        # Create a Lambda function
        my_lambda = _lambda.Function(
            self, "HelloHandler",
            runtime=_lambda.Runtime.PYTHON_3_9,
            code=_lambda.Code.from_inline("""
def handler(event, context):
    return {
        'statusCode': 200,
        'body': 'Hello from CDK!'
    }
            """),
            handler="index.handler",
            timeout=Duration.seconds(30)
        )
```

### Step 4: Deploy Your Stack

```bash
# 1. See what will be created
cdk diff

# Output:
# Stack MyFirstCdkStack
# Resources
# [+] AWS::S3::Bucket MyFirstBucket
# [+] AWS::Lambda::Function HelloHandler

# 2. Deploy to AWS
cdk deploy

# You'll see:
# ✅  MyFirstCdkStack
# 
# Outputs:
# MyFirstCdkStack.BucketName = myfirstcdkstack-myfirstbucket-xxx

# 3. Test your Lambda
aws lambda invoke --function-name HelloHandler output.json
cat output.json
# {"statusCode": 200, "body": "Hello from CDK!"}
```

### Step 5: Clean Up

```bash
# Delete all resources
cdk destroy

# Confirm with 'y'
# All AWS resources will be deleted
```

### Complete First App Example

```python
# A more complete example

from aws_cdk import (
    Stack,
    aws_s3 as s3,
    aws_lambda as _lambda,
    aws_apigateway as apigw,
    Duration,
    CfnOutput,
)
from constructs import Construct

class HelloWorldStack(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs):
        super().__init__(scope, id, **kwargs)
        
        # Lambda function
        hello_lambda = _lambda.Function(
            self, "HelloFunction",
            runtime=_lambda.Runtime.PYTHON_3_9,
            handler="index.handler",
            code=_lambda.Code.from_inline("""
def handler(event, context):
    name = event.get('queryStringParameters', {}).get('name', 'World')
    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json'},
        'body': f'{{"message": "Hello, {name}!"}}'
    }
            """)
        )
        
        # API Gateway to expose the Lambda
        api = apigw.LambdaRestApi(
            self, "HelloApi",
            handler=hello_lambda,
            rest_api_name="Hello Service"
        )
        
        # Output the API URL
        CfnOutput(
            self, "ApiUrl",
            value=api.url,
            description="API Gateway URL"
        )
```

After deploying, you can access: `https://xxx.execute-api.region.amazonaws.com/prod/?name=Alice`

---

# Chapter 11: CDK Fundamentals

## 11.1 Constructs (L1, L2, L3)

### What are Constructs?

Constructs are the building blocks of CDK. They represent AWS resources and come in three levels:

```
┌─────────────────────────────────────────────────────────────┐
│                    CONSTRUCT LEVELS                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   L3 (Patterns)     ← Highest Level - Complete solutions   │
│   ┌────────────────────────────────────────┐                │
│   │ LambdaRestApi = Lambda + API Gateway   │                │
│   │ + Permissions + Logging all in one     │                │
│   └────────────────────────────────────────┘                │
│                                                              │
│   L2 (High-Level)   ← Most Common - Sensible defaults      │
│   ┌────────────────────────────────────────┐                │
│   │ s3.Bucket(), lambda.Function()         │                │
│   │ Easy to use, handles complexity        │                │
│   └────────────────────────────────────────┘                │
│                                                              │
│   L1 (CFN)          ← Lowest Level - Raw CloudFormation    │
│   ┌────────────────────────────────────────┐                │
│   │ CfnBucket(), CfnFunction()             │                │
│   │ Full control, no abstractions          │                │
│   └────────────────────────────────────────┘                │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### L1 Constructs (CFN Resources)

Direct mapping to CloudFormation. Prefixed with `Cfn`.

```python
from aws_cdk import aws_s3 as s3

# L1 - Full control, verbose
bucket = s3.CfnBucket(
    self, "MyBucket",
    bucket_name="my-bucket",
    versioning_configuration=s3.CfnBucket.VersioningConfigurationProperty(
        status="Enabled"
    )
)
```

### L2 Constructs (Higher-Level)

Easier to use with sensible defaults.

```python
from aws_cdk import aws_s3 as s3

# L2 - Simple and clean
bucket = s3.Bucket(
    self, "MyBucket",
    versioned=True  # That's it!
)

# L2 provides helper methods
bucket.grant_read(my_lambda)  # Easy permissions!
```

### L3 Constructs (Patterns)

Complete solutions combining multiple resources.

```python
from aws_cdk import aws_apigateway as apigw

# L3 - Complete API with Lambda backend
api = apigw.LambdaRestApi(
    self, "MyApi",
    handler=my_lambda
)
# This creates:
# - API Gateway
# - Lambda integration
# - IAM permissions
# - All wired together!
```

### When to Use Each Level

```
L3: Quick start, standard patterns
    "I need a Lambda with API Gateway"

L2: Most cases, good defaults with customization
    "I need an S3 bucket with specific settings"

L1: Maximum control, complex scenarios
    "I need features not yet in L2"
```

---

## 11.2 Stacks and Environments

### What is a Stack?

A stack is a unit of deployment. All resources in a stack are deployed and deleted together.

```python
from aws_cdk import Stack, App
from constructs import Construct

class NetworkStack(Stack):
    """VPC and networking resources."""
    def __init__(self, scope: Construct, id: str, **kwargs):
        super().__init__(scope, id, **kwargs)
        # Network resources

class DatabaseStack(Stack):
    """Database resources."""
    def __init__(self, scope: Construct, id: str, **kwargs):
        super().__init__(scope, id, **kwargs)
        # Database resources

class ApplicationStack(Stack):
    """Application resources."""
    def __init__(self, scope: Construct, id: str, **kwargs):
        super().__init__(scope, id, **kwargs)
        # Application resources

# app.py
app = App()
NetworkStack(app, "Network")
DatabaseStack(app, "Database")
ApplicationStack(app, "Application")
```

### Environments

Deploy to specific AWS accounts and regions.

```python
from aws_cdk import App, Environment

app = App()

# Environment for development
dev_env = Environment(
    account="111111111111",
    region="us-east-1"
)

# Environment for production
prod_env = Environment(
    account="222222222222",
    region="us-west-2"
)

# Deploy to dev
MyStack(app, "DevStack", env=dev_env)

# Deploy to prod
MyStack(app, "ProdStack", env=prod_env)
```

### Deploying to Specific Environment

```bash
# Deploy dev stack
cdk deploy DevStack

# Deploy prod stack
cdk deploy ProdStack

# Deploy all
cdk deploy --all
```

---

## 11.3 Assets

### What are Assets?

Assets are local files (code, data) that CDK uploads to AWS during deployment.

```python
from aws_cdk import aws_lambda as _lambda

# Lambda code from local directory
lambda_fn = _lambda.Function(
    self, "MyFunction",
    runtime=_lambda.Runtime.PYTHON_3_9,
    handler="main.handler",
    code=_lambda.Code.from_asset("./lambda")  # Local folder
)

# S3 asset deployment
from aws_cdk import aws_s3_deployment as s3deploy

s3deploy.BucketDeployment(
    self, "DeployWebsite",
    sources=[s3deploy.Source.asset("./website")],  # Local files
    destination_bucket=my_bucket
)
```

### Asset Flow

```
Local Files (./lambda/)
        ↓
    cdk deploy
        ↓
CDK zips and uploads to S3 (CDK Bootstrap bucket)
        ↓
Lambda references the S3 location
        ↓
Lambda deployed with your code
```

---

## 11.4 Context and Parameters

### Context Values

Configuration that can change between deployments.

```python
# cdk.json
{
  "context": {
    "environment": "dev",
    "bucket_name": "my-dev-bucket"
  }
}

# In your stack
environment = self.node.try_get_context("environment")
bucket_name = self.node.try_get_context("bucket_name")

# Command line override
cdk deploy -c environment=prod -c bucket_name=my-prod-bucket
```

### Stack Parameters (CloudFormation Parameters)

```python
from aws_cdk import CfnParameter

# Define parameter
bucket_name_param = CfnParameter(
    self, "BucketName",
    type="String",
    description="Name of the S3 bucket",
    default="my-default-bucket"
)

# Use parameter
bucket = s3.Bucket(
    self, "MyBucket",
    bucket_name=bucket_name_param.value_as_string
)
```

---

## 11.5 Tokens and Lazy Values

### What are Tokens?

Tokens are placeholders for values that aren't known until deployment time.

```python
from aws_cdk import aws_s3 as s3

bucket = s3.Bucket(self, "MyBucket")

# bucket.bucket_name is a TOKEN, not the actual name yet!
print(bucket.bucket_name)  
# Output: ${Token[TOKEN.123]}

# It gets resolved during deployment
```

### Why Tokens?

```
When CDK runs (your computer):
  bucket.bucket_name = "${Token[123]}"
  
When CloudFormation deploys:
  bucket.bucket_name = "my-actual-bucket-name-abc123"
```

### Using Tokens

```python
# Passing to other resources
lambda_fn = _lambda.Function(
    self, "MyFunction",
    environment={
        "BUCKET_NAME": bucket.bucket_name  # Token - resolved at deploy
    }
)

# Tokens work automatically in CDK!
```

---

## 11.6 Cross-Stack References

### Sharing Resources Between Stacks

```python
# Stack 1: Creates a VPC
class NetworkStack(Stack):
    def __init__(self, scope, id, **kwargs):
        super().__init__(scope, id, **kwargs)
        
        # Create VPC
        self.vpc = ec2.Vpc(self, "MyVpc", max_azs=2)
        # ↑ self.vpc makes it accessible from outside

# Stack 2: Uses the VPC from Stack 1
class ApplicationStack(Stack):
    def __init__(self, scope, id, vpc: ec2.Vpc, **kwargs):
        super().__init__(scope, id, **kwargs)
        #              ↑ Receives VPC as parameter
        
        # Use the VPC from NetworkStack
        cluster = ecs.Cluster(self, "Cluster", vpc=vpc)

# app.py
app = App()

network_stack = NetworkStack(app, "NetworkStack")

# Pass VPC to ApplicationStack
app_stack = ApplicationStack(
    app, "AppStack",
    vpc=network_stack.vpc  # Reference from other stack
)

# Make app_stack depend on network_stack
app_stack.add_dependency(network_stack)
```

### How It Works

```
NetworkStack
    ├── Creates VPC
    └── Exports: VPC ID (stored in AWS)
         ↓
ApplicationStack
    └── Imports: VPC ID (retrieved from AWS)
```

---

*Continue to Chapter 12-16 for more AWS CDK topics...*
