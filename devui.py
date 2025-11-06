from agent_framework import ChatAgent
from agent_framework.openai import OpenAIChatClient
from workflow_agents.workflow import workflow
from agent_framework.devui import serve


def get_weather(location: str) -> str:
    """Get weather for a location."""
    return f"Weather in {location}: 72°F and sunny"


llm = OpenAIChatClient(
    api_key="ollama",  # Just a placeholder, Ollama doesn't require API key
    base_url="http://localhost:11434/v1",
    model_id="gpt-oss:20b",
)

# Create your agent
agent = ChatAgent(name="WeatherAgent", chat_client=llm, tools=[get_weather])

# Launch debug UI - that's it!
serve(entities=[agent, workflow], auto_open=True)
# → Opens browser to http://localhost:8080
