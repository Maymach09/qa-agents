from pathlib import Path
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from src.graph.state import AgentState

TEST_CASE_DESIGNER_PROMPT = Path("src/prompts/test_case_designer.txt").read_text()

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

def test_case_designer_node(state: AgentState) -> AgentState:
    user_story = state.get("user_story", "")
    # Read the test plan markdown
    test_plan_path = Path("output/test_plan.md")
    test_plan = test_plan_path.read_text() if test_plan_path.exists() else ""
    # Optionally, read snapshots
    snapshot_dir = Path("output/snapshots")
    snapshot_data = []
    if snapshot_dir.exists():
        for file in snapshot_dir.glob("*.json"):
            snapshot_data.append(file.read_text())
    messages = [
        SystemMessage(content=TEST_CASE_DESIGNER_PROMPT),
        HumanMessage(content=f"""
User Story:
{user_story}

Test Plan:
{test_plan}

Snapshots:
{snapshot_data}
""")
    ]
    response = llm.invoke(messages)
    # Save the test cases as JSON array
    Path("output/test_cases.json").write_text(response.content)
    return {**state, "messages": [response]}
