#!/usr/bin/env python3
"""
Script to delete duplicate builty entries from the database.
These duplicates were identified by having the same LR number.
"""

import os
import libsql_experimental as libsql

# Duplicate Builty IDs to delete (keeping the lowest ID for each LR number)
DUPLICATE_BUILTY_IDS = [
    2,    # LR 1001 (RK001)
    40,   # LR 1032
    48,   # LR 1038
    50,   # LR 1039
    52,   # LR 1040
    56,   # LR 1041
    58,   # LR 1042
    60,   # LR 1043
    62,   # LR 1044
    64,   # LR 1045
    69,   # LR 1048
    74,   # LR 1050
    76,   # LR 1051
    78,   # LR 1052
    80,   # LR 1053
    82,   # LR 1054
    84,   # LR 1055 (duplicate 1)
    85,   # LR 1055 (duplicate 2)
    86,   # LR 1055 (duplicate 3)
    88,   # LR 1056
    90,   # LR 1057
    98,   # LR 1061
]

def main():
    # Get Turso credentials from environment
    turso_url = os.environ.get('TURSO_DATABASE_URL')
    turso_token = os.environ.get('TURSO_AUTH_TOKEN')
    
    if not turso_url or not turso_token:
        print("ERROR: TURSO_DATABASE_URL and TURSO_AUTH_TOKEN environment variables must be set")
        print("Run with:")
        print('  export TURSO_DATABASE_URL="libsql://fims-production-srijanmishra08.aws-ap-south-1.turso.io"')
        print('  export TURSO_AUTH_TOKEN="your-token-here"')
        return
    
    print("🔌 Connecting to Turso database...")
    conn = libsql.connect(database=turso_url, auth_token=turso_token)
    cursor = conn.cursor()
    
    print(f"\n📊 Found {len(DUPLICATE_BUILTY_IDS)} duplicate builties to delete")
    print(f"IDs: {DUPLICATE_BUILTY_IDS}\n")
    
    # First, show what we're about to delete
    print("=" * 80)
    print("BUILTIES TO BE DELETED:")
    print("=" * 80)
    
    for builty_id in DUPLICATE_BUILTY_IDS:
        cursor.execute('''
            SELECT builty_id, builty_number, rake_code, lr_number, quantity_mt, unloading_point
            FROM builty WHERE builty_id = ?
        ''', (builty_id,))
        row = cursor.fetchone()
        if row:
            print(f"  ID: {row[0]:3} | Builty: {row[1]} | Rake: {row[2]} | LR: {row[3]} | QT: {row[4]} MT | Dest: {row[5]}")
        else:
            print(f"  ID: {builty_id} - NOT FOUND (already deleted?)")
    
    print("\n" + "=" * 80)
    
    # Ask for confirmation
    confirm = input("\n⚠️  Are you sure you want to DELETE these builties? (yes/no): ")
    
    if confirm.lower() != 'yes':
        print("❌ Aborted. No changes made.")
        return
    
    # Delete builties and their associated warehouse_stock entries
    deleted_count = 0
    warehouse_stock_deleted = 0
    
    for builty_id in DUPLICATE_BUILTY_IDS:
        try:
            # First delete associated warehouse_stock entries
            cursor.execute('DELETE FROM warehouse_stock WHERE builty_id = ?', (builty_id,))
            ws_deleted = cursor.rowcount
            warehouse_stock_deleted += ws_deleted
            
            # Then delete the builty
            cursor.execute('DELETE FROM builty WHERE builty_id = ?', (builty_id,))
            if cursor.rowcount > 0:
                deleted_count += 1
                print(f"  ✓ Deleted builty ID {builty_id} (+ {ws_deleted} warehouse_stock entries)")
            else:
                print(f"  - Builty ID {builty_id} not found (already deleted?)")
                
        except Exception as e:
            print(f"  ✗ Error deleting builty ID {builty_id}: {e}")
    
    # Commit the changes
    conn.commit()
    
    print("\n" + "=" * 80)
    print(f"✅ COMPLETED: Deleted {deleted_count} duplicate builties")
    print(f"   Also removed {warehouse_stock_deleted} associated warehouse_stock entries")
    print("=" * 80)
    
    # Verify the fix - show updated totals for MBAPL01
    print("\n📊 Verifying MBAPL01 rake totals after cleanup:")
    
    cursor.execute('''
        SELECT 
            COALESCE(SUM(ls.quantity_mt), 0) as loading_slip_total,
            (SELECT COALESCE(SUM(b.quantity_mt), 0) FROM builty b WHERE b.rake_code = 'MBAPL01') as builty_total
        FROM loading_slips ls 
        WHERE ls.rake_code = 'MBAPL01'
    ''')
    row = cursor.fetchone()
    ls_total = row[0] or 0
    builty_total = row[1] or 0
    
    print(f"   Loading Slip Total: {ls_total:.2f} MT")
    print(f"   Builty Total:       {builty_total:.2f} MT")
    print(f"   Trucks Loading:     {ls_total - builty_total:.2f} MT")
    
    if builty_total <= ls_total:
        print("   ✅ Data is now consistent!")
    else:
        print(f"   ⚠️  Still have {builty_total - ls_total:.2f} MT excess in builties")

if __name__ == '__main__':
    main()
