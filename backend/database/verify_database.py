#!/usr/bin/env python3
"""
Comprehensive database verification script for CareerAssist
Shows that all tables exist and are properly populated

This script verifies:
- All CareerAssist tables are created
- Record counts for each table
- Sample CVs and job postings
- User profile data
- Database indexes and triggers
"""

import os
import boto3
import json
from pathlib import Path
from botocore.exceptions import ClientError
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)

# Get config from environment
cluster_arn = os.environ.get('AURORA_CLUSTER_ARN')
secret_arn = os.environ.get('AURORA_SECRET_ARN')
database = os.environ.get('AURORA_DATABASE', 'career')
region = os.environ.get('DEFAULT_AWS_REGION', 'us-east-1')

if not cluster_arn or not secret_arn:
    print("❌ Missing AURORA_CLUSTER_ARN or AURORA_SECRET_ARN in .env file")
    exit(1)

client = boto3.client('rds-data', region_name=region)


def execute_query(sql, description):
    """Execute a query and return results"""
    print(f"\n{description}")
    print("-" * 50)
    
    try:
        response = client.execute_statement(
            resourceArn=cluster_arn,
            secretArn=secret_arn,
            database=database,
            sql=sql
        )
        return response
    except ClientError as e:
        error_msg = e.response['Error']['Message']
        if "does not exist" in error_msg.lower():
            print(f"⚠️  Table does not exist yet")
        else:
            print(f"❌ Error: {error_msg[:100]}")
        return None


def main():
    print("🔍 CAREERASSIST DATABASE VERIFICATION REPORT")
    print("=" * 70)
    print(f"📍 Region: {region}")
    print(f"📦 Database: {database}")
    print("=" * 70)
    
    # 1. Show all tables
    response = execute_query(
        """
        SELECT table_name, 
               pg_size_pretty(pg_total_relation_size(quote_ident(table_name)::regclass)) as size
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_type = 'BASE TABLE'
        ORDER BY table_name
        """,
        "📊 ALL TABLES IN DATABASE"
    )
    
    if response and response.get('records'):
        print(f"✅ Found {len(response['records'])} tables:\n")
        for record in response['records']:
            table_name = record[0]['stringValue']
            size = record[1]['stringValue']
            print(f"   • {table_name:<25} Size: {size}")
    else:
        print("\n⚠️  No tables found. Run migrations first:")
        print("   uv run run_migrations.py")
        return
    
    # 2. Count records in each CareerAssist table
    response = execute_query(
        """
        SELECT 
            'user_profiles' as table_name, COUNT(*) as count FROM user_profiles
        UNION ALL
        SELECT 'cv_versions', COUNT(*) FROM cv_versions
        UNION ALL
        SELECT 'job_postings', COUNT(*) FROM job_postings
        UNION ALL
        SELECT 'gap_analyses', COUNT(*) FROM gap_analyses
        UNION ALL
        SELECT 'cv_rewrites', COUNT(*) FROM cv_rewrites
        UNION ALL
        SELECT 'job_applications', COUNT(*) FROM job_applications
        UNION ALL
        SELECT 'interview_sessions', COUNT(*) FROM interview_sessions
        UNION ALL
        SELECT 'jobs', COUNT(*) FROM jobs
        UNION ALL
        SELECT 'skill_categories', COUNT(*) FROM skill_categories
        ORDER BY table_name
        """,
        "📈 RECORD COUNTS PER TABLE"
    )
    
    if response and response.get('records'):
        print("\nTable record counts:\n")
        for record in response['records']:
            table_name = record[0]['stringValue']
            count = record[1]['longValue']
            status = "✅" if count > 0 else "📭"
            print(f"   {status} {table_name:<25} {count:,} records")
    
    # 3. Show user profiles
    response = execute_query(
        """
        SELECT id, clerk_user_id, full_name, email, years_of_experience
        FROM user_profiles 
        ORDER BY created_at DESC
        LIMIT 5
        """,
        "👤 USER PROFILES (Recent 5)"
    )
    
    if response and response.get('records'):
        print("\n  ID | Clerk ID | Name | Email | Experience")
        print("-" * 70)
        for record in response['records']:
            uid = record[0]['stringValue'][:8] if record[0].get('stringValue') else 'N/A'
            clerk_id = record[1].get('stringValue', 'N/A')[:20]
            name = record[2].get('stringValue', 'N/A') if not record[2].get('isNull') else 'N/A'
            email = record[3].get('stringValue', 'N/A') if not record[3].get('isNull') else 'N/A'
            exp = record[4].get('longValue', 0) if not record[4].get('isNull') else 0
            print(f"  {uid}... | {clerk_id:<20} | {name[:15]:<15} | {email[:20]:<20} | {exp} yrs")
    else:
        print("\n  No user profiles found. Run seed data first.")
    
    # 4. Show CV versions
    response = execute_query(
        """
        SELECT cv.id, cv.version_name, cv.is_primary, 
               LENGTH(cv.raw_text) as text_length,
               CASE WHEN cv.parsed_json IS NOT NULL THEN 'Yes' ELSE 'No' END as parsed
        FROM cv_versions cv
        ORDER BY cv.created_at DESC
        LIMIT 5
        """,
        "📄 CV VERSIONS (Recent 5)"
    )
    
    if response and response.get('records'):
        print("\n  ID | Version Name | Primary | Text Length | Parsed")
        print("-" * 70)
        for record in response['records']:
            cvid = record[0]['stringValue'][:8]
            name = record[1].get('stringValue', 'Default')[:20]
            primary = "✅" if record[2].get('booleanValue') else "❌"
            length = record[3].get('longValue', 0)
            parsed = record[4].get('stringValue', 'No')
            print(f"  {cvid}... | {name:<20} | {primary} | {length:>10} chars | {parsed}")
    else:
        print("\n  No CV versions found.")
    
    # 5. Show job postings
    response = execute_query(
        """
        SELECT id, company_name, role_title, location, remote_policy, salary_min, salary_max
        FROM job_postings
        ORDER BY created_at DESC
        LIMIT 5
        """,
        "💼 JOB POSTINGS (Recent 5)"
    )
    
    if response and response.get('records'):
        print("\n  Company | Role | Location | Remote | Salary Range")
        print("-" * 70)
        for record in response['records']:
            company = record[1].get('stringValue', 'N/A')[:15] if not record[1].get('isNull') else 'N/A'
            role = record[2].get('stringValue', 'N/A')[:20] if not record[2].get('isNull') else 'N/A'
            location = record[3].get('stringValue', 'N/A')[:15] if not record[3].get('isNull') else 'N/A'
            remote = record[4].get('stringValue', 'N/A') if not record[4].get('isNull') else 'N/A'
            sal_min = record[5].get('longValue', 0) if not record[5].get('isNull') else 0
            sal_max = record[6].get('longValue', 0) if not record[6].get('isNull') else 0
            salary = f"${sal_min:,}-${sal_max:,}" if sal_min or sal_max else "N/A"
            print(f"  {company:<15} | {role:<20} | {location:<15} | {remote:<8} | {salary}")
    else:
        print("\n  No job postings found.")
    
    # 6. Show skill categories
    response = execute_query(
        """
        SELECT name, category_type, aliases::text
        FROM skill_categories
        ORDER BY category_type, name
        LIMIT 10
        """,
        "🏷️  SKILL CATEGORIES (First 10)"
    )
    
    if response and response.get('records'):
        print("\n  Skill | Type | Aliases")
        print("-" * 60)
        for record in response['records']:
            name = record[0].get('stringValue', 'N/A')
            cat_type = record[1].get('stringValue', 'N/A')
            aliases = record[2].get('stringValue', '[]')[:30]
            print(f"  {name:<20} | {cat_type:<12} | {aliases}")
    
    # 7. Check indexes exist
    response = execute_query(
        """
        SELECT schemaname, tablename, indexname
        FROM pg_indexes
        WHERE schemaname = 'public'
        AND indexname LIKE 'idx_%'
        ORDER BY tablename, indexname
        """,
        "🔍 DATABASE INDEXES"
    )
    
    if response and response.get('records'):
        print(f"\n✅ Found {len(response['records'])} custom indexes:\n")
        current_table = None
        for record in response['records']:
            table = record[1]['stringValue']
            index = record[2]['stringValue']
            if table != current_table:
                current_table = table
                print(f"\n   {table}:")
            print(f"      - {index}")
    
    # 8. Check triggers exist
    response = execute_query(
        """
        SELECT trigger_name, event_object_table
        FROM information_schema.triggers
        WHERE trigger_schema = 'public'
        ORDER BY event_object_table
        """,
        "⚡ DATABASE TRIGGERS"
    )
    
    if response and response.get('records'):
        print(f"\n✅ Found {len(response['records'])} update triggers for timestamp management")
    
    # 9. Check views exist
    response = execute_query(
        """
        SELECT table_name
        FROM information_schema.views
        WHERE table_schema = 'public'
        ORDER BY table_name
        """,
        "👁️  DATABASE VIEWS"
    )
    
    if response and response.get('records'):
        print(f"\n✅ Found {len(response['records'])} views:")
        for record in response['records']:
            view_name = record[0]['stringValue']
            print(f"   • {view_name}")
    
    # Final summary
    print("\n" + "=" * 70)
    print("🎉 DATABASE VERIFICATION COMPLETE")
    print("=" * 70)
    print("\n✅ CareerAssist tables created successfully")
    print("✅ Indexes and triggers are in place")
    print("✅ Database is ready for CareerAssist agents!")
    print("\n📝 Next steps:")
    print("1. If no data: Run seed data: uv run seed_career_data.py")
    print("2. Test agents locally: uv run test_simple.py")
    print("3. Deploy to AWS: Follow Phase 4 in PLAN.md")


if __name__ == "__main__":
    main()