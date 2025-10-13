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
        # Generate builty number (can be auto-generated based on date + sequence)
        builty_number = f"BLT-{datetime.now().strftime('%Y%m%d')}-{datetime.now().strftime('%H%M%S')}"
        
        # Get loading_slip_id to link builty to loading slip
        loading_slip_id = request.form.get('loading_slip_id')
        
        # Get 14 fields from form + rake_code
        rake_code = request.form.get('rake_code')  # NEW: Link to rake
        date = request.form.get('date') or request.form.get('builty_date')  # Support both field names
        rake_point_name = request.form.get('rake_point_name')
        account_warehouse = request.form.get('account_warehouse')  # Field 3
        truck_number = request.form.get('truck_number')  # Field 4
        loading_point = request.form.get('loading_point')  # Field 5
        unloading_point = request.form.get('unloading_point')  # Field 6
        truck_driver = request.form.get('truck_driver')  # Field 7
        truck_owner = request.form.get('truck_owner')  # Field 8
        mobile_number_1 = request.form.get('mobile_number_1')  # Field 9
        mobile_number_2 = request.form.get('mobile_number_2')  # Field 10
        goods_name = request.form.get('goods_name')  # Field 11
        number_of_bags = int(request.form.get('number_of_bags'))  # Field 12
        quantity_wt_mt = float(request.form.get('quantity_wt_mt'))  # Field 13
        freight_details = request.form.get('freight_details')  # Field 14
        lr_number = request.form.get('lr_number')  # Field 15
        
        # Determine if account_warehouse is account or warehouse
        account_id = None
        warehouse_id = None
        # Simple check - you may want to improve this
        accounts = db.get_all_accounts()
        warehouses = db.get_all_warehouses()
        
        for account in accounts:
            if account[1] == account_warehouse:
                account_id = account[0]
                break
        
        if account_id is None:
            for warehouse in warehouses:
                if warehouse[1] == account_warehouse:
                    warehouse_id = warehouse[0]
                    break
        
        # Check if truck exists, if not create it
        truck = db.get_truck_by_number(truck_number)
        if not truck:
            truck_id = db.add_truck(truck_number, truck_driver, mobile_number_1, truck_owner, mobile_number_2)
        else:
            truck_id = truck[0]
        
        # Parse freight details - assuming it's a number or contains a number
        try:
            total_freight = float(freight_details.replace('₹', '').replace(',', '').strip())
        except:
            total_freight = 0.0
        
        # Calculate kg per bag (assuming 50kg per bag as default)
        kg_per_bag = (quantity_wt_mt * 1000) / number_of_bags if number_of_bags > 0 else 50
        rate_per_mt = total_freight / quantity_wt_mt if quantity_wt_mt > 0 else 0
        
        builty_id = db.add_builty(builty_number, rake_code, date, rake_point_name, account_id, warehouse_id,
                                  truck_id, loading_point, unloading_point, goods_name, number_of_bags,
                                  quantity_wt_mt, kg_per_bag, rate_per_mt, total_freight, lr_number,
                                  0, 'RakePoint')
        
        if builty_id:
            # Link the loading slip to this builty
            if loading_slip_id:
                db.link_loading_slip_to_builty(int(loading_slip_id), builty_id)
            
            flash(f'Builty {builty_number} created successfully!', 'success')
            return redirect(url_for('rakepoint_dashboard'))
        else:
            flash('Error creating builty. Please try again.', 'error')
    
    accounts = db.get_all_accounts()
    warehouses = db.get_all_warehouses()
    rakes = db.get_all_rakes()  # NEW: Get all rakes for selection
    loading_slips = db.get_all_loading_slips()  # NEW: Get all loading slips for auto-fill
    
    return render_template('rakepoint/create_builty.html', 
                         accounts=accounts, 
                         warehouses=warehouses,
                         rakes=rakes,
                         loading_slips=loading_slips)

@app.route('/rakepoint/create-loading-slip', methods=['GET', 'POST'])
@login_required
def rakepoint_create_loading_slip():
    if current_user.role != 'RakePoint':
        flash('Unauthorized access', 'error')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        rake_code = request.form.get('rake_code')
        serial_number = int(request.form.get('serial_number'))
        loading_point = request.form.get('loading_point')
        destination = request.form.get('destination')
        account = request.form.get('account')
        quantity_in_bags = int(request.form.get('quantity_in_bags'))
        quantity_in_mt = float(request.form.get('quantity_in_mt'))
        truck_number = request.form.get('truck_number')
        wagon_number = request.form.get('wagon_number')
        goods_name = request.form.get('goods_name')
        truck_driver = request.form.get('truck_driver')
        truck_owner = request.form.get('truck_owner')
        mobile_number_1 = request.form.get('mobile_number_1')
        mobile_number_2 = request.form.get('mobile_number_2', '')
        truck_details = request.form.get('truck_details', '')
        
        # Find account_id
        accounts = db.get_all_accounts()
        account_id = None
        for acc in accounts:
            if acc[1] == account:
                account_id = acc[0]
                break
        
        # Check if truck exists, if not create it with driver/owner details
        truck = db.get_truck_by_number(truck_number)
        if not truck:
            truck_id = db.add_truck(truck_number, truck_driver, mobile_number_1, truck_owner, mobile_number_2)
        else:
            truck_id = truck[0]
        
        slip_id = db.add_loading_slip(rake_code, serial_number, loading_point, destination,
                                      account_id, quantity_in_bags, quantity_in_mt, truck_id, 
                                      wagon_number, goods_name, truck_driver, truck_owner,
                                      mobile_number_1, mobile_number_2, truck_details, None)
        
        if slip_id:
            flash(f'Loading slip #{serial_number} created successfully!', 'success')
            if request.form.get('action') == 'print':
                # Redirect to print view (implement later)
                return redirect(url_for('rakepoint_loading_slips'))
            return redirect(url_for('rakepoint_dashboard'))
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

@app.route('/rakepoint/loading-slips')
@login_required
def rakepoint_loading_slips():
    if current_user.role != 'RakePoint':
        flash('Unauthorized access', 'error')
        return redirect(url_for('index'))
    
    loading_slips = db.get_all_loading_slips()
    
    return render_template('rakepoint/loading_slips.html', loading_slips=loading_slips)

@app.route('/rakepoint/loading-slips/<rake_code>')
@login_required
def rakepoint_view_loading_slips(rake_code):
    if current_user.role != 'RakePoint':
        flash('Unauthorized access', 'error')
        return redirect(url_for('index'))
    
    rake = db.get_rake_by_code(rake_code)
    slips = db.get_loading_slips_by_rake(rake_code)
    
    return render_template('rakepoint/loading_slips.html', rake=rake, loading_slips=slips)

# ========== WAREHOUSE Dashboard & Routes ==========

@app.route('/warehouse/dashboard')
@login_required
def warehouse_dashboard():
    if current_user.role != 'Warehouse':
        flash('Unauthorized access', 'error')
        return redirect(url_for('index'))
    
    warehouses = db.get_all_warehouses()
    warehouse_stats = []
    
    total_stock_in = 0
    total_stock_out = 0
    
    for warehouse in warehouses:
        balance = db.get_warehouse_balance_stock(warehouse[0])
        warehouse_stats.append({
            'warehouse': warehouse,
            'stock_in': balance['stock_in'],
            'stock_out': balance['stock_out'],
            'balance': balance['balance']
        })
        total_stock_in += balance['stock_in']
        total_stock_out += balance['stock_out']
    
    # Get recent stock movements (last 10)
    recent_movements = db.execute_query('''
        SELECT ws.date, ws.transaction_type, b.builty_number, w.warehouse_name, ws.quantity_mt
        FROM warehouse_stock ws
        JOIN builty b ON ws.builty_id = b.builty_id
        JOIN warehouses w ON ws.warehouse_id = w.warehouse_id
        ORDER BY ws.date DESC, ws.stock_id DESC
        LIMIT 10
    ''')
    
    # Get additional stats for info section
    account_count = len(db.get_all_accounts())
    builty_count = len(db.get_all_builties())
    
    # Today's stock IN
    today_stock_in_result = db.execute_query('''
        SELECT COALESCE(SUM(quantity_mt), 0)
        FROM warehouse_stock
        WHERE transaction_type = 'IN' AND date = date('now')
    ''')
    today_stock_in = today_stock_in_result[0][0] if today_stock_in_result else 0
    
    return render_template('warehouse/dashboard.html', 
                         warehouse_stats=warehouse_stats,
                         total_stock_in=total_stock_in,
                         total_stock_out=total_stock_out,
                         warehouse_count=len(warehouses),
                         recent_movements=recent_movements,
                         account_count=account_count,
                         builty_count=builty_count,
                         today_stock_in=today_stock_in)

@app.route('/warehouse/stock-in', methods=['GET', 'POST'])
@login_required
def warehouse_stock_in():
    if current_user.role != 'Warehouse':
        flash('Unauthorized access', 'error')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        builty_number = request.form.get('builty_number')
        unloaded_quantity = float(request.form.get('unloaded_quantity'))
        unloader_employee = request.form.get('unloader_employee')
        warehouse_name = request.form.get('warehouse_name')
        account_name = request.form.get('account_name')
        stock_in_date = request.form.get('stock_in_date')
        remarks = request.form.get('remarks', '')
        
        # Get IDs from names/numbers
        builty = db.execute_query('SELECT builty_id, account_id, rake_code, quantity_mt FROM builty WHERE builty_number = ?', (builty_number,))
        warehouse = db.execute_query('SELECT warehouse_id FROM warehouses WHERE warehouse_name = ?', (warehouse_name,))
        
        if builty and warehouse:
            builty_id = builty[0][0]
            account_id = builty[0][1]
            rake_code = builty[0][2]
            builty_quantity = builty[0][3]
            warehouse_id = warehouse[0][0]
            
            # CRITICAL CHECK: Verify this builty hasn't been fully stocked IN already
            existing_stock_in = db.execute_query('''
                SELECT COALESCE(SUM(quantity_mt), 0)
                FROM warehouse_stock
                WHERE builty_id = ? AND transaction_type = 'IN'
            ''', (builty_id,))
            
            total_already_in = existing_stock_in[0][0] if existing_stock_in else 0
            
            # Check if trying to add more than builty quantity
            if total_already_in + unloaded_quantity > builty_quantity:
                remaining = builty_quantity - total_already_in
                if remaining <= 0:
                    flash(f'Error: Builty {builty_number} already fully stocked IN ({builty_quantity} MT). Cannot add more stock!', 'error')
                else:
                    flash(f'Error: Builty {builty_number} has only {remaining:.2f} MT remaining (Total: {builty_quantity} MT, Already IN: {total_already_in:.2f} MT)', 'error')
                return redirect(url_for('warehouse_stock_in'))
            
            stock_id = db.add_warehouse_stock_in(warehouse_id, builty_id, unloaded_quantity,
                                                 unloader_employee, account_id, stock_in_date, remarks)
            
            if stock_id:
                remaining_after = builty_quantity - (total_already_in + unloaded_quantity)
                if remaining_after > 0:
                    flash(f'Stock IN recorded successfully! Remaining from this builty: {remaining_after:.2f} MT', 'success')
                else:
                    flash(f'Stock IN recorded successfully! Builty {builty_number} now fully stocked IN.', 'success')
                return redirect(url_for('warehouse_dashboard'))
            else:
                flash('Error recording stock IN', 'error')
        else:
            flash('Invalid builty or warehouse', 'error')
    
    warehouses = db.get_all_warehouses()
    builties = db.get_all_builties()
    
    # Get recent stock IN entries for display
    recent_stock_in = db.execute_query('''
        SELECT ws.date, b.builty_number, w.warehouse_name, COALESCE(a.account_name, 'N/A') as account_name, 
               ws.quantity_mt, ws.unloader_employee
        FROM warehouse_stock ws
        JOIN builty b ON ws.builty_id = b.builty_id
        JOIN warehouses w ON ws.warehouse_id = w.warehouse_id
        LEFT JOIN accounts a ON ws.account_id = a.account_id
        WHERE ws.transaction_type = 'IN'
        ORDER BY ws.date DESC, ws.stock_id DESC
        LIMIT 10
    ''')
    
    return render_template('warehouse/stock_in.html', 
                         warehouses=warehouses,
                         builties=builties,
                         recent_stock_in=recent_stock_in)

@app.route('/warehouse/stock-out', methods=['GET', 'POST'])
@login_required
def warehouse_stock_out():
    if current_user.role != 'Warehouse':
        flash('Unauthorized access', 'error')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        warehouse_name = request.form.get('warehouse_name')
        stock_out_date = request.form.get('stock_out_date')
        
        # Builty details (14 fields)
        date = request.form.get('date')
        rake_point_name = request.form.get('rake_point_name')
        account_warehouse = request.form.get('account_warehouse')
        truck_number = request.form.get('truck_number')
        loading_point = request.form.get('loading_point')
        unloading_point = request.form.get('unloading_point')
        truck_driver = request.form.get('truck_driver')
        truck_owner = request.form.get('truck_owner')
        mobile_number_1 = request.form.get('mobile_number_1')
        mobile_number_2 = request.form.get('mobile_number_2', '')
        goods_name = request.form.get('goods_name')
        number_of_bags = int(request.form.get('number_of_bags'))
        quantity_wt_mt = float(request.form.get('quantity_wt_mt'))
        freight_details = request.form.get('freight_details')
        lr_number = request.form.get('lr_number')
        
        # Get warehouse ID
        warehouse = db.execute_query('SELECT warehouse_id FROM warehouses WHERE warehouse_name = ?', (warehouse_name,))
        if not warehouse:
            flash('Invalid warehouse', 'error')
            return redirect(url_for('warehouse_stock_out'))
        warehouse_id = warehouse[0][0]
        
        # Check if warehouse has enough stock
        balance = db.get_warehouse_balance_stock(warehouse_id)
        if balance['balance'] < quantity_wt_mt:
            flash(f'Error: Warehouse has only {balance["balance"]:.2f} MT available. Cannot dispatch {quantity_wt_mt:.2f} MT', 'error')
            return redirect(url_for('warehouse_stock_out'))
        
        # Determine if account or warehouse
        account_id = None
        destination_warehouse_id = None
        accounts = db.get_all_accounts()
        for account in accounts:
            if account[1] == account_warehouse:
                account_id = account[0]
                break
        
        # Get or create truck
        truck = db.get_truck_by_number(truck_number)
        if not truck:
            truck_id = db.add_truck(truck_number, truck_driver, mobile_number_1, truck_owner, mobile_number_2)
        else:
            truck_id = truck[0]
        
        # Auto-generate builty number for stock OUT
        from datetime import datetime
        builty_number = f"BLTO-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        
        # Calculate additional fields
        try:
            total_freight = float(freight_details.replace('₹', '').replace(',', '').strip())
        except:
            total_freight = 0.0
        kg_per_bag = (quantity_wt_mt * 1000) / number_of_bags if number_of_bags > 0 else 50
        rate_per_mt = total_freight / quantity_wt_mt if quantity_wt_mt > 0 else 0
        
        # Get rake_code from warehouse stock (use most recent rake)
        rake_code_result = db.execute_query('''
            SELECT b.rake_code
            FROM warehouse_stock ws
            JOIN builty b ON ws.builty_id = b.builty_id
            WHERE ws.warehouse_id = ? AND ws.transaction_type = 'IN'
            ORDER BY ws.stock_id DESC
            LIMIT 1
        ''', (warehouse_id,))
        rake_code = rake_code_result[0][0] if rake_code_result else None
        
        # Create builty for stock OUT
        builty_id = db.add_builty(builty_number, rake_code, date, rake_point_name, account_id, destination_warehouse_id,
                                  truck_id, loading_point, unloading_point, goods_name, number_of_bags,
                                  quantity_wt_mt, kg_per_bag, rate_per_mt, total_freight, lr_number,
                                  0, 'Warehouse')
        
        if builty_id:
            # Add stock out transaction
            stock_id = db.add_warehouse_stock_out(warehouse_id, builty_id, quantity_wt_mt,
                                                  account_id, stock_out_date, '')
            
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

@app.route('/warehouse/balance')
@login_required
def warehouse_balance_all():
    """View balance across all warehouses"""
    if current_user.role != 'Warehouse':
        flash('Unauthorized access', 'error')
        return redirect(url_for('index'))
    
    # Get overall stock statistics
    warehouse_balances = []
    account_balances = []
    
    warehouses = db.get_all_warehouses()
    for warehouse in warehouses:
        balance = db.get_warehouse_balance_stock(warehouse[0])
        warehouse_balances.append([
            warehouse[1],  # warehouse_name
            warehouse[2],  # location
            balance.get('stock_in', 0),
            balance.get('stock_out', 0)
        ])
    
    # Calculate totals
    total_stock_in = sum(w[2] for w in warehouse_balances)
    total_stock_out = sum(w[3] for w in warehouse_balances)
    
    # Get account balances (simplified)
    accounts = db.get_all_accounts()
    for account in accounts:
        # This would need a database function to calculate per-account stock
        account_balances.append([account[1], 0, 0])  # Placeholder
    
    return render_template('warehouse/balance.html',
                         warehouse_balances=warehouse_balances,
                         account_balances=account_balances,
                         total_stock_in=total_stock_in,
                         total_stock_out=total_stock_out)

@app.route('/warehouse/balance/<int:warehouse_id>')
@login_required
def warehouse_balance(warehouse_id):
    """View balance for specific warehouse"""
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
