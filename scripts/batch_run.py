#!/usr/bin/env python3
"""Batch evaluation script for IoT agent.

Reads tasks from design_list-arduino.txt (separated by [labX_taskY])
and runs create_and_build for each task, outputting to iot_project/labX_taskY/
"""

import argparse
import os
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.config import load_config
from src.graph import build_graph
from src.nodes import configure_auto_pin_mapping, configure_model, configure_registry


def parse_tasks(filepath: str) -> dict:
    def _parse_tasks_from_file(filepath: str) -> dict:
        """Parse tasks from design list file.

        Args:
            filepath: Path to design_list file

        Returns:
            Dict mapping task_id (e.g., 'lab1_task1') to task description
        """
        with open(filepath, 'r') as f:
            content = f.read()

        
        # pattern = r'\[(lab\d+_task\d+)\]'   # Split by [labX_taskY] markers
        pattern = r'\[([^\]]+)\]'   # Split by [anything] markers
        parts = re.split(pattern, content)

        tasks = {}
        # parts[0] is empty or content before first marker
        # then alternating: task_id, task_content, task_id, task_content, ...
        for i in range(1, len(parts), 2):
            task_id = parts[i]
            task_content = parts[i + 1].strip() if i + 1 < len(parts) else ""
            if task_content:
                tasks[task_id] = task_content

        return tasks
    
    def _parse_tasks_from_files(input_dir: str) -> dict:
        """Parse tasks from individual design.txt files in a directory.

        Args:
            input_dir: Directory containing subdirectories for each task, each with a design.txt
        Returns:
            Dict mapping task_id to task description
        """
        tasks = {}
        for task_id in sorted(os.listdir(input_dir)):
            task_dir = os.path.join(input_dir, task_id)
            if not os.path.isdir(task_dir):
                continue
            design_path = os.path.join(task_dir, f"{task_id}.txt")
            if os.path.exists(design_path):
                with open(design_path, "r") as f:
                    task_content = f.read().strip()
                    if task_content:
                        tasks[task_id] = task_content
                        print(f"📂 Loaded {task_id} from {design_path}")
                    else:
                        print(f"⚠️  Warning: {design_path} is empty")
            else:
                print(f"⚠️  Warning: No {task_id}.txt found in {task_dir}")
        return tasks
    
    if os.path.isdir(filepath):
        return _parse_tasks_from_files(filepath)
    else:
        return _parse_tasks_from_file(filepath)

def write_tasks_to_files(tasks: dict, output_base: str):
    """Write each task to a separate design.txt file in its own directory.

    Args:
        tasks: Dict mapping task_id to task description
        output_base: Base output directory
    """
    for task_id, task_content in tasks.items():
        task_dir = os.path.join(output_base, task_id)
        os.makedirs(task_dir, exist_ok=True)
        design_path = os.path.join(task_dir, f"{task_id}.txt")
        with open(design_path, "w") as f:
            f.write(task_content)
        print(f"📝 Task {task_id} written to {design_path}")


def run_task(task_id: str, task_content: str, config, output_dir: str):
    """Run a single task.

    Args:
        task_id: Task identifier (e.g., 'lab1_task1')
        task_content: Task description
        config: Configuration object
        input_dir: Input directory containing task definitions (e.g., 'tasks_arduino')
    """
    print(f"\n{'='*60}")
    print(f"🚀 Running {task_id}")
    print(f"{'='*60}")
    print(f"📝 Task: {task_content[:]}")
    
    # Task prefix: board and development framework
    board_name = config.input.board
    framework = config.input.framework
    task_prefix = f"Use board {board_name}, develop with {framework} framework.\n"
    print(f"📝 Task Prefix: {task_prefix}")

    # Create timestamped run directory under the task directory
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    run_dir = Path(output_dir) / task_id / "runs" / timestamp
    run_dir.mkdir(parents=True, exist_ok=True)

    # Run the graph
    try:
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
            "task_name": task_id,
            "prompt_file": f"{task_id}.txt",
            "run_dir": str(run_dir),
            "messages": [],
            "debug_logs": [],
            "token_usage": [],
        }

        for event in app.stream(inputs):
            for node_name, output in event.items():
                print(f"--- Node: {node_name} ---")
                if node_name == "manager":
                    print(f"  Project: {output.get('project_name')}")
                    print(f"  Skills: {output.get('active_skills')}")
                elif node_name == "persist":
                    print(f"  {output.get('status_msg')}")

        print(f"✅ {task_id} complete -> {run_dir}")

    except Exception as e:
        print(f"❌ {task_id} failed: {e}")
        import traceback
        traceback.print_exc()



def log_config(output_dir: str, config):
    """Log config values to a YAML file in the output directory."""
    log_path = os.path.join(output_dir, "config.yaml")

    with open(log_path, "w") as f:
        f.write(f"# Batch Evaluation Config\n")
        f.write(f"generated: {datetime.now().isoformat()}\n\n")
        f.write(f"model: {config.model.name}\n")
        f.write(f"temperature: {config.model.temperature}\n")
        f.write(f"api_base: {config.model.api_base}\n")
        f.write(f"use_skills: {config.graph.use_skills}\n")
        f.write(f"skills_dir: {config.graph.skills_dir}\n")
        f.write(f"enable_diagram: {config.graph.enable_diagram}\n")
        f.write(f"auto_pin_mapping: {config.graph.auto_pin_mapping}\n")

    print(f"📝 Config logged to {log_path}")


def main():    
    parser = argparse.ArgumentParser(description="Batch evaluation for IoT agent")
    parser.add_argument(
        "--config", "-c",
        default="config.yaml",
        help="Config file (default: config.yaml)"
    )
    parser.add_argument(
        "--input", "-i",
        default="tasks_arduino.txt",
        help="Input task list file (default: tasks_arduino.txt)"
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Output base directory (default: output/tasks-<board>-<framework>)"
    )
    parser.add_argument(
        "--tasks", "-t",
        nargs="*",
        help="Specific tasks to run (e.g., lab1_task1 lab2_task2). If not specified, runs all."
    )
    parser.add_argument(
        "--repeat", "-r",
        type=int,
        default=1,
        help="Number of times to repeat each task (default: 1)"
    )
    args = parser.parse_args()


    # Load configuration
    config = load_config(args.config)

    # Parse tasks
    tasks = parse_tasks(args.input)
    print(f"📋 Found {len(tasks)} tasks in {args.input}")

    # Filter tasks if specified
    if args.tasks:
        tasks = {k: v for k, v in tasks.items() if k in args.tasks}
        print(f"🎯 Running {len(tasks)} selected tasks: {list(tasks.keys())}")

    # Create output directory
    # output_dir = args.output

    # Output dir: default under root "output/" folder
    if args.output:
        base_name = args.output
    else:
        base_name = os.path.join("output", f"tasks-{config.input.board}-{config.input.framework}")
    if config.graph.use_skills:
        skills_dir_name = os.path.basename(config.graph.skills_dir.rstrip('/'))
        skill_suffix = f"w_skills_{skills_dir_name}"
    else:
        skill_suffix = "wo_skills"
    model_suffix = config.model.name
    output_dir = os.path.join(base_name, skill_suffix, model_suffix)
    # output_dir = base_name

    os.makedirs(output_dir, exist_ok=True)

    log_config(output_dir, config)

    # Run each task (with repetitions)
    total_runs = len(tasks) * args.repeat
    run_count = 0
    for task_id, task_content in tasks.items():
        for rep in range(1, args.repeat + 1):
            run_count += 1
            rep_label = f" [Rep {rep}/{args.repeat}]" if args.repeat > 1 else ""
            print(f"\n📊 Run {run_count}/{total_runs}{rep_label}")
            run_task(task_id, task_content, config, output_dir)

    print(f"\n{'='*60}")
    print(f"🏁 Batch evaluation complete ({total_runs} total runs)")
    print(f"📁 Results in: {output_dir}/")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
