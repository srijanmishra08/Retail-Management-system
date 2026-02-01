#!/usr/bin/env python3
"""Fix RK001 and investigate IPLRSD mismatch"""

import os
import libsql_experimental as libsql

turso_url = os.environ.get('TURSO_DATABASE_URL')
turso_token = os.environ.get('TURSO_AUTH_TOKEN')

if not turso_url or not turso_token:
    print("ERROR: Set TURSO_DATABASE_URL and TURSO_AUTH_TOKEN")
    exit(1)

conn = libsql.connect(database=turso_url, auth_token=turso_token)
cursor = conn.cursor()

print("=" * 80)
print("STEP 1: Delete RK001 Warehouse Builty (ID 4)")
print("=" * 80)

# Delete warehouse stock entries for builty 4
cursor.execute('DELETE FROM warehouse_stock WHERE builty_id = 4')
ws_count = cursor.rowcount
print(f"Deleted {ws_count} warehouse_stock entries")

# Delete builty 4
cursor.execute('DELETE FROM builty WHERE builty_id = 4')
b_count = cursor.rowcount
print(f"Deleted {b_count} builty record (ID 4)")

conn.commit()
print("✅ RK001 warehouse builty deleted!")

print()
print("=" * 80)
print("STEP 2: Investigate IPLRSD mismatch")
print("=" * 80)

rake = 'IPLRSD INDIAN POTASH LIMITED'

# Get loading slip totals
cursor.execute('SELECT slip_id, slip_number, quantity_mt, truck_id FROM loading_slips WHERE rake_code = ?', (rake,))
loading_slips = cursor.fetchall()
ls_total = sum(ls[2] for ls in loading_slips)
print(f"Loading slips: {len(loading_slips)} records, Total: {ls_total} MT")

# Get builty totals
cursor.execute('SELECT builty_id, builty_number, lr_number, quantity_mt, truck_id FROM builty WHERE rake_code = ?', (rake,))
builties = cursor.fetchall()
b_total = sum(b[3] for b in builties)
print(f"Builties: {len(builties)} records, Total: {b_total} MT")

print(f"\nDifference: {ls_total - b_total} MT (should be >= 0)")

# Check for duplicate LR numbers in builties
print("\n--- Duplicate LR numbers in Builties ---")
lr_counts = {}
for b in builties:
    lr = b[2]
    if lr not in lr_counts:
        lr_counts[lr] = []
    lr_counts[lr].append(b)

duplicates_found = False
for lr, bs in lr_counts.items():
    if len(bs) > 1:
        duplicates_found = True
        print(f"  LR: {lr} ({len(bs)} builties)")
        for b in bs:
            print(f"    -> ID: {b[0]} | {b[1]} | {b[3]} MT | Truck: {b[4]}")

if not duplicates_found:
    print("  No duplicates found")

# Check truck-level: multiple builties for same truck
print("\n--- Trucks with multiple builties ---")
truck_builties = {}
for b in builties:
    truck = b[4]
    if truck not in truck_builties:
        truck_builties[truck] = []
    truck_builties[truck].append(b)

multi_builty_trucks = []
for truck, bs in truck_builties.items():
    if len(bs) > 1:
        multi_builty_trucks.append((truck, bs))
        print(f"  Truck {truck}: {len(bs)} builties, Total: {sum(b[3] for b in bs)} MT")
        for b in bs:
            print(f"    -> ID: {b[0]} | {b[1]} | LR: {b[2]} | {b[3]} MT")

if not multi_builty_trucks:
    print("  All trucks have single builty")
    
# Compare truck counts
ls_trucks = set(ls[3] for ls in loading_slips)
b_trucks = set(b[4] for b in builties)
extra_b_trucks = b_trucks - ls_trucks
if extra_b_trucks:
    print(f"\n--- Builty trucks NOT in Loading Slips ---")
    for t in extra_b_trucks:
        for b in builties:
            if b[4] == t:
                print(f"  Truck {t}: ID {b[0]} | {b[1]} | {b[3]} MT")

# Find trucks where builty count > loading slip count
print("\n--- Trucks where Builty Count > Loading Slip Count ---")
ls_by_truck = {}
for ls in loading_slips:
    t = ls[3]  # truck_id
    if t not in ls_by_truck:
        ls_by_truck[t] = []
    ls_by_truck[t].append(ls)

for truck, bs in truck_builties.items():
    ls_count = len(ls_by_truck.get(truck, []))
    b_count = len(bs)
    if b_count > ls_count:
        print(f"Truck {truck}: LS={ls_count}, Builty={b_count} (excess: {b_count - ls_count})")
        print(f"  Loading Slips:")
        for ls in ls_by_truck.get(truck, []):
            print(f"    ID: {ls[0]} | {ls[1]} | {ls[2]} MT")
        print(f"  Builties:")
        for b in bs:
            print(f"    ID: {b[0]} | {b[1]} | LR: {b[2]} | {b[3]} MT")

# Final summary
print()
print("=" * 80)
print("FINAL SUMMARY:")
print("=" * 80)
for rake in ['IPLRSD INDIAN POTASH LIMITED', 'RK001']:
    cursor.execute('SELECT COALESCE(SUM(quantity_mt), 0) FROM loading_slips WHERE rake_code = ?', (rake,))
    ls_total = cursor.fetchone()[0]
    cursor.execute('SELECT COALESCE(SUM(quantity_mt), 0) FROM builty WHERE rake_code = ?', (rake,))
    b_total = cursor.fetchone()[0]
    diff = ls_total - b_total
    status = "✅" if diff >= 0 else "⚠️"
    print(f'{status} {rake}: LS={ls_total} MT, Builty={b_total} MT, Trucks Loading={diff} MT')
