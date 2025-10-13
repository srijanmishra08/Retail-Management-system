# 📦 Fertilizer Inventory Management System (FIMS)

A comprehensive web-based inventory management system for managing fertilizer distribution from rake points to warehouses, dispatches to dealers, and billing operations.

## 🎯 Features

### Core Modules

1. **Rake Management**
   - Add and track incoming rakes from suppliers
   - Record rake unloading details
   - Allocate stock to warehouses or direct market dispatch
   - Track rake-wise inventory

2. **Warehouse Management**
   - Manage 3 warehouse locations
   - Track stock in/out operations
   - Monitor current stock levels
   - Low stock alerts
   - Per-lot tracking with rent calculation

3. **Dispatch Management**
   - Record dispatches to dealers, government, and own company
   - Truck-wise tracking
   - Transport company details
   - Automatic stock deduction

4. **Billing & Rent Module**
   - Generate transportation bills
   - Calculate warehouse rent (per day per MT)
   - Calculate lifting charges
   - Download bills as PDF
   - Billing summary and analytics

5. **Reports & Analytics**
   - Dashboard with key statistics
   - Rake-wise reports
   - Warehouse-wise stock reports
   - Dealer-wise dispatch reports
   - Billing summary reports

## 🚀 Quick Start

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)

### Installation

1. **Clone or navigate to the project directory**
   ```bash
   cd /Users/s/Documents/Retail-Management-system
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application**
   ```bash
   python app.py
   ```

4. **Access the application**
   - Open your browser and navigate to: `http://localhost:5000`
   - The database will be automatically created on first run

## 👥 Default User Credentials

| Role | Username | Password |
|------|----------|----------|
| Admin/Manager | `admin` | `admin123` |
| Warehouse Worker | `warehouse1` | `warehouse123` |
| Dispatch Clerk | `dispatch1` | `dispatch123` |
| Billing Officer | `billing1` | `billing123` |

## 📂 Project Structure

```
Retail-Management-system/
│
├── app.py                 # Main Flask application
├── database.py            # Database operations and queries
├── reports.py             # PDF report generation
├── requirements.txt       # Python dependencies
├── SRS.txt               # Software Requirements Specification
├── fims.db               # SQLite database (auto-created)
│
├── templates/            # HTML templates
│   ├── base.html
│   ├── login.html
│   ├── dashboard.html
│   ├── rakes.html
│   ├── warehouses.html
│   ├── dispatches.html
│   ├── billing.html
│   ├── reports.html
│   └── settings.html
│
└── reports/              # Generated PDF reports (auto-created)
```

## 🔧 Configuration

### Database
- The system uses SQLite for data storage
- Database file: `fims.db` (automatically created)
- All tables and default data are initialized on first run

### Customization
- Modify warehouse capacity in Settings
- Add new suppliers, dealers, and users
- Configure billing rates per dispatch

## 📊 Database Schema

### Main Tables
- **users** - System users with role-based access
- **suppliers** - Fertilizer suppliers
- **warehouses** - Warehouse locations
- **dealers** - Customers and dealers
- **rakes** - Incoming rake shipments
- **warehouse_stock** - Stock tracking per warehouse
- **dispatches** - Outgoing dispatches
- **billing** - Bills for transport, rent, and lifting

## 🎨 User Interface

- **Modern Bootstrap 5** design
- **Responsive** layout for desktop and tablet
- **Role-based navigation** and access control
- **Real-time statistics** on dashboard
- **Interactive forms** with validation
- **Data tables** with sorting and filtering

## 🔐 Security Features

- Password hashing using Werkzeug
- Session-based authentication
- Role-based access control (RBAC)
- CSRF protection via Flask
- Secure password storage

## 📝 Usage Guide

### Adding a New Rake
1. Navigate to **Rakes** section
2. Click **"Add New Rake"**
3. Fill in rake details (number, supplier, date, quantity)
4. Select allocation type (Warehouse or Market Dispatch)
5. If warehouse, select destination warehouse
6. Submit to add rake

### Recording a Dispatch
1. Go to **Dispatches**
2. Click **"Add Dispatch"**
3. Select source warehouse
4. Choose destination type and dealer
5. Enter truck details and quantity
6. Set dispatch date
7. Submit to create dispatch

### Generating Bills
1. Navigate to **Billing** section
2. View pending dispatches
3. Click **"Generate Bill"**
4. Select bill type (Transport/Rent/Lifting)
5. Enter rate and other details
6. System calculates total amount
7. Submit to generate bill
8. Download PDF invoice

## 🛠️ Technologies Used

- **Backend**: Python 3, Flask
- **Database**: SQLite3
- **Frontend**: HTML5, CSS3, Bootstrap 5
- **Authentication**: Flask-Login
- **PDF Generation**: ReportLab
- **Icons**: Bootstrap Icons

## 📈 Future Enhancements

- [ ] Excel export functionality
- [ ] Advanced analytics and charts
- [ ] Email notifications for low stock
- [ ] Multi-language support
- [ ] Mobile app integration
- [ ] Barcode/QR code scanning
- [ ] Advanced user management
- [ ] Audit trail logging

## 🐛 Troubleshooting

### Database Issues
```bash
# If database gets corrupted, delete and restart
rm fims.db
python app.py
```

### Port Already in Use
```bash
# Change port in app.py (last line)
app.run(debug=True, host='0.0.0.0', port=5001)
```

### Dependencies Not Installing
```bash
# Upgrade pip first
pip install --upgrade pip
pip install -r requirements.txt
```

## 📄 License

This project is developed for internal use in fertilizer inventory management.

## 👨‍💻 Support

For issues or questions, refer to the SRS.txt document for detailed system specifications.

---

**Version**: 1.0.0  
**Last Updated**: October 2025  
**Built with** ❤️ **for efficient fertilizer inventory management**
