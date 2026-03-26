# Skilled AI Agents for Embedded and IoT Systems Development

[![Paper](https://img.shields.io/badge/Paper-ArXiv-red.svg)](https://arxiv.org/abs/2603.19583)
[![License](https://img.shields.io/badge/license-Apache%202-blue)](LICENSE)

Official codebase for the paper: **"Skilled AI Agents for Embedded and IoT Systems Development"**.

## Overview

Large language models (LLMs) and agentic systems show immense promise for automated software development. However, applying them to hardware-in-the-loop (HIL) embedded and IoT systems is notoriously difficult due to the tight coupling between software logic, timing constraints, and physical hardware behavior. Code that compiles successfully often fails on real devices.

To bridge this gap, we introduce a **skills-based agentic framework** and **IoT-SkillsBench**.

![System Overview](docs/assets/system-overview.png)

### Highlights:

- **IoT-SkillsBench** — A benchmark for evaluating AI agents in real embedded programming environments, spanning 3 platforms, 23 peripherals, and 42 tasks across 3 difficulty levels.
- **Skills-based agentic framework** — A structured approach to injecting domain knowledge into LLM-based agents for embedded development.
- **378 hardware-validated experiments** — Each task evaluated under three agent configurations (no-skills, LLM-generated skills, and human-expert skills) and validated through real hardware execution, demonstrating that structured human-expert skills enable near-perfect success rates.

### Demo #1 (Arduino Mega 2560 + Arduino):

💡 Feel free to build your own tasks by creatively combining hardware components from [this peripheral list](docs/atmega2560-arduino-wiring.md) using the wiring diagram below. Here is one example:
```
Set RTC to Mar. 3, 2025 at 14:53:28. 
Then, start collecting MPU6050 measurements every second.
Display the MPU6050 results and date/time on LCD1602 every second.
Also print results to serial.
```

![Demo Mega2560 Combined](docs/assets/atmega2560-arduino-wiring-15-peripherals-annotated.png)

### Demo #2 (ESP32-S3 + ESP-IDF):
```
Task: "Write the program that will read the password input from the 16-key keypad (password is set to "1234").
If the keypad input matches the password, the program will connect the relay to unlock the safebox.
The program will also display the input password on the LCD1602 display in the format.
```

![Demo ESP-IDF Safebox](docs/assets/demo-esp-idf-safebox.webp)


---


## Repository Structure

```
.
├── docs/                         # Documentation and assets
│   ├── assets
│   └── ...
├── scripts/
│   ├── batch_run.py              # Batch task execution
│   ├── auto_test.py              # Automated compile-and-retry (Arduino only)
│   └── run_task_single.py        # Run a single task
├── skills-human-expert/          # Curated human-expert skills
├── skills-llm-generated/         # LLM-generated skills
├── src/                          # Agentic framework (e.g., based on LangGraph)
│   ├── ...
│   └── ...
├── tasks/                        # Task definitions per board/framework
│   ├── level1/
│   ├── level2/
│   ├── level3/
│   └── single/
│       └── tmp_task.txt          # Example task for testing the agent
├── output/                       # Generated code and metadata (created at runtime)
├── config.template.yaml          # Configuration template (copy to config.yaml)
├── config.yaml                   # Local configuration — DO NOT commit
└── .env                          # Local API keys — DO NOT commit
```

---

## Installation

**Prerequisites:** Python 3.9+

1. **Clone the repository:**

```bash
git clone https://github.com/YOUR_ORG/YOUR_REPO.git
cd YOUR_REPO
```

2. **Install dependencies:**

```bash
pip install -r requirements.txt
```

Key dependencies include LangChain, LangGraph, and the relevant LLM provider SDKs. See `requirements.txt` for the full list.

3. **Set up your API key:**

Create a `.env` file in the project root:

```dotenv
OPENROUTER_API_KEY=your_key_here
```

This file is listed in `.gitignore` and should never be committed.

4. **Create your local configuration:**

```bash
cp config.template.yaml config.yaml
```

Edit `config.yaml` for your environment. The template contains all available options and their defaults — see [Configuration](#configuration) for details.

Hardware-in-the-loop evaluation additionally requires a supported board and the corresponding toolchain (see [Evaluation](#evaluation)).

---

## Quick Start

After completing the [Installation](#installation) steps, run a task:

**Single task run (`tasks/single/tmp_task.txt`):**

```bash
python scripts/run_task_single.py -o scripts/tmp_output
```

**Batch run (benchmark file + task id):**

```bash
python scripts/batch_run.py -i tasks/level3/level3-ATmega2560-Arduino.txt -t Safe_Box_with_display
```

Output is written to:

```
output/tasks-{board}-{framework}/w_skills_{skills_dir}/{model.name}/{task_id}/
```

---

## Configuration

All settings are controlled through `config.yaml`, created by copying `config.template.yaml` (see [Installation](#installation)).

### Skills

Enable or disable skill injection, and select the skill set:

```yaml
graph:
  use_skills: true
  skills_dir: skills-human-expert/   # or skills-llm-generated/
```

### Board and Framework

Select the target embedded platform:

```yaml
input:
  board: esp32_s3_box_3
  framework: ESP-IDF
```

Supported combinations:

| Board                  | Framework |
|------------------------|-----------|
| `esp32_s3_box_3`       | ESP-IDF   |
| `arduino_mega_2560`    | Arduino   |
| `arduino_nano_33_ble`  | Zephyr    |

### Model

Specify the LLM used for code generation:

```yaml
model:
  name: "claude-sonnet-4-5"
```

### Expected Run Outputs

Each run creates:

- Generated source under run-specific output directory
- `manifest.lock.json` (artifact manifest)
- `metadata.json` (task/config/token usage)
- `debug.json` (per-node debug traces)

---

## Evaluation

### Build and Flash

After code generation, the output must be compiled and flashed to the target board using the platform's native toolchain. Please refer to each platform's official documentation for detailed setup and usage:

- **ESP-IDF** — [ESP-IDF Get Started](https://docs.espressif.com/projects/esp-idf/en/latest/esp32/get-started/)
- **Arduino** — [Arduino CLI Documentation](https://arduino.github.io/arduino-cli/latest/)
- **Zephyr** — [Zephyr Getting Started Guide](https://docs.zephyrproject.org/latest/develop/getting_started/index.html)

As an example, for an Arduino Mega on macOS:

```bash
# Compile and upload
arduino-cli compile --upload --port /dev/cu.usbmodemxxxx --fqbn arduino:avr:mega ./

# Open serial monitor
arduino-cli monitor -p /dev/cu.usbmodemxxxx --config 115200
```

For Arduino targets, an automated compile-and-retry script is also available — see `scripts/auto_test.py`.

### Token Usage

Each run produces a `metadata.json` in the output directory with per-node and aggregate token counts:

```json
{
  "token_usage": {
    "per_node": [
      {"node": "manager", "usage": {"input_tokens": 512,  "output_tokens": 89,   "total_tokens": 601}},
      {"node": "coder",   "usage": {"input_tokens": 2048, "output_tokens": 1500, "total_tokens": 3548}}
    ],
    "total_input_tokens": 2560,
    "total_output_tokens": 1589,
    "total_tokens": 4149
  }
}
```

Token tracking is implemented using [`AIMessage`](https://reference.langchain.com/python/langchain-core/messages/ai/AIMessage) from LangChain Core.

---

## Citation

If you use this code or benchmark in your research, please cite:

```bibtex
@article{li2026skilledaiagentsembedded,
      title={Skilled AI Agents for Embedded and IoT Systems Development}, 
      author={Li, Yiming and Cheng, Yuhan and Ma, Mingchen and Zou, Yihang and Yang, Ningyuan and Cheng, Wei and Li, Hai "Helen" and Chen, Yiran and Chen, Tingjun},
      journal={arXiv preprint arXiv:2603.19583},
      year={2026}
}
```

---

## License

This project is released under the [Apache 2.0 License](LICENSE).

---

## Contact

We welcome feedback, collaboration, and contributions.

- 💬 Open an issue for questions or feature requests
