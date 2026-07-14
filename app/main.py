"""FastAPI entrypoint: exposes POST /orchestrate over the LangGraph orchestrator."""

from fastapi import FastAPI

from app.config import settings
from app.graph import orchestrator_graph
from app.schemas import OrchestrateRequest, OrchestrateResponse
from app.state import OrchestratorState

app = FastAPI(title=settings.app_name)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/orchestrate", response_model=OrchestrateResponse)
def orchestrate(request: OrchestrateRequest) -> OrchestrateResponse:
    initial_state: OrchestratorState = {
        "message": request.message,
        "user_id": request.user_id,
        "customer_id": request.customer_id,
        "machine_id": request.machine_id,
        "session_id": request.session_id,
    }

    try:
        result: OrchestratorState = orchestrator_graph.invoke(initial_state)
    except Exception as exc:  # noqa: BLE001 - surface any node failure to the caller
        return OrchestrateResponse(
            session_id=request.session_id,
            intent="",
            selected_agent="",
            answer="",
            citations=[],
            error=str(exc),
        )

    return OrchestrateResponse(
        session_id=request.session_id,
        intent=result.get("intent", ""),
        selected_agent=result.get("selected_agent", ""),
        answer=result.get("answer", ""),
        citations=result.get("citations", []),
        error=result.get("error"),
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=True)
