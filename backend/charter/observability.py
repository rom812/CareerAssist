"""
Observability module for LangFuse integration - Charter Agent.
Receives and continues traces from the Orchestrator for distributed tracing.
"""

import os
import json
import logging
from contextlib import contextmanager
from typing import Optional, Dict, Any

# Use root logger for Lambda compatibility
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Global Langfuse client (initialized lazily)
_langfuse_client = None


def get_langfuse_client():
    """Get or create the Langfuse client singleton."""
    global _langfuse_client
    
    if _langfuse_client is not None:
        return _langfuse_client
    
    secret_key = os.getenv("LANGFUSE_SECRET_KEY")
    public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
    base_url = os.getenv("LANGFUSE_BASE_URL", "https://cloud.langfuse.com")
    
    if not secret_key or not public_key:
        logger.info("🔍 Observability: Langfuse not configured (missing keys)")
        return None
    
    try:
        from langfuse import Langfuse
        
        _langfuse_client = Langfuse(
            secret_key=secret_key,
            public_key=public_key,
            host=base_url,
            enabled=True,
        )
        
        if _langfuse_client.auth_check():
            logger.info("✅ Observability: Langfuse client initialized")
            
        return _langfuse_client
        
    except ImportError as e:
        logger.error(f"❌ Observability: langfuse package not installed: {e}")
        return None
    except Exception as e:
        logger.error(f"❌ Observability: Failed to initialize Langfuse: {e}")
        return None


def truncate_for_trace(data: Any, max_length: int = 2000) -> Any:
    """Truncate large data for trace storage."""
    if isinstance(data, str) and len(data) > max_length:
        return data[:max_length] + f"... [truncated, total {len(data)} chars]"
    elif isinstance(data, dict):
        return {k: truncate_for_trace(v, max_length) for k, v in data.items()}
    elif isinstance(data, list):
        return [truncate_for_trace(item, max_length) for item in data[:10]]
    return data


@contextmanager
def observe(
    job_id: Optional[str] = None,
    agent_name: str = "career-charter",
    user_id: Optional[str] = None,
    trace_id: Optional[str] = None,
    parent_span_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
):
    """Context manager for observability with LangFuse."""
    client = get_langfuse_client()
    trace = None
    span = None
    
    if not client:
        yield None
        return
    
    try:
        if trace_id:
            logger.info(f"🔍 Continuing trace: {trace_id[:16]}...")
            trace = client.trace(
                id=trace_id,
                name=agent_name,
                metadata={"agent": agent_name, "job_id": job_id, **(metadata or {})},
                tags=["career-assist", agent_name],
            )
        elif job_id:
            new_trace_id = client.create_trace_id(seed=job_id)
            trace = client.trace(
                id=new_trace_id,
                name=agent_name,
                metadata={"agent": agent_name, "job_id": job_id, **(metadata or {})},
                tags=["career-assist", agent_name],
            )
        else:
            trace = client.trace(
                name=agent_name,
                metadata={"agent": agent_name, **(metadata or {})},
                tags=["career-assist", agent_name],
            )
        
        if user_id:
            trace.update(user_id=user_id)
        
        span = trace.span(
            name=f"{agent_name}-execution",
            parent_observation_id=parent_span_id,
        )
        
        yield {"trace": trace, "span": span, "trace_id": trace.id, "client": client}
        
    except Exception as e:
        logger.error(f"❌ Observability error: {e}")
        yield None
        
    finally:
        if span:
            try:
                span.end()
            except:
                pass
        if client:
            try:
                client.flush()
                logger.info("✅ Traces flushed")
            except Exception as e:
                logger.error(f"❌ Flush failed: {e}")


def log_span(trace_context, name, input_data=None, output_data=None, metadata=None, level="DEFAULT"):
    """Log a span to Langfuse."""
    if not trace_context or not trace_context.get("trace"):
        return
    try:
        span = trace_context["trace"].span(
            name=name,
            input=truncate_for_trace(input_data) if input_data else None,
            output=truncate_for_trace(output_data) if output_data else None,
            metadata=metadata or {},
            level=level,
        )
        span.end()
    except Exception as e:
        logger.warning(f"Failed to log span: {e}")


def extract_trace_context(event: Dict[str, Any]) -> Dict[str, Optional[str]]:
    """Extract trace context from Lambda event payload."""
    trace_ctx = event.get("_trace_context", {})
    return {
        "trace_id": trace_ctx.get("trace_id"),
        "parent_span_id": trace_ctx.get("parent_span_id"),
    }
