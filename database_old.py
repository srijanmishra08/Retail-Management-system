"""
Database module for FIMS
Handles all database operations with SQLite
"""

import sqlite3
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

class Database:
    def __init__(self, db_name='fims.db'):
        self.db_name = db_name
    
    def get_connection(self):
        """Get database connection"""
        conn = sqlite3.connect(self.db_name)
        conn.row_factory = sqlite3.Row
        return conn
    
    def initialize_database(self):
        """Create all tables and insert default data"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Suppliers table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS suppliers (
                supplier_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                contact TEXT,
                address TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Warehouses table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS warehouses (
                warehouse_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                location TEXT,
                capacity REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Dealers table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS dealers (
                dealer_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                contact TEXT,
                address TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Rakes table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS rakes (
                rake_id INTEGER PRIMARY KEY AUTOINCREMENT,
                rake_number TEXT UNIQUE NOT NULL,
                supplier_id INTEGER,
                date DATE NOT NULL,
                quantity REAL NOT NULL,
                allocation_type TEXT NOT NULL,
                warehouse_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (supplier_id) REFERENCES suppliers(supplier_id),
                FOREIGN KEY (warehouse_id) REFERENCES warehouses(warehouse_id)
            )
        ''')
        
        # Warehouse Stock table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS warehouse_stock (
                stock_id INTEGER PRIMARY KEY AUTOINCREMENT,
                warehouse_id INTEGER NOT NULL,
                rake_id INTEGER NOT NULL,
                quantity_in REAL NOT NULL,
                quantity_out REAL DEFAULT 0,
                current_balance REAL NOT NULL,
                rent_start_date DATE,
                section TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (warehouse_id) REFERENCES warehouses(warehouse_id),
                FOREIGN KEY (rake_id) REFERENCES rakes(rake_id)
            )
        ''')
        
        # Dispatches table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS dispatches (
                dispatch_id INTEGER PRIMARY KEY AUTOINCREMENT,
                warehouse_id INTEGER,
                rake_id INTEGER,
                destination_type TEXT NOT NULL,
                destination_id INTEGER NOT NULL,
                truck_number TEXT NOT NULL,
                quantity REAL NOT NULL,
                dispatch_date DATE NOT NULL,
                transport_company TEXT,
                bill_generated BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (warehouse_id) REFERENCES warehouses(warehouse_id),
                FOREIGN KEY (rake_id) REFERENCES rakes(rake_id)
            )
        ''')
        
        # Billing table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS billing (
                bill_id INTEGER PRIMARY KEY AUTOINCREMENT,
                bill_type TEXT NOT NULL,
                dispatch_id INTEGER,
                rate REAL NOT NULL,
                quantity REAL NOT NULL,
                total_amount REAL NOT NULL,
                generated_on TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (dispatch_id) REFERENCES dispatches(dispatch_id)
            )
        ''')
        
        # Insert default users if not exist
        cursor.execute("SELECT COUNT(*) FROM users")
        if cursor.fetchone()[0] == 0:
            default_users = [
                ('admin', generate_password_hash('admin123'), 'Admin'),
                ('rakepoint', generate_password_hash('rake123'), 'RakePoint'),
                ('warehouse', generate_password_hash('warehouse123'), 'Warehouse'),
                ('accountant', generate_password_hash('account123'), 'Accountant'),
            ]
            cursor.executemany('INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)', default_users)
        
        # Insert default warehouses if not exist
        cursor.execute("SELECT COUNT(*) FROM warehouses")
        if cursor.fetchone()[0] == 0:
            default_warehouses = [
                ('Warehouse 1', 'Location A', 5000),
                ('Warehouse 2', 'Location B', 7000),
                ('Warehouse 3', 'Location C', 6000),
            ]
            cursor.executemany('INSERT INTO warehouses (name, location, capacity) VALUES (?, ?, ?)', default_warehouses)
        
        # Insert default suppliers if not exist
        cursor.execute("SELECT COUNT(*) FROM suppliers")
        if cursor.fetchone()[0] == 0:
            default_suppliers = [
                ('ABC Fertilizers Ltd', '9876543210', 'Mumbai'),
                ('XYZ Chemicals', '9876543211', 'Delhi'),
            ]
            cursor.executemany('INSERT INTO suppliers (name, contact, address) VALUES (?, ?, ?)', default_suppliers)
        
        # Insert default dealers if not exist
        cursor.execute("SELECT COUNT(*) FROM dealers")
        if cursor.fetchone()[0] == 0:
            default_dealers = [
                ('Payal Fertilizers', '9876543220', 'Company Address'),
                ('Government Dept', '9876543221', 'Govt Office'),
            ]
            cursor.executemany('INSERT INTO dealers (name, contact, address) VALUES (?, ?, ?)', default_dealers)
        
        conn.commit()
        conn.close()
        print("Database initialized successfully!")
    
    # ========== User Operations ==========
    
    def authenticate_user(self, username, password):
        """Authenticate user and return user data"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        user = cursor.fetchone()
        conn.close()
        
        if user and check_password_hash(user[2], password):
            return user
        return None
    
    def get_user_by_id(self, user_id):
        """Get user by ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        user = cursor.fetchone()
        conn.close()
        return user
    
    def get_all_users(self):
        """Get all users"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT user_id, username, role, created_at FROM users')
        users = cursor.fetchall()
        conn.close()
        return users
    
    # ========== Rake Operations ==========
    
    def add_rake(self, rake_number, supplier_id, date, quantity, allocation_type, warehouse_id=None):
        """Add new rake"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO rakes (rake_number, supplier_id, date, quantity, allocation_type, warehouse_id)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (rake_number, supplier_id, date, quantity, allocation_type, warehouse_id))
            
            rake_id = cursor.lastrowid
            
            # If allocated to warehouse, add to warehouse stock
            if allocation_type == 'warehouse' and warehouse_id:
                cursor.execute('''
                    INSERT INTO warehouse_stock (warehouse_id, rake_id, quantity_in, current_balance, rent_start_date)
                    VALUES (?, ?, ?, ?, ?)
                ''', (warehouse_id, rake_id, quantity, quantity, date))
            
            conn.commit()
            return rake_id
        except Exception as e:
            print(f"Error adding rake: {e}")
            conn.rollback()
            return None
        finally:
            conn.close()
    
    def get_all_rakes(self):
        """Get all rakes"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT r.*, s.name as supplier_name, w.name as warehouse_name
            FROM rakes r
            LEFT JOIN suppliers s ON r.supplier_id = s.supplier_id
            LEFT JOIN warehouses w ON r.warehouse_id = w.warehouse_id
            ORDER BY r.created_at DESC
        ''')
        rakes = cursor.fetchall()
        conn.close()
        return rakes
    
    def get_recent_rakes(self, limit=5):
        """Get recent rakes"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT r.*, s.name as supplier_name
            FROM rakes r
            LEFT JOIN suppliers s ON r.supplier_id = s.supplier_id
            ORDER BY r.created_at DESC
            LIMIT ?
        ''', (limit,))
        rakes = cursor.fetchall()
        conn.close()
        return rakes
    
    def get_rake_details(self, rake_id):
        """Get rake details"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT r.*, s.name as supplier_name, w.name as warehouse_name
            FROM rakes r
            LEFT JOIN suppliers s ON r.supplier_id = s.supplier_id
            LEFT JOIN warehouses w ON r.warehouse_id = w.warehouse_id
            WHERE r.rake_id = ?
        ''', (rake_id,))
        rake = cursor.fetchone()
        conn.close()
        return rake
    
    def record_rake_unloading(self, rake_id, warehouse_id, actual_quantity, shortage, notes):
        """Record rake unloading details"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                UPDATE warehouse_stock
                SET quantity_in = ?, current_balance = ?, notes = ?
                WHERE rake_id = ? AND warehouse_id = ?
            ''', (actual_quantity, actual_quantity, notes, rake_id, warehouse_id))
            
            conn.commit()
            return True
        except Exception as e:
            print(f"Error recording unloading: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    # ========== Warehouse Operations ==========
    
    def get_all_warehouses(self):
        """Get all warehouses"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM warehouses')
        warehouses = cursor.fetchall()
        conn.close()
        return warehouses
    
    def get_warehouse_by_id(self, warehouse_id):
        """Get warehouse by ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM warehouses WHERE warehouse_id = ?', (warehouse_id,))
        warehouse = cursor.fetchone()
        conn.close()
        return warehouse
    
    def get_warehouse_current_stock(self, warehouse_id):
        """Get total current stock in warehouse"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT COALESCE(SUM(current_balance), 0) as total_stock
            FROM warehouse_stock
            WHERE warehouse_id = ?
        ''', (warehouse_id,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else 0
    
    def get_warehouse_stock_details(self, warehouse_id):
        """Get detailed stock information for warehouse"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT ws.*, r.rake_number, s.name as supplier_name
            FROM warehouse_stock ws
            JOIN rakes r ON ws.rake_id = r.rake_id
            JOIN suppliers s ON r.supplier_id = s.supplier_id
            WHERE ws.warehouse_id = ? AND ws.current_balance > 0
            ORDER BY ws.rent_start_date
        ''', (warehouse_id,))
        stock = cursor.fetchall()
        conn.close()
        return stock
    
    def get_warehouse_stock_by_rake(self, rake_id):
        """Get warehouse stock for specific rake"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT ws.*, w.name as warehouse_name
            FROM warehouse_stock ws
            JOIN warehouses w ON ws.warehouse_id = w.warehouse_id
            WHERE ws.rake_id = ?
        ''', (rake_id,))
        stock = cursor.fetchall()
        conn.close()
        return stock
    
    def update_warehouse_stock_out(self, warehouse_id, quantity):
        """Update warehouse stock after dispatch"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            # Get stock entries with balance, oldest first
            cursor.execute('''
                SELECT stock_id, current_balance
                FROM warehouse_stock
                WHERE warehouse_id = ? AND current_balance > 0
                ORDER BY rent_start_date ASC
            ''', (warehouse_id,))
            
            stocks = cursor.fetchall()
            remaining_qty = quantity
            
            for stock in stocks:
                stock_id, balance = stock[0], stock[1]
                
                if remaining_qty <= 0:
                    break
                
                if balance >= remaining_qty:
                    # This stock can fulfill the remaining quantity
                    new_balance = balance - remaining_qty
                    cursor.execute('''
                        UPDATE warehouse_stock
                        SET quantity_out = quantity_out + ?, current_balance = ?
                        WHERE stock_id = ?
                    ''', (remaining_qty, new_balance, stock_id))
                    remaining_qty = 0
                else:
                    # Take all from this stock and continue
                    cursor.execute('''
                        UPDATE warehouse_stock
                        SET quantity_out = quantity_out + ?, current_balance = 0
                        WHERE stock_id = ?
                    ''', (balance, stock_id))
                    remaining_qty -= balance
            
            conn.commit()
            return True
        except Exception as e:
            print(f"Error updating warehouse stock: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def get_low_stock_alerts(self, threshold=100):
        """Get warehouses with low stock"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT w.warehouse_id, w.name, COALESCE(SUM(ws.current_balance), 0) as total_stock
            FROM warehouses w
            LEFT JOIN warehouse_stock ws ON w.warehouse_id = ws.warehouse_id
            GROUP BY w.warehouse_id, w.name
            HAVING total_stock < ?
        ''', (threshold,))
        alerts = cursor.fetchall()
        conn.close()
        return alerts
    
    # ========== Dispatch Operations ==========
    
    def add_dispatch(self, warehouse_id, destination_type, destination_id, truck_number, 
                     quantity, dispatch_date, transport_company):
        """Add new dispatch"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO dispatches (warehouse_id, destination_type, destination_id, 
                                       truck_number, quantity, dispatch_date, transport_company)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (warehouse_id, destination_type, destination_id, truck_number, 
                  quantity, dispatch_date, transport_company))
            
            dispatch_id = cursor.lastrowid
            conn.commit()
            return dispatch_id
        except Exception as e:
            print(f"Error adding dispatch: {e}")
            conn.rollback()
            return None
        finally:
            conn.close()
    
    def get_all_dispatches(self):
        """Get all dispatches"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT d.*, w.name as warehouse_name
            FROM dispatches d
            LEFT JOIN warehouses w ON d.warehouse_id = w.warehouse_id
            ORDER BY d.created_at DESC
        ''')
        dispatches = cursor.fetchall()
        conn.close()
        return dispatches
    
    def get_dispatch_details(self, dispatch_id):
        """Get dispatch details"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT d.*, w.name as warehouse_name
            FROM dispatches d
            LEFT JOIN warehouses w ON d.warehouse_id = w.warehouse_id
            WHERE d.dispatch_id = ?
        ''', (dispatch_id,))
        dispatch = cursor.fetchone()
        conn.close()
        return dispatch
    
    def get_dispatches_by_rake(self, rake_id):
        """Get dispatches for specific rake"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT d.*, w.name as warehouse_name
            FROM dispatches d
            LEFT JOIN warehouses w ON d.warehouse_id = w.warehouse_id
            WHERE d.rake_id = ?
        ''', (rake_id,))
        dispatches = cursor.fetchall()
        conn.close()
        return dispatches
    
    def get_dispatches_by_dealer(self, dealer_id):
        """Get dispatches for specific dealer"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT d.*, w.name as warehouse_name
            FROM dispatches d
            LEFT JOIN warehouses w ON d.warehouse_id = w.warehouse_id
            WHERE d.destination_type = 'Dealer' AND d.destination_id = ?
        ''', (dealer_id,))
        dispatches = cursor.fetchall()
        conn.close()
        return dispatches
    
    def get_dispatches_without_bills(self):
        """Get dispatches without generated bills"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT d.*, w.name as warehouse_name
            FROM dispatches d
            LEFT JOIN warehouses w ON d.warehouse_id = w.warehouse_id
            WHERE d.bill_generated = 0
            ORDER BY d.dispatch_date
        ''')
        dispatches = cursor.fetchall()
        conn.close()
        return dispatches
    
    def update_dispatch_bill_status(self, dispatch_id, status):
        """Update dispatch bill generation status"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                UPDATE dispatches SET bill_generated = ? WHERE dispatch_id = ?
            ''', (1 if status else 0, dispatch_id))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error updating dispatch bill status: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    # ========== Billing Operations ==========
    
    def add_bill(self, bill_type, dispatch_id, rate, quantity, total_amount):
        """Add new bill"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO billing (bill_type, dispatch_id, rate, quantity, total_amount)
                VALUES (?, ?, ?, ?, ?)
            ''', (bill_type, dispatch_id, rate, quantity, total_amount))
            
            bill_id = cursor.lastrowid
            conn.commit()
            return bill_id
        except Exception as e:
            print(f"Error adding bill: {e}")
            conn.rollback()
            return None
        finally:
            conn.close()
    
    def get_all_bills(self):
        """Get all bills"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT b.*, d.truck_number, d.dispatch_date
            FROM billing b
            LEFT JOIN dispatches d ON b.dispatch_id = d.dispatch_id
            ORDER BY b.generated_on DESC
        ''')
        bills = cursor.fetchall()
        conn.close()
        return bills
    
    def get_bill_details(self, bill_id):
        """Get bill details"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT b.*, d.truck_number, d.dispatch_date, d.destination_type, d.destination_id
            FROM billing b
            LEFT JOIN dispatches d ON b.dispatch_id = d.dispatch_id
            WHERE b.bill_id = ?
        ''', (bill_id,))
        bill = cursor.fetchone()
        conn.close()
        return bill
    
    def get_bill_by_dispatch(self, dispatch_id):
        """Get bill for specific dispatch"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM billing WHERE dispatch_id = ?', (dispatch_id,))
        bill = cursor.fetchone()
        conn.close()
        return bill
    
    def get_billing_summary(self):
        """Get billing summary by type"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT bill_type, COUNT(*) as count, SUM(total_amount) as total
            FROM billing
            GROUP BY bill_type
        ''')
        summary = cursor.fetchall()
        conn.close()
        return summary
    
    # ========== Supplier Operations ==========
    
    def add_supplier(self, name, contact, address):
        """Add new supplier"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO suppliers (name, contact, address)
                VALUES (?, ?, ?)
            ''', (name, contact, address))
            supplier_id = cursor.lastrowid
            conn.commit()
            return supplier_id
        except Exception as e:
            print(f"Error adding supplier: {e}")
            conn.rollback()
            return None
        finally:
            conn.close()
    
    def get_all_suppliers(self):
        """Get all suppliers"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM suppliers')
        suppliers = cursor.fetchall()
        conn.close()
        return suppliers
    
    # ========== Dealer Operations ==========
    
    def add_dealer(self, name, contact, address):
        """Add new dealer"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO dealers (name, contact, address)
                VALUES (?, ?, ?)
            ''', (name, contact, address))
            dealer_id = cursor.lastrowid
            conn.commit()
            return dealer_id
        except Exception as e:
            print(f"Error adding dealer: {e}")
            conn.rollback()
            return None
        finally:
            conn.close()
    
    def get_all_dealers(self):
        """Get all dealers"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM dealers')
        dealers = cursor.fetchall()
        conn.close()
        return dealers
    
    # ========== Dashboard Statistics ==========
    
    def get_dashboard_stats(self):
        """Get dashboard statistics"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Total rakes
        cursor.execute('SELECT COUNT(*) FROM rakes')
        total_rakes = cursor.fetchone()[0]
        
        # Total stock in warehouses
        cursor.execute('SELECT COALESCE(SUM(current_balance), 0) FROM warehouse_stock')
        total_stock = cursor.fetchone()[0]
        
        # Total dispatches
        cursor.execute('SELECT COUNT(*) FROM dispatches')
        total_dispatches = cursor.fetchone()[0]
        
        # Total billing amount
        cursor.execute('SELECT COALESCE(SUM(total_amount), 0) FROM billing')
        total_billing = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'total_rakes': total_rakes,
            'total_stock': total_stock,
            'total_dispatches': total_dispatches,
            'total_billing': total_billing
        }
