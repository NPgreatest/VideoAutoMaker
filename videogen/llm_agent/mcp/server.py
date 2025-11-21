"""MCP Server 框架占位。

未来会在此注册工具，并暴露给各 Agent 使用。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass
class MCPServerConfig:
    host: str = "127.0.0.1"
    port: int = 7337


class MCPServer:
    def __init__(self, config: MCPServerConfig | None = None) -> None:
        self.config = config or MCPServerConfig()
        self.tools: list[str] = []

    def register_tool(self, tool_name: str) -> None:
        if tool_name not in self.tools:
            self.tools.append(tool_name)

    def run(self) -> None:  # pragma: no cover - 待实现
        raise NotImplementedError("MCPServer.run 尚未实现")

    def list_tools(self) -> Iterable[str]:
        return tuple(self.tools)


__all__ = ["MCPServer", "MCPServerConfig"]
