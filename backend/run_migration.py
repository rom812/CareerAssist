import os
import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).parent.absolute()
sys.path.append(str(backend_dir))

from database.src import Database

def run_migration():
    """Run migration to add missing columns."""
    print("Connecting to database...")
    db = Database()
    
    migration_file = backend_dir / "database" / "migrations" / "003_add_missing_payloads.sql"
    if not migration_file.exists():
        print(f"Error: Migration file not found at {migration_file}")
        return
        
    print(f"Reading migration file: {migration_file.name}")
    sql = migration_file.read_text()
    
    print("Executing migration steps...")
    statements = [s.strip() for s in sql.split(';') if s.strip()]
    
    for stmt in statements:
        try:
            print(f"Running: {stmt[:50]}...")
            db.client.execute(stmt)
        except Exception as e:
            print(f"❌ Statement failed: {e}")
            sys.exit(1)
            
    print("✅ Migration executed successfully successfully!")

if __name__ == "__main__":
    run_migration()
