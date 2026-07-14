"""Orders & Docs Agent placeholder — will fetch order/quote/contract status via MCP (ERP/CRM)."""

from app.state import OrchestratorState


def run(state: OrchestratorState) -> OrchestratorState:
    return {
        "answer": "[Orders Agent placeholder] This will answer using quote, order and contract data from the ERP/CRM.",
        "citations": [
            {"source": "orders_agent:stub", "snippet": "Placeholder citation from ERP/CRM order records."}
        ],
    }
