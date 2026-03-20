"""
commands/llm_command.py — Send a freeform question to a local or remote LLM.
Triggers: "ask", "hey gpt", "chat", "question"

STATUS: Ready to wire up. Fill in _call_llm() below with your preferred backend.
Supported options (pick one):
  - Ollama local:   http://localhost:11434  (ollama run llama3)
  - OpenAI API:     requires OPENAI_API_KEY env var
  - Anthropic API:  requires ANTHROPIC_API_KEY env var
"""
import os
from bot.speaker import speak

# ── Configuration ─────────────────────────────────────────────────────────────
LLM_BACKEND  = "ollama"          # "ollama" | "openai" | "anthropic"
OLLAMA_MODEL = "llama3"          # any model you have pulled locally
OLLAMA_URL   = "http://localhost:11434/api/generate"
OPENAI_MODEL = "gpt-4o-mini"
MAX_TOKENS   = 150               # keep responses short and speakable


def run(query: str) -> str:
    # Strip trigger words to isolate the actual question
    q = query.lower()
    for prefix in ["ask", "hey gpt", "chat", "question"]:
        if prefix in q:
            q = q.split(prefix, 1)[-1].strip(" :,.")
            break

    if not q:
        speak("What would you like to ask?")
        return "No question given."

    speak("Let me think...")
    response = _call_llm(q)
    speak(response)
    return response


def _call_llm(prompt: str) -> str:
    """
    Call the configured LLM backend and return a plain text response.
    Swap out the backend by changing LLM_BACKEND above.
    """
    try:
        if LLM_BACKEND == "ollama":
            return _ollama(prompt)
        elif LLM_BACKEND == "openai":
            return _openai(prompt)
        elif LLM_BACKEND == "anthropic":
            return _anthropic(prompt)
        else:
            return f"Unknown LLM backend: {LLM_BACKEND}"
    except Exception as e:
        return f"I couldn't get a response. Error: {e}"


def _ollama(prompt: str) -> str:
    import urllib.request, json
    payload = json.dumps({
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"num_predict": MAX_TOKENS}
    }).encode()
    req = urllib.request.Request(OLLAMA_URL, data=payload,
                                  headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read())
    return data.get("response", "No response.").strip()


def _openai(prompt: str) -> str:
    import urllib.request, json
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        return "OpenAI API key not set. Add OPENAI_API_KEY to your environment variables."
    payload = json.dumps({
        "model": OPENAI_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": MAX_TOKENS
    }).encode()
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=payload,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read())
    return data["choices"][0]["message"]["content"].strip()


def _anthropic(prompt: str) -> str:
    import urllib.request, json
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return "Anthropic API key not set. Add ANTHROPIC_API_KEY to your environment variables."
    payload = json.dumps({
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": MAX_TOKENS,
        "messages": [{"role": "user", "content": prompt}]
    }).encode()
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01"
        }
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read())
    return data["content"][0]["text"].strip()