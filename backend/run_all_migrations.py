
import os
import sys
import boto3
from dotenv import load_dotenv

load_dotenv(override=True)

AURORA_CLUSTER_ARN = os.getenv("AURORA_CLUSTER_ARN")
AURORA_SECRET_ARN = os.getenv("AURORA_SECRET_ARN")
DATABASE_NAME = os.getenv("DATABASE_NAME", "career")
AWS_REGION = os.getenv("DEFAULT_AWS_REGION", "us-east-1")

rds = boto3.client('rds-data', region_name=AWS_REGION)

def execute_sql(sql):
    try:
        response = rds.execute_statement(
            resourceArn=AURORA_CLUSTER_ARN,
            secretArn=AURORA_SECRET_ARN,
            database=DATABASE_NAME,
            sql=sql
        )
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def run_migration_file(filename):
    print(f"Running migration: {filename}")
    try:
        with open(filename, 'r') as f:
            sql = f.read()
            
        # Split into statements (rough approximation, splitting by ;)
        statements = [s.strip() for s in sql.split(';') if s.strip()]
        
        for stmt in statements:
            if not execute_sql(stmt):
                print(f"❌ Statement failed in {filename}")
                return False
                
        print(f"✅ Migration {filename} completed successfully")
        return True
    except Exception as e:
        print(f"❌ Failed to read/transact {filename}: {e}")
        return False

if __name__ == "__main__":
    # Create trigger function first
    trigger_sql = """
    CREATE OR REPLACE FUNCTION update_updated_at_column()
    RETURNS TRIGGER AS $$
    BEGIN
        NEW.updated_at = NOW();
        RETURN NEW;
    END;
    $$ language 'plpgsql';
    """
    if not execute_sql(trigger_sql):
        print("❌ Failed to create trigger function")
        # Continue anyway, might already exist or be error in this script
    
    migrations = [
        "database/migrations/004_research_findings.sql",
        "database/migrations/005_discovered_jobs.sql"
    ]
    
    
    for migration in migrations:
        if not run_migration_file(migration):
            sys.exit(1)
            
    print("\n✅ All migrations applied successfully!")
