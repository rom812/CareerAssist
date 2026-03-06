"""
CareerAssist Researcher Service - Career Research Agent
"""

import logging
import os
from datetime import UTC, datetime

from agents import Agent, Runner, trace
from agents.extensions.models.litellm_model import LitellmModel
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Security
from fastapi.security import APIKeyHeader
from pydantic import BaseModel

# Suppress LiteLLM warnings about optional dependencies
logging.getLogger("LiteLLM").setLevel(logging.CRITICAL)

# Import from our modules
from context import DEFAULT_RESEARCH_PROMPT, get_agent_instructions
from mcp_servers import create_playwright_mcp_server
from tools import ingest_career_document, store_discovered_job, store_research_finding

# Load environment
load_dotenv(override=True)

logger = logging.getLogger(__name__)

app = FastAPI(title="Career Researcher Service")

# API Key authentication
RESEARCHER_API_KEY = os.getenv("RESEARCHER_API_KEY", "")
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(api_key: str = Security(api_key_header)) -> str:
    """Verify the API key for protected endpoints."""
    if not RESEARCHER_API_KEY:
        # If no key is configured, allow access (local dev mode)
        return "dev"
    if not api_key or api_key != RESEARCHER_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid or missing API key")
    return api_key


# Request model
class ResearchRequest(BaseModel):
    topic: str | None = None  # Optional - if not provided, agent picks a topic


async def run_research_agent(topic: str = None) -> str:
    """Run the research agent to generate career advice and insights."""

    # Prepare the user query
    if topic:
        query = f"Research this career topic: {topic}"
    else:
        query = DEFAULT_RESEARCH_PROMPT

    # Please override these variables with the region you are using
    # Other choices: us-west-2 (for OpenAI OSS models) and eu-central-1
    REGION = "us-east-1"  # Changed from us-west-2 for Nova Pro
    os.environ["AWS_REGION_NAME"] = REGION  # LiteLLM's preferred variable
    os.environ["AWS_REGION"] = REGION  # Boto3 standard
    os.environ["AWS_DEFAULT_REGION"] = REGION  # Fallback

    # Please override this variable with the model you are using
    # Common choices: bedrock/eu.amazon.nova-pro-v1:0 for EU and bedrock/us.amazon.nova-pro-v1:0 for US
    # or bedrock/amazon.nova-pro-v1:0 if you are not using inference profiles
    # bedrock/openai.gpt-oss-120b-1:0 for OpenAI OSS models
    # bedrock/converse/us.anthropic.claude-sonnet-4-20250514-v1:0 for Claude Sonnet 4
    # NOTE that nova-pro is needed to support tools and MCP servers; nova-lite is not enough - thank you Yuelin L.!
    MODEL = "bedrock/us.amazon.nova-pro-v1:0"  # Changed from OSS model to Nova Pro
    model = LitellmModel(model=MODEL)

    # Create and run the agent with MCP server
    with trace("Researcher"):
        async with create_playwright_mcp_server(timeout_seconds=180) as playwright_mcp:
            agent = Agent(
                name="Career Researcher",
                instructions=get_agent_instructions(),
                model=model,
                tools=[store_research_finding, store_discovered_job, ingest_career_document],
                mcp_servers=[playwright_mcp],
            )

            result = await Runner.run(agent, input=query, max_turns=25)

    return result.final_output


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "service": "Career Researcher",
        "status": "healthy",
        "timestamp": datetime.now(UTC).isoformat(),
    }


@app.post("/research")
async def research(request: ResearchRequest, _: str = Depends(verify_api_key)) -> str:
    """
    Generate career research and advice.

    The agent will:
    1. Browse career websites for current job market insights
    2. Analyze the information found
    3. Store the analysis in the knowledge base

    If no topic is provided, the agent will pick a trending career topic.
    """
    import asyncio

    max_retries = 3
    last_error = None
    for attempt in range(max_retries):
        try:
            response = await run_research_agent(request.topic)
            return response
        except Exception as e:
            last_error = e
            error_msg = str(e)
            logger.error(f"Error in research endpoint (attempt {attempt + 1}/{max_retries}): {error_msg}")
            # Retry on Bedrock ToolUse errors (intermittent model issue)
            if "ToolUse" in error_msg or "invalid sequence" in error_msg:
                if attempt < max_retries - 1:
                    wait_time = 2**attempt
                    logger.info(f"Retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                    continue
            # Non-retryable error
            logger.error(f"Research failed: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Research request failed. Please try again later.")

    # All retries exhausted
    logger.error(f"Research failed after {max_retries} retries: {last_error}", exc_info=True)
    raise HTTPException(status_code=500, detail="Research request failed after multiple retries.")


@app.get("/research/auto")
async def research_auto(_: str = Depends(verify_api_key)):
    """
    Automated research endpoint for scheduled runs.
    Picks a trending topic automatically and generates research.
    Used by EventBridge Scheduler for periodic research updates.
    """
    import asyncio

    try:
        # Always use agent's choice for automated runs, with retry
        response = None
        for attempt in range(3):
            try:
                response = await run_research_agent(topic=None)
                break
            except Exception as e:
                if "ToolUse" in str(e) and attempt < 2:
                    await asyncio.sleep(2**attempt)
                    continue
                raise
        if response is None:
            raise Exception("All retries exhausted")
        return {
            "status": "success",
            "timestamp": datetime.now(UTC).isoformat(),
            "message": "Automated research completed",
            "preview": response[:200] + "..." if len(response) > 200 else response,
        }
    except Exception as e:
        logger.error(f"Error in automated research: {e}", exc_info=True)
        return {"status": "error", "timestamp": datetime.now(UTC).isoformat(), "error": "Research failed"}


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "service": "Career Researcher",
        "status": "healthy",
        "timestamp": datetime.now(UTC).isoformat(),
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
