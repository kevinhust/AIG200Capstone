# 🚀 Quick Start Guide

Get up and running with the Antigravity Workspace Template in minutes.

## 📋 Prerequisites

- Python 3.9+
- pip or conda
- Git

## 🏃 Local Development

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run the Agent
```bash
python src/agent.py
```

The agent will start and wait for your commands. It automatically:
- 🧠 Loads memory from `agent_memory.json`
- 🛠️ Discovers tools in `src/tools/`
- 📚 Ingests context from `.context/`

### 3. Example Usage
```bash
# In your terminal or IDE:
> "Build a Python function to calculate Fibonacci numbers"
```

The agent will:
1. 📄 Create a plan in `artifacts/plan_[id].md`
2. 💻 Write code in appropriate directories
3. ✅ Provide evidence logs

## 🐳 Docker Deployment

### Build & Run
```bash
docker-compose up --build
```

This will:
- Install all dependencies
- Start the agent in a containerized environment
- Mount your workspace for live code editing

Access the agent via the exposed interface.

### Customizing Docker
Edit `docker-compose.yml` to:
- Change environment variables
- Mount additional volumes
- Expose different ports

## 🔧 Configuration

### Environment Variables
Create a `.env` file:

```bash
# LLM Configuration
GEMINI_API_KEY=your-api-key-here
GEMINI_MODEL=gemini-2.0-flash

# MCP Configuration
MCP_ENABLED=true

# Custom settings
LOG_LEVEL=INFO
ARTIFACTS_DIR=artifacts
```

### Memory Management
The agent automatically manages memory via `agent_memory.json`. To reset:

```bash
rm agent_memory.json
python src/agent.py
```

## 📁 Project Structure Reference

```
├── src/
│   ├── agent.py         # Main agent loop
│   ├── config.py        # Configuration management
│   ├── memory.py        # Memory engine
│   ├── agents/          # Specialist agents
│   └── tools/           # Tool implementations
├── artifacts/           # Output artifacts
├── .context/            # Knowledge base
└── .antigravity/        # Antigravity rules
```

See [Project Structure](../README.md#project-structure) for details.

## 🧪 Running Tests

```bash
# Run all tests
pytest

# Run specific test
pytest tests/test_agent.py -v

# With coverage
pytest --cov=src tests/
```

## 🐛 Troubleshooting

### Agent doesn't start
```bash
# Check if dependencies are installed
pip list | grep -i google-generativeai

# Verify GEMINI_API_KEY is set
echo $GEMINI_API_KEY
```

### Tools not loading
```bash
# Verify src/tools/ has valid Python files
ls -la src/tools/

# Check for syntax errors
python -m py_compile src/tools/*.py
```

### Memory issues
```bash
# Check memory file
cat agent_memory.json | python -m json.tool

# Clear memory
rm agent_memory.json
```

## 🔌 MCP Integration

To enable MCP servers:

1. Set `MCP_ENABLED=true` in `.env`
2. Configure servers in `mcp_servers.json`
3. Restart the agent

See [MCP Integration Guide](MCP_INTEGRATION.md) for detailed setup.

## 📚 Next Steps

- **Learn Philosophy**: [Project Philosophy](PHILOSOPHY.md)
- **Explore MCP**: [MCP Integration](MCP_INTEGRATION.md)
- **Multi-Agent**: [Swarm Protocol](SWARM_PROTOCOL.md)
- **Advanced**: [Zero-Config Features](ZERO_CONFIG.md)
- **Roadmap**: [Development Roadmap](ROADMAP.md)

---

**Questions?** Check the [Full Index](README.md) or open an issue on GitHub.
