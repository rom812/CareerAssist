"""
Interviewer Agent - Generates interview questions and evaluates answers.
"""

import json
import logging
import os
from dataclasses import dataclass
from typing import Any

from agents import Agent, AgentOutputSchema, RunContextWrapper, Runner, function_tool, trace
from agents.extensions.models.litellm_model import LitellmModel

logger = logging.getLogger()

BEDROCK_MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "us.anthropic.claude-3-7-sonnet-20250219-v1:0")
BEDROCK_REGION = os.getenv("BEDROCK_REGION", "us-west-2")


# Import schemas
try:
    from src.schemas import AnswerEvaluation, InterviewPack, InterviewQuestion, InterviewType, QuestionDifficulty
except ImportError:
    from typing import Literal

    from pydantic import BaseModel, Field

    InterviewType = Literal["behavioral", "technical", "system_design", "situational", "motivation", "mixed"]
    QuestionDifficulty = Literal["easy", "medium", "hard"]

    class InterviewQuestion(BaseModel):
        id: str = Field(description="Unique question ID")
        question: str = Field(description="The interview question")
        type: InterviewType = Field(description="Type of question")
        topic: str = Field(description="Topic area being tested")
        difficulty: QuestionDifficulty = Field(description="Difficulty level")
        what_theyre_testing: str = Field(description="What this question assesses")
        sample_answer_outline: str = Field(description="Outline of a good answer structure")
        follow_up_questions: list[str] = Field(default=[], description="Potential follow-up questions")
        company_specific: bool = Field(default=False, description="Whether specific to this company")
        gap_related: bool = Field(default=False, description="Whether addresses a gap from analysis")

    class InterviewPack(BaseModel):
        job_id: str = Field(description="UUID of the job posting")
        company: str = Field(description="Company name")
        role: str = Field(description="Role title")
        questions: list[InterviewQuestion] = Field(description="Prepared interview questions")
        focus_areas: list[str] = Field(description="Key areas to focus on based on job and any gaps")
        company_specific_tips: list[str] = Field(default=[], description="Tips specific to this company")
        general_tips: list[str] = Field(default=[], description="General interview tips for this role type")

    class AnswerEvaluation(BaseModel):
        question_id: str = Field(description="ID of the question being evaluated")
        score: int = Field(description="Score 1-5", ge=1, le=5)
        star_method_used: bool | None = Field(None, description="For behavioral: was STAR used?")
        clarity: int = Field(description="Clarity of communication 1-5", ge=1, le=5)
        relevance: int = Field(description="Relevance to the question 1-5", ge=1, le=5)
        depth: int = Field(description="Depth of answer 1-5", ge=1, le=5)
        strengths: list[str] = Field(default=[], description="What was done well")
        improvements: list[str] = Field(default=[], description="Areas for improvement")
        better_answer_example: str = Field(description="Example of an improved answer")


from templates import ANSWER_EVALUATION_PROMPT, INTERVIEW_PREP_PROMPT


@dataclass
class InterviewerContext:
    """Context for the Interviewer agent"""

    job_id: str
    job_profile: dict[str, Any]
    cv_profile: dict[str, Any] | None = None
    gap_analysis: dict[str, Any] | None = None
    db: Any | None = None


def format_job_for_interview(job_profile: dict[str, Any]) -> str:
    """Format job profile for interview question generation."""
    lines = [
        f"## Role: {job_profile.get('role_title', 'Unknown')} at {job_profile.get('company', 'Unknown')}",
        f"Seniority: {job_profile.get('seniority', 'unknown')}",
        "",
    ]

    if job_profile.get("must_have"):
        lines.append("**Key Requirements:**")
        for req in job_profile["must_have"][:8]:
            text = req.get("text", "") if isinstance(req, dict) else str(req)
            lines.append(f"- {text}")
        lines.append("")

    if job_profile.get("responsibilities"):
        lines.append("**Responsibilities:**")
        for resp in job_profile["responsibilities"][:6]:
            lines.append(f"- {resp}")
        lines.append("")

    return "\n".join(lines)


def format_gaps_for_interview(gap_analysis: dict[str, Any]) -> str:
    """Format gap analysis for targeted interview prep."""
    if not gap_analysis:
        return ""

    lines = ["## Candidate Gaps to Address:"]
    for gap in gap_analysis.get("gaps", [])[:5]:
        if isinstance(gap, dict):
            lines.append(f"- {gap.get('missing_element', gap.get('requirement', ''))}")

    return "\n".join(lines)


@function_tool
async def get_interview_questions(wrapper: RunContextWrapper[InterviewerContext], role_type: str, company: str) -> str:
    """
    Get common interview questions from knowledge base.

    Args:
        role_type: Type of role (e.g., "software_engineer")
        company: Company name for company-specific questions

    Returns:
        Relevant interview questions from database
    """
    try:
        import boto3

        sts = boto3.client("sts")
        account_id = sts.get_caller_identity()["Account"]
        bucket = f"career-vectors-{account_id}"

        sagemaker_region = os.getenv("DEFAULT_AWS_REGION", "us-east-1")
        sagemaker = boto3.client("sagemaker-runtime", region_name=sagemaker_region)
        endpoint_name = os.getenv("SAGEMAKER_ENDPOINT", "career-embedding-endpoint")
        query = f"interview questions for {role_type} at {company}"

        response = sagemaker.invoke_endpoint(
            EndpointName=endpoint_name,
            ContentType="application/json",
            Body=json.dumps({"inputs": query}),
        )

        result = json.loads(response["Body"].read().decode())
        if isinstance(result, list) and result:
            embedding = result[0][0] if isinstance(result[0], list) else result[0]
        else:
            embedding = result

        s3v = boto3.client("s3vectors", region_name=sagemaker_region)
        response = s3v.query_vectors(
            vectorBucketName=bucket,
            indexName="interview-questions",
            queryVector={"float32": embedding},
            topK=5,
            returnMetadata=True,
        )

        questions = []
        for vector in response.get("vectors", []):
            metadata = vector.get("metadata", {})
            q_list = metadata.get("questions", [])
            questions.extend(q_list)

        if questions:
            return "Common interview questions:\n" + "\n".join(f"• {q}" for q in questions[:8])
        return "No specific questions found - generate based on job requirements."

    except Exception as e:
        logger.warning(f"Could not retrieve interview questions: {e}")
        return "Questions database unavailable - generate based on job requirements."


def _extract_json_from_text(text: str) -> dict[str, Any]:
    """Extract JSON object from LLM text response."""
    # Try to find JSON block in markdown code fence
    import re

    json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if json_match:
        return json.loads(json_match.group(1))

    # Try to find raw JSON object
    start = text.find("{")
    if start == -1:
        raise ValueError("No JSON object found in response")

    # Find matching closing brace
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return json.loads(text[start : i + 1])

    raise ValueError("No complete JSON object found in response")


async def generate_interview_pack(
    job_id: str, job_profile: dict[str, Any], cv_profile: dict[str, Any] = None, gap_analysis: dict[str, Any] = None
) -> InterviewPack:
    """
    Generate comprehensive interview preparation pack.

    Uses text output instead of structured output_type to avoid Bedrock
    "Model produced invalid sequence as part of ToolUse" errors with
    complex nested schemas.

    Args:
        job_id: Job posting ID
        job_profile: Parsed job profile
        cv_profile: Optional CV profile for personalization
        gap_analysis: Optional gap analysis for targeted questions

    Returns:
        InterviewPack with questions and tips
    """
    os.environ["AWS_REGION_NAME"] = BEDROCK_REGION
    model = LitellmModel(model=f"bedrock/{BEDROCK_MODEL_ID}")

    job_text = format_job_for_interview(job_profile)
    gap_text = format_gaps_for_interview(gap_analysis) if gap_analysis else ""

    agent = Agent(
        name="Interview Coach",
        instructions=INTERVIEW_PREP_PROMPT,
        model=model,
    )

    task = f"""Generate an interview preparation pack for this role.

{job_text}

{gap_text}

Job ID: {job_id}
Company: {job_profile.get("company", "Unknown")}
Role: {job_profile.get("role_title", "Unknown")}

Generate:
1. 8-12 interview questions covering behavioral, technical, and situational types
2. Focus areas for preparation
3. Company-specific tips if known
4. General interview tips for this role type

For each question:
- Assign a unique ID (use format: q1, q2, etc.)
- Specify what the interviewer is testing
- Provide an answer outline
- Include potential follow-up questions
- Mark if it addresses a gap from the analysis

IMPORTANT: Return your response as a single JSON object with this exact structure:
{{
  "job_id": "{job_id}",
  "company": "<company name>",
  "role": "<role title>",
  "questions": [
    {{
      "id": "q1",
      "question": "<the question>",
      "type": "<behavioral|technical|system_design|situational|motivation|mixed>",
      "topic": "<topic area>",
      "difficulty": "<easy|medium|hard>",
      "what_theyre_testing": "<what this assesses>",
      "sample_answer_outline": "<outline of a good answer>",
      "follow_up_questions": ["<follow-up 1>", "<follow-up 2>"],
      "company_specific": false,
      "gap_related": false
    }}
  ],
  "focus_areas": ["<area 1>", "<area 2>"],
  "company_specific_tips": ["<tip 1>"],
  "general_tips": ["<tip 1>", "<tip 2>"]
}}

Return ONLY the JSON object, no other text."""

    with trace("Interview Pack Generation"):
        result = await Runner.run(agent, input=task)

    # Parse JSON from text response and validate with Pydantic
    raw_text = result.final_output
    try:
        data = _extract_json_from_text(raw_text)
    except (json.JSONDecodeError, ValueError) as e:
        logger.error(f"Failed to parse interview pack JSON: {e}")
        logger.error(f"Raw response (first 500 chars): {raw_text[:500]}")
        raise ValueError(f"Failed to parse interview pack from LLM response: {e}") from e

    pack = InterviewPack(**data)
    logger.info(f"Generated interview pack with {len(pack.questions)} questions")
    return pack


async def evaluate_answer(question: InterviewQuestion, answer: str) -> AnswerEvaluation:
    """
    Evaluate a candidate's interview answer.

    Args:
        question: The interview question
        answer: Candidate's answer text

    Returns:
        AnswerEvaluation with scores and feedback
    """
    os.environ["AWS_REGION_NAME"] = BEDROCK_REGION
    model = LitellmModel(model=f"bedrock/{BEDROCK_MODEL_ID}")

    agent = Agent(
        name="Interview Evaluator",
        instructions=ANSWER_EVALUATION_PROMPT,
        model=model,
        output_type=AgentOutputSchema(AnswerEvaluation, strict_json_schema=False),
    )

    task = f"""Evaluate this interview answer.

**Question:** {question.question}
**Type:** {question.type}
**What they're testing:** {question.what_theyre_testing}

**Candidate's Answer:**
{answer}

Provide:
1. Overall score (1-5)
2. Whether STAR method was used (for behavioral questions)
3. Clarity, relevance, and depth scores (1-5 each)
4. Specific strengths of the answer
5. Areas for improvement
6. Example of a better answer

Question ID: {question.id}"""

    with trace("Answer Evaluation"):
        result = await Runner.run(agent, input=task)

    return result.final_output


def create_agent(
    job_id: str,
    job_profile: dict[str, Any],
    cv_profile: dict[str, Any] = None,
    gap_analysis: dict[str, Any] = None,
    db=None,
):
    """Create the interviewer agent with tools and context."""

    os.environ["AWS_REGION_NAME"] = BEDROCK_REGION
    model = LitellmModel(model=f"bedrock/{BEDROCK_MODEL_ID}")

    context = InterviewerContext(
        job_id=job_id, job_profile=job_profile, cv_profile=cv_profile, gap_analysis=gap_analysis, db=db
    )

    tools = [get_interview_questions]

    job_text = format_job_for_interview(job_profile)
    gap_text = format_gaps_for_interview(gap_analysis) if gap_analysis else ""

    task = f"""Prepare interview coaching for this role.

{job_text}

{gap_text}

Use available tools to find relevant interview questions, then provide comprehensive preparation."""

    return model, tools, task, context
