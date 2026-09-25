import importlib.util
import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")
os.environ.setdefault("AWS_EC2_METADATA_DISABLED", "true")


def load_lambda(relative_path, module_name):
    path = ROOT / relative_path
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


validate_order = load_lambda(
    "lambdas/validate_order/lambda_function.py",
    "validate_order",
)

finish_order = load_lambda(
    "lambdas/finish_order/lambda_function.py",
    "finish_order",
)


def test_ai_analysis_parses_model_json():
    with patch("boto3.client") as client:
        client.return_value.converse.return_value = {
            "output": {"message": {"content": [{"text": '```json\n{"risk":"HIGH","category":"review","reason":"high amount"}\n```'}]}}
        }
        analyze_order = load_lambda(
            "lambdas/analyze_order_ai/lambda_function.py",
            "analyze_order_ai",
        )
        result = analyze_order.lambda_handler(
            {"order_id": "ORDER-AI-001", "customer": "Rafaella", "amount": 9000},
            None,
        )

    assert result["ai_analysis"]["risk"] == "HIGH"
    assert result["ai_analysis"]["category"] == "review"


def test_ai_analysis_rejects_invalid_risk():
    with patch("boto3.client"):
        analyze_order = load_lambda(
            "lambdas/analyze_order_ai/lambda_function.py",
            "analyze_order_ai_invalid",
        )

    with pytest.raises(ValueError):
        analyze_order._parse_analysis('{"risk":"UNKNOWN","category":"x","reason":"x"}')


def test_validate_order_success():
    event = {
        "order_id": "ORDER-TEST-001",
        "customer": "Rafaella",
        "amount": 100,
    }

    result = validate_order.lambda_handler(event, None)

    assert result == {
        "valid": True,
        "order_id": "ORDER-TEST-001",
        "customer": "Rafaella",
        "amount": 100,
    }


@pytest.mark.parametrize(
    "event",
    [
        {"customer": "Rafaella", "amount": 100},
        {"order_id": "ORDER-001", "amount": 100},
        {"order_id": "ORDER-001", "customer": "Rafaella"},
        {
            "order_id": "ORDER-001",
            "customer": "Rafaella",
            "amount": 0,
        },
        {
            "order_id": "ORDER-001",
            "customer": "Rafaella",
            "amount": -10,
        },
    ],
)
def test_validate_order_invalid(event):
    with pytest.raises(ValueError):
        validate_order.lambda_handler(event, None)


def test_finish_order_processed():
    event = {
        "order_id": "ORDER-TEST-001",
        "processed": True,
        "duplicate": False,
    }

    result = finish_order.lambda_handler(event, None)

    assert result["status"] == "SUCCESS"
    assert result["processed"] is True
    assert result["duplicate"] is False


def test_finish_order_duplicate():
    event = {
        "order_id": "ORDER-TEST-001",
        "processed": False,
        "duplicate": True,
    }

    result = finish_order.lambda_handler(event, None)

    assert result["status"] == "SUCCESS"
    assert result["processed"] is False
    assert result["duplicate"] is True


def test_workflow_is_valid_json():
    workflow_path = ROOT / "workflow/order-processing-workflow.json"

    with workflow_path.open() as file:
        workflow = json.load(file)

    assert workflow["StartAt"] == "ValidateOrder"
    assert "ValidateOrder" in workflow["States"]
    assert "ProcessOrder" in workflow["States"]
    assert "FinishOrder" in workflow["States"]
    assert "SendToDLQ" in workflow["States"]

    assert workflow["States"]["ValidateOrder"]["Next"] == "AnalyzeOrderAI"
    assert workflow["States"]["AnalyzeOrderAI"]["Next"] == "ProcessOrder"
    assert workflow["States"]["ProcessOrder"]["Next"] == "FinishOrder"
    assert workflow["States"]["FinishOrder"]["Next"] == "NotifyOrder"
    assert workflow["States"]["NotifyOrder"]["Next"] == "OrderCompleted"

    assert workflow["States"]["ValidateOrder"]["Retry"]
    assert workflow["States"]["ProcessOrder"]["Retry"]
    assert workflow["States"]["FinishOrder"]["Retry"]
    assert workflow["States"]["AnalyzeOrderAI"]["Retry"]
    assert workflow["States"]["NotifyOrder"]["Retry"]

    assert workflow["States"]["SendToDLQ"]["Type"] == "Task"
    assert workflow["States"]["SendToDLQ"]["Resource"] == "arn:aws:states:::sqs:sendMessage"
