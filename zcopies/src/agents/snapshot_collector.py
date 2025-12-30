from dotenv import load_dotenv
from langchain_core.messages import SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from datetime import datetime
from src.tools.playwright_tools import browser_snapshot, browser_navigate, browser_wait
from src.graph.state import AgentState
import logging
from pathlib import Path


load_dotenv()

PROMPT = Path("src/prompts/snapshot_collector.txt").read_text()
OUTPUT_DIR = Path("output/raw_snapshots")

# Register the tools
tools = [
    browser_navigate,
    browser_wait,
    browser_snapshot
]

# -------- MODEL --------
llm_with_tools = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0
).bind_tools(tools)


def snapshot_node(state: AgentState) -> AgentState:
    system_message = SystemMessage(content=PROMPT)
    response = llm_with_tools.invoke([system_message] + state["messages"])
    return {"messages": [response]}
