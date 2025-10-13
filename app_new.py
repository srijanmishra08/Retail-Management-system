"""
Fertilizer Inventory Management System (FIMS) - Redesigned
Role-based application with specific dashboards
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
        # Redirect to role-specific dashboard
        if current_user.role == 'Admin':
            return redirect(url_for('admin_dashboard'))
        elif current_user.role == 'RakePoint':
            return redirect(url_for('rakepoint_dashboard'))
        elif current_user.role == 'Warehouse':
            return redirect(url_for('warehouse_dashboard'))
        elif current_user.role == 'Accountant':
            return redirect(url_for('accountant_dashboard'))
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
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully', 'success')
    return redirect(url_for('login'))

# ========== ADMIN Dashboard & Routes ==========

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if current_user.role != 'Admin':
        flash('Unauthorized access', 'error')
        return redirect(url_for('index'))
    
    stats = db.get_admin_dashboard_stats()
    recent_rakes = db.get_all_rakes()[:5]
    
    return render_template('admin/dashboard.html', stats=stats, recent_rakes=recent_rakes)

@app.route('/admin/add-rake', methods=['GET', 'POST'])
@login_required
def admin_add_rake():
    if current_user.role != 'Admin':
        flash('Unauthorized access', 'error')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        rake_code = request.form.get('rake_code')
        company_name = request.form.get('company_name')
        company_code = request.form.get('company_code')
        date = request.form.get('date')
        rr_quantity = float(request.form.get('rr_quantity'))
        product_name = request.form.get('product_name')
        product_code = request.form.get('product_code')
        rake_point_name = request.form.get('rake_point_name')
        
        rake_id = db.add_rake(rake_code, company_name, company_code, date, rr_quantity,
                             product_name, product_code, rake_point_name)
        
        if rake_id:
            flash(f'Rake {rake_code} added successfully!', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Error adding rake. Rake code may already exist.', 'error')
    
    return render_template('admin/add_rake.html')

@app.route('/admin/summary')
@login_required
def admin_summary():
    if current_user.role != 'Admin':
        flash('Unauthorized access', 'error')
        return redirect(url_for('index'))
    
    summary = db.get_rake_summary()
    return render_template('admin/summary.html', summary=summary)

@app.route('/admin/manage-accounts', methods=['GET', 'POST'])
@login_required
def admin_manage_accounts():
    if current_user.role != 'Admin':
        flash('Unauthorized access', 'error')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        account_name = request.form.get('account_name')
        account_type = request.form.get('account_type')
        contact = request.form.get('contact')
        address = request.form.get('address')
        
        account_id = db.add_account(account_name, account_type, contact, address)
        
        if account_id:
            flash(f'Account {account_name} added successfully!', 'success')
        else:
            flash('Error adding account', 'error')
    
    accounts = db.get_all_accounts()
    return render_template('admin/manage_accounts.html', accounts=accounts)

# ========== RAKE POINT Dashboard & Routes ==========

@app.route('/rakepoint/dashboard')
@login_required
def rakepoint_dashboard():
    if current_user.role != 'RakePoint':
        flash('Unauthorized access', 'error')
        return redirect(url_for('index'))
    
    recent_builties = db.get_all_builties()[:10]
    rakes = db.get_all_rakes()
    
    return render_template('rakepoint/dashboard.html', recent_builties=recent_builties, rakes=rakes)

@app.route('/rakepoint/create-builty', methods=['GET', 'POST'])
@login_required
def rakepoint_create_builty():
    if current_user.role != 'RakePoint':
        flash('Unauthorized access', 'error')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        builty_number = request.form.get('builty_number')
        date = request.form.get('date')
        rake_point_name = request.form.get('rake_point_name')
        account_id = request.form.get('account_id') if request.form.get('account_id') else None
        warehouse_id = request.form.get('warehouse_id') if request.form.get('warehouse_id') else None
        truck_number = request.form.get('truck_number')
        loading_point = request.form.get('loading_point')
        unloading_point = request.form.get('unloading_point')
        goods_name = request.form.get('goods_name')
        number_of_bags = int(request.form.get('number_of_bags'))
        quantity_mt = float(request.form.get('quantity_mt'))
        kg_per_bag = float(request.form.get('kg_per_bag'))
        rate_per_mt = float(request.form.get('rate_per_mt'))
        total_freight = float(request.form.get('total_freight'))
        lr_number = request.form.get('lr_number')
        lr_index = int(request.form.get('lr_index'))
        
        # Check if truck exists, if not create it
        truck = db.get_truck_by_number(truck_number)
        if not truck:
            driver_name = request.form.get('driver_name')
            driver_mobile = request.form.get('driver_mobile')
            owner_name = request.form.get('owner_name')
            owner_mobile = request.form.get('owner_mobile')
            truck_id = db.add_truck(truck_number, driver_name, driver_mobile, owner_name, owner_mobile)
        else:
            truck_id = truck[0]
        
        builty_id = db.add_builty(builty_number, date, rake_point_name, account_id, warehouse_id,
                                  truck_id, loading_point, unloading_point, goods_name, number_of_bags,
                                  quantity_mt, kg_per_bag, rate_per_mt, total_freight, lr_number,
                                  lr_index, 'RakePoint')
        
        if builty_id:
            flash(f'Builty {builty_number} created successfully!', 'success')
            return redirect(url_for('rakepoint_dashboard'))
        else:
            flash('Error creating builty. Builty number may already exist.', 'error')
    
    accounts = db.get_all_accounts()
    warehouses = db.get_all_warehouses()
    trucks = db.get_all_trucks()
    
    return render_template('rakepoint/create_builty.html', 
                         accounts=accounts, 
                         warehouses=warehouses,
                         trucks=trucks)

@app.route('/rakepoint/create-loading-slip', methods=['GET', 'POST'])
@login_required
def rakepoint_create_loading_slip():
    if current_user.role != 'RakePoint':
        flash('Unauthorized access', 'error')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        rake_code = request.form.get('rake_code')
        slip_number = int(request.form.get('slip_number'))
        loading_point_name = request.form.get('loading_point_name')
        destination = request.form.get('destination')
        account_id = request.form.get('account_id')
        quantity_bags = int(request.form.get('quantity_bags'))
        quantity_mt = float(request.form.get('quantity_mt'))
        truck_number = request.form.get('truck_number')
        wagon_number = request.form.get('wagon_number')
        builty_id = request.form.get('builty_id') if request.form.get('builty_id') else None
        
        # Check if truck exists
        truck = db.get_truck_by_number(truck_number)
        if not truck:
            flash('Truck not found. Please add truck details first.', 'error')
            return redirect(url_for('rakepoint_create_loading_slip'))
        
        truck_id = truck[0]
        
        slip_id = db.add_loading_slip(rake_code, slip_number, loading_point_name, destination,
                                      account_id, quantity_bags, quantity_mt, truck_id, 
                                      wagon_number, builty_id)
        
        if slip_id:
            flash(f'Loading slip #{slip_number} created successfully!', 'success')
            return redirect(url_for('rakepoint_view_loading_slips', rake_code=rake_code))
        else:
            flash('Error creating loading slip', 'error')
    
    rakes = db.get_all_rakes()
    accounts = db.get_all_accounts()
    trucks = db.get_all_trucks()
    builties = db.get_all_builties()
    
    return render_template('rakepoint/create_loading_slip.html', 
                         rakes=rakes,
                         accounts=accounts,
                         trucks=trucks,
                         builties=builties)

@app.route('/rakepoint/loading-slips/<rake_code>')
@login_required
def rakepoint_view_loading_slips(rake_code):
    if current_user.role != 'RakePoint':
        flash('Unauthorized access', 'error')
        return redirect(url_for('index'))
    
    rake = db.get_rake_by_code(rake_code)
    slips = db.get_loading_slips_by_rake(rake_code)
    
    return render_template('rakepoint/loading_slips.html', rake=rake, slips=slips)

# ========== WAREHOUSE Dashboard & Routes ==========

@app.route('/warehouse/dashboard')
@login_required
def warehouse_dashboard():
    if current_user.role != 'Warehouse':
        flash('Unauthorized access', 'error')
        return redirect(url_for('index'))
    
    warehouses = db.get_all_warehouses()
    warehouse_stats = []
    
    for warehouse in warehouses:
        balance = db.get_warehouse_balance_stock(warehouse[0])
        warehouse_stats.append({
            'warehouse': warehouse,
            'stock_in': balance['stock_in'],
            'stock_out': balance['stock_out'],
            'balance': balance['balance']
        })
    
    return render_template('warehouse/dashboard.html', warehouse_stats=warehouse_stats)

@app.route('/warehouse/stock-in', methods=['GET', 'POST'])
@login_required
def warehouse_stock_in():
    if current_user.role != 'Warehouse':
        flash('Unauthorized access', 'error')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        warehouse_id = request.form.get('warehouse_id')
        builty_id = request.form.get('builty_id')
        quantity_mt = float(request.form.get('quantity_mt'))
        unloader_employee = request.form.get('unloader_employee')
        account_id = request.form.get('account_id')
        date = request.form.get('date')
        notes = request.form.get('notes', '')
        
        stock_id = db.add_warehouse_stock_in(warehouse_id, builty_id, quantity_mt,
                                             unloader_employee, account_id, date, notes)
        
        if stock_id:
            flash('Stock IN recorded successfully!', 'success')
            return redirect(url_for('warehouse_dashboard'))
        else:
            flash('Error recording stock IN', 'error')
    
    warehouses = db.get_all_warehouses()
    builties = db.get_all_builties()
    accounts = db.get_all_accounts()
    
    return render_template('warehouse/stock_in.html', 
                         warehouses=warehouses,
                         builties=builties,
                         accounts=accounts)

@app.route('/warehouse/stock-out', methods=['GET', 'POST'])
@login_required
def warehouse_stock_out():
    if current_user.role != 'Warehouse':
        flash('Unauthorized access', 'error')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        warehouse_id = request.form.get('warehouse_id')
        # First create a builty for stock out
        builty_number = request.form.get('builty_number')
        date = request.form.get('date')
        account_id = request.form.get('account_id')
        truck_number = request.form.get('truck_number')
        loading_point = request.form.get('loading_point')
        unloading_point = request.form.get('unloading_point')
        goods_name = request.form.get('goods_name')
        number_of_bags = int(request.form.get('number_of_bags'))
        quantity_mt = float(request.form.get('quantity_mt'))
        kg_per_bag = float(request.form.get('kg_per_bag'))
        rate_per_mt = float(request.form.get('rate_per_mt'))
        total_freight = float(request.form.get('total_freight'))
        lr_number = request.form.get('lr_number')
        lr_index = int(request.form.get('lr_index'))
        
        # Get or create truck
        truck = db.get_truck_by_number(truck_number)
        if not truck:
            driver_name = request.form.get('driver_name')
            driver_mobile = request.form.get('driver_mobile')
            owner_name = request.form.get('owner_name')
            owner_mobile = request.form.get('owner_mobile')
            truck_id = db.add_truck(truck_number, driver_name, driver_mobile, owner_name, owner_mobile)
        else:
            truck_id = truck[0]
        
        # Create builty
        builty_id = db.add_builty(builty_number, date, None, account_id, warehouse_id,
                                  truck_id, loading_point, unloading_point, goods_name, number_of_bags,
                                  quantity_mt, kg_per_bag, rate_per_mt, total_freight, lr_number,
                                  lr_index, 'Warehouse')
        
        if builty_id:
            # Add stock out transaction
            stock_id = db.add_warehouse_stock_out(warehouse_id, builty_id, quantity_mt,
                                                  account_id, date, '')
            
            if stock_id:
                flash(f'Stock OUT recorded successfully! Builty: {builty_number}', 'success')
                return redirect(url_for('warehouse_dashboard'))
            else:
                flash('Error recording stock OUT', 'error')
        else:
            flash('Error creating builty for stock OUT', 'error')
    
    warehouses = db.get_all_warehouses()
    accounts = db.get_all_accounts()
    trucks = db.get_all_trucks()
    
    return render_template('warehouse/stock_out.html', 
                         warehouses=warehouses,
                         accounts=accounts,
                         trucks=trucks)

@app.route('/warehouse/balance/<int:warehouse_id>')
@login_required
def warehouse_balance(warehouse_id):
    if current_user.role != 'Warehouse':
        flash('Unauthorized access', 'error')
        return redirect(url_for('index'))
    
    warehouse = db.get_warehouse_by_id(warehouse_id)
    balance = db.get_warehouse_balance_stock(warehouse_id)
    transactions = db.get_warehouse_stock_transactions(warehouse_id)
    
    return render_template('warehouse/balance.html', 
                         warehouse=warehouse,
                         balance=balance,
                         transactions=transactions)

# ========== ACCOUNTANT Dashboard & Routes ==========

@app.route('/accountant/dashboard')
@login_required
def accountant_dashboard():
    if current_user.role != 'Accountant':
        flash('Unauthorized access', 'error')
        return redirect(url_for('index'))
    
    ebills = db.get_all_ebills()[:10]
    pending_builties = db.get_builties_without_ebills()
    
    return render_template('accountant/dashboard.html', 
                         ebills=ebills,
                         pending_builties=pending_builties)

@app.route('/accountant/create-ebill', methods=['GET', 'POST'])
@login_required
def accountant_create_ebill():
    if current_user.role != 'Accountant':
        flash('Unauthorized access', 'error')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        builty_id = request.form.get('builty_id')
        ebill_number = request.form.get('ebill_number')
        amount = float(request.form.get('amount'))
        generated_date = request.form.get('generated_date')
        
        ebill_id = db.add_ebill(builty_id, ebill_number, amount, generated_date)
        
        if ebill_id:
            flash(f'E-Bill {ebill_number} created successfully!', 'success')
            return redirect(url_for('accountant_dashboard'))
        else:
            flash('Error creating e-bill. E-Bill number may already exist.', 'error')
    
    builties = db.get_builties_without_ebills()
    
    return render_template('accountant/create_ebill.html', builties=builties)

@app.route('/accountant/ebills')
@login_required
def accountant_all_ebills():
    if current_user.role != 'Accountant':
        flash('Unauthorized access', 'error')
        return redirect(url_for('index'))
    
    ebills = db.get_all_ebills()
    
    return render_template('accountant/all_ebills.html', ebills=ebills)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)
