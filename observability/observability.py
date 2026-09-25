import json
import time
from datetime import datetime, timezone


NAMESPACE = "FinalProject/OrderProcessing"


def log_event(
    level,
    service,
    event,
    order_id=None,
    status=None,
    extra=None,
):
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "level": level,
        "service": service,
        "event": event,
    }

    if order_id is not None:
        payload["order_id"] = order_id

    if status is not None:
        payload["status"] = status

    if extra:
        payload["details"] = extra

    print(json.dumps(payload, default=str))


def emit_metric(
    metric_name,
    value=1,
    unit="Count",
    service="OrderProcessing",
):
    payload = {
        "_aws": {
            "Timestamp": int(time.time() * 1000),
            "CloudWatchMetrics": [
                {
                    "Namespace": NAMESPACE,
                    "Dimensions": [["Service"]],
                    "Metrics": [
                        {
                            "Name": metric_name,
                            "Unit": unit,
                        }
                    ],
                }
            ],
        },
        "Service": service,
        metric_name: value,
    }

    print(json.dumps(payload, default=str))
