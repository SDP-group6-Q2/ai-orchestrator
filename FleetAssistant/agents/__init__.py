"""Class-based FleetAssistant agents."""

from FleetAssistant.agents.iot import IotAgent
from FleetAssistant.agents.manuals import ManualsAgent
from FleetAssistant.agents.orchestrator import FleetOrchestrator
from FleetAssistant.agents.orders import OrdersAgent
from FleetAssistant.agents.service import ServiceAgent
from FleetAssistant.agents.synthesizer import SynthesizerAgent

__all__ = [
    "FleetOrchestrator",
    "IotAgent",
    "ManualsAgent",
    "OrdersAgent",
    "ServiceAgent",
    "SynthesizerAgent",
]