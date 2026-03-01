#!/usr/bin/env python3
"""
Populate realistic job postings into the discovered_jobs table.
These represent the kind of jobs the scraper would find on Indeed/Glassdoor.
"""

import os
import uuid

import boto3
from dotenv import load_dotenv

load_dotenv(override=True)

AURORA_CLUSTER_ARN = os.getenv("AURORA_CLUSTER_ARN")
AURORA_SECRET_ARN = os.getenv("AURORA_SECRET_ARN")
DATABASE_NAME = os.getenv("DATABASE_NAME", "career")
AWS_REGION = os.getenv("DEFAULT_AWS_REGION", "us-east-1")

rds = boto3.client("rds-data", region_name=AWS_REGION)

JOBS = [
    {
        "source": "indeed",
        "source_job_id": "indeed-swe-001",
        "company_name": "Stripe",
        "role_title": "Senior Software Engineer, Payments",
        "location": "San Francisco, CA",
        "remote_policy": "hybrid",
        "salary_min": 185000,
        "salary_max": 265000,
        "description_text": "Join Stripe's Payments team to build the economic infrastructure for the internet. You'll work on low-latency, high-reliability payment processing systems that handle billions of dollars annually. Design and implement APIs used by millions of businesses worldwide.",
        "requirements_text": "7+ years software engineering experience. Strong proficiency in Ruby, Java, or Go. Experience with distributed systems and databases. Understanding of payment processing, PCI compliance a plus.",
    },
    {
        "source": "indeed",
        "source_job_id": "indeed-ml-002",
        "company_name": "OpenAI",
        "role_title": "Machine Learning Engineer, Safety",
        "location": "San Francisco, CA",
        "remote_policy": "onsite",
        "salary_min": 200000,
        "salary_max": 370000,
        "description_text": "Work on the cutting edge of AI safety research. Build evaluation frameworks, red-teaming tools, and safety classifiers for large language models. Contribute to making AI systems safer and more aligned with human values.",
        "requirements_text": "MS/PhD in CS, ML, or related field. 3+ years ML engineering experience. Strong Python and PyTorch skills. Experience with LLMs, RLHF, or constitutional AI preferred.",
    },
    {
        "source": "glassdoor",
        "source_job_id": "gd-ds-003",
        "company_name": "Netflix",
        "role_title": "Senior Data Scientist, Content Analytics",
        "location": "Los Gatos, CA",
        "remote_policy": "hybrid",
        "salary_min": 170000,
        "salary_max": 300000,
        "description_text": "Drive data-informed content decisions at Netflix. Build predictive models for content performance, audience segmentation, and recommendation improvements. Partner with content executives to shape our $17B content investment strategy.",
        "requirements_text": "5+ years data science experience. Expert in Python, SQL, and statistical modeling. Experience with A/B testing, causal inference, and recommendation systems. Strong communication skills for presenting to executives.",
    },
    {
        "source": "indeed",
        "source_job_id": "indeed-fe-004",
        "company_name": "Vercel",
        "role_title": "Staff Frontend Engineer",
        "location": "Remote",
        "remote_policy": "remote",
        "salary_min": 190000,
        "salary_max": 260000,
        "description_text": "Shape the future of web development at Vercel. Work on Next.js, Turbopack, and the Vercel platform. Build developer tools used by millions. Optimize performance and developer experience for the modern web.",
        "requirements_text": "8+ years frontend engineering. Deep expertise in React, TypeScript, and Next.js. Experience with build tools, bundlers, and web performance optimization. Open source contributions valued.",
    },
    {
        "source": "indeed",
        "source_job_id": "indeed-be-005",
        "company_name": "Databricks",
        "role_title": "Software Engineer, Data Platform",
        "location": "Seattle, WA",
        "remote_policy": "hybrid",
        "salary_min": 160000,
        "salary_max": 240000,
        "description_text": "Build the next generation of data lakehouse technology. Work on Apache Spark internals, Delta Lake, and Unity Catalog. Design distributed computing solutions that process petabytes of data for Fortune 500 companies.",
        "requirements_text": "4+ years in distributed systems or data infrastructure. Proficiency in Scala, Java, or Python. Experience with Spark, Hadoop, or similar frameworks. Understanding of storage systems and query optimization.",
    },
    {
        "source": "glassdoor",
        "source_job_id": "gd-devops-006",
        "company_name": "Cloudflare",
        "role_title": "Site Reliability Engineer",
        "location": "Austin, TX",
        "remote_policy": "hybrid",
        "salary_min": 150000,
        "salary_max": 210000,
        "description_text": "Keep the internet running at Cloudflare. Manage systems serving 25M+ HTTP requests per second. Design and implement automation, monitoring, and incident response for one of the world's largest networks.",
        "requirements_text": "5+ years SRE/DevOps experience. Strong Linux systems knowledge. Experience with Kubernetes, Terraform, and monitoring tools (Prometheus, Grafana). Networking fundamentals (BGP, DNS, TCP/IP).",
    },
    {
        "source": "indeed",
        "source_job_id": "indeed-ai-007",
        "company_name": "Anthropic",
        "role_title": "Research Engineer, Interpretability",
        "location": "San Francisco, CA",
        "remote_policy": "hybrid",
        "salary_min": 220000,
        "salary_max": 380000,
        "description_text": "Advance the science of AI interpretability at Anthropic. Build tools and techniques to understand what happens inside neural networks. Contribute to mechanistic interpretability research that helps make AI systems transparent and trustworthy.",
        "requirements_text": "Strong ML fundamentals and programming skills. Experience with transformer architectures. Published research in interpretability, representation learning, or related areas preferred. Python, JAX/PyTorch required.",
    },
    {
        "source": "glassdoor",
        "source_job_id": "gd-pm-008",
        "company_name": "Figma",
        "role_title": "Senior Product Manager, AI Features",
        "location": "New York, NY",
        "remote_policy": "hybrid",
        "salary_min": 175000,
        "salary_max": 270000,
        "description_text": "Define and execute the AI strategy for Figma's design tools. Lead cross-functional teams to ship AI-powered features that help millions of designers work more efficiently. Balance innovation with user trust and design tool integrity.",
        "requirements_text": "6+ years product management experience. Track record shipping AI/ML features. Strong understanding of design tools and creative workflows. Excellent stakeholder management and communication skills.",
    },
    {
        "source": "indeed",
        "source_job_id": "indeed-sec-009",
        "company_name": "CrowdStrike",
        "role_title": "Cloud Security Engineer",
        "location": "Remote",
        "remote_policy": "remote",
        "salary_min": 140000,
        "salary_max": 200000,
        "description_text": "Protect organizations from cyber threats at CrowdStrike. Design and implement cloud security solutions across AWS, Azure, and GCP. Build detection and response capabilities for cloud-native environments.",
        "requirements_text": "4+ years cloud security experience. Deep knowledge of AWS/Azure/GCP security services. Experience with CSPM, CWPP, or CNAPP. Scripting skills in Python or Go. Security certifications (CISSP, AWS Security) preferred.",
    },
    {
        "source": "glassdoor",
        "source_job_id": "gd-mobile-010",
        "company_name": "Airbnb",
        "role_title": "iOS Engineer, Search & Discovery",
        "location": "San Francisco, CA",
        "remote_policy": "hybrid",
        "salary_min": 165000,
        "salary_max": 240000,
        "description_text": "Build search and discovery experiences on Airbnb's iOS app used by 150M+ users. Work on personalized ranking, real-time availability, and map-based search. Optimize for performance and accessibility across all iOS devices.",
        "requirements_text": "5+ years iOS development. Expert in Swift and SwiftUI. Experience with search/ranking systems. Strong UIKit and performance optimization skills. Published apps with large user bases preferred.",
    },
    {
        "source": "indeed",
        "source_job_id": "indeed-data-011",
        "company_name": "Snowflake",
        "role_title": "Data Engineer, Platform",
        "location": "Bellevue, WA",
        "remote_policy": "hybrid",
        "salary_min": 155000,
        "salary_max": 225000,
        "description_text": "Build and scale Snowflake's internal data platform. Design ETL pipelines, data models, and analytics infrastructure that powers business decisions. Work with petabyte-scale data across cloud providers.",
        "requirements_text": "4+ years data engineering. Strong SQL and Python skills. Experience with Snowflake, dbt, Airflow, or Spark. Understanding of data modeling, warehousing, and governance. Cloud experience (AWS/Azure/GCP).",
    },
    {
        "source": "indeed",
        "source_job_id": "indeed-infra-012",
        "company_name": "Palantir Technologies",
        "role_title": "Forward Deployed Software Engineer",
        "location": "Washington, DC",
        "remote_policy": "onsite",
        "salary_min": 145000,
        "salary_max": 210000,
        "description_text": "Work directly with government and commercial clients to solve their hardest data problems. Deploy Palantir's platforms (Foundry, Gotham) and build custom integrations. Travel to client sites to understand needs and deliver solutions.",
        "requirements_text": "2+ years software engineering. Strong problem-solving and communication skills. Willingness to travel 25-50%. Experience with Java, Python, or TypeScript. US citizenship and ability to obtain security clearance required.",
    },
    {
        "source": "glassdoor",
        "source_job_id": "gd-gpu-013",
        "company_name": "NVIDIA",
        "role_title": "CUDA Software Engineer",
        "location": "Santa Clara, CA",
        "remote_policy": "hybrid",
        "salary_min": 180000,
        "salary_max": 310000,
        "description_text": "Develop GPU-accelerated computing solutions at NVIDIA. Optimize CUDA kernels for AI training and inference workloads. Work on next-generation GPU architectures and software frameworks that power the AI revolution.",
        "requirements_text": "5+ years systems programming (C/C++). GPU programming experience (CUDA, OpenCL). Strong understanding of computer architecture and performance optimization. Experience with deep learning frameworks (PyTorch, TensorFlow) a plus.",
    },
    {
        "source": "indeed",
        "source_job_id": "indeed-startup-014",
        "company_name": "Replit",
        "role_title": "Full Stack Engineer, AI Code Generation",
        "location": "Remote",
        "remote_policy": "remote",
        "salary_min": 150000,
        "salary_max": 220000,
        "description_text": "Build the future of software creation at Replit. Work on AI-powered code generation, intelligent autocomplete, and collaborative coding features. Make programming accessible to the next billion developers.",
        "requirements_text": "3+ years full-stack development. Experience with TypeScript, React, and Node.js. Interest in AI/ML and developer tools. Experience with LLM integration and prompt engineering a plus.",
    },
    {
        "source": "glassdoor",
        "source_job_id": "gd-health-015",
        "company_name": "Epic Systems",
        "role_title": "Software Developer, Clinical Applications",
        "location": "Madison, WI",
        "remote_policy": "onsite",
        "salary_min": 115000,
        "salary_max": 165000,
        "description_text": "Build healthcare software used by 305M+ patients. Develop clinical applications for electronic health records, patient portals, and interoperability platforms. Impact healthcare delivery across 2,800+ hospitals worldwide.",
        "requirements_text": "BS in CS or related field. Strong programming fundamentals. Interest in healthcare technology. Experience with C#, TypeScript, or similar languages. Willingness to relocate to Madison, WI.",
    },
]


def store_job(job: dict) -> bool:
    job_id = str(uuid.uuid4())
    sql = """
    INSERT INTO discovered_jobs
    (id, source, source_job_id, company_name, role_title, location, remote_policy,
     salary_min, salary_max, description_text, requirements_text, is_active, created_at)
    VALUES
    (:id::uuid, :source, :source_job_id, :company_name, :role_title, :location, :remote_policy,
     :salary_min, :salary_max, :description_text, :requirements_text, true, NOW())
    ON CONFLICT (source, source_job_id) DO UPDATE SET
        company_name = EXCLUDED.company_name,
        role_title = EXCLUDED.role_title,
        location = EXCLUDED.location,
        salary_min = EXCLUDED.salary_min,
        salary_max = EXCLUDED.salary_max,
        description_text = EXCLUDED.description_text,
        requirements_text = EXCLUDED.requirements_text,
        is_active = true,
        updated_at = NOW()
    """

    params = [
        {"name": "id", "value": {"stringValue": job_id}},
        {"name": "source", "value": {"stringValue": job["source"]}},
        {"name": "source_job_id", "value": {"stringValue": job["source_job_id"]}},
        {"name": "company_name", "value": {"stringValue": job["company_name"]}},
        {"name": "role_title", "value": {"stringValue": job["role_title"]}},
        {"name": "location", "value": {"stringValue": job["location"]}},
        {"name": "remote_policy", "value": {"stringValue": job["remote_policy"]}},
        {"name": "salary_min", "value": {"longValue": job["salary_min"]}},
        {"name": "salary_max", "value": {"longValue": job["salary_max"]}},
        {"name": "description_text", "value": {"stringValue": job["description_text"]}},
        {"name": "requirements_text", "value": {"stringValue": job["requirements_text"]}},
    ]

    try:
        rds.execute_statement(
            resourceArn=AURORA_CLUSTER_ARN,
            secretArn=AURORA_SECRET_ARN,
            database=DATABASE_NAME,
            sql=sql,
            parameters=params,
        )
        return True
    except Exception as e:
        print(f"  Error: {e}")
        return False


if __name__ == "__main__":
    if not AURORA_CLUSTER_ARN or not AURORA_SECRET_ARN:
        print("Database credentials missing in .env")
        exit(1)

    print("Populating discovered jobs...")
    print("=" * 60)

    stored = 0
    for job in JOBS:
        if store_job(job):
            stored += 1
            print(f"  Added: {job['role_title']} at {job['company_name']}")
        else:
            print(f"  FAILED: {job['role_title']} at {job['company_name']}")

    print(f"\n{'=' * 60}")
    print(f"Done! {stored}/{len(JOBS)} jobs stored in database")
