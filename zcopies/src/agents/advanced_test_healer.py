"""
Advanced Test Healer Agent
Implements a systematic workflow for debugging and healing Playwright tests:
1. Run all tests
2. Debug failed tests
3. Investigate errors using Playwright tools
4. Analyze root cause
5. Edit test code
6. Verify fixes
7. Iterate until all tests pass
"""

import json
from pathlib import Path
from datetime import datetime
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage
from langchain_openai import ChatOpenAI
from src.graph.state import AgentState
from src.tools.playwright_tools import (
    playwright_run_all_tests,
    playwright_analyze_failure,
    update_test_script,
    browser_snapshot,
    browser_navigate,
    browser_wait
)

ADVANCED_HEALER_PROMPT = Path("src/prompts/test_healer_advanced.txt").read_text()


async def advanced_test_healer_node(state: AgentState) -> AgentState:
    """
    Advanced healing workflow using iterative debugging and tool-based investigation.
    Follows the strict workflow defined in the healer prompt.
    """
    
    print("\n" + "="*80)
    print("ADVANCED TEST HEALER - Starting Systematic Healing Process")
    print("="*80)
    
    llm = ChatOpenAI(model="gpt-4o", temperature=0)
    
    # Bind all available Playwright tools to the LLM
    healing_tools = [
        playwright_run_all_tests,
        playwright_analyze_failure,
        update_test_script,
        browser_snapshot,
        browser_navigate,
        browser_wait
    ]
    
    llm_with_tools = llm.bind_tools(healing_tools)
    
    # Initialize conversation with system prompt
    messages = [
        SystemMessage(content=ADVANCED_HEALER_PROMPT),
        HumanMessage(content="""
Begin the advanced healing workflow:
1. Run all tests to identify failures
2. Debug each failing test systematically
3. Investigate, diagnose, and fix issues
4. Verify fixes by re-running tests
5. Iterate until all tests pass

Start now by running all tests.
""")
    ]
    
    max_iterations = 5  # Prevent infinite loops
    iteration = 0
    all_tests_passing = False
    
    while iteration < max_iterations and not all_tests_passing:
        iteration += 1
        print(f"\n{'─'*80}")
        print(f"ITERATION {iteration}/{max_iterations}")
        print(f"{'─'*80}")
        
        # Invoke LLM with tools
        response = llm_with_tools.invoke(messages)
        messages.append(response)
        
        # Check if LLM wants to use tools
        if hasattr(response, "tool_calls") and response.tool_calls:
            print(f"\n🔧 Agent requested {len(response.tool_calls)} tool call(s)")
            
            # Execute each tool call
            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]
                
                print(f"  → Executing: {tool_name}({tool_args})")
                
                # Execute the tool
                try:
                    tool_func = next(t for t in healing_tools if t.name == tool_name)
                    
                    # Check if tool is async and use ainvoke instead
                    if hasattr(tool_func, 'coroutine'):
                        import asyncio
                        tool_result = await tool_func.ainvoke(tool_args)
                    else:
                        tool_result = tool_func.invoke(tool_args)
                    
                    # Format result for LLM
                    if isinstance(tool_result, dict):
                        result_str = json.dumps(tool_result, indent=2)
                    else:
                        result_str = str(tool_result)
                    
                    print(f"  ✓ Result: {result_str[:200]}...")
                    
                    # Add tool result to messages
                    messages.append(
                        ToolMessage(
                            content=result_str,
                            tool_call_id=tool_call["id"]
                        )
                    )
                    
                    # Check if all tests are passing
                    if tool_name == "playwright_run_all_tests" and isinstance(tool_result, dict):
                        # Parse test results
                        suites = tool_result.get("suites", [])
                        total_failures = sum(
                            len([t for t in suite.get("specs", []) 
                                 if any(r.get("status") == "failed" for r in t.get("tests", [{}])[0].get("results", []))])
                            for suite in suites
                        )
                        
                        if total_failures == 0:
                            all_tests_passing = True
                            print("\n✅ ALL TESTS PASSING - Healing Complete!")
                            break
                    
                except Exception as e:
                    error_msg = f"Tool execution error: {str(e)}"
                    print(f"  ✗ Error: {error_msg}")
                    messages.append(
                        ToolMessage(
                            content=error_msg,
                            tool_call_id=tool_call["id"]
                        )
                    )
        else:
            # LLM provided a text response without tool calls
            print(f"\n💭 Agent response: {response.content[:300]}...")
            
            # Ask for next action
            messages.append(
                HumanMessage(content="Continue with the next step in the healing workflow.")
            )
    
    # Generate final healing report
    healing_report_dir = Path("output/healing_summary")
    healing_report_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = healing_report_dir / f"advanced_healing_summary_{timestamp}.md"
    
    # Generate summary from conversation
    summary_response = llm.invoke([
        SystemMessage(content="You are a technical report writer. Summarize the test healing process."),
        HumanMessage(content=f"""
Based on the following healing conversation, create a comprehensive summary report:

Iterations completed: {iteration}
All tests passing: {all_tests_passing}

Conversation history:
{chr(10).join([f"- {msg.content if hasattr(msg, 'content') else str(msg)}" for msg in messages[-10:]])}

Create a report with:
1. Executive Summary
2. Issues Identified
3. Fixes Applied
4. Tests Modified
5. Final Status
6. Recommendations
""")
    ])
    
    report_path.write_text(summary_response.content, encoding="utf-8")
    print(f"\n📄 Healing report saved: {report_path}")
    
    return {
        **state,
        "messages": state["messages"] + messages,
        "healing_complete": all_tests_passing,
        "healing_iterations": iteration,
        "healing_report_path": str(report_path)
    }