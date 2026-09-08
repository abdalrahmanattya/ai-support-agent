from types import SimpleNamespace

from domain.dynamo import DynamoRepository
from domain.fixtures import ORDERS
from domain.models import ReturnRequest, ReturnStatus


class TransactionClient:
    def __init__(self) -> None:
        self.request = None

    def transact_write_items(self, **kwargs) -> None:
        self.request = kwargs


class Table:
    name = "business-table"

    def __init__(self, client: TransactionClient) -> None:
        self.meta = SimpleNamespace(client=client)


class Resource:
    def __init__(self, table: Table) -> None:
        self.table = table

    def Table(self, _name: str) -> Table:  # noqa: N802
        return self.table


def test_transaction_uses_resource_client_native_values() -> None:
    client = TransactionClient()
    repository = DynamoRepository("business-table", resource=Resource(Table(client)))
    proposal = ReturnRequest(
        return_id="RET-TEST",
        order_id=ORDERS[1].order_id,
        customer_id=ORDERS[1].customer_id,
        amount=ORDERS[1].total,
        reason="No longer needed",
        status=ReturnStatus.CONFIRMED,
        created_at="2026-09-08T12:00:00Z",
    )

    repository.save_return(proposal, "request-key")

    assert client.request is not None
    item = client.request["TransactItems"][0]["Put"]["Item"]
    assert item["pk"] == "IDEMPOTENCY#request-key"
    assert item["data"]["order_id"] == ORDERS[1].order_id
