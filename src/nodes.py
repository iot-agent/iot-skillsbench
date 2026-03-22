"""
Node implementations for the embedded code generation workflow.

Nodes:
- manager_node: Plans the project and selects relevant skills
- prepare_workspace_node: Prepares output directories before code generation
- coder_node: Generates the main code file
- diagram_node: Placeholder for future diagram generation
- assemble_artifacts_node: Converts generated outputs into artifact list
- persist_node: Persists artifacts and run metadata to disk
"""

import hashlib
import json
import os
import re
import time
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any, List

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from src.loader import SkillRegistry
from src.state import AgentState, Artifact, WorkspaceInfo

registry = SkillRegistry()
MODEL_NAME = "anthropic/claude-4.5-sonnet"
MODEL_TEMPERATURE = 0.0
MODEL_API_BASE = "https://openrouter.ai/api/v1"
MODEL_API_KEY_ENV = "OPENAI_API_KEY"
SKILLS_DIR = "skills"


def configure_registry(skills_dir: str) -> None:
    """
    Configure the skills directory used by the registry.

    Reinitializes the registry with the new skills directory.
    """
    global registry, SKILLS_DIR  # pylint: disable=global-statement
    SKILLS_DIR = skills_dir
    registry = SkillRegistry(skills_dir=skills_dir)


def configure_model(
    model_name: str,
    temperature: float = 0.0,
    api_base: str = "https://openrouter.ai/api/v1",
    api_key_env: str = "OPENAI_API_KEY",
) -> None:
    """
    Configure model settings used by all LLM nodes.

    Clearing get_model cache ensures runtime config takes effect immediately.
    """
    global MODEL_NAME, MODEL_TEMPERATURE, MODEL_API_BASE, MODEL_API_KEY_ENV  # pylint: disable=global-statement
    MODEL_NAME = model_name
    MODEL_TEMPERATURE = temperature
    MODEL_API_BASE = api_base
    MODEL_API_KEY_ENV = api_key_env
    get_model.cache_clear()


@lru_cache(maxsize=1)
def get_model() -> ChatOpenAI:
    """Return a cached LLM instance configured from runtime settings."""
    api_key = os.environ.get(MODEL_API_KEY_ENV) or os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError(
            f"Missing API key. Set {MODEL_API_KEY_ENV} (or OPENROUTER_API_KEY)."
        )

    return ChatOpenAI(
        model=MODEL_NAME,
        openai_api_key=api_key,
        openai_api_base=MODEL_API_BASE,
        temperature=MODEL_TEMPERATURE,
        max_tokens=8192,
    )


def create_debug_log(
    node: str,
    input_messages: Any,
    output: Any,
    duration_ms: float,
    metadata: dict = None,
) -> dict:
    """Create a debug log entry for an LLM call."""
    return {
        "node": node,
        "timestamp": datetime.now().isoformat(),
        "duration_ms": round(duration_ms, 2),
        "input": input_messages,
        "output": output,
        "metadata": metadata or {},
    }


def extract_clean_code(raw_text: str) -> str:
    """
    Extract C/C++ code from an LLM response.

    Handles multiple formats:
    - ```c or ```cpp code blocks
    - Generic ``` code blocks
    - Raw code with conversational prefixes stripped
    """
    # Try ```c, ```cpp, or ```cc blocks
    match = re.search(r"```(?:c|cpp|cc)\n(.*?)```", raw_text, re.DOTALL)
    if match:
        return match.group(1).strip()

    # Try generic ``` blocks
    match = re.search(r"```\n(.*?)```", raw_text, re.DOTALL)
    if match:
        return match.group(1).strip()

    # Fallback: detect code by common starting patterns
    lines = raw_text.split("\n")
    code_lines = []
    started = False

    for line in lines:
        if not started:
            if line.strip().startswith(("#include", "//", "/*", "void", "int")):
                started = True
                code_lines.append(line)
        else:
            code_lines.append(line)

    if code_lines:
        return "\n".join(code_lines).strip()

    return raw_text.strip()


# --- Schema ---


class ProjectPlan(BaseModel):
    """Schema for the manager's project planning output."""

    project_name: str = Field(
        ..., description="Project name in snake_case (e.g., 'esp32_sensor_node')"
    )
    selected_skills: List[str] = Field(
        ..., description="List of relevant skill names (e.g., ['esp-idf', 'arduino'])"
    )


# --- Nodes ---


def manager_node(state: AgentState) -> dict:
    """
    Plan the project by analyzing requirements and selecting skills.

    Reads: requirements
    Writes: project_name, active_skills, active_skill_content, debug_logs
    """
    llm = get_model()
    available_skills = registry.scan_skills()

    parser = PydanticOutputParser(pydantic_object=ProjectPlan)

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are a Project Planner. Analyze the request and output a JSON plan.\n"
                "1. Use snake_case for the project_name.\n"
                "2. Select relevant skills ONLY from the AVAILABLE SKILLS list.\n\n"
                "AVAILABLE SKILLS:\n{skills}\n\n"
                "{format_instructions}",
            ),
            ("user", "{request}"),
        ]
    )

    # Split chain to capture raw AIMessage for token usage
    prompt_chain = prompt | llm

    input_data = {
        "skills": available_skills,
        "format_instructions": parser.get_format_instructions(),
        "request": state["requirements"],
    }

    start_time = time.time()

    try:
        response = prompt_chain.invoke(input_data)
        duration_ms = (time.time() - start_time) * 1000

        usage = {}
        if hasattr(response, "usage_metadata") and response.usage_metadata:
            usage = dict(response.usage_metadata)

        plan: ProjectPlan = parser.invoke(response)

        # Only use skills that were actually loaded from config (filter out any LLM hallucination)
        selected_skills = [
            s for s in plan.selected_skills
            if s in registry.descriptions
        ]

        skill_content = registry.get_combined_skill_content(selected_skills)

        debug_log = create_debug_log(
            node="manager",
            input_messages={
                "system": prompt.messages[0].prompt.template,
                "user": state["requirements"],
                "available_skills": available_skills,
            },
            output=plan.model_dump(),
            duration_ms=duration_ms,
            metadata={
                "parser": "PydanticOutputParser",
                "schema": "ProjectPlan",
                "token_usage": usage,
            },
        )

        token_record = {"node": "manager", "usage": usage}

        return {
            "project_name": plan.project_name,
            "active_skills": selected_skills,
            "active_skill_content": skill_content,
            "debug_logs": [debug_log],
            "token_usage": [token_record],
        }

    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000

        debug_log = create_debug_log(
            node="manager",
            input_messages={"request": state["requirements"]},
            output={"error": str(e)},
            duration_ms=duration_ms,
            metadata={"status": "fallback"},
        )

        # Fallback: no hardcoded skills, only use what was loaded from config
        fallback_skills = [
            s for s in registry.descriptions
        ]  # Use all available skills if any
        fallback_content = registry.get_combined_skill_content(
            fallback_skills
        ) if fallback_skills else "Use standard embedded development best practices."
        return {
            "project_name": "esp32_fallback",
            "active_skills": fallback_skills,
            "active_skill_content": fallback_content,
            "debug_logs": [debug_log],
        }


def prepare_workspace_node(state: AgentState) -> dict:
    """
    Prepare output folders and target code file path before code generation.

    Reads: run_dir, project_name, active_skills
    Writes: prepared_output_dir, prepared_code_path, active_platform
    """
    project_name = state.get("project_name", "embedded_project")
    active_skills = state.get("active_skills", [])
    run_dir = state.get("run_dir", "./output")

    run_path = Path(run_dir)
    output_dir = run_path / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    if state.get("framework") == "Arduino":
    # if "arduino" in active_skills:
        code_path = output_dir / "output.ino"
        active_platform = "arduino"
    elif state.get("framework") == "ESP-IDF":
    # if "esp-idf" in active_skills:
        main_dir = output_dir / "main"
        main_dir.mkdir(parents=True, exist_ok=True)
        code_path = main_dir / "main.c"
        active_platform = "esp-idf"
    elif state.get("framework") == "Zephyr":
        main_dir = output_dir / "src"
        main_dir.mkdir(parents=True, exist_ok=True)
        code_path = main_dir / "main.c"
        active_platform = "zephyr"
    else:
        raise NotImplementedError(state.get("framework"))

    workspace: WorkspaceInfo = {
        "output_root": str(output_dir),
        "target": active_platform,
        "project_name": project_name,
    }

    return {
        "prepared_output_dir": str(output_dir),
        "prepared_code_path": str(code_path),
        "active_platform": active_platform,
        "workspace": workspace,
    }


def coder_node(state: AgentState) -> dict:
    """
    Generate the main code file based on requirements and skill standards.

    Reads: requirements, project_name, active_skill_content
    Writes: code_content, messages, active_skills, debug_logs
    """
    llm = get_model()

    skill_instructions = state.get("active_skill_content") or "No specific standards."
    project_name = state.get("project_name", "embedded_project")
    active_skills = state.get("active_skills", [])

    system_prompt = f"""You are an expert Embedded Engineer. Generate ONLY the code for main.c or *.ino file.

Target Project: {project_name}

=== APPLICABLE STANDARDS ===
{skill_instructions}
============================

Task: Write the main C/C++ code file.

RULES:
1. Do NOT ask clarifying questions. Make reasonable engineering assumptions.
2. Output ONLY the code block (inside ```c wrapper).
3. Include all necessary headers based on the requirements.
4. Use reasonable GPIO pins if not specified."""

    messages = [("system", system_prompt), ("user", state["requirements"])]

    start_time = time.time()
    response = llm.invoke(messages)
    duration_ms = (time.time() - start_time) * 1000

    usage = {}
    if hasattr(response, "usage_metadata") and response.usage_metadata:
        usage = dict(response.usage_metadata)

    debug_log = create_debug_log(
        node="coder",
        input_messages={
            "system": system_prompt,
            "user": state["requirements"],
        },
        output=response.content,
        duration_ms=duration_ms,
        metadata={
            "project_name": project_name,
            "active_skills": active_skills,
            "token_usage": usage,
        },
    )

    token_record = {"node": "coder", "usage": usage}

    return {
        "code_content": response.content,
        "messages": [response],
        "active_skills": active_skills,
        "debug_logs": [debug_log],
        "token_usage": [token_record],
    }


def diagram_node(state: AgentState) -> dict:  # noqa: ARG001  # pylint: disable=unused-argument
    """Placeholder for future diagram generation."""
    return {"diagram_content": ""}


def _get_workspace(state: AgentState) -> WorkspaceInfo:
    """Return normalized workspace info from state with compatibility fallbacks."""
    workspace = state.get("workspace", {})
    output_root = workspace.get("output_root") or state.get("prepared_output_dir")
    target = workspace.get("target") or state.get("active_platform")
    project_name = workspace.get("project_name") or state.get("project_name", "output_project")

    if not output_root:
        run_dir = state.get("run_dir", "./output")
        output_root = str(Path(run_dir) / "output")

    if target not in {"arduino", "esp-idf", "zephyr"}:
        active_skills = state.get("active_skills", [])
        target = "arduino" if "arduino" in active_skills else "esp-idf"

    return {
        "output_root": str(output_root),
        "target": target,
        "project_name": project_name,
    }


def assemble_artifacts_node(state: AgentState) -> dict:
    """
    Convert generated outputs into file artifacts without touching disk.
    """
    workspace = _get_workspace(state)
    raw_code = state.get("code_content", "")
    clean_code = extract_clean_code(raw_code)
    diagram_content = (state.get("diagram_content") or "").strip()

    artifacts: List[Artifact] = []
    project_name = workspace["project_name"]
    target = workspace["target"]

    if target == "arduino":
        code_rel_path = "output.ino"
    elif target == "esp-idf":
        code_rel_path = "main/main.c"
    elif target == "zephyr":
        code_rel_path = "src/main.c"
        
    artifacts.append({
        "path": code_rel_path,
        "content": clean_code,
        "role": "code",
    })

    if target == "esp-idf":
        artifacts.append({
            "path": "CMakeLists.txt",
            "content": (
                "cmake_minimum_required(VERSION 3.16)\n"
                "include($ENV{IDF_PATH}/tools/cmake/project.cmake)\n"
                f"project({project_name})"
            ),
            "role": "meta",
        })
        artifacts.append({
            "path": "main/CMakeLists.txt",
            "content": 'idf_component_register(SRCS "main.c" INCLUDE_DIRS ".")',
            "role": "meta",
        })
        artifacts.append({
            "path": "main/idf_component.yml",
            "content": (
                '''version: "1.0.0"
description: "Main application component for ESP32-S3-BOX-3"
dependencies:
    idf: ">=5.0"
    lvgl/lvgl: ^9.2.0
    esp_lcd_ili9341: ^1.0
    espressif/esp_lvgl_port: ^2.6.0
    espressif/mpu6050: "^1.2.0"
'''
            ),
            "role": "meta",
        })
        artifacts.append({
            "path": "sdkconfg",
            "content": ('''# ESP-IDF SDK Configuration
CONFIG_ESPTOOLPY_FLASHMODE_QIO=y
CONFIG_ESPTOOLPY_FLASHFREQ_40M=y
'''
            ),
            "role": "meta",
        })
        artifacts.append({
            "path": "sdkconfig.defaults",
            "content": ('''CONFIG_IDF_TARGET="esp32s3"
'''
            ),
            "role": "meta",
        })
    elif target == "zephyr":
        artifacts.append({
            "path": "CMakeLists.txt",
            "content": (
                "cmake_minimum_required(VERSION 3.20.0)\n"
                "find_package(Zephyr REQUIRED HINTS $ENV{ZEPHYR_BASE})\n"
                f"project({project_name})\n"
                "target_sources(app PRIVATE src/main.c)"
            ),
            "role": "meta",
        })
        artifacts.append({
            "path": "prj.conf",
            "content": ('''# Zephyr Project Configuration
# Turn on the USB Device Stack
CONFIG_USB_DEVICE_STACK=y

# Have Zephyr automatically initialize the USB stack at boot 
# (This saves you from having to write usb_enable() in your C code!)
CONFIG_USB_DEVICE_INITIALIZE_AT_BOOT=y

# Enable the Serial Console over the virtual UART
CONFIG_SERIAL=y
CONFIG_CONSOLE=y
CONFIG_UART_CONSOLE=y
CONFIG_UART_LINE_CTRL=y
CONFIG_I2C=y
CONFIG_SPI=y
CONFIG_CBPRINTF_FP_SUPPORT=y
'''),
            "role": "meta",
        })
        artifacts.append({
            "path": "arduino_nano_33_ble.overlay",
            "content":('''/ {
    chosen {
        /* Route the console to our virtual USB serial port */
        zephyr,console = &cdc_acm_uart0;
    };
};

/* Attach the virtual serial port to the nRF52840's USB controller */
&zephyr_udc0 {
    cdc_acm_uart0: cdc_acm_uart0 {
        compatible = "zephyr,cdc-acm-uart";
    };
};
'''),
            "role":"meta"
        })  
    if diagram_content:
        artifacts.append({
            "path": "wiring/wokwi.json",
            "content": diagram_content,
            "role": "diagram",
        })

    return {
        "workspace": workspace,
        "artifacts": artifacts,
    }


def _validate_artifact_path(output_root: Path, rel_path: str) -> Path:
    """Validate artifact relative path and return resolved absolute path."""
    relative = Path(rel_path)
    if relative.is_absolute():
        raise ValueError(f"Artifact path must be relative: {rel_path}")
    if not rel_path.strip():
        raise ValueError("Artifact path must not be empty.")
    if ".." in relative.parts:
        raise ValueError(f"Artifact path must not contain '..': {rel_path}")

    root_resolved = output_root.resolve()
    final_path = (output_root / relative).resolve()
    final_path.relative_to(root_resolved)
    return final_path


def persist_node(state: AgentState) -> dict:
    """Persist artifacts and run-level metadata to disk."""
    workspace = _get_workspace(state)
    run_dir = state.get("run_dir", "./output")
    run_path = Path(run_dir)
    output_root = Path(workspace["output_root"])
    output_root.mkdir(parents=True, exist_ok=True)

    artifacts = state.get("artifacts", [])
    persisted_paths: List[str] = []
    manifest_artifacts: List[dict] = []

    for artifact in artifacts:
        rel_path = artifact.get("path", "")
        content = artifact.get("content", "")
        role = artifact.get("role", "unknown")

        final_path = _validate_artifact_path(output_root, rel_path)
        final_path.parent.mkdir(parents=True, exist_ok=True)
        final_path.write_text(content, encoding="utf-8")

        payload = content.encode("utf-8")
        manifest_artifacts.append({
            "path": rel_path,
            "role": role,
            "bytes": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
        })
        persisted_paths.append(str(final_path))

    active_skills = state.get("active_skills", [])
    project_name = workspace["project_name"]
    output_type = workspace["target"]

    manifest = {
        "project_name": project_name,
        "target": workspace["target"],
        "active_skills": active_skills,
        "timestamp": datetime.now().isoformat(),
        "artifacts": manifest_artifacts,
    }
    manifest_path = output_root / "manifest.lock.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    debug_logs = state.get("debug_logs", [])
    debug_path = run_path / "debug.json"
    debug_path.write_text(json.dumps(debug_logs, indent=2), encoding="utf-8")

    # Aggregate token usage
    token_usage_records = state.get("token_usage", [])
    total_input = sum(r.get("usage", {}).get("input_tokens", 0) for r in token_usage_records)
    total_output = sum(r.get("usage", {}).get("output_tokens", 0) for r in token_usage_records)

    metadata = {
        "task_name": state.get("task_name", "unknown"),
        "prompt_file": state.get("prompt_file", "unknown"),
        "project_name": project_name,
        "active_skills": active_skills,
        "output_type": output_type,
        "timestamp": datetime.now().isoformat(),
        "requirements": state.get("requirements", ""),
        "token_usage": {
            "per_node": token_usage_records,
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
            "total_tokens": total_input + total_output,
        },
    }
    metadata_path = run_path / "metadata.json"
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    return {
        "manifest_path": str(manifest_path),
        "persisted_paths": persisted_paths,
        "status_msg": f"Project generated at {run_path}",
    }