# Beyond Prompting — Agentic AI: Live Workshop Repository

**Hands-on workshop:** *Beyond Prompting: Engineering Intelligent Agentic AI Systems with Context, Tools, Loops, Graphs & Harnesses*

This repository contains the **actual workshop teaching programs**, the editable slide deck, and the inventory CSV. Code is organized by approach so participants can run the demonstrations on their own laptops and inspect which component selects actions and which component executes them.

## Quick start (Windows)

1. Download the repository ZIP from GitHub (**Code → Download ZIP**) and extract it. Open a terminal in the extracted folder.
2. Create and activate a Python environment:
   ```cmd
   py -m venv .venv
   .venv\Scripts\activate.bat
   python -m pip install -r requirements.txt
   ```
   PowerShell activation: `.\.venv\Scripts\Activate.ps1` (subject to your execution policy).
3. Copy `.env.example` to `.env`. Edit `.env` and replace `PASTE_YOUR_PERSONAL_GROQ_KEY_HERE` with your **own** Groq API key from https://console.groq.com/keys. Never commit `.env`.
4. Start with the **no-API** rules demo:
   ```cmd
   python 00_rule_based_math.py --expression "12 + 8 * 3 - 10 / 5" --trace NO
   python 00_rule_based_inventory.py --trace NO
   ```
5. When the key is configured, run the model-powered demos below.

### macOS / Linux setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
```

Open `.env`, add your key, then use `python` in the commands below.

## Workshop programs

| Approach | Math demonstration | Inventory demonstration | Main idea |
|---|---|---|---|
| Baseline chat | `normal_llm01.py` (single API request), `normal_llm02.py` (interactive chat) | — | Remote LLM replies; no local tools |
| 0 — Rule-based | `00_rule_based_math.py` | `00_rule_based_inventory.py` | Python decides and executes; no API |
| 1 — Normal LLM | `01_normal_llm_math.py` | `01_normal_llm_inventory.py` | LLM produces the answer without local tool calling |
| 2 — Agentic tools | `02_agentic_math_tools.py` | `02_agentic_tools_inventory.py` | LLM selects local functions, Python executes |
| 3 — Graph/harness/loop | `03_graph_harness_math.py` | `03_graph_harness_inventory.py` | Explicit validation, feedback, state, and retries |

**Shared inventory code:** `common.py` provides `load_inventory`, `read_product`, `restock_row`, `print_report`, and `save_report`. All inventory scripts must stay in the same directory as `common.py` and `inventory.csv`.

## Copy-and-run commands

```bash
# Baseline: one simple API call and interactive chat
python normal_llm01.py
python normal_llm02.py                  # enter q to quit

# Rule-based: works without Groq
python 00_rule_based_math.py --expression "12 + 8 * 3 - 10 / 5" --trace NO
python 00_rule_based_inventory.py --trace NO

# Normal LLM: calculates without tools
python 01_normal_llm_math.py --expression "12 + 8 * 3 - 10 / 5"
python 01_normal_llm_inventory.py

# Agentic: Groq requests a Python function; Python performs the operation
python 02_agentic_math_tools.py --expression "12 + 8 * 3 - 10 / 5"
python 02_agentic_tools_inventory.py --trace NO

# Graph/Harness: validation, feedback, retry, state update
python 03_graph_harness_math.py --expression "12 + 8 * 3 - 10 / 5"
python 03_graph_harness_inventory.py --trace NO
```

**Interactive pauses:** Several math scripts deliberately stop at `Press <Enter>` checkpoints for live teaching. The inventory demos support `--trace YES` for detailed interactive pauses and `--trace NO` to run without them. `01_normal_llm_inventory.py` still has intentional Enter pauses.

## Inventory example and failure experiment

`inventory.csv` includes an **intentional invalid price**: product `P003` has `price = X`. Do not remove this until after the failure demo.

- Rule-based and direct-LLM inventory demos use `load_inventory()` to skip malformed rows before processing.
- Agentic Tools inventory skips an invalid row and moves on.
- Graph/Harness inventory gives each invalid product **up to three attempts**; you may edit the CSV value between attempts with `--trace YES` before it skips the row.
- Duplicate product IDs do not by themselves invalidate a row; product-reading tools use the one-based **CSV data row number**.
- The number of products is read from the CSV; it is not hardcoded to 15.

To see the three-retry harness demonstration, leave `P003.price=X` and run:

```bash
python 03_graph_harness_inventory.py --trace YES
```

To test successful execution afterward, change `P003.price` to a valid nonnegative numeric price, save the CSV, and rerun.

## What is really executed?

- A model **requests** a tool; it never runs Python on your laptop itself.
- `TOOLS` gives the LLM names, descriptions and JSON argument definitions; `FUNCTIONS` maps approved names to actual Python callables.
- Tool outputs must be appended to the conversation and sent to the LLM in a subsequent API call.
- The rule-based and inventory restock functions calculate in Python. The direct-answer LLM and the math graph's final response are not independently certified just by a generated explanation.
- The application controls phases, allowed tool calls, retries, and safety limits; `tool_choice="auto"` does not guarantee that a model selects a tool.

## Folder contents

- `docs/WORKSHOP_GUIDE.md` — presenter and attendee walkthrough, demo order, troubleshooting.
- `docs/REPO_RELEASE_NOTES.md` — precise changes made when packaging uploads.
- `tests/` — local offline smoke tests; no Groq key needed.
- `OUTPUT/` — generated results and logs (ignored by Git except `.gitkeep`).

## Safety and API costs

Every participant should use a **personal** Groq key. The `.env` file is ignored by Git. Do not paste API keys into the presentation, source code, commits, or screenshots. Groq has limits and may charge for API usage depending on the plan; model availability can change. Several agentic demonstrations make multiple remote calls per product, and a full inventory run may take longer than a few seconds.

## Troubleshooting

- `ModuleNotFoundError: dotenv` → activate your environment and run `python -m pip install -r requirements.txt`.
- `GROQ_API_KEY missing` → copy `.env.example` to `.env` and insert a real key.
- `401` / `403` → check your key and Groq account permissions; never share the key publicly.
- `429` → your API rate/token limit was reached; wait for quota or reduce calls.
- `FileNotFoundError inventory.csv` → keep the CSV next to `common.py`, and run scripts from this repository.
- `InvalidOperation` or nonnumeric CSV value → use the invalid-input workshop exercise and verify the program skips/retries instead of crashing.
- No agentic tool request → `tool_choice="auto"` permits the model not to select a tool; the demo logs this outcome.
- `Press <Enter>` → this is a teaching checkpoint, not a frozen program.

For further steps, see [the workshop guide](docs/WORKSHOP_GUIDE.md).
