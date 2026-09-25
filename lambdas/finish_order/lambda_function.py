import time

from observability.observability import log_event, emit_metric


def lambda_handler(event, context):
    """
    Finaliza o processamento do pedido.
    """

    start_time = time.perf_counter()
    order_id = event.get("order_id")

    if not order_id:
        log_event(
            "ERROR",
            "FinishOrder",
            "finish_failed",
            status="ERROR",
            extra={
                "error": "order_id é obrigatório"
            }
        )

        emit_metric(
            "FinishFailures",
            1,
            service="FinishOrder"
        )

        raise ValueError("order_id é obrigatório")

    processed = event.get("processed", False)
    duplicate = event.get("duplicate", False)

    try:
        if duplicate:
            message = f"Pedido {order_id} já havia sido processado."
            status = "DUPLICATE"
        elif processed:
            message = f"Pedido {order_id} finalizado com sucesso."
            status = "SUCCESS"
        else:
            message = f"Pedido {order_id} não foi processado."
            status = "NOT_PROCESSED"

        duration_ms = (time.perf_counter() - start_time) * 1000

        log_event(
            "INFO",
            "FinishOrder",
            "order_finished",
            order_id=order_id,
            status=status,
            extra={
                "duration_ms": round(duration_ms, 2),
                "processed": processed,
                "duplicate": duplicate
            }
        )

        emit_metric(
            "OrdersFinished",
            1,
            service="FinishOrder"
        )

        emit_metric(
            "FinishDuration",
            duration_ms,
            unit="Milliseconds",
            service="FinishOrder"
        )

        return {
            **event,
            "order_id": order_id,
            "status": "SUCCESS",
            "processed": processed,
            "duplicate": duplicate,
            "message": message
        }

    except Exception as error:
        duration_ms = (time.perf_counter() - start_time) * 1000

        log_event(
            "ERROR",
            "FinishOrder",
            "finish_failed",
            order_id=order_id,
            status="ERROR",
            extra={
                "error": str(error),
                "duration_ms": round(duration_ms, 2)
            }
        )

        emit_metric(
            "FinishFailures",
            1,
            service="FinishOrder"
        )

        raise
