import re
from pathlib import Path
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from src.graph.state import AgentState

TEST_HEALER_PROMPT = Path("src/prompts/test_healer.txt").read_text()


def test_healer_node(state: AgentState) -> AgentState:
    """
    Applies LLM-suggested fixes from the failure report exactly once
    and generates a markdown report describing applied changes.
    """

    failure_report_path = state.get("failure_report_path")
    if not failure_report_path:
        print("No failure report found. Skipping healing.")
        return state

    failure_report = Path(failure_report_path).read_text()

    # Load current test scripts
    test_scripts: dict[str, str] = {}
    for script in Path("tests").glob("*.spec.ts"):
        test_scripts[script.name] = script.read_text()

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

    messages = [
        SystemMessage(content=TEST_HEALER_PROMPT),
        HumanMessage(content=f"""
FAILURE REPORT:
{failure_report}

CURRENT TEST SCRIPTS:
{test_scripts}
""")
    ]

    response = llm.invoke(messages)

    raw_content = response.content
    if isinstance(raw_content, list):
        llm_output = "\n".join(
            item if isinstance(item, str) else str(item)
            for item in raw_content
        )
    else:
        llm_output = raw_content

    # ---------------------------------
    # Parse UPDATED SCRIPTS section
    # ---------------------------------
    updated_scripts_pattern = re.compile(
        r"### (.+?\.spec\.ts)\s*```typescript\s*(.*?)```",
        re.DOTALL
    )

    updates = updated_scripts_pattern.findall(llm_output)

    applied_changes = []

    for script_name, updated_content in updates:
        script_path = Path("tests") / script_name
        if not script_path.exists():
            print(f"Skipping unknown script: {script_name}")
            continue

        script_path.write_text(updated_content.strip(), encoding="utf-8")
        applied_changes.append(script_name)
        print(f"✓ Updated {script_name}")

    # ---------------------------------
    # Write change summary report
    # ---------------------------------
    report_dir = Path("output/healer_report")
    report_dir.mkdir(parents=True, exist_ok=True)
    change_report_path = report_dir / "applied_changes.md"

    change_report_path.write_text(llm_output, encoding="utf-8")

    return {
        **state,
        "messages": state["messages"] + [response]
    }