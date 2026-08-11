from typing import TypedDict, Annotated, Literal

import uuid

from pydantic import BaseModel, Field

from langchain_ollama import ChatOllama

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages, MessagesState
from langgraph.checkpoint.memory import InMemorySaver

llm = ChatOllama(model="gpt-oss:20b-cloud", base_url="http://localhost:11434")


class IntentClassifier(BaseModel):
    message_intent: Literal['telemetry', 'manuals', 'orders', 'service'] = Field(..., description="The intent of the user's message, classified into one of the predefined categories.")

class State(TypedDict):
    messages: Annotated[list, add_messages]
    intent: str | None

def classify_intent(state: State):
    structured_llm = llm.with_structured_output(IntentClassifier, method="function_calling")
    response = structured_llm.invoke([
        {'role': 'system', 'content': "Classify the user's message into one of the following intents: telemetry, manuals, orders or service"},
        {'role': 'user', 'content': state['messages'][-1].content}
    ])

    return {"message_intent": response.message_intent}


def prompt_telemetry_system(state: MessagesState):
    messages = [{'role': 'system', 'content': "You are a telemetry system that provides information about the status and health of various devices. No matter what the user says, always respond that you have no available data yet."}] + state['messages']
    response = llm.invoke(messages)
    return {'messages': [{'role': 'assistant', 'content': response.content}]}


def prompt_manuals_system(state: MessagesState):
    messages = [{'role': 'system', 'content': "You are a manuals system that provides information about the user's manual. No matter what the user says, always respond that you have no available data yet."}] + state['messages']
    response = llm.invoke(messages)
    return {'messages': [{'role': 'assistant', 'content': response.content}]}


def prompt_orders_system(state: MessagesState):
    messages = [{'role': 'system', 'content': "You are a orders system that provides information about the user's orders. No matter what the user says, always respond that you have no available data yet."}] + state['messages']
    response = llm.invoke(messages)
    return {'messages': [{'role': 'assistant', 'content': response.content}]}


def prompt_service_system(state: MessagesState):
    messages = [{'role': 'system', 'content': "You are a service system that provides information about the user's service requests. No matter what the user says, always respond that you have no available data yet."}] + state['messages']
    response = llm.invoke(messages)
    return {'messages': [{'role': 'assistant', 'content': response.content}]}


graph_builder = StateGraph(State)

graph_builder.add_node("classifier", classify_intent)
graph_builder.add_node("telemetry", prompt_telemetry_system)
graph_builder.add_node("manuals", prompt_manuals_system)
graph_builder.add_node("orders", prompt_orders_system)
graph_builder.add_node("service", prompt_service_system)

graph_builder.add_edge(START, "classifier")
graph_builder.add_conditional_edges(
    "classifier",
    lambda state: state['message_intent'],
    {
        "telemetry": "telemetry",
        "manuals": "manuals",
        "orders": "orders",
        "service": "service"
    },
)

graph_builder.add_edge("telemetry", END)
graph_builder.add_edge("manuals", END)
graph_builder.add_edge("orders", END)
graph_builder.add_edge("service", END)

checkpointer = InMemorySaver()

graph = graph_builder.compile(checkpointer=checkpointer)

config = {'configurable': {'thread_id': uuid.uuid4()}}

while 1:
    user_input = input("User: ")
    result = graph.invoke({"messages": [{"role": "user", "content": user_input}]}, config=config)

    print("Assistant:", result['messages'][-1].content)