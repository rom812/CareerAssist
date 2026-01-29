"""
Charter Agent - Creates application tracking analytics and visualizations.
"""

import os
import json
import logging
from typing import Dict, Any, List

from agents import Agent, Runner, trace
from agents.extensions.models.litellm_model import LitellmModel

logger = logging.getLogger()

BEDROCK_MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "us.anthropic.claude-3-7-sonnet-20250219-v1:0")
BEDROCK_REGION = os.getenv("BEDROCK_REGION", "us-west-2")


from templates import CHARTER_INSTRUCTIONS, create_charter_task


def analyze_applications(applications_data: Dict[str, Any]) -> str:
    """
    Analyze application tracking data.
    Returns detailed breakdown for chart generation.
    """
    result = []
    
    applications = applications_data.get("applications", [])
    total_apps = len(applications)
    
    # Status breakdown
    status_counts = {}
    for app in applications:
        status = app.get("status", "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1
    
    result.append("Application Analytics:")
    result.append(f"Total Applications: {total_apps}")
    result.append("\nStatus Breakdown:")
    for status, count in sorted(status_counts.items(), key=lambda x: x[1], reverse=True):
        pct = (count / total_apps * 100) if total_apps > 0 else 0
        result.append(f"  {status}: {count} ({pct:.1f}%)")
    
    # Calculate funnel metrics
    saved = status_counts.get("saved", 0)
    applied = status_counts.get("applied", 0) + status_counts.get("screening", 0)
    interview = sum(status_counts.get(s, 0) for s in ["phone_screen", "interview", "technical", "onsite"])
    offer = status_counts.get("offer", 0) + status_counts.get("accepted", 0)
    
    result.append("\nFunnel Analysis:")
    result.append(f"  Saved: {saved}")
    result.append(f"  Applied: {applied}")
    result.append(f"  Interview Stage: {interview}")
    result.append(f"  Offers: {offer}")
    
    if applied > 0:
        response_rate = (interview / applied * 100)
        result.append(f"  Response Rate: {response_rate:.1f}%")
    
    if interview > 0:
        offer_rate = (offer / interview * 100)
        result.append(f"  Interview-to-Offer Rate: {offer_rate:.1f}%")
    
    # Gap frequency analysis
    gap_counts = {}
    for app in applications:
        gaps = app.get("gaps", [])
        for gap in gaps:
            skill = gap.get("missing_element", gap.get("requirement", "Unknown"))
            gap_counts[skill] = gap_counts.get(skill, 0) + 1
    
    if gap_counts:
        result.append("\nMost Common Skill Gaps:")
        for gap, count in sorted(gap_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
            result.append(f"  {gap}: {count} jobs")
    
    # Role breakdown
    role_counts = {}
    for app in applications:
        role = app.get("role_title", app.get("job", {}).get("role_title", "Unknown"))
        role_counts[role] = role_counts.get(role, 0) + 1
    
    if role_counts:
        result.append("\nApplications by Role:")
        for role, count in sorted(role_counts.items(), key=lambda x: x[1], reverse=True)[:8]:
            result.append(f"  {role}: {count}")
    
    # Fit score distribution
    fit_scores = [app.get("fit_score", 0) for app in applications if app.get("fit_score")]
    if fit_scores:
        avg_score = sum(fit_scores) / len(fit_scores)
        result.append(f"\nAverage Fit Score: {avg_score:.1f}/100")
    
    return "\n".join(result)


def create_agent(job_id: str, applications_data: Dict[str, Any], db=None):
    """Create the charter agent for application analytics."""
    
    os.environ["AWS_REGION_NAME"] = BEDROCK_REGION
    model = LitellmModel(model=f"bedrock/{BEDROCK_MODEL_ID}")
    
    logger.info(f"Charter: Creating agent for job {job_id}")
    
    # Analyze the applications upfront
    analysis = analyze_applications(applications_data)
    logger.info(f"Charter: Analysis generated, length: {len(analysis)}")
    
    # Create the task
    task = create_charter_task(analysis, applications_data)
    
    return model, task