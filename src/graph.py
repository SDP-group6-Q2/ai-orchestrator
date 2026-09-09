"""Graph wiring for the FleetAssistant orchestration flow."""

from pydantic import BaseModel, Field
from typing_extensions import Literal

from langchain_core.language_models import BaseChatModel
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import START, StateGraph, END
from langchain.messages import SystemMessage
from langgraph.graph.message import RemoveMessage
from langgraph.runtime import Runtime


from src.state import GraphState as State
from src.context import AgentContext
from src.security.access import (
    can_access_commercial_data,
    can_access_technical_data,
    get_user_context,
)

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

    "You will also decide whether you have enough conversation history to classify confidently. "
    "The message list you receive may be a partial window of a longer conversation. "
    "Set needs_more_context to true only if the latest user message clearly refers back to "
    "something earlier (e.g. 'that error', 'what I just asked', 'the machine I mentioned') and "
    "you cannot resolve that reference from the messages you were given. Otherwise set it to false, "
    "including whenever the latest message is understandable on its own. "

    "You will receive the user query as input and you must return the intent as output."
    "Return the intent as a json formated string with the following format: "
    "{\"intent\": \"<intent>\", \"needs_more_context\": <true|false>}. "
)

_HISTORY_WINDOW_SIZES = (1, 2, 4, 8)  # escalating message counts; last value is the cap

class Route(BaseModel):
    intent: Literal["technical", "commercial", "out_of_scope"] = Field(None, description="The next step in the routing process") # type: ignore
    needs_more_context: bool = Field(False, description="True if classification needs more conversation history than was given")


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

    def access_denied(state: State):
        state["messages"].append(
            SystemMessage(content="I'm sorry, you don't have permission to access that type of information. Please contact your administrator if you believe this is a mistake.")
        )
        return state

    def check_access(state: State, runtime: Runtime[AgentContext]):
        # Runs right after intent classification, before any specialist agent is invoked --
        # a per-request, single lookup that denies a whole category of request up front,
        # rather than relying only on each tool's own per-call visibility gate. This also
        # covers a blind spot the tool-level gates can't: if the LLM answers a commercial/
        # technical question without calling any gated tool at all (e.g. from hallucinated
        # or conversation-history "knowledge"), there's no tool call to deny -- routing the
        # unauthorized intent away before the specialist agent ever runs closes that gap.
        intent = state["intent"]
        if intent not in ("commercial", "technical"):
            return {}

        user_context = get_user_context(runtime.context.user_id)
        if user_context is None:
            return {"intent": "access_denied"}

        if intent == "commercial" and not can_access_commercial_data(user_context):
            return {"intent": "access_denied"}
        if intent == "technical" and not can_access_technical_data(user_context):
            return {"intent": "access_denied"}

        return {}

    def llm_classify_intent(state: State):
        # Classify using an escalating window of the conversation, not always the full history:
        # most turns are classifiable from just the latest message or two, and re-sending the
        # whole conversation to the router every turn is wasted cost as it grows. Start minimal
        # (1 message) and only widen (2, 4, then 8 -- the cap) when the router itself signals it
        # can't resolve a back-reference ("that error", "what I just asked") from the window it has.
        # comment: it seems ollama bypasses the structured output functionality, so this might fail with ollama. Thats why include formatting the output as json in the system prompt.
        all_messages = state["messages"]

        # FleetAssistant.run always puts the user_id/machine_id SystemMessage first; it must
        # survive windowing or technical_agent loses which machine to query tools against.
        leading_context = all_messages[:1] if all_messages and isinstance(all_messages[0], SystemMessage) else []
        rest = all_messages[len(leading_context):]

        window = all_messages
        for size in _HISTORY_WINDOW_SIZES:
            window = leading_context + rest[-size:]
            decision = router.invoke(
                [
                    SystemMessage(content=_ROUTER_SYSTEM_PROMPT),
                    *window,
                ]
            )
            if not decision.needs_more_context or size == _HISTORY_WINDOW_SIZES[-1]: # type: ignore
                break

        # technical_agent/commercial_agent read state["messages"] directly (they're prebuilt
        # create_agent subgraphs, not aware of any separate "window" field), so the settled
        # window has to become state["messages"] itself for them to only see what the router
        # used. add_messages only appends by id -- RemoveMessage is the supported way to shrink
        # it. This permanently drops the trimmed messages from this graph run's own state/
        # checkpoint, which is fine here: FleetAssistant's checkpointer is per-request and never
        # relied on for persistence -- the backend's Postgres history is the source of truth and
        # is reloaded in full on every call regardless of what this graph run trims.
        window_ids = {m.id for m in window}
        removals = [RemoveMessage(id=m.id) for m in all_messages if m.id not in window_ids]

        return {"intent": decision.intent, "messages": removals} # type: ignore

    router = llm.with_structured_output(Route)

    router_builder = StateGraph(State, context_schema=AgentContext)
    router_builder.add_node("llm_classify_intent", llm_classify_intent)
    router_builder.add_node("check_access", check_access)
    router_builder.add_node("commercial_agent", make_commercial_agent(llm, checkpointer=checkpointer))
    router_builder.add_node("technical_agent", make_technical_agent(llm, checkpointer=checkpointer))
    router_builder.add_node("out_of_scope", out_of_scope)
    router_builder.add_node("access_denied", access_denied)

    router_builder.add_edge(START, "llm_classify_intent")
    router_builder.add_edge("llm_classify_intent", "check_access")
    router_builder.add_conditional_edges(
        "check_access",
        route_decision,
        {
            "commercial": "commercial_agent",
            "technical": "technical_agent",
            "out_of_scope": "out_of_scope",
            "access_denied": "access_denied",
        },
    )
    router_builder.add_edge("commercial_agent", END)
    router_builder.add_edge("technical_agent", END)
    router_builder.add_edge("out_of_scope", END)
    router_builder.add_edge("access_denied", END)
    return router_builder.compile()
