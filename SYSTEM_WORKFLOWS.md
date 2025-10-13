# FIMS - Complete System Workflows & Process Diagrams

## 📊 Visual Business Flow Diagrams

---

## Workflow 1: COMPLETE LIFECYCLE (End-to-End)

```
┌─────────────────────────────────────────────────────────────────┐
│                     PHASE 1: PROCUREMENT                         │
│                    (Admin - System Setup)                        │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
                    ┏━━━━━━━━━━━━━━━━━━━┓
                    ┃   RAKE ARRIVES    ┃
                    ┃   at Rake Point   ┃
                    ┗━━━━━━━━┬━━━━━━━━━━┛
                             │
                             ▼
                    [Admin Creates Rake]
                    • Rake Code: RK-2023-001
                    • Company: ABC Fertilizers
                    • Product: Urea
                    • RR Quantity: 500 MT
                    • Rake Point: Station A
                             │
┌────────────────────────────────┴────────────────────────────────┐
│                                                                  │
▼                                                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                  PHASE 2A: DISTRIBUTION PATH A                   │
│              (RakePoint - Warehouse Storage Path)                │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
                [RakePoint User Logs In]
                                │
                    ┌───────────┴───────────┐
                    │                       │
                    ▼                       ▼
        [Create Loading Slips]   [Create Builties]
        • Slip #1: W1→Truck1      • BLT-001 (50 MT)
        • Slip #2: W2→Truck2      • BLT-002 (50 MT)
        • Slip #3: W3→Truck3      • BLT-003 (50 MT)
        ...                       ...
        (Track wagon unloading)   (Transportation docs)
                    │                       │
                    └───────────┬───────────┘
                                │
                                ▼
                    ╔═══════════════════╗
                    ║   TRUCKS DEPART   ║
                    ║   to Warehouses   ║
                    ╚═════════╤═════════╝
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│ WAREHOUSE 1 │      │ WAREHOUSE 2 │      │ WAREHOUSE 3 │
│  BLT-001    │      │  BLT-002    │      │  BLT-003    │
│  50 MT      │      │  50 MT      │      │  50 MT      │
└──────┬──────┘      └──────┬──────┘      └──────┬──────┘
       │                    │                    │
       └────────────────────┼────────────────────┘
                            │
                            ▼
                [Warehouse User Logs In]
                            │
                            ▼
                    [Record STOCK IN]
                    • Select Builty: BLT-001
                    • Unloaded Qty: 49.8 MT
                    • Unloader: John
                    • Warehouse: WH-1
                    • Date: 2023-10-08
                            │
                            ▼
                    [VALIDATION CHECK]
                    Total for BLT-001 < 50 MT? ✓
                    Record in database
                            │
                            ▼
                    ┏━━━━━━━━━━━━━━━━━┓
                    ┃  STOCK STORED   ┃
                    ┃  Balance: 49.8  ┃
                    ┗━━━━━━━┯━━━━━━━━━┛
                            │
                            ▼
                    [Time Passes...]
                    [Customer Order Received]
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    PHASE 3: DISPATCH                             │
│              (Warehouse - Customer Delivery)                     │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
                    [Warehouse - STOCK OUT]
                    • Select Warehouse: WH-1
                    • Check Balance: 49.8 MT ✓
                    • Create NEW Builty (14 fields):
                      - Builty: BLTO-20231010-103045
                      - Truck: GJ-05-CD-5678
                      - Destination: Dealer A
                      - Quantity: 30 MT
                      - Freight: ₹15,000
                      - Auto-link: RK-2023-001
                            │
                            ▼
                    [VALIDATION CHECK]
                    30 MT < 49.8 MT Balance? ✓
                    Create new builty
                    Record Stock OUT
                            │
                            ▼
                    ┏━━━━━━━━━━━━━━━━━┓
                    ┃  TRUCK DEPARTS  ┃
                    ┃  to Dealer A    ┃
                    ┗━━━━━━━┯━━━━━━━━━┛
                            │
                    New Balance: 19.8 MT
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    PHASE 4: BILLING                              │
│                (Accountant - Financial Docs)                     │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
                [Accountant User Logs In]
                                │
                                ▼
                    [Create E-Bill]
                    • Select Builty: BLTO-20231010-103045
                    • E-Bill #: EB-2023-001
                    • Amount: ₹1,50,000
                    • Date: 2023-10-10
                    • Upload Eway Bill PDF ✓
                            │
                            ▼
                    ┏━━━━━━━━━━━━━━━━━┓
                    ┃  BILL GENERATED ┃
                    ┃  Status: PAID   ┃
                    ┗━━━━━━━┯━━━━━━━━━┛
                            │
                            ▼
                    ╔═══════════════════╗
                    ║  COMPLETE CYCLE   ║
                    ╚═══════════════════╝

TRACEABILITY CHAIN:
E-Bill EB-2023-001
  → Builty BLTO-20231010-103045 (Stock OUT)
    → Warehouse Stock (49.8 MT → 19.8 MT)
      → Builty BLT-001 (Stock IN)
        → Rake RK-2023-001 (500 MT)
          → ABC Fertilizers, Urea
```

---

## Workflow 2: DIRECT MARKET DISPATCH (Bypass Warehouse)

```
┌─────────────────────────────────────────────────────────────────┐
│              SCENARIO: Government Emergency Order                │
│           (Goods go directly from Rake to Customer)              │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
                    ┏━━━━━━━━━━━━━━━━━━━┓
                    ┃   RAKE ARRIVES    ┃
                    ┃   RK-2023-002     ┃
                    ┗━━━━━━━━┬━━━━━━━━━━┛
                             │
                             ▼
                [Admin Creates Rake]
                • Rake Code: RK-2023-002
                • Company: XYZ Fertilizers
                • Product: DAP
                • RR Quantity: 300 MT
                • For: Government Order
                             │
                             ▼
                [RakePoint User Logs In]
                             │
                             ▼
            [Create Builties - Direct Dispatch]
            • BLT-101: 30 MT → Govt WH-A
            • BLT-102: 30 MT → Govt WH-B
            • BLT-103: 30 MT → Govt WH-C
            ...
            (10 builties × 30 MT = 300 MT)
                             │
                             ▼
                    ┏━━━━━━━━━━━━━━━━━┓
                    ┃  TRUCKS DEPART  ┃
                    ┃  DIRECTLY TO    ┃
                    ┃  GOVERNMENT     ┃
                    ┗━━━━━━━┯━━━━━━━━━┛
                            │
                            ▼
        ╔═══════════════════════════════╗
        ║   NO WAREHOUSE STOCK IN       ║
        ║   (Company warehouse bypassed)║
        ╚════════════╤══════════════════╝
                     │
                     ▼
        [Accountant Creates E-Bills]
        • EB-2023-101 for BLT-101: ₹1,50,000
        • EB-2023-102 for BLT-102: ₹1,50,000
        ...
        Total: ₹15,00,000
                     │
                     ▼
            ┏━━━━━━━━━━━━━━━━━┓
            ┃   ORDER COMPLETE ┃
            ┃   No Storage Cost┃
            ┗━━━━━━━━━━━━━━━━━┛

KEY DIFFERENCE:
• NO Stock IN to company warehouses
• Direct delivery = No rent charges
• Faster dispatch
• Government pays full freight
```

---

## Workflow 3: TWO BUILTY TYPES Explained

```
┌─────────────────────────────────────────────────────────────────┐
│         BUILTY TYPE A: RakePoint Builty (BLT-*)                  │
│              (Created during rake unloading)                     │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
                    [RakePoint User Action]
                    Click "Create Builty"
                                │
                    ┌───────────┴────────────┐
                    │                        │
        STEP 1: Select Rake Code    STEP 2: Fill 14 Fields
        ↓                                    ↓
        RK-2023-001 selected         • Date: 2023-10-08
        Auto-fills:                  • Account: Warehouse 1
        • Rake Point Name            • Truck: MH-12-AB-1234
        • Goods Name (Urea)          • Driver: John Doe
                    │                • Quantity: 50 MT
                    │                • LR Number: LR-12345
                    │                ...
                    └───────────┬────────────┘
                                │
                                ▼
                    [System Generates]
                    Builty Number: BLT-20231008-143022
                    Links to: RK-2023-001
                    Purpose: Transport from Rake → Warehouse
                                │
                                ▼
                    ┏━━━━━━━━━━━━━━━━━━━┓
                    ┃  BUILTY CREATED   ┃
                    ┃  Used for STOCK IN┃
                    ┗━━━━━━━━━━━━━━━━━━━┛

┌─────────────────────────────────────────────────────────────────┐
│         BUILTY TYPE B: Warehouse Builty (BLTO-*)                 │
│              (Created during warehouse dispatch)                 │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
                    [Warehouse User Action]
                    Click "Stock OUT"
                                │
                    ┌───────────┴────────────┐
                    │                        │
        STEP 1: Select Warehouse     STEP 2: Create NEW Builty
        ↓                                    ↓
        Warehouse 1 selected         Fill complete 14 fields:
        Check Balance: 49.8 MT       • Date: 2023-10-10
                    │                • Truck: GJ-05-CD-5678
                    │                • Destination: Dealer A
                    │                • Driver: Mike Smith
                    │                • Quantity: 30 MT
                    │                • LR Number: LR-67890
                    │                ...
                    └───────────┬────────────┘
                                │
                                ▼
                    [System Generates]
                    Builty Number: BLTO-20231010-103045
                    Auto-links to: RK-2023-001
                      (via warehouse stock history)
                    Purpose: Transport Warehouse → Customer
                                │
                                ▼
                    ┏━━━━━━━━━━━━━━━━━━━━┓
                    ┃  NEW BUILTY CREATED ┃
                    ┃  Used for STOCK OUT ┃
                    ┗━━━━━━━━━━━━━━━━━━━━┛

WHY TWO TYPES?
┌─────────────────────────────────────────┐
│  BLT-* (RakePoint Builty)               │
│  • Describes Rake → Warehouse transport │
│  • User SELECTS rake_code               │
│  • Used when RECEIVING goods            │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│  BLTO-* (Warehouse Builty)              │
│  • Describes Warehouse → Customer       │
│  • System AUTO-DETECTS rake_code        │
│  • Used when DISPATCHING goods          │
│  • NEW truck, driver, freight details   │
└─────────────────────────────────────────┘

BOTH link back to original Rake Code!
```

---

## Workflow 4: STOCK IN Validation (Critical Feature)

```
┌─────────────────────────────────────────────────────────────────┐
│              STOCK IN VALIDATION FLOWCHART                       │
│         (Prevents duplicate entries beyond capacity)             │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
                    [Warehouse User Action]
                    Click "Stock IN"
                                │
                                ▼
                    [Select Builty: BLT-001]
                    Builty Details Loaded:
                    • Rake Code: RK-2023-001
                    • Original Quantity: 50 MT
                    • Account: Dealer A
                                │
                                ▼
                    [Enter Details]
                    • Unloaded Quantity: 12 MT
                    • Warehouse: WH-1
                    • Date: 2023-10-08
                                │
                                ▼
                    [Click "Record Stock IN"]
                                │
                                ▼
            ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
            ┃  SYSTEM VALIDATION CHECK     ┃
            ┗━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━┛
                          │
                          ▼
        [Query Database]
        SELECT quantity_mt 
        FROM builty 
        WHERE builty_number = 'BLT-001'
        
        Result: builty_quantity = 50 MT
                          │
                          ▼
        [Query Existing Stock IN]
        SELECT SUM(quantity_mt) 
        FROM warehouse_stock
        WHERE builty_id = (BLT-001) 
          AND transaction_type = 'IN'
        
        Result: existing_stock_in = 36 MT
          (Previous entries: 10 + 12 + 12 + 12)
                          │
                          ▼
        [Calculate]
        total_already_in = 36 MT
        new_quantity = 12 MT
        builty_capacity = 50 MT
                          │
                          ▼
        [Check Capacity]
        IF (36 + 12) > 50:
            remaining = 50 - 36 = 14 MT
                          │
        ┌─────────────────┴─────────────────┐
        │                                   │
        ▼                                   ▼
    [12 ≤ 14?]                          [If 12 > 14]
    YES ✓                               NO ✗
        │                                   │
        ▼                                   ▼
    [ACCEPT]                            [REJECT]
    Record in database                  Show Error:
    New total: 48 MT                    "Builty BLT-001 has only
    Remaining: 2 MT                      14.00 MT remaining"
        │                                   │
        ▼                                   ▼
    ┏━━━━━━━━━━━━━━━━━┓          ┏━━━━━━━━━━━━━━━━━┓
    ┃  SUCCESS MESSAGE ┃          ┃  ERROR MESSAGE  ┃
    ┃  "Stock IN       ┃          ┃  "Cannot record ┃
    ┃   recorded!      ┃          ┃   stock IN"     ┃
    ┃   Remaining:     ┃          ┃                 ┃
    ┃   2.00 MT"       ┃          ┃  User must try  ┃
    ┗━━━━━━━━━━━━━━━━━┛          ┃  with ≤14 MT    ┃
                                  ┗━━━━━━━━━━━━━━━━━┛

EXAMPLE SCENARIO:
Builty BLT-001: 50 MT capacity

Entry 1: 10 MT ✓ (40 MT remaining)
Entry 2: 12 MT ✓ (28 MT remaining)
Entry 3: 12 MT ✓ (16 MT remaining)
Entry 4: 12 MT ✓ (4 MT remaining)
Entry 5: 12 MT ✗ REJECTED! (only 4 MT left)
Entry 5: 4 MT  ✓ (0 MT remaining)
Entry 6: 1 MT  ✗ REJECTED! (builty full)
```

---

## Workflow 5: STOCK OUT Validation & Balance Check

```
┌─────────────────────────────────────────────────────────────────┐
│              STOCK OUT VALIDATION FLOWCHART                      │
│         (Prevents negative warehouse balance)                    │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
                    [Warehouse User Action]
                    Click "Stock OUT"
                                │
                                ▼
                    [Select Warehouse: WH-1]
                                │
                                ▼
            [System Checks Current Balance]
            Query:
            SELECT 
              SUM(CASE WHEN type='IN' THEN qty END) as stock_in,
              SUM(CASE WHEN type='OUT' THEN qty END) as stock_out
            FROM warehouse_stock
            WHERE warehouse_id = WH-1
            
            Result:
            Stock IN: 99.8 MT
            Stock OUT: 50 MT
            Balance: 49.8 MT
                                │
                                ▼
                    [User Fills Form]
                    • Quantity: 30 MT
                    • Destination: Dealer A
                    • Truck: GJ-05-CD-5678
                    • ... (14 fields)
                                │
                                ▼
                    [Click "Record Stock OUT"]
                                │
                                ▼
            ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
            ┃  VALIDATION CHECK            ┃
            ┗━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━┛
                          │
                          ▼
        [Compare]
        Requested: 30 MT
        Available: 49.8 MT
                          │
        ┌─────────────────┴─────────────────┐
        │                                   │
        ▼                                   ▼
    [30 ≤ 49.8?]                        [If 30 > 49.8]
    YES ✓                               NO ✗
        │                                   │
        ▼                                   ▼
    [ACCEPT]                            [REJECT]
    • Generate Builty:                  Show Error:
      BLTO-20231010-103045              "Warehouse has only
    • Auto-link: RK-2023-001             49.8 MT available.
    • Record Stock OUT                   Cannot dispatch 30 MT"
    • New Balance: 19.8 MT                  │
        │                                   │
        ▼                                   ▼
    ┏━━━━━━━━━━━━━━━━━┓          ┏━━━━━━━━━━━━━━━━━┓
    ┃  SUCCESS         ┃          ┃  ERROR MESSAGE  ┃
    ┃  Truck can leave ┃          ┃  Adjust quantity┃
    ┃  New balance:    ┃          ┃  or select      ┃
    ┃  19.8 MT         ┃          ┃  different WH   ┃
    ┗━━━━━━━━━━━━━━━━━┛          ┗━━━━━━━━━━━━━━━━━┛

EXAMPLE SCENARIO:
Warehouse 1 Balance: 49.8 MT

Request 1: 30 MT  ✓ (New balance: 19.8 MT)
Request 2: 15 MT  ✓ (New balance: 4.8 MT)
Request 3: 10 MT  ✗ REJECTED! (only 4.8 MT left)
Request 3: 4.8 MT ✓ (New balance: 0 MT)
Request 4: 1 MT   ✗ REJECTED! (warehouse empty)
```

---

## Workflow 6: COMPLETE DATA FLOW (All Tables)

```
┌─────────────────────────────────────────────────────────────────┐
│                      DATABASE RELATIONSHIPS                      │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
                        ┏━━━━━━━━━━━━┓
                        ┃   RAKES    ┃ ← Admin creates
                        ┃ (rake_code)┃
                        ┗━━━━┯━━━━━━━┛
                             │ 1
                             │
                    ┌────────┼────────┐
                    │        │        │
                    ▼ *      ▼ *      ▼ *
            ┏━━━━━━━━━━┓ ┏━━━━━━━━━━━━━┓ ┏━━━━━━━━━━━━━┓
            ┃  BUILTY  ┃ ┃ LOADING_SLIP┃ ┃  (Summary)  ┃
            ┃(builty_id)┃←┃ (slip_id)   ┃ ┃             ┃
            ┗━━━━┯━━━━━━┛ ┗━━━━━━━━━━━━━┛ ┗━━━━━━━━━━━━━┛
                 │ 1           │ *
                 │             │
                 │        ┌────┘
                 │        │
                 ▼ *      ▼ (optional link)
        ┏━━━━━━━━━━━━━━━━━━┓
        ┃ WAREHOUSE_STOCK  ┃ ← Warehouse records
        ┃   (stock_id)     ┃
        ┃ • transaction:   ┃
        ┃   'IN' or 'OUT'  ┃
        ┗━━━━━━━━┯━━━━━━━━━┛
                 │
                 │ (builty_id links back)
                 │
                 ▼
        ┏━━━━━━━━━━━━━━━━━━┓
        ┃     EBILLS       ┃ ← Accountant creates
        ┃   (ebill_id)     ┃
        ┃ • builty_id (FK) ┃
        ┃ • eway_bill_pdf  ┃
        ┗━━━━━━━━━━━━━━━━━━┛

DATA INSERTION SEQUENCE:
1. Admin → INSERT INTO rakes (rake_code, ...)
2. RakePoint → INSERT INTO loading_slips (rake_code FK)
3. RakePoint → INSERT INTO builty (rake_code FK)
4. Warehouse → INSERT INTO warehouse_stock (builty_id FK, type='IN')
5. Warehouse → INSERT INTO builty (rake_code from history)
6. Warehouse → INSERT INTO warehouse_stock (builty_id FK, type='OUT')
7. Accountant → INSERT INTO ebills (builty_id FK)

TRACEABILITY QUERY:
SELECT 
    r.rake_code,
    r.company_name,
    r.product_name,
    b1.builty_number as rake_builty,
    ws.transaction_type,
    ws.quantity_mt,
    b2.builty_number as dispatch_builty,
    e.ebill_number,
    e.amount
FROM rakes r
LEFT JOIN builty b1 ON r.rake_code = b1.rake_code
LEFT JOIN warehouse_stock ws ON b1.builty_id = ws.builty_id
LEFT JOIN builty b2 ON ws.builty_id = b2.builty_id (for OUT)
LEFT JOIN ebills e ON b2.builty_id = e.builty_id
WHERE r.rake_code = 'RK-2023-001'
ORDER BY ws.date;
```

---

## Workflow 7: USER ROLE PERMISSIONS

```
┌─────────────────────────────────────────────────────────────────┐
│                    ROLE-BASED ACCESS CONTROL                     │
└───────────────────────────────┬─────────────────────────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        │                       │                       │
        ▼                       ▼                       ▼
┏━━━━━━━━━━━━┓        ┏━━━━━━━━━━━━━┓        ┏━━━━━━━━━━━━━┓
┃   ADMIN    ┃        ┃  RAKE POINT  ┃        ┃  WAREHOUSE  ┃
┗━━━━━━━━━━━━┛        ┗━━━━━━━━━━━━━┛        ┗━━━━━━━━━━━━━┛
      │                      │                      │
      │ CAN:                 │ CAN:                 │ CAN:
      ├─ Create Rakes        ├─ Create Builties    ├─ Stock IN
      ├─ Manage Accounts     ├─ Create Load Slips  ├─ Stock OUT
      ├─ Manage Warehouses   ├─ View Builties      ├─ View Balance
      ├─ View Summary        ├─ View Load Slips    ├─ View Dashboard
      ├─ View All Reports    │                     │
      │                      │ CANNOT:              │ CANNOT:
      │ CANNOT:              ├─ See Warehouse      ├─ See Rake Point
      ├─ Create Builties     │   Operations        │   Operations
      ├─ Record Stock        ├─ Record Stock       ├─ Create Rakes
      ├─ Create E-Bills      ├─ Create E-Bills     ├─ Create E-Bills
      │                      │                     │
      ▼                      ▼                     ▼
        ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
        ┃           ACCOUNTANT                    ┃
        ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
                      │
                      │ CAN:
                      ├─ Create E-Bills
                      ├─ Upload Eway Bills
                      ├─ View All E-Bills
                      ├─ View Builties (read-only)
                      │
                      │ CANNOT:
                      ├─ Create Rakes
                      ├─ Create Builties
                      ├─ Record Stock
                      │
                      ▼

LOGIN FLOW:
User → /login → Check credentials → Load role
                                   │
        ┌──────────────────────────┼──────────────────────────┐
        ▼                          ▼                          ▼
    role=Admin             role=RakePoint           role=Warehouse
        │                          │                          │
        └─→ /admin/dashboard  /rakepoint/dashboard  /warehouse/dashboard
                                   │                          │
                              role=Accountant                 │
                                   │                          │
                              /accountant/dashboard ←─────────┘

SECURITY CHECK (on every route):
@app.route('/warehouse/stock-in')
@login_required  ← Must be logged in
def warehouse_stock_in():
    if current_user.role != 'Warehouse':  ← Role check
        flash('Unauthorized')
        return redirect(url_for('index'))
    # ... route logic
```

---

## Workflow 8: REPORT GENERATION

```
┌─────────────────────────────────────────────────────────────────┐
│                    ADMIN SUMMARY REPORT                          │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
                [Admin Clicks "Summary"]
                                │
                                ▼
            [Query: Rake-wise Aggregation]
            
            SELECT 
                r.rake_code,
                r.company_name,
                r.date,
                r.rr_quantity,
                COALESCE(SUM(CASE 
                    WHEN ws.transaction_type = 'IN' 
                    THEN ws.quantity_mt 
                    ELSE 0 END), 0) as stock_in,
                COALESCE(SUM(CASE 
                    WHEN ws.transaction_type = 'OUT' 
                    THEN ws.quantity_mt 
                    ELSE 0 END), 0) as stock_out
            FROM rakes r
            LEFT JOIN builty b ON r.rake_code = b.rake_code
            LEFT JOIN warehouse_stock ws ON b.builty_id = ws.builty_id
            GROUP BY r.rake_code
            ORDER BY r.date DESC;
                                │
                                ▼
                    [Display Table]
                    
    ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
    ┃  Rake    │ Company │ Date  │ RR   │ IN  │ OUT │Balance┃
    ┃  Code    │         │       │ Qty  │     │     │       ┃
    ┣━━━━━━━━━━╋━━━━━━━━━╋━━━━━━━╋━━━━━━╋━━━━━╋━━━━━╋━━━━━━━┫
    ┃ RK-001   │ ABC Ltd │ 01-10 │ 500  │ 480 │ 200 │ 280   ┃
    ┃ RK-002   │ XYZ Ltd │ 05-10 │ 300  │ 300 │ 300 │ 0     ┃
    ┃ RK-003   │ PQR Ltd │ 10-10 │ 400  │ 200 │ 0   │ 200   ┃
    ┗━━━━━━━━━━┻━━━━━━━━━┻━━━━━━━┻━━━━━━┻━━━━━┻━━━━━┻━━━━━━━┛
    
    TOTALS: RR: 1200 MT │ IN: 980 MT │ OUT: 500 MT │ Balance: 480 MT

┌─────────────────────────────────────────────────────────────────┐
│                 WAREHOUSE BALANCE REPORT                         │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
            [Warehouse Clicks "View Balance"]
                                │
                                ▼
            [Query: Warehouse-wise Stock]
            
            SELECT 
                w.warehouse_name,
                w.location,
                COALESCE(SUM(CASE 
                    WHEN ws.transaction_type = 'IN' 
                    THEN ws.quantity_mt 
                    ELSE 0 END), 0) as stock_in,
                COALESCE(SUM(CASE 
                    WHEN ws.transaction_type = 'OUT' 
                    THEN ws.quantity_mt 
                    ELSE 0 END), 0) as stock_out
            FROM warehouses w
            LEFT JOIN warehouse_stock ws ON w.warehouse_id = ws.warehouse_id
            GROUP BY w.warehouse_id
            ORDER BY w.warehouse_name;
                                │
                                ▼
                    [Display Report]
                    
    ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
    ┃  Warehouse  │ Location │ IN    │ OUT  │ Balance ┃
    ┣━━━━━━━━━━━━━╋━━━━━━━━━━╋━━━━━━━╋━━━━━━╋━━━━━━━━━┫
    ┃ Warehouse 1 │ Loc-A    │ 250   │ 100  │ 150     ┃
    ┃ Warehouse 2 │ Loc-B    │ 230   │ 50   │ 180     ┃
    ┃ Warehouse 3 │ Loc-C    │ 0     │ 0    │ 0       ┃
    ┗━━━━━━━━━━━━━┻━━━━━━━━━━┻━━━━━━━┻━━━━━━┻━━━━━━━━━┛
    
    TOTAL:                  480 MT   150 MT   330 MT
```

---

## KEY TAKEAWAYS

### 1. **Code-Based Linking**
Every transaction traces back to rake_code:
```
E-Bill → Builty → Warehouse Stock → Original Builty → Rake
```

### 2. **Two Builty Types**
- **BLT-*** (RakePoint): Rake → Warehouse transport
- **BLTO-*** (Warehouse): Warehouse → Customer dispatch

### 3. **Critical Validations**
- Stock IN: Cannot exceed builty capacity
- Stock OUT: Cannot exceed warehouse balance

### 4. **Role Separation**
Each user role has specific functions - no overlap

### 5. **Complete Traceability**
From railway rake to customer delivery - full audit trail

---

**Document Version:** 1.0  
**Date:** October 9, 2025  
**Purpose:** Visual workflow reference for FIMS system
