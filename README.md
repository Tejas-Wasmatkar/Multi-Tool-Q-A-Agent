# Multi-Tool Research Agent

A locally running agentic AI that can browse websites, read PDFs, and answer questions — powered by [qwen2.5](https://ollama.com/library/qwen2.5) via [Ollama](https://ollama.com) and served through a Flask web UI.

No API keys. No cloud. Everything runs on your machine.

---

## What it does

You ask a question. The agent decides which tools it needs, calls them, reads the results, and gives you a sourced answer. You can watch every tool call happen in real time in the UI.

**Three tools available:**

| Tool | What it does |
|---|---|
| `browse_web` | Fetches and reads the visible text of any webpage |
| `read_pdf_from_url` | Downloads and extracts text from a PDF at a URL |
| `read_pdf_from_text` | Reads a PDF you upload directly from your computer |

**Example prompts to try:**

- `Summarise https://en.wikipedia.org/wiki/Agentic_AI`
- `What are the key findings in this paper?` *(upload a PDF)*
- `Compare the pricing on https://somesite.com/pricing`
- `Read https://arxiv.org/pdf/2303.08774 and list the main contributions`

---

## Project structure

```
multi_tool_agent/
├── agent.py              # Agentic loop + tool definitions and implementations
├── app.py                # Flask server with SSE streaming
├── templates/
│   └── index.html        # Chat UI
├── requirements.txt      # Python dependencies
└── README.md
```

---

## Prerequisites

- Python 3.9 or higher
- [Ollama](https://ollama.com) installed and running
- qwen2.5 model pulled locally

---

## Setup

### 1. Install Ollama

Download from [https://ollama.com](https://ollama.com) and follow the installer for your OS (macOS, Linux, or Windows).

### 2. Pull the qwen2.5 model

```bash
ollama pull qwen2.5
```

This downloads ~4.7 GB on first run. You only need to do this once.

### 3. Clone or download this project

```bash
git clone <your-repo-url>
cd multi_tool_agent
```

Or just place all the files in a folder called `multi_tool_agent`.

### 4. Install Python dependencies

```bash
pip install -r requirements.txt
```

---

## Running the app

**Terminal 1 — start Ollama:**

```bash
ollama serve
```

**Terminal 2 — start the Flask app:**

```bash
python app.py
```

Then open your browser at:

```
http://localhost:5000
```

---

## How it works

The core of the project is the **agentic loop** in `agent.py`. Here's the flow:

```
User asks a question
        │
        ▼
  Send to qwen2.5 with tool definitions
        │
        ▼
  Did the model call a tool?
    ├── YES → Execute the tool → Feed result back → Loop again
    └── NO  → Return the final answer to the user
```

This loop continues until the model is satisfied it has enough information to answer — it may call one tool or several in sequence.

The Flask app streams events back to the browser using **Server-Sent Events (SSE)** so you can watch tool calls happen in real time without waiting for the full response.

---

## Key files explained

### `agent.py`

Contains three sections:

- **TOOLS** — the tool schema in OpenAI-compatible format that tells qwen2.5 what tools exist and what arguments they take
- **Tool implementations** — the actual Python functions (`browse_web`, `read_pdf_from_url`, `read_pdf_from_text`) that do the real work
- **`run_agent()`** — the agentic loop that sends messages to Ollama, checks for tool calls, executes them, and yields streaming events

### `app.py`

A minimal Flask server with two routes:

- `GET /` — serves the chat UI
- `POST /ask` — accepts the user's question and optional PDF upload, then streams agent events back as SSE

### `templates/index.html`

A self-contained chat interface. Displays user messages, assistant answers, and tool call/result blocks as they stream in. No external JS frameworks — plain HTML, CSS, and vanilla JS.

---

## Changing the model

To use a different Ollama model, edit the top of `agent.py`:

```python
MODEL = "qwen2.5"  # change to e.g. "llama3.1:8b" or "mistral"
```

Then make sure the model is pulled:

```bash
ollama pull llama3.1:8b
```

Note: not all models support tool calling reliably. Models known to work well: `qwen2.5`, `llama3.1`, `mistral`, `llama3.2`.

---

## Configuration

| Setting | Where | Default |
|---|---|---|
| Model name | `agent.py` → `MODEL` | `qwen2.5` |
| Max webpage text | `agent.py` → `browse_web()` | 6000 chars |
| Max PDF text | `agent.py` → `read_pdf_from_url/text()` | 6000 chars |
| Max upload size | `app.py` → `MAX_CONTENT_LENGTH` | 20 MB |
| Port | `app.py` → `app.run()` | 5000 |

---

## Extending the agent

Adding a new tool takes three steps:

**1. Define it in `TOOLS`** (in `agent.py`):

```python
{
    "type": "function",
    "function": {
        "name": "my_tool",
        "description": "What this tool does and when to use it.",
        "parameters": {
            "type": "object",
            "properties": {
                "my_param": {"type": "string", "description": "..."}
            },
            "required": ["my_param"]
        }
    }
}
```

**2. Implement the function:**

```python
def my_tool(my_param: str) -> str:
    # do something
    return "result as a string"
```

**3. Add a case to `dispatch_tool()`:**

```python
elif name == "my_tool":
    return my_tool(args["my_param"])
```

That's it — the agent will start using it automatically.

---

## Troubleshooting

**`ollama: command not found`**
Make sure Ollama is installed and on your PATH. Try running `ollama serve` first.

**`Connection refused` when starting the app**
Ollama isn't running. Start it with `ollama serve` in a separate terminal.

**Model doesn't call any tools**
Some smaller models ignore tool definitions. Switch to `qwen2.5` or `llama3.1:8b` which have reliable tool-calling support.

**PDF upload fails**
Check that `pymupdf` is installed (`pip install pymupdf`) and the file is a valid PDF under 20 MB.

**Slow responses**
qwen2.5 is a 7B model — first response after startup is slower as the model loads into memory. Subsequent calls are faster. For faster responses, try `llama3.2` (3B).

---

## Dependencies

| Package | Purpose |
|---|---|
| `ollama` | Python client for the Ollama API |
| `flask` | Web server and SSE streaming |
| `requests` | HTTP requests for web browsing and PDF downloads |
| `beautifulsoup4` | HTML parsing and text extraction |
| `pymupdf` | PDF text extraction |

---

## Learning resources

Now that you have this running, good next steps:

- [Ollama tool use docs](https://ollama.com/blog/tool-support) — how tool calling works under the hood
- [Model Context Protocol (MCP)](https://modelcontextprotocol.io) — the standard for connecting agents to external tools
- [Anthropic's agent patterns guide](https://docs.anthropic.com/en/docs/build-with-claude/tool-use) — patterns for building reliable agents