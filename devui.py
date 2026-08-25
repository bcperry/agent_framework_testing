"""DevUI: one records agent per tool transport per demo user.

Pick two agents that differ only by user and ask the same question -- the answers
differ because the token differs, not because the prompt does. Picking two that
differ only by transport shows REST function tools and MCP reaching identical
conclusions from the same FastAPI app.

Starts the records API (:8099) and the generated MCP server (:8098) if they are
not already listening.
"""

import atexit
import os
import socket
import subprocess
import sys
import time

import httpx
from agent_framework import Agent, MCPStreamableHTTPTool
from agent_framework.devui import serve
from agent_framework.openai import OpenAIChatOptions
from dotenv import load_dotenv

from azure_client import create_chat_client
from user_api.auth import mint_user_token
from user_api.data import DEMO_USERS
from user_api.tools import make_records_tools
from workflow_agents.workflow import workflow

load_dotenv()

API_URL = "http://127.0.0.1:8099"
MCP_URL = "http://127.0.0.1:8098/mcp"
LEARN_MCP_URL = os.getenv("MCP_LEARN_URL", "https://learn.microsoft.com/api/mcp")

# Every demo persona, including Nia -- authenticated but not authorized (0 records).
DEMO_AGENT_USERS = list(DEMO_USERS)

# Keep history client-side. With server-side state the agent replays a stored
# `previous_response_id`, and one failed turn poisons that conversation for good.
STATELESS = OpenAIChatOptions(store=False)

RECORDS_INSTRUCTIONS = (
    "You help users inspect records. Use the provided tools. Report exactly what the "
    "tools return - never invent records. If access is denied, say so plainly and "
    "explain why. You cannot act as anyone other than the signed-in user."
)


def _port_open(port: int) -> bool:
    with socket.socket() as sock:
        sock.settimeout(0.3)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def _start_backing_services() -> None:
    commands = {
        8099: [sys.executable, "-m", "uvicorn", "user_api.api:app", "--port", "8099", "--log-level", "warning"],
        8098: [sys.executable, "-m", "user_api.mcp_server"],
    }
    for port, command in commands.items():
        if _port_open(port):
            print(f"port {port}: already serving")
            continue
        process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        atexit.register(process.terminate)
        for _ in range(40):
            if _port_open(port):
                break
            time.sleep(0.5)
        print(f"port {port}: {'started' if _port_open(port) else 'FAILED TO START'}")


def _records_agents(llm) -> list[Agent]:
    """Build a function-tool agent and an MCP agent for each demo user."""
    agents = []
    for upn in DEMO_AGENT_USERS:
        token = mint_user_token(DEMO_USERS[upn])
        given_name = DEMO_USERS[upn]["name"].split()[0]

        agents.append(
            Agent(
                llm,
                RECORDS_INSTRUCTIONS,
                name=f"Records_Functions_{given_name}",
                description=f"REST function tools, acting as {upn}",
                tools=make_records_tools(token, base_url=API_URL),
                default_options=STATELESS,
            )
        )
        agents.append(
            Agent(
                llm,
                RECORDS_INSTRUCTIONS,
                name=f"Records_MCP_{given_name}",
                description=f"MCP tools generated from the FastAPI app, acting as {upn}",
                # The agent connects this on first run, inside its own event loop.
                tools=[
                    MCPStreamableHTTPTool(
                        name="Records MCP",
                        url=MCP_URL,
                        http_client=httpx.AsyncClient(
                            headers={"Authorization": f"Bearer {token}"},
                            follow_redirects=True,
                            timeout=30,
                        ),
                    )
                ],
                default_options=STATELESS,
            )
        )
    return agents


_start_backing_services()

llm = create_chat_client()


# The public Learn MCP server from the notebooks -- no auth, for contrast with the
# user-scoped records agents below it.
learn_agent = Agent(
    llm,
    "You answer questions about Microsoft and Azure using the Microsoft Learn MCP tools. "
    "Ground every answer in what the tools return, and cite the doc URLs they give you.",
    name="MSLearnAgent",
    description="Microsoft Learn MCP (public, unauthenticated)",
    tools=[MCPStreamableHTTPTool(name="Microsoft Learn MCP", url=LEARN_MCP_URL)],
    default_options=STATELESS,
)

serve(
    entities=[learn_agent, *_records_agents(llm), workflow],
    auto_open=True,
    auth_enabled=False,
)
