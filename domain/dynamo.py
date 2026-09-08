"""DynamoDB single-table adapter for the CircuitCare domain."""

from __future__ import annotations

import os
from typing import Any

import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

from .models import AuditEvent, Order, ReturnRequest, SupportCase
from .repository import ConflictError


class DynamoRepository:
    def __init__(self, table_name: str, resource: Any | None = None) -> None:
        self.table = (
            resource
            or boto3.resource("dynamodb", region_name=os.getenv("AWS_REGION", "us-east-1"))
        ).Table(table_name)

    def _query(self, pk: str, prefix: str) -> list[dict[str, Any]]:
        return self.table.query(KeyConditionExpression=Key("pk").eq(pk) & Key("sk").begins_with(prefix))["Items"]

    def list_orders(self, customer_id: str) -> list[Order]:
        return [Order.model_validate(v["data"]) for v in self._query(f"CUSTOMER#{customer_id}", "ORDER#")]

    def get_order(self, order_id: str) -> Order | None:
        response = self.table.get_item(Key={"pk": f"ORDER#{order_id}", "sk": "DETAIL"})
        return Order.model_validate(response["Item"]["data"]) if "Item" in response else None

    def list_returns(self, customer_id: str) -> list[ReturnRequest]:
        return [ReturnRequest.model_validate(v["data"]) for v in self._query(f"CUSTOMER#{customer_id}", "RETURN#")]

    def get_return_by_key(self, idempotency_key: str) -> ReturnRequest | None:
        response = self.table.get_item(Key={"pk": f"IDEMPOTENCY#{idempotency_key}", "sk": "RETURN"})
        return ReturnRequest.model_validate(response["Item"]["data"]) if "Item" in response else None

    def save_return(self, value: ReturnRequest, idempotency_key: str) -> None:
        data = value.model_dump(mode="json")
        try:
            self.table.meta.client.transact_write_items(
                TransactItems=[
                    {
                        "Put": {
                            "TableName": self.table.name,
                            "Item": {
                                "pk": f"IDEMPOTENCY#{idempotency_key}",
                                "sk": "RETURN",
                                "data": data,
                            },
                            "ConditionExpression": "attribute_not_exists(pk)",
                        }
                    },
                    {
                        "Put": {
                            "TableName": self.table.name,
                            "Item": {
                                "pk": f"CUSTOMER#{value.customer_id}",
                                "sk": f"RETURN#{value.return_id}",
                                "data": data,
                            },
                        }
                    },
                    {
                        "Put": {
                            "TableName": self.table.name,
                            "Item": {
                                "pk": f"RETURN_LOCK#{value.customer_id}#{value.order_id}",
                                "sk": "CONFIRMED",
                                "return_id": value.return_id,
                            },
                            "ConditionExpression": "attribute_not_exists(pk)",
                        }
                    },
                ]
            )
        except ClientError as exc:
            reasons = exc.response.get("CancellationReasons", [])
            if exc.response.get("Error", {}).get("Code") == "TransactionCanceledException" and any(
                reason.get("Code") == "ConditionalCheckFailed" for reason in reasons
            ):
                raise ConflictError("A return already exists for this order") from exc
            raise

    def list_cases(self, customer_id: str | None = None) -> list[SupportCase]:
        if customer_id:
            items = self._query(f"CUSTOMER#{customer_id}", "CASE#")
        else:
            items = self.table.scan(
                FilterExpression="begins_with(sk, :prefix)", ExpressionAttributeValues={":prefix": "CASE#"}
            )["Items"]
        return [SupportCase.model_validate(v["data"]) for v in items]

    def get_case(self, case_id: str) -> SupportCase | None:
        response = self.table.get_item(Key={"pk": f"CASE#{case_id}", "sk": "DETAIL"})
        return SupportCase.model_validate(response["Item"]["data"]) if "Item" in response else None

    def save_case(self, value: SupportCase) -> None:
        data = value.model_dump(mode="json")
        with self.table.batch_writer() as batch:
            batch.put_item(Item={"pk": f"CASE#{value.case_id}", "sk": "DETAIL", "data": data})
            batch.put_item(Item={"pk": f"CUSTOMER#{value.customer_id}", "sk": f"CASE#{value.case_id}", "data": data})

    def append_audit(self, value: AuditEvent) -> None:
        self.table.put_item(
            Item={
                "pk": f"CUSTOMER#{value.customer_id}",
                "sk": f"AUDIT#{value.occurred_at.isoformat()}#{value.event_id}",
                "data": value.model_dump(mode="json"),
            }
        )
