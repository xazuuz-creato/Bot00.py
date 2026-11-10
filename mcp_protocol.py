import json
import asyncio
from typing import Dict, Any, Callable

class ModelContextProtocol:
    def __init__(self):
        self.registered_tools: Dict[str, Callable] = {}

    def register_tool(self, name: str, handler: Callable):
        self.registered_tools[name] = handler
        print(f"[MCP Protocol] Registered tool: {name}")

    async def execute_mcp_request(self, payload_str: str) -> str:
        try:
            payload = json.loads(payload_str)
            tool_name = payload.get("tool")
            args = payload.get("args", {})

            if tool_name in self.registered_tools:
                result = await self.registered_tools[tool_name](**args)
                return json.dumps({"status": "success", "result": result}, ensure_ascii=False)
            else:
                return json.dumps({"status": "error", "message": f"Tool '{tool_name}' not registered"}, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False)
