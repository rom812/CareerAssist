"""
MCP server configurations for the CareerAssist Researcher
"""
from agents.mcp import MCPServerStdio
import os


def create_playwright_mcp_server(timeout_seconds=60):
    """Create a Playwright MCP server instance for web browsing.
    
    Args:
        timeout_seconds: Client session timeout in seconds (default: 60)
        
    Returns:
        MCPServerStdio instance configured for Playwright
    """
    # Base arguments - removed --executable-path as it's not a valid MCP server flag
    args = [
        "-y",
        "@playwright/mcp@latest",
        "--headless",
        "--isolated", 
        "--no-sandbox",
        "--ignore-https-errors",
        "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"
    ]
    
    # Remove manual executable path finding - let Playwright discover it naturally
    # since we installed it with 'playwright install' in the Dockerfile
    
    params = {
        "command": "npx",
        "args": args,
        "env": os.environ  # Pass environment variables to the MCP server process
    }
    
    return MCPServerStdio(params=params, client_session_timeout_seconds=timeout_seconds)