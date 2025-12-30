from typing import TypedDict, Annotated, List, Optional, Dict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

class TestFailure(TypedDict):
    test_name: str
    test_file: str
    error: str
    step: Optional[str]
    snapshot_path: Optional[str]

class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]

    user_story: str
    snapshots: list

    # Test execution
    test_run_attempt: int
    max_test_fix_attempts: int

    has_test_failures: bool
    failures: List[TestFailure]

    # Reporting
    failure_report_path: Optional[str]
    advanced_healing_report_path: Optional[str]