"""
Fertilizer Inventory Management System (FIMS) - Redesigned
Role-based application with specific dashboards
"""

from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file, jsonify
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
    all_rakes = db.get_all_rakes()
    
    # Get total shortage from closed rakes
    total_shortage = db.get_total_shortage()
    
    # Enrich recent rakes with dispatched and remaining quantities
    recent_rakes = []
    for rake in all_rakes[:5]:
        rake_code = rake[1]
        balance = db.get_rake_balance(rake_code)
        # Check if rake is closed (index 10 is is_closed after migration)
        is_closed = rake[10] if len(rake) > 10 else 0
        shortage = rake[12] if len(rake) > 12 else 0  # Index 12 is shortage after migration
        recent_rakes.append({
            'rake_code': rake[1],
            'company_name': rake[2],
            'company_code': rake[3],
            'date': rake[4],
            'rr_quantity': rake[5],
            'product_name': rake[6],
            'product_code': rake[7],
            'rake_point_name': rake[8],
            'dispatched': balance['dispatched'] if balance else 0,
            'remaining': balance['remaining'] if balance else rake[5],
            'is_closed': is_closed,
            'shortage': shortage
        })
    
    return render_template('admin/dashboard.html', stats=stats, recent_rakes=recent_rakes, total_shortage=total_shortage)

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
    
    products = db.get_all_products()
    companies = db.get_all_companies()
    return render_template('admin/add_rake.html', products=products, companies=companies)

@app.route('/admin/close-rake/<rake_code>', methods=['POST'])
@login_required
def admin_close_rake(rake_code):
    if current_user.role != 'Admin':
        flash('Unauthorized access', 'error')
        return redirect(url_for('index'))
    
    success, result = db.close_rake(rake_code)
    
    if success:
        flash(f'Rake {rake_code} closed successfully! Shortage: {result:.2f} MT', 'success')
    else:
        flash(f'Error closing rake: {result}', 'error')
    
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/summary')
@login_required
def admin_summary():
    if current_user.role != 'Admin':
        flash('Unauthorized access', 'error')
        return redirect(url_for('index'))
    
    view_type = request.args.get('view', 'rakes')  # rakes, total, per_account
    
    # Get total shortage from closed rakes
    total_shortage = db.get_total_shortage()
    
    # Get all rakes with enriched data (like dashboard)
    all_rakes = db.get_all_rakes()
    rakes_with_balance = []
    for rake in all_rakes:
        rake_code = rake[1]
        balance = db.get_rake_balance(rake_code)
        # Check if rake is closed (index 10 is is_closed after migration)
        is_closed = rake[10] if len(rake) > 10 else 0
        shortage = rake[12] if len(rake) > 12 else 0  # Index 12 is shortage after migration
        rakes_with_balance.append({
            'rake_code': rake[1],
            'company_name': rake[2],
            'company_code': rake[3],
            'date': rake[4],
            'rr_quantity': rake[5],
            'product_name': rake[6],
            'product_code': rake[7],
            'rake_point_name': rake[8],
            'dispatched': balance['dispatched'] if balance else 0,
            'remaining': balance['remaining'] if balance else rake[5],
            'is_closed': is_closed,
            'shortage': shortage
        })
    
    # Get total summary (all accounts with dispatch quantities)
    total_account_summary = db.execute_custom_query('''
        SELECT a.account_name, a.account_type, 
               SUM(b.quantity_mt) as total_quantity,
               COUNT(DISTINCT b.rake_code) as rake_count,
               COUNT(b.builty_id) as builty_count
        FROM builty b
        JOIN accounts a ON b.account_id = a.account_id
        GROUP BY a.account_id, a.account_name, a.account_type
        ORDER BY total_quantity DESC
    ''')
    
    # Get CGMF dispatch summary
    cgmf_summary = db.execute_custom_query('''
        SELECT c.society_name, c.district, c.destination,
               SUM(b.quantity_mt) as total_quantity,
               COUNT(DISTINCT b.rake_code) as rake_count,
               COUNT(b.builty_id) as builty_count
        FROM builty b
        JOIN cgmf c ON b.cgmf_id = c.cgmf_id
        GROUP BY c.cgmf_id, c.society_name, c.district
        ORDER BY total_quantity DESC
    ''')
    
    # Get warehouse dispatch summary
    warehouse_summary = db.execute_custom_query('''
        SELECT w.warehouse_name, w.location,
               SUM(b.quantity_mt) as total_quantity,
               COUNT(DISTINCT b.rake_code) as rake_count,
               COUNT(b.builty_id) as builty_count
        FROM builty b
        JOIN warehouses w ON b.warehouse_id = w.warehouse_id
        GROUP BY w.warehouse_id, w.warehouse_name
        ORDER BY total_quantity DESC
    ''')
    
    return render_template('admin/summary.html', 
                         rakes=rakes_with_balance,
                         view_type=view_type,
                         total_account_summary=total_account_summary,
                         cgmf_summary=cgmf_summary,
                         warehouse_summary=warehouse_summary,
                         total_shortage=total_shortage)

@app.route('/admin/rake-details/<rake_code>')
@login_required
def admin_rake_details(rake_code):
    """View detailed dispatch information for a specific rake"""
    if current_user.role != 'Admin':
        flash('Unauthorized access', 'error')
        return redirect(url_for('index'))
    
    # Get rake basic info
    rake_info = db.execute_custom_query('''
        SELECT r.rake_code, r.company_name, r.product_name, r.date, 
               r.rr_quantity, r.rake_point_name
        FROM rakes r
        WHERE r.rake_code = ?
    ''', (rake_code,))
    
    if not rake_info:
        flash('Rake not found', 'error')
        return redirect(url_for('admin_summary'))
    
    # Get stock dispatched to accounts FROM LOADING SLIPS (the actual dispatch record)
    account_dispatches = db.execute_custom_query('''
        SELECT a.account_name, a.account_type, 
               SUM(ls.quantity_mt) as total_quantity,
               COUNT(ls.slip_id) as slip_count,
               GROUP_CONCAT('Slip#' || ls.slip_number || ' (' || ls.quantity_mt || ' MT)', ', ') as slip_details
        FROM loading_slips ls
        JOIN accounts a ON ls.account_id = a.account_id
        WHERE ls.rake_code = ?
        GROUP BY a.account_id, a.account_name, a.account_type
        ORDER BY total_quantity DESC
    ''', (rake_code,))
    
    # Get stock sent to warehouses FROM LOADING SLIPS
    warehouse_dispatches = db.execute_custom_query('''
        SELECT w.warehouse_name, w.location,
               SUM(ls.quantity_mt) as total_quantity,
               COUNT(ls.slip_id) as slip_count,
               GROUP_CONCAT('Slip#' || ls.slip_number || ' (' || ls.quantity_mt || ' MT)', ', ') as slip_details
        FROM loading_slips ls
        JOIN warehouses w ON ls.warehouse_id = w.warehouse_id
        WHERE ls.rake_code = ?
        GROUP BY w.warehouse_id, w.warehouse_name, w.location
        ORDER BY total_quantity DESC
    ''', (rake_code,))
    
    # Get CGMF dispatches FROM LOADING SLIPS
    cgmf_dispatches = db.execute_custom_query('''
        SELECT c.society_name, c.district, c.destination,
               SUM(ls.quantity_mt) as total_quantity,
               COUNT(ls.slip_id) as slip_count,
               GROUP_CONCAT('Slip#' || ls.slip_number || ' (' || ls.quantity_mt || ' MT)', ', ') as slip_details
        FROM loading_slips ls
        JOIN cgmf c ON ls.cgmf_id = c.cgmf_id
        WHERE ls.rake_code = ?
        GROUP BY c.cgmf_id, c.society_name, c.district
        ORDER BY total_quantity DESC
    ''', (rake_code,))
    
    # Calculate totals
    total_to_accounts = sum(row[2] for row in account_dispatches) if account_dispatches else 0
    total_to_warehouses = sum(row[2] for row in warehouse_dispatches) if warehouse_dispatches else 0
    total_to_cgmf = sum(row[3] for row in cgmf_dispatches) if cgmf_dispatches else 0
    
    return render_template('admin/rake_details.html',
                         rake_info=rake_info[0],
                         account_dispatches=account_dispatches,
                         warehouse_dispatches=warehouse_dispatches,
                         cgmf_dispatches=cgmf_dispatches,
                         total_to_accounts=total_to_accounts,
                         total_to_warehouses=total_to_warehouses,
                         total_to_cgmf=total_to_cgmf)

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
    companies = db.get_all_companies()
    employees = db.get_all_employees()
    cgmf_list = db.get_all_cgmf()
    return render_template('admin/manage_accounts.html', accounts=accounts, companies=companies, employees=employees, cgmf_list=cgmf_list)

@app.route('/admin/add-company', methods=['POST'])
@login_required
def admin_add_company():
    if current_user.role != 'Admin':
        flash('Unauthorized access', 'error')
        return redirect(url_for('index'))
    
    company_name = request.form.get('company_name')
    company_code = request.form.get('company_code', '')
    contact_person = request.form.get('contact_person', '')
    mobile = request.form.get('mobile', '')
    address = request.form.get('address', '')
    
    company_id = db.add_company(company_name, company_code, contact_person, mobile, address)
    
    if company_id:
        flash(f'Company {company_name} added successfully!', 'success')
    else:
        flash('Error adding company. Company may already exist.', 'error')
    
    return redirect(url_for('admin_manage_accounts'))

@app.route('/admin/add-employee', methods=['POST'])
@login_required
def admin_add_employee():
    if current_user.role != 'Admin':
        flash('Unauthorized access', 'error')
        return redirect(url_for('index'))
    
    employee_name = request.form.get('employee_name')
    employee_code = request.form.get('employee_code', '')
    mobile = request.form.get('mobile', '')
    designation = request.form.get('designation', '')
    
    employee_id = db.add_employee(employee_name, employee_code, mobile, designation)
    
    if employee_id:
        flash(f'Employee {employee_name} added successfully!', 'success')
    else:
        flash('Error adding employee.', 'error')
    
    return redirect(url_for('admin_manage_accounts'))

@app.route('/admin/add-cgmf', methods=['POST'])
@login_required
def admin_add_cgmf():
    if current_user.role != 'Admin':
        flash('Unauthorized access', 'error')
        return redirect(url_for('index'))
    
    district = request.form.get('district')
    destination = request.form.get('destination')
    society_name = request.form.get('society_name')
    contact = request.form.get('contact', '')
    
    cgmf_id = db.add_cgmf(district, destination, society_name, contact)
    
    if cgmf_id:
        flash(f'CGMF Society "{society_name}" added successfully!', 'success')
    else:
        flash('Error adding CGMF society.', 'error')
    
    return redirect(url_for('admin_manage_accounts'))

@app.route('/admin/add-product', methods=['POST'])
@login_required
def admin_add_product():
    if current_user.role != 'Admin':
        flash('Unauthorized access', 'error')
        return redirect(url_for('index'))
    
    product_name = request.form.get('product_name')
    product_code = request.form.get('product_code')
    product_type = request.form.get('product_type', 'Fertilizer')
    unit = request.form.get('unit', 'MT')
    unit_per_bag = float(request.form.get('unit_per_bag', 50.0))
    unit_type = request.form.get('unit_type', 'kg')
    description = request.form.get('description', '')
    
    product_id = db.add_product(product_name, product_code, product_type, unit, unit_per_bag, unit_type, description)
    
    if product_id:
        flash(f'Product {product_name} added successfully!', 'success')
    else:
        flash('Error adding product. Product may already exist.', 'error')
    
    return redirect(url_for('admin_add_rake'))


# ========== ADMIN Viewing Routes (All System Data) ==========

@app.route('/admin/all-loading-slips')
@login_required
def admin_all_loading_slips():
    """Admin view of all loading slips from all sources"""
    if current_user.role != 'Admin':
        flash('Unauthorized access', 'error')
        return redirect(url_for('index'))
    
    loading_slips = db.get_all_loading_slips_with_status()
    return render_template('admin/all_loading_slips.html', loading_slips=loading_slips)

@app.route('/admin/all-builties')
@login_required
def admin_all_builties():
    """Admin view of all builties"""
    if current_user.role != 'Admin':
        flash('Unauthorized access', 'error')
        return redirect(url_for('index'))
    
    builties = db.get_all_builties()
    return render_template('admin/all_builties.html', builties=builties)

@app.route('/admin/all-ebills')
@login_required
def admin_all_ebills():
    """Admin view of all e-bills"""
    if current_user.role != 'Admin':
        flash('Unauthorized access', 'error')
        return redirect(url_for('index'))
    
    ebills = db.get_all_ebills()
    return render_template('admin/all_ebills.html', ebills=ebills)

@app.route('/admin/warehouse-transactions')
@login_required
def admin_warehouse_transactions():
    """Admin view of all warehouse stock IN and OUT transactions"""
    if current_user.role != 'Admin':
        flash('Unauthorized access', 'error')
        return redirect(url_for('index'))
    
    # Get all warehouse transactions
    transactions = db.execute_custom_query('''
        SELECT ws.stock_id, ws.transaction_type, ws.quantity_mt, ws.date,
               ws.notes, ws.created_at,
               w.warehouse_name,
               b.builty_number, b.goods_name,
               COALESCE(a.account_name, 'N/A') as account_name
        FROM warehouse_stock ws
        LEFT JOIN warehouses w ON ws.warehouse_id = w.warehouse_id
        LEFT JOIN builty b ON ws.builty_id = b.builty_id
        LEFT JOIN accounts a ON ws.account_id = a.account_id
        ORDER BY ws.created_at DESC
    ''')
    
    # Ensure transactions is always a list
    if transactions is None:
        transactions = []
    
    return render_template('admin/warehouse_transactions.html', transactions=transactions)

@app.route('/admin/warehouse-summary')
@login_required
def admin_warehouse_summary():
    """Admin view of warehouse stock summary - same as warehouse balance page"""
    if current_user.role != 'Admin':
        flash('Unauthorized access', 'error')
        return redirect(url_for('index'))
    
    # Get filter parameters
    selected_warehouse = request.args.get('warehouse', 'all')
    date_filter = request.args.get('date_filter', 'all')
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    
    # Get all warehouses for dropdown
    warehouses = db.get_all_warehouses()
    
    # Build date condition
    date_condition = ""
    date_params = []
    
    from datetime import datetime, timedelta
    today = datetime.now().strftime('%Y-%m-%d')
    
    if date_filter == 'today':
        date_condition = " AND DATE(ws.date) = ?"
        date_params = [today]
    elif date_filter == 'week':
        week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        date_condition = " AND DATE(ws.date) >= ?"
        date_params = [week_ago]
    elif date_filter == 'month':
        month_ago = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        date_condition = " AND DATE(ws.date) >= ?"
        date_params = [month_ago]
    elif date_filter == 'custom' and start_date and end_date:
        date_condition = " AND DATE(ws.date) >= ? AND DATE(ws.date) <= ?"
        date_params = [start_date, end_date]
    
    # Get overall stock statistics
    warehouse_balances = []
    
    # Build warehouse condition
    if selected_warehouse != 'all':
        try:
            selected_warehouse_id = int(selected_warehouse)
            warehouse_filter = [w for w in warehouses if w[0] == selected_warehouse_id]
            warehouses_to_process = warehouse_filter
        except:
            warehouses_to_process = warehouses
    else:
        warehouses_to_process = warehouses
    
    for warehouse in warehouses_to_process:
        # Get filtered balance
        if date_condition:
            result = db.execute_custom_query(f'''
                SELECT 
                    COALESCE(SUM(CASE WHEN transaction_type = 'IN' THEN quantity_mt ELSE 0 END), 0) as stock_in,
                    COALESCE(SUM(CASE WHEN transaction_type = 'OUT' THEN quantity_mt ELSE 0 END), 0) as stock_out
                FROM warehouse_stock ws
                WHERE warehouse_id = ? {date_condition}
            ''', [warehouse[0]] + date_params)
            if result:
                stock_in = result[0][0] or 0
                stock_out = result[0][1] or 0
            else:
                stock_in, stock_out = 0, 0
        else:
            balance = db.get_warehouse_balance_stock(warehouse[0])
            stock_in = balance.get('stock_in', 0)
            stock_out = balance.get('stock_out', 0)
        
        warehouse_balances.append([
            warehouse[0],  # warehouse_id
            warehouse[1],  # warehouse_name
            warehouse[2],  # location
            stock_in,
            stock_out
        ])
    
    # Calculate totals
    total_stock_in = sum(w[3] for w in warehouse_balances)
    total_stock_out = sum(w[4] for w in warehouse_balances)
    total_balance = total_stock_in - total_stock_out
    
    # Get recent transactions for the filtered scope
    if selected_warehouse != 'all':
        wh_cond = "ws.warehouse_id = ?"
        wh_params = [int(selected_warehouse)]
    else:
        wh_cond = "1=1"
        wh_params = []
    
    recent_transactions = db.execute_custom_query(f'''
        SELECT ws.date, ws.transaction_type, ws.quantity_mt, w.warehouse_name,
               COALESCE(b.builty_number, 'Direct Entry') as builty_number,
               ws.notes
        FROM warehouse_stock ws
        JOIN warehouses w ON ws.warehouse_id = w.warehouse_id
        LEFT JOIN builty b ON ws.builty_id = b.builty_id
        WHERE {wh_cond} {date_condition}
        ORDER BY ws.date DESC, ws.created_at DESC
        LIMIT 20
    ''', wh_params + date_params)
    
    # Get selected warehouse name for display
    selected_warehouse_name = "All Warehouses"
    if selected_warehouse != 'all':
        for wh in warehouses:
            if wh[0] == int(selected_warehouse):
                selected_warehouse_name = wh[1]
                break
    
    return render_template('admin/warehouse_summary.html',
                         warehouse_balances=warehouse_balances,
                         total_stock_in=total_stock_in,
                         total_stock_out=total_stock_out,
                         total_balance=total_balance,
                         warehouses=warehouses,
                         selected_warehouse=selected_warehouse,
                         selected_warehouse_name=selected_warehouse_name,
                         date_filter=date_filter,
                         start_date=start_date,
                         end_date=end_date,
                         recent_transactions=recent_transactions)

@app.route('/api/warehouse-account-stock/<int:warehouse_id>')
@login_required
def api_warehouse_account_stock(warehouse_id):
    """API to get account-wise stock breakdown for a warehouse"""
    # Get stock IN grouped by account
    account_stock = db.execute_custom_query('''
        SELECT a.account_id, a.account_name, a.account_type,
               SUM(ws.quantity_mt) as total_stock
        FROM warehouse_stock ws
        JOIN accounts a ON ws.account_id = a.account_id
        WHERE ws.warehouse_id = ? AND ws.transaction_type = 'IN'
        GROUP BY a.account_id, a.account_name, a.account_type
        ORDER BY total_stock DESC
    ''', (warehouse_id,))
    
    result = []
    for row in account_stock:
        result.append({
            'account_id': row[0],
            'account_name': row[1],
            'account_type': row[2],
            'total_stock': row[3]
        })
    
    return jsonify(result)

@app.route('/admin/edit-warehouse-stock', methods=['GET', 'POST'])
@login_required
def admin_edit_warehouse_stock():
    """Admin can edit warehouse stock allocations"""
    if current_user.role != 'Admin':
        flash('Unauthorized access', 'error')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        stock_id = int(request.form.get('stock_id'))
        quantity_mt = float(request.form.get('quantity_mt'))
        account_type = request.form.get('account_type')
        dealer_name = request.form.get('dealer_name')
        remark = request.form.get('remark')
        
        success = db.update_warehouse_stock_allocation(stock_id, quantity_mt, account_type, dealer_name, remark)
        
        if success:
            flash('Warehouse stock allocation updated successfully!', 'success')
        else:
            flash('Error updating warehouse stock allocation', 'error')
        
        return redirect(url_for('admin_edit_warehouse_stock'))
    
    # Get all warehouse stock entries
    stock_entries = db.execute_custom_query('''
        SELECT ws.stock_id, ws.serial_number, w.warehouse_name, c.company_name, p.product_name,
               ws.quantity_mt, ws.account_type, ws.dealer_name, ws.remark, ws.date
        FROM warehouse_stock ws
        LEFT JOIN warehouses w ON ws.warehouse_id = w.warehouse_id
        LEFT JOIN companies c ON ws.company_id = c.company_id
        LEFT JOIN products p ON ws.product_id = p.product_id
        WHERE ws.transaction_type = 'IN'
        ORDER BY ws.date DESC
    ''')
    
    return render_template('admin/edit_warehouse_stock.html', stock_entries=stock_entries)

@app.route('/admin/download-eway-bill/<filename>')
@login_required
def admin_download_eway_bill(filename):
    """Admin can also download eway bill PDFs"""
    if current_user.role != 'Admin':
        flash('Unauthorized access', 'error')
        return redirect(url_for('index'))
    
    upload_folder = os.path.join(os.path.dirname(__file__), 'uploads', 'eway_bills')
    filepath = os.path.join(upload_folder, filename)
    
    if os.path.exists(filepath):
        return send_file(filepath, as_attachment=True)
    else:
        flash('File not found', 'error')
        return redirect(url_for('admin_all_ebills'))

@app.route('/admin/print-loading-slip/<int:slip_id>')
@login_required
def admin_print_loading_slip(slip_id):
    """Admin can print any loading slip"""
    if current_user.role != 'Admin':
        flash('Unauthorized access', 'error')
        return redirect(url_for('index'))
    
    # Get loading slip details
    slip = db.execute_custom_query('''
        SELECT ls.slip_id, ls.rake_code, ls.slip_number, ls.loading_point_name,
               ls.destination, ls.quantity_bags, ls.quantity_mt, ls.goods_name,
               ls.truck_driver, ls.truck_owner, ls.mobile_number_1, ls.mobile_number_2,
               ls.wagon_number, ls.created_at, t.truck_number,
               COALESCE(a.account_name, w.warehouse_name) as destination_name,
               COALESCE(a.account_type, 'Warehouse') as destination_type
        FROM loading_slips ls
        LEFT JOIN trucks t ON ls.truck_id = t.truck_id
        LEFT JOIN accounts a ON ls.account_id = a.account_id
        LEFT JOIN warehouses w ON ls.warehouse_id = w.warehouse_id
        WHERE ls.slip_id = ?
    ''', (slip_id,))
    
    if not slip:
        flash('Loading slip not found', 'error')
        return redirect(url_for('admin_all_loading_slips'))
    
    return render_template('print_loading_slip.html', slip=slip[0])

@app.route('/admin/print-builty/<int:builty_id>')
@login_required
def admin_print_builty(builty_id):
    """Admin can print any builty"""
    if current_user.role != 'Admin':
        flash('Unauthorized access', 'error')
        return redirect(url_for('index'))
    
    # Get builty details with all related information
    builty = db.get_builty_by_id(builty_id)
    
    if not builty:
        flash('Builty not found', 'error')
        return redirect(url_for('admin_all_builties'))
    
    # Convert to dict for easier template access
    # Explicit column order from get_builty_by_id query
    builty_dict = {
        'builty_id': builty[0],
        'builty_number': builty[1],
        'rake_code': builty[2],
        'date': builty[3],
        'rake_point_name': builty[4],
        'account_id': builty[5],
        'warehouse_id': builty[6],
        'cgmf_id': builty[7],
        'truck_id': builty[8],
        'loading_point': builty[9],
        'unloading_point': builty[10],
        'goods_name': builty[11],
        'number_of_bags': builty[12],
        'quantity_mt': builty[13],
        'kg_per_bag': builty[14],
        'rate_per_mt': builty[15],
        'total_freight': builty[16],
        'advance': builty[17],
        'to_pay': builty[18],
        'lr_number': builty[19],
        'lr_index': builty[20],
        'created_by_role': builty[21],
        'created_at': builty[22],
        'account_name': builty[23],
        'warehouse_name': builty[24],
        'truck_number': builty[25],
        'driver_name': builty[26],
        'driver_mobile': builty[27],
        'owner_name': builty[28],
        'owner_mobile': builty[29]
    }
    
    return render_template('print_builty.html', builty=builty_dict)

# ========== RAKE POINT Dashboard & Routes ==========

@app.route('/rakepoint/dashboard')
@login_required
def rakepoint_dashboard():
    if current_user.role != 'RakePoint':
        flash('Unauthorized access', 'error')
        return redirect(url_for('index'))
    
    # Get all data
    all_builties = db.get_all_builties()
    all_loading_slips = db.get_all_loading_slips_with_status()
    all_rakes = db.get_all_rakes()
    
    # Recent builties (last 10)
    recent_builties = all_builties[:10]
    
    # Calculate statistics
    total_builties = len(all_builties)
    total_loading_slips = len(all_loading_slips)
    
    # Count active rakes (rakes with remaining quantity > 0)
    active_rakes = 0
    for rake in all_rakes:
        rake_code = rake[1]
        balance = db.get_rake_balance(rake_code)
        if balance and balance['remaining'] > 0:
            active_rakes += 1
    
    # Today's builties (created today)
    today = datetime.now().date()
    today_builties = 0
    for builty in all_builties:
        builty_date_str = builty[3]  # date field
        try:
            builty_date = datetime.strptime(builty_date_str, '%Y-%m-%d').date()
            if builty_date == today:
                today_builties += 1
        except:
            pass
    
    return render_template('rakepoint/dashboard.html', 
                         recent_builties=recent_builties,
                         rakes=all_rakes,
                         total_builties=total_builties,
                         total_loading_slips=total_loading_slips,
                         active_rakes=active_rakes,
                         today_builties=today_builties)

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
        
        # Determine if account_warehouse is account, warehouse, or CGMF
        account_id = None
        warehouse_id = None
        cgmf_id = None
        
        # Check if it's a CGMF account
        if account_warehouse and account_warehouse.startswith('CGMF:'):
            cgmf_id = int(account_warehouse.split(':')[1])
        else:
            # Simple check for account or warehouse
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
        
        # Parse freight details and advance
        freight_advance = float(request.form.get('freight_advance', 0))
        to_pay = float(request.form.get('to_pay', 0))
        
        # Calculate kg per bag (assuming 50kg per bag as default)
        kg_per_bag = (quantity_wt_mt * 1000) / number_of_bags if number_of_bags > 0 else 50
        rate_per_mt = total_freight / quantity_wt_mt if quantity_wt_mt > 0 else 0
        
        builty_id = db.add_builty(builty_number, rake_code, date, rake_point_name, account_id, warehouse_id,
                                  truck_id, loading_point, unloading_point, goods_name, number_of_bags,
                                  quantity_wt_mt, kg_per_bag, rate_per_mt, total_freight, freight_advance, to_pay, lr_number,
                                  0, 'RakePoint', cgmf_id)
        
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
    cgmf_list = db.get_all_cgmf()
    
    return render_template('rakepoint/create_builty.html', 
                         accounts=accounts, 
                         warehouses=warehouses,
                         rakes=rakes,
                         loading_slips=loading_slips,
                         cgmf_list=cgmf_list)

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
        sub_head = request.form.get('sub_head', '')  # Sub head for Payal accounts
        
        # CRITICAL: Check rake quantity balance before creating loading slip
        rake_balance = db.get_rake_balance(rake_code)
        if not rake_balance:
            flash('Error: Invalid rake code', 'error')
            return redirect(url_for('rakepoint_create_loading_slip'))
        
        if quantity_in_mt > rake_balance['remaining']:
            flash(f'Error: Insufficient rake quantity! Remaining: {rake_balance["remaining"]:.2f} MT, Requested: {quantity_in_mt:.2f} MT', 'error')
            return redirect(url_for('rakepoint_create_loading_slip'))
        
        # Determine if dispatch is to account, warehouse, or CGMF
        accounts = db.get_all_accounts()
        warehouses = db.get_all_warehouses()
        cgmf_list = db.get_all_cgmf()
        account_id = None
        warehouse_id = None
        cgmf_id = None
        
        # Check if it's a CGMF (format: CGMF:<id>)
        if account and account.startswith('CGMF:'):
            cgmf_id = int(account.split(':')[1])
        else:
            # Check if it's an account
            for acc in accounts:
                if acc[1] == account:
                    account_id = acc[0]
                    break
            
            # If not found in accounts, check warehouses
            if account_id is None:
                for wh in warehouses:
                    if wh[1] == account:
                        warehouse_id = wh[0]
                        break
        
        # Check if truck exists, if not create it with driver/owner details
        truck = db.get_truck_by_number(truck_number)
        if not truck:
            truck_id = db.add_truck(truck_number, truck_driver, mobile_number_1, truck_owner, mobile_number_2)
        else:
            truck_id = truck[0]
        
        slip_id = db.add_loading_slip(rake_code, serial_number, loading_point, destination,
                                      account_id, warehouse_id, quantity_in_bags, quantity_in_mt, truck_id, 
                                      wagon_number, goods_name, truck_driver, truck_owner,
                                      mobile_number_1, mobile_number_2, truck_details, None, cgmf_id, sub_head)
        
        if slip_id:
            flash(f'Loading slip #{serial_number} created successfully!', 'success')
            if request.form.get('action') == 'print':
                # Store slip_id in session to open print in new window
                return render_template('rakepoint/create_loading_slip.html', 
                                     rakes=db.get_all_rakes(),
                                     accounts=db.get_all_accounts(),
                                     warehouses=db.get_all_warehouses(),
                                     cgmf_list=db.get_all_cgmf(),
                                     trucks=db.get_all_trucks(),
                                     builties=db.get_all_builties(),
                                     print_slip_id=slip_id)
            return redirect(url_for('rakepoint_dashboard'))
        else:
            flash('Error creating loading slip', 'error')
    
    rakes = db.get_all_rakes()
    accounts = db.get_all_accounts()
    warehouses = db.get_all_warehouses()
    cgmf_list = db.get_all_cgmf()
    trucks = db.get_all_trucks()
    builties = db.get_all_builties()
    
    return render_template('rakepoint/create_loading_slip.html', 
                         rakes=rakes,
                         accounts=accounts,
                         warehouses=warehouses,
                         cgmf_list=cgmf_list,
                         trucks=trucks,
                         builties=builties)

@app.route('/api/rake-balance/<rake_code>')
@login_required
def get_rake_balance_api(rake_code):
    """API endpoint to get rake balance"""
    if current_user.role != 'RakePoint':
        return jsonify({'error': 'Unauthorized'}), 403
    
    balance = db.get_rake_balance(rake_code)
    if balance:
        return jsonify(balance)
    else:
        return jsonify({'error': 'Rake not found'}), 404

@app.route('/api/next-serial-number/<rake_code>')
@login_required
def get_next_serial_number_api(rake_code):
    """API endpoint to get next serial number for rake"""
    if current_user.role != 'RakePoint':
        return jsonify({'error': 'Unauthorized'}), 403
    
    next_serial = db.get_next_serial_number_for_rake(rake_code)
    return jsonify({'next_serial': next_serial})

@app.route('/api/next-lr-number')
@login_required
def get_next_lr_number_api():
    """API endpoint to get next LR number"""
    if current_user.role not in ['RakePoint', 'Warehouse']:
        return jsonify({'error': 'Unauthorized'}), 403
    
    next_lr = db.get_next_lr_number()
    return jsonify({'next_lr': next_lr})

@app.route('/api/next-warehouse-serial/<int:warehouse_id>')
@login_required
def get_next_warehouse_serial_api(warehouse_id):
    """API endpoint to get next warehouse stock serial number"""
    if current_user.role not in ['Warehouse', 'Admin']:
        return jsonify({'error': 'Unauthorized'}), 403
    
    next_serial = db.get_next_warehouse_stock_serial(warehouse_id)
    return jsonify({'serial_number': next_serial})

@app.route('/api/builty-details/<int:builty_id>')
@login_required
def get_builty_details_api(builty_id):
    """API endpoint to get builty details for auto-filling warehouse stock in form"""
    if current_user.role not in ['Warehouse', 'Admin']:
        return jsonify({'error': 'Unauthorized'}), 403
    
    builty = db.get_builty_by_id(builty_id)
    
    if not builty:
        return jsonify({'error': 'Builty not found'}), 404
    
    # Get rake details to find company and product info
    rake = db.execute_custom_query('''
        SELECT r.company_name, r.product_name, r.rake_point_name
        FROM rakes r
        WHERE r.rake_code = ?
    ''', (builty[2],))
    
    company_name = rake[0][0] if rake else None
    product_name = rake[0][1] if rake else builty[10]  # fallback to goods_name
    
    # Find company_id by company_name
    company_id = None
    if company_name:
        company = db.execute_custom_query('SELECT company_id FROM companies WHERE company_name = ?', (company_name,))
        if company:
            company_id = company[0][0]
    
    # Find product_id by product_name
    product_id = None
    if product_name:
        product = db.execute_custom_query('SELECT product_id FROM products WHERE product_name = ?', (product_name,))
        if product:
            product_id = product[0][0]
    
    return jsonify({
        'builty_number': builty[1],
        'goods_name': builty[10],
        'quantity_mt': float(builty[12]),
        'company_id': company_id,
        'product_id': product_id,
        'account_id': builty[5],
        'warehouse_id': builty[6]
    })

@app.route('/api/next-loading-slip-serial/<warehouse_name>')
@login_required
def get_next_loading_slip_serial_api(warehouse_name):
    """API endpoint to get next loading slip serial number for warehouse"""
    if current_user.role not in ['Warehouse', 'Admin']:
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Get the maximum serial number for this warehouse
    result = db.execute_custom_query('''
        SELECT MAX(CAST(slip_number AS INTEGER)) 
        FROM loading_slips 
        WHERE loading_point_name = ?
    ''', (warehouse_name,))
    
    max_serial = result[0][0] if result and result[0][0] else 0
    next_serial = max_serial + 1
    
    return jsonify({'serial_number': next_serial})

@app.route('/api/account-dispatches/<account_name>')
@login_required
def get_account_dispatches(account_name):
    """API endpoint to get all dispatches for a specific account"""
    if current_user.role != 'Admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    dispatches = db.execute_custom_query('''
        SELECT b.rake_code, b.builty_number, b.date, b.quantity_mt, b.goods_name
        FROM builty b
        JOIN accounts a ON b.account_id = a.account_id
        WHERE a.account_name = ?
        ORDER BY b.date DESC, b.builty_id DESC
    ''', (account_name,))
    
    result = []
    if dispatches:
        for d in dispatches:
            result.append({
                'rake_code': d[0] or 'N/A',
                'builty_number': d[1],
                'date': d[2],
                'quantity_mt': d[3],
                'goods_name': d[4] or 'N/A'
            })
    
    return jsonify(result)

@app.route('/api/cgmf-dispatches/<society_name>')
@login_required
def get_cgmf_dispatches(society_name):
    """API endpoint to get all dispatches for a specific CGMF society"""
    if current_user.role != 'Admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    dispatches = db.execute_custom_query('''
        SELECT b.rake_code, b.builty_number, b.date, b.quantity_mt, b.goods_name
        FROM builty b
        JOIN cgmf c ON b.cgmf_id = c.cgmf_id
        WHERE c.society_name = ?
        ORDER BY b.date DESC, b.builty_id DESC
    ''', (society_name,))
    
    result = []
    if dispatches:
        for d in dispatches:
            result.append({
                'rake_code': d[0] or 'N/A',
                'builty_number': d[1],
                'date': d[2],
                'quantity_mt': d[3],
                'goods_name': d[4] or 'N/A'
            })
    
    return jsonify(result)

@app.route('/rakepoint/loading-slips')
@login_required
def rakepoint_loading_slips():
    if current_user.role != 'RakePoint':
        flash('Unauthorized access', 'error')
        return redirect(url_for('index'))
    
    loading_slips = db.get_all_loading_slips_with_status()
    
    return render_template('rakepoint/loading_slips.html', loading_slips=loading_slips)

@app.route('/rakepoint/print-loading-slip/<int:slip_id>')
@login_required
def rakepoint_print_loading_slip(slip_id):
    """Print a specific loading slip"""
    if current_user.role != 'RakePoint':
        flash('Unauthorized access', 'error')
        return redirect(url_for('index'))
    
    # Get loading slip details
    slip = db.execute_custom_query('''
        SELECT ls.slip_id, ls.rake_code, ls.slip_number, ls.loading_point_name,
               ls.destination, ls.quantity_bags, ls.quantity_mt, ls.goods_name,
               ls.truck_driver, ls.truck_owner, ls.mobile_number_1, ls.mobile_number_2,
               ls.wagon_number, ls.created_at, t.truck_number,
               COALESCE(a.account_name, w.warehouse_name) as destination_name,
               COALESCE(a.account_type, 'Warehouse') as destination_type
        FROM loading_slips ls
        LEFT JOIN trucks t ON ls.truck_id = t.truck_id
        LEFT JOIN accounts a ON ls.account_id = a.account_id
        LEFT JOIN warehouses w ON ls.warehouse_id = w.warehouse_id
        WHERE ls.slip_id = ?
    ''', (slip_id,))
    
    if not slip:
        flash('Loading slip not found', 'error')
        return redirect(url_for('rakepoint_loading_slips'))
    
    return render_template('print_loading_slip.html', slip=slip[0])

@app.route('/rakepoint/print-builty/<int:builty_id>')
@login_required
def rakepoint_print_builty(builty_id):
    """RakePoint can print builty"""
    if current_user.role != 'RakePoint':
        flash('Unauthorized access', 'error')
        return redirect(url_for('index'))
    
    # Get builty details with all related information
    builty = db.get_builty_by_id(builty_id)
    
    if not builty:
        flash('Builty not found', 'error')
        return redirect(url_for('rakepoint_dashboard'))
    
    # Convert to dict for easier template access
    # Explicit column order from get_builty_by_id query
    builty_dict = {
        'builty_id': builty[0],
        'builty_number': builty[1],
        'rake_code': builty[2],
        'date': builty[3],
        'rake_point_name': builty[4],
        'account_id': builty[5],
        'warehouse_id': builty[6],
        'cgmf_id': builty[7],
        'truck_id': builty[8],
        'loading_point': builty[9],
        'unloading_point': builty[10],
        'goods_name': builty[11],
        'number_of_bags': builty[12],
        'quantity_mt': builty[13],
        'kg_per_bag': builty[14],
        'rate_per_mt': builty[15],
        'total_freight': builty[16],
        'advance': builty[17],
        'to_pay': builty[18],
        'lr_number': builty[19],
        'lr_index': builty[20],
        'created_by_role': builty[21],
        'created_at': builty[22],
        'account_name': builty[23],
        'warehouse_name': builty[24],
        'truck_number': builty[25],
        'driver_name': builty[26],
        'driver_mobile': builty[27],
        'owner_name': builty[28],
        'owner_mobile': builty[29]
    }
    
    return render_template('print_builty.html', builty=builty_dict)

@app.route('/rakepoint/loading-slips/<rake_code>')
@login_required
def rakepoint_view_loading_slips(rake_code):
    if current_user.role != 'RakePoint':
        flash('Unauthorized access', 'error')
        return redirect(url_for('index'))
    
    rake = db.get_rake_by_code(rake_code)
    slips = db.get_loading_slips_by_rake(rake_code)
    
    return render_template('rakepoint/loading_slips.html', rake=rake, loading_slips=slips)

@app.route('/rakepoint/all-builties')
@login_required
def rakepoint_all_builties():
    """View all builties created by rakepoint"""
    if current_user.role != 'RakePoint':
        flash('Unauthorized access', 'error')
        return redirect(url_for('index'))
    
    # Get all builties created by rakepoint
    builties = db.execute_custom_query('''
        SELECT b.*, a.account_name, w.warehouse_name, t.truck_number
        FROM builty b
        LEFT JOIN accounts a ON b.account_id = a.account_id
        LEFT JOIN warehouses w ON b.warehouse_id = w.warehouse_id
        LEFT JOIN trucks t ON b.truck_id = t.truck_id
        WHERE b.created_by_role = 'RakePoint'
        ORDER BY b.created_at DESC
    ''')
    
    return render_template('rakepoint/all_builties.html', builties=builties)

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
    recent_movements = db.execute_custom_query('''
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
    today_stock_in_result = db.execute_custom_query('''
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
        serial_number = request.form.get('serial_number')
        warehouse_id = int(request.form.get('warehouse_name'))
        source_type = request.form.get('source_type', 'rake')
        builty_id = request.form.get('builty_number') if source_type == 'rake' else None
        truck_id = request.form.get('truck_number') if source_type == 'truck' else None
        company_id = int(request.form.get('company_id'))
        product_id = int(request.form.get('product_id'))
        quantity = float(request.form.get('unloaded_quantity'))
        employee_id = int(request.form.get('employee_id'))
        
        # Handle account_id which may be a regular account or CGMF
        account_id_raw = request.form.get('account_id')
        account_id = None
        cgmf_id = None
        
        if account_id_raw.startswith('CGMF:'):
            cgmf_id = int(account_id_raw.replace('CGMF:', ''))
        else:
            account_id = int(account_id_raw)
        
        stock_in_date = request.form.get('stock_in_date')
        remarks = request.form.get('remarks', '')
        sub_head = request.form.get('sub_head', '')  # Sub head for Payal accounts
        
        # Convert builty_id and truck_id to integers if present
        if builty_id:
            builty_id = int(builty_id)
            
            # Check if this builty has already been used for stock IN
            existing_stock = db.execute_custom_query('''
                SELECT stock_id, w.warehouse_name, ws.date, ws.quantity_mt
                FROM warehouse_stock ws
                JOIN warehouses w ON ws.warehouse_id = w.warehouse_id
                WHERE ws.builty_id = ? AND ws.transaction_type = 'IN'
            ''', (builty_id,))
            
            if existing_stock:
                warehouse_name = existing_stock[0][1]
                stock_date = existing_stock[0][2]
                stock_quantity = existing_stock[0][3]
                flash(f'Error: This builty has already been recorded for Stock IN at {warehouse_name} on {stock_date} ({stock_quantity:.2f} MT). Cannot record duplicate stock IN for the same builty.', 'error')
                # Re-render form with all the data
                warehouses = db.get_all_warehouses()
                # Only show builties that were sent to warehouses (have warehouse_id) and not yet used for stock IN
                builties = db.execute_custom_query('''
                    SELECT b.*, w.warehouse_name
                    FROM builty b
                    JOIN warehouses w ON b.warehouse_id = w.warehouse_id
                    LEFT JOIN warehouse_stock ws ON b.builty_id = ws.builty_id AND ws.transaction_type = 'IN'
                    WHERE b.warehouse_id IS NOT NULL AND ws.stock_id IS NULL
                    ORDER BY b.builty_id DESC
                ''')
                trucks = db.get_all_trucks()
                companies = db.get_all_companies()
                products = db.get_all_products()
                employees = db.get_all_employees()
                accounts = db.get_all_accounts()
                cgmf_list = db.get_all_cgmf()
                recent_stock_in = db.execute_custom_query('''
                    SELECT ws.date, COALESCE(b.builty_number, 'Direct Truck') as builty_number, 
                           w.warehouse_name, COALESCE(a.account_name, 'N/A') as account_name,
                           ws.quantity_mt, COALESCE(e.employee_name, 'N/A') as employee_name
                    FROM warehouse_stock ws
                    JOIN warehouses w ON ws.warehouse_id = w.warehouse_id
                    LEFT JOIN builty b ON ws.builty_id = b.builty_id
                    LEFT JOIN accounts a ON ws.account_id = a.account_id
                    LEFT JOIN employees e ON ws.employee_id = e.employee_id
                    WHERE ws.transaction_type = 'IN'
                    ORDER BY ws.date DESC, ws.stock_id DESC
                    LIMIT 10
                ''')
                return render_template('warehouse/stock_in.html', 
                                     warehouses=warehouses,
                                     builties=builties,
                                     trucks=trucks,
                                     companies=companies,
                                     products=products,
                                     employees=employees,
                                     accounts=accounts,
                                     cgmf_list=cgmf_list,
                                     recent_stock_in=recent_stock_in)
        if truck_id:
            truck_id = int(truck_id)
        
        stock_id = db.add_warehouse_stock_in(
            warehouse_id=warehouse_id,
            builty_id=builty_id,
            quantity_mt=quantity,
            employee_id=employee_id,
            account_id=account_id,
            cgmf_id=cgmf_id,
            date=stock_in_date,
            notes=remarks,
            company_id=company_id,
            product_id=product_id,
            source_type=source_type,
            truck_id=truck_id,
            serial_number=int(serial_number) if serial_number else None,
            sub_head=sub_head
        )
        
        if stock_id:
            flash(f'Stock IN recorded successfully! Serial No: {serial_number}', 'success')
            return redirect(url_for('warehouse_dashboard'))
        else:
            flash('Error recording stock IN', 'error')
    
    warehouses = db.get_all_warehouses()
    # Get only builties that were sent to warehouses (have warehouse_id) and haven't been used for stock IN yet
    builties = db.execute_custom_query('''
        SELECT b.*, w.warehouse_name as dest_warehouse_name
        FROM builty b
        JOIN warehouses w ON b.warehouse_id = w.warehouse_id
        LEFT JOIN warehouse_stock ws ON b.builty_id = ws.builty_id AND ws.transaction_type = 'IN'
        WHERE b.warehouse_id IS NOT NULL AND ws.stock_id IS NULL
        ORDER BY b.builty_id DESC
    ''')
    trucks = db.get_all_trucks()
    companies = db.get_all_companies()
    products = db.get_all_products()
    employees = db.get_all_employees()
    accounts = db.get_all_accounts()
    cgmf_list = db.get_all_cgmf()
    
    # Get recent stock IN entries for display
    recent_stock_in = db.execute_custom_query('''
        SELECT ws.date, COALESCE(b.builty_number, 'Direct Truck') as builty_number, 
               w.warehouse_name, COALESCE(a.account_name, 'N/A') as account_name,
               ws.quantity_mt, COALESCE(e.employee_name, 'N/A') as employee_name
        FROM warehouse_stock ws
        JOIN warehouses w ON ws.warehouse_id = w.warehouse_id
        LEFT JOIN builty b ON ws.builty_id = b.builty_id
        LEFT JOIN accounts a ON ws.account_id = a.account_id
        LEFT JOIN employees e ON ws.employee_id = e.employee_id
        WHERE ws.transaction_type = 'IN'
        ORDER BY ws.date DESC, ws.stock_id DESC
        LIMIT 10
    ''')
    
    return render_template('warehouse/stock_in.html', 
                         warehouses=warehouses,
                         builties=builties,
                         trucks=trucks,
                         companies=companies,
                         products=products,
                         employees=employees,
                         accounts=accounts,
                         cgmf_list=cgmf_list,
                         recent_stock_in=recent_stock_in)

@app.route('/warehouse/create-loading-slip', methods=['GET', 'POST'])
@login_required
def warehouse_create_loading_slip():
    if current_user.role != 'Warehouse':
        flash('Unauthorized access', 'error')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        warehouse_name = request.form.get('warehouse_name')
        serial_number = int(request.form.get('serial_number'))
        loading_point = request.form.get('loading_point')
        destination = request.form.get('destination')
        account = request.form.get('account')
        quantity_in_bags = int(request.form.get('quantity_in_bags'))
        quantity_in_mt = float(request.form.get('quantity_in_mt'))
        truck_number = request.form.get('truck_number')
        wagon_number = request.form.get('wagon_number', '')
        goods_name = request.form.get('goods_name')
        truck_driver = request.form.get('truck_driver')
        truck_owner = request.form.get('truck_owner')
        mobile_number_1 = request.form.get('mobile_number_1')
        mobile_number_2 = request.form.get('mobile_number_2', '')
        truck_details = request.form.get('truck_details', '')
        
        # Get warehouse ID
        warehouse = db.execute_custom_query('SELECT warehouse_id FROM warehouses WHERE warehouse_name = ?', (warehouse_name,))
        if not warehouse:
            flash('Invalid warehouse', 'error')
            return redirect(url_for('warehouse_create_loading_slip'))
        warehouse_id = warehouse[0][0]
        
        # Check if warehouse has enough stock
        balance = db.get_warehouse_balance_stock(warehouse_id)
        if balance['balance'] < quantity_in_mt:
            flash(f'Error: Warehouse has only {balance["balance"]:.2f} MT available. Cannot dispatch {quantity_in_mt:.2f} MT', 'error')
            return redirect(url_for('warehouse_create_loading_slip'))
        
        # Determine if dispatch is to account, warehouse, or CGMF
        accounts = db.get_all_accounts()
        warehouses_list = db.get_all_warehouses()
        cgmf_list = db.get_all_cgmf()
        account_id = None
        destination_warehouse_id = None
        cgmf_id = None
        
        # Check if it's a CGMF (format: CGMF_<id>)
        if account and account.startswith('CGMF_'):
            cgmf_id = int(account.replace('CGMF_', ''))
        else:
            # Check if it's an account
            for acc in accounts:
                if acc[1] == account:
                    account_id = acc[0]
                    break
            
            # If not found in accounts, check warehouses
            if account_id is None:
                for wh in warehouses_list:
                    if wh[1] == account:
                        destination_warehouse_id = wh[0]
                        break
        
        # Check if truck exists, if not create it with driver/owner details
        truck = db.get_truck_by_number(truck_number)
        if not truck:
            truck_id = db.add_truck(truck_number, truck_driver, mobile_number_1, truck_owner, mobile_number_2)
        else:
            truck_id = truck[0]
        
        # Get rake_code from most recent stock IN
        rake_code_result = db.execute_custom_query('''
            SELECT b.rake_code
            FROM warehouse_stock ws
            JOIN builty b ON ws.builty_id = b.builty_id
            WHERE ws.warehouse_id = ? AND ws.transaction_type = 'IN'
            ORDER BY ws.stock_id DESC
            LIMIT 1
        ''', (warehouse_id,))
        rake_code = rake_code_result[0][0] if rake_code_result else 'WAREHOUSE'
        
        # Add loading slip
        slip_id = db.add_loading_slip(rake_code, serial_number, loading_point, destination,
                                      account_id, destination_warehouse_id, quantity_in_bags, quantity_in_mt, 
                                      truck_id, wagon_number, goods_name, truck_driver, truck_owner,
                                      mobile_number_1, mobile_number_2, truck_details, None, cgmf_id)
        
        if slip_id:
            flash(f'Loading slip #{serial_number} created successfully!', 'success')
            if request.form.get('action') == 'print':
                # Return to form with print_slip_id to open print in new window
                return render_template('warehouse/create_loading_slip.html',
                                     warehouses=db.get_all_warehouses(),
                                     accounts=db.get_all_accounts(),
                                     cgmf_list=db.get_all_cgmf(),
                                     trucks=db.get_all_trucks(),
                                     products=db.get_all_products(),
                                     print_slip_id=slip_id)
            return redirect(url_for('warehouse_dashboard'))
        else:
            flash('Error creating loading slip', 'error')
    
    warehouses = db.get_all_warehouses()
    accounts = db.get_all_accounts()
    cgmf_list = db.get_all_cgmf()
    trucks = db.get_all_trucks()
    products = db.get_all_products()
    
    return render_template('warehouse/create_loading_slip.html',
                         warehouses=warehouses,
                         accounts=accounts,
                         cgmf_list=cgmf_list,
                         trucks=trucks,
                         products=products)

@app.route('/warehouse/loading-slips')
@login_required
def warehouse_loading_slips():
    if current_user.role != 'Warehouse':
        flash('Unauthorized access', 'error')
        return redirect(url_for('index'))
    
    # Get all loading slips (warehouse creates loading slips for stock OUT)
    # No need to filter - warehouse sees all loading slips they can access
    loading_slips = db.execute_custom_query('''
        SELECT ls.slip_id, ls.rake_code, ls.slip_number, ls.loading_point_name, 
               ls.destination, 
               COALESCE(a.account_name, w.warehouse_name) as destination_name,
               ls.quantity_bags, ls.quantity_mt, t.truck_number,
               ls.wagon_number, ls.builty_id, ls.created_at,
               ls.goods_name, ls.truck_driver, ls.truck_owner,
               ls.mobile_number_1, ls.mobile_number_2,
               b.builty_number
        FROM loading_slips ls
        LEFT JOIN accounts a ON ls.account_id = a.account_id
        LEFT JOIN warehouses w ON ls.warehouse_id = w.warehouse_id
        LEFT JOIN trucks t ON ls.truck_id = t.truck_id
        LEFT JOIN builty b ON ls.builty_id = b.builty_id
        WHERE ls.loading_point_name IN (SELECT warehouse_name FROM warehouses)
        ORDER BY ls.slip_id DESC
    ''')
    
    return render_template('warehouse/loading_slips.html', loading_slips=loading_slips)

@app.route('/warehouse/print-loading-slip/<int:slip_id>')
@login_required
def warehouse_print_loading_slip(slip_id):
    """Print a specific loading slip"""
    if current_user.role != 'Warehouse':
        flash('Unauthorized access', 'error')
        return redirect(url_for('index'))
    
    # Get loading slip details
    slip = db.execute_custom_query('''
        SELECT ls.slip_id, ls.rake_code, ls.slip_number, ls.loading_point_name,
               ls.destination, ls.quantity_bags, ls.quantity_mt, ls.goods_name,
               ls.truck_driver, ls.truck_owner, ls.mobile_number_1, ls.mobile_number_2,
               ls.wagon_number, ls.created_at, t.truck_number,
               COALESCE(a.account_name, w.warehouse_name) as destination_name,
               COALESCE(a.account_type, 'Warehouse') as destination_type
        FROM loading_slips ls
        LEFT JOIN trucks t ON ls.truck_id = t.truck_id
        LEFT JOIN accounts a ON ls.account_id = a.account_id
        LEFT JOIN warehouses w ON ls.warehouse_id = w.warehouse_id
        WHERE ls.slip_id = ?
    ''', (slip_id,))
    
    if not slip:
        flash('Loading slip not found', 'error')
        return redirect(url_for('warehouse_loading_slips'))
    
    return render_template('print_loading_slip.html', slip=slip[0])

@app.route('/warehouse/print-builty/<int:builty_id>')
@login_required
def warehouse_print_builty(builty_id):
    """Warehouse can print builty"""
    if current_user.role != 'Warehouse':
        flash('Unauthorized access', 'error')
        return redirect(url_for('index'))
    
    # Get builty details with all related information
    builty = db.get_builty_by_id(builty_id)
    
    if not builty:
        flash('Builty not found', 'error')
        return redirect(url_for('warehouse_dashboard'))
    
    # Convert to dict for easier template access
    # Explicit column order from get_builty_by_id query
    builty_dict = {
        'builty_id': builty[0],
        'builty_number': builty[1],
        'rake_code': builty[2],
        'date': builty[3],
        'rake_point_name': builty[4],
        'account_id': builty[5],
        'warehouse_id': builty[6],
        'cgmf_id': builty[7],
        'truck_id': builty[8],
        'loading_point': builty[9],
        'unloading_point': builty[10],
        'goods_name': builty[11],
        'number_of_bags': builty[12],
        'quantity_mt': builty[13],
        'kg_per_bag': builty[14],
        'rate_per_mt': builty[15],
        'total_freight': builty[16],
        'advance': builty[17],
        'to_pay': builty[18],
        'lr_number': builty[19],
        'lr_index': builty[20],
        'created_by_role': builty[21],
        'created_at': builty[22],
        'account_name': builty[23],
        'warehouse_name': builty[24],
        'truck_number': builty[25],
        'driver_name': builty[26],
        'driver_mobile': builty[27],
        'owner_name': builty[28],
        'owner_mobile': builty[29]
    }
    
    return render_template('print_builty.html', builty=builty_dict)

@app.route('/warehouse/create-builty', methods=['GET', 'POST'])
@login_required
def warehouse_create_builty():
    if current_user.role != 'Warehouse':
        flash('Unauthorized access', 'error')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        # Generate builty number
        builty_number = f"WBLT-{datetime.now().strftime('%Y%m%d')}-{datetime.now().strftime('%H%M%S')}"
        
        loading_slip_id = request.form.get('loading_slip_id')
        warehouse_name = request.form.get('warehouse_name')
        date = request.form.get('date') or request.form.get('builty_date')
        account_warehouse = request.form.get('account_warehouse')
        truck_number = request.form.get('truck_number')
        loading_point = request.form.get('loading_point')
        unloading_point = request.form.get('unloading_point')
        goods_name = request.form.get('goods_name')
        number_of_bags = int(request.form.get('number_of_bags'))
        quantity_wt_mt = float(request.form.get('quantity_wt_mt'))
        freight_details = request.form.get('freight_details')
        lr_number = request.form.get('lr_number')
        
        # Get data from loading slip if provided
        if loading_slip_id:
            loading_slip = db.execute_custom_query('''
                SELECT ls.slip_id, ls.rake_code, ls.slip_number, ls.loading_point_name,
                       ls.destination, ls.quantity_bags, ls.quantity_mt, ls.goods_name,
                       ls.truck_id, ls.truck_driver, ls.truck_owner, 
                       ls.mobile_number_1, ls.mobile_number_2,
                       t.truck_number, t.driver_name, t.driver_mobile, 
                       t.owner_name, t.owner_mobile,
                       ls.account_id, ls.warehouse_id, ls.builty_id
                FROM loading_slips ls
                LEFT JOIN trucks t ON ls.truck_id = t.truck_id
                WHERE ls.slip_id = ?
            ''', (loading_slip_id,))
            
            if loading_slip:
                # Check if this loading slip already has a builty
                if loading_slip[0][20]:  # builty_id is index 20
                    flash('Error: This loading slip already has a builty created!', 'error')
                    return redirect(url_for('warehouse_create_builty'))
                slip = loading_slip[0]
                # Use truck data from JOIN (if available) or from loading_slip fields
                truck_number = slip[13] if slip[13] else truck_number  # t.truck_number
                truck_driver = slip[14] if slip[14] else slip[9]  # t.driver_name or ls.truck_driver
                mobile_number_1 = slip[15] if slip[15] else slip[11]  # t.driver_mobile or ls.mobile_number_1
                truck_owner = slip[16] if slip[16] else slip[10]  # t.owner_name or ls.truck_owner
                mobile_number_2 = slip[17] if slip[17] else slip[12]  # t.owner_mobile or ls.mobile_number_2
                truck_id = slip[8]  # truck_id from loading_slips
                
                # Override form values with loading slip data
                warehouse_name = warehouse_name  # Keep from form as user already selected
                loading_point = slip[3]  # loading_point_name
                goods_name = slip[7]  # goods_name
                number_of_bags = slip[5]  # quantity_bags
                quantity_wt_mt = slip[6]  # quantity_mt
        else:
            # Get truck details from form
            truck_driver = request.form.get('truck_driver')
            truck_owner = request.form.get('truck_owner')
            mobile_number_1 = request.form.get('mobile_number_1')
            mobile_number_2 = request.form.get('mobile_number_2', '')
            
            truck = db.get_truck_by_number(truck_number)
            if not truck:
                truck_id = db.add_truck(truck_number, truck_driver, mobile_number_1, truck_owner, mobile_number_2)
            else:
                truck_id = truck[0]
        
        # Get warehouse ID for stock OUT
        warehouse = db.execute_custom_query('SELECT warehouse_id FROM warehouses WHERE warehouse_name = ?', (warehouse_name,))
        if not warehouse:
            flash('Invalid warehouse', 'error')
            return redirect(url_for('warehouse_create_builty'))
        warehouse_id = warehouse[0][0]
        
        # Check warehouse balance
        balance = db.get_warehouse_balance_stock(warehouse_id)
        if balance['balance'] < quantity_wt_mt:
            flash(f'Error: Warehouse has only {balance["balance"]:.2f} MT available. Cannot dispatch {quantity_wt_mt:.2f} MT', 'error')
            return redirect(url_for('warehouse_create_builty'))
        
        # Determine destination (account, warehouse, or CGMF)
        accounts = db.get_all_accounts()
        account_id = None
        destination_warehouse_id = None
        cgmf_id = None
        
        # Check if it's a CGMF account
        if account_warehouse and account_warehouse.startswith('CGMF:'):
            cgmf_id = int(account_warehouse.split(':')[1])
        else:
            for account in accounts:
                if account[1] == account_warehouse:
                    account_id = account[0]
                    break
        
        # Get rake code from most recent stock IN
        rake_code_result = db.execute_custom_query('''
            SELECT b.rake_code
            FROM warehouse_stock ws
            JOIN builty b ON ws.builty_id = b.builty_id
            WHERE ws.warehouse_id = ? AND ws.transaction_type = 'IN'
            ORDER BY ws.stock_id DESC
            LIMIT 1
        ''', (warehouse_id,))
        rake_code = rake_code_result[0][0] if rake_code_result else 'WAREHOUSE'
        
        # Calculate freight fields
        try:
            total_freight = float(freight_details.replace('₹', '').replace(',', '').strip())
        except:
            total_freight = 0.0
        kg_per_bag = (quantity_wt_mt * 1000) / number_of_bags if number_of_bags > 0 else 50
        rate_per_mt = total_freight / quantity_wt_mt if quantity_wt_mt > 0 else 0
        
        # Create builty
        builty_id = db.add_builty(builty_number, rake_code, date, warehouse_name, account_id, destination_warehouse_id,
                                  truck_id, loading_point, unloading_point, goods_name, number_of_bags,
                                  quantity_wt_mt, kg_per_bag, rate_per_mt, total_freight, lr_number,
                                  0, 'Warehouse', cgmf_id)
        
        if builty_id:
            # Link loading slip to builty if provided
            if loading_slip_id:
                db.link_loading_slip_to_builty(int(loading_slip_id), builty_id)
            
            # Add stock OUT transaction
            stock_id = db.add_warehouse_stock_out(warehouse_id, builty_id, quantity_wt_mt,
                                                  account_id, date, '')
            
            if stock_id:
                flash(f'Builty {builty_number} created and stock OUT recorded successfully!', 'success')
                return redirect(url_for('warehouse_dashboard'))
            else:
                flash('Builty created but error recording stock OUT', 'warning')
                return redirect(url_for('warehouse_dashboard'))
        else:
            flash('Error creating builty', 'error')
    
    # GET request
    warehouses = db.get_all_warehouses()
    accounts = db.get_all_accounts()
    loading_slips = db.get_all_loading_slips()  # Only unlinked loading slips
    cgmf_list = db.get_all_cgmf()
    
    return render_template('warehouse/create_builty.html',
                         warehouses=warehouses,
                         accounts=accounts,
                         loading_slips=loading_slips,
                         cgmf_list=cgmf_list)

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
        warehouse = db.execute_custom_query('SELECT warehouse_id FROM warehouses WHERE warehouse_name = ?', (warehouse_name,))
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
        rake_code_result = db.execute_custom_query('''
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
    """View balance across all warehouses with filtering support"""
    if current_user.role != 'Warehouse':
        flash('Unauthorized access', 'error')
        return redirect(url_for('index'))
    
    # Get filter parameters
    selected_warehouse = request.args.get('warehouse', 'all')
    date_filter = request.args.get('date_filter', 'all')
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    
    # Get all warehouses for dropdown
    warehouses = db.get_all_warehouses()
    
    # Build date condition
    date_condition = ""
    date_params = []
    
    from datetime import datetime, timedelta
    today = datetime.now().strftime('%Y-%m-%d')
    
    if date_filter == 'today':
        date_condition = " AND DATE(ws.date) = ?"
        date_params = [today]
    elif date_filter == 'week':
        week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        date_condition = " AND DATE(ws.date) >= ?"
        date_params = [week_ago]
    elif date_filter == 'month':
        month_ago = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        date_condition = " AND DATE(ws.date) >= ?"
        date_params = [month_ago]
    elif date_filter == 'custom' and start_date and end_date:
        date_condition = " AND DATE(ws.date) >= ? AND DATE(ws.date) <= ?"
        date_params = [start_date, end_date]
    
    # Get overall stock statistics
    warehouse_balances = []
    account_balances = []
    
    # Build warehouse condition
    if selected_warehouse != 'all':
        try:
            selected_warehouse_id = int(selected_warehouse)
            warehouse_filter = [w for w in warehouses if w[0] == selected_warehouse_id]
            warehouses_to_process = warehouse_filter
        except:
            warehouses_to_process = warehouses
    else:
        warehouses_to_process = warehouses
    
    for warehouse in warehouses_to_process:
        # Get filtered balance
        if date_condition:
            result = db.execute_custom_query(f'''
                SELECT 
                    COALESCE(SUM(CASE WHEN transaction_type = 'IN' THEN quantity_mt ELSE 0 END), 0) as stock_in,
                    COALESCE(SUM(CASE WHEN transaction_type = 'OUT' THEN quantity_mt ELSE 0 END), 0) as stock_out
                FROM warehouse_stock ws
                WHERE warehouse_id = ? {date_condition}
            ''', [warehouse[0]] + date_params)
            if result:
                stock_in = result[0][0] or 0
                stock_out = result[0][1] or 0
            else:
                stock_in, stock_out = 0, 0
        else:
            balance = db.get_warehouse_balance_stock(warehouse[0])
            stock_in = balance.get('stock_in', 0)
            stock_out = balance.get('stock_out', 0)
        
        warehouse_balances.append([
            warehouse[0],  # warehouse_id
            warehouse[1],  # warehouse_name
            warehouse[2],  # location
            stock_in,
            stock_out
        ])
    
    # Calculate totals
    total_stock_in = sum(w[3] for w in warehouse_balances)
    total_stock_out = sum(w[4] for w in warehouse_balances)
    total_balance = total_stock_in - total_stock_out
    
    # Get recent transactions for the filtered scope
    if selected_warehouse != 'all':
        wh_cond = "ws.warehouse_id = ?"
        wh_params = [int(selected_warehouse)]
    else:
        wh_cond = "1=1"
        wh_params = []
    
    recent_transactions = db.execute_custom_query(f'''
        SELECT ws.date, ws.transaction_type, ws.quantity_mt, w.warehouse_name,
               COALESCE(b.builty_number, 'Direct Entry') as builty_number,
               ws.notes
        FROM warehouse_stock ws
        JOIN warehouses w ON ws.warehouse_id = w.warehouse_id
        LEFT JOIN builty b ON ws.builty_id = b.builty_id
        WHERE {wh_cond} {date_condition}
        ORDER BY ws.date DESC, ws.created_at DESC
        LIMIT 20
    ''', wh_params + date_params)
    
    # Get account balances (simplified)
    accounts = db.get_all_accounts()
    for account in accounts:
        account_balances.append([account[1], 0, 0])  # Placeholder
    
    # Get selected warehouse name for display
    selected_warehouse_name = "All Warehouses"
    if selected_warehouse != 'all':
        for wh in warehouses:
            if wh[0] == int(selected_warehouse):
                selected_warehouse_name = wh[1]
                break
    
    return render_template('warehouse/balance.html',
                         warehouse_balances=warehouse_balances,
                         account_balances=account_balances,
                         total_stock_in=total_stock_in,
                         total_stock_out=total_stock_out,
                         total_balance=total_balance,
                         warehouses=warehouses,
                         selected_warehouse=selected_warehouse,
                         selected_warehouse_name=selected_warehouse_name,
                         date_filter=date_filter,
                         start_date=start_date,
                         end_date=end_date,
                         recent_transactions=recent_transactions)

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

@app.route('/warehouse/all-builties')
@login_required
def warehouse_all_builties():
    """View all builties created by warehouse"""
    if current_user.role != 'Warehouse':
        flash('Unauthorized access', 'error')
        return redirect(url_for('index'))
    
    # Get all builties created by warehouse role OR warehouse-specific builties
    # Warehouse builties have builty numbers starting with "WBLT-" or created_by_role='Warehouse'
    builties = db.execute_custom_query('''
        SELECT b.*, a.account_name, w.warehouse_name, t.truck_number
        FROM builty b
        LEFT JOIN accounts a ON b.account_id = a.account_id
        LEFT JOIN warehouses w ON b.warehouse_id = w.warehouse_id
        LEFT JOIN trucks t ON b.truck_id = t.truck_id
        WHERE b.created_by_role = 'Warehouse' OR b.builty_number LIKE 'WBLT-%'
        ORDER BY b.created_at DESC
    ''')
    
    return render_template('warehouse/all_builties.html', builties=builties)

# ========== ACCOUNTANT Dashboard & Routes ==========

@app.route('/accountant/dashboard')
@login_required
def accountant_dashboard():
    if current_user.role != 'Accountant':
        flash('Unauthorized access', 'error')
        return redirect(url_for('index'))
    
    # Get all e-bills and recent ones
    all_ebills = db.get_all_ebills()
    recent_ebills = all_ebills[:10] if all_ebills else []
    
    # Get builties without e-bills
    pending_builties = db.get_builties_without_ebills()
    
    # Calculate statistics
    from datetime import datetime, date
    
    # Total e-bills count
    ebill_count = len(all_ebills) if all_ebills else 0
    
    # E-bills with eway bill PDFs uploaded
    eway_bill_count = sum(1 for ebill in all_ebills if ebill[4]) if all_ebills else 0
    
    # Total builties available
    all_builties = db.get_all_builties()
    builty_count = len(all_builties) if all_builties else 0
    
    # Today's e-bills
    today = date.today().strftime('%Y-%m-%d')
    today_ebill_count = sum(1 for ebill in all_ebills if ebill[3] and ebill[3].startswith(today)) if all_ebills else 0
    
    # Total accounts
    all_accounts = db.get_all_accounts()
    account_count = len(all_accounts) if all_accounts else 0
    
    # Pending uploads (e-bills without PDF)
    pending_uploads = ebill_count - eway_bill_count
    
    # This month's e-bills
    current_month = date.today().strftime('%Y-%m')
    month_ebills = sum(1 for ebill in all_ebills if ebill[3] and ebill[3].startswith(current_month)) if all_ebills else 0
    
    return render_template('accountant/dashboard.html', 
                         ebills=all_ebills,
                         recent_ebills=recent_ebills,
                         pending_builties=pending_builties,
                         ebill_count=ebill_count,
                         eway_bill_count=eway_bill_count,
                         builty_count=builty_count,
                         today_ebill_count=today_ebill_count,
                         account_count=account_count,
                         pending_uploads=pending_uploads,
                         month_ebills=month_ebills)

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
        generated_date = request.form.get('ebill_date')  # Fixed: was 'generated_date'
        
        # Handle file upload for eway bill PDF
        eway_bill_pdf = None
        if 'eway_bill_pdf' in request.files:
            file = request.files['eway_bill_pdf']
            if file and file.filename and file.filename.endswith('.pdf'):
                # Create uploads directory if it doesn't exist
                import os
                upload_folder = os.path.join(os.path.dirname(__file__), 'uploads', 'eway_bills')
                os.makedirs(upload_folder, exist_ok=True)
                
                # Generate unique filename
                from datetime import datetime
                filename = f"{ebill_number}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
                filepath = os.path.join(upload_folder, filename)
                
                # Save the file
                file.save(filepath)
                eway_bill_pdf = filename
        
        ebill_id = db.add_ebill(builty_id, ebill_number, amount, generated_date, eway_bill_pdf)
        
        if ebill_id:
            flash(f'E-Bill {ebill_number} created successfully!', 'success')
            return redirect(url_for('accountant_dashboard'))
        else:
            flash('Error creating e-bill. E-Bill number may already exist or date is missing.', 'error')
    
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

@app.route('/accountant/download-eway-bill/<filename>')
@login_required
def download_eway_bill(filename):
    """Download eway bill PDF"""
    if current_user.role != 'Accountant':
        flash('Unauthorized access', 'error')
        return redirect(url_for('index'))
    
    upload_folder = os.path.join(os.path.dirname(__file__), 'uploads', 'eway_bills')
    filepath = os.path.join(upload_folder, filename)
    
    if os.path.exists(filepath):
        return send_file(filepath, as_attachment=True)
    else:
        flash('File not found', 'error')
        return redirect(url_for('accountant_all_ebills'))


@app.route('/admin/download-database-backup')
@login_required
def download_database():
    """Admin-only endpoint to download database backup"""
    if current_user.role != 'Admin':
        flash('Unauthorized access', 'error')
        return redirect(url_for('index'))
    
    db_path = os.path.join(os.path.dirname(__file__), 'fims.db')
    if os.path.exists(db_path):
        # Create backup filename with timestamp
        from datetime import datetime
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        return send_file(db_path, as_attachment=True, download_name=f'fims_backup_{timestamp}.db')
    else:
        flash('Database file not found', 'error')
        return redirect(url_for('admin_dashboard'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)
