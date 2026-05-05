# Part 2: AWS CDK — Infrastructure as Code with Python

---

## 4.1 Introduction to AWS CDK

AWS CDK (Cloud Development Kit) lets you define cloud infrastructure using real programming languages — Python, TypeScript, Java, Go. CDK synthesizes to CloudFormation templates, giving you the power of a programming language with CloudFormation's reliability.

**CDK vs CloudFormation vs Terraform**:
| Feature | CDK | CloudFormation | Terraform |
|---------|-----|----------------|-----------|
| Language | Python/TS/Java/Go | YAML/JSON | HCL |
| Abstraction | High-level constructs | Low-level resources | Mid-level |
| Testing | pytest/jest | cfn-guard | terratest |
| State | CloudFormation stacks | CloudFormation stacks | terraform.tfstate |
| Multi-cloud | AWS only | AWS only | Yes |
| Learning curve | Medium | Medium | Medium |

---

## 4.2 CDK Setup

```bash
# Install CDK CLI
npm install -g aws-cdk

# Verify installation
cdk --version

# Bootstrap your AWS account (one-time per account/region)
cdk bootstrap aws://123456789012/us-east-1

# Create new Python CDK project
mkdir my-infra && cd my-infra
cdk init app --language=python

# Install Python dependencies
source .venv/bin/activate
pip install aws-cdk-lib constructs
pip install -r requirements.txt
```

### CDK Project Structure

```
my-infra/
├── app.py                    # CDK app entry point
├── my_infra/
│   ├── __init__.py
│   ├── network_stack.py      # VPC, subnets, SGs
│   ├── data_stack.py         # Databases
│   ├── app_stack.py          # ECS, Lambda
│   └── pipeline_stack.py    # CI/CD pipeline
├── tests/
│   ├── __init__.py
│   └── unit/
│       └── test_network_stack.py
├── cdk.json
└── requirements.txt
```

---

## 4.3 Core CDK Concepts

```python
# app.py — CDK app entry point
import aws_cdk as cdk
from my_infra.network_stack import NetworkStack
from my_infra.data_stack import DataStack
from my_infra.app_stack import AppStack

app = cdk.App()

# Environment definition
prod_env = cdk.Environment(account="123456789012", region="us-east-1")
dev_env = cdk.Environment(account="987654321098", region="us-east-1")

# Create stacks
network = NetworkStack(app, "ProdNetwork",
    env=prod_env,
    environment="prod",
)

data = DataStack(app, "ProdData",
    env=prod_env,
    environment="prod",
    vpc=network.vpc,
)

application = AppStack(app, "ProdApp",
    env=prod_env,
    environment="prod",
    vpc=network.vpc,
    aurora_cluster=data.aurora_cluster,
    image_tag="v1.2.3",
)

# Tag everything
cdk.Tags.of(app).add("ManagedBy", "CDK")
cdk.Tags.of(app).add("Environment", "prod")

app.synth()
```

---

## 4.4 VPC Stack

```python
# my_infra/network_stack.py
import aws_cdk as cdk
from aws_cdk import (
    aws_ec2 as ec2,
    aws_logs as logs,
    aws_iam as iam,
)
from constructs import Construct


class NetworkStack(cdk.Stack):
    
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        environment: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        # ── VPC ──────────────────────────────────────────
        self.vpc = ec2.Vpc(
            self, "VPC",
            vpc_name=f"myapp-{environment}",
            ip_addresses=ec2.IpAddresses.cidr("10.0.0.0/16"),
            max_azs=3,
            nat_gateways=3 if environment == "prod" else 1,
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="Public",
                    subnet_type=ec2.SubnetType.PUBLIC,
                    cidr_mask=24,
                    map_public_ip_on_launch=False,
                ),
                ec2.SubnetConfiguration(
                    name="Private",
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
                    cidr_mask=24,
                ),
                ec2.SubnetConfiguration(
                    name="Isolated",
                    subnet_type=ec2.SubnetType.PRIVATE_ISOLATED,
                    cidr_mask=24,
                ),
            ],
        )
        
        # ── VPC Endpoints ────────────────────────────────
        # S3 Gateway Endpoint (free, no NAT needed for S3)
        self.vpc.add_gateway_endpoint(
            "S3Endpoint",
            service=ec2.GatewayVpcEndpointAwsService.S3,
        )
        
        # DynamoDB Gateway Endpoint
        self.vpc.add_gateway_endpoint(
            "DynamoDBEndpoint",
            service=ec2.GatewayVpcEndpointAwsService.DYNAMODB,
        )
        
        # SSM Interface Endpoints (for Systems Manager in private subnets)
        for service_name in ["ssm", "ec2messages", "ssmmessages"]:
            self.vpc.add_interface_endpoint(
                f"{service_name.upper()}Endpoint",
                service=ec2.InterfaceVpcEndpointAwsService(
                    f"com.amazonaws.{self.region}.{service_name}"
                ),
                private_dns_enabled=True,
                subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            )
        
        # ── VPC Flow Logs ────────────────────────────────
        flow_log_group = logs.LogGroup(
            self, "FlowLogGroup",
            log_group_name=f"/aws/vpc/{environment}/flow-logs",
            retention=logs.RetentionDays.ONE_MONTH,
            removal_policy=cdk.RemovalPolicy.DESTROY,
        )
        
        flow_log_role = iam.Role(
            self, "FlowLogRole",
            assumed_by=iam.ServicePrincipal("vpc-flow-logs.amazonaws.com"),
        )
        flow_log_group.grant_write(flow_log_role)
        
        ec2.FlowLog(
            self, "FlowLog",
            resource_type=ec2.FlowLogResourceType.from_vpc(self.vpc),
            destination=ec2.FlowLogDestination.to_cloud_watch_logs(
                flow_log_group, flow_log_role
            ),
            traffic_type=ec2.FlowLogTrafficType.REJECT,   # Only log rejected traffic
        )
        
        # ── Outputs ──────────────────────────────────────
        cdk.CfnOutput(self, "VpcId", value=self.vpc.vpc_id)
        cdk.CfnOutput(
            self, "PrivateSubnetIds",
            value=",".join([s.subnet_id for s in self.vpc.private_subnets]),
        )
```

---

## 4.5 ECS Fargate Stack

```python
# my_infra/app_stack.py
import aws_cdk as cdk
from aws_cdk import (
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_ecs_patterns as ecs_patterns,
    aws_elasticloadbalancingv2 as elbv2,
    aws_iam as iam,
    aws_logs as logs,
    aws_rds as rds,
    aws_certificatemanager as acm,
    aws_route53 as route53,
    aws_route53_targets as targets,
    aws_autoscaling as autoscaling,
)
from constructs import Construct


class AppStack(cdk.Stack):
    
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        environment: str,
        vpc: ec2.Vpc,
        aurora_cluster: rds.DatabaseCluster,
        image_tag: str = "latest",
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        # ── ECS Cluster ──────────────────────────────────
        cluster = ecs.Cluster(
            self, "Cluster",
            vpc=vpc,
            cluster_name=f"myapp-{environment}",
            container_insights=True,
            enable_fargate_capacity_providers=True,
        )
        
        # ── Task Role ────────────────────────────────────
        task_role = iam.Role(
            self, "TaskRole",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
        )
        
        # Allow reading from Secrets Manager
        task_role.add_to_policy(iam.PolicyStatement(
            actions=["secretsmanager:GetSecretValue"],
            resources=[aurora_cluster.secret.secret_arn],
        ))
        
        # ── Task Definition ──────────────────────────────
        log_group = logs.LogGroup(
            self, "LogGroup",
            log_group_name=f"/ecs/myapp/{environment}",
            retention=logs.RetentionDays.ONE_MONTH,
            removal_policy=cdk.RemovalPolicy.DESTROY,
        )
        
        task_definition = ecs.FargateTaskDefinition(
            self, "TaskDef",
            cpu=512,
            memory_limit_mib=1024,
            task_role=task_role,
            runtime_platform=ecs.RuntimePlatform(
                operating_system_family=ecs.OperatingSystemFamily.LINUX,
                cpu_architecture=ecs.CpuArchitecture.ARM64,   # Graviton — cheaper
            ),
        )
        
        container = task_definition.add_container(
            "app",
            image=ecs.ContainerImage.from_registry(
                f"{self.account}.dkr.ecr.{self.region}.amazonaws.com/myapp:{image_tag}"
            ),
            logging=ecs.LogDrivers.aws_logs(
                log_group=log_group,
                stream_prefix="app",
            ),
            environment={
                "ENVIRONMENT": environment,
                "AWS_REGION": self.region,
            },
            secrets={
                "DATABASE_URL": ecs.Secret.from_secrets_manager(
                    aurora_cluster.secret, field="database_url"
                ),
            },
            health_check=ecs.HealthCheck(
                command=["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"],
                interval=cdk.Duration.seconds(30),
                timeout=cdk.Duration.seconds(5),
                retries=3,
                start_period=cdk.Duration.seconds(60),
            ),
            readonly_root_filesystem=True,
        )
        container.add_port_mappings(ecs.PortMapping(container_port=8000))
        
        # ── ALB Fargate Service ──────────────────────────
        # Use the L3 pattern construct for simplicity
        self.fargate_service = ecs_patterns.ApplicationLoadBalancedFargateService(
            self, "Service",
            cluster=cluster,
            task_definition=task_definition,
            desired_count=2,
            public_load_balancer=True,
            listener_port=443,
            redirect_http=True,
            assign_public_ip=False,
            task_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
            ),
            circuit_breaker=ecs.DeploymentCircuitBreaker(rollback=True),
        )
        
        # ── Auto Scaling ─────────────────────────────────
        scalable_target = self.fargate_service.service.auto_scale_task_count(
            min_capacity=2,
            max_capacity=20,
        )
        
        # CPU-based scaling
        scalable_target.scale_on_cpu_utilization(
            "CpuScaling",
            target_utilization_percent=70,
            scale_in_cooldown=cdk.Duration.seconds(300),
            scale_out_cooldown=cdk.Duration.seconds(60),
        )
        
        # Request-count-based scaling
        scalable_target.scale_on_request_count(
            "RequestScaling",
            requests_per_target=1000,
            target_group=self.fargate_service.target_group,
            scale_in_cooldown=cdk.Duration.seconds(300),
            scale_out_cooldown=cdk.Duration.seconds(60),
        )
        
        # ── DB Security Group Access ──────────────────────
        aurora_cluster.connections.allow_from(
            self.fargate_service.service,
            ec2.Port.tcp(5432),
            description="Allow ECS tasks to access Aurora",
        )
        
        # ── Outputs ──────────────────────────────────────
        cdk.CfnOutput(
            self, "ServiceURL",
            value=f"https://{self.fargate_service.load_balancer.load_balancer_dns_name}",
        )
```

---

## 4.6 CDK Commands

```bash
# Synthesize CloudFormation templates
cdk synth

# View diff before deploying
cdk diff ProdApp

# Deploy specific stack
cdk deploy ProdNetwork ProdData ProdApp --require-approval never

# Deploy all stacks
cdk deploy --all

# Destroy stacks (careful!)
cdk destroy ProdApp

# List all stacks
cdk ls

# Check for security-sensitive changes
cdk diff --security-only

# Generate CloudFormation template without deploying
cdk synth > template.yaml
```

---

## 4.7 CDK Testing

```python
# tests/unit/test_network_stack.py
import aws_cdk as cdk
from aws_cdk.assertions import Template, Match
from my_infra.network_stack import NetworkStack
import pytest


@pytest.fixture
def template():
    app = cdk.App()
    stack = NetworkStack(app, "TestNetwork", environment="test",
                         env=cdk.Environment(account="123456789012", region="us-east-1"))
    return Template.from_stack(stack)


def test_vpc_created(template):
    template.resource_count_is("AWS::EC2::VPC", 1)


def test_vpc_has_dns_enabled(template):
    template.has_resource_properties("AWS::EC2::VPC", {
        "EnableDnsHostnames": True,
        "EnableDnsSupport": True,
    })


def test_nat_gateway_exists(template):
    # Should have at least 1 NAT gateway
    template.resource_count_is("AWS::EC2::NatGateway", Match.any_value())


def test_flow_logs_configured(template):
    template.resource_count_is("AWS::EC2::FlowLog", 1)
    template.has_resource_properties("AWS::EC2::FlowLog", {
        "TrafficType": "REJECT",
    })


def test_s3_endpoint_exists(template):
    template.has_resource_properties("AWS::EC2::VPCEndpoint", {
        "ServiceName": Match.string_like_regexp(".*s3.*"),
        "VpcEndpointType": "Gateway",
    })
```

---

## 4.8 Interview Q&A

**Q: What are the three levels of CDK constructs?**
A: **L1 (Cfn resources)**: Direct 1:1 mapping to CloudFormation resources (e.g., `ec2.CfnVpc`). Full control, verbose. Use when no L2/L3 exists. **L2 (Curated constructs)**: Higher-level abstractions with defaults and helper methods (e.g., `ec2.Vpc`, `ecs.FargateTaskDefinition`). Most common usage. They set secure defaults (encryption, least-privilege). **L3 (Patterns)**: Multi-resource constructs solving complete use cases (e.g., `ecs_patterns.ApplicationLoadBalancedFargateService` creates ALB + ECS + security groups + IAM all at once). Great for prototyping, less flexible for production customization.

**Q: What is CDK bootstrapping and why is it required?**
A: Bootstrapping creates AWS resources CDK needs to operate: an S3 bucket (stores large CloudFormation templates and Lambda code assets), ECR repository (stores Docker images for Lambda/ECS deployments), IAM roles (allow CDK to perform deployments). Run `cdk bootstrap aws://ACCOUNT/REGION` once per account/region. For multi-account pipelines, you must bootstrap all target accounts and configure trust between the pipeline account and target accounts. Bootstrap resources are in a stack called `CDKToolkit`.

**Q: How do you share values between CDK stacks?**
A: Three approaches: (1) **Direct references**: Pass constructs as constructor parameters (`AppStack(app, "App", vpc=network.vpc)`) — CDK handles the dependency and creates CloudFormation exports automatically. (2) **SSM Parameter Store**: Store values in SSM and read them cross-stack with `ssm.StringParameter.value_from_lookup()`. Works across stacks deployed at different times. (3) **CloudFormation exports**: Use `cdk.Fn.import_value()` — creates hard coupling (can't delete exporting stack while import exists). Direct references are preferred within the same CDK app; SSM for cross-app sharing.
