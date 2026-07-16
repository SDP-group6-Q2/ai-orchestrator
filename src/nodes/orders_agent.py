"""Compatibility node wrapper around the class-based orders agent."""

from src.agents import OrdersAgent
from src.state import GraphState


def make_orders_agent_node(agent: OrdersAgent | None = None):
    orders_agent = agent or OrdersAgent()

    def orders_agent_node(state: GraphState) -> GraphState:
        return orders_agent.run(state)

    return orders_agent_node


orders_agent_node = make_orders_agent_node()
