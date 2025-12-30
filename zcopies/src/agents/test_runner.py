import subprocess
from pathlib import Path
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from src.graph.state import AgentState, TestFailure

TEST_RUNNER_PROMPT = Path("src/prompts/test_runner.txt").read_text()


def test_runner_node(state: AgentState) -> AgentState:
    test_dir = Path("tests")
    report_dir = Path("output/failure_report")
    report_dir.mkdir(parents=True, exist_ok=True)
    report_md_path = report_dir / "failure_analysis.md"

    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0
    )

    failures: list[TestFailure] = []

    # ----------------------------
    # Run Playwright tests
    # ----------------------------
    for script in test_dir.glob("*.spec.ts"):
        cmd = [
            "npx", "playwright", "test", str(script),
            "--project=chromium",
            "--headed",
            "--timeout=30000",
            "--reporter=list"
        ]

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )

            if proc.returncode != 0:
                failures.append({
                    "script_name": script.name,
                    "script_path": str(script),
                    "script_content": script.read_text(),
                    "logs": (proc.stderr or proc.stdout).strip()[:4000]
                })

        except subprocess.TimeoutExpired:
            failures.append({
                "script_name": script.name,
                "script_path": str(script),
                "script_content": script.read_text(),
                "logs": "Test execution timed out after 60 seconds"
            })

    # ----------------------------
    # No failures → return early
    # ----------------------------
    if not failures:
        return {
            **state,
            "has_test_failures": False,
            "failures": [],
            "failure_report_path": None,
            "llm_analysis": None
        }

    # ----------------------------
    # Build LLM input
    # ----------------------------
    payload = []
    for f in failures:
        payload.append(
            f"""
SCRIPT NAME:
{f['script_name']}

SCRIPT CONTENT:
{f['script_content']}

FAILURE LOGS:
{f['logs']}
"""
        )

    messages = [
        SystemMessage(content=TEST_RUNNER_PROMPT),
        HumanMessage(content="\n\n---\n\n".join(payload))
    ]

    llm_response = llm.invoke(messages)

    # Normalize LLM output to string
    raw_content = llm_response.content
    if isinstance(raw_content, list):
        markdown_report = "\n".join(
            item if isinstance(item, str) else str(item)
            for item in raw_content
        )
    else:
        markdown_report = raw_content

    report_md_path.write_text(markdown_report, encoding="utf-8")

    return {
        **state,
        "has_test_failures": True,
        "failures": failures,
        "failure_report_path": str(report_md_path),
        "llm_analysis": markdown_report
    }