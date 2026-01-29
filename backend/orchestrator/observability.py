"""
Observability module for LangFuse integration.
Provides comprehensive tracing for multi-agent career assistant.

Features:
- Deterministic trace IDs from job_id for cross-service correlation
- Trace context propagation between Lambda functions
- Structured logging of inputs, outputs, and errors
- Proper Lambda flush without arbitrary sleeps
"""

import os
import json
import logging
from contextlib import contextmanager
from typing import Optional, Dict, Any
from functools import wraps

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


def create_trace_id(job_id: str) -> Optional[str]:
    """
    Create a deterministic trace ID from job_id.
    This ensures all operations for the same job appear in the same Langfuse trace.
    """
    client = get_langfuse_client()
    if client:
        try:
            return client.create_trace_id(seed=job_id)
        except Exception as e:
            logger.warning(f"Could not create trace ID: {e}")
    return None


def truncate_for_trace(data: Any, max_length: int = 2000) -> Any:
    """Truncate large data for trace storage to avoid bloat."""
    if isinstance(data, str) and len(data) > max_length:
        return data[:max_length] + f"... [truncated, total {len(data)} chars]"
    elif isinstance(data, dict):
        return {k: truncate_for_trace(v, max_length) for k, v in data.items()}
    elif isinstance(data, list):
        return [truncate_for_trace(item, max_length) for item in data[:10]]  # Max 10 items
    return data


@contextmanager
def observe(
    job_id: Optional[str] = None,
    agent_name: str = "career-orchestrator",
    user_id: Optional[str] = None,
    trace_id: Optional[str] = None,
    parent_span_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
):
    """
    Context manager for observability with LangFuse.
    
    Creates or continues a trace for the given job_id, ensuring all
    operations are correlated in the Langfuse dashboard.
    
    Args:
        job_id: The job ID to use as trace seed (creates deterministic trace_id)
        agent_name: Name of the agent (for display in Langfuse)
        user_id: Optional user ID for user tracking
        trace_id: Optional explicit trace ID (overrides job_id seed)
        parent_span_id: Optional parent span ID for distributed tracing
        metadata: Optional metadata to attach to the trace
    
    Usage:
        with observe(job_id="abc-123", agent_name="orchestrator"):
            result = await agent.run(...)
    """
    client = get_langfuse_client()
    trace = None
    span = None
    
    if not client:
        logger.info("🔍 Observability: Langfuse not configured, skipping trace")
        yield None
        return
    
    try:
        # Create or use provided trace ID
        if trace_id is None and job_id:
            trace_id = create_trace_id(job_id)
        
        # Build trace context
        trace_kwargs = {
            "name": agent_name,
            "metadata": {
                "agent": agent_name,
                "job_id": job_id,
                **(metadata or {})
            },
            "tags": ["career-assist", agent_name],
        }
        
        if trace_id:
            trace_kwargs["id"] = trace_id
        if user_id:
            trace_kwargs["user_id"] = user_id
        
        # Create trace
        trace = client.trace(**trace_kwargs)
        logger.info(f"🔍 Trace created: {trace.id} for job {job_id}")
        
        # If continuing from parent span, create a child span
        if parent_span_id:
            span = trace.span(
                name=f"{agent_name}-execution",
                parent_observation_id=parent_span_id,
                metadata={"continued_from": parent_span_id}
            )
            logger.info(f"🔍 Continuing trace from parent span: {parent_span_id}")
        
        # Yield trace context for use in the wrapped code
        yield {
            "trace": trace,
            "span": span,
            "trace_id": trace.id,
            "client": client,
        }
        
    except Exception as e:
        logger.error(f"❌ Observability: Error during tracing: {e}", exc_info=True)
        if trace:
            try:
                trace.update(
                    metadata={"error": str(e)},
                    level="ERROR"
                )
            except:
                pass
        yield None
        
    finally:
        # End span if created
        if span:
            try:
                span.end()
            except Exception as e:
                logger.warning(f"Failed to end span: {e}")
        
        # Flush traces - critical for Lambda!
        if client:
            try:
                logger.info("🔍 Observability: Flushing traces to Langfuse...")
                client.flush()
                logger.info("✅ Observability: Traces flushed successfully")
            except Exception as e:
                logger.error(f"❌ Observability: Failed to flush traces: {e}")


def log_agent_invocation(
    trace_context: Optional[Dict],
    agent_name: str,
    input_payload: Dict[str, Any],
    output_payload: Optional[Dict[str, Any]] = None,
    error: Optional[str] = None,
    duration_ms: Optional[float] = None,
):
    """
    Log an agent invocation (Lambda call) to Langfuse.
    
    Args:
        trace_context: The trace context from observe()
        agent_name: Name of the invoked agent
        input_payload: The payload sent to the agent
        output_payload: The response from the agent (if successful)
        error: Error message (if failed)
        duration_ms: Duration of the call in milliseconds
    """
    if not trace_context or not trace_context.get("trace"):
        return
    
    trace = trace_context["trace"]
    
    try:
        # Create a span for the agent invocation
        span = trace.span(
            name=f"invoke-{agent_name}",
            input=truncate_for_trace(input_payload),
            output=truncate_for_trace(output_payload) if output_payload else None,
            metadata={
                "agent_invoked": agent_name,
                "success": error is None,
                "error": error,
            },
            level="ERROR" if error else "DEFAULT",
        )
        
        if duration_ms:
            span.update(metadata={"duration_ms": duration_ms})
        
        span.end()
        
        logger.info(f"📊 Logged invocation of {agent_name}: success={error is None}")
        
    except Exception as e:
        logger.warning(f"Failed to log agent invocation: {e}")


def log_tool_call(
    trace_context: Optional[Dict],
    tool_name: str,
    input_args: Dict[str, Any],
    output: Any = None,
    error: Optional[str] = None,
):
    """
    Log a tool call to Langfuse.
    """
    if not trace_context or not trace_context.get("trace"):
        return
    
    trace = trace_context["trace"]
    
    try:
        span = trace.span(
            name=f"tool-{tool_name}",
            input=truncate_for_trace(input_args),
            output=truncate_for_trace(output) if output else None,
            metadata={
                "tool_name": tool_name,
                "success": error is None,
                "error": error,
            },
            level="ERROR" if error else "DEFAULT",
        )
        span.end()
        
    except Exception as e:
        logger.warning(f"Failed to log tool call: {e}")


def log_db_operation(
    trace_context: Optional[Dict],
    operation: str,
    table: str,
    success: bool,
    error: Optional[str] = None,
    affected_rows: Optional[int] = None,
):
    """
    Log a database operation to Langfuse.
    """
    if not trace_context or not trace_context.get("trace"):
        return
    
    trace = trace_context["trace"]
    
    try:
        span = trace.span(
            name=f"db-{operation}-{table}",
            metadata={
                "operation": operation,
                "table": table,
                "success": success,
                "error": error,
                "affected_rows": affected_rows,
            },
            level="ERROR" if error else "DEFAULT",
        )
        span.end()
        
    except Exception as e:
        logger.warning(f"Failed to log DB operation: {e}")


def get_trace_context_for_propagation(trace_context: Optional[Dict]) -> Dict[str, str]:
    """
    Get trace context to propagate to child Lambda invocations.
    
    Returns a dict with trace_id and parent_span_id that should be
    included in the Lambda payload.
    """
    if not trace_context:
        return {}
    
    result = {}
    
    if trace_context.get("trace"):
        result["trace_id"] = trace_context["trace"].id
    
    if trace_context.get("span"):
        result["parent_span_id"] = trace_context["span"].id
    elif trace_context.get("trace"):
        # Use trace ID as parent if no span
        result["parent_span_id"] = trace_context["trace"].id
    
    return result


# Instrument OpenAI Agents SDK if available
def setup_openai_agents_instrumentation():
    """
    Set up instrumentation for OpenAI Agents SDK.
    This captures all LLM calls made through the agents framework.
    """
    try:
        from openinference.instrumentation.openai_agents import OpenAIAgentsInstrumentor
        OpenAIAgentsInstrumentor().instrument()
        logger.info("✅ Observability: OpenAI Agents SDK instrumented")
        return True
    except ImportError:
        logger.info("🔍 Observability: openinference not available, using basic tracing")
        return False
    except Exception as e:
        logger.warning(f"⚠️ Observability: Failed to instrument OpenAI Agents: {e}")
        return False
