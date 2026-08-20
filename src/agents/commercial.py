from langchain_core.language_models import BaseChatModel
from langgraph.checkpoint.base import BaseCheckpointSaver
from langchain.agents import create_agent

_logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
	"You are a commercial support agent for AROL capping machines. For now, reply every request saying that you have no capability yet"
)

def make_commercial_agent(llm: BaseChatModel, checkpointer: BaseCheckpointSaver | None = None):
    
	return create_agent(
		model=llm,
		system_prompt=_SYSTEM_PROMPT,
		checkpointer=checkpointer,
	)
