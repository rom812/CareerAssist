#!/usr/bin/env python3
"""
Seed data for CareerAssist
Loads sample CV templates, interview questions, and testing data
"""

import os
import json
import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv(override=True)

# Get config from environment
cluster_arn = os.environ.get("AURORA_CLUSTER_ARN")
secret_arn = os.environ.get("AURORA_SECRET_ARN")
database = os.environ.get("AURORA_DATABASE", "career")
region = os.environ.get("DEFAULT_AWS_REGION", "us-east-1")

if not cluster_arn or not secret_arn:
    print("❌ Missing AURORA_CLUSTER_ARN or AURORA_SECRET_ARN in .env file")
    exit(1)

client = boto3.client("rds-data", region_name=region)


# ==============================================================================
# Sample CV Templates (for testing and demonstration)
# ==============================================================================

SAMPLE_CVS = [
    {
        "version_name": "Software Engineer",
        "raw_text": """
JOHN DOE
Software Engineer | john.doe@email.com | (555) 123-4567
San Francisco, CA | linkedin.com/in/johndoe | github.com/johndoe

PROFESSIONAL SUMMARY
Experienced software engineer with 5+ years of experience building scalable web applications. 
Proficient in Python, JavaScript, and cloud technologies. Passionate about clean code and 
test-driven development.

TECHNICAL SKILLS
Languages: Python, JavaScript, TypeScript, Java, SQL
Frameworks: React, Node.js, Django, FastAPI, Flask
Cloud: AWS (EC2, Lambda, S3, RDS), GCP, Docker, Kubernetes
Databases: PostgreSQL, MongoDB, Redis
Tools: Git, Jenkins, Terraform, GitHub Actions

WORK EXPERIENCE

Senior Software Engineer | TechCorp Inc. | Jan 2022 - Present
- Led development of microservices architecture serving 500K+ daily users
- Reduced API response time by 40% through Redis caching implementation
- Mentored team of 3 junior developers, conducting code reviews and pair programming
- Implemented CI/CD pipeline reducing deployment time from 2 hours to 15 minutes

Software Engineer | StartupXYZ | Jun 2019 - Dec 2021
- Built real-time data pipeline processing 1M+ events/day using Kafka and Spark
- Developed React frontend with TypeScript, achieving 95% code coverage
- Designed and implemented RESTful APIs serving mobile and web clients
- Collaborated with product team to define technical requirements

Junior Developer | WebAgency | Mar 2018 - May 2019
- Developed responsive web applications using React and Node.js
- Maintained and improved legacy PHP codebases
- Participated in agile ceremonies and sprint planning

EDUCATION
B.S. Computer Science | University of California, Berkeley | 2018
GPA: 3.7/4.0 | Dean's List

CERTIFICATIONS
- AWS Solutions Architect Associate (2023)
- Kubernetes Administrator (CKA) (2022)
""",
        "parsed_json": {
            "name": "John Doe",
            "email": "john.doe@email.com",
            "phone": "(555) 123-4567",
            "location": "San Francisco, CA",
            "linkedin_url": "linkedin.com/in/johndoe",
            "github_url": "github.com/johndoe",
            "summary": "Experienced software engineer with 5+ years of experience building scalable web applications.",
            "total_years_experience": 5,
            "skills": [
                {"name": "Python", "proficiency": "expert", "years": 5},
                {"name": "JavaScript", "proficiency": "expert", "years": 5},
                {"name": "React", "proficiency": "proficient", "years": 4},
                {"name": "AWS", "proficiency": "proficient", "years": 3},
                {"name": "Docker", "proficiency": "proficient", "years": 3},
                {"name": "PostgreSQL", "proficiency": "proficient", "years": 4}
            ],
            "experience": [
                {
                    "company": "TechCorp Inc.",
                    "role": "Senior Software Engineer",
                    "start_date": "2022-01",
                    "end_date": "Present",
                    "is_current": True
                }
            ]
        }
    },
    {
        "version_name": "Data Scientist",
        "raw_text": """
SARAH JOHNSON
Data Scientist | sarah.johnson@email.com | (555) 987-6543
New York, NY | linkedin.com/in/sarahjohnson

PROFESSIONAL SUMMARY
Data Scientist with 4 years of experience in machine learning, statistical analysis, and 
data visualization. Expert in developing predictive models and extracting insights from 
complex datasets to drive business decisions.

TECHNICAL SKILLS
Languages: Python, R, SQL, Scala
ML/AI: TensorFlow, PyTorch, Scikit-learn, XGBoost, Keras
Data: Pandas, NumPy, Apache Spark, Hadoop
Visualization: Tableau, Power BI, Matplotlib, Seaborn
Cloud: AWS SageMaker, Azure ML, GCP AI Platform
Statistics: Hypothesis Testing, A/B Testing, Time Series Analysis

WORK EXPERIENCE

Senior Data Scientist | FinanceAI Corp | Mar 2022 - Present
- Built fraud detection model reducing false positives by 35% using ensemble methods
- Developed customer churn prediction system saving $2M annually
- Led team of 2 data scientists on NLP project for sentiment analysis
- Created automated reporting dashboards for C-level executives

Data Scientist | DataDriven Inc. | Jul 2020 - Feb 2022
- Implemented recommendation engine increasing user engagement by 25%
- Built ETL pipelines processing 50GB+ of daily data
- Conducted A/B tests for feature launches with statistical rigor
- Presented findings to stakeholders and translated insights to action items

Data Analyst | RetailCo | Jun 2019 - Jun 2020
- Analyzed customer behavior patterns using SQL and Python
- Created Tableau dashboards for sales performance tracking
- Automated weekly reporting saving 10 hours per week

EDUCATION
M.S. Data Science | Columbia University | 2019
B.S. Statistics | NYU | 2017

PUBLICATIONS
- "Ensemble Methods for Fraud Detection" - Journal of ML Research (2023)

CERTIFICATIONS
- AWS Machine Learning Specialty (2023)
- Google Professional Data Engineer (2022)
""",
        "parsed_json": {
            "name": "Sarah Johnson",
            "email": "sarah.johnson@email.com",
            "phone": "(555) 987-6543",
            "location": "New York, NY",
            "linkedin_url": "linkedin.com/in/sarahjohnson",
            "summary": "Data Scientist with 4 years of experience in machine learning and statistical analysis.",
            "total_years_experience": 4,
            "skills": [
                {"name": "Python", "proficiency": "expert", "years": 4},
                {"name": "Machine Learning", "proficiency": "expert", "years": 4},
                {"name": "TensorFlow", "proficiency": "proficient", "years": 3},
                {"name": "SQL", "proficiency": "expert", "years": 4},
                {"name": "AWS SageMaker", "proficiency": "proficient", "years": 2}
            ]
        }
    }
]


# ==============================================================================
# Sample Job Postings (for testing)
# ==============================================================================

SAMPLE_JOBS = [
    {
        "company_name": "TechStartup",
        "role_title": "Senior Backend Engineer",
        "location": "San Francisco, CA",
        "remote_policy": "hybrid",
        "salary_min": 150000,
        "salary_max": 200000,
        "raw_text": """
Senior Backend Engineer - TechStartup

About Us:
TechStartup is a fast-growing company revolutionizing the fintech space. We're looking for 
passionate engineers to join our team.

Role:
We're seeking a Senior Backend Engineer to design and build scalable systems that power 
our financial platform.

Requirements:
- 5+ years of backend development experience
- Strong proficiency in Python or Go
- Experience with microservices architecture
- Solid understanding of SQL and NoSQL databases
- Experience with cloud platforms (AWS preferred)
- Excellent problem-solving skills
- Strong communication abilities

Nice to Have:
- Experience in fintech or financial services
- Knowledge of Kubernetes and Docker
- Experience with event-driven architecture
- Contributions to open source projects

Responsibilities:
- Design and implement scalable backend services
- Lead technical design discussions
- Mentor junior engineers
- Collaborate with product and frontend teams
- Participate in on-call rotation

Benefits:
- Competitive salary + equity
- Health, dental, vision insurance
- 401k with matching
- Unlimited PTO
- Remote work flexibility
""",
        "parsed_json": {
            "company": "TechStartup",
            "role_title": "Senior Backend Engineer",
            "seniority": "senior",
            "location": "San Francisco, CA",
            "remote_policy": "hybrid",
            "must_have": [
                {"text": "5+ years of backend development experience", "type": "must_have", "category": "experience"},
                {"text": "Strong proficiency in Python or Go", "type": "must_have", "category": "technical"},
                {"text": "Experience with microservices architecture", "type": "must_have", "category": "technical"},
                {"text": "Solid understanding of SQL and NoSQL databases", "type": "must_have", "category": "technical"},
                {"text": "Experience with cloud platforms (AWS preferred)", "type": "must_have", "category": "technical"}
            ],
            "nice_to_have": [
                {"text": "Experience in fintech or financial services", "type": "nice_to_have", "category": "domain"},
                {"text": "Knowledge of Kubernetes and Docker", "type": "nice_to_have", "category": "technical"},
                {"text": "Experience with event-driven architecture", "type": "nice_to_have", "category": "technical"}
            ],
            "ats_keywords": ["Python", "Go", "microservices", "AWS", "SQL", "NoSQL", "backend", "scalable"]
        }
    },
    {
        "company_name": "DataCorp",
        "role_title": "Machine Learning Engineer",
        "location": "Remote",
        "remote_policy": "remote",
        "salary_min": 160000,
        "salary_max": 220000,
        "raw_text": """
Machine Learning Engineer - DataCorp

Join our AI team building the future of intelligent systems!

Requirements:
- MS/PhD in Computer Science, Machine Learning, or related field
- 3+ years of experience in ML/AI
- Expert knowledge of Python and ML frameworks (TensorFlow, PyTorch)
- Experience deploying ML models to production
- Strong foundation in statistics and mathematics
- Experience with large-scale data processing
- Excellent communication skills

Nice to Have:
- Experience with LLMs and NLP
- Published research papers
- Open source contributions
- Experience with MLOps tools (MLflow, Kubeflow)

What You'll Do:
- Develop and deploy machine learning models at scale
- Research and implement state-of-the-art ML techniques
- Collaborate with data scientists and engineers
- Build ML pipelines and infrastructure
- Present findings to stakeholders

Benefits:
- Fully remote position
- Top-tier compensation
- Stock options
- Learning budget
- Flexible hours
"""
    }
]


# ==============================================================================
# Sample Interview Questions (for knowledge base)
# ==============================================================================

SAMPLE_SKILL_CATEGORIES = [
    {"name": "Python", "category_type": "technical", "aliases": ["Python3", "python programming"]},
    {"name": "JavaScript", "category_type": "technical", "aliases": ["JS", "ECMAScript"]},
    {"name": "Machine Learning", "category_type": "technical", "aliases": ["ML", "AI", "artificial intelligence"]},
    {"name": "Leadership", "category_type": "soft_skill", "aliases": ["team lead", "management"]},
    {"name": "Communication", "category_type": "soft_skill", "aliases": ["presentation", "public speaking"]},
    {"name": "AWS", "category_type": "tool", "aliases": ["Amazon Web Services"]},
    {"name": "Docker", "category_type": "tool", "aliases": ["containerization"]},
    {"name": "Kubernetes", "category_type": "tool", "aliases": ["K8s", "container orchestration"]},
    {"name": "PostgreSQL", "category_type": "tool", "aliases": ["Postgres", "PSQL"]},
    {"name": "React", "category_type": "tool", "aliases": ["ReactJS", "React.js"]},
]


# ==============================================================================
# Database Operations
# ==============================================================================

def execute_sql(sql: str, parameters: list = None) -> dict:
    """Execute a SQL statement"""
    try:
        kwargs = {
            "resourceArn": cluster_arn,
            "secretArn": secret_arn,
            "database": database,
            "sql": sql,
        }
        if parameters:
            kwargs["parameters"] = parameters
        return client.execute_statement(**kwargs)
    except ClientError as e:
        print(f"    ❌ Error: {e.response['Error']['Message'][:200]}")
        return None


def create_test_user() -> str:
    """Create a test user and return their ID"""
    print("\n👤 Creating test user...")
    
    # Check if test user exists
    sql = "SELECT id FROM user_profiles WHERE clerk_user_id = :clerk_id"
    params = [{"name": "clerk_id", "value": {"stringValue": "test_user_001"}}]
    result = execute_sql(sql, params)
    
    if result and result.get("records"):
        user_id = result["records"][0][0]["stringValue"]
        print(f"    ✅ Test user already exists: {user_id}")
        return user_id
    
    # Create new test user
    sql = """
        INSERT INTO user_profiles (clerk_user_id, full_name, email, target_roles, target_locations, years_of_experience)
        VALUES (:clerk_id, :name, :email, :roles::jsonb, :locations::jsonb, :years)
        RETURNING id
    """
    params = [
        {"name": "clerk_id", "value": {"stringValue": "test_user_001"}},
        {"name": "name", "value": {"stringValue": "Test User"}},
        {"name": "email", "value": {"stringValue": "test@example.com"}},
        {"name": "roles", "value": {"stringValue": '["Software Engineer", "Backend Developer"]'}},
        {"name": "locations", "value": {"stringValue": '["San Francisco", "Remote"]'}},
        {"name": "years", "value": {"longValue": 5}},
    ]
    result = execute_sql(sql, params)
    
    if result and result.get("records"):
        user_id = result["records"][0][0]["stringValue"]
        print(f"    ✅ Created test user: {user_id}")
        return user_id
    
    print("    ❌ Failed to create test user")
    return None


def seed_cv_versions(user_id: str):
    """Seed sample CV versions"""
    print("\n📄 Seeding CV versions...")
    
    for i, cv in enumerate(SAMPLE_CVS):
        sql = """
            INSERT INTO cv_versions (user_id, raw_text, parsed_json, version_name, is_primary)
            VALUES (:user_id::uuid, :raw_text, :parsed_json::jsonb, :version_name, :is_primary)
            ON CONFLICT DO NOTHING
            RETURNING id
        """
        params = [
            {"name": "user_id", "value": {"stringValue": user_id}},
            {"name": "raw_text", "value": {"stringValue": cv["raw_text"]}},
            {"name": "parsed_json", "value": {"stringValue": json.dumps(cv["parsed_json"])}},
            {"name": "version_name", "value": {"stringValue": cv["version_name"]}},
            {"name": "is_primary", "value": {"booleanValue": i == 0}},  # First one is primary
        ]
        result = execute_sql(sql, params)
        if result:
            print(f"    ✅ {cv['version_name']}")
        else:
            print(f"    ⏭️  {cv['version_name']} (already exists or error)")


def seed_job_postings(user_id: str):
    """Seed sample job postings"""
    print("\n💼 Seeding job postings...")
    
    for job in SAMPLE_JOBS:
        sql = """
            INSERT INTO job_postings (user_id, company_name, role_title, raw_text, parsed_json, 
                                      location, remote_policy, salary_min, salary_max)
            VALUES (:user_id::uuid, :company, :role, :raw_text, :parsed_json::jsonb,
                    :location, :remote, :salary_min, :salary_max)
            RETURNING id
        """
        params = [
            {"name": "user_id", "value": {"stringValue": user_id}},
            {"name": "company", "value": {"stringValue": job["company_name"]}},
            {"name": "role", "value": {"stringValue": job["role_title"]}},
            {"name": "raw_text", "value": {"stringValue": job["raw_text"]}},
            {"name": "parsed_json", "value": {"stringValue": json.dumps(job.get("parsed_json", {}))}},
            {"name": "location", "value": {"stringValue": job["location"]}},
            {"name": "remote", "value": {"stringValue": job["remote_policy"]}},
            {"name": "salary_min", "value": {"longValue": job.get("salary_min", 0)}},
            {"name": "salary_max", "value": {"longValue": job.get("salary_max", 0)}},
        ]
        result = execute_sql(sql, params)
        if result:
            print(f"    ✅ {job['company_name']} - {job['role_title']}")
        else:
            print(f"    ❌ Failed: {job['company_name']}")


def seed_skill_categories():
    """Seed skill categories reference data"""
    print("\n🏷️  Seeding skill categories...")
    
    for skill in SAMPLE_SKILL_CATEGORIES:
        sql = """
            INSERT INTO skill_categories (name, category_type, aliases)
            VALUES (:name, :type, :aliases::jsonb)
            ON CONFLICT (name) DO UPDATE SET
                category_type = EXCLUDED.category_type,
                aliases = EXCLUDED.aliases
        """
        params = [
            {"name": "name", "value": {"stringValue": skill["name"]}},
            {"name": "type", "value": {"stringValue": skill["category_type"]}},
            {"name": "aliases", "value": {"stringValue": json.dumps(skill["aliases"])}},
        ]
        result = execute_sql(sql, params)
        if result:
            print(f"    ✅ {skill['name']} ({skill['category_type']})")


def verify_data():
    """Verify seeded data"""
    print("\n🔍 Verifying data...")
    
    tables = [
        ("user_profiles", "User profiles"),
        ("cv_versions", "CV versions"),
        ("job_postings", "Job postings"),
        ("skill_categories", "Skill categories"),
    ]
    
    for table, name in tables:
        sql = f"SELECT COUNT(*) as count FROM {table}"
        result = execute_sql(sql)
        if result and result.get("records"):
            count = result["records"][0][0]["longValue"]
            print(f"    {name}: {count} records")


def main():
    print("🚀 CareerAssist Seed Data")
    print("=" * 50)
    print(f"Database: {database}")
    print(f"Region: {region}")
    
    # Create test user
    user_id = create_test_user()
    if not user_id:
        print("\n❌ Cannot proceed without test user")
        exit(1)
    
    # Seed data
    seed_cv_versions(user_id)
    seed_job_postings(user_id)
    seed_skill_categories()
    
    # Verify
    verify_data()
    
    print("\n" + "=" * 50)
    print("✅ Seed data loaded successfully!")
    print("\n📝 Next steps:")
    print("1. Test the database operations: uv run verify_database.py")
    print("2. Run agents locally: uv run test_simple.py")


if __name__ == "__main__":
    main()
