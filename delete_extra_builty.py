#!/usr/bin/env python3
"""Delete the extra IPLRSD builty (ID 194) to fix the 30 MT mismatch"""

import sys
sys.path.insert(0, '/Users/s/Documents/Retail-Management-system')

from database import Database

db = Database()

# Reset the connection first
Database.reset_cloud_connection()

builty_id = 194

# Check first  
result = db.execute_custom_query('SELECT builty_id, builty_number, rake_code, quantity_mt FROM builty WHERE builty_id = ?', (builty_id,))
if not result:
    print(f"Builty ID {builty_id} not found - already deleted?")
else:
    builty = result[0]
    print(f"Found builty: ID {builty[0]} | {builty[1]} | {builty[2]} | {builty[3]} MT")

# Reset and do the delete
Database.reset_cloud_connection()

# Delete warehouse stock entries
ws_deleted = db.execute_custom_query('DELETE FROM warehouse_stock WHERE builty_id = ?', (builty_id,))
print(f"Deleted warehouse_stock: {ws_deleted}")

# Reset for next operation
Database.reset_cloud_connection()

# Delete builty
b_deleted = db.execute_custom_query('DELETE FROM builty WHERE builty_id = ?', (builty_id,))
print(f"Deleted builty: {b_deleted}")

db.invalidate_cache()

# Reset and verify
Database.reset_cloud_connection()

result = db.execute_custom_query('SELECT builty_id FROM builty WHERE builty_id = ?', (builty_id,))
if result:
    print(f"⚠️ Builty {builty_id} still exists!")
else:
    print(f"✅ Builty {builty_id} confirmed deleted!")

rake = 'IPLRSD INDIAN POTASH LIMITED'
ls_result = db.execute_custom_query('SELECT COALESCE(SUM(quantity_mt), 0) FROM loading_slips WHERE rake_code = ?', (rake,))
ls_total = ls_result[0][0]
b_result = db.execute_custom_query('SELECT COALESCE(SUM(quantity_mt), 0) FROM builty WHERE rake_code = ?', (rake,))
b_total = b_result[0][0]
diff = ls_total - b_total
status = "✅" if diff >= 0 else "⚠️"
print(f"\n{status} IPLRSD: LS={ls_total} MT, Builty={b_total} MT, Trucks Loading={diff} MT")
