import os
import time

import boto3
from botocore.exceptions import ClientError

from observability.observability import log_event, emit_metric


dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(
    os.environ.get("IDEMPOTENCY_TABLE", "orders-idempotency")
)


def lambda_handler(event, context):
    """
    Processa um pedido garantindo idempotência.
    """

    start_time = time.perf_counter()
    order_id = event.get("order_id")

    if not order_id:
        log_event(
            "ERROR",
            "ProcessOrder",
            "processing_failed",
            status="ERROR",
            extra={
                "error": "order_id é obrigatório"
            }
        )

        emit_metric(
            "ProcessingFailures",
            1,
            service="ProcessOrder"
        )

        raise ValueError("order_id é obrigatório")

    log_event(
        "INFO",
        "ProcessOrder",
        "order_processing_started",
        order_id=order_id,
        status="STARTED"
    )

    try:
        try:
            table.put_item(
                Item={"order_id": order_id, "status": "COMPLETED"},
                ConditionExpression="attribute_not_exists(order_id)",
            )
        except ClientError as error:
            if error.response.get("Error", {}).get("Code") != "ConditionalCheckFailedException":
                raise
            duration_ms = (time.perf_counter() - start_time) * 1000

            log_event(
                "INFO",
                "ProcessOrder",
                "duplicate_order",
                order_id=order_id,
                status="DUPLICATE",
                extra={
                    "duration_ms": round(duration_ms, 2)
                }
            )

            emit_metric(
                "DuplicateOrders",
                1,
                service="ProcessOrder"
            )

            emit_metric(
                "ProcessingDuration",
                duration_ms,
                unit="Milliseconds",
                service="ProcessOrder"
            )

            return {
                **event,
                "processed": False,
                "duplicate": True,
                "order_id": order_id,
                "message": "Pedido já processado"
            }

        log_event(
            "INFO",
            "ProcessOrder",
            "order_processing",
            order_id=order_id,
            status="PROCESSING"
        )

        # Simula o processamento do pedido.
        result = {
            **event,
            "processed": True,
            "duplicate": False,
            "order_id": order_id,
            "message": "Pedido processado com sucesso"
        }

        duration_ms = (time.perf_counter() - start_time) * 1000

        log_event(
            "INFO",
            "ProcessOrder",
            "order_processed",
            order_id=order_id,
            status="COMPLETED",
            extra={
                "duration_ms": round(duration_ms, 2)
            }
        )

        emit_metric(
            "OrdersProcessed",
            1,
            service="ProcessOrder"
        )

        emit_metric(
            "ProcessingDuration",
            duration_ms,
            unit="Milliseconds",
            service="ProcessOrder"
        )

        return result

    except ClientError as error:
        duration_ms = (time.perf_counter() - start_time) * 1000

        log_event(
            "ERROR",
            "ProcessOrder",
            "dynamodb_error",
            order_id=order_id,
            status="ERROR",
            extra={
                "error": str(error),
                "duration_ms": round(duration_ms, 2)
            }
        )

        emit_metric(
            "ProcessingFailures",
            1,
            service="ProcessOrder"
        )

        emit_metric(
            "ProcessingDuration",
            duration_ms,
            unit="Milliseconds",
            service="ProcessOrder"
        )

        raise
