# FIMS Code-Based System Architecture

## Overview
The Fertilizer Inventory Management System (FIMS) is a **code-based interconnected system** where all operations are linked through unique codes created by the Admin. This creates a dynamic, traceable flow from Rake creation to final e-billing.

## Code Hierarchy & Flow

```
ADMIN CREATES
    ↓
[RAKE CODE] → Links everything together
    ↓
RAKE POINT CREATES
    ↓
[BUILTY] → Links to Rake Code + Account/Warehouse + Truck
    ↓
[LOADING SLIP] → Links to Rake Code + Builty
    ↓
WAREHOUSE PROCESSES
    ↓
[STOCK IN] → Links to Builty + Warehouse
    ↓
[STOCK OUT] → Creates new Builty + Stock transaction
    ↓
ACCOUNTANT CREATES
    ↓
[E-BILL] → Links to Builty + Eway Bill PDF
```

## 1. ADMIN - The Foundation Creator

### Creates Rakes (Master Data)
**Fields:**
- **Rake Code** (Unique) - e.g., RK001, RK2023-001
- Company Name + Company Code
- Product Name + Product Code (Urea, DAP, etc.)
- RR Quantity (Railway Receipt Quantity in MT)
- Rake Point Name
- Date

**Purpose:** Creates the master rake entries that all other operations link to.

**Code Example:**
```
Rake Code: RK2023-001
Company: ABC Fertilizers
Product: Urea
RR Quantity: 500 MT
Rake Point: Main Depot
```

### Manages Accounts
**Types:**
- Dealers
- Retailers  
- Companies

**Purpose:** Creates account codes that link to builties and stock transactions.

---

## 2. RAKE POINT USER - Creates Builty & Loading Slips

### Creates Builty (14 Fields + Rake Link)
**CRITICAL: Must select Rake Code first!**

When a Rake Code is selected:
- Rake Point Name auto-fills from rake
- Goods Name auto-fills from rake's product

**14 Fields:**
1. Date
2. Rake Point Name (auto-filled)
3. Account/Warehouse (dropdown)
4. Truck Number (manual or from truck database)
5. Loading Point
6. Unloading Point
7. Truck Driver (auto-filled if truck exists, else manual)
8. Truck Owner
9. Mobile Number 1
10. Mobile Number 2
11. Goods Name (auto-filled from rake product)
12. Number of Bags
13. Quantity (Weight in MT)
14. Freight Details
15. LR Number

**Code Links Created:**
```
Builty BLT-20231008-143022
    ├─ Rake Code: RK2023-001 (LINK)
    ├─ Account: Dealer ABC (LINK)
    ├─ Truck: MH-12-AB-1234 (LINK)
    └─ LR Number: LR12345
```

### Creates Loading Slip
**Links to:**
- Rake Code (required)
- Serial Number
- Account
- Truck Number
- Wagon Number

**Purpose:** Documents the loading from rake to trucks/wagons.

---

## 3. WAREHOUSE USER - Stock Management

### Stock IN
**Links to:**
- **Builty Number** (required) - This connects to the rake through builty's rake_code
- Warehouse Name
- Account Name (auto-filled from builty)
- Unloaded Quantity
- Unloader Employee

**Flow:**
```
Builty BLT-20231008-143022
    ├─ Linked Rake: RK2023-001
    └─ Stock IN to Warehouse: WH-001
        └─ Unloaded: 25.50 MT
```

### Stock OUT
**Creates New Builty + Stock Transaction**

When warehouse dispatches stock:
1. Select Warehouse
2. Create new builty with all 14 fields
3. System automatically:
   - Links to original rake code
   - Records stock OUT transaction
   - Reduces warehouse balance

**Balance Calculation:**
```
For Each Warehouse:
    Balance = Stock IN - Stock OUT

For Each Rake Code:
    RR Quantity = Original quantity from rake
    Total Stock IN = All builties linked to this rake
    Total Stock OUT = All stock OUT for this rake
    Balance = Stock IN - Stock OUT
```

---

## 4. ACCOUNTANT - E-Billing & Eway Bills

### Creates E-Bill from Builty
**Links to:**
- **Builty** (auto-fills all details)
- E-Bill Number
- Amount
- Tax Amount
- Eway Bill Number
- Eway Bill PDF Upload

**Complete Traceability:**
```
E-Bill EB-2023-001
    └─ Builty: BLT-20231008-143022
        └─ Rake: RK2023-001
            ├─ Company: ABC Fertilizers
            ├─ Product: Urea
            └─ Account: Dealer XYZ
```

---

## Database Relationships (Code Links)

### Foreign Key Relationships:
```sql
builty table:
    ├─ rake_code → rakes.rake_code (THE MAIN LINK)
    ├─ account_id → accounts.account_id
    ├─ warehouse_id → warehouses.warehouse_id
    └─ truck_id → trucks.truck_id

loading_slips table:
    ├─ rake_code → rakes.rake_code
    ├─ account_id → accounts.account_id
    └─ truck_id → trucks.truck_id

warehouse_stock table:
    ├─ warehouse_id → warehouses.warehouse_id
    ├─ builty_id → builty.builty_id (links to rake through builty)
    └─ account_id → accounts.account_id

ebills table:
    └─ builty_id → builty.builty_id (links to rake through builty)
```

---

## How Codes Work Together - Example Workflow

### Step 1: Admin Creates Foundation
```
Admin adds Rake: RK2023-001
    Company: ABC Fertilizers (Code: ABC01)
    Product: Urea (Code: URE01)
    RR Quantity: 500 MT
    Rake Point: Main Depot
```

### Step 2: Rake Point Creates Builty
```
Rake Point User logs in:
1. Selects Rake Code: RK2023-001
   → Auto-fills: Rake Point Name = "Main Depot"
   → Auto-fills: Goods Name = "Urea"
   
2. Fills 14 fields:
   - Account: Dealer XYZ
   - Truck: MH-12-AB-1234
   - Quantity: 25.50 MT
   - etc.
   
3. System generates: Builty BLT-20231008-143022
   → Linked to Rake: RK2023-001 ✓
```

### Step 3: Warehouse Receives Stock
```
Warehouse User logs in:
1. Stock IN Entry
2. Selects Builty: BLT-20231008-143022
   → Auto-fills Account from builty
   → Knows which rake it's from (RK2023-001)
   
3. Records: 25.50 MT received at WH-001
```

### Step 4: Warehouse Dispatches Stock
```
Warehouse User creates Stock OUT:
1. Select Warehouse: WH-001
2. Create new builty (14 fields)
   → System links to same Rake Code: RK2023-001
3. Quantity: 10.00 MT
4. Balance updated: 25.50 - 10.00 = 15.50 MT
```

### Step 5: Accountant Creates E-Bill
```
Accountant logs in:
1. Selects Builty: BLT-20231008-143022
   → Sees full details:
      - Rake: RK2023-001
      - Company: ABC Fertilizers
      - Product: Urea
      - Account: Dealer XYZ
      - Truck: MH-12-AB-1234
      - Quantity: 25.50 MT
      
2. Creates E-Bill: EB-2023-001
3. Uploads Eway Bill PDF
```

---

## Summary Reports Available

### 1. Admin Summary (by Rake Code)
```
Rake Code | Company | RR Qty | Stock IN | Stock OUT | Balance
----------|---------|--------|----------|-----------|--------
RK2023-001| ABC Fert| 500 MT | 450 MT   | 200 MT    | 250 MT
RK2023-002| XYZ Ltd | 600 MT | 580 MT   | 300 MT    | 280 MT
```

### 2. Warehouse Balance (by Warehouse)
```
Warehouse | Stock IN | Stock OUT | Balance | Status
----------|----------|-----------|---------|--------
WH-001    | 250 MT   | 100 MT    | 150 MT  | Medium
WH-002    | 200 MT   | 180 MT    | 20 MT   | Low
```

### 3. Accountant E-Bills (by Builty)
```
E-Bill No  | Builty          | Rake      | Amount  | Eway Bill
-----------|-----------------|-----------|---------|----------
EB-2023-01 | BLT-20231008-01 | RK2023-01 | ₹50,000 | Uploaded ✓
```

---

## Why This Code System is Powerful

### 1. **Complete Traceability**
Every transaction can be traced back to the original rake:
```
E-Bill → Builty → Rake → Company & Product
```

### 2. **Dynamic Linking**
No hardcoded values - everything is linked through codes created by Admin

### 3. **Data Consistency**
When Admin adds a rake with Product "Urea", all builties linked to that rake automatically show "Urea"

### 4. **Accurate Balancing**
System can calculate:
- Stock by Rake Code
- Stock by Warehouse
- Stock by Account
- Total balance across entire system

### 5. **Audit Trail**
Complete history of:
- Which rake the goods came from
- Which warehouse stored them
- Which account received them
- Which e-bills were generated

---

## Key Features of Code-Based System

✅ **Admin Control** - All master codes created by Admin
✅ **Auto-Fill** - Related data auto-fills based on code selection  
✅ **Foreign Keys** - Database enforces relationships
✅ **No Duplicates** - Unique codes prevent errors
✅ **Cascading Updates** - Change rake details, all linked records updated
✅ **Multi-Level Tracking** - Rake → Builty → Stock → E-Bill
✅ **Real-time Balance** - Calculated from all linked transactions

This code-based architecture ensures the entire fertilizer management system runs smoothly with complete data integrity and traceability!
