"""
LangGraph workflow definition for the embedded code generation agent.

Graph structure:
    manager -> [pin_mapper] -> prepare_workspace -> coder -> assemble_artifacts -> persist -> END

Diagram support is kept behind a switch so it can be re-enabled without
changing node implementations.
"""

from langgraph.graph import END, StateGraph

from src.nodes import (
    assemble_artifacts_node,
    coder_node,
    diagram_node,
    manager_node,
    pin_mapper_node,
    persist_node,
    prepare_workspace_node,
)
from src.state import AgentState


def build_graph(
    use_skills: bool = True,
    enable_diagram: bool = False,
    enable_pin_mapper: bool = True,
):
    """Build and compile the agent workflow graph."""
    workflow = StateGraph(AgentState)

    # Add nodes
    if use_skills:
        workflow.add_node("manager", manager_node)
    if enable_pin_mapper:
        workflow.add_node("pin_mapper", pin_mapper_node)
    workflow.add_node("prepare_workspace", prepare_workspace_node)
    workflow.add_node("coder", coder_node)
    workflow.add_node("diagram", diagram_node)
    workflow.add_node("assemble_artifacts", assemble_artifacts_node)
    workflow.add_node("persist", persist_node)

    # Entry point
    if use_skills:
        workflow.set_entry_point("manager")
    elif enable_pin_mapper:
        workflow.set_entry_point("pin_mapper")
    else:
        workflow.set_entry_point("prepare_workspace")

    # Main path: manager -> [pin_mapper] -> prepare_workspace -> coder
    if use_skills:
        if enable_pin_mapper:
            workflow.add_edge("manager", "pin_mapper")
        else:
            workflow.add_edge("manager", "prepare_workspace")
    if enable_pin_mapper:
        workflow.add_edge("pin_mapper", "prepare_workspace")
    workflow.add_edge("prepare_workspace", "coder")
    workflow.add_edge("coder", "assemble_artifacts")

    if enable_diagram:
        # Optional branch: prepare_workspace -> diagram, then fan-in at assembly.
        workflow.add_edge("prepare_workspace", "diagram")
        workflow.add_edge("diagram", "assemble_artifacts")

    workflow.add_edge("assemble_artifacts", "persist")

    # End
    workflow.add_edge("persist", END)

    return workflow.compile()