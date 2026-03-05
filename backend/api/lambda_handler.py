"""Lambda handler for the FastAPI application."""

import json
import logging
import os
import urllib.error
import urllib.request

from mangum import Mangum

from api.main import app

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Mangum handler for API Gateway requests
_mangum_handler = Mangum(app, lifespan="off")


def handler(event, context):
    """
    Lambda handler that supports both API Gateway requests and async research invocations.

    When invoked with {"_async_research": True, ...}, it calls the researcher service
    directly with a long timeout (bypassing API Gateway's 30s limit).
    Otherwise, it delegates to Mangum for normal FastAPI request handling.
    """
    if event.get("_async_research"):
        return _handle_async_research(event)

    return _mangum_handler(event, context)


def _handle_async_research(event):
    """Call the researcher service with a long timeout."""
    researcher_url = event.get("researcher_url", "")
    topic = event.get("topic", "")

    if not researcher_url:
        logger.error("Async research: no researcher_url provided")
        return {"statusCode": 500, "body": "No researcher URL"}

    import time

    url = f"{researcher_url}/research"
    max_retries = 3

    for attempt in range(max_retries):
        try:
            data = json.dumps({"topic": topic or None}).encode("utf-8")
            req = urllib.request.Request(
                url, data=data, headers={"Content-Type": "application/json"}, method="POST"
            )

            logger.info(f"Async research (attempt {attempt + 1}): calling {url} with topic={topic!r}")
            with urllib.request.urlopen(req, timeout=280) as response:
                result = response.read().decode("utf-8")

            logger.info(f"Async research completed successfully: {result[:200]}")
            return {"statusCode": 200, "body": result}

        except urllib.error.HTTPError as e:
            logger.error(f"Async research HTTP error (attempt {attempt + 1}): {e.code} {e.reason}")
            # Retry on 502/503 (App Runner transient errors)
            if e.code in (502, 503) and attempt < max_retries - 1:
                time.sleep(5 * (attempt + 1))
                continue
            return {"statusCode": e.code, "body": "Research service error"}

        except Exception as e:
            logger.error(f"Async research error (attempt {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                time.sleep(5)
                continue
            return {"statusCode": 500, "body": "Research request failed"}
