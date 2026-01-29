# CareerAssist - AI-Powered Career Assistant

## Multi-agent Enterprise-Grade SaaS Career Platform

_If you're looking at this in an IDE, please open the preview to view it in formatted glory._

---

## What is CareerAssist?

**CareerAssist** is an AI-powered career assistance platform that helps job seekers:

- 🎯 **Optimize CVs** for specific job postings with ATS-friendly rewrites
- 📊 **Analyze job fit** with detailed gap analysis and improvement suggestions  
- 🎤 **Prepare for interviews** with AI-generated questions tailored to the role
- 📈 **Track applications** with analytics and success rate insights

---

## Features

### CV Optimization
- Upload and parse CVs into structured data
- Get ATS-optimized rewrites tailored to specific jobs
- Maintain multiple CV versions for different roles

### Gap Analysis
- Compare your CV against job requirements
- Get fit scores (0-100) with detailed breakdowns
- Receive actionable improvement suggestions

### Interview Preparation
- AI-generated questions based on role and company
- Practice with behavioral, technical, and situational questions
- Get feedback on your answers with improvement tips

### Application Tracking
- Track applications through the pipeline
- Visualize success rates and response times
- Identify which CV versions perform best

---

## Architecture

CareerAssist uses a multi-agent architecture with 5 specialized AI agents:

| Agent | Purpose |
|-------|---------|
| **Orchestrator** | Routes career requests to specialist agents |
| **Extractor** | Parses CVs and job postings into structured data |
| **Analyzer** | Performs gap analysis and creates CV rewrites |
| **Charter** | Generates application tracking analytics |
| **Interviewer** | Creates interview questions and evaluates answers |

---

## Directory Structure

```
CV_Agent/
├── guides/              # Step-by-step deployment guides (START HERE)
├── backend/             # Agent code and Lambda functions
│   ├── orchestrator/    # Career request router
│   ├── extractor/       # CV and job parser
│   ├── analyzer/        # Gap analysis and rewrites
│   ├── charter/         # Application analytics
│   ├── interviewer/     # Interview preparation
│   ├── researcher/      # Job market research (App Runner)
│   ├── ingest/          # Document ingestion Lambda
│   ├── database/        # Shared database library
│   └── api/             # FastAPI backend for frontend
├── frontend/            # NextJS React application
├── terraform/           # Infrastructure as Code
└── scripts/             # Deployment and development scripts
```

---

## Getting Started

### Prerequisites

- AWS account with appropriate permissions
- Docker Desktop
- Node.js 18+
- Python 3.11+ with uv

### Deployment Guides

Follow the guides in the `guides/` directory in order:

1. **1_permissions.md** - Set up AWS IAM permissions
2. **2_sagemaker.md** - Deploy embedding endpoint
3. **3_ingest.md** - Set up vector storage
4. **4_researcher.md** - Deploy research agent
5. **5_database.md** - Deploy Aurora database
6. **6_agents.md** - Deploy AI agent orchestra
7. **7_frontend.md** - Deploy frontend and API
8. **8_enterprise.md** - Add monitoring and observability

---

## Tech Stack

- **Backend**: Python, OpenAI Agents SDK, AWS Lambda
- **Frontend**: NextJS, React, Clerk Authentication
- **Database**: Aurora Serverless v2 PostgreSQL
- **Vector Search**: S3 Vectors with SageMaker embeddings
- **LLM**: AWS Bedrock (Nova Pro)
- **Infrastructure**: Terraform, Docker

---

## Development

### Python Environment

Always use uv for Python:
```bash
uv add package
uv run script.py
```

### Testing

Each agent has two test files:
- `test_simple.py` - Local testing with mocks
- `test_full.py` - AWS deployment testing

### Deployment

```bash
# Package Lambda functions
uv run backend/package_docker.py

# Deploy Lambda functions
uv run backend/deploy_all_lambdas.py

# Deploy frontend
uv run scripts/deploy.py
```

---

## Documentation

- **[PLAN.md](PLAN.md)** - Complete conversion plan from Alex to CareerAssist
- **[AGENTS.md](AGENTS.md)** - Agent architecture details
- **[CLAUDE.md](CLAUDE.md)** - Context for AI assistants
- **[gameplan.md](gameplan.md)** - Full project guide

---

## Conversion Status

This project was converted from the "Alex" financial planner. Current status:

- ✅ Phase 1: Project Rename & Structure
- ✅ Phase 2: Database Schema Redesign
- ✅ Phase 3: Backend Agent Conversion
- ✅ Phase 4: Terraform Updates
- ✅ Phase 5: Vector Knowledge Base
- ✅ Phase 6: Frontend Conversion
- ✅ Phase 7: Documentation Updates
- ⏳ Phase 8: Testing & Deployment

---

## Cost Management

- Destroy Aurora when not actively working (biggest savings)
- Use `terraform destroy` in each directory
- Monitor costs in AWS Cost Explorer

---

## Support

If you encounter issues:
1. Check the troubleshooting sections in the guides
2. Review CloudWatch logs for Lambda errors
3. Verify terraform.tfvars is properly configured

---

*CareerAssist - Helping you land your dream job with AI-powered career assistance*