import json
import os
import re

import boto3

from observability.observability import emit_metric, log_event


bedrock = boto3.client("bedrock-runtime")
MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "amazon.nova-lite-v1:0")


def _parse_analysis(text):
    """Extract the JSON object even if the model adds Markdown fences."""
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError("A IA não retornou um JSON válido")

    analysis = json.loads(match.group(0))
    risk = str(analysis.get("risk", "")).upper()
    if risk not in {"LOW", "MEDIUM", "HIGH"}:
        raise ValueError("Classificação de risco inválida")

    return {
        "risk": risk,
        "category": str(analysis.get("category", "UNCLASSIFIED"))[:80],
        "reason": str(analysis.get("reason", ""))[:300],
    }


def lambda_handler(event, context):
    order_id = event.get("order_id")
    prompt = (
        "Analise o pedido abaixo para apoiar a triagem operacional. "
        "Não aprove nem rejeite o pedido. Responda somente JSON com as chaves "
        "risk (LOW, MEDIUM ou HIGH), category e reason. "
        f"Pedido: {json.dumps(event, ensure_ascii=False)}"
    )

    try:
        response = bedrock.converse(
            modelId=MODEL_ID,
            messages=[{"role": "user", "content": [{"text": prompt}]}],
            inferenceConfig={"maxTokens": 250, "temperature": 0},
        )
        text = response["output"]["message"]["content"][0]["text"]
        analysis = _parse_analysis(text)

        log_event(
            "INFO",
            "AnalyzeOrderAI",
            "order_analyzed",
            order_id=order_id,
            status=analysis["risk"],
            extra={"model_id": MODEL_ID, "category": analysis["category"]},
        )
        emit_metric("OrdersAnalyzedByAI", 1, service="AnalyzeOrderAI")
        emit_metric(
            f"{analysis['risk'].title()}RiskOrders",
            1,
            service="AnalyzeOrderAI",
        )

        return {**event, "ai_analysis": analysis}
    except Exception as error:
        log_event(
            "ERROR",
            "AnalyzeOrderAI",
            "ai_analysis_failed",
            order_id=order_id,
            status="ERROR",
            extra={"error": str(error), "model_id": MODEL_ID},
        )
        emit_metric("AIAnalysisFailures", 1, service="AnalyzeOrderAI")

        error_code = (
            getattr(error, "response", {})
            .get("Error", {})
            .get("Code")
        )

        if error_code in {"AccessDeniedException", "ThrottlingException"}:
            amount = event.get("amount", 0)

            if amount >= 5000:
                risk = "HIGH"
            elif amount >= 1000:
                risk = "MEDIUM"
            else:
                risk = "LOW"

            fallback_analysis = {
                "risk": risk,
                "category": "FALLBACK_RULE",
                "reason": (
                    "Classificação temporária baseada no valor do pedido "
                    "porque o serviço de IA está indisponível."
                ),
            }

            log_event(
                "WARNING",
                "AnalyzeOrderAI",
                "ai_fallback_applied",
                order_id=order_id,
                status=risk,
                extra={"reason": "Bedrock temporarily unavailable"},
            )

            emit_metric(
                "AIFallbackApplied",
                1,
                service="AnalyzeOrderAI",
            )

            return {
                **event,
                "ai_analysis": fallback_analysis,
                "ai_provider": "fallback",
            }

        raise
