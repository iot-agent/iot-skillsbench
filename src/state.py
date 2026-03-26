from typing import TypedDict, Optional, List, Annotated
from langchain_core.messages import BaseMessage
import operator
from src.config import FrameworkType


class WorkspaceInfo(TypedDict, total=False):
    """Structured workspace information prepared before generation."""

    output_root: str
    target: str
    project_name: str


class Artifact(TypedDict, total=False):
    """Generated artifact payload (not persisted yet)."""

    path: str
    content: str
    role: str


class AgentState(TypedDict, total=False):
    """State schema for the embedded code generation agent."""

    # Required inputs
    requirements: str
    framework: FrameworkType

    # Run configuration
    task_name: str
    prompt_file: str  # Name of the prompt file used (e.g., "prompt_v2.txt")
    run_dir: str  # Path to current run directory (e.g., tasks/dht11/runs/2026-02-12_14-30-25)

    # Project metadata (set by manager)
    project_name: str
    active_platform: Optional[str]
    active_skills: List[str]
    active_skill_content: Optional[str]
    pin_mapping_notes: Optional[str]
    prepared_output_dir: Optional[str]
    prepared_code_path: Optional[str]
    workspace: WorkspaceInfo

    # Artifacts from generation/assembly
    code_content: Optional[str]
    diagram_content: Optional[str]
    artifacts: List[Artifact]

    # Message history for multi-turn interactions
    messages: Annotated[List[BaseMessage], operator.add]

    # Debug logging - accumulates LLM call records
    debug_logs: Annotated[List[dict], operator.add]

    # Token usage - accumulates per-node usage records
    token_usage: Annotated[List[dict], operator.add]

    # Final output
    manifest_path: Optional[str]
    persisted_paths: List[str]
    status_msg: str