#!/usr/bin/env python3
"""
Database Reset Script for CareerAssist
Drops all tables, recreates schema, and optionally loads seed data
"""

import sys
import argparse
from pathlib import Path
from src.client import DataAPIClient
from src.models import Database
from src.schemas import UserProfileCreate, CVVersionCreate, JobPostingCreate


def drop_all_tables(db: DataAPIClient):
    """Drop all CareerAssist tables in correct order (respecting foreign keys)"""
    print("🗑️  Dropping existing tables...")
    
    # Order matters due to foreign key constraints
    # Drop in reverse order of dependencies
    tables_to_drop = [
        # Child tables first
        'cv_rewrites',
        'interview_sessions',
        'job_applications',
        'gap_analyses',
        'cv_versions',
        'job_postings',
        'jobs',
        'skill_categories',
        'user_profiles',
        # Legacy Alex tables (if they exist)
        'positions',
        'accounts',
        'instruments',
        'users'
    ]
    
    # Drop views first
    views_to_drop = [
        'application_pipeline_stats',
        'recent_gap_analyses'
    ]
    
    for view in views_to_drop:
        try:
            db.execute(f"DROP VIEW IF EXISTS {view} CASCADE")
            print(f"   ✅ Dropped view {view}")
        except Exception as e:
            pass  # Views might not exist
    
    for table in tables_to_drop:
        try:
            db.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
            print(f"   ✅ Dropped {table}")
        except Exception as e:
            print(f"   ⚠️  Error dropping {table}: {e}")
    
    # Also drop the function
    try:
        db.execute("DROP FUNCTION IF EXISTS update_updated_at_column() CASCADE")
        print(f"   ✅ Dropped update_updated_at_column function")
    except Exception as e:
        print(f"   ⚠️  Error dropping function: {e}")


def create_test_user_and_data(db_models: Database):
    """Create test user with sample CV and job postings"""
    print("\n👤 Creating test user and sample data...")
    
    # Check if test user exists
    existing = db_models.user_profiles.find_by_clerk_id('test_user_001')
    if existing:
        print("   ℹ️  Test user already exists")
        user_id = existing['id']
    else:
        # Create new test user
        profile = UserProfileCreate(
            clerk_user_id='test_user_001',
            full_name='Test User',
            email='test@example.com',
            target_roles=['Software Engineer', 'Backend Developer'],
            target_locations=['San Francisco', 'Remote'],
            years_of_experience=5
        )
        user_id = db_models.user_profiles.create_user(profile)
        print(f"   ✅ Created test user: {user_id}")
    
    # Check if CVs exist
    existing_cvs = db_models.cv_versions.find_by_user(user_id)
    if existing_cvs:
        print(f"   ℹ️  User already has {len(existing_cvs)} CV versions")
    else:
        # Create sample CV
        cv = CVVersionCreate(
            raw_text="""
JOHN DOE
Software Engineer | john.doe@email.com | (555) 123-4567
San Francisco, CA | linkedin.com/in/johndoe | github.com/johndoe

PROFESSIONAL SUMMARY
Experienced software engineer with 5+ years of experience building scalable web applications. 
Proficient in Python, JavaScript, and cloud technologies.

TECHNICAL SKILLS
Languages: Python, JavaScript, TypeScript, Java, SQL
Frameworks: React, Node.js, Django, FastAPI
Cloud: AWS (EC2, Lambda, S3, RDS), Docker, Kubernetes
Databases: PostgreSQL, MongoDB, Redis

WORK EXPERIENCE
Senior Software Engineer | TechCorp Inc. | Jan 2022 - Present
- Led development of microservices architecture serving 500K+ daily users
- Reduced API response time by 40% through Redis caching implementation
- Mentored team of 3 junior developers

Software Engineer | StartupXYZ | Jun 2019 - Dec 2021
- Built real-time data pipeline processing 1M+ events/day
- Developed React frontend with TypeScript, 95% code coverage

EDUCATION
B.S. Computer Science | University of California, Berkeley | 2018

CERTIFICATIONS
- AWS Solutions Architect Associate (2023)
- Kubernetes Administrator (CKA) (2022)
""",
            version_name="Software Engineer Resume",
            is_primary=True
        )
        cv_id = db_models.cv_versions.create_cv_version(user_id, cv)
        print(f"   ✅ Created sample CV: {cv_id}")
    
    # Check if job postings exist
    existing_jobs = db_models.job_postings.find_by_user(user_id)
    if existing_jobs:
        print(f"   ℹ️  User already has {len(existing_jobs)} job postings")
    else:
        # Create sample job posting
        job = JobPostingCreate(
            raw_text="""
Senior Backend Engineer - TechStartup

About Us:
TechStartup is a fast-growing company revolutionizing the fintech space.

Requirements:
- 5+ years of backend development experience
- Strong proficiency in Python or Go
- Experience with microservices architecture
- Solid understanding of SQL and NoSQL databases
- Experience with cloud platforms (AWS preferred)

Responsibilities:
- Design and implement scalable backend services
- Lead technical design discussions
- Mentor junior engineers

Benefits:
- Competitive salary + equity
- Health, dental, vision insurance
- Unlimited PTO
""",
            company_name="TechStartup",
            role_title="Senior Backend Engineer",
            location="San Francisco, CA",
            remote_policy="hybrid",
            salary_min=150000,
            salary_max=200000
        )
        job_id = db_models.job_postings.create_job_posting(user_id, job)
        print(f"   ✅ Created sample job posting: {job_id}")


def main():
    parser = argparse.ArgumentParser(description='Reset CareerAssist database')
    parser.add_argument('--with-test-data', action='store_true',
                       help='Create test user with sample CV and job posting')
    parser.add_argument('--skip-drop', action='store_true',
                       help='Skip dropping tables (just reload data)')
    parser.add_argument('--seed', action='store_true',
                       help='Run seed data script after migrations')
    args = parser.parse_args()
    
    print("🚀 CareerAssist Database Reset Script")
    print("=" * 50)
    
    # Initialize database
    db = DataAPIClient()
    db_models = Database()
    
    if not args.skip_drop:
        # Drop all tables
        drop_all_tables(db)
        
        # Run migrations
        print("\n📝 Running migrations...")
        import subprocess
        result = subprocess.run(
            ['uv', 'run', 'run_migrations.py'], 
            capture_output=True, 
            text=True
        )
        
        if result.returncode != 0:
            print("❌ Migration failed!")
            print(result.stderr)
            sys.exit(1)
        else:
            print("✅ Migrations completed")
    
    # Load seed data if requested
    if args.seed:
        print("\n🌱 Loading seed data...")
        import subprocess
        result = subprocess.run(
            ['uv', 'run', 'seed_career_data.py'], 
            capture_output=True, 
            text=True
        )
        
        if result.returncode != 0:
            print("❌ Seed data failed!")
            print(result.stderr)
            sys.exit(1)
        else:
            print("✅ Seed data loaded")
    
    # Create test data if requested
    if args.with_test_data:
        create_test_user_and_data(db_models)
    
    # Final verification
    print("\n🔍 Final verification...")
    
    # Count records
    tables = [
        'user_profiles', 'cv_versions', 'job_postings', 
        'gap_analyses', 'cv_rewrites', 'job_applications',
        'interview_sessions', 'jobs', 'skill_categories'
    ]
    
    for table in tables:
        try:
            result = db.query(f"SELECT COUNT(*) as count FROM {table}")
            count = result[0]['count'] if result else 0
            print(f"   • {table:<25} {count:>5} records")
        except Exception as e:
            print(f"   • {table:<25} ⚠️  Error: {str(e)[:30]}")
    
    print("\n" + "=" * 50)
    print("✅ Database reset complete!")
    
    if args.with_test_data:
        print("\n📝 Test data created:")
        print("   • User ID: test_user_001")
        print("   • 1 CV version (Software Engineer Resume)")
        print("   • 1 Job posting (Senior Backend Engineer)")
        print("\n📝 Next steps:")
        print("1. Verify database: uv run verify_database.py")
        print("2. Test agents locally: uv run test_simple.py")


if __name__ == "__main__":
    main()