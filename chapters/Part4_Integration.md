# Part 4: Integration — FastAPI + AWS Services

---

## 7.1 FastAPI with DynamoDB

```python
# app/services/dynamo_service.py
import boto3
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError
import os
from datetime import datetime
from typing import Any


class DynamoService:
    """Single-table DynamoDB service using access patterns."""
    
    def __init__(self):
        self.dynamodb = boto3.resource("dynamodb", region_name=os.environ["AWS_REGION"])
        self.table = self.dynamodb.Table(os.environ["TABLE_NAME"])
    
    async def get_item(self, pk: str, sk: str) -> dict | None:
        try:
            response = self.table.get_item(
                Key={"PK": pk, "SK": sk},
                ConsistentRead=False,  # Eventually consistent (cheaper)
            )
            return response.get("Item")
        except ClientError as e:
            raise Exception(f"DynamoDB error: {e.response['Error']['Message']}")
    
    async def put_item(self, item: dict) -> None:
        item["createdAt"] = datetime.utcnow().isoformat()
        item["updatedAt"] = item["createdAt"]
        self.table.put_item(Item=item)
    
    async def update_item(
        self,
        pk: str,
        sk: str,
        updates: dict[str, Any],
        condition: str | None = None,
    ) -> dict:
        """Build and execute an UpdateExpression from a dict."""
        update_expr = "SET "
        expr_attr_names = {}
        expr_attr_values = {":updatedAt": datetime.utcnow().isoformat()}
        
        set_parts = ["#updatedAt = :updatedAt"]
        expr_attr_names["#updatedAt"] = "updatedAt"
        
        for key, value in updates.items():
            placeholder = f"#{key}"
            value_placeholder = f":{key}"
            set_parts.append(f"{placeholder} = {value_placeholder}")
            expr_attr_names[placeholder] = key
            expr_attr_values[value_placeholder] = value
        
        update_expr += ", ".join(set_parts)
        
        kwargs = dict(
            Key={"PK": pk, "SK": sk},
            UpdateExpression=update_expr,
            ExpressionAttributeNames=expr_attr_names,
            ExpressionAttributeValues=expr_attr_values,
            ReturnValues="ALL_NEW",
        )
        if condition:
            kwargs["ConditionExpression"] = condition
        
        response = self.table.update_item(**kwargs)
        return response["Attributes"]
    
    async def query_by_pk(
        self,
        pk: str,
        sk_prefix: str | None = None,
        limit: int = 100,
        last_evaluated_key: dict | None = None,
    ) -> tuple[list[dict], dict | None]:
        kwargs = dict(
            KeyConditionExpression=Key("PK").eq(pk),
            Limit=limit,
            ScanIndexForward=False,   # Descending order (newest first)
        )
        if sk_prefix:
            kwargs["KeyConditionExpression"] &= Key("SK").begins_with(sk_prefix)
        if last_evaluated_key:
            kwargs["ExclusiveStartKey"] = last_evaluated_key
        
        response = self.table.query(**kwargs)
        return response["Items"], response.get("LastEvaluatedKey")
    
    async def query_gsi(
        self,
        index_name: str,
        pk_value: str,
        sk_value: str | None = None,
    ) -> list[dict]:
        key_condition = Key("GSI1PK").eq(pk_value)
        if sk_value:
            key_condition &= Key("GSI1SK").begins_with(sk_value)
        
        response = self.table.query(
            IndexName=index_name,
            KeyConditionExpression=key_condition,
        )
        return response["Items"]
    
    async def transact_write(self, operations: list[dict]) -> None:
        """Execute multiple writes atomically."""
        self.dynamodb.meta.client.transact_write(
            TransactItems=operations
        )
```

```python
# Usage in FastAPI router
dynamo = DynamoService()

@router.post("/orders", status_code=201)
async def create_order(order_in: OrderCreate, current_user=Depends(get_current_user)):
    order_id = str(uuid.uuid4())
    
    # Transactional write: create order + update user order count
    await dynamo.transact_write([
        {
            "Put": {
                "TableName": os.environ["TABLE_NAME"],
                "Item": {
                    "PK": f"ORDER#{order_id}",
                    "SK": "METADATA",
                    "GSI1PK": f"USER#{current_user.id}",
                    "GSI1SK": f"ORDER#{datetime.utcnow().isoformat()}",
                    "status": "PENDING",
                    "userId": current_user.id,
                    **order_in.model_dump(),
                },
                "ConditionExpression": "attribute_not_exists(PK)",
            }
        },
        {
            "Update": {
                "TableName": os.environ["TABLE_NAME"],
                "Key": {"PK": f"USER#{current_user.id}", "SK": "STATS"},
                "UpdateExpression": "ADD orderCount :inc",
                "ExpressionAttributeValues": {":inc": 1},
            }
        },
    ])
    
    return {"orderId": order_id, "status": "PENDING"}
```

---

## 7.2 FastAPI with S3

```python
# app/services/s3_service.py
import boto3
from botocore.config import Config
import os

class S3Service:
    def __init__(self):
        self.client = boto3.client(
            "s3",
            region_name=os.environ["AWS_REGION"],
            config=Config(signature_version="s3v4"),
        )
        self.bucket = os.environ["S3_BUCKET"]
    
    def generate_presigned_upload_url(
        self,
        key: str,
        content_type: str,
        expiry: int = 3600,
        max_size: int = 10 * 1024 * 1024,
    ) -> dict:
        """Generate a presigned POST URL for direct browser upload."""
        conditions = [
            ["content-length-range", 1, max_size],
            ["eq", "$Content-Type", content_type],
        ]
        
        response = self.client.generate_presigned_post(
            Bucket=self.bucket,
            Key=key,
            Fields={"Content-Type": content_type},
            Conditions=conditions,
            ExpiresIn=expiry,
        )
        return response
    
    def generate_presigned_download_url(self, key: str, expiry: int = 3600) -> str:
        return self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": key},
            ExpiresIn=expiry,
        )
    
    def copy_object(self, source_key: str, dest_key: str) -> None:
        self.client.copy_object(
            Bucket=self.bucket,
            CopySource={"Bucket": self.bucket, "Key": source_key},
            Key=dest_key,
            ServerSideEncryption="aws:kms",
        )
    
    def delete_object(self, key: str) -> None:
        self.client.delete_object(Bucket=self.bucket, Key=key)


# FastAPI endpoint using presigned URL pattern (avoids large uploads through API)
s3 = S3Service()

@router.post("/uploads/presigned-url")
async def get_presigned_upload_url(
    request: PresignedUrlRequest,
    current_user=Depends(get_current_user),
):
    """Return presigned POST URL for direct browser-to-S3 upload."""
    ext = request.filename.rsplit(".", 1)[-1].lower()
    key = f"uploads/{current_user.id}/{uuid.uuid4()}.{ext}"
    
    presigned = s3.generate_presigned_upload_url(
        key=key,
        content_type=request.content_type,
    )
    return {"upload_url": presigned["url"], "fields": presigned["fields"], "key": key}
```

---

## 7.3 FastAPI with SQS/SNS (Async Messaging)

```python
# app/services/messaging.py
import boto3
import json
import os
from dataclasses import dataclass
from typing import Any


class MessageBus:
    """Pub/sub via SNS fan-out to SQS queues."""
    
    def __init__(self):
        self.sns = boto3.client("sns", region_name=os.environ["AWS_REGION"])
        self.sqs = boto3.client("sqs", region_name=os.environ["AWS_REGION"])
        self.topic_arn = os.environ["SNS_TOPIC_ARN"]
    
    async def publish_event(
        self,
        event_type: str,
        payload: dict[str, Any],
        attributes: dict[str, str] | None = None,
    ) -> str:
        """Publish event to SNS topic for fan-out delivery."""
        message_attrs = {
            "event_type": {
                "DataType": "String",
                "StringValue": event_type,
            }
        }
        
        if attributes:
            for key, value in attributes.items():
                message_attrs[key] = {"DataType": "String", "StringValue": value}
        
        response = self.sns.publish(
            TopicArn=self.topic_arn,
            Message=json.dumps(payload),
            Subject=event_type,
            MessageAttributes=message_attrs,
        )
        return response["MessageId"]
    
    async def send_to_queue(self, queue_url: str, message: dict) -> str:
        """Send message directly to SQS queue."""
        response = self.sqs.send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps(message),
            MessageGroupId=message.get("user_id", "default"),  # For FIFO queues
        )
        return response["MessageId"]


# Usage in FastAPI
message_bus = MessageBus()

@router.post("/orders/{order_id}/confirm")
async def confirm_order(order_id: str, current_user=Depends(get_current_user)):
    # Update order status
    await update_order_status(order_id, "CONFIRMED")
    
    # Publish event for downstream services (email, inventory, analytics)
    await message_bus.publish_event(
        event_type="OrderConfirmed",
        payload={
            "order_id": order_id,
            "user_id": current_user.id,
            "confirmed_at": datetime.utcnow().isoformat(),
        },
    )
    
    return {"status": "confirmed"}
```

---

## 7.4 FastAPI with Cognito

```python
# app/auth/cognito.py
import boto3
import requests
from functools import lru_cache
from jose import jwk, jwt
from jose.utils import base64url_decode
import os

COGNITO_REGION = os.environ["AWS_REGION"]
USER_POOL_ID = os.environ["COGNITO_USER_POOL_ID"]
CLIENT_ID = os.environ["COGNITO_CLIENT_ID"]

JWKS_URL = f"https://cognito-idp.{COGNITO_REGION}.amazonaws.com/{USER_POOL_ID}/.well-known/jwks.json"


@lru_cache(maxsize=None)
def get_jwks() -> dict:
    """Cache JWKS keys — they change rarely."""
    return requests.get(JWKS_URL).json()


def verify_cognito_token(token: str) -> dict:
    """Verify Cognito JWT and return claims."""
    headers = jwt.get_unverified_headers(token)
    kid = headers["kid"]
    
    # Find matching key
    jwks = get_jwks()
    public_key = None
    for key in jwks["keys"]:
        if key["kid"] == kid:
            public_key = jwk.construct(key)
            break
    
    if not public_key:
        raise ValueError("Public key not found")
    
    # Verify signature and claims
    claims = jwt.decode(
        token,
        public_key,
        algorithms=["RS256"],
        audience=CLIENT_ID,
        issuer=f"https://cognito-idp.{COGNITO_REGION}.amazonaws.com/{USER_POOL_ID}",
    )
    return claims


# FastAPI dependency
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

bearer_scheme = HTTPBearer()

async def get_cognito_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> dict:
    try:
        claims = verify_cognito_token(credentials.credentials)
        return claims
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")
```

---

## 7.5 FastAPI with ElastiCache Redis

```python
# app/cache/redis_cache.py
import redis.asyncio as aioredis
import json
import os
from typing import Any

redis_client: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    global redis_client
    if redis_client is None:
        redis_client = await aioredis.from_url(
            os.environ["REDIS_URL"],
            encoding="utf-8",
            decode_responses=True,
            max_connections=20,
        )
    return redis_client


class CacheService:
    
    async def get(self, key: str) -> Any | None:
        r = await get_redis()
        value = await r.get(key)
        if value:
            return json.loads(value)
        return None
    
    async def set(self, key: str, value: Any, ttl: int = 300) -> None:
        r = await get_redis()
        await r.setex(key, ttl, json.dumps(value, default=str))
    
    async def delete(self, key: str) -> None:
        r = await get_redis()
        await r.delete(key)
    
    async def delete_pattern(self, pattern: str) -> int:
        r = await get_redis()
        keys = await r.keys(pattern)
        if keys:
            return await r.delete(*keys)
        return 0
    
    async def increment(self, key: str, amount: int = 1) -> int:
        r = await get_redis()
        return await r.incrby(key, amount)
    
    async def set_if_not_exists(self, key: str, value: Any, ttl: int) -> bool:
        """SET NX — for distributed locks and idempotency."""
        r = await get_redis()
        return await r.set(key, json.dumps(value), ex=ttl, nx=True)


# Idempotency with Redis
cache = CacheService()

@router.post("/orders")
async def create_order(
    order_in: OrderCreate,
    idempotency_key: str = Header(...),
    current_user=Depends(get_current_user),
):
    # Check if request was already processed
    cache_key = f"idempotency:{idempotency_key}"
    cached = await cache.get(cache_key)
    if cached:
        return cached  # Return same response as original request
    
    # Process order
    result = await process_order(order_in, current_user)
    
    # Cache result for 24 hours
    await cache.set(cache_key, result, ttl=86400)
    return result
```

---

## 7.6 Interview Q&A

**Q: When should you use DynamoDB vs RDS in a serverless architecture?**
A: **DynamoDB**: Use when you have well-defined, predictable access patterns; need massive scale (millions of writes/sec); want serverless-compatible (no connection pooling issues); have simple relational needs. **RDS**: Use when you need complex queries (JOINs, aggregations, ad-hoc analytics); data modeling is uncertain (schemaless iteration); existing SQL tooling is required; strong ACID transactions across many tables. For Lambda: DynamoDB wins because RDS requires VPC + RDS Proxy or database proxy to manage connection pools (Lambda can create thousands of concurrent connections, exhausting RDS limits). DynamoDB uses HTTP API — no persistent connections.

**Q: How do you implement idempotency in API endpoints?**
A: Use an `Idempotency-Key` header. On first request: process and cache the response (in Redis or DynamoDB) with a TTL. On duplicate request with same key: return cached response without reprocessing. This prevents issues with retries (double-charging, duplicate orders). AWS Lambda Powertools has a built-in idempotency decorator: `@idempotent(config=IdempotencyConfig(...))` backed by DynamoDB. For payment processors, idempotency is essential. Key should be client-generated (UUID) and associated with the specific operation + user, not shared across different operations.

**Q: What is the SNS fan-out pattern and when do you use it?**
A: SNS fan-out = one message published to SNS → delivered to multiple SQS queues simultaneously. Use when one event triggers multiple independent downstream processes: `OrderPlaced` → (1) SQS for inventory service, (2) SQS for email service, (3) SQS for analytics service. Benefits: decoupled services (add new subscribers without changing publisher), parallel processing, each service processes at its own pace with backpressure via SQS. Alternative: EventBridge supports content-based routing (filter rules), schema registry, and cross-account delivery — prefer EventBridge for new architectures.
