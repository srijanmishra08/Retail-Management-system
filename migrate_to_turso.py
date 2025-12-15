"""
Migration script to transfer data from local SQLite to Turso cloud database.

Usage:
1. Set environment variables:
   export TURSO_DATABASE_URL="libsql://your-db-name.turso.io"
   export TURSO_AUTH_TOKEN="your-auth-token"

2. Run: python migrate_to_turso.py
"""

import sqlite3
import os

def migrate_data():
    # Check for Turso credentials
    turso_url = os.environ.get('TURSO_DATABASE_URL')
    turso_token = os.environ.get('TURSO_AUTH_TOKEN')
    
    if not turso_url or not turso_token:
        print("❌ Error: Please set TURSO_DATABASE_URL and TURSO_AUTH_TOKEN environment variables")
        print("\nExample:")
        print('  export TURSO_DATABASE_URL="libsql://fims-production-yourusername.turso.io"')
        print('  export TURSO_AUTH_TOKEN="your-auth-token-here"')
        return False
    
    # Try to import libsql
    try:
        import libsql_experimental as libsql
    except ImportError:
        print("❌ Error: libsql-experimental package not installed")
        print("Run: pip install libsql-experimental")
        return False
    
    # Check if local database exists
    if not os.path.exists('fims.db'):
        print("❌ Error: Local database 'fims.db' not found")
        return False
    
    print("🔄 Starting migration from local SQLite to Turso cloud...")
    
    # Connect to local SQLite
    local_conn = sqlite3.connect('fims.db')
    local_cursor = local_conn.cursor()
    
    # Connect to Turso cloud
    try:
        cloud_conn = libsql.connect(turso_url, auth_token=turso_token)
        cloud_cursor = cloud_conn.cursor()
        print("✅ Connected to Turso cloud database")
    except Exception as e:
        print(f"❌ Error connecting to Turso: {e}")
        return False
    
    # Get list of tables from local database
    local_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    tables = [row[0] for row in local_cursor.fetchall()]
    
    print(f"\n📋 Found {len(tables)} tables to migrate: {', '.join(tables)}\n")
    
    # First, create all tables in cloud database by running initialize_database
    print("📝 Creating tables in cloud database...")
    
    # Get schema for each table and create in cloud
    for table in tables:
        local_cursor.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{table}'")
        create_sql = local_cursor.fetchone()[0]
        
        if create_sql:
            try:
                # Drop table if exists and recreate
                cloud_cursor.execute(f"DROP TABLE IF EXISTS {table}")
                cloud_cursor.execute(create_sql)
                cloud_conn.commit()
                print(f"  ✅ Created table: {table}")
            except Exception as e:
                print(f"  ⚠️ Error creating {table}: {e}")
    
    print("\n📦 Migrating data...")
    
    total_rows = 0
    
    for table in tables:
        try:
            # Get all data from local table
            local_cursor.execute(f"SELECT * FROM {table}")
            rows = local_cursor.fetchall()
            
            if rows:
                # Get column names
                local_cursor.execute(f"PRAGMA table_info({table})")
                columns = [col[1] for col in local_cursor.fetchall()]
                placeholders = ','.join(['?' for _ in columns])
                column_names = ','.join(columns)
                
                # Insert into cloud database
                success_count = 0
                for row in rows:
                    try:
                        cloud_cursor.execute(
                            f"INSERT INTO {table} ({column_names}) VALUES ({placeholders})", 
                            row
                        )
                        success_count += 1
                    except Exception as e:
                        print(f"    ⚠️ Error inserting row into {table}: {e}")
                
                cloud_conn.commit()
                total_rows += success_count
                print(f"  ✅ {table}: {success_count}/{len(rows)} rows migrated")
            else:
                print(f"  ⏭️  {table}: No data to migrate")
                
        except Exception as e:
            print(f"  ❌ Error migrating {table}: {e}")
    
    local_conn.close()
    
    print(f"\n🎉 Migration complete! Total rows migrated: {total_rows}")
    print("\n📌 Next steps:")
    print("1. Set environment variables on Render:")
    print(f"   TURSO_DATABASE_URL = {turso_url}")
    print("   TURSO_AUTH_TOKEN = [your token]")
    print("2. Deploy your application")
    print("3. Your data will now persist across deployments!")
    
    return True


def verify_migration():
    """Verify that data was migrated correctly"""
    turso_url = os.environ.get('TURSO_DATABASE_URL')
    turso_token = os.environ.get('TURSO_AUTH_TOKEN')
    
    if not turso_url or not turso_token:
        print("❌ Set TURSO_DATABASE_URL and TURSO_AUTH_TOKEN to verify")
        return
    
    try:
        import libsql_experimental as libsql
        cloud_conn = libsql.connect(turso_url, auth_token=turso_token)
        cloud_cursor = cloud_conn.cursor()
        
        print("\n📊 Cloud Database Status:")
        
        # Get all tables
        cloud_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        tables = [row[0] for row in cloud_cursor.fetchall()]
        
        for table in tables:
            cloud_cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cloud_cursor.fetchone()[0]
            print(f"  {table}: {count} rows")
        
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == '--verify':
        verify_migration()
    else:
        migrate_data()
