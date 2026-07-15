
from langchain.messages import AnyMessage
from typing_extensions import TypedDict, Annotated

class AgentCallState(TypedDict):
    """
    Represents the state of an agent call.
    This class is a simple dictionary that holds the state of the agent call.
    """
    agent_name: Annotated[str, "The name of the agent."]
    agent_request: Annotated[AnyMessage, "The request sent to the agent."]
    agent_response: Annotated[AnyMessage, "The response from the agent."]

class UserInfoState(TypedDict):
    """
    Represents the state of a user request.
    This class is a simple dictionary that holds the state of the user request.
    """
    user_id: Annotated[str, "The ID of the user making the request."]
    machine_id: Annotated[str, "The ID of the machine associated with the request."]


class GraphState(TypedDict):
    """
    Represents the state of the orchestrator graph.
    This class is a simple dictionary that holds the state of the graph.
    """
    request: Annotated[AnyMessage, "The user request."]
    user_info: Annotated[UserInfoState, "Information about the user that made the request."]
    agent_call: Annotated[AgentCallState, "The state of the agent call."]
    response: Annotated[AnyMessage, "The response from the orchestrator graph."]

