"""MCP 客户端占位实现。

后续可在此封装与 MCP server 交互的通用逻辑。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass
class MCPResponse:
    """MCP 工具统一响应结构占位。"""

    success: bool
    data: Any
    message: str | None = None


class MCPClient:
    """未来用于通过 MCP Server 调用工具的客户端。

    当前版本尚未实现实际通信，仅保留接口以利于架构演进。
    """

    def __init__(self, server_url: str | None = None) -> None:
        self.server_url = server_url or "http://localhost:7337"

    def invoke_tool(self, tool_name: str, payload: Mapping[str, Any]) -> MCPResponse:  # pragma: no cover - 未实现
        raise NotImplementedError("MCPClient.invoke_tool 尚未实现")


__all__ = ["MCPClient", "MCPResponse"]
