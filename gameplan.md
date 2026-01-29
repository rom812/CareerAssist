# CareerAssist - AI Career Assistant Project Guide

## Project Overview

**CareerAssist** is a multi-agent enterprise-grade SaaS career assistance platform. This project converts the original "Alex" financial planner into a comprehensive career assistant that helps job seekers optimize CVs, analyze job fit, prepare for interviews, and track applications.

The project maintains full AWS deployability with Terraform and uses the same robust multi-agent architecture.

### What CareerAssist Provides

CareerAssist is an AI-powered career assistant that helps job seekers:
- **Optimize CVs** for specific job postings with ATS-friendly rewrites
- **Analyze job fit** with detailed gap analysis and improvement suggestions
- **Prepare for interviews** with AI-generated questions tailored to the role
- **Track applications** with analytics and success rate insights

### Why This Architecture Fits

The existing multi-agent architecture is perfect because:
- Multi-agent orchestration handles complex career workflows
- SQS enables async processing of CV analysis jobs
- S3 Vectors stores career knowledge (bullet templates, interview questions)
- Aurora DB tracks user data, applications, and history
- Terraform enables one-click AWS deployment

---

## Directory Structure

```
CV_Agent/
├── guides/              # Step-by-step deployment guides (START HERE)
│   ├── 1_permissions.md
│   ├── 2_sagemaker.md
│   ├── 3_ingest.md
│   ├── 4_researcher.md
│   ├── 5_database.md
│   ├── 6_agents.md
│   ├── 7_frontend.md
│   ├── 8_enterprise.md
│   ├── architecture.md
│   └── agent_architecture.md
│
├── backend/             # Agent code and Lambda functions
│   ├── orchestrator/    # Career request orchestrator agent
│   ├── extractor/       # CV and job posting parser agent
│   ├── analyzer/        # Gap analysis and CV rewriting agent
│   ├── charter/         # Application analytics visualization agent
│   ├── interviewer/     # Interview preparation agent
│   ├── researcher/      # Job market research agent (App Runner)
│   ├── ingest/          # Document ingestion Lambda
│   ├── database/        # Shared database library
│   └── api/             # FastAPI backend for frontend
│
├── frontend/            # NextJS React application
│   ├── pages/
│   ├── components/
│   └── lib/
│
├── terraform/           # Infrastructure as Code (IMPORTANT: Independent directories)
│   ├── 2_sagemaker/     # SageMaker embedding endpoint
│   ├── 3_ingestion/     # S3 Vectors and ingest Lambda
│   ├── 4_researcher/    # App Runner research service
│   ├── 5_database/      # Aurora Serverless v2
│   ├── 6_agents/        # Multi-agent Lambda functions
│   ├── 7_frontend/      # CloudFront, S3, API Gateway
│   └── 8_enterprise/    # CloudWatch dashboards and monitoring
│
└── scripts/             # Deployment and local development scripts
    ├── deploy.py        # Frontend deployment
    ├── run_local.py     # Local development
    └── destroy.py       # Cleanup script
```

---

## Agent Architecture

### Agent Transformation (from Alex)

| Original Agent | CareerAssist Agent | Lambda Function | Purpose |
|---------------|-------------------|-----------------|---------|
| `planner` | `orchestrator` | `career-orchestrator` | Route requests to specialists |
| `tagger` | `extractor` | `career-extractor` | Parse CV and job postings |
| `reporter` | `analyzer` | `career-analyzer` | Gap analysis + CV rewriting |
| `charter` | `charter` | `career-charter` | Application analytics charts |
| `retirement` | `interviewer` | `career-interviewer` | Interview question generation |
| `researcher` | `researcher` | `career-researcher` | Job market research (App Runner) |

### Agent Collaboration Pattern

```
User Request → SQS Queue → Orchestrator
                            ├─→ Extractor (CV/Job parsing)
                            ├─→ Analyzer (Gap analysis, rewrites)
                            ├─→ Charter (Application analytics)
                            └─→ Interviewer (Interview prep)
```

---

## Course Structure: The 8 Guides

**IMPORTANT:** Before working on the project, read all guides in the guides folder to fully understand the system.

### Week 3: Research Infrastructure

**Day 3 - Foundations**
- **Guide 1: AWS Permissions** (1_permissions.md)
  - Set up IAM permissions for CareerAssist project
  - Create CareerAccess group with required policies
  - Configure AWS CLI and credentials

- **Guide 2: SageMaker Deployment** (2_sagemaker.md)
  - Deploy SageMaker Serverless endpoint for embeddings
  - Use HuggingFace all-MiniLM-L6-v2 model
  - Test embedding generation

**Day 4 - Vector Storage**
- **Guide 3: Ingestion Pipeline** (3_ingest.md)
  - Create S3 Vectors bucket (90% cost savings!)
  - Deploy Lambda function for document ingestion
  - Set up API Gateway with API key auth
  - Seed career knowledge base (CV templates, interview questions)

**Day 5 - Research Agent**
- **Guide 4: Researcher Agent** (4_researcher.md)
  - Deploy autonomous research agent on App Runner
  - Use AWS Bedrock with Nova Pro model
  - Research job market, companies, and salary data

### Week 4: Career Platform

**Day 1 - Database**
- **Guide 5: Database & Infrastructure** (5_database.md)
  - Deploy Aurora Serverless v2 PostgreSQL
  - Enable Data API
  - Create career-focused database schema:
    - `user_profiles` - User data
    - `cv_versions` - Versioned resume storage
    - `job_postings` - Stored job descriptions
    - `gap_analyses` - CV vs Job comparisons
    - `cv_rewrites` - Job-tailored CV versions
    - `job_applications` - Application tracking pipeline
    - `interview_sessions` - Practice and real interviews
    - `jobs` - Async processing queue

**Day 2 - Agent Orchestra**
- **Guide 6: AI Agent Orchestra** (6_agents.md)
  - Deploy 5 Lambda agents (Orchestrator, Extractor, Analyzer, Charter, Interviewer)
  - Set up SQS queue for orchestration
  - Configure agent collaboration patterns

**Day 3 - Frontend**
- **Guide 7: Frontend & API** (7_frontend.md)
  - Set up Clerk authentication
  - Deploy NextJS React frontend with:
    - CV Manager page (`/cv`)
    - Job Board page (`/jobs`)
    - Job Analyzer page (`/analyze/[jobId]`)
    - Interview Practice page (`/interview/[sessionId]`)
    - Application Tracker page (`/tracker`)
    - Reports page (`/reports`)

**Day 4 - Enterprise Features**
- **Guide 8: Enterprise Grade** (8_enterprise.md)
  - Implement scalability configurations
  - Set up CloudWatch dashboards and alarms
  - Configure LangFuse observability

---

## IMPORTANT: Development Approach

Always use uv for ALL python code; there are uv projects in every directory.

Always do `uv add package` and `uv run module.py`, but NEVER `pip install xxx` and NEVER `python script.py`.

Try to lean away from shell scripts or Powershell scripts as they are platform dependent. Heavily favor writing python scripts (via uv) and managing files in the File Explorer.

---

## Terraform Strategy

### Independent Directory Architecture

Each terraform directory (2_sagemaker, 3_ingestion, etc.) is **independent** with:
- Its own local state file (`terraform.tfstate`)
- Its own `terraform.tfvars` configuration
- No dependencies on other terraform directories

### Critical Requirements

**⚠️ You MUST configure `terraform.tfvars` in each directory before running terraform apply**

Copy `terraform.tfvars.example` to `terraform.tfvars` and update the variables.

---

## Agent Strategy - OpenAI Agents SDK

Each Agent subdirectory has a common structure:

1. `lambda_handler.py` for the lambda function and running the agent
2. `agent.py` for the Agent creation and code
3. `templates.py` for prompts

CareerAssist uses OpenAI Agents SDK with LiteLLM to connect to Bedrock:

```python
model = LitellmModel(model=f"bedrock/{model_id}")
```

**IMPORTANT:** When using Bedrock through LiteLLM, set:
```python
os.environ["AWS_REGION_NAME"] = bedrock_region
```

---

## Common Issues and Troubleshooting

### Issue 1: `package_docker.py` Fails
**Root Cause**: Docker Desktop is not running
**Solution**: Start Docker Desktop, wait for it to fully initialize, then retry

### Issue 2: Bedrock Model Access Denied
**Root Cause**: Model access not granted in Bedrock, or wrong region
**Solution**: 
1. Go to Bedrock console in the correct region
2. Click "Model access"
3. Request access to Nova Pro

### Issue 3: Terraform Apply Fails
**Root Cause**: `terraform.tfvars` not configured
**Solution**: Copy from `.example` and fill in all required values

### Issue 4: Lambda Function Failures
**Diagnosis**: Check CloudWatch logs: `aws logs tail /aws/lambda/career-{agent-name} --follow`

### Issue 5: Aurora Database Connection Fails
**Root Cause**: Database not fully initialized (takes 10-15 minutes)
**Solution**: Wait for cluster to reach "available" status

---

## Technical Architecture Quick Reference

### Core Services by Guide

**Guides 1-2**: Foundations
- IAM permissions
- SageMaker Serverless endpoint (embeddings)

**Guide 3**: Vector Storage
- S3 Vectors bucket and index
- Lambda ingest function
- CV bullet templates, interview questions, ATS keyword guides

**Guide 4**: Research Agent
- App Runner service (Researcher)
- Job market and company research

**Guide 5**: Database
- Aurora Serverless v2 PostgreSQL
- Career-focused schema (CVs, jobs, analyses, applications, interviews)

**Guide 6**: Agent Orchestra
- 5 Lambda functions: Orchestrator, Extractor, Analyzer, Charter, Interviewer
- SQS queue for orchestration

**Guide 7**: Frontend
- NextJS static site on S3
- CloudFront CDN
- API Gateway + Lambda backend
- Clerk authentication

**Guide 8**: Enterprise
- CloudWatch dashboards
- Monitoring and alarms
- LangFuse observability

### Cost Management

**Cost optimization**:
- Destroy Aurora when not actively working (biggest savings)
- Use `terraform destroy` in each directory
- Monitor costs in AWS Cost Explorer

### Cleanup Process

```bash
# Destroy in reverse order (optional, but cleaner)
cd terraform/8_enterprise && terraform destroy
cd terraform/7_frontend && terraform destroy
cd terraform/6_agents && terraform destroy
cd terraform/5_database && terraform destroy  # Biggest cost savings
cd terraform/4_researcher && terraform destroy
cd terraform/3_ingestion && terraform destroy
cd terraform/2_sagemaker && terraform destroy
```

---

## Key Files to Modify

### Configuration Files
- `.env` - Root environment variables
- `frontend/.env.local` - Frontend Clerk configuration
- `terraform/*/terraform.tfvars` - Each terraform directory (copy from .example)

### Code Files
- `backend/researcher/server.py` - Region and model configuration
- Agent templates in `backend/*/templates.py` - For customization
- Frontend pages for UI modifications

---

## Conversion Progress

### Phase 1: Project Rename & Structure ✅ COMPLETED
- Backend directories renamed (planner→orchestrator, tagger→extractor, reporter→analyzer, retirement→interviewer)
- Utility scripts updated (deploy_all_lambdas.py, package_docker.py, test_full.py, test_simple.py, watch_agents.py)

### Phase 2: Database Schema Redesign ✅ COMPLETED
- New SQL migration created (002_career_schema.sql)
- Database library updated with career-focused functions
- Seed script created (seed_career_data.py)

### Remaining Phases
- Phase 3: Backend Agent Conversion
- Phase 4: Terraform Updates
- Phase 5: Vector Knowledge Base
- Phase 6: Frontend Conversion
- Phase 7: Documentation Updates
- Phase 8: Testing & Deployment

---

*This guide documents the CareerAssist project - an AI-powered career assistant. Last updated: January 2026*
