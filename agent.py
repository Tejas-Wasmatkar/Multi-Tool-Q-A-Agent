import json
import requests
from bs4 import BeautifulSoup
import fitz  # PyMuPDF
import ollama

MODEL = "qwen2.5"

# ── Tool definitions ─────────────────────────────────────────────────────────

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "browse_web",
            "description": (
                "Fetches the visible text content of a webpage given its URL. "
                "Use this when the user references a website or asks you to look something up online."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The full URL of the webpage to fetch, including https://"
                    }
                },
                "required": ["url"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_pdf_from_url",
            "description": (
                "Downloads a PDF from a URL and extracts its text. "
                "Use this when the user provides a direct link to a PDF file."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The direct URL of the PDF file."
                    }
                },
                "required": ["url"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_pdf_from_text",
            "description": (
                "Reads text already extracted from a locally uploaded PDF. "
                "Use this when the user has uploaded a PDF directly."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "The full extracted text from the PDF."
                    },
                    "filename": {
                        "type": "string",
                        "description": "The original filename of the PDF."
                    }
                },
                "required": ["text", "filename"]
            }
        }
    }
]

# ── Tool implementations ─────────────────────────────────────────────────────

def browse_web(url: str) -> str:
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)
        return text[:6000]
    except Exception as e:
        return f"Error fetching URL: {e}"


def read_pdf_from_url(url: str) -> str:
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        doc = fitz.open(stream=resp.content, filetype="pdf")
        text = "\n".join(page.get_text() for page in doc)
        return text[:6000]
    except Exception as e:
        return f"Error reading PDF: {e}"


def read_pdf_from_text(text: str, filename: str) -> str:
    return f"PDF '{filename}' loaded.\n\n{text[:6000]}"


def dispatch_tool(name: str, args: dict) -> str:
    if name == "browse_web":
        return browse_web(args["url"])
    elif name == "read_pdf_from_url":
        return read_pdf_from_url(args["url"])
    elif name == "read_pdf_from_text":
        return read_pdf_from_text(args["text"], args["filename"])
    return f"Unknown tool: {name}"


# ── Agentic loop ─────────────────────────────────────────────────────────────

def run_agent(user_message: str, pdf_text: str = None, pdf_filename: str = None):
    """
    Agentic loop using Ollama's tool-calling API.

    Yields (type, payload) tuples for the Flask route to stream:
      ("tool_call",   {"name": ..., "input": ...})
      ("tool_result", {"name": ..., "result": ...})
      ("answer",      "final answer string")
    """
    system_prompt = (
        "You are a helpful research assistant with three tools:\n"
        "1. browse_web — fetch and read any webpage\n"
        "2. read_pdf_from_url — download and read a PDF from a URL\n"
        "3. read_pdf_from_text — read a PDF the user already uploaded\n\n"
        "Always use the right tool to gather information before answering. "
        "Cite where your information came from."
    )

    content = user_message
    if pdf_text and pdf_filename:
        content = (
            f"I uploaded a PDF called '{pdf_filename}'. "
            f"Please use the read_pdf_from_text tool to read it. "
            f"Extracted text:\n\n{pdf_text[:5000]}\n\n"
            f"My question: {user_message}"
        )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user",   "content": content}
    ]

    while True:
        response = ollama.chat(
            model=MODEL,
            messages=messages,
            tools=TOOLS
        )

        msg = response["message"]
        messages.append(msg)

        tool_calls = msg.get("tool_calls") or []

        if not tool_calls:
            yield ("answer", msg.get("content", "").strip())
            break

        for tc in tool_calls:
            fn   = tc["function"]
            name = fn["name"]
            args = fn.get("arguments", {})

            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except json.JSONDecodeError:
                    args = {}

            yield ("tool_call", {"name": name, "input": args})

            result = dispatch_tool(name, args)

            yield ("tool_result", {"name": name, "result": result[:300]})

            messages.append({
                "role":    "tool",
                "content": result,
                "name":    name
            })