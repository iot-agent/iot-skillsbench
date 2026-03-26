"""
Configuration loading for embed-agent.
"""

from dataclasses import dataclass, field
import os
from pathlib import Path
from typing import Optional, Literal

import yaml

# Valid options for board and framework
BoardType = Literal["esp32_s3_box_3", "arduino_mega_2560", "arduino_nano_33_ble"]
FrameworkType = Literal["ESP-IDF", "Arduino", "Zephyr"]

def get_board_alias(board: BoardType):
    board_name_alias = {
        "esp32_s3_box_3": "ESP32-S3-BOX-3",
        "arduino_mega_2560": "Arduino Mega 2560 R3", 
        "arduino_nano_33_ble": "Arduino Nano 33 BLE",
    }
    return board_name_alias[board]



@dataclass(frozen=True)
class InputConfig:
    """Input-related runtime configuration."""

    task_dir: Optional[str] = None
    prompt_file: Optional[str] = None

    board: BoardType = "esp32_s3_box_3"
    framework: FrameworkType = "Arduino"

@dataclass(frozen=True)
class ModelConfig:
    """LLM-related runtime configuration."""

    name: str = "anthropic/claude-4.5-sonnet"
    temperature: float = 0.0
    api_base: str = ""
    api_key_env: str = "OPENAI_API_KEY"


@dataclass(frozen=True)
class GraphConfig:
    """Graph-related runtime configuration."""

    use_skills: bool = True
    skills_dir: str = "skills"
    enable_diagram: bool = False
    auto_pin_mapping: bool = True


@dataclass(frozen=True)
class AppConfig:
    """Top-level runtime configuration."""

    input: InputConfig = field(default_factory=InputConfig)
    model: ModelConfig = field(default_factory=ModelConfig)
    graph: GraphConfig = field(default_factory=GraphConfig)


def load_config(config_path: str | Path = "config.yaml") -> AppConfig:
    """
    Load application config from a YAML file.

    Args:
        config_path: Path to YAML config file.

    Returns:
        AppConfig object with validated values.
    """
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(
            f"Config file not found: {path}. Please create config.yaml."
        )

    raw = yaml.safe_load(path.read_text()) or {}
    if not isinstance(raw, dict):
        raise ValueError("Invalid config format: root must be a YAML mapping.")

    input_cfg = raw.get("input", {})
    if input_cfg is None:
        input_cfg = {}
    if not isinstance(input_cfg, dict):
        raise ValueError("Invalid config format: 'input' must be a mapping.")

    task_dir = input_cfg.get("task_dir")
    if task_dir is not None and not isinstance(task_dir, str):
        raise ValueError("Invalid config value: 'input.task_dir' must be string.")

    prompt_file = input_cfg.get("prompt_file")
    if prompt_file is not None and not isinstance(prompt_file, str):
        raise ValueError("Invalid config value: 'input.prompt_file' must be string.")

    board = input_cfg.get("board")
    framework = input_cfg.get("framework")

    
    model_cfg = raw.get("model", {})
    if model_cfg is None:
        model_cfg = {}
    if not isinstance(model_cfg, dict):
        raise ValueError("Invalid config format: 'model' must be a mapping.")

    model_name = model_cfg.get("name", "anthropic/claude-4.5-sonnet")
    if not isinstance(model_name, str) or not model_name.strip():
        raise ValueError("Invalid config value: 'model.name' must be non-empty string.")

    temperature = model_cfg.get("temperature", 0.0)
    if not isinstance(temperature, (int, float)):
        raise ValueError("Invalid config value: 'model.temperature' must be numeric.")

    default_api_base = os.environ.get("OPENAI_BASE_URL", "https://openrouter.ai/api/v1")
    api_base = model_cfg.get("api_base", default_api_base)
    if not isinstance(api_base, str) or not api_base.strip():
        raise ValueError("Invalid config value: 'model.api_base' must be non-empty string.")

    api_key_env = model_cfg.get("api_key_env", "OPENAI_API_KEY")
    if not isinstance(api_key_env, str) or not api_key_env.strip():
        raise ValueError("Invalid config value: 'model.api_key_env' must be non-empty string.")

    graph_cfg = raw.get("graph", {})
    if graph_cfg is None:
        graph_cfg = {}
    if not isinstance(graph_cfg, dict):
        raise ValueError("Invalid config format: 'graph' must be a mapping.")

    use_skills = graph_cfg.get("use_skills", True)
    if not isinstance(use_skills, bool):
        raise ValueError("Invalid condig value: 'graph.use_skills' must be boolean.")
    skills_dir = graph_cfg.get("skills_dir", "skills")
    if not isinstance(skills_dir, str) or not skills_dir.strip():
        raise ValueError("Invalid config value: 'graph.skills_dir' must be non-empty string.")
    enable_diagram = graph_cfg.get("enable_diagram", False)
    if not isinstance(enable_diagram, bool):
        raise ValueError("Invalid config value: 'graph.enable_diagram' must be boolean.")
    auto_pin_mapping = graph_cfg.get("auto_pin_mapping")
    if auto_pin_mapping is None:
        # Backward compatibility with older config key
        auto_pin_mapping = graph_cfg.get("pin_mapper_on_missing_pins", True)
    if not isinstance(auto_pin_mapping, bool):
        raise ValueError("Invalid config value: 'graph.auto_pin_mapping' must be boolean.")

    return AppConfig(
        input=InputConfig(
            task_dir=task_dir,
            prompt_file=prompt_file,
            board=board,
            framework=framework,
        ),
        model=ModelConfig(
            name=model_name,
            temperature=float(temperature),
            api_base=api_base,
            api_key_env=api_key_env,
        ),
        graph=GraphConfig(
            use_skills=use_skills,
            skills_dir=skills_dir,
            enable_diagram=enable_diagram,
            auto_pin_mapping=auto_pin_mapping,
        ),
    )
