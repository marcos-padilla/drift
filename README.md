# Drift

**Drift** is a professional, scalable AI code assistant framework designed for developers who want a powerful, extensible CLI tool for code assistance. Built with modern Python practices, type safety, and comprehensive documentation, Drift provides a robust foundation for AI-powered development workflows.

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Local Models (Ollama)](#local-models-ollama)
- [Usage](#usage)
- [Architecture](#architecture)
- [Adding Tools](#adding-tools)
- [Safety & Approval System](#safety--approval-system)
- [Context Management](#context-management)
- [Hooks System](#hooks-system)
- [MCP Integration](#mcp-integration)
- [Session Persistence](#session-persistence)
- [Examples](#examples)
- [Development](#development)
- [Contributing](#contributing)
- [License](#license)

## Features

### Core Capabilities

- **🤖 AI-Powered Code Assistance**: Interact with OpenAI models (GPT-4o, GPT-4, etc.) or local models via Ollama for code generation, debugging, and refactoring
- **🏠 Local Model Support**: Use Ollama for private, offline AI assistance with no API costs
- **🛠️ Rich Tool Ecosystem**: Built-in tools for file operations, shell commands, web search, and more
- **🔌 MCP Integration**: Connect to Model Context Protocol servers for extended capabilities
- **🔒 Safety & Approval**: Configurable approval policies for potentially dangerous operations
- **💾 Session Management**: Save, resume, and checkpoint conversation sessions
- **🎨 Beautiful TUI**: Minimal, clean dark-themed interface with syntax highlighting
- **📝 Context Management**: Intelligent conversation history with compression and loop detection
- **🔧 Hooks System**: Execute scripts/commands at various trigger points
- **📊 Token Tracking**: Monitor token usage and manage context windows
- **🔄 Retry Logic**: Automatic retry with exponential backoff for API calls

### Built-in Tools

#### File Operations
- **Read/Write**: `read_file`, `write_file`, `edit_file`
- **File Management**: `copy_file`, `move_file`, `delete_file`, `create_directory`
- **Directory Operations**: `list_dir`, `glob`

#### Code Analysis
- **Search**: `grep` (text search)
- **Code Analysis**: `find_imports`, `find_definitions`, `find_usages`, `code_metrics`

#### Git Operations
- **Status & History**: `git_status`, `git_diff`, `git_log`
- **Commits & Branches**: `git_commit`, `git_branch`, `git_stash`

#### Code Quality
- **Formatting**: `format_code` (black, prettier, etc.)
- **Linting**: `lint_code` (ruff, flake8, eslint, etc.)
- **Type Checking**: `type_check` (mypy, tsc, etc.)

#### Testing & Dependencies
- **Testing**: `run_tests` (pytest, unittest, jest, mocha)
- **Dependencies**: `list_dependencies`, `check_updates`

#### Other Operations
- **Shell Execution**: `shell` (with safety checks)
- **Web Operations**: `web_search`, `web_fetch`
- **Task Management**: `todos`
- **Memory**: `memory` (key-value storage)

## Installation

### Prerequisites

- Python 3.12 or higher
- OpenAI API key

### Install from Source

1. Clone the repository:
```bash
git clone <repository-url>
cd drift
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

Or install as an editable package:
```bash
pip install -e .
```

### Environment Setup

Create a `.env` file in the project root:

```bash
# For OpenAI (required)
API_KEY=your_openai_api_key_here

# For Ollama (optional - provider auto-sets base_url)
# DRIFT_PROVIDER=ollama
# BASE_URL=http://localhost:11434/v1
```

**Note**: For Ollama, you don't need an API key. Just set `DRIFT_PROVIDER=ollama` or use the `/provider` command.

## Quick Start

### Interactive Mode

Run Drift in interactive mode:

```bash
python main.py
```

You'll see a welcome message and can start chatting with Drift:

```
Drift
model: gpt-4o
cwd: /path/to/project
commands: /help /config /approval /model /exit

user> Fix the bug in main.py
```

### Single Command Mode

Run a single command:

```bash
python main.py "Add error handling to the login function"
```

### Specify Working Directory

```bash
python main.py --cwd /path/to/project
```

## Configuration

Drift uses a hierarchical configuration system that loads settings from multiple sources:

1. **Default values** (built-in)
2. **Configuration file** (`drift.toml` or `pyproject.toml`)
3. **Environment variables**
4. **Command-line arguments**

### Configuration File

Create a `drift.toml` file in your project root or home directory:

```toml
[api]
provider = "openai"  # or "ollama"
base_url = "https://api.openai.com/v1"  # Auto-set based on provider

[model]
name = "gpt-4o"
temperature = 1.0
context_window = 256000

[approval]
policy = "auto-edit"  # Options: on-request, on-failure, auto, auto-edit, never, yolo

[shell_environment]
ignore_default_excludes = false
exclude_patterns = ["*KEY*", "*TOKEN*", "*SECRET*", "*PASSWORD*"]
set_vars = { DEBUG = "true" }

[context]
max_messages = 100
enable_compression = true
compression_threshold = 0.8

[hooks]
enabled = true

[[hooks.hooks]]
name = "pre-test"
trigger = "before_tool"
command = "python3 tests.py"
timeout_sec = 30.0
enabled = true

[[mcp.servers]]
name = "filesystem"
command = "npx"
args = ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/allowed/dir"]
env = { FILESYSTEM_ALLOWED_DIRS = "/path/to/allowed/dir" }
```

### Configuration Options

#### Model Configuration

- `model.name`: Model identifier (default: `"gpt-4o"` for OpenAI, varies for Ollama)
- `model.temperature`: Sampling temperature 0.0-2.0 (default: `1.0`)
- `model.context_window`: Maximum context window in tokens (default: `256000`)

#### API Configuration

- `api.provider`: LLM provider - `"openai"` or `"ollama"` (default: `"openai"`)
- `api.base_url`: API base URL (auto-set based on provider if not specified)
  - OpenAI: `https://api.openai.com/v1`
  - Ollama: `http://localhost:11434/v1`
- `api.key`: API key (required for OpenAI, optional for Ollama)

#### Approval Policy

- `on-request`: Always request approval for mutating operations
- `on-failure`: Request approval only after failures
- `auto`: Automatically approve safe operations
- `auto-edit`: Automatically approve file edits, request approval for other operations
- `never`: Never request approval (not recommended)
- `yolo`: Approve everything automatically (dangerous)

#### Shell Environment

- `shell_environment.ignore_default_excludes`: Ignore default exclusion patterns
- `shell_environment.exclude_patterns`: Patterns to exclude from environment
- `shell_environment.set_vars`: Environment variables to set explicitly

#### Context Management

- `context.max_messages`: Maximum messages to keep in history
- `context.enable_compression`: Enable automatic context compression
- `context.compression_threshold`: Token usage threshold for compression (0.0-1.0)

#### API Configuration

- `api.provider`: LLM provider (`"openai"` or `"ollama"`)
- `api.base_url`: API base URL (auto-set based on provider)
- `api.key`: API key (required for OpenAI, optional for Ollama)

## Local Models (Ollama)

Drift supports local AI models through Ollama, allowing you to run AI code assistance completely offline and privately.

### Quick Setup

1. **Install Ollama**: Download from [ollama.com](https://ollama.com)

2. **Download a Code Model**:
   ```bash
   ollama pull codellama:13b
   # Or for your specific model:
   ollama pull gpt-oss:20b
   ```

3. **Configure Drift**:

   **Option A: Configuration File** (`drift.toml`):
   ```toml
   [api]
   provider = "ollama"
   # base_url is auto-set to http://localhost:11434/v1

   [model]
   name = "gpt-oss:20b"
   temperature = 0.7
   ```

   **Option B: Command Line**:
   ```bash
   # In Drift interactive mode
   → /provider ollama
   → /models
   → /model gpt-oss:20b
   ```

### Using Ollama Commands

**Switch to Ollama**:
```
→ /provider ollama
✓ Provider switched to Ollama
✓ Base URL set to: http://localhost:11434/v1
```

**List Available Models**:
```
→ /models
Available Ollama Models:
  • gpt-oss:20b (13 GB)
  • codellama:13b (7.3 GB)
  • qwen2.5-coder:32b (18 GB)
```

**Select a Model**:
```
→ /model gpt-oss:20b
✓ Model changed to: gpt-oss:20b
```

**Check Configuration**:
```
→ /config
Current Configuration:
  Provider: Ollama
  Base URL: http://localhost:11434/v1
  Model: gpt-oss:20b
  ...
```

### Recommended Models for Code

- **gpt-oss:20b** - Your current model, good balance
- **codellama:13b** - Excellent for code generation
- **qwen2.5-coder:32b** - Best quality (requires more RAM)
- **codellama:7b** - Faster, good for simple tasks

### Troubleshooting Ollama

**"Connection refused"**:
- Make sure Ollama is running: `ollama list` should work
- Check if Ollama is on the default port (11434)

**"Model not found"**:
- Verify the model is installed: `ollama list`
- Use the exact model name from `ollama list`

**Slow responses**:
- Use a smaller model (7B instead of 13B+)
- Enable GPU acceleration in Ollama
- Close other applications to free up resources

### Benefits of Local Models

- ✅ **Privacy**: Your code never leaves your computer
- ✅ **Cost**: No API costs
- ✅ **Offline**: Works without internet
- ✅ **Speed**: No network latency (depending on hardware)
- ✅ **Control**: Full control over model behavior

## Usage

### Interactive Commands

Drift supports various slash commands in interactive mode:

- `/help` - Show help message
- `/exit` or `/quit` - Exit Drift
- `/clear` - Clear conversation history
- `/config` - Show current configuration
- `/provider [ollama|openai]` - Show or change LLM provider
- `/models` - List available models (Ollama only)
- `/model <name>` - Change the model
- `/approval <mode>` - Change approval policy
- `/stats` - Show session statistics
- `/tools` - List available tools
- `/mcp` - Show MCP server status
- `/save` - Save current session
- `/checkpoint` - Create a checkpoint
- `/restore <checkpoint_id>` - Restore a checkpoint
- `/sessions` - List saved sessions
- `/resume <session_id>` - Resume a saved session

### Examples

#### File Operations

```
user> Read the main.py file
Drift> [Reads and displays the file with syntax highlighting]

user> Edit main.py to add error handling
Drift> [Shows diff and requests approval if needed]
```

#### Code Search

```
user> Search for all functions that use the database connection
Drift> [Uses grep tool to find matches]
```

#### Shell Commands

```
user> Run the tests
Drift> [Executes test command with safety checks]
```

#### Web Search

```
user> Search for Python async best practices
Drift> [Searches web and summarizes results]
```

## Architecture

Drift follows a modular, scalable architecture:

```
drift/
├── core/
│   ├── agent/          # Agent execution and session management
│   ├── config/         # Configuration loading and validation
│   ├── context/        # Conversation history and context management
│   ├── hooks/          # Hook system for script execution
│   ├── llm/            # LLM client and retry logic
│   ├── prompts/        # System prompt building
│   ├── safety/         # Approval and safety policies
│   ├── tools/          # Tool system
│   │   ├── builtin/    # Built-in tools
│   │   ├── mcp/        # MCP integration
│   │   ├── registration/# Tool registration
│   │   └── subagents/  # Subagent tools
│   ├── ui/             # Text user interface
│   └── utils/          # Utility functions
└── main.py             # Entry point
```

### Key Components

- **Agent**: Orchestrates tool execution and LLM interactions
- **Session**: Manages conversation state and tool registry
- **Context Manager**: Handles message history and compression
- **Tool Registry**: Central registry for all available tools
- **Safety System**: Manages approval workflows
- **TUI**: Rich console interface for user interaction

## Adding Tools

Drift makes it easy to add custom tools. There are three ways to add tools:

### 1. Built-in Tool (Recommended)

Create a new file in `core/tools/builtin/`:

```python
"""
Custom tool for your specific use case.
"""

from pathlib import Path
from pydantic import BaseModel, Field

from core.tools.base import Tool
from core.tools.models import ToolInvocation, ToolKind, ToolResult
from core.tools.registration.decorator import register_tool


class MyToolParams(BaseModel):
    """Parameters for my custom tool."""
    
    input: str = Field(..., description="Input parameter")
    option: bool = Field(default=False, description="Optional flag")


@register_tool(name="my_tool", description="Does something useful")
class MyTool(Tool):
    """Custom tool implementation."""
    
    name: str = "my_tool"
    description: str = "Does something useful"
    kind: ToolKind = ToolKind.READ  # or WRITE, SHELL, NETWORK, etc.
    schema: type[MyToolParams] = MyToolParams
    
    async def execute(
        self,
        invocation: ToolInvocation[MyToolParams],
    ) -> ToolResult:
        """Execute the tool."""
        params = invocation.params
        
        # Your tool logic here
        result = f"Processed: {params.input}"
        
        return ToolResult.success(
            output=result,
            metadata={"processed": True},
        )
    
    def is_mutating(self, params: MyToolParams) -> bool:
        """Whether this tool modifies system state."""
        return False  # Set to True if tool modifies files/system
```

The tool will be automatically discovered and registered when the module is imported.

### 2. Using the Decorator

Use the `@register_tool` decorator for automatic registration:

```python
from core.tools.registration.decorator import register_tool

@register_tool(name="custom_tool", description="My custom tool")
class CustomTool(Tool):
    # ... implementation
```

### 3. Manual Registration

Register tools manually in your code:

```python
from core.tools.registry import ToolRegistry

tool_registry = ToolRegistry(config)
tool_registry.register(MyTool(config))
```

### Tool Kinds

Tools are categorized by kind:

- `READ`: Read-only operations (read_file, list_dir)
- `WRITE`: File modification operations (write_file, edit_file)
- `SHELL`: Shell command execution
- `NETWORK`: Network operations (web_search, web_fetch)
- `MEMORY`: Memory operations
- `MCP`: MCP server tools

### Tool Parameters

Use Pydantic models for parameter validation:

```python
from pydantic import BaseModel, Field

class MyParams(BaseModel):
    required_param: str = Field(..., description="Required parameter")
    optional_param: int = Field(default=10, description="Optional with default")
    validated_param: str = Field(..., pattern=r"^[a-z]+$", description="Validated parameter")
```

### Tool Results

Return structured results:

```python
# Success
return ToolResult.success(
    output="Operation completed",
    metadata={"key": "value"},
    diff="--- a/file.py\n+++ b/file.py\n..."  # For file changes
)

# Error
return ToolResult.error_result("Error message")

# With truncation
return ToolResult.success(
    output=large_output,
    truncated=True,  # Indicates output was truncated
)
```

### Tool Confirmation

Request user confirmation for dangerous operations:

```python
async def get_confirmation(
    self,
    invocation: ToolInvocation[MyToolParams],
) -> ToolConfirmation | None:
    """Request confirmation if needed."""
    if invocation.params.dangerous_operation:
        return ToolConfirmation(
            tool_name=self.name,
            params=invocation.params.model_dump(),
            description="This operation will delete important files",
            affected_paths=[Path("important.txt")],
            is_dangerous=True,
        )
    return None
```

## Safety & Approval System

Drift includes a comprehensive safety system to protect against dangerous operations.

### Approval Policies

Configure approval behavior in `drift.toml`:

```toml
[approval]
policy = "auto-edit"  # See Configuration section for options
```

### Dangerous Command Detection

The system automatically detects dangerous shell commands:

- File deletion (`rm -rf`, `del /f`)
- System modifications (`sudo`, `chmod 777`)
- Network operations (`curl | sh`, `wget | bash`)
- And more patterns...

### Custom Approval Logic

Tools can implement custom approval logic:

```python
def is_mutating(self, params: MyToolParams) -> bool:
    """Whether this tool modifies system state."""
    return True  # Will trigger approval checks

async def get_confirmation(
    self,
    invocation: ToolInvocation[MyToolParams],
) -> ToolConfirmation | None:
    """Request confirmation for specific operations."""
    if params.destructive:
        return ToolConfirmation(
            tool_name=self.name,
            params=params.model_dump(),
            description="This is a destructive operation",
            is_dangerous=True,
        )
    return None
```

## Context Management

Drift intelligently manages conversation context to stay within token limits.

### Automatic Compression

When context approaches the limit, Drift automatically compresses old messages:

```toml
[context]
enable_compression = true
compression_threshold = 0.8  # Compress when 80% of context used
```

### Loop Detection

Drift detects repetitive agent behaviors and warns you:

```
⚠️  Loop detected: Agent is repeating similar actions
```

### Message Pruning

Old messages are automatically pruned when limits are exceeded:

```toml
[context]
max_messages = 100  # Maximum messages to keep
```

### Manual Context Management

Clear context manually:

```
user> /clear
```

## Hooks System

Execute scripts or commands at various trigger points in the agent lifecycle.

### Hook Triggers

- `before_agent`: Before agent starts processing
- `after_agent`: After agent completes
- `before_tool`: Before tool execution
- `after_tool`: After tool execution
- `on_error`: On error occurrence

### Configuration

```toml
[hooks]
enabled = true

[[hooks.hooks]]
name = "pre-test"
trigger = "before_tool"
command = "python3 tests.py"
timeout_sec = 30.0
enabled = true

[[hooks.hooks]]
name = "post-commit"
trigger = "after_tool"
script = "./scripts/post-commit.sh"
timeout_sec = 60.0
enabled = true
```

### Hook Environment

Hooks receive environment variables:

- `DRIFT_TOOL_NAME`: Name of the tool (for tool hooks)
- `DRIFT_TOOL_PARAMS`: JSON string of tool parameters
- `DRIFT_SESSION_ID`: Current session ID
- `DRIFT_CWD`: Current working directory
- And more...

## MCP Integration

Connect to Model Context Protocol (MCP) servers for extended capabilities.

### Configuration

```toml
[[mcp.servers]]
name = "filesystem"
command = "npx"
args = ["-y", "@modelcontextprotocol/server-filesystem", "/allowed/dir"]
env = { FILESYSTEM_ALLOWED_DIRS = "/allowed/dir" }

[[mcp.servers]]
name = "github"
url = "https://mcp-server.example.com/sse"
headers = { Authorization = "Bearer token" }
```

### MCP Server Types

#### stdio Transport

For local MCP servers:

```toml
[[mcp.servers]]
name = "local-server"
command = "python"
args = ["-m", "my_mcp_server"]
env = { API_KEY = "secret" }
```

#### HTTP/SSE Transport

For remote MCP servers:

```toml
[[mcp.servers]]
name = "remote-server"
url = "https://mcp.example.com/sse"
headers = { Authorization = "Bearer token" }
```

### Using MCP Tools

MCP tools are automatically discovered and available:

```
user> /tools
Available tools (15)
  • read_file
  • write_file
  • mcp_filesystem_read
  • mcp_filesystem_write
  • ...
```

## Session Persistence

Save and resume conversation sessions.

### Save Session

```
user> /save
Session saved: session_abc123
```

### List Sessions

```
user> /sessions
Saved Sessions
  • session_abc123 (turns: 5, updated: 2024-01-15 10:30:00)
  • session_def456 (turns: 12, updated: 2024-01-14 15:20:00)
```

### Resume Session

```
user> /resume session_abc123
Resumed session: session_abc123
```

### Checkpoints

Create checkpoints for important states:

```
user> /checkpoint
Checkpoint created: checkpoint_xyz789
```

Restore from checkpoint:

```
user> /restore checkpoint_xyz789
Resumed session: session_abc123, checkpoint: checkpoint_xyz789
```

## Examples

### Example 1: Code Refactoring

```
user> Refactor the authentication module to use async/await
Drift> [Reads auth module, analyzes code, shows proposed changes]
     [Requests approval, applies changes]
```

### Example 2: Bug Fixing

```
user> Fix the memory leak in the data processing function
Drift> [Searches for the function, identifies issue, applies fix]
```

### Example 3: Adding Features

```
user> Add a rate limiter to the API endpoints
Drift> [Reads API code, implements rate limiter, adds tests]
```

### Example 4: Documentation

```
user> Generate comprehensive docstrings for all functions in utils.py
Drift> [Reads file, generates docstrings, updates file]
```

## Development

### Project Structure

```
drift/
├── core/                    # Core framework
│   ├── agent/               # Agent and session management
│   ├── config/              # Configuration system
│   ├── context/             # Context management
│   ├── hooks/               # Hook system
│   ├── llm/                 # LLM client
│   ├── prompts/             # Prompt building
│   ├── safety/              # Safety system
│   ├── tools/               # Tool system
│   ├── ui/                  # User interface
│   └── utils/               # Utilities
├── main.py                  # Entry point
├── pyproject.toml            # Project configuration
├── requirements.txt         # Dependencies
└── README.md                # This file
```

### Code Style

- **Type Hints**: All functions must have complete type hints
- **Documentation**: NumPy-style docstrings for all public APIs
- **Formatting**: Black (100 char line length)
- **Linting**: Ruff with strict rules
- **Type Checking**: mypy with strict mode

### Running Tests

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run with coverage
pytest --cov=core --cov-report=html

# Type checking
mypy core/

# Linting
ruff check core/
```

### Development Setup

1. Clone the repository
2. Install in editable mode: `pip install -e ".[dev]"`
3. Set up pre-commit hooks (if configured)
4. Create a `.env` file with your API key
5. Run tests: `pytest`

### Adding New Features

1. Create feature branch
2. Implement with tests
3. Update documentation
4. Ensure type checking passes
5. Submit pull request

## Contributing

Contributions are welcome! Please follow these guidelines:

1. **Code Quality**: Maintain high code quality with type hints and documentation
2. **Tests**: Add tests for new features
3. **Documentation**: Update README and docstrings
4. **Style**: Follow existing code style (Black, Ruff, mypy)
5. **Atomic Commits**: Keep commits focused and atomic

### Contribution Areas

- New tools
- UI improvements
- Performance optimizations
- Documentation
- Bug fixes
- Test coverage

## License

MIT License - see LICENSE file for details.

## Support

For issues, questions, or contributions:

- Open an issue on GitHub
- Check existing documentation
- Review code examples

---

**Drift** - Professional AI Code Assistant Framework

Built with ❤️ using modern Python practices.
