#!/usr/bin/env python3
"""Seed deterministic fictional business records and Cognito demo identities."""

from __future__ import annotations

import argparse
import getpass
import os
import sys
from pathlib import Path

import boto3

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from domain.fixtures import ORDERS  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--user-pool-id", required=True)
    parser.add_argument("--table-name", required=True)
    args = parser.parse_args()
    password = os.getenv("CIRCUITCARE_SEED_PASSWORD") or getpass.getpass("Temporary demo password: ")
    if len(password) < 12:
        raise SystemExit("Demo password must be at least 12 characters")

    table = boto3.resource("dynamodb").Table(args.table_name)
    with table.batch_writer() as batch:
        for order in ORDERS:
            data = order.model_dump(mode="json")
            batch.put_item(Item={"pk": f"ORDER#{order.order_id}", "sk": "DETAIL", "data": data})
            batch.put_item(
                Item={
                    "pk": f"CUSTOMER#{order.customer_id}",
                    "sk": f"ORDER#{order.order_id}",
                    "data": data,
                }
            )

    cognito = boto3.client("cognito-idp")
    users = [
        ("jane@circuitcare.example", "Jane Smith", "CUST-123", None),
        ("bob@circuitcare.example", "Bob Johnson", "CUST-456", None),
        ("support@circuitcare.example", "Maya Support", "STAFF", "support-staff"),
    ]
    for email, name, customer_id, group in users:
        try:
            cognito.admin_create_user(
                UserPoolId=args.user_pool_id,
                Username=email,
                MessageAction="SUPPRESS",
                UserAttributes=[
                    {"Name": "email", "Value": email},
                    {"Name": "email_verified", "Value": "true"},
                    {"Name": "name", "Value": name},
                    {"Name": "custom:customer_id", "Value": customer_id},
                ],
            )
        except cognito.exceptions.UsernameExistsException:
            pass
        cognito.admin_set_user_password(UserPoolId=args.user_pool_id, Username=email, Password=password, Permanent=True)
        if group:
            cognito.admin_add_user_to_group(UserPoolId=args.user_pool_id, Username=email, GroupName=group)
    print("Seeded three fictional identities and deterministic order records.")


if __name__ == "__main__":
    main()
