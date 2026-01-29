#!/usr/bin/env python3
"""
Test job discovery mode of the CareerAssist researcher
"""

import asyncio
from context import get_agent_instructions
from mcp_servers import create_playwright_mcp_server
from tools import store_discovered_job
from agents import Agent, Runner
from dotenv import load_dotenv

load_dotenv(override=True)


async def test_job_discovery():
    """Test the researcher agent in job discovery mode."""
    print("Testing CareerAssist researcher - JOB DISCOVERY MODE")
    print("=" * 60)
    print("This will scrape job listings from Indeed/Glassdoor...")
    print("=" * 60)

    # Use a query that triggers job discovery mode
    query = "Discover software engineering jobs on Indeed"

    try:
        async with create_playwright_mcp_server() as playwright_mcp:
            agent = Agent(
                name="CareerAssist Job Hunter",
                instructions=get_agent_instructions(),
                model="gpt-4.1-mini",
                tools=[store_discovered_job],
                mcp_servers=[playwright_mcp],
            )

            print("\n🔍 Starting job discovery...")
            result = await Runner.run(agent, input=query, max_turns=20)

        print("\nRESULT:")
        print("=" * 60)
        print(result.final_output)
        print("=" * 60)
        print("\n✅ Job discovery test completed!")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_job_discovery())
