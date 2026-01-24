#!/bin/bash
# Install agent-skills globally for Claude Code

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CLAUDE_DIR="$HOME/.claude"

echo "Installing agent-skills for Claude Code..."

# Create .claude directories if they don't exist
mkdir -p "$CLAUDE_DIR/skills"
mkdir -p "$CLAUDE_DIR/agents"

# Copy skills
echo "Installing skills..."
cp -r "$SCRIPT_DIR/.claude/skills/"* "$CLAUDE_DIR/skills/"

# Copy agents
echo "Installing agents..."
cp -r "$SCRIPT_DIR/.claude/agents/"* "$CLAUDE_DIR/agents/"

# Setup router service
echo ""
echo "Setting up router service..."
cd "$SCRIPT_DIR/router-service"

if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

echo "Installing Python dependencies..."
source .venv/bin/activate
pip install -q -r requirements.txt
deactivate

echo ""
echo "✓ Installation complete!"
echo ""
echo "Installed skills:"
ls -1 "$CLAUDE_DIR/skills/"
echo ""
echo "Installed agents:"
ls -1 "$CLAUDE_DIR/agents/"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "NEXT STEPS:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "1. Install at least one AI CLI tool:"
echo "   npm install -g @openai/codex          # OpenAI Codex"
echo "   npm install -g @githubnext/github-copilot-cli  # GitHub Copilot"
echo "   npm install -g @google/generative-ai  # Gemini CLI"
echo "   # Or install Cursor from https://cursor.com"
echo ""
echo "2. Start the router service:"
echo "   cd $SCRIPT_DIR/router-service"
echo "   source .venv/bin/activate"
echo "   uvicorn router:app --host 127.0.0.1 --port 8765"
echo ""
echo "3. (Optional) Add to ~/.zshrc or ~/.bashrc for easy startup:"
echo "   alias start-router='cd $SCRIPT_DIR/router-service && source .venv/bin/activate && uvicorn router:app --host 127.0.0.1 --port 8765 &'"
echo ""
echo "4. Use in any Claude Code session:"
echo "   /delegate Fix the authentication bug"
echo "   /delegate Write a function to parse JSON"
echo ""
echo "For troubleshooting, see: $SCRIPT_DIR/TROUBLESHOOTING.md"
echo ""
