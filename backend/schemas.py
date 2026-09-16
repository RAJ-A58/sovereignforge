from pydantic import BaseModel
from typing import Any, Optional


class AgentEvent(BaseModel):
    """
    A single event streamed from the agent to the frontend via WebSocket.
    type values:
      "agent_start"   - agent initialized
      "classified"    - task classification result
      "thinking"      - iteration heartbeat
      "thought"       - LLM reasoning step
      "tool_call"     - about to call a tool
      "tool_result"   - tool returned a result
      "finish"        - final answer ready
      "error"         - something went wrong
      "max_iterations"- hit iteration cap
    """

    type: str
    data: dict[str, Any]


class TaskRequest(BaseModel):
    user_input: str
    task_type: Optional[str] = None   # if None, auto-classify
    file_path: Optional[str] = None


class TaskResponse(BaseModel):
    task_id: str
    status: str


class UploadResponse(BaseModel):
    file_id: str
    file_path: str
    filename: str
