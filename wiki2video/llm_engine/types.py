from typing import TypedDict, Literal, List, Optional, Dict, Any

Role = Literal["system", "user", "assistant"]

class ChatMessage(TypedDict):
    role: Role
    content: str

class ChatResult(TypedDict):
    content: str
    raw: Dict[str, Any]
