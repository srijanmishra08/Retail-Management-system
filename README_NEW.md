# 📦 Fertilizer Inventory Management System (FIMS) - REDESIGNED

A role-based fertilizer inventory management system with specific dashboards and workflows for each user type.

## 🎯 System Overview

The system has been completely redesigned with **4 distinct user roles**, each with their own dashboard and specific tasks:

### 👥 User Roles

#### 1. **Admin** (`admin` / `admin123`)
**Capabilities:**
- View comprehensive dashboard with system statistics
- **Add Rake**: Create new rake entries with:
  - Auto-generated rake code
  - Company name and code
  - Date of rake
  - RR quantity
  - Product name and code
  - Rake point name
- **View Summary**: Rake-wise summary showing:
  - Rake code
  - Company name  
  - Date
  - Stock IN
  - Stock OUT
  - Balance
- **Manage Accounts**: Add/manage dealers, retailers, and company accounts

#### 2. **Rake Point User** (`rakepoint` / `rake123`)
**Capabilities:**

**a. Enter Builty Details:**
- Date
- Rake point name
- Account (dealer/retailer name) OR warehouse
- Truck number (automatic selection)
- Loading point
- Unloading point
- Truck driver (automatic/editable)
- Truck owner
- Mobile numbers (truck owner, driver)
- Goods name
- Number of bags
- Quantity (weight in MT)
- Freight details:
  - Number of bags
  - KG per bag
  - Weight in MT (total)
  - Rate per MT
  - Total freight (wt × rate)
- LR number (index, serial number)

**b. Create Loading Slip:**
- Rake code (from admin-uploaded rakes)
- Serial number
- Loading point name
- Destination/unloading point
- Account (dealer/retailer name)
- Quantity in bags
- Quantity in MT
- Truck details
- Wagon number
- **Print Loading Slip** option available

#### 3. **Warehouse Manager** (`warehouse` / `warehouse123`)
**Capabilities:**

**a. Stock IN:**
- Builty number
- Unloaded quantity
- Unloader employee name
- Warehouse name
- Account name (Payal/Company/Dealer)

**b. Stock OUT:**
- Create new builty with same details as rake point builty
- Warehouse name selection
- All freight and truck details

**c. Balance Stock:**
- Real-time calculation: **Stock IN - Stock OUT**
- View transaction history
- Warehouse-wise balance

#### 4. **Accountant** (`accountant` / `account123`)
**Capabilities:**

**a. E-Bill Generation:**
- Create e-bills from builty details
- Bills can be created from rake point OR warehouse builties
- E-bill number generation
- Amount calculation

**b. E-Way Bill Management:**
- Upload e-way bill as PDF for each builty
- Track e-way bill status
- View all generated bills

## 🗄️ Database Schema

### Main Tables:
1. **users** - System users with roles
2. **rakes** - Rake entries (Admin)
3. **accounts** - Dealers, Retailers, Companies
4. **warehouses** - Warehouse locations
5. **trucks** - Truck and driver details
6. **builty** - Bilty/Challan documents
7. **loading_slips** - Loading slips for rakes
8. **warehouse_stock** - Stock IN/OUT transactions
9. **ebills** - E-bills and e-way bills

## 🚀 Quick Start

### 1. **Install Dependencies** (if not already done)
```bash
pip3 install -r requirements.txt
```

### 2. **Run the Application**
```bash
python3 app.py
```

### 3. **Access the System**
Open browser: `http://localhost:5001`

### 4. **Login**
Use appropriate credentials based on your role:
- **Admin**: `admin` / `admin123`
- **Rake Point**: `rakepoint` / `rake123`
- **Warehouse**: `warehouse` / `warehouse123`
- **Accountant**: `accountant` / `account123`

## 📋 Current Implementation Status

### ✅ Completed:
- ✅ New database schema with all required tables
- ✅ User authentication with 4 roles
- ✅ Role-based routing (redirects to appropriate dashboard)
- ✅ Admin dashboard template
- ✅ Database operations for all workflows
- ✅ All backend routes for 4 user types

### 🚧 In Progress (Templates Need to be Created):
- Rake Point templates:
  - Create builty form
  - Create loading slip form
  - View loading slips
- Warehouse templates:
  - Stock IN form
  - Stock OUT form
  - Balance view
- Accountant templates:
  - Create e-bill form
  - View all e-bills
  - Upload e-way bill
- Admin templates:
  - Add rake form
  - Summary table
  - Manage accounts

## 📝 Workflow Examples

### Admin Workflow:
1. Login as admin
2. Add new rake with company details
3. View system-wide summary
4. Manage dealer/retailer accounts

### Rake Point Workflow:
1. Login as rakepoint user
2. Create builty for incoming goods
3. Generate loading slip for specific rake
4. Print loading slip
5. Track all builties created

### Warehouse Workflow:
1. Login as warehouse user
2. Record Stock IN from builty
3. Check current balance
4. Create Stock OUT with new builty
5. View transaction history

### Accountant Workflow:
1. Login as accountant
2. View pending builties (without e-bills)
3. Create e-bill from builty
4. Upload e-way bill PDF
5. Track all generated bills

## 🔧 Key Features

### Smart Truck Management:
- Automatic truck number selection
- Store driver and owner details
- Reuse truck data across builties

### Flexible Destination:
- Builty can go to **Account** (Dealer/Retailer) OR **Warehouse**
- Tracks origin (Rake Point or Warehouse)

### Real-time Stock Calculation:
- Balance = Stock IN - Stock OUT
- Warehouse-wise tracking
- Transaction history

### Complete Billing System:
- E-bill generation from builty
- E-way bill PDF upload
- Amount tracking

## 📂 Project Structure

```
Retail-Management-system/
├── app.py                    # Main application (NEW - role-based)
├── database.py               # Database operations (NEW schema)
├── requirements.txt          # Dependencies
├── fims.db                   # SQLite database (auto-created)
│
├── templates/
│   ├── base.html            # Base template with sidebar
│   ├── login.html           # Login page
│   │
│   ├── admin/               # Admin templates
│   │   ├── dashboard.html   # ✅ Created
│   │   ├── add_rake.html    # 🚧 To be created
│   │   ├── summary.html     # 🚧 To be created
│   │   └── manage_accounts.html # 🚧 To be created
│   │
│   ├── rakepoint/           # Rake Point templates
│   │   ├── dashboard.html   # 🚧 To be created
│   │   ├── create_builty.html # 🚧 To be created
│   │   ├── create_loading_slip.html # 🚧 To be created
│   │   └── loading_slips.html # 🚧 To be created
│   │
│   ├── warehouse/           # Warehouse templates
│   │   ├── dashboard.html   # 🚧 To be created
│   │   ├── stock_in.html    # 🚧 To be created
│   │   ├── stock_out.html   # 🚧 To be created
│   │   └── balance.html     # 🚧 To be created
│   │
│   └── accountant/          # Accountant templates
│       ├── dashboard.html   # 🚧 To be created
│       ├── create_ebill.html # 🚧 To be created
│       └── all_ebills.html  # 🚧 To be created
│
└── OLD_FILES/               # Backup of previous system
    ├── app_old.py
    ├── database_old.py
    └── fims_old.db
```

## 🔄 Migration from Old System

The old system files have been backed up:
- `app_old.py` - Old Flask app
- `database_old.py` - Old database schema
- `fims_old.db` - Old database

## 🛠️ Next Steps

1. **Complete Template Creation**: Create all remaining HTML templates for the 4 user roles
2. **Test Workflows**: Test each user role's complete workflow
3. **PDF Generation**: Implement loading slip and e-bill PDF generation
4. **E-way Bill Upload**: Add file upload functionality for e-way bills
5. **Validation**: Add form validation and error handling
6. **UI Polish**: Enhance UI/UX for better usability

## 📞 Support

For questions or issues:
1. Check the SRS.txt document for detailed requirements
2. Review database.py for available operations
3. Check app.py for routing logic

---

**Version**: 2.0.0 (Redesigned)  
**Last Updated**: October 2025  
**Status**: Backend Complete, Frontend Templates In Progress
