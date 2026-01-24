# Troubleshooting

Common issues and solutions when using agent-skills.

## Router Service Issues

### "Connection refused" when using /delegate

**Problem:** Claude Code can't connect to the router service.

**Solution:** Start the router service before using `/delegate`:

```bash
cd ~/agent-skills/router-service
source .venv/bin/activate
uvicorn router:app --host 127.0.0.1 --port 8765
```

To verify it's running:
```bash
curl http://127.0.0.1:8765/health
```

### Router service fails to start

**Problem:** `uvicorn` or dependencies not found.

**Solution:** Re-run the install script or manually set up the virtual environment:

```bash
cd ~/agent-skills/router-service
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn router:app --host 127.0.0.1 --port 8765
```

### Port 8765 already in use

**Problem:** Another process is using the router port.

**Solution:** Find and kill the existing process, or use a different port:

```bash
# Find what's using the port
lsof -i :8765

# Kill it (replace PID with actual process ID)
kill <PID>

# Or use a different port
uvicorn router:app --host 127.0.0.1 --port 8766
```

If using a different port, update the curl commands in your skills accordingly.

---

## CLI Tool Issues

### "Command not found: codex" (or copilot, gemini, cursor)

**Problem:** The CLI tool isn't installed or isn't in your PATH.

**Solution:** Install the CLI tool:

```bash
# OpenAI Codex
npm install -g @openai/codex

# GitHub Copilot
npm install -g @githubnext/github-copilot-cli

# Gemini CLI
npm install -g @google/generative-ai

# Cursor - install from https://cursor.com
```

Then verify:
```bash
codex --version
gh copilot --version
gemini --version
cursor --version
```

### API key not set

**Problem:** The CLI runs but fails with authentication errors.

**Solution:** Set the required API key:

```bash
# For Codex
export OPENAI_API_KEY="sk-..."

# For Gemini
export GOOGLE_API_KEY="..."

# For Copilot
gh auth login

# For Cursor - authenticate through the Cursor app
```

Add these to your `~/.zshrc` or `~/.bashrc` to persist them.

### Copilot CLI requires GitHub authentication

**Problem:** Copilot CLI fails with authentication errors.

**Solution:**
```bash
gh auth login
gh auth status  # Verify you're authenticated
```

---

## Skill/Agent Issues

### Skills not found in Claude Code

**Problem:** `/delegate` or driver agents don't appear in Claude Code.

**Solution:** Re-run the install script:

```bash
cd ~/agent-skills
./install.sh
```

Then restart Claude Code to pick up the new skills.

Verify installation:
```bash
ls ~/.claude/skills/
ls ~/.claude/agents/
```

### Driver agent not delegating properly

**Problem:** The driver agent runs but doesn't execute the CLI tool.

**Solution:** Check that:
1. The CLI tool is installed and in your PATH
2. API keys are set (if required)
3. The router service is running

Try invoking the CLI directly to test:
```bash
codex "Write a hello world function"
```

---

## Performance Issues

### Router is slow

**Problem:** Routing takes several seconds instead of ~1ms.

**Cause:** You may have `USE_NVIDIA_MODEL=1` enabled, which loads a large model.

**Solution:** Use the default rule-based classifier (don't set `USE_NVIDIA_MODEL`):

```bash
# Fast (default)
uvicorn router:app --host 127.0.0.1 --port 8765

# Slow (NVIDIA model - only for testing)
USE_NVIDIA_MODEL=1 uvicorn router:app --host 127.0.0.1 --port 8765
```

### Large output from agents

**Problem:** Agent output is too verbose and uses many tokens.

**Solution:** Use the compress endpoint:

```bash
curl -s -X POST http://127.0.0.1:8765/compress \
  -H "Content-Type: application/json" \
  -d '{"content": "<output>", "level": "aggressive"}' | jq -r '.compressed'
```

Compression levels:
- `minimal` - Light cleanup
- `moderate` - Remove verbosity, keep code
- `aggressive` - Only essential code and errors

---

## Getting Help

1. Check the router health: `curl http://127.0.0.1:8765/health`
2. Test routing directly: `curl -X POST http://127.0.0.1:8765/route -H "Content-Type: application/json" -d '{"prompt": "test"}'`
3. Check CLI tool directly: `codex --help` (or your chosen tool)
4. Review logs from the router service terminal

If issues persist, check that all components are using compatible versions:
- Python 3.9+
- Node.js 18+ (for npm-installed CLIs)
- Claude Code with skills support
