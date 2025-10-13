# FIMS - Quick Reference Card

## 🚀 5-Minute System Overview

### What is FIMS?
**Fertilizer Inventory Management System** - Tracks fertilizer from railway rake arrival to customer delivery with complete traceability.

### Core Concept
**Everything links to Rake Code (RK-*)**
```
Railway Rake → Builty → Warehouse Stock → Dispatch Builty → E-Bill
     ↑_____________ All trace back to this _________________↑
```

---

## 👥 4 User Roles

| Role | Username | Password | Main Function |
|------|----------|----------|---------------|
| **Admin** | admin | admin123 | Create rakes, manage system |
| **RakePoint** | rakepoint | rake123 | Create builties, loading slips |
| **Warehouse** | warehouse | warehouse123 | Stock IN/OUT operations |
| **Accountant** | accountant | account123 | Generate e-bills |

**Access:** http://127.0.0.1:5001

---

## 📝 Key Documents (In Order of Importance)

1. **README_DOCUMENTATION.md** - Start here! (Navigation guide)
2. **USER_GUIDE.md** - How to use the system
3. **BUSINESS_LOGIC_ANALYSIS.md** - Complete architecture (28 KB)
4. **SYSTEM_WORKFLOWS.md** - Visual diagrams (39 KB)
5. **IMPROVEMENTS_ROADMAP.md** - Future enhancements (32 KB)
6. **VISUAL_SYSTEM_MAP.txt** - ASCII diagrams (26 KB)
7. **SRS.txt** - Original requirements

**Total Documentation:** ~150 KB / 8 files

---

## 🔑 Critical Concepts

### 1. Two Builty Types

**Type A: BLT-YYYYMMDD-HHMMSS** (RakePoint creates)
- Purpose: Transport from rake to warehouse
- Created when: Loading goods at rake point
- Links to: Selected rake_code

**Type B: BLTO-YYYYMMDD-HHMMSS** (Warehouse creates)
- Purpose: Dispatch from warehouse to customer
- Created when: Stock OUT operation
- Links to: Auto-detected rake_code (from warehouse history)

### 2. Two Distribution Paths

**Path A: Warehouse Storage**
```
Rake → RakePoint (creates BLT-*) → Warehouse (Stock IN)
     → Later: Warehouse (Stock OUT, creates BLTO-*) → Customer
```

**Path B: Direct Dispatch**
```
Rake → RakePoint (creates BLT-* to account) → Customer directly
     (No warehouse storage)
```

### 3. Critical Validations

**Stock IN:**
```
IF (Total Stock IN for builty) > (Builty's original quantity):
   ✗ REJECT: "Builty has only X MT remaining"
```

**Stock OUT:**
```
IF (Requested quantity) > (Warehouse balance):
   ✗ REJECT: "Warehouse has only X MT available"
```

---

## 📊 Quick Database Reference

### 9 Tables

1. **users** - 4 roles (Admin, RakePoint, Warehouse, Accountant)
2. **rakes** - Source of all data (rake_code is the link)
3. **accounts** - Customers (Dealers, Retailers, Company)
4. **warehouses** - 3 storage locations
5. **trucks** - Transportation vehicles
6. **builty** - Transportation documents (2 types)
7. **loading_slips** - Rake unloading records
8. **warehouse_stock** - Stock IN/OUT transactions
9. **ebills** - Financial billing documents

### Foreign Key Chain
```
rakes.rake_code
  ↓
builty.rake_code
  ↓
warehouse_stock.builty_id
  ↓
ebills.builty_id
```

---

## 🎯 Common Operations

### Admin: Add New Rake (START HERE!)
1. Login as admin/admin123
2. Click "Add Rake"
3. Fill: Rake Code, Company, Product, RR Quantity
4. **This is the foundation - all other operations need this!**

### RakePoint: Create Builty
1. Login as rakepoint/rake123
2. Click "Create Builty"
3. **SELECT RAKE CODE FIRST** (critical!)
4. Fill 14 fields (truck, quantity, freight, etc.)
5. System auto-fills: Rake Point Name, Goods Name

### Warehouse: Stock IN
1. Login as warehouse/warehouse123
2. Click "Stock IN"
3. Select Builty Number (from dropdown)
4. Enter: Unloaded Quantity, Warehouse, Employee
5. **System validates:** Quantity not exceeding builty capacity

### Warehouse: Stock OUT
1. Login as warehouse/warehouse123
2. Click "Stock OUT"
3. Select Warehouse
4. **Create complete NEW builty** (14 fields again!)
5. System auto-generates: BLTO-YYYYMMDD-HHMMSS
6. **System validates:** Quantity not exceeding warehouse balance

### Accountant: Create E-Bill
1. Login as accountant/account123
2. Click "Create E-Bill"
3. Select Builty (shows complete chain)
4. Fill: E-Bill Number, Amount, Date
5. Upload Eway Bill PDF (optional)

---

## 🔍 Traceability Example

**Question:** Where did this e-bill come from?

```
E-Bill: EB-2023-001 (₹1,50,000)
  ↓ (query: SELECT builty_id FROM ebills WHERE...)
Builty: BLTO-20231010-103045 (Stock OUT builty)
  ↓ (query: SELECT rake_code FROM builty WHERE...)
  ↓ (check: warehouse_stock to find original builty)
Builty: BLT-20231008-143022 (Stock IN builty)
  ↓ (query: SELECT * FROM rakes WHERE rake_code=...)
Rake: RK-2023-001
  • Company: ABC Fertilizers
  • Product: Urea
  • RR Quantity: 500 MT
  • Date: 2023-10-01
```

**Answer:** From ABC Fertilizers' Urea rake (RK-2023-001, 500 MT)

---

## ⚠️ Common Issues & Solutions

### Issue 1: "No rakes found" when creating builty
**Solution:** Login as Admin first and create at least one rake

### Issue 2: Stock IN shows 0 MT on dashboard
**Solution:** Check if you used LEFT JOIN in query (accounts can be NULL)

### Issue 3: Duplicate stock IN entries
**Solution:** Validation now prevents this! System checks builty capacity

### Issue 4: Can't dispatch from warehouse
**Solution:** Ensure warehouse has sufficient balance (Stock IN > Stock OUT)

### Issue 5: E-Bill error "already exists"
**Solution:** Each builty can only have one e-bill (by design)

---

## 📈 System Status (Current)

### ✅ Working Features
- ✓ 4-role authentication
- ✓ Rake creation with code system
- ✓ Builty creation (2 types)
- ✓ Loading slip management
- ✓ Stock IN/OUT with validations
- ✓ E-Bill generation
- ✓ Dashboard statistics
- ✓ Basic reports

### ⚠️ Missing (From SRS)
- ⚠️ Rent calculation (daily per MT)
- ⚠️ Lifting charges (per MT dispatch)
- ⚠️ Stock aging reports
- ⚠️ PDF/Excel export
- ⚠️ Advanced financial summaries

---

## 🚀 Next Steps

### For New Users
1. Read USER_GUIDE.md (15 min)
2. Login and explore each role (30 min)
3. Create test data (30 min)
   - Admin: Add rake
   - RakePoint: Create builty
   - Warehouse: Stock IN/OUT
   - Accountant: Create e-bill

### For Developers
1. Read BUSINESS_LOGIC_ANALYSIS.md (1 hour)
2. Study SYSTEM_WORKFLOWS.md (30 min)
3. Review code in app.py and database.py (1 hour)
4. Check IMPROVEMENTS_ROADMAP.md for tasks (30 min)

### For Managers
1. Review README_DOCUMENTATION.md (20 min)
2. Check system status in IMPROVEMENTS_ROADMAP.md (15 min)
3. Compare with SRS.txt for gaps (15 min)
4. Plan priorities from roadmap (30 min)

---

## 💡 Pro Tips

1. **Always start with Admin** - Create rake first, everything else follows
2. **Rake Code is the key** - All reports, queries, traceability depend on it
3. **Two builty types** - BLT for IN, BLTO for OUT (remember this!)
4. **Watch the validations** - They prevent 90% of errors
5. **Use Loading Slips** - Good for wagon-wise tracking
6. **E-Bills need Builty** - Can't bill without a builty
7. **Stock OUT creates new builty** - Not reusing old one (new truck, new freight)
8. **Left Join for accounts** - Builty can go to warehouse (account_id = NULL)

---

## 📞 Quick Help

### If you need to...
- **Understand architecture** → BUSINESS_LOGIC_ANALYSIS.md
- **See workflows** → SYSTEM_WORKFLOWS.md
- **Learn usage** → USER_GUIDE.md
- **Find improvements** → IMPROVEMENTS_ROADMAP.md
- **Navigate docs** → README_DOCUMENTATION.md
- **See ASCII diagrams** → VISUAL_SYSTEM_MAP.txt
- **Check requirements** → SRS.txt

### If you're stuck...
1. Check USER_GUIDE.md Troubleshooting section
2. Review relevant workflow in SYSTEM_WORKFLOWS.md
3. Verify data in database (use sqlite3 fims.db)
4. Check terminal for error messages
5. Review validation logic in BUSINESS_LOGIC_ANALYSIS.md

---

## 📊 Quick Stats

| Metric | Value |
|--------|-------|
| **Database Tables** | 9 |
| **Application Routes** | 20+ |
| **User Roles** | 4 |
| **Templates** | 15+ |
| **Validations** | 4 critical |
| **Documentation Files** | 8 (150 KB) |
| **Code Files** | 3 main (app.py, database.py, reports.py) |
| **Lines of Code** | ~2000+ |

---

## 🎯 Success Criteria

You've mastered FIMS when you can:
- ✓ Explain the rake_code linking system
- ✓ Describe the difference between BLT-* and BLTO-*
- ✓ Trace an e-bill back to its original rake
- ✓ Understand why Stock IN validation is critical
- ✓ Know when to use warehouse path vs direct dispatch
- ✓ Create complete workflow from rake to e-bill

---

**Document:** Quick Reference Card  
**Version:** 1.0  
**Date:** October 9, 2025  
**Purpose:** Fast lookup for common tasks and concepts

**Print this page for quick reference!**
