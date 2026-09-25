from observability.observability import log_event, emit_metric


def lambda_handler(event, context):
    """
    Valida os dados básicos de um pedido antes do processamento.
    """

    order_id = event.get("order_id")
    customer = event.get("customer")
    amount = event.get("amount")

    try:
        if not order_id:
            raise ValueError("order_id é obrigatório")

        if not customer:
            raise ValueError("customer é obrigatório")

        if amount is None:
            raise ValueError("amount é obrigatório")

        if not isinstance(amount, (int, float)) or amount <= 0:
            raise ValueError("amount deve ser um número maior que zero")

        log_event(
            "INFO",
            "ValidateOrder",
            "order_validated",
            order_id=order_id,
            status="VALID"
        )

        emit_metric(
            "OrdersValidated",
            1,
            service="ValidateOrder"
        )

        return {
            "valid": True,
            "order_id": order_id,
            "customer": customer,
            "amount": amount
        }

    except Exception as error:
        log_event(
            "ERROR",
            "ValidateOrder",
            "validation_failed",
            order_id=order_id,
            status="INVALID",
            extra={
                "error": str(error)
            }
        )

        emit_metric(
            "ValidationFailures",
            1,
            service="ValidateOrder"
        )

        raise
