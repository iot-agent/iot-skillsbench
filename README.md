# Skilled AI Agents for Embedded and IoT Systems Development

[![Paper](https://img.shields.io/badge/Paper-ArXiv-red.svg)](https://arxiv.org/abs/2603.19583)
[![License](https://img.shields.io/badge/license-Apache%202-blue)](LICENSE)

Official codebase for the paper: **"Skilled AI Agents for Embedded and IoT Systems Development"**.

## Overview

Large language models (LLMs) and agentic systems show immense promise for automated software development. However, applying them to hardware-in-the-loop (HIL) embedded and IoT systems is notoriously difficult due to the tight coupling between software logic, timing constraints, and physical hardware behavior. Code that compiles successfully often fails on real devices.

To bridge this gap, we introduce a **skills-based agentic framework** and **IoT-SkillsBench**.

![demo](docs/assets/system-overview.png)

### Key Contributions

- **IoT-SkillsBench** — A benchmark for evaluating AI agents in real embedded programming environments, spanning 3 platforms, 23 peripherals, and 42 tasks across 3 difficulty levels.
- **Skills-based agentic framework** — A structured approach to injecting domain knowledge into LLM-based agents for embedded development.
- **378 hardware-validated experiments** — Each task evaluated under three agent configurations (no-skills, LLM-generated skills, and human-expert skills) and validated through real hardware execution, demonstrating that structured human-expert skills enable near-perfect success rates.



https://github.com/user-attachments/assets/e9f83311-8c1b-4790-baca-0ed0304bca5b


---


## Repository Structure

```
.
├── scripts/
│   ├── batch_run.py              # Batch task execution
│   └── auto_test.py              # Automated compile-and-retry (Arduino only)
├── tasks/
│   ├── level1/
│   ├── level2/
│   └── level3/                   # Task definitions per board/framework
├── skills-human-expert/          # Curated human-expert skills
├── skills-llm-generated/         # LLM-generated skills
├── outputs/                      # Generated code and metadata (created at runtime)
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

```bash
python scripts/batch_run.py -i tasks/level3/level3-ATmega2560-Arduino.txt -t Safe_Box_with_display
```

Output is written to:

```
outputs/tasks-{board}-{framework}/w_skills_{skills_dir}/{model.name}/{task_id}/
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
@misc{li2026skilledaiagentsembedded,
      title={Skilled AI Agents for Embedded and IoT Systems Development}, 
      author={Yiming Li and Yuhan Cheng and Mingchen Ma and Yihang Zou and Ningyuan Yang and Wei Cheng and Hai "Helen" Li and Yiran Chen and Tingjun Chen},
      year={2026},
      eprint={2603.19583},
      archivePrefix={arXiv},
      primaryClass={cs.SE},
      url={https://arxiv.org/abs/2603.19583}, 
}
```

---

## License

This project is released under the [Apache 2.0 License](LICENSE).
