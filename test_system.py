#!/usr/bin/env python3
"""
FIMS - Comprehensive System Test Suite
======================================
This script performs extensive testing of the entire Retail Management System:
- Database integrity and consistency checks
- Security vulnerability assessment
- Business logic validation
- Data flow verification
- Edge case handling
- Performance analysis

Run with: python3 test_system.py
"""

import os
import sys
import json
import time
import hashlib
import re
from datetime import datetime, timedelta
from collections import defaultdict

# Set environment variables for Turso
os.environ['TURSO_DATABASE_URL'] = os.environ.get('TURSO_DATABASE_URL', 'libsql://fims-production-srijanmishra08.aws-ap-south-1.turso.io')
os.environ['TURSO_AUTH_TOKEN'] = os.environ.get('TURSO_AUTH_TOKEN', 'eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9.eyJhIjoicnciLCJpYXQiOjE3NjYxMzMyMzIsImlkIjoiZjY5YWYwYzEtNGNkNi00YzBhLWI3YWUtYTY0NGJkMTBlOWViIiwicmlkIjoiMDhjYmI3YWYtMDc2My00YjdhLWE3MGMtZmQwYmE5OWU0NDZiIn0.qbioLnGW7hRmKfQQ4Y8Y_47YixHQMv-KrZuF5quIHmQok1P22oGlE5XXb-KR4SNMrWL_hqflMi2XNam0tHE8CQ')

import database

# ============================================================================
# ANSI Color Codes for Pretty Output
# ============================================================================
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_header(text):
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*70}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text.center(70)}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*70}{Colors.ENDC}\n")

def print_section(text):
    print(f"\n{Colors.CYAN}{Colors.BOLD}--- {text} ---{Colors.ENDC}")

def print_pass(text):
    print(f"  {Colors.GREEN}✓ PASS:{Colors.ENDC} {text}")

def print_fail(text):
    print(f"  {Colors.FAIL}✗ FAIL:{Colors.ENDC} {text}")

def print_warn(text):
    print(f"  {Colors.WARNING}⚠ WARN:{Colors.ENDC} {text}")

def print_info(text):
    print(f"  {Colors.BLUE}ℹ INFO:{Colors.ENDC} {text}")

# ============================================================================
# Test Results Collector
# ============================================================================
class TestResults:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.warnings = 0
        self.security_issues = []
        self.logic_issues = []
        self.db_issues = []
        self.recommendations = []
        
    def add_pass(self, category, message):
        self.passed += 1
        print_pass(message)
        
    def add_fail(self, category, message, details=None):
        self.failed += 1
        print_fail(message)
        if details:
            print(f"       Details: {details}")
        if category == 'security':
            self.security_issues.append(message)
        elif category == 'logic':
            self.logic_issues.append(message)
        elif category == 'database':
            self.db_issues.append(message)
            
    def add_warning(self, category, message):
        self.warnings += 1
        print_warn(message)
        
    def add_recommendation(self, message):
        self.recommendations.append(message)

results = TestResults()

# ============================================================================
# DATABASE TESTS
# ============================================================================
def test_database_connection():
    """Test database connection and basic operations"""
    print_section("DATABASE CONNECTION TESTS")
    
    try:
        db = database.Database()
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        if result and result[0] == 1:
            results.add_pass('database', "Database connection successful")
        else:
            results.add_fail('database', "Database connection returned unexpected result")
        db.close_connection(conn)
    except Exception as e:
        results.add_fail('database', f"Database connection failed: {str(e)}")

def test_database_schema():
    """Verify all required tables exist with correct structure"""
    print_section("DATABASE SCHEMA VERIFICATION")
    
    required_tables = [
        'users', 'rakes', 'rake_products', 'loading_slips',
        'builty', 'warehouses', 'warehouse_stock', 'accounts', 'companies',
        'cgmf', 'ebills', 'rake_bill_payments'
    ]
    
    db = database.Database()
    conn = db.get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    existing_tables = [row[0] for row in cursor.fetchall()]
    
    for table in required_tables:
        if table in existing_tables:
            results.add_pass('database', f"Table '{table}' exists")
        else:
            results.add_fail('database', f"Required table '{table}' is MISSING")
    
    db.close_connection(conn)

def test_database_integrity():
    """Check for orphaned records and referential integrity"""
    print_section("DATABASE REFERENTIAL INTEGRITY")
    
    db = database.Database()
    conn = db.get_connection()
    cursor = conn.cursor()
    
    # Test 1: Builties with invalid rake_code
    cursor.execute("""
        SELECT COUNT(*) FROM builty b 
        WHERE b.rake_code IS NOT NULL 
        AND b.rake_code NOT IN (SELECT rake_code FROM rakes)
    """)
    orphan_builties = cursor.fetchone()[0]
    if orphan_builties == 0:
        results.add_pass('database', "All builties have valid rake references")
    else:
        results.add_fail('database', f"Found {orphan_builties} builties with invalid rake_code")
    
    # Test 2: Loading slips without valid rake reference
    cursor.execute("""
        SELECT COUNT(*) FROM loading_slips ls
        WHERE ls.rake_code IS NOT NULL 
        AND ls.rake_code NOT IN (SELECT rake_code FROM rakes)
    """)
    orphan_slips = cursor.fetchone()[0]
    if orphan_slips == 0:
        results.add_pass('database', "All loading slips have valid rake references")
    else:
        results.add_fail('database', f"Found {orphan_slips} loading slips with invalid rake_code")
    
    # Test 3: Warehouse stock with invalid warehouse_id
    cursor.execute("""
        SELECT COUNT(*) FROM warehouse_stock ws
        WHERE ws.warehouse_id IS NOT NULL 
        AND ws.warehouse_id NOT IN (SELECT warehouse_id FROM warehouses)
    """)
    orphan_stock = cursor.fetchone()[0]
    if orphan_stock == 0:
        results.add_pass('database', "All warehouse stock entries have valid warehouse references")
    else:
        results.add_fail('database', f"Found {orphan_stock} warehouse stock entries with invalid warehouse_id")
    
    # Test 4: Check for duplicate builty numbers
    cursor.execute("""
        SELECT builty_number, COUNT(*) as cnt FROM builty 
        GROUP BY builty_number HAVING cnt > 1
    """)
    duplicate_builties = cursor.fetchall()
    if len(duplicate_builties) == 0:
        results.add_pass('database', "No duplicate builty numbers found")
    else:
        results.add_fail('database', f"Found {len(duplicate_builties)} duplicate builty numbers")
        for dup in duplicate_builties[:5]:
            print_info(f"Duplicate: {dup[0]} (count: {dup[1]})")
    
    # Test 5: Check for duplicate loading slip numbers
    cursor.execute("""
        SELECT slip_number, COUNT(*) as cnt FROM loading_slips 
        GROUP BY slip_number HAVING cnt > 1
    """)
    duplicate_slips = cursor.fetchall()
    if len(duplicate_slips) == 0:
        results.add_pass('database', "No duplicate loading slip numbers found")
    else:
        results.add_fail('database', f"Found {len(duplicate_slips)} duplicate loading slip numbers")
        for dup in duplicate_slips[:5]:
            print_info(f"Duplicate: {dup[0]} (count: {dup[1]})")
    
    db.close_connection(conn)

def test_data_consistency():
    """Check for data consistency issues"""
    print_section("DATA CONSISTENCY CHECKS")
    
    db = database.Database()
    conn = db.get_connection()
    cursor = conn.cursor()
    
    # Test 1: Builties with both account_id AND warehouse_id (should be mutually exclusive)
    cursor.execute("""
        SELECT COUNT(*) FROM builty 
        WHERE account_id IS NOT NULL AND warehouse_id IS NOT NULL
    """)
    both_ids = cursor.fetchone()[0]
    if both_ids == 0:
        results.add_pass('database', "Builties have proper account/warehouse exclusivity")
    else:
        results.add_warning('database', f"{both_ids} builties have BOTH account_id AND warehouse_id set")
    
    # Test 2: Builties with neither account_id nor warehouse_id
    cursor.execute("""
        SELECT COUNT(*) FROM builty 
        WHERE account_id IS NULL AND warehouse_id IS NULL AND cgmf_id IS NULL
    """)
    no_destination = cursor.fetchone()[0]
    if no_destination == 0:
        results.add_pass('database', "All builties have a destination (account/warehouse/cgmf)")
    else:
        results.add_fail('database', f"{no_destination} builties have NO destination set")
    
    # Test 3: Negative quantities
    cursor.execute("""
        SELECT COUNT(*) FROM builty WHERE quantity_mt < 0
    """)
    neg_qty = cursor.fetchone()[0]
    if neg_qty == 0:
        results.add_pass('database', "No negative quantities in builties")
    else:
        results.add_fail('logic', f"Found {neg_qty} builties with negative quantities")
    
    cursor.execute("""
        SELECT COUNT(*) FROM warehouse_stock WHERE quantity_mt < 0
    """)
    neg_stock = cursor.fetchone()[0]
    if neg_stock == 0:
        results.add_pass('database', "No negative quantities in warehouse stock")
    else:
        results.add_fail('logic', f"Found {neg_stock} warehouse stock entries with negative quantities")
    
    # Test 4: Future dates (suspicious data)
    future_date = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
    cursor.execute(f"SELECT COUNT(*) FROM rakes WHERE date > '{future_date}'")
    future_rakes = cursor.fetchone()[0]
    if future_rakes == 0:
        results.add_pass('database', "No rakes with future dates")
    else:
        results.add_warning('database', f"{future_rakes} rakes have future dates")
    
    # Test 5: Check warehouse stock balance consistency
    cursor.execute("""
        SELECT w.warehouse_id, w.warehouse_name,
            COALESCE(SUM(CASE WHEN ws.transaction_type = 'IN' THEN ws.quantity_mt ELSE 0 END), 0) as total_in,
            COALESCE(SUM(CASE WHEN ws.transaction_type = 'OUT' THEN ws.quantity_mt ELSE 0 END), 0) as total_out
        FROM warehouses w
        LEFT JOIN warehouse_stock ws ON w.warehouse_id = ws.warehouse_id
        GROUP BY w.warehouse_id, w.warehouse_name
    """)
    warehouses = cursor.fetchall()
    negative_balance = False
    for wh in warehouses:
        balance = wh[2] - wh[3]
        if balance < -0.01:  # Small tolerance for floating point
            results.add_fail('logic', f"Warehouse '{wh[1]}' has negative balance: {balance:.2f} MT")
            negative_balance = True
    if not negative_balance:
        results.add_pass('logic', "All warehouses have non-negative stock balance")
    
    db.close_connection(conn)

def test_name_collisions():
    """Check for name collisions between accounts and warehouses"""
    print_section("NAME COLLISION DETECTION")
    
    db = database.Database()
    conn = db.get_connection()
    cursor = conn.cursor()
    
    # Get all warehouse names
    cursor.execute("SELECT warehouse_id, warehouse_name FROM warehouses")
    warehouses = {row[1].upper().strip(): row[0] for row in cursor.fetchall() if row[1]}
    
    # Get all account names
    cursor.execute("SELECT account_id, account_name FROM accounts")
    accounts = {row[1].upper().strip(): row[0] for row in cursor.fetchall() if row[1]}
    
    # Find collisions
    collisions = set(warehouses.keys()) & set(accounts.keys())
    
    if len(collisions) == 0:
        results.add_pass('logic', "No name collisions between accounts and warehouses")
    else:
        results.add_fail('logic', f"Found {len(collisions)} name collision(s) between accounts and warehouses")
        for name in collisions:
            print_info(f"'{name}' exists as both Account (ID={accounts[name]}) and Warehouse (ID={warehouses[name]})")
        results.add_recommendation("Consider renaming accounts to avoid confusion with warehouses")
    
    db.close_connection(conn)

# ============================================================================
# SECURITY TESTS
# ============================================================================
def test_password_security():
    """Check password storage security"""
    print_section("PASSWORD SECURITY AUDIT")
    
    db = database.Database()
    conn = db.get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT username, password_hash FROM users LIMIT 10")
    users = cursor.fetchall()
    
    plaintext_count = 0
    weak_hash_count = 0
    
    for user in users:
        username, password = user
        if password:
            # Check if password looks like plaintext (no hash format)
            if len(password) < 20 and not password.startswith('$'):
                plaintext_count += 1
                print_info(f"User '{username}' may have plaintext password")
            # Check for weak MD5 hash (32 hex chars)
            elif len(password) == 32 and all(c in '0123456789abcdef' for c in password.lower()):
                weak_hash_count += 1
    
    if plaintext_count == 0:
        results.add_pass('security', "No obvious plaintext passwords detected")
    else:
        results.add_fail('security', f"Found {plaintext_count} potential plaintext passwords")
        results.add_recommendation("Use bcrypt or argon2 for password hashing")
    
    if weak_hash_count > 0:
        results.add_warning('security', f"Found {weak_hash_count} passwords using weak MD5 hash")
        results.add_recommendation("Migrate from MD5 to bcrypt for password storage")
    
    db.close_connection(conn)

def test_sql_injection_patterns():
    """Scan code for potential SQL injection vulnerabilities"""
    print_section("SQL INJECTION VULNERABILITY SCAN")
    
    vulnerable_patterns = [
        (r'execute\s*\(\s*f["\']', 'F-string in SQL query'),
        (r'execute\s*\(\s*["\'].*\+', 'String concatenation in SQL'),
    ]
    
    files_to_check = ['app.py', 'database.py', 'reports.py']
    vulnerabilities_found = 0
    
    for filename in files_to_check:
        filepath = os.path.join(os.path.dirname(__file__), filename)
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                content = f.read()
                lines = content.split('\n')
                
            for line_no, line in enumerate(lines, 1):
                for pattern, desc in vulnerable_patterns:
                    if re.search(pattern, line, re.IGNORECASE):
                        # Check if it's actually a parameterized query
                        if '?' in line or 'params' in line.lower():
                            continue
                        # Skip comments
                        if line.strip().startswith('#'):
                            continue
                        # Skip if it's just building where_clause
                        if 'where_clause' in line or 'conditions' in line:
                            continue
                        vulnerabilities_found += 1
                        print_warn(f"{filename}:{line_no} - Potential {desc}")
    
    if vulnerabilities_found == 0:
        results.add_pass('security', "No obvious SQL injection patterns detected")
    else:
        results.add_warning('security', f"Found {vulnerabilities_found} potential SQL injection points (review needed)")
        results.add_recommendation("Review flagged lines and use parameterized queries")

def test_authentication_checks():
    """Verify routes have proper authentication"""
    print_section("AUTHENTICATION AUDIT")
    
    filepath = os.path.join(os.path.dirname(__file__), 'app.py')
    
    if not os.path.exists(filepath):
        results.add_fail('security', "Cannot find app.py for authentication audit")
        return
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Find all routes
    route_pattern = r'@app\.route\([\'"]([^\'"]+)[\'"]'
    
    # Check for @login_required decorator
    unprotected_routes = []
    admin_routes_without_check = []
    
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if '@app.route' in line:
            route_match = re.search(route_pattern, line)
            if route_match:
                route = route_match.group(1)
                # Skip public routes
                if route in ['/', '/login', '/logout', '/static/<path:filename>']:
                    continue
                
                # Look for @login_required in nearby lines (within 5 lines)
                has_login_required = False
                has_role_check = False
                for j in range(max(0, i-2), min(len(lines), i+10)):
                    if '@login_required' in lines[j]:
                        has_login_required = True
                    if "current_user.role" in lines[j] or "role !=" in lines[j]:
                        has_role_check = True
                
                if not has_login_required:
                    unprotected_routes.append(route)
                
                if '/admin/' in route and not has_role_check:
                    # Check function body for role check
                    for j in range(i, min(len(lines), i+30)):
                        if "current_user.role" in lines[j]:
                            has_role_check = True
                            break
                    if not has_role_check:
                        admin_routes_without_check.append(route)
    
    if len(unprotected_routes) == 0:
        results.add_pass('security', "All routes have @login_required decorator")
    else:
        results.add_warning('security', f"Found {len(unprotected_routes)} routes without @login_required")
        for route in unprotected_routes[:5]:
            print_info(f"Unprotected: {route}")
    
    if len(admin_routes_without_check) == 0:
        results.add_pass('security', "All admin routes have role verification")
    else:
        results.add_warning('security', f"Found {len(admin_routes_without_check)} admin routes without explicit role check")

def test_csrf_protection():
    """Check for CSRF protection"""
    print_section("CSRF PROTECTION AUDIT")
    
    filepath = os.path.join(os.path.dirname(__file__), 'app.py')
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Check if Flask-WTF or CSRFProtect is used
    has_csrf = 'CSRFProtect' in content or 'csrf' in content.lower()
    
    if has_csrf:
        results.add_pass('security', "CSRF protection appears to be implemented")
    else:
        results.add_fail('security', "No CSRF protection detected")
        results.add_recommendation("Add Flask-WTF CSRFProtect to prevent cross-site request forgery")

def test_sensitive_data_exposure():
    """Check for sensitive data exposure in code"""
    print_section("SENSITIVE DATA EXPOSURE CHECK")
    
    sensitive_patterns = [
        (r'password\s*=\s*["\'][^"\']+["\']', 'Hardcoded password'),
        (r'secret\s*=\s*["\'][^"\']+["\']', 'Hardcoded secret'),
        (r'api_key\s*=\s*["\'][^"\']+["\']', 'Hardcoded API key'),
    ]
    
    files_to_check = ['app.py', 'database.py']
    issues_found = 0
    
    for filename in files_to_check:
        filepath = os.path.join(os.path.dirname(__file__), filename)
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                lines = f.readlines()
            
            for line_no, line in enumerate(lines, 1):
                if line.strip().startswith('#'):
                    continue
                for pattern, desc in sensitive_patterns:
                    if re.search(pattern, line, re.IGNORECASE):
                        # Skip environment variable assignments
                        if 'environ' in line or 'getenv' in line or 'os.get' in line:
                            continue
                        # Skip if it's a variable name check
                        if '==' in line or '!=' in line:
                            continue
                        issues_found += 1
                        print_warn(f"{filename}:{line_no} - {desc}")
    
    if issues_found == 0:
        results.add_pass('security', "No hardcoded sensitive data detected")
    else:
        results.add_fail('security', f"Found {issues_found} potential hardcoded credentials")
        results.add_recommendation("Move sensitive data to environment variables")

# ============================================================================
# BUSINESS LOGIC TESTS
# ============================================================================
def test_stock_flow_logic():
    """Verify stock flow logic: Rake -> Loading Slip -> Builty -> Warehouse"""
    print_section("STOCK FLOW LOGIC VERIFICATION")
    
    db = database.Database()
    conn = db.get_connection()
    cursor = conn.cursor()
    
    # Test 1: Check for loading slips without builty (incomplete flow)
    cursor.execute("""
        SELECT COUNT(*) FROM loading_slips ls
        WHERE ls.builty_id IS NULL AND ls.created_at < datetime('now', '-1 day')
    """)
    incomplete_slips = cursor.fetchone()[0]
    
    if incomplete_slips == 0:
        results.add_pass('logic', "All loading slips (older than 1 day) have corresponding builties")
    else:
        results.add_warning('logic', f"Found {incomplete_slips} loading slips without builties")
    
    # Test 2: Warehouse IN should have corresponding builty
    cursor.execute("""
        SELECT COUNT(*) FROM warehouse_stock ws
        WHERE ws.transaction_type = 'IN' 
        AND ws.builty_id IS NOT NULL
        AND ws.builty_id NOT IN (SELECT builty_id FROM builty)
    """)
    orphan_stock_in = cursor.fetchone()[0]
    
    if orphan_stock_in == 0:
        results.add_pass('logic', "All warehouse stock-in entries have valid builty references")
    else:
        results.add_fail('logic', f"Found {orphan_stock_in} warehouse stock-in entries with invalid builty_id")
    
    # Test 3: Check total rake quantities
    cursor.execute("""
        SELECT r.rake_code, r.rr_quantity,
            COALESCE((SELECT SUM(quantity_mt) FROM builty WHERE rake_code = r.rake_code), 0) as total_builty
        FROM rakes r
        WHERE r.rr_quantity > 0
    """)
    rakes = cursor.fetchall()
    over_utilized = 0
    for rake in rakes:
        if rake[2] > rake[1] * 1.05:  # 5% tolerance
            over_utilized += 1
            print_info(f"Rake {rake[0]}: RR={rake[1]} MT, Builty Total={rake[2]:.2f} MT")
    
    if over_utilized == 0:
        results.add_pass('logic', "No rakes have over-utilized quantities")
    else:
        results.add_warning('logic', f"Found {over_utilized} rakes with over-utilized quantities")
    
    db.close_connection(conn)

def test_multi_product_rake_logic():
    """Test multi-product rake handling"""
    print_section("MULTI-PRODUCT RAKE LOGIC")
    
    db = database.Database()
    conn = db.get_connection()
    cursor = conn.cursor()
    
    # Find rakes with multiple products
    cursor.execute("""
        SELECT rake_code, COUNT(DISTINCT product_name) as product_count
        FROM rake_products
        GROUP BY rake_code
        HAVING product_count > 1
    """)
    multi_product_rakes = cursor.fetchall()
    
    print_info(f"Found {len(multi_product_rakes)} multi-product rakes")
    
    issues_found = 0
    for rake_code, product_count in multi_product_rakes:
        # Check if products have proper allocations
        cursor.execute("""
            SELECT rp.product_name, rp.quantity_mt,
                COALESCE((SELECT SUM(quantity_mt) FROM builty 
                          WHERE rake_code = rp.rake_code AND goods_name = rp.product_name), 0) as total_builty_qty
            FROM rake_products rp
            WHERE rp.rake_code = ?
        """, (rake_code,))
        
        products = cursor.fetchall()
        for prod in products:
            product_name, allocated, used = prod
            if allocated and used > allocated * 1.05:
                issues_found += 1
                print_info(f"Rake {rake_code}: {product_name} over-utilized ({used:.2f}/{allocated:.2f} MT)")
    
    if issues_found == 0:
        results.add_pass('logic', "Multi-product rake allocations are within limits")
    else:
        results.add_warning('logic', f"Found {issues_found} over-allocated products in multi-product rakes")
    
    db.close_connection(conn)

def test_ebill_logic():
    """Test e-bill creation and consistency"""
    print_section("E-BILL LOGIC VERIFICATION")
    
    db = database.Database()
    conn = db.get_connection()
    cursor = conn.cursor()
    
    # Check for ebills with invalid references
    cursor.execute("""
        SELECT COUNT(*) FROM ebills e
        WHERE e.builty_id IS NOT NULL
        AND e.builty_id NOT IN (SELECT builty_id FROM builty)
    """)
    invalid_ebills = cursor.fetchone()[0]
    
    if invalid_ebills == 0:
        results.add_pass('logic', "All e-bills have valid builty references")
    else:
        results.add_fail('logic', f"Found {invalid_ebills} e-bills with invalid builty_id")
    
    # Check for duplicate ebills for same builty
    cursor.execute("""
        SELECT builty_id, COUNT(*) as cnt FROM ebills
        WHERE builty_id IS NOT NULL
        GROUP BY builty_id HAVING cnt > 1
    """)
    duplicate_ebills = cursor.fetchall()
    
    if len(duplicate_ebills) == 0:
        results.add_pass('logic', "No duplicate e-bills for single builty")
    else:
        results.add_warning('logic', f"Found {len(duplicate_ebills)} builties with multiple e-bills")
    
    db.close_connection(conn)

def test_payment_tracking():
    """Test payment tracking consistency"""
    print_section("PAYMENT TRACKING VERIFICATION")
    
    db = database.Database()
    conn = db.get_connection()
    cursor = conn.cursor()
    
    # Check for negative payments
    cursor.execute("""
        SELECT COUNT(*) FROM rake_bill_payments
        WHERE received_amount < 0 OR total_bill_amount < 0
    """)
    negative_payments = cursor.fetchone()[0]
    
    if negative_payments == 0:
        results.add_pass('logic', "No negative payment amounts found")
    else:
        results.add_fail('logic', f"Found {negative_payments} records with negative payment amounts")
    
    # Check for received > total
    cursor.execute("""
        SELECT rake_code, total_bill_amount, received_amount 
        FROM rake_bill_payments
        WHERE received_amount > total_bill_amount AND total_bill_amount > 0
    """)
    overpaid = cursor.fetchall()
    
    if len(overpaid) == 0:
        results.add_pass('logic', "No over-payments detected")
    else:
        results.add_warning('logic', f"Found {len(overpaid)} rakes where received > total bill")
        for rake in overpaid[:3]:
            print_info(f"Rake {rake[0]}: Bill={rake[1]}, Received={rake[2]}")
    
    db.close_connection(conn)

# ============================================================================
# PERFORMANCE TESTS
# ============================================================================
def test_query_performance():
    """Test performance of common queries"""
    print_section("QUERY PERFORMANCE TESTS")
    
    db = database.Database()
    
    queries = [
        ("Get all rakes", "SELECT * FROM rakes ORDER BY date DESC LIMIT 100"),
        ("Get all warehouses", "SELECT * FROM warehouses"),
        ("Get pending builties for warehouse", """
            SELECT b.* FROM builty b
            LEFT JOIN warehouse_stock ws ON b.builty_id = ws.builty_id
            WHERE ws.stock_id IS NULL AND b.warehouse_id IS NOT NULL
            LIMIT 100
        """),
        ("Bill summary query", """
            SELECT r.rake_code, r.company_name, r.rr_quantity, r.date,
                COALESCE(rbp.total_bill_amount, 0) as bill_amount
            FROM rakes r
            LEFT JOIN rake_bill_payments rbp ON r.rake_code = rbp.rake_code
            ORDER BY r.date DESC LIMIT 50
        """),
    ]
    
    for name, query in queries:
        conn = db.get_connection()
        cursor = conn.cursor()
        start = time.time()
        cursor.execute(query)
        cursor.fetchall()
        elapsed = (time.time() - start) * 1000
        db.close_connection(conn)
        
        if elapsed < 100:
            results.add_pass('performance', f"{name}: {elapsed:.1f}ms")
        elif elapsed < 500:
            results.add_warning('performance', f"{name}: {elapsed:.1f}ms (slow)")
        else:
            results.add_fail('performance', f"{name}: {elapsed:.1f}ms (very slow)")

def test_index_usage():
    """Check if important indexes exist"""
    print_section("DATABASE INDEX CHECK")
    
    db = database.Database()
    conn = db.get_connection()
    cursor = conn.cursor()
    
    # Get existing indexes
    cursor.execute("SELECT name, tbl_name FROM sqlite_master WHERE type='index'")
    indexes = cursor.fetchall()
    index_info = [(idx[0], idx[1]) for idx in indexes]
    
    print_info(f"Found {len(indexes)} indexes in database")
    
    # Recommended indexes
    recommended_indexes = [
        ('builty', 'rake_code'),
        ('builty', 'warehouse_id'),
        ('builty', 'account_id'),
        ('loading_slips', 'rake_code'),
        ('warehouse_stock', 'warehouse_id'),
        ('warehouse_stock', 'builty_id'),
    ]
    
    missing_indexes = []
    for table, column in recommended_indexes:
        found = False
        for idx_name, idx_table in index_info:
            if idx_table == table and column in idx_name.lower():
                found = True
                break
        if not found:
            missing_indexes.append((table, column))
    
    if len(missing_indexes) == 0:
        results.add_pass('performance', "All recommended indexes exist")
    else:
        results.add_warning('performance', f"Missing {len(missing_indexes)} recommended indexes")
        for table, column in missing_indexes[:5]:
            print_info(f"Consider: CREATE INDEX idx_{table}_{column} ON {table}({column})")
    
    db.close_connection(conn)

# ============================================================================
# DATA STATISTICS
# ============================================================================
def show_data_statistics():
    """Display database statistics"""
    print_section("DATABASE STATISTICS")
    
    db = database.Database()
    conn = db.get_connection()
    cursor = conn.cursor()
    
    stats = [
        ("Users", "SELECT COUNT(*) FROM users"),
        ("Rakes", "SELECT COUNT(*) FROM rakes"),
        ("Loading Slips", "SELECT COUNT(*) FROM loading_slips"),
        ("Builties", "SELECT COUNT(*) FROM builty"),
        ("Warehouses", "SELECT COUNT(*) FROM warehouses"),
        ("Warehouse Stock Entries", "SELECT COUNT(*) FROM warehouse_stock"),
        ("Accounts/Dealers", "SELECT COUNT(*) FROM accounts"),
        ("Companies", "SELECT COUNT(*) FROM companies"),
        ("E-Bills", "SELECT COUNT(*) FROM ebills"),
        ("Rake Products", "SELECT COUNT(*) FROM rake_products"),
    ]
    
    print(f"\n  {'Entity':<25} {'Count':>10}")
    print(f"  {'-'*35}")
    
    for name, query in stats:
        try:
            cursor.execute(query)
            count = cursor.fetchone()[0]
            print(f"  {name:<25} {count:>10,}")
        except Exception as e:
            print(f"  {name:<25} {'ERROR':>10}")
    
    db.close_connection(conn)

# ============================================================================
# MAIN TEST RUNNER
# ============================================================================
def run_all_tests():
    """Run all tests and generate report"""
    print_header("FIMS COMPREHENSIVE SYSTEM TEST")
    print(f"  Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  System: Retail Management System (FIMS)")
    
    # Run all test categories
    test_database_connection()
    test_database_schema()
    test_database_integrity()
    test_data_consistency()
    test_name_collisions()
    
    test_password_security()
    test_sql_injection_patterns()
    test_authentication_checks()
    test_csrf_protection()
    test_sensitive_data_exposure()
    
    test_stock_flow_logic()
    test_multi_product_rake_logic()
    test_ebill_logic()
    test_payment_tracking()
    
    test_query_performance()
    test_index_usage()
    
    show_data_statistics()
    
    # Print summary
    print_header("TEST SUMMARY")
    
    total = results.passed + results.failed + results.warnings
    print(f"  {Colors.GREEN}Passed:   {results.passed}{Colors.ENDC}")
    print(f"  {Colors.FAIL}Failed:   {results.failed}{Colors.ENDC}")
    print(f"  {Colors.WARNING}Warnings: {results.warnings}{Colors.ENDC}")
    print(f"  Total:    {total}")
    
    if results.security_issues:
        print(f"\n  {Colors.FAIL}{Colors.BOLD}SECURITY ISSUES:{Colors.ENDC}")
        for issue in results.security_issues:
            print(f"    • {issue}")
    
    if results.logic_issues:
        print(f"\n  {Colors.WARNING}{Colors.BOLD}LOGIC ISSUES:{Colors.ENDC}")
        for issue in results.logic_issues:
            print(f"    • {issue}")
    
    if results.db_issues:
        print(f"\n  {Colors.FAIL}{Colors.BOLD}DATABASE ISSUES:{Colors.ENDC}")
        for issue in results.db_issues:
            print(f"    • {issue}")
    
    if results.recommendations:
        print(f"\n  {Colors.CYAN}{Colors.BOLD}RECOMMENDATIONS:{Colors.ENDC}")
        for rec in results.recommendations:
            print(f"    → {rec}")
    
    print_header("TEST COMPLETE")
    
    # Return exit code based on failures
    return 0 if results.failed == 0 else 1

if __name__ == '__main__':
    sys.exit(run_all_tests())
