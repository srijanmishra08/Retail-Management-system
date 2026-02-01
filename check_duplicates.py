#!/usr/bin/env python3
"""Check for duplicate builties in IPLRSD and RK001 rakes"""

import os
import libsql_experimental as libsql

turso_url = os.environ.get('TURSO_DATABASE_URL')
turso_token = os.environ.get('TURSO_AUTH_TOKEN')

if not turso_url or not turso_token:
    print("ERROR: Set TURSO_DATABASE_URL and TURSO_AUTH_TOKEN")
    exit(1)

conn = libsql.connect(database=turso_url, auth_token=turso_token)
cursor = conn.cursor()

# Check IPLRSD duplicates
print('=' * 80)
print('IPLRSD - Checking for duplicates by LR number:')
print('=' * 80)
cursor.execute('''
    SELECT lr_number, COUNT(*) as cnt, GROUP_CONCAT(builty_id) as ids, SUM(quantity_mt) as total_qt
    FROM builty 
    WHERE rake_code LIKE 'IPLRSD%'
    GROUP BY lr_number 
    HAVING COUNT(*) > 1
    ORDER BY lr_number
''')
dups = cursor.fetchall()
if dups:
    for row in dups:
        print(f'LR: {row[0]} | Count: {row[1]} | IDs: {row[2]} | Total QT: {row[3]} MT')
else:
    print('No duplicates found by LR number')

# Check RK001 all builties
print()
print('=' * 80)
print('RK001 - All builties:')
print('=' * 80)
cursor.execute('''
    SELECT builty_id, builty_number, lr_number, quantity_mt, unloading_point
    FROM builty 
    WHERE rake_code = 'RK001'
    ORDER BY builty_id
''')
for row in cursor.fetchall():
    print(f'ID: {row[0]} | Builty: {row[1]} | LR: {row[2]} | QT: {row[3]} MT | Dest: {row[4]}')

# Summary
print()
print('=' * 80)
print('Summary:')
print('=' * 80)
for rake in ['IPLRSD INDIAN POTASH LIMITED', 'RK001']:
    cursor.execute('SELECT COALESCE(SUM(quantity_mt), 0) FROM loading_slips WHERE rake_code = ?', (rake,))
    ls_total = cursor.fetchone()[0]
    cursor.execute('SELECT COALESCE(SUM(quantity_mt), 0) FROM builty WHERE rake_code = ?', (rake,))
    b_total = cursor.fetchone()[0]
    print(f'{rake}: LS={ls_total} MT, Builty={b_total} MT, Diff={ls_total - b_total} MT')
