# MCP Server Quickstart

Set up glintefy as an MCP server for Claude Desktop in 5 minutes.

## What is MCP?

MCP (Model Context Protocol) allows Claude Desktop to interact with external tools. With glintefy as an MCP server, you can ask Claude to review your code directly.

## Installation

```bash
# Install the package
pip install glintefy

# Or with uv
uv pip install glintefy
```

## Configure Claude Desktop

### Step 1: Find Config File

| OS | Location |
|----|----------|
| macOS | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Linux | `~/.config/claude/claude_desktop_config.json` |
| Windows | `%APPDATA%\Claude\claude_desktop_config.json` |

### Step 2: Add Server Configuration

Edit the config file:

```json
{
  "mcpServers": {
    "glintefy-review": {
      "command": "python",
      "args": ["-m", "glintefy.servers.review"],
      "cwd": "/path/to/your/project"
    }
  }
}
```

**Important:** Set `cwd` to your project directory.

### Step 3: Restart Claude Desktop

Close and reopen Claude Desktop to load the new server.

## Usage

Once configured, you can ask Claude:

> "Review the code quality of this project"

> "Check this project for security vulnerabilities"

> "Find functions that would benefit from caching"

> "Analyze the documentation coverage"

## Available MCP Tools

| Tool | Description |
|------|-------------|
| `review_all` | Run all analyses |
| `review_scope` | Discover files to analyze |
| `review_quality` | Code quality analysis |
| `review_security` | Security vulnerability scan |
| `review_deps` | Dependency analysis |
| `review_docs` | Documentation coverage |
| `review_perf` | Performance analysis |
| `review_cache` | Cache optimization |

## Example Conversation

**You:** Review the code quality of this project

**Claude:** I'll run a comprehensive code quality analysis using the glintefy-review server.

*[Uses review_all tool]*

Here's what I found:
- 3 functions with high complexity (>10)
- 2 functions exceeding 50 lines
- 5 potential security issues
- Documentation coverage: 72%

Would you like me to help fix any of these issues?

## Troubleshooting

### Server Not Found

Check that:
1. Package is installed: `pip show glintefy`
2. Python path is correct in config
3. Claude Desktop was restarted

### Permission Errors

Ensure `cwd` in config points to a directory you have access to.

### View Server Logs

Check Claude Desktop logs for MCP server errors:
- macOS: `~/Library/Logs/Claude/`
- Linux: `~/.local/share/claude/logs/`

## Next Steps

- [MCP Tools Reference](TOOLS.md) - All MCP tools and options
- [Configuration](../reference/CONFIGURATION.md) - Customize thresholds
- [CLI Quickstart](../cli/QUICKSTART.md) - Use CLI directly
