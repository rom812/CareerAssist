#!/usr/bin/env python3
"""
Migration runner for CareerAssist database
Supports running either the old Alex schema (001) or the new Career schema (002)
"""

import os
import sys
import argparse
import boto3
from pathlib import Path
from botocore.exceptions import ClientError
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)

# Get config from environment
cluster_arn = os.environ.get("AURORA_CLUSTER_ARN")
secret_arn = os.environ.get("AURORA_SECRET_ARN")
database = os.environ.get("AURORA_DATABASE", "career")
region = os.environ.get("DEFAULT_AWS_REGION", "us-east-1")

if not cluster_arn or not secret_arn:
    raise ValueError("Missing AURORA_CLUSTER_ARN or AURORA_SECRET_ARN in environment variables")

client = boto3.client("rds-data", region_name=region)


def execute_statement(sql: str) -> dict:
    """Execute a single SQL statement"""
    try:
        return client.execute_statement(
            resourceArn=cluster_arn,
            secretArn=secret_arn,
            database=database,
            sql=sql
        )
    except ClientError as e:
        raise


def run_migration_file(file_path: Path):
    """Run a migration SQL file by parsing and executing statements"""
    print(f"\n📄 Running migration: {file_path.name}")
    print("-" * 50)
    
    with open(file_path) as f:
        content = f.read()
    
    # Parse SQL file into individual statements
    # This is a simple parser - handles basic SQL files
    statements = []
    current_statement = []
    in_function = False
    
    for line in content.split('\n'):
        stripped = line.strip()
        
        # Skip comments and empty lines (unless in a statement)
        if not current_statement and (stripped.startswith('--') or not stripped):
            continue
        
        current_statement.append(line)
        
        # Track if we're inside a function/trigger block
        if 'CREATE OR REPLACE FUNCTION' in line.upper() or 'CREATE FUNCTION' in line.upper():
            in_function = True
        
        # Check for statement terminator
        if stripped.endswith(';'):
            if in_function:
                # For functions, we need to wait for the $$ delimiter
                if '$$;' in stripped or "$$;" in stripped:
                    in_function = False
                    statements.append('\n'.join(current_statement))
                    current_statement = []
            else:
                statements.append('\n'.join(current_statement))
                current_statement = []
    
    # Execute each statement
    success_count = 0
    error_count = 0
    
    for i, stmt in enumerate(statements, 1):
        stmt = stmt.strip()
        if not stmt:
            continue
        
        # Get statement type for display
        stmt_type = "statement"
        if "CREATE TABLE" in stmt.upper():
            stmt_type = "table"
        elif "CREATE INDEX" in stmt.upper():
            stmt_type = "index"
        elif "CREATE TRIGGER" in stmt.upper():
            stmt_type = "trigger"
        elif "CREATE FUNCTION" in stmt.upper() or "CREATE OR REPLACE FUNCTION" in stmt.upper():
            stmt_type = "function"
        elif "CREATE EXTENSION" in stmt.upper():
            stmt_type = "extension"
        elif "CREATE VIEW" in stmt.upper() or "CREATE OR REPLACE VIEW" in stmt.upper():
            stmt_type = "view"
        elif "DROP TABLE" in stmt.upper():
            stmt_type = "drop table"
        elif "DROP TRIGGER" in stmt.upper():
            stmt_type = "drop trigger"
        
        # First non-empty line for display
        first_line = next((l for l in stmt.split("\n") if l.strip()), "")[:60]
        print(f"\n[{i}/{len(statements)}] Running {stmt_type}...")
        print(f"    {first_line}...")
        
        try:
            execute_statement(stmt)
            print(f"    ✅ Success")
            success_count += 1
        except ClientError as e:
            error_msg = e.response["Error"]["Message"]
            if "already exists" in error_msg.lower():
                print(f"    ⚠️  Already exists (skipping)")
                success_count += 1
            elif "does not exist" in error_msg.lower() and "DROP" in stmt.upper():
                print(f"    ⚠️  Does not exist (skipping)")
                success_count += 1
            else:
                print(f"    ❌ Error: {error_msg[:150]}")
                error_count += 1
    
    return success_count, error_count


def main():
    parser = argparse.ArgumentParser(description='Run CareerAssist database migrations')
    parser.add_argument('--schema', choices=['alex', 'career'], default='career',
                       help='Which schema to run (alex = 001, career = 002)')
    parser.add_argument('--all', action='store_true',
                       help='Run all migrations in order')
    parser.add_argument('--file', type=str,
                       help='Run a specific migration file')
    args = parser.parse_args()
    
    print("🚀 CareerAssist Database Migration Runner")
    print("=" * 50)
    print(f"📍 Database: {database}")
    print(f"📍 Region: {region}")
    
    migrations_dir = Path(__file__).parent / "migrations"
    
    if args.file:
        # Run specific file
        file_path = Path(args.file)
        if not file_path.exists():
            file_path = migrations_dir / args.file
        if not file_path.exists():
            print(f"❌ Migration file not found: {args.file}")
            sys.exit(1)
        files_to_run = [file_path]
        
    elif args.all:
        # Run all migrations in order
        files_to_run = sorted(migrations_dir.glob("*.sql"))
        
    elif args.schema == 'alex':
        # Run old Alex schema
        files_to_run = [migrations_dir / "001_schema.sql"]
        
    else:
        # Run new Career schema (default)
        files_to_run = [migrations_dir / "002_career_schema.sql"]
    
    total_success = 0
    total_errors = 0
    
    for file_path in files_to_run:
        if not file_path.exists():
            print(f"⚠️  Migration file not found: {file_path}")
            continue
        
        success, errors = run_migration_file(file_path)
        total_success += success
        total_errors += errors
    
    print("\n" + "=" * 50)
    print(f"Migration complete: {total_success} successful, {total_errors} errors")
    
    if total_errors == 0:
        print("\n✅ All migrations completed successfully!")
        print("\n📝 Next steps:")
        print("1. Load seed data: uv run seed_career_data.py")
        print("2. Verify database: uv run verify_database.py")
    else:
        print(f"\n⚠️  Some statements failed. Check errors above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
