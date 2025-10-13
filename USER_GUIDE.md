# FIMS User Guide - Quick Start

## Login Credentials

| Role | Username | Password |
|------|----------|----------|
| Admin | admin | admin123 |
| Rake Point | rakepoint | rake123 |
| Warehouse | warehouse | warehouse123 |
| Accountant | accountant | account123 |

**Access URL:** http://127.0.0.1:5001

---

## Admin User Guide

### 1. Add a New Rake (START HERE!)
**This is the FOUNDATION of the entire system**

1. Login as Admin
2. Click **"Add Rake"** from sidebar or dashboard
3. Fill in:
   - **Rake Code** (e.g., RK2023-001) - UNIQUE identifier
   - Company Name + Code
   - Product Name + Code (e.g., Urea, DAP)
   - RR Quantity (Railway Receipt quantity in MT)
   - Rake Point Name
   - Date
4. Click **"Add Rake"**

**Important:** All builties, loading slips, and stock transactions will link to this Rake Code!

### 2. Manage Accounts
1. Click **"Manage Accounts"**
2. Click **"Add Account"** button
3. Fill in:
   - Account Name
   - Type (Dealer / Retailer / Company)
   - Contact & Address
4. Click **"Add Account"**

### 3. View Summary
- Click **"Rake Summary"** to see:
  - Each rake's RR Quantity
  - Stock IN (total received)
  - Stock OUT (total dispatched)
  - Balance (IN - OUT)

---

## Rake Point User Guide

### 1. Create Builty (14 Fields + Rake Link)

**CRITICAL FIRST STEP:** Select Rake Code!

1. Login as Rake Point user
2. Click **"Create Builty"**
3. **STEP 1: Select Rake Code** (dropdown)
   - This auto-fills:
     - Rake Point Name
     - Goods Name (from rake's product)
4. Fill 14 Fields:
   - **Date:** Today (auto-filled)
   - **Rake Point Name:** Auto-filled from rake
   - **Account/Warehouse:** Select from dropdown
   - **Truck Number:** Enter or select
   - **Loading Point:** Enter location
   - **Unloading Point:** Enter destination
   - **Truck Driver:** Enter name
   - **Truck Owner:** Enter name
   - **Mobile Number 1:** Required
   - **Mobile Number 2:** Optional
   - **Goods Name:** Auto-filled from rake
   - **Number of Bags:** Enter count
   - **Quantity (Weight in MT):** Enter weight
   - **Freight Details:** Enter amount
   - **LR Number:** Enter LR number
5. Click **"Create Builty"**

**Result:** Builty created and LINKED to selected Rake!

### 2. Create Loading Slip
1. Click **"Create Loading Slip"**
2. Fill in:
   - Rake Code (links to rake)
   - Serial Number
   - Loading Point & Destination
   - Account
   - Quantity (bags & MT)
   - Truck & Wagon Numbers
3. Choose:
   - **"Save & Print"** - Saves and opens print dialog
   - **"Save"** - Just saves

### 3. View Loading Slips
- Click **"View All Loading Slips"** to see complete list

---

## Warehouse User Guide

### 1. Record Stock IN
**When goods arrive at warehouse**

1. Login as Warehouse user
2. Click **"Stock IN"** from sidebar/dashboard
3. Fill in:
   - **Builty Number:** Select from dropdown
     - System auto-fills Account Name from builty
     - System knows which Rake it's from
   - **Unloaded Quantity (MT):** Actual quantity unloaded
   - **Unloader Employee:** Employee name
   - **Warehouse Name:** Select warehouse
   - **Stock IN Date:** Today (auto-filled)
   - **Remarks:** Optional notes
4. Click **"Record Stock IN"**

**Result:** Stock added to warehouse, linked to Builty → Rake

### 2. Record Stock OUT
**When dispatching goods from warehouse**

1. Click **"Stock OUT"**
2. Select **Warehouse Name**
3. Create **New Builty** (same 14 fields as Rake Point)
   - System automatically links to same Rake Code
   - Fill all 14 required fields
4. Click **"Record Stock OUT"**

**Result:** 
- New builty created for outgoing stock
- Stock deducted from warehouse
- Linked to original Rake Code

### 3. View Balance
1. Click **"View Balance"**
2. See reports:
   - **By Warehouse:** Stock IN/OUT/Balance per warehouse
   - **By Account:** Stock distribution by account
   - **Overall Totals:** Complete system balance

---

## Accountant User Guide

### 1. Create E-Bill from Builty
1. Login as Accountant
2. Click **"Create E-Bill"** from sidebar/dashboard
3. **Select Builty:** Choose from dropdown
   - System shows complete details:
     - Rake Code → Company → Product
     - Account, Truck, Quantity
     - Loading/Unloading points
4. Fill E-Bill Details:
   - E-Bill Number (auto or manual)
   - E-Bill Date (today auto-filled)
   - Amount (₹)
   - Tax Amount (optional)
   - Description (optional)
5. **Upload Eway Bill (Optional):**
   - Eway Bill Number
   - Upload PDF file (max 5MB)
6. Click **"Create E-Bill"**

**Result:** E-Bill created with complete traceability to Rake

### 2. View All E-Bills
1. Click **"View All E-Bills"** or **"All E-Bills"**
2. Use filters:
   - Date Range (From/To)
   - Status (Uploaded / Pending)
3. Actions available:
   - View details
   - Print e-bill
   - Upload eway bill (if not uploaded)
   - View PDF (if uploaded)

---

## Common Operations

### How to Trace a Transaction
**Example: Find which rake a specific e-bill came from**

1. View E-Bill → See Builty Number
2. Builty shows → Rake Code
3. Rake shows → Company, Product, RR Quantity

**Complete Chain:**
```
E-Bill EB-2023-001
  └─> Builty BLT-20231008-143022
      └─> Rake RK2023-001
          └─> ABC Fertilizers, Urea, 500 MT
```

### How Stock Balance is Calculated

**Per Rake:**
```
RR Quantity (from Admin's rake entry)
- Stock IN (all builties linked to this rake)
- Stock OUT (all warehouse dispatches for this rake)
= Balance
```

**Per Warehouse:**
```
Stock IN (all builties received)
- Stock OUT (all builties dispatched)
= Current Balance
```

---

## Tips & Best Practices

### For Admin:
- ✅ Create all Rakes FIRST before other users start work
- ✅ Use consistent naming for Rake Codes (e.g., RK-2023-001, RK-2023-002)
- ✅ Add all Accounts/Warehouses before Rake Point starts creating builties
- ✅ Check Summary regularly to monitor stock flow

### For Rake Point:
- ✅ ALWAYS select Rake Code first when creating builty
- ✅ Verify auto-filled data (rake point name, goods name)
- ✅ Keep LR Numbers unique and accurate
- ✅ Double-check quantities before submitting

### For Warehouse:
- ✅ Verify builty details before recording Stock IN
- ✅ Record unloaded quantity accurately (may differ from builty quantity)
- ✅ For Stock OUT, create complete new builty with all details
- ✅ Check Balance report regularly

### For Accountant:
- ✅ Create E-Bills promptly after builty creation
- ✅ Upload Eway Bill PDFs immediately
- ✅ Use filters to find pending uploads
- ✅ Keep E-Bill numbers consistent and sequential

---

## Troubleshooting

### "No rakes found" in Builty creation
**Solution:** Login as Admin and add at least one Rake first

### "Unique constraint failed: rake_code"
**Solution:** Rake Code already exists, use a different code

### Auto-fill not working
**Solution:** Make sure you selected from dropdown (not typing manually)

### Can't find a builty
**Solution:** Check if it was created by correct user role (Rake Point or Warehouse)

### Balance doesn't match
**Solution:** Check all Stock IN and Stock OUT entries for that rake/warehouse

---

## Report Generation

### Available Reports:

1. **Admin Summary** (Admin → Summary)
   - Rake-wise balance sheet
   - RR vs Stock IN/OUT comparison

2. **Warehouse Balance** (Warehouse → View Balance)
   - Warehouse-wise stock levels
   - Account-wise distribution
   - Overall system balance

3. **E-Bill List** (Accountant → All E-Bills)
   - Filtered by date/status
   - Printable format
   - Eway bill tracking

**All reports are printable** - Click Print button and use browser print dialog

---

## Data Flow Diagram

```
┌─────────┐
│  ADMIN  │ Creates Rake (RK2023-001)
└────┬────┘
     │
     ├─> Rake Code: RK2023-001
     │   Company: ABC Fertilizers
     │   Product: Urea (500 MT)
     │
┌────▼──────────┐
│  RAKE POINT   │ Creates Builty (linked to RK2023-001)
└────┬──────────┘
     │
     ├─> Builty: BLT-20231008-143022
     │   Rake: RK2023-001 ←─ LINK
     │   Truck: MH-12-AB-1234
     │   Quantity: 25.50 MT
     │
┌────▼───────────┐
│   WAREHOUSE    │ Records Stock IN/OUT
└────┬───────────┘
     │
     ├─> Stock IN: 25.50 MT
     │   From Builty: BLT-20231008-143022
     │   Warehouse: WH-001
     │
┌────▼─────────┐
│  ACCOUNTANT  │ Creates E-Bill
└──────────────┘
     │
     └─> E-Bill: EB-2023-001
         From Builty: BLT-20231008-143022
         Amount: ₹50,000
         Eway Bill: Uploaded ✓
```

---

## Need Help?

- **System not loading?** Make sure Flask app is running on port 5001
- **Login issues?** Use exact credentials from table above
- **Missing features?** Check if you're logged in with correct role
- **Data errors?** Contact system administrator

---

## System Status
✅ All 4 roles functional
✅ All templates created (15 total)
✅ Code-based linking operational
✅ Stock tracking accurate
✅ Complete traceability implemented

**Version:** 1.0
**Last Updated:** October 8, 2025
