from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from src.graph.state import AgentState
from src.agents.snapshot_collector import snapshot_node, tools
from src.agents.test_planner import test_planner_node
from src.agents.test_case_designer import test_case_designer_node
from src.agents.test_script_generator import test_script_generator_node
from src.agents.test_runner import test_runner_node
from src.agents.advanced_test_healer import advanced_test_healer_node


def should_continue(state: AgentState):
    last_message = state["messages"][-1]
    # Only check tool_calls if the attribute exists (e.g., AIMessage, not SystemMessage)
    if hasattr(last_message, "tool_calls") and getattr(last_message, "tool_calls", None):
        return "tool_call"
    return "test_plan"


def route_after_test_runner(state: AgentState):
    if state.get("has_test_failures", False):
        return "heal_advanced"
    return "end"


def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("snapshot_agent", snapshot_node)
    graph.add_node("tools", ToolNode(tools))
    graph.add_node("test_planner_agent", test_planner_node)
    graph.add_node("test_case_designer_agent", test_case_designer_node)
    graph.add_node("test_script_generator_agent", test_script_generator_node)
    graph.add_node("test_runner_agent", test_runner_node)
    graph.add_node("advanced_test_healer_agent", advanced_test_healer_node)

    graph.set_entry_point("snapshot_agent")

    graph.add_conditional_edges(
        "snapshot_agent",
        should_continue,
        {
            "tool_call": "tools",
            "test_plan": "test_planner_agent",
        },
    )

    graph.add_edge("tools", "snapshot_agent")
    graph.add_edge("test_planner_agent", "test_case_designer_agent")
    graph.add_edge("test_case_designer_agent", "test_script_generator_agent")
    graph.add_edge("test_script_generator_agent", "test_runner_agent")

    # Route to advanced healer if tests fail
    graph.add_conditional_edges(
        "test_runner_agent",
        route_after_test_runner,
        {
            "heal_advanced": "advanced_test_healer_agent",
            "end": END,
        },
    )

    # Advanced healer terminates workflow after completion
    graph.add_edge("advanced_test_healer_agent", END)

    return graph.compile()