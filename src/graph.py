"""Graph wiring for the FleetAssistant orchestration flow."""

from pydantic import BaseModel, Field
from typing_extensions import Literal

from langchain_core.language_models import BaseChatModel
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import START, StateGraph, END
from langchain.messages import HumanMessage, SystemMessage


from src.state import GraphState as State

from src.agents import (make_commercial_agent, make_technical_agent)

_ROUTER_SYSTEM_PROMPT = (
    "You are a routing agent for an AROL chatbot. AROL is a capping machine manufacturer."
    "Every user request can be classified into one of three intents: technical, commercial, or out of scope. "

    "**technical: **"
    " - Retrieve technical information from the machine manuals; "
    " - Provide operating, maintenance and troubleshooting instructions; "
    " - Provide usefull information from technical manuals PDF documentation"
    " - Analyse machine health and detect anomalies"
    " - Identify performance degradation"
    " - Correlate alarms with maintenance history "

    " **commercial: **  "
    " - Retrieve quotation and order history; "
    " - Answer questions on the commercial relationship with a customer." 

    " **out_of_scope: **  "
    " - Requests that are not related to technical or commercial topics. "

    "You will receive the user query as input and you must return the intent as output."
    "Return the intent as a json formated string with the following format: {\"intent\": \"<intent>\"}. "
)

class Route(BaseModel):
    intent: Literal["technical", "commercial", "out_of_scope"] = Field(None, description="The next step in the routing process")


def build_graph(llm: BaseChatModel, checkpointer: BaseCheckpointSaver):
    if not checkpointer:
        raise ValueError("A checkpointer must be provided to build the graph.")

    def route_decision(state: State):
        return state["intent"]

    def out_of_scope(state: State):
        state["messages"].append(
            SystemMessage(content="I'm sorry, it seems your request is out of scope for this assistant. Please contact AROL support for further assistance.")
        )
        return state

    def llm_classify_intent(state: State):
        request = state["messages"][-1].content
        # comment: it seems ollama bypasses the structured output functionality, so this might fail with ollama. Thats why include formatting the output as json in the system prompt.
        decision = router.invoke(
            [
                SystemMessage(content=_ROUTER_SYSTEM_PROMPT),
                HumanMessage(content=request),
            ]
        )
        return {"intent": decision.intent} # type: ignore
    
    router = llm.with_structured_output(Route)

    router_builder = StateGraph(State)
    router_builder.add_node("llm_classify_intent", llm_classify_intent)
    router_builder.add_node("commercial_agent", make_commercial_agent(llm, checkpointer=checkpointer))
    router_builder.add_node("technical_agent", make_technical_agent(llm, checkpointer=checkpointer))
    router_builder.add_node("out_of_scope", out_of_scope)

    router_builder.add_edge(START, "llm_classify_intent")
    router_builder.add_conditional_edges(
        "llm_classify_intent",
        route_decision,
        {
            "commercial": "commercial_agent",
            "technical": "technical_agent",
            "out_of_scope": "out_of_scope"
        },
    )
    router_builder.add_edge("commercial_agent", END)
    router_builder.add_edge("technical_agent", END)
    router_builder.add_edge("out_of_scope", END)
    return router_builder.compile()
