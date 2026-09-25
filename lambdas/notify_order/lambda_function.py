import json
import os

import boto3

from observability.observability import emit_metric, log_event


sns = boto3.client("sns")
TOPIC_ARN = os.environ["ORDER_EVENTS_TOPIC_ARN"]


def lambda_handler(event, context):
    order_id = event.get("order_id")
    response = sns.publish(
        TopicArn=TOPIC_ARN,
        Subject="OrderProcessed",
        Message=json.dumps(event, ensure_ascii=False, default=str),
        MessageAttributes={
            "event_type": {"DataType": "String", "StringValue": "OrderProcessed"},
            "risk": {
                "DataType": "String",
                "StringValue": event.get("ai_analysis", {}).get("risk", "UNKNOWN"),
            },
        },
    )

    log_event(
        "INFO",
        "NotifyOrder",
        "order_event_published",
        order_id=order_id,
        status="PUBLISHED",
        extra={"message_id": response["MessageId"]},
    )
    emit_metric("OrderEventsPublished", 1, service="NotifyOrder")
    return {**event, "notification_message_id": response["MessageId"]}
