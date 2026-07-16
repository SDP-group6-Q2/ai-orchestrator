"""Class-based FleetAssistant agents."""

from src.agents.iot import IotAgent
from src.agents.manuals import ManualsAgent
from src.agents.orchestrator import FleetOrchestrator
from src.agents.orders import OrdersAgent
from src.agents.service import ServiceAgent
from src.agents.synthesizer import SynthesizerAgent

__all__ = [
    "FleetOrchestrator",
    "IotAgent",
    "ManualsAgent",
    "OrdersAgent",
    "ServiceAgent",
    "SynthesizerAgent",
]