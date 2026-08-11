"""Compatibility node wrapper around the class-based orders agent."""

from src.agents import OrdersAgent
from src.state import GraphState

from langchain_core.language_models import BaseChatModel

def make_orders_agent_node(llm: BaseChatModel):
    orders_agent = OrdersAgent(llm)

    def orders_agent_node(state: GraphState) -> GraphState:
        return orders_agent.run(state)

    return orders_agent_node
