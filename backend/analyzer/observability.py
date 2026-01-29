"""
Observability module for LangFuse integration - Analyzer Agent.
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
    
    # Check for required environment variables
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
        
        # Verify connection
        if _langfuse_client.auth_check():
            logger.info("✅ Observability: Langfuse client initialized and authenticated")
        else:
            logger.warning("⚠️ Observability: Langfuse auth check failed")
            
        return _langfuse_client
        
    except ImportError as e:
        logger.error(f"❌ Observability: langfuse package not installed: {e}")
        return None
    except Exception as e:
        logger.error(f"❌ Observability: Failed to initialize Langfuse: {e}")
        return None


def truncate_for_trace(data: Any, max_length: int = 2000) -> Any:
    """Truncate large data for trace storage to avoid bloat."""
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
    agent_name: str = "career-analyzer",
    user_id: Optional[str] = None,
    trace_id: Optional[str] = None,
    parent_span_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
):
    """
    Context manager for observability with LangFuse.
    
    Can receive trace context from parent (Orchestrator) to continue
    the distributed trace, or create a new trace if invoked directly.
    
    Args:
        job_id: The job ID (used as trace seed if no trace_id provided)
        agent_name: Name of this agent
        user_id: Optional user ID for tracking
        trace_id: Trace ID from parent (for distributed tracing)
        parent_span_id: Parent span ID from parent
        metadata: Additional metadata
    """
    client = get_langfuse_client()
    trace = None
    span = None
    
    if not client:
        logger.info("🔍 Observability: Langfuse not configured, skipping trace")
        yield None
        return
    
    try:
        # If we have trace_id from parent, continue that trace
        # Otherwise create a new trace (for direct invocation)
        if trace_id:
            logger.info(f"🔍 Continuing trace from orchestrator: {trace_id[:16]}...")
            trace = client.trace(
                id=trace_id,
                name=agent_name,
                metadata={
                    "agent": agent_name,
                    "job_id": job_id,
                    "continued_from_orchestrator": True,
                    **(metadata or {})
                },
                tags=["career-assist", agent_name],
            )
        elif job_id:
            # Create new trace with job_id as seed
            new_trace_id = client.create_trace_id(seed=job_id)
            trace = client.trace(
                id=new_trace_id,
                name=agent_name,
                metadata={
                    "agent": agent_name,
                    "job_id": job_id,
                    **(metadata or {})
                },
                tags=["career-assist", agent_name],
            )
            logger.info(f"🔍 Created new trace: {new_trace_id[:16]}...")
        else:
            # No job_id, create trace with random ID
            trace = client.trace(
                name=agent_name,
                metadata={"agent": agent_name, **(metadata or {})},
                tags=["career-assist", agent_name],
            )
            logger.info(f"🔍 Created trace: {trace.id[:16]}...")
        
        if user_id:
            trace.update(user_id=user_id)
        
        # Create a span for this agent's execution
        span = trace.span(
            name=f"{agent_name}-execution",
            parent_observation_id=parent_span_id,
            metadata={
                "parent_span_id": parent_span_id,
            }
        )
        
        yield {
            "trace": trace,
            "span": span,
            "trace_id": trace.id,
            "client": client,
        }
        
    except Exception as e:
        logger.error(f"❌ Observability: Error during tracing: {e}", exc_info=True)
        yield None
        
    finally:
        # End span
        if span:
            try:
                span.end()
            except Exception as e:
                logger.warning(f"Failed to end span: {e}")
        
        # Flush traces - critical for Lambda
        if client:
            try:
                logger.info("🔍 Observability: Flushing traces to Langfuse...")
                client.flush()
                logger.info("✅ Observability: Traces flushed successfully")
            except Exception as e:
                logger.error(f"❌ Observability: Failed to flush traces: {e}")


def log_generation(
    trace_context: Optional[Dict],
    name: str,
    input_text: str,
    output: Any,
    model: str = "bedrock/nova-pro",
    metadata: Optional[Dict] = None,
):
    """Log an LLM generation to Langfuse."""
    if not trace_context or not trace_context.get("trace"):
        return
    
    trace = trace_context["trace"]
    
    try:
        generation = trace.generation(
            name=name,
            input=truncate_for_trace(input_text),
            output=truncate_for_trace(output),
            model=model,
            metadata=metadata or {},
        )
        generation.end()
    except Exception as e:
        logger.warning(f"Failed to log generation: {e}")


def log_span(
    trace_context: Optional[Dict],
    name: str,
    input_data: Any = None,
    output_data: Any = None,
    metadata: Optional[Dict] = None,
    level: str = "DEFAULT",
):
    """Log a span (operation) to Langfuse."""
    if not trace_context or not trace_context.get("trace"):
        return
    
    trace = trace_context["trace"]
    
    try:
        span = trace.span(
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
    """
    Extract trace context from Lambda event payload.
    The orchestrator passes trace context in the _trace_context field.
    """
    trace_ctx = event.get("_trace_context", {})
    return {
        "trace_id": trace_ctx.get("trace_id"),
        "parent_span_id": trace_ctx.get("parent_span_id"),
    }
