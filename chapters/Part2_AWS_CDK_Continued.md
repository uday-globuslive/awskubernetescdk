# Part 2 (Continued): AWS CDK — Advanced Patterns and CDK Pipelines

---

## 5.1 Lambda Functions with CDK

```python
# my_infra/lambda_stack.py
import aws_cdk as cdk
from aws_cdk import (
    aws_lambda as lambda_,
    aws_lambda_event_sources as event_sources,
    aws_apigatewayv2 as apigwv2,
    aws_apigatewayv2_integrations as integrations,
    aws_dynamodb as dynamodb,
    aws_sqs as sqs,
    aws_iam as iam,
    aws_logs as logs,
)
from constructs import Construct


class LambdaStack(cdk.Stack):
    
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        environment: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        # ── DynamoDB Table ───────────────────────────────
        self.table = dynamodb.TableV2(
            self, "OrdersTable",
            table_name=f"orders-{environment}",
            partition_key=dynamodb.Attribute(name="PK", type=dynamodb.AttributeType.STRING),
            sort_key=dynamodb.Attribute(name="SK", type=dynamodb.AttributeType.STRING),
            billing=dynamodb.Billing.on_demand(),
            point_in_time_recovery=True,
            encryption=dynamodb.TableEncryptionV2.aws_managed_key(),
            removal_policy=cdk.RemovalPolicy.RETAIN if environment == "prod" else cdk.RemovalPolicy.DESTROY,
            global_secondary_indexes=[
                dynamodb.GlobalSecondaryIndexPropsV2(
                    index_name="GSI1",
                    partition_key=dynamodb.Attribute(name="GSI1PK", type=dynamodb.AttributeType.STRING),
                    sort_key=dynamodb.Attribute(name="GSI1SK", type=dynamodb.AttributeType.STRING),
                )
            ],
            dynamo_stream=dynamodb.StreamViewType.NEW_AND_OLD_IMAGES,
        )
        
        # ── SQS Dead Letter Queue ────────────────────────
        dlq = sqs.Queue(
            self, "OrdersDLQ",
            queue_name=f"orders-dlq-{environment}",
            encryption=sqs.QueueEncryption.KMS_MANAGED,
            retention_period=cdk.Duration.days(14),
        )
        
        orders_queue = sqs.Queue(
            self, "OrdersQueue",
            queue_name=f"orders-{environment}",
            encryption=sqs.QueueEncryption.KMS_MANAGED,
            visibility_timeout=cdk.Duration.seconds(300),
            dead_letter_queue=sqs.DeadLetterQueue(
                max_receive_count=3,
                queue=dlq,
            ),
        )
        
        # ── Lambda Layer ─────────────────────────────────
        dependencies_layer = lambda_.LayerVersion(
            self, "DependenciesLayer",
            layer_version_name=f"myapp-deps-{environment}",
            code=lambda_.Code.from_asset("lambda_layers/dependencies"),
            compatible_runtimes=[lambda_.Runtime.PYTHON_3_11],
            compatible_architectures=[lambda_.Architecture.ARM_64],
            description="Common Python dependencies",
            removal_policy=cdk.RemovalPolicy.RETAIN,
        )
        
        # ── API Lambda Function ──────────────────────────
        api_function = lambda_.Function(
            self, "ApiFunction",
            function_name=f"orders-api-{environment}",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="app.handler",
            code=lambda_.Code.from_asset(
                "src/api",
                bundling=cdk.BundlingOptions(
                    image=lambda_.Runtime.PYTHON_3_11.bundling_image,
                    command=[
                        "bash", "-c",
                        "pip install -r requirements.txt -t /asset-output && cp -r . /asset-output"
                    ],
                ),
            ),
            architecture=lambda_.Architecture.ARM_64,
            memory_size=512,
            timeout=cdk.Duration.seconds(29),
            environment={
                "ORDERS_TABLE": self.table.table_name,
                "QUEUE_URL": orders_queue.queue_url,
                "ENVIRONMENT": environment,
                "POWERTOOLS_SERVICE_NAME": "orders-api",
                "LOG_LEVEL": "INFO",
            },
            layers=[dependencies_layer],
            tracing=lambda_.Tracing.ACTIVE,
            insights_version=lambda_.LambdaInsightsVersion.VERSION_1_0_229_0,
            log_retention=logs.RetentionDays.ONE_MONTH,
        )
        
        # Grant DynamoDB permissions
        self.table.grant_read_write_data(api_function)
        orders_queue.grant_send_messages(api_function)
        
        # ── Worker Lambda Function ───────────────────────
        worker_function = lambda_.Function(
            self, "WorkerFunction",
            function_name=f"orders-worker-{environment}",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="worker.handler",
            code=lambda_.Code.from_asset("src/worker"),
            architecture=lambda_.Architecture.ARM_64,
            memory_size=1024,
            timeout=cdk.Duration.seconds(300),
            environment={
                "ORDERS_TABLE": self.table.table_name,
                "ENVIRONMENT": environment,
            },
            layers=[dependencies_layer],
            tracing=lambda_.Tracing.ACTIVE,
        )
        
        self.table.grant_write_data(worker_function)
        
        # Add SQS event source
        worker_function.add_event_source(
            event_sources.SqsEventSource(
                orders_queue,
                batch_size=10,
                max_batching_window=cdk.Duration.seconds(5),
                report_batch_item_failures=True,
            )
        )
        
        # ── HTTP API Gateway ─────────────────────────────
        self.api = apigwv2.HttpApi(
            self, "HttpApi",
            api_name=f"orders-api-{environment}",
            cors_preflight=apigwv2.CorsPreflightOptions(
                allow_methods=[apigwv2.CorsHttpMethod.ANY],
                allow_headers=["*"],
                allow_origins=["https://myapp.com"] if environment == "prod" else ["*"],
                max_age=cdk.Duration.seconds(300),
            ),
            default_authorizer=self._create_jwt_authorizer(environment),
        )
        
        lambda_integration = integrations.HttpLambdaIntegration(
            "LambdaIntegration",
            api_function,
            payload_format_version=apigwv2.PayloadFormatVersion.VERSION_2_0,
        )
        
        self.api.add_routes(
            path="/{proxy+}",
            methods=[apigwv2.HttpMethod.ANY],
            integration=lambda_integration,
        )
        
        cdk.CfnOutput(self, "ApiEndpoint", value=self.api.api_endpoint)
    
    def _create_jwt_authorizer(self, environment: str) -> apigwv2.IHttpRouteAuthorizer:
        from aws_cdk import aws_cognito as cognito
        
        user_pool = cognito.UserPool(
            self, "UserPool",
            user_pool_name=f"myapp-{environment}",
            self_sign_up_enabled=True,
            standard_attributes=cognito.StandardAttributes(
                email=cognito.StandardAttribute(required=True, mutable=True),
            ),
            password_policy=cognito.PasswordPolicy(
                min_length=8,
                require_digits=True,
                require_uppercase=True,
                require_symbols=True,
            ),
            removal_policy=cdk.RemovalPolicy.RETAIN,
        )
        
        client = user_pool.add_client("WebClient",
            o_auth=cognito.OAuthSettings(
                flows=cognito.OAuthFlows(authorization_code_grant=True),
                scopes=[cognito.OAuthScope.EMAIL, cognito.OAuthScope.OPENID],
            ),
        )
        
        from aws_cdk.aws_apigatewayv2_authorizers import HttpJwtAuthorizer
        return HttpJwtAuthorizer(
            "JwtAuthorizer",
            f"https://cognito-idp.{self.region}.amazonaws.com/{user_pool.user_pool_id}",
            jwt_audience=[client.user_pool_client_id],
        )
```

---

## 5.2 CDK Pipelines (Self-Mutating CI/CD)

```python
# my_infra/pipeline_stack.py
import aws_cdk as cdk
from aws_cdk import (
    aws_codecommit as codecommit,
    aws_codebuild as codebuild,
    pipelines,
)
from constructs import Construct
from my_infra.app_stage import AppStage


class PipelineStack(cdk.Stack):
    
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        # Source
        repo = codecommit.Repository.from_repository_name(
            self, "Repo", "my-infra-repo"
        )
        
        # Pipeline definition
        pipeline = pipelines.CodePipeline(
            self, "Pipeline",
            pipeline_name="InfrastructurePipeline",
            self_mutation=True,   # Pipeline updates itself when cdk code changes
            synth=pipelines.ShellStep(
                "Synth",
                input=pipelines.CodePipelineSource.code_commit(repo, "main"),
                install_commands=[
                    "npm install -g aws-cdk",
                    "pip install -r requirements.txt",
                ],
                commands=["cdk synth"],
            ),
            docker_enabled_for_synth=True,
            code_build_defaults=pipelines.CodeBuildOptions(
                build_environment=codebuild.BuildEnvironment(
                    build_image=codebuild.LinuxBuildImage.STANDARD_7_0,
                    compute_type=codebuild.ComputeType.SMALL,
                ),
            ),
        )
        
        # ── Staging Stage ────────────────────────────────
        staging = AppStage(self, "Staging",
            env=cdk.Environment(account="111111111111", region="us-east-1"),
            environment="staging",
        )
        
        staging_stage = pipeline.add_stage(
            staging,
            pre=[
                pipelines.ShellStep(
                    "RunUnitTests",
                    commands=["pip install pytest", "pytest tests/unit/"],
                )
            ],
            post=[
                pipelines.ShellStep(
                    "IntegrationTests",
                    env_from_cfn_outputs={
                        "API_ENDPOINT": staging.api_endpoint,
                    },
                    commands=["pytest tests/integration/ -v"],
                )
            ],
        )
        
        # ── Production Stage (with manual approval) ──────
        prod = AppStage(self, "Production",
            env=cdk.Environment(account="222222222222", region="us-east-1"),
            environment="prod",
        )
        
        pipeline.add_stage(
            prod,
            pre=[
                pipelines.ManualApprovalStep(
                    "ApproveProduction",
                    comment="Review staging test results before deploying to production",
                )
            ],
        )


class AppStage(cdk.Stage):
    """CDK Stage — groups related stacks for pipeline deployment."""
    
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        environment: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        from my_infra.network_stack import NetworkStack
        from my_infra.lambda_stack import LambdaStack
        
        network = NetworkStack(self, "Network", environment=environment)
        lambda_stack = LambdaStack(self, "Lambda",
            environment=environment,
        )
        
        self.api_endpoint = lambda_stack.api.api_endpoint
```

---

## 5.3 Custom CDK Constructs

```python
# my_infra/constructs/secure_bucket.py
"""Reusable secure S3 bucket construct."""
import aws_cdk as cdk
from aws_cdk import (
    aws_s3 as s3,
    aws_kms as kms,
)
from constructs import Construct


class SecureBucket(Construct):
    """S3 bucket with security best practices pre-configured."""
    
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        bucket_name: str | None = None,
        versioned: bool = False,
        lifecycle_rules: list[s3.LifecycleRule] | None = None,
        removal_policy: cdk.RemovalPolicy = cdk.RemovalPolicy.RETAIN,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        key = kms.Key(
            self, "Key",
            description=f"Encryption key for {construct_id}",
            enable_key_rotation=True,
            removal_policy=removal_policy,
        )
        
        self.bucket = s3.Bucket(
            self, "Bucket",
            bucket_name=bucket_name,
            encryption=s3.BucketEncryption.KMS,
            encryption_key=key,
            versioned=versioned,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            enforce_ssl=True,
            object_ownership=s3.ObjectOwnership.BUCKET_OWNER_ENFORCED,
            lifecycle_rules=lifecycle_rules or [
                s3.LifecycleRule(
                    id="delete-incomplete-multipart",
                    abort_incomplete_multipart_upload_after=cdk.Duration.days(7),
                )
            ],
            removal_policy=removal_policy,
        )
    
    def grant_read(self, grantee: iam.IGrantable) -> iam.Grant:
        return self.bucket.grant_read(grantee)
    
    def grant_read_write(self, grantee: iam.IGrantable) -> iam.Grant:
        return self.bucket.grant_read_write(grantee)


# Usage
logs_bucket = SecureBucket(
    self, "LogsBucket",
    versioned=True,
    removal_policy=cdk.RemovalPolicy.RETAIN,
)
logs_bucket.grant_read(my_lambda)
```

---

## 5.4 Interview Q&A

**Q: What is the CDK Asset system and how does it work?**
A: CDK Assets handle local files (Lambda code, Docker images, configuration) that need to be uploaded to AWS. When you use `lambda_.Code.from_asset("./src")`, CDK bundles the directory, computes a hash, and uploads it to the CDK bootstrap S3 bucket during `cdk deploy`. Docker images go to ECR. The hash ensures assets are only re-uploaded when changed. For Lambda, CDK can bundle during synth using Docker (`bundling` option) — this installs Python packages with the correct platform (Linux) even when developing on Mac/Windows. The S3 asset key includes the hash, enabling safe parallel deployments.

**Q: How do CDK Pipelines handle self-mutation?**
A: CDK Pipelines create a CodePipeline that includes a "SelfMutate" stage. When you push infrastructure changes (new stacks, changed stages), the pipeline first updates itself with the new pipeline definition, then redeploys from the beginning with the new structure. This means you can add new stages or modify the pipeline without manually updating it. The synth step runs `cdk synth` to generate CloudFormation templates, which are stored in the artifact bucket and used by subsequent deploy stages. This is the "GitOps" model for infrastructure.

**Q: How do you handle secrets in CDK?**
A: Never put secrets in CDK code or synthesis output (it's stored in CloudFormation). Options: (1) `secretsmanager.Secret` creates a secret with auto-generated password, and you reference it in ECS/Lambda via `ecs.Secret.from_secrets_manager()` or Lambda environment var `secretsmanager:arn:field`; (2) `ssm.StringParameter` for non-sensitive config; (3) For secrets that already exist (created outside CDK), use `secretsmanager.Secret.from_secret_complete_arn()` to import — CDK will create an IAM policy to allow reading but won't manage the secret. Avoid `CfnOutput` for sensitive values.
