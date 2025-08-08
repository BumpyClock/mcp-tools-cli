# MCP Tools

🔧 Modern CLI tools for managing MCP (Model Context Protocol) server configurations with style and safety.

## Features

- **🎮 Interactive & Command-Line**: Both guided interactive menus AND traditional CLI arguments
- **🚀 Modern CLI**: Beautiful terminal interface with rich output using Typer
- **⌨️ Comprehensive Keyboard Shortcuts**: Full keyboard navigation with context-sensitive shortcuts
- **🔄 Bidirectional Sync**: Push/pull configurations between `mcp-servers.json` and `~/.claude.json`
- **🌐 Platform Management**: Manage MCP servers across Claude Desktop, Claude Code, VSCode, and more
- **➕ Custom Server Management**: Add your own MCP servers manually with interactive configuration
- **🔐 Secrets Management**: Secure API key handling with automatic extraction and loading
- **✅ Validation**: Comprehensive configuration validation using Pydantic models
- **🏥 Health Checks**: Test server accessibility before syncing
- **🪟 Windows Compatible**: Automatic command wrapping for Windows environments
- **🧪 Well Tested**: Comprehensive test suite with pytest
- **📝 Type Safe**: Full type hints and Pydantic validation throughout

## Installation

### Using uv (Recommended)

```bash
# Clone or navigate to the mcp-tools-cli directory
cd mcp-tools-cli

# Install in development mode
uv pip install -e .

# Or install with development dependencies
uv pip install -e ".[dev]"
```

### Using pip

```bash
# Install in development mode
pip install -e .

# Or install with development dependencies  
pip install -e ".[dev]"
```

## Quick Start

Once installed, you'll have access to the `mcp-sync` command with two modes:

### 🎮 Interactive Mode (Recommended for New Users)

```bash
# Launch interactive mode (default when no arguments)
mcp-sync

# Or explicitly launch interactive mode
mcp-sync interactive
```

The interactive mode provides:
- 📊 Real-time configuration status
- 🧭 Guided workflows with confirmations
- 🔐 Interactive API key management
- 📋 Step-by-step options selection
- ✅ Built-in validation and health checks

### ⚡ Command-Line Mode (Great for Automation)

```bash
# Show status of your configurations
mcp-sync status

# Validate both configuration files
mcp-sync validate

# Check health of all servers
mcp-sync health

# Push from mcp-servers.json to ~/.claude.json
mcp-sync push

# Pull from ~/.claude.json to mcp-servers.json  
mcp-sync pull

# Dry run to preview changes
mcp-sync push --dry-run
mcp-sync pull --dry-run
```

## Interactive Mode Features

### 🎯 Main Menu Options

- **🚀 Push configurations**: Interactive wizard for mcp-servers.json → ~/.claude.json
- **⬇️ Pull configurations**: Interactive wizard for ~/.claude.json → mcp-servers.json  
- **✅ Validate configurations**: Check both files for errors
- **🏥 Health check servers**: Test server accessibility with detailed results
- **🔐 Manage API keys**: View status, configure missing keys, load/save secrets
- **🌐 Manage MCP servers**: Add custom servers and sync across platforms
- **📁 Change file paths**: Customize configuration file locations
- **⚙️ Advanced options**: Custom workflows and detailed server information

### 🧭 Interactive Workflows

Each operation includes:
- 📋 **Configuration options**: Choose dry-run, health checks, secrets management
- 🔍 **Preview changes**: See exactly what will be modified before applying
- ✅ **Confirmation prompts**: Never accidentally overwrite configurations  
- 📊 **Real-time status**: Live updates on file existence and server counts
- 🎨 **Rich formatting**: Beautiful tables, progress bars, and status indicators

### 🔐 API Key Management

- **🔍 View status**: See which servers need API key configuration
- **➕ Configure keys**: Step-by-step API key setup (coming soon)
- **📁 Load from secrets**: Import keys from secure secrets repository
- **💾 Save to secrets**: Export keys to secure storage (coming soon)

### 🌐 Platform Management

- **📊 View platform status**: See which Claude platforms are detected and their server counts
- **➕ Add custom servers**: Manually configure your own MCP servers with interactive wizard
- **🔄 Sync servers**: Copy servers between platforms (Claude Desktop ↔ Claude Code ↔ VSCode)
- **❌ Remove servers**: Uninstall servers from selected platforms
- **📋 Installation matrix**: View which servers are installed on which platforms

### 🖥️ TUI Interface

Launch the Text User Interface for visual management:

```bash
# Start the full-featured TUI
mcp-sync tui
```

#### ⌨️ Keyboard Shortcuts

The TUI provides comprehensive keyboard navigation:

**Primary Actions:**
- `A` - Add new server
- `E` - Edit selected server  
- `D` - Deploy server(s)
- `R` - Refresh data
- `H` - Health check
- `Q` - Quit (with confirmation)

**Navigation:**
- `Tab` / `Shift+Tab` - Switch between panes
- `Enter` - Context-sensitive action
- `Escape` - Cancel operation
- `Space` - Toggle server selection

**Context-Sensitive:**
- `Delete` - Remove server (in server pane)
- `U` - Undeploy server (in deployment pane)

📋 All shortcuts are shown in the status bar with context-sensitive help!

For complete details see: [docs/keyboard-shortcuts.md](docs/keyboard-shortcuts.md)

## Command-Line Mode

### `mcp-sync push`

Push MCP server configurations from `mcp-servers.json` to `~/.claude.json`.

```bash
# Basic push
mcp-sync push

# Push with health check
mcp-sync push --health-check

# Push with secrets loading
mcp-sync push --sync-secrets

# Dry run to preview changes
mcp-sync push --dry-run
```

**Options:**
- `--mcp-file, -m`: Path to mcp-servers.json file (default: auto-detect)
- `--claude-file, -c`: Path to ~/.claude.json file (default: ~/.claude.json)
- `--dry-run, -n`: Show what would change without making changes
- `--health-check, -h`: Check server accessibility before syncing
- `--sync-secrets, -s`: Load API keys from secrets repository
- `--verbose, -v`: Enable verbose logging

### `mcp-sync pull`

Pull MCP server configurations from `~/.claude.json` to `mcp-servers.json`.

```bash
# Basic pull
mcp-sync pull

# Pull and extract secrets
mcp-sync pull --sync-secrets

# Pull with health check
mcp-sync pull --health-check --dry-run
```

**Options:**
- Same as push, plus:
- `--sync-secrets, -s`: Extract API keys to secrets repository and replace with placeholders

### `mcp-sync validate`

Validate MCP server configurations in both files.

```bash
mcp-sync validate
```

### `mcp-sync health`

Check health/accessibility of MCP servers.

```bash
mcp-sync health
```

### `mcp-sync status`

Show overview of configuration files and server counts.

```bash
mcp-sync status
```

## Configuration Files

### mcp-servers.json

Your main MCP server configuration file. Example:

```json
{
  "mcpServers": {
    "filesystem": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]
    },
    "brave-search": {
      "type": "stdio", 
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-brave-search"],
      "env": {
        "BRAVE_API_KEY": "YOUR_API_KEY_HERE"
      }
    },
    "web-api": {
      "type": "http",
      "url": "https://api.example.com/mcp"
    }
  }
}
```

### ~/.claude.json

Claude's configuration file where MCP servers are loaded from.

## Secrets Management

MCP Tools provides secure API key management:

### Automatic Secrets Loading

```bash
# Load API keys from secrets repository during push
mcp-sync push --sync-secrets
```

### Secrets Extraction

```bash
# Extract API keys from Claude config and store securely
mcp-sync pull --sync-secrets
```

### Secrets Storage

API keys are stored in `secrets/api-keys/mcp-env.json`:

```json
{
  "_comment": "API keys for MCP servers",
  "brave-search": {
    "BRAVE_API_KEY": "actual-api-key-here"
  },
  "openai-server": {
    "OPENAI_API_KEY": "sk-...",
    "OPENAI_ORG_ID": "org-..."
  }
}
```

## Supported Server Types

- **stdio**: Standard input/output servers (npx, uvx, python, etc.)
- **http**: HTTP-based servers
- **sse**: Server-Sent Events servers  
- **docker**: Docker container servers

## Supported Platforms

MCP Tools can manage servers across multiple Claude installations:

- **🖥️ Claude Desktop**: Anthropic's official desktop application
- **⚡ Claude Code**: Claude CLI tool for development
- **📝 VSCode Claude**: Claude extension for Visual Studio Code
- **🔄 Continue.dev**: Continue.dev VS Code extension (if using MCP)

The tool automatically detects available platforms and their configuration file locations.

## Windows Compatibility

MCP Tools automatically handles Windows compatibility:

- Commands like `npx` and `uvx` are wrapped with `cmd /c` on Windows
- Unwrapped automatically when pulling for cross-platform compatibility
- No manual configuration needed

## Development

### Setup Development Environment

```bash
# Clone the repository
git clone <repository-url>
cd mcp-tools-cli

# Install with development dependencies
uv pip install -e ".[dev]"

# Install pre-commit hooks (optional)
pre-commit install
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=mcp_tools --cov-report=html

# Run specific test file
pytest tests/test_cli.py

# Run with verbose output
pytest -v
```

### Code Quality

```bash
# Format code
black src tests

# Sort imports
isort src tests

# Type checking
mypy src/mcp_tools

# Lint code
ruff src tests
```

## Project Structure

```
mcp-tools-cli/
├── pyproject.toml          # Project configuration
├── README.md              # This file
├── src/
│   └── mcp_tools/         # Main package
│       ├── __init__.py    # Package info
│       ├── cli.py         # CLI interface (Typer)
│       ├── config.py      # Pydantic models
│       ├── sync.py        # Core sync logic
│       ├── validators.py  # Validation functions
│       ├── secrets.py     # API key management
│       ├── platforms.py   # Platform management
│       ├── interactive.py # Interactive TUI
│       └── utils.py       # Utility functions
├── tests/                 # Test suite
│   ├── test_cli.py
│   ├── test_config.py
│   └── test_utils.py
└── docs/                  # Documentation
```

## Migration from Original Script

If you're migrating from the original `sync-mcp-config.py` script:

1. **Same functionality**: All original features are preserved
2. **Better UX**: Rich terminal output with colors and progress indicators
3. **New commands**: Additional `validate`, `health`, and `status` commands
4. **Same arguments**: Most command-line arguments are the same
5. **Enhanced secrets**: Better API key management and security

### Command Mapping

| Original | New MCP Tools |
|----------|---------------|
| `python sync-mcp-config.py` | `mcp-sync push` |
| `python sync-mcp-config.py pull` | `mcp-sync pull` |
| `python sync-mcp-config.py --dry-run` | `mcp-sync push --dry-run` |
| `python sync-mcp-config.py --health-check` | `mcp-sync push --health-check` |

## Troubleshooting

### Common Issues

1. **Command not found**: Ensure you've installed with `uv pip install -e .`
2. **Permission errors**: Check file permissions on config files
3. **API key issues**: Use `--sync-secrets` for automatic key management
4. **Windows compatibility**: The tool handles this automatically

### Debug Mode

```bash
# Enable verbose logging
mcp-sync push --verbose

# Check status first
mcp-sync status
```

### Getting Help

```bash
# General help
mcp-sync --help

# Command-specific help
mcp-sync push --help
mcp-sync pull --help
```

## License

MIT License - see the original dotfiles repository for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for your changes
4. Run the test suite
5. Submit a pull request

## Changelog

### v0.1.0
- Initial release
- Modern CLI with Typer and Rich
- Full feature parity with original script
- Comprehensive test suite
- Type safety with Pydantic
- Enhanced secrets management