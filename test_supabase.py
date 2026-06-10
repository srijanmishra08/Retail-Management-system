#!/usr/bin/env python3
"""
Quick Supabase PostgreSQL Connection Test
"""
import os
from dotenv import load_dotenv
load_dotenv()

import database_pg as database

print("=" * 70)
print("SUPABASE POSTGRESQL CONNECTION TEST".center(70))
print("=" * 70)

try:
    # Test 1: Database connection
    print("\n✓ Testing database connection...")
    db = database.Database()
    conn = db.get_connection()
    cursor = conn.cursor()
    
    # Test 2: Simple query  
    print("✓ Running test query...")
    cursor.execute("SELECT 1")
    result = cursor.fetchone()
    print(f"  Query result: {result[0]}")
    
    # Test 3: Check tables
    print("\n✓ Checking tables...")
    cursor.execute("""
        SELECT tablename FROM pg_tables 
        WHERE schemaname = 'public'
        ORDER BY tablename
    """)
    tables = cursor.fetchall()
    print(f"  Found {len(tables)} tables:")
    for table in tables:
        print(f"    - {table[0]}")
    
    # Test 4: Check users table
    print("\n✓ Checking users table...")
    cursor.execute("SELECT COUNT(*) FROM users")
    user_count = cursor.fetchone()[0]
    print(f"  Total users: {user_count}")
    
    # Test 5: Check rakes
    print("\n✓ Checking rakes...")
    cursor.execute("SELECT COUNT(*) FROM rakes")
    rake_count = cursor.fetchone()[0]
    print(f"  Total rakes: {rake_count}")
    
    # Test 6: Check builty
    print("\n✓ Checking builties...")
    cursor.execute("SELECT COUNT(*) FROM builty")
    builty_count = cursor.fetchone()[0]
    print(f"  Total builties: {builty_count}")
    
    # Test 7: Check loading slips
    print("\n✓ Checking loading slips...")
    cursor.execute("SELECT COUNT(*) FROM loading_slips")
    slip_count = cursor.fetchone()[0]
    print(f"  Total loading slips: {slip_count}")
    
    # Test 8: Test database methods
    print("\n✓ Testing database methods...")
    all_rakes = db.get_all_rakes()
    print(f"  get_all_rakes() returned {len(all_rakes) if all_rakes else 0} rakes")
    
    accounts = db.get_all_accounts()
    print(f"  get_all_accounts() returned {len(accounts) if accounts else 0} accounts")
    
    warehouses = db.get_all_warehouses()
    print(f"  get_all_warehouses() returned {len(warehouses) if warehouses else 0} warehouses")
    
    # Test 9: Test UUID columns
    print("\n✓ Testing UUID primary keys...")
    cursor.execute("""
        SELECT id FROM rakes LIMIT 1
    """)
    result = cursor.fetchone()
    if result:
        print(f"  Sample rake ID (UUID): {result[0]}")
    else:
        print("  No rakes found")
    
    print("\n" + "=" * 70)
    print("ALL TESTS PASSED! ✓".center(70))
    print("Supabase PostgreSQL connection is working correctly!".center(70))
    print("=" * 70)
    
    db.close_connection(conn)
    
except Exception as e:
    print(f"\n✗ ERROR: {type(e).__name__}: {str(e)}")
    import traceback
    traceback.print_exc()
    print("\n" + "=" * 70)
    print("TEST FAILED ✗".center(70))
    print("=" * 70)
