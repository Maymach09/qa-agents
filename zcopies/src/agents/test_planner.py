from pathlib import Path
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from src.graph.state import AgentState
import json

TEST_PLANNER_PROMPT = Path("src/prompts/test_planner.txt").read_text()

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

def test_planner_node(state: AgentState) -> AgentState:
    user_story = state.get("user_story", "")
    # Read all snapshot files from output/snapshots/
    snapshot_dir = Path("output/snapshots")
    snapshot_data = []
    if snapshot_dir.exists():
        for file in snapshot_dir.glob("*.json"):
            try:
                with open(file, "r") as f:
                    data = json.load(f)
                    snapshot_data.append({"file": str(file), "data": data})
            except Exception as e:
                snapshot_data.append({"file": str(file), "error": str(e)})
    messages = [
        SystemMessage(content=TEST_PLANNER_PROMPT),
        HumanMessage(content=f"""
User Story:
{user_story}

Captured Snapshots:
{snapshot_data}
""")
    ]
    response = llm.invoke(messages)
    # Save the test plan as markdown
    Path("output/test_plan.md").write_text(response.content)
    return {**state, "messages": [response]}
