import json
import os

import boto3

from observability.observability import log_event, emit_metric


stepfunctions = boto3.client("stepfunctions")

STATE_MACHINE_ARN = os.environ["STATE_MACHINE_ARN"]


def lambda_handler(event, context):
    body = event.get("body", event)

    if isinstance(body, str):
        body = json.loads(body)

    if not isinstance(body, dict):
        return {"statusCode": 400, "body": json.dumps({"error": "corpo inválido"})}

    order_id = body.get("order_id")

    log_event(
        "INFO",
        "StartOrder",
        "order_started",
        order_id=order_id,
        status="STARTED"
    )

    emit_metric(
        "OrdersStarted",
        1,
        service="StartOrder"
    )

    try:
        response = stepfunctions.start_execution(
            stateMachineArn=STATE_MACHINE_ARN,
            input=json.dumps(body)
        )

        log_event(
            "INFO",
            "StartOrder",
            "step_function_started",
            order_id=order_id,
            status="ACCEPTED",
            extra={
                "execution_arn": response["executionArn"]
            }
        )

        return {
            "statusCode": 202,
            "headers": {
                "Content-Type": "application/json"
            },
            "body": json.dumps({
                "message": "Pedido enviado para processamento",
                "executionArn": response["executionArn"],
                "startDate": response["startDate"].isoformat()
            })
        }

    except Exception as error:
        log_event(
            "ERROR",
            "StartOrder",
            "step_function_start_failed",
            order_id=order_id,
            status="ERROR",
            extra={
                "error": str(error)
            }
        )

        emit_metric(
            "StartFailures",
            1,
            service="StartOrder"
        )

        raise
