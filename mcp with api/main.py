import asyncio
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from dotenv import load_dotenv 
from google import genai
from google.genai.types import GenerateContentConfig, Tool
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from memory import add_to_memory, get_memory, format_memory, clear_memory

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))  

MODEL_NAME = "gemini-2.5-flash"
UI_FILE = os.path.join(BASE_DIR, "main.html")

def get_genai_client() -> genai.Client:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("Set GEMINI_API_KEY before starting the server.")
    return genai.Client(api_key=api_key)


def clean_schema(schema):
    if not isinstance(schema, dict):
        return schema

    cleaned = schema.copy()
    for field in ["additionalProperties", "$schema", "title"]:
        cleaned.pop(field, None)

    if "properties" in cleaned:
        for key, value in cleaned["properties"].items():
            cleaned["properties"][key] = clean_schema(value)

    if "items" in cleaned:
        cleaned["items"] = clean_schema(cleaned["items"])

    return cleaned


def extract_tool_text(result) -> str:
    parts = []
    for content in getattr(result, "content", []):
        if getattr(content, "type", None) == "text":
            parts.append(getattr(content, "text", ""))
    return "\n".join([part for part in parts if part]).strip()


async def ask_model(message: str) -> str:
    client = get_genai_client()

    server_params = StdioServerParameters(
        command=sys.executable,
        args=[os.path.join(BASE_DIR, "mcp_wrapper.py")],
        env=None,
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()

            gemini_tools = []
            for tool in tools.tools:
                gemini_tools.append(
                    Tool(
                        function_declarations=[
                            {
                                "name": tool.name,
                                "description": tool.description,
                                "parameters": clean_schema(tool.inputSchema),
                            }
                        ]
                    )
                )

            chat = client.aio.chats.create(
                model=MODEL_NAME,
                config=GenerateContentConfig(tools=gemini_tools),
            )

            # Include conversation history for context-aware responses
            memory_context = format_memory()
            next_prompt = f"Previous conversation context:\n{memory_context}\n\nUser message: {message}" if memory_context != "No previous conversation." else message
            last_text = ""

            for _ in range(3):
                response = await chat.send_message(next_prompt)
                if response.text:
                    last_text = response.text

                function_calls = []
                if response.candidates and response.candidates[0].content.parts:
                    for part in response.candidates[0].content.parts:
                        if part.function_call:
                            function_calls.append(part.function_call)

                if not function_calls:
                    result = last_text or "I couldn't generate a response."
                    # Add exchange to memory for future context
                    add_to_memory(message, result)
                    return result

                tool_lines = []
                for call in function_calls:
                    try:
                        tool_result = await session.call_tool(
                            call.name, arguments=call.args or {}
                        )
                        tool_text = extract_tool_text(tool_result) or str(tool_result)
                        tool_lines.append(f"{call.name}: {tool_text}")
                    except Exception as error:
                        tool_lines.append(f"{call.name} failed: {error}")

                next_prompt = (
                    "Tool results from MCP server:\n"
                    + "\n".join(tool_lines)
                    + "\nNow answer the user naturally based on these results."
                )

            result = last_text or "I couldn't complete the request."
            # Add exchange to memory for future context
            add_to_memory(message, result)
            return result


class ChatHandler(BaseHTTPRequestHandler):
    def _send_json(self, status_code: int, payload: dict):
        response = json.dumps(payload).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)

    def _send_html(self, html: str):
        encoded = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def do_GET(self):
        if self.path in ["/", "/main.html"]:
            if not os.path.exists(UI_FILE):
                self._send_json(500, {"error": "main.html not found"})
                return
            with open(UI_FILE, "r", encoding="utf-8") as file:
                self._send_html(file.read())
            return

        self._send_json(404, {"error": "Not found"})

    def do_POST(self):
        if self.path == "/chat":
            try:
                content_length = int(self.headers.get("Content-Length", "0"))
                body = self.rfile.read(content_length).decode("utf-8")
                payload = json.loads(body) if body else {}
                message = (payload.get("message") or "").strip()
            except Exception:
                self._send_json(400, {"error": "Invalid request body"})
                return

            if not message:
                self._send_json(400, {"error": "Message is required"})
                return

            try:
                reply = asyncio.run(ask_model(message))
                self._send_json(200, {"reply": reply})
            except Exception as error:
                self._send_json(500, {"error": str(error)})
        
        elif self.path == "/clear-memory":
            try:
                clear_memory()
                self._send_json(200, {"message": "Chat history cleared successfully"})
            except Exception as error:
                self._send_json(500, {"error": str(error)})
        
        elif self.path == "/get-memory":
            try:
                memory = get_memory()
                self._send_json(200, {"memory": memory})
            except Exception as error:
                self._send_json(500, {"error": str(error)})
        
        else:
            self._send_json(404, {"error": "Not found"})


def main():
    host = "127.0.0.1"
    port = int(os.getenv("PORT", "8080"))
    server = ThreadingHTTPServer((host, port), ChatHandler)
    print(f"Chat UI running on http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
