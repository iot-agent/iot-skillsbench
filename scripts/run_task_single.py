#!/usr/bin/env python3
"""Run the agent graph once for the single task in tasks/single/tmp_task.txt."""

import argparse
import sys
import traceback
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config.yaml"
DEFAULT_TASK_PATH = PROJECT_ROOT / "tasks" / "single" / "tmp_task.txt"

load_dotenv(PROJECT_ROOT / ".env")

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import load_config
from src.graph import build_graph
from src.nodes import configure_auto_pin_mapping, configure_model, configure_registry


def read_task(task_path: Path) -> tuple[str, str]:
    """Read the single task file and derive its task name."""
    if not task_path.exists():
        raise FileNotFoundError(f"Task file not found: {task_path}")

    task_content = task_path.read_text(encoding="utf-8").strip()
    if not task_content:
        raise ValueError(f"Task file is empty: {task_path}")

    return task_path.stem, task_content


def resolve_output_dir(config, output_base: str | None) -> Path:
    """Compute the output directory for a single-task run."""
    if output_base:
        base_dir = Path(output_base)
    else:
        base_dir = PROJECT_ROOT / "output" / f"single-{config.input.board}-{config.input.framework}"

    return base_dir


def log_config(output_dir: Path, config) -> None:
    """Write the effective config values to the output directory."""
    log_path = output_dir / "config.yaml"
    log_path.write_text(
        "\n".join(
            [
                "# Single Task Run Config",
                f"generated: {datetime.now().isoformat()}",
                f"model: {config.model.name}",
                f"temperature: {config.model.temperature}",
                f"api_base: {config.model.api_base}",
                f"use_skills: {config.graph.use_skills}",
                f"skills_dir: {config.graph.skills_dir}",
                f"enable_diagram: {config.graph.enable_diagram}",
                f"auto_pin_mapping: {config.graph.auto_pin_mapping}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"📝 Config logged to {log_path}")


def run_single_task(task_path: Path, task_name: str, task_content: str, config, output_dir: Path) -> Path:
    """Run the agent graph once for a single task."""
    board_name = config.input.board
    framework = config.input.framework
    task_prefix = f"Use board {board_name}, develop with {framework} framework.\n"

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    run_dir = output_dir / task_name
    run_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'=' * 60}")
    print(f"🚀 Running single task: {task_name}")
    print(f"{'=' * 60}")
    print(f"📝 Task file: {task_path}")
    print(f"📝 Task: {task_content}")

    configure_model(
        model_name=config.model.name,
        temperature=config.model.temperature,
        api_base=config.model.api_base,
        api_key_env=config.model.api_key_env,
    )
    configure_auto_pin_mapping(enabled=config.graph.auto_pin_mapping)
    configure_registry(skills_dir=config.graph.skills_dir)

    app = build_graph(
        use_skills=config.graph.use_skills,
        enable_diagram=config.graph.enable_diagram,
        enable_pin_mapper=config.graph.auto_pin_mapping,
    )

    inputs = {
        "requirements": task_prefix + task_content,
        "framework": framework,
        "task_name": task_name,
        "prompt_file": task_path.name,
        "run_dir": str(run_dir),
        "messages": [],
        "debug_logs": [],
        "token_usage": [],
    }

    for event in app.stream(inputs):
        for node_name, output in event.items():
            print(f"\n--- Node: {node_name} ---")
            if node_name == "manager":
                print(f"  Project: {output.get('project_name')}")
                print(f"  Skills: {output.get('active_skills')}")
            elif node_name == "pin_mapper":
                print(f"  Pin Mapping Results:")
                print(output.get("pin_mapping_notes", ""))
            elif node_name == "persist":
                print(f"  {output.get('status_msg')}")

    print(f"✅ Single task complete -> {run_dir}")
    return run_dir


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the IoT agent for one single task")
    parser.add_argument(
        "--config", "-c",
        default=str(DEFAULT_CONFIG_PATH),
        help="Config file (default: config.yaml)",
    )
    parser.add_argument(
        "--task-file",
        default=str(DEFAULT_TASK_PATH),
        help="Single task file to run (default: tasks/single/tmp_task.txt)",
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Output base directory (default: output/single-<board>-<framework>)",
    )
    args = parser.parse_args()

    try:
        config = load_config(args.config)
        task_path = Path(args.task_file).resolve()
        task_name, task_content = read_task(task_path)

        output_dir = resolve_output_dir(config, args.output)
        output_dir.mkdir(parents=True, exist_ok=True)
        log_config(output_dir, config)

        run_dir = run_single_task(task_path, task_name, task_content, config, output_dir)
        print(f"\n📁 Results in: {run_dir}")
        return 0
    except Exception as exc:
        print(f"❌ Single task run failed: {exc}")
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
