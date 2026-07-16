"""FastAPI entrypoint: exposes POST /orchestrate over the FleetAssistant graph."""

from fastapi import FastAPI

from api.config import settings
from api.schemas import OrchestrateRequest, OrchestrateResponse
from FleetAssistant import FleetAssistant

app = FastAPI(title=settings.app_name)

_assistant = FleetAssistant(llama_model=settings.ollama_model, llama_base_url=settings.ollama_base_url)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/orchestrate", response_model=OrchestrateResponse)
def orchestrate(request: OrchestrateRequest) -> OrchestrateResponse:
    try:
        result = _assistant.run(request.message, user_id=request.user_id, machine_id=request.machine_id)
    except Exception as exc:  # noqa: BLE001 - surface any node failure to the caller
        return OrchestrateResponse(session_id=request.session_id, response="", error=str(exc))

    return OrchestrateResponse(
        session_id=request.session_id,
        response=result.get("response", ""),
        error=result.get("error"),
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=True)
