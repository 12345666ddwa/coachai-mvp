# Running CoachAI with Local Ollama (no API key needed)

Ollama runs open-source models **on your own machine**. There is **no API key**:
it is a local server (default `http://127.0.0.1:11434`). The only key-like value
in the config is a placeholder that the OpenAI SDK requires; the local server
ignores it. You do **not** need to get a key from anyone.

## 1. Install Ollama

- Windows / macOS: download from https://ollama.com/download
- Linux: `curl -fsSL https://ollama.com/install.sh | sh`

Verify: `ollama --version`

## 2. Pull a model

Pick something that fits your machine (7B models run on ~8 GB RAM/VRAM):

```bash
ollama pull qwen2.5:7b        # good general choice (~4.7 GB download)
# alternatives: llama3.1:8b, gemma2:9b, mistral:7b
ollama list                   # confirm what you have
```

## 3. Make sure the server is running

```bash
ollama serve                  # if not already running as a service
curl http://127.0.0.1:11434/api/tags   # should list your models as JSON
```

## 4. Point CoachAI at Ollama

The project's model layer (`agents/models.py`) already supports `ollama` as a
provider. Two ways to use it:

**Option A - environment variables** (in `.env`, all optional; defaults shown):

```
# OLLAMA_BASE_URL=http://127.0.0.1:11434/v1
# OLLAMA_MODEL=qwen2.5:7b
# OLLAMA_API_KEY not needed — a placeholder is used automatically
```

**Option B - per call** (code):

```python
from agents.models import complete

reply = complete(system_prompt="You are a marker.", user_prompt="...",
                 provider="ollama", model="qwen2.5:7b")
```

Switching the whole app to Ollama for local testing:

```python
# in the module that calls complete(), pass provider="ollama"
# upstream logic (marker, verifier, planner, tracker...) needs zero changes.
```

## 5. Test that it works

```bash
python3 - <<'EOF'
from agents.models import complete
print(complete("You are a helpful assistant.", "Reply with exactly: PONG",
               provider="ollama", model="qwen2.5:7b"))
EOF
```

Expect `PONG`. If you get a connection error, the server is not running (step 3).

## Troubleshooting

| Symptom | Fix |
|---|---|
| `Connection refused` / `APIConnectionError` | Start Ollama (`ollama serve`) and confirm `curl http://127.0.0.1:11434/api/tags` works |
| `model not found` | `ollama pull <model>` first; check the exact tag in `ollama list` |
| Very slow replies | A 7B model on CPU is expected to be slow (30-90 s); a GPU or a smaller model (e.g. `qwen2.5:3b`) helps |
| WSL users | If Ollama runs on Windows, WSL can reach it via `http://<windows-host-ip>:11434` (with `OLLAMA_HOST=0.0.0.0` set on Windows) |
| HTTP 403/401 with a key set | Remove `OLLAMA_API_KEY`; local Ollama does not authenticate |

## Notes

- Ollama is **free** and works fully offline after the model download.
- Marking quality with small local models is lower than the cloud model; this
  mode is for local development and the offline-deployment story, not for the
  validated Golden Set numbers (those were measured on DeepSeek).
