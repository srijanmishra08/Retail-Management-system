"""
Fertilizer Inventory Management System (FIMS)
Main Flask Application
"""

from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import os
from database import Database
from reports import ReportGenerator

app = Flask(__name__)
app.secret_key = 'fims-secret-key-change-in-production'

# Initialize database
db = Database()
db.initialize_database()

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# User class for Flask-Login
class User(UserMixin):
    def __init__(self, user_id, username, role):
        self.id = user_id
        self.username = username
        self.role = role

@login_manager.user_loader
def load_user(user_id):
    user_data = db.get_user_by_id(user_id)
    if user_data:
        return User(user_data[0], user_data[1], user_data[3])
    return None

# Context processor to make datetime available in all templates
@app.context_processor
def inject_datetime():
    return {'datetime': datetime}

# ========== Authentication Routes ==========

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user_data = db.authenticate_user(username, password)
        if user_data:
            user = User(user_data[0], user_data[1], user_data[3])
            login_user(user)
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully', 'success')
    return redirect(url_for('login'))

# ========== Dashboard ==========

@app.route('/dashboard')
@login_required
def dashboard():
    stats = db.get_dashboard_stats()
    recent_rakes = db.get_recent_rakes(limit=5)
    low_stock_alerts = db.get_low_stock_alerts()
    
    return render_template('dashboard.html', 
                         stats=stats, 
                         recent_rakes=recent_rakes,
                         low_stock_alerts=low_stock_alerts)

# ========== Rake Management ==========

@app.route('/rakes')
@login_required
def rakes():
    all_rakes = db.get_all_rakes()
    suppliers = db.get_all_suppliers()
    warehouses = db.get_all_warehouses()
    return render_template('rakes.html', rakes=all_rakes, suppliers=suppliers, warehouses=warehouses)

@app.route('/rake/add', methods=['POST'])
@login_required
def add_rake():
    if current_user.role not in ['Admin', 'Manager']:
        flash('Unauthorized access', 'error')
        return redirect(url_for('rakes'))
    
    rake_number = request.form.get('rake_number')
    supplier_id = request.form.get('supplier_id')
    date = request.form.get('date')
    quantity = float(request.form.get('quantity'))
    allocation_type = request.form.get('allocation_type')
    warehouse_id = request.form.get('warehouse_id') if allocation_type == 'warehouse' else None
    
    rake_id = db.add_rake(rake_number, supplier_id, date, quantity, allocation_type, warehouse_id)
    
    if rake_id:
        flash(f'Rake {rake_number} added successfully!', 'success')
    else:
        flash('Error adding rake', 'error')
    
    return redirect(url_for('rakes'))

@app.route('/rake/<int:rake_id>')
@login_required
def rake_details(rake_id):
    rake = db.get_rake_details(rake_id)
    if not rake:
        flash('Rake not found', 'error')
        return redirect(url_for('rakes'))
    
    warehouse_stock = db.get_warehouse_stock_by_rake(rake_id)
    dispatches = db.get_dispatches_by_rake(rake_id)
    
    return render_template('rake_details.html', 
                         rake=rake, 
                         warehouse_stock=warehouse_stock,
                         dispatches=dispatches)

@app.route('/rake/<int:rake_id>/unload', methods=['POST'])
@login_required
def record_unloading(rake_id):
    if current_user.role not in ['Admin', 'Manager', 'Warehouse']:
        flash('Unauthorized access', 'error')
        return redirect(url_for('rake_details', rake_id=rake_id))
    
    warehouse_id = request.form.get('warehouse_id')
    actual_quantity = float(request.form.get('actual_quantity'))
    shortage = float(request.form.get('shortage', 0))
    notes = request.form.get('notes', '')
    
    success = db.record_rake_unloading(rake_id, warehouse_id, actual_quantity, shortage, notes)
    
    if success:
        flash('Unloading details recorded successfully!', 'success')
    else:
        flash('Error recording unloading details', 'error')
    
    return redirect(url_for('rake_details', rake_id=rake_id))

# ========== Warehouse Management ==========

@app.route('/warehouses')
@login_required
def warehouses():
    all_warehouses = db.get_all_warehouses()
    warehouse_stocks = []
    
    for warehouse in all_warehouses:
        stock = db.get_warehouse_current_stock(warehouse[0])
        warehouse_stocks.append({
            'warehouse': warehouse,
            'stock': stock
        })
    
    return render_template('warehouses.html', warehouse_stocks=warehouse_stocks)

@app.route('/warehouse/<int:warehouse_id>')
@login_required
def warehouse_details(warehouse_id):
    warehouse = db.get_warehouse_by_id(warehouse_id)
    if not warehouse:
        flash('Warehouse not found', 'error')
        return redirect(url_for('warehouses'))
    
    stock_details = db.get_warehouse_stock_details(warehouse_id)
    total_stock = db.get_warehouse_current_stock(warehouse_id)
    
    return render_template('warehouse_details.html', 
                         warehouse=warehouse,
                         stock_details=stock_details,
                         total_stock=total_stock)

# ========== Dispatch Management ==========

@app.route('/dispatches')
@login_required
def dispatches():
    all_dispatches = db.get_all_dispatches()
    warehouses = db.get_all_warehouses()
    dealers = db.get_all_dealers()
    
    return render_template('dispatches.html', 
                         dispatches=all_dispatches,
                         warehouses=warehouses,
                         dealers=dealers)

@app.route('/dispatch/add', methods=['POST'])
@login_required
def add_dispatch():
    if current_user.role not in ['Admin', 'Manager', 'Dispatch']:
        flash('Unauthorized access', 'error')
        return redirect(url_for('dispatches'))
    
    warehouse_id = request.form.get('warehouse_id')
    destination_type = request.form.get('destination_type')
    destination_id = request.form.get('destination_id')
    truck_number = request.form.get('truck_number')
    quantity = float(request.form.get('quantity'))
    dispatch_date = request.form.get('dispatch_date')
    transport_company = request.form.get('transport_company', '')
    
    # Check if warehouse has enough stock
    current_stock = db.get_warehouse_current_stock(warehouse_id)
    if current_stock < quantity:
        flash(f'Insufficient stock. Available: {current_stock} MT', 'error')
        return redirect(url_for('dispatches'))
    
    dispatch_id = db.add_dispatch(warehouse_id, destination_type, destination_id, 
                                  truck_number, quantity, dispatch_date, transport_company)
    
    if dispatch_id:
        # Update warehouse stock
        db.update_warehouse_stock_out(warehouse_id, quantity)
        flash(f'Dispatch added successfully! ID: {dispatch_id}', 'success')
    else:
        flash('Error adding dispatch', 'error')
    
    return redirect(url_for('dispatches'))

@app.route('/dispatch/<int:dispatch_id>')
@login_required
def dispatch_details(dispatch_id):
    dispatch = db.get_dispatch_details(dispatch_id)
    if not dispatch:
        flash('Dispatch not found', 'error')
        return redirect(url_for('dispatches'))
    
    bill = db.get_bill_by_dispatch(dispatch_id)
    
    return render_template('dispatch_details.html', dispatch=dispatch, bill=bill)

# ========== Billing Management ==========

@app.route('/billing')
@login_required
def billing():
    if current_user.role not in ['Admin', 'Manager', 'Billing']:
        flash('Unauthorized access', 'error')
        return redirect(url_for('dashboard'))
    
    all_bills = db.get_all_bills()
    pending_dispatches = db.get_dispatches_without_bills()
    
    return render_template('billing.html', bills=all_bills, pending_dispatches=pending_dispatches)

@app.route('/bill/generate', methods=['POST'])
@login_required
def generate_bill():
    if current_user.role not in ['Admin', 'Manager', 'Billing']:
        flash('Unauthorized access', 'error')
        return redirect(url_for('billing'))
    
    bill_type = request.form.get('bill_type')
    dispatch_id = request.form.get('dispatch_id')
    rate = float(request.form.get('rate'))
    quantity = float(request.form.get('quantity'))
    days = int(request.form.get('days', 0))
    
    # Calculate amount based on bill type
    if bill_type == 'transport':
        amount = rate * quantity
    elif bill_type == 'rent':
        amount = rate * quantity * days
    elif bill_type == 'lifting':
        amount = rate * quantity
    else:
        amount = 0
    
    bill_id = db.add_bill(bill_type, dispatch_id, rate, quantity, amount)
    
    if bill_id:
        # Update dispatch to mark bill as generated
        db.update_dispatch_bill_status(dispatch_id, True)
        flash(f'Bill generated successfully! Amount: ₹{amount:.2f}', 'success')
    else:
        flash('Error generating bill', 'error')
    
    return redirect(url_for('billing'))

@app.route('/bill/<int:bill_id>/download')
@login_required
def download_bill(bill_id):
    bill = db.get_bill_details(bill_id)
    if not bill:
        flash('Bill not found', 'error')
        return redirect(url_for('billing'))
    
    # Generate PDF
    report_gen = ReportGenerator()
    pdf_path = report_gen.generate_bill_pdf(bill)
    
    return send_file(pdf_path, as_attachment=True, download_name=f'bill_{bill_id}.pdf')

# ========== Reports ==========

@app.route('/reports')
@login_required
def reports():
    return render_template('reports.html')

@app.route('/reports/rake-wise')
@login_required
def rake_wise_report():
    rakes = db.get_all_rakes()
    return render_template('report_rake_wise.html', rakes=rakes)

@app.route('/reports/warehouse-wise')
@login_required
def warehouse_wise_report():
    warehouses = db.get_all_warehouses()
    warehouse_data = []
    
    for warehouse in warehouses:
        stock = db.get_warehouse_current_stock(warehouse[0])
        stock_details = db.get_warehouse_stock_details(warehouse[0])
        warehouse_data.append({
            'warehouse': warehouse,
            'total_stock': stock,
            'details': stock_details
        })
    
    return render_template('report_warehouse_wise.html', warehouse_data=warehouse_data)

@app.route('/reports/dealer-wise')
@login_required
def dealer_wise_report():
    dealers = db.get_all_dealers()
    dealer_data = []
    
    for dealer in dealers:
        dispatches = db.get_dispatches_by_dealer(dealer[0])
        total_quantity = sum([d[5] for d in dispatches])
        dealer_data.append({
            'dealer': dealer,
            'dispatches': dispatches,
            'total_quantity': total_quantity
        })
    
    return render_template('report_dealer_wise.html', dealer_data=dealer_data)

@app.route('/reports/billing-summary')
@login_required
def billing_summary_report():
    billing_summary = db.get_billing_summary()
    return render_template('report_billing_summary.html', summary=billing_summary)

# ========== Settings & Master Data ==========

@app.route('/settings')
@login_required
def settings():
    if current_user.role not in ['Admin', 'Manager']:
        flash('Unauthorized access', 'error')
        return redirect(url_for('dashboard'))
    
    suppliers = db.get_all_suppliers()
    warehouses = db.get_all_warehouses()
    dealers = db.get_all_dealers()
    users = db.get_all_users()
    
    return render_template('settings.html', 
                         suppliers=suppliers,
                         warehouses=warehouses,
                         dealers=dealers,
                         users=users)

@app.route('/supplier/add', methods=['POST'])
@login_required
def add_supplier():
    if current_user.role not in ['Admin', 'Manager']:
        flash('Unauthorized access', 'error')
        return redirect(url_for('settings'))
    
    name = request.form.get('name')
    contact = request.form.get('contact')
    address = request.form.get('address')
    
    supplier_id = db.add_supplier(name, contact, address)
    
    if supplier_id:
        flash(f'Supplier {name} added successfully!', 'success')
    else:
        flash('Error adding supplier', 'error')
    
    return redirect(url_for('settings'))

@app.route('/dealer/add', methods=['POST'])
@login_required
def add_dealer():
    if current_user.role not in ['Admin', 'Manager']:
        flash('Unauthorized access', 'error')
        return redirect(url_for('settings'))
    
    name = request.form.get('name')
    contact = request.form.get('contact')
    address = request.form.get('address')
    
    dealer_id = db.add_dealer(name, contact, address)
    
    if dealer_id:
        flash(f'Dealer {name} added successfully!', 'success')
    else:
        flash('Error adding dealer', 'error')
    
    return redirect(url_for('settings'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)
