from pathlib import Path
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from src.graph.state import AgentState
import json

PROMPT = Path("src/prompts/test_script_generator.txt").read_text()

# -------- MODEL --------
llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0
)

def load_snapshots():
    """Load all snapshot files and return as a dictionary."""
    snapshot_dir = Path("output/snapshots")
    snapshots = {}
    for file in snapshot_dir.glob("*.json"):
        data = json.loads(file.read_text(encoding="utf-8"))
        page_name = data.get("page_name", file.stem)
        snapshots[page_name] = data
    return snapshots

def test_script_generator_node(state: AgentState) -> AgentState:
    """
    Generate Playwright-compatible TypeScript test scripts using test cases and snapshot elements.
    """
    # Load test cases
    test_cases_path = Path("output/test_cases.json")
    test_cases = json.loads(test_cases_path.read_text(encoding="utf-8"))
    
    # Load all snapshots
    snapshots = load_snapshots()
    
    # Create context with test cases and snapshots
    context = f"""
Test Cases:
{json.dumps(test_cases, indent=2)}

Available Snapshots:
{json.dumps(snapshots, indent=2)}
"""
    
    system_message = SystemMessage(content=PROMPT)
    human_message = HumanMessage(content=context)
    
    # Generate all test scripts at once
    response = llm.invoke([system_message, human_message])
    
    # Split the generated TypeScript code into individual test scripts
    import re
    scripts = re.split(r'(?=test\()', response.content)
    
    # Filter out empty scripts and the header
    header = 'import { test, expect } from "@playwright/test";\ntest.use({ storageState: "auth_state.json" });\n\n'
    
    # Extract test scripts (skip first element if it's just imports)
    test_scripts = []
    for script in scripts:
        script = script.strip()
        if script and script.startswith('test('):
            test_scripts.append(header + script)
    
    # If no test scripts were found, try to extract from the full response
    if not test_scripts:
        # Fallback: split by test case IDs
        for case in test_cases:
            case_id = case.get("id", "")
            pattern = rf'test\(["\'].*?{case_id}.*?[\'"](.*?)(?=test\(|$)'
            match = re.search(pattern, response.content, re.DOTALL)
            if match:
                test_scripts.append(header + f'test({match.group(0)}')
    
    # Save each test script to a separate file
    for idx, case in enumerate(test_cases):
        case_id = case.get("id", f"case_{idx+1}")
        script = test_scripts[idx] if idx < len(test_scripts) else header + f'// TODO: Generate test for {case_id}'
        output_path = Path(f"tests/{case_id}.spec.ts")
        output_path.write_text(script, encoding="utf-8")

    return {
        "messages": [response],
        "user_story": state.get("user_story", ""),
        "snapshots": state.get("snapshots", [])
    }
