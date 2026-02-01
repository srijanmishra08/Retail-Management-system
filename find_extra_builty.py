#!/usr/bin/env python3
"""Find the extra IPLRSD builty causing 30 MT mismatch"""

import os
import libsql_experimental as libsql

turso_url = os.environ.get('TURSO_DATABASE_URL')
turso_token = os.environ.get('TURSO_AUTH_TOKEN')

conn = libsql.connect(database=turso_url, auth_token=turso_token)
cursor = conn.cursor()

rake = 'IPLRSD INDIAN POTASH LIMITED'

# Get loading slips
cursor.execute('SELECT slip_id, slip_number, truck_id, quantity_mt FROM loading_slips WHERE rake_code = ? ORDER BY slip_id', (rake,))
loading_slips = cursor.fetchall()
print(f"Loading slips: {len(loading_slips)}")

# Get builties  
cursor.execute('SELECT builty_id, builty_number, truck_id, quantity_mt, lr_number FROM builty WHERE rake_code = ? ORDER BY builty_id', (rake,))
builties = cursor.fetchall()
print(f"Builties: {len(builties)}")

# Group by truck
ls_by_truck = {}
for ls in loading_slips:
    t = ls[2]
    if t not in ls_by_truck:
        ls_by_truck[t] = []
    ls_by_truck[t].append(ls)

b_by_truck = {}
for b in builties:
    t = b[2]
    if t not in b_by_truck:
        b_by_truck[t] = []
    b_by_truck[t].append(b)

# Find truck with more builties than loading slips
print("\nTrucks with excess builties:")
for truck, bs in b_by_truck.items():
    ls_count = len(ls_by_truck.get(truck, []))
    b_count = len(bs)
    if b_count > ls_count:
        print(f"\nTruck {truck}: LS={ls_count}, Builty={b_count}")
        print(f"  Loading Slips:")
        for ls in ls_by_truck.get(truck, []):
            print(f"    ID: {ls[0]} | {ls[1]} | {ls[3]} MT")
        print(f"  Builties:")
        for b in bs:
            print(f"    ID: {b[0]} | {b[1]} | LR: {b[4]} | {b[3]} MT")
        
        # Suggest which builty to delete
        if b_count - ls_count == 1:
            print(f"\n  >>> EXTRA BUILTY: ID {bs[-1][0]} ({bs[-1][1]}) - {bs[-1][3]} MT <<<")
