"""
Database module for FIMS - Redesigned for specific workflows
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
    
    def execute_custom_query(self, query, params=None):
        """Execute a custom SQL query and return results"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            # Check if it's a SELECT query
            if query.strip().upper().startswith('SELECT'):
                results = cursor.fetchall()
                # Convert Row objects to tuples for easier access
                return [tuple(row) for row in results]
            else:
                # For INSERT/UPDATE/DELETE, commit and return affected rows
                conn.commit()
                return cursor.rowcount
        except Exception as e:
            print(f"Error executing query: {e}")
            conn.rollback()
            return None
        finally:
            conn.close()
    
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
        
        # Rakes table (Admin adds rakes)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS rakes (
                rake_id INTEGER PRIMARY KEY AUTOINCREMENT,
                rake_code TEXT UNIQUE NOT NULL,
                company_name TEXT NOT NULL,
                company_code TEXT,
                date DATE NOT NULL,
                rr_quantity REAL NOT NULL,
                product_name TEXT NOT NULL,
                product_code TEXT,
                rake_point_name TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Accounts table (Dealers, Retailers, Companies)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS accounts (
                account_id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_name TEXT NOT NULL,
                account_type TEXT NOT NULL,
                contact TEXT,
                address TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Products table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                product_id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_name TEXT UNIQUE NOT NULL,
                product_code TEXT,
                product_type TEXT DEFAULT 'Fertilizer',
                unit TEXT DEFAULT 'MT',
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Warehouses table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS warehouses (
                warehouse_id INTEGER PRIMARY KEY AUTOINCREMENT,
                warehouse_name TEXT NOT NULL,
                location TEXT,
                capacity REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Trucks table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trucks (
                truck_id INTEGER PRIMARY KEY AUTOINCREMENT,
                truck_number TEXT UNIQUE NOT NULL,
                driver_name TEXT,
                driver_mobile TEXT,
                owner_name TEXT,
                owner_mobile TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Builty table (Created by Rake Point or Warehouse)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS builty (
                builty_id INTEGER PRIMARY KEY AUTOINCREMENT,
                builty_number TEXT UNIQUE NOT NULL,
                rake_code TEXT,
                date DATE NOT NULL,
                rake_point_name TEXT,
                account_id INTEGER,
                warehouse_id INTEGER,
                truck_id INTEGER NOT NULL,
                loading_point TEXT NOT NULL,
                unloading_point TEXT NOT NULL,
                goods_name TEXT NOT NULL,
                number_of_bags INTEGER NOT NULL,
                quantity_mt REAL NOT NULL,
                kg_per_bag REAL,
                rate_per_mt REAL,
                total_freight REAL,
                lr_number TEXT,
                lr_index INTEGER,
                created_by_role TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (account_id) REFERENCES accounts(account_id),
                FOREIGN KEY (warehouse_id) REFERENCES warehouses(warehouse_id),
                FOREIGN KEY (truck_id) REFERENCES trucks(truck_id),
                FOREIGN KEY (rake_code) REFERENCES rakes(rake_code)
            )
        ''')
        
        # Loading Slip table (Rake Point)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS loading_slips (
                slip_id INTEGER PRIMARY KEY AUTOINCREMENT,
                rake_code TEXT NOT NULL,
                slip_number INTEGER NOT NULL,
                loading_point_name TEXT NOT NULL,
                destination TEXT NOT NULL,
                account_id INTEGER,
                warehouse_id INTEGER,
                quantity_bags INTEGER NOT NULL,
                quantity_mt REAL NOT NULL,
                truck_id INTEGER NOT NULL,
                wagon_number TEXT,
                goods_name TEXT,
                truck_driver TEXT,
                truck_owner TEXT,
                mobile_number_1 TEXT,
                mobile_number_2 TEXT,
                truck_details TEXT,
                builty_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (account_id) REFERENCES accounts(account_id),
                FOREIGN KEY (warehouse_id) REFERENCES warehouses(warehouse_id),
                FOREIGN KEY (truck_id) REFERENCES trucks(truck_id),
                FOREIGN KEY (builty_id) REFERENCES builty(builty_id)
            )
        ''')
        
        # Stock table (Warehouse operations)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS warehouse_stock (
                stock_id INTEGER PRIMARY KEY AUTOINCREMENT,
                warehouse_id INTEGER NOT NULL,
                builty_id INTEGER,
                transaction_type TEXT NOT NULL,
                quantity_mt REAL NOT NULL,
                unloader_employee TEXT,
                account_id INTEGER,
                date DATE NOT NULL,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (warehouse_id) REFERENCES warehouses(warehouse_id),
                FOREIGN KEY (builty_id) REFERENCES builty(builty_id),
                FOREIGN KEY (account_id) REFERENCES accounts(account_id)
            )
        ''')
        
        # E-Bills table (Accountant)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ebills (
                ebill_id INTEGER PRIMARY KEY AUTOINCREMENT,
                builty_id INTEGER NOT NULL,
                ebill_number TEXT UNIQUE NOT NULL,
                amount REAL NOT NULL,
                eway_bill_pdf TEXT,
                generated_date DATE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (builty_id) REFERENCES builty(builty_id)
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
            cursor.executemany('INSERT INTO warehouses (warehouse_name, location, capacity) VALUES (?, ?, ?)', default_warehouses)
        
        # Insert default accounts if not exist
        cursor.execute("SELECT COUNT(*) FROM accounts")
        if cursor.fetchone()[0] == 0:
            default_accounts = [
                ('Payal Fertilizers', 'Payal', '9876543210', 'Company Address'),
                ('Dealer 1', 'Dealer', '9876543211', 'Dealer Address'),
                ('Retailer 1', 'Retailer', '9876543212', 'Retailer Address'),
            ]
            cursor.executemany('INSERT INTO accounts (account_name, account_type, contact, address) VALUES (?, ?, ?, ?)', default_accounts)
        
        # Insert default products if not exist
        cursor.execute("SELECT COUNT(*) FROM products")
        if cursor.fetchone()[0] == 0:
            default_products = [
                ('Urea', 'URE01', 'Fertilizer', 'MT', 'Nitrogen fertilizer'),
                ('DAP', 'DAP01', 'Fertilizer', 'MT', 'Diammonium Phosphate'),
                ('MOP', 'MOP01', 'Fertilizer', 'MT', 'Muriate of Potash'),
                ('NPK', 'NPK01', 'Fertilizer', 'MT', 'NPK Complex fertilizer'),
            ]
            cursor.executemany('INSERT INTO products (product_name, product_code, product_type, unit, description) VALUES (?, ?, ?, ?, ?)', default_products)
        
        # Migrate old 'Company' account type to 'Payal'
        cursor.execute("UPDATE accounts SET account_type = 'Payal' WHERE account_type = 'Company'")
        
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
    
    # ========== Rake Operations (Admin) ==========
    
    def add_rake(self, rake_code, company_name, company_code, date, rr_quantity, 
                 product_name, product_code, rake_point_name):
        """Add new rake"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO rakes (rake_code, company_name, company_code, date, rr_quantity,
                                  product_name, product_code, rake_point_name)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (rake_code, company_name, company_code, date, rr_quantity, 
                  product_name, product_code, rake_point_name))
            
            rake_id = cursor.lastrowid
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
        cursor.execute('SELECT * FROM rakes ORDER BY created_at DESC')
        rakes = cursor.fetchall()
        conn.close()
        return rakes
    
    def get_rake_by_code(self, rake_code):
        """Get rake by code"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM rakes WHERE rake_code = ?', (rake_code,))
        rake = cursor.fetchone()
        conn.close()
        return rake
    
    def get_rake_balance(self, rake_code):
        """Get rake quantity balance (total - dispatched via loading slips)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Get total rake quantity
        cursor.execute('SELECT rr_quantity FROM rakes WHERE rake_code = ?', (rake_code,))
        rake_result = cursor.fetchone()
        if not rake_result:
            conn.close()
            return None
        
        total_quantity = rake_result[0]
        
        # Get total dispatched via loading slips
        cursor.execute('''
            SELECT COALESCE(SUM(quantity_mt), 0)
            FROM loading_slips
            WHERE rake_code = ?
        ''', (rake_code,))
        dispatched_quantity = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'total': total_quantity,
            'dispatched': dispatched_quantity,
            'remaining': total_quantity - dispatched_quantity
        }
    
    def get_next_serial_number_for_rake(self, rake_code):
        """Get the next serial number for a rake's loading slip"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Get the highest serial number for this rake
        cursor.execute('''
            SELECT COALESCE(MAX(slip_number), 0) + 1
            FROM loading_slips
            WHERE rake_code = ?
        ''', (rake_code,))
        next_serial = cursor.fetchone()[0]
        
        conn.close()
        return next_serial
    
    def get_next_lr_number(self):
        """Get the next LR number sequentially"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Get the highest LR number
        cursor.execute('''
            SELECT MAX(CAST(lr_number AS INTEGER))
            FROM builty
            WHERE lr_number IS NOT NULL AND lr_number != ''
            AND lr_number GLOB '[0-9]*'
        ''')
        result = cursor.fetchone()[0]
        
        conn.close()
        
        if result:
            return str(int(result) + 1)
        else:
            return "1001"  # Starting LR number
    
    # ========== Account Operations ==========
    
    def add_account(self, account_name, account_type, contact, address):
        """Add new account"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO accounts (account_name, account_type, contact, address)
                VALUES (?, ?, ?, ?)
            ''', (account_name, account_type, contact, address))
            account_id = cursor.lastrowid
            conn.commit()
            return account_id
        except Exception as e:
            print(f"Error adding account: {e}")
            conn.rollback()
            return None
        finally:
            conn.close()
    
    def get_all_accounts(self):
        """Get all accounts"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM accounts ORDER BY account_name')
        accounts = cursor.fetchall()
        conn.close()
        return accounts
    
    def get_accounts_by_type(self, account_type):
        """Get accounts by type"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM accounts WHERE account_type = ? ORDER BY account_name', (account_type,))
        accounts = cursor.fetchall()
        conn.close()
        return accounts
    
    # ========== Product Operations ==========
    
    def add_product(self, product_name, product_code, product_type='Fertilizer', unit='MT', description=''):
        """Add new product"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO products (product_name, product_code, product_type, unit, description)
                VALUES (?, ?, ?, ?, ?)
            ''', (product_name, product_code, product_type, unit, description))
            product_id = cursor.lastrowid
            conn.commit()
            return product_id
        except Exception as e:
            print(f"Error adding product: {e}")
            conn.rollback()
            return None
        finally:
            conn.close()
    
    def get_all_products(self):
        """Get all products"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM products ORDER BY product_name')
        products = cursor.fetchall()
        conn.close()
        return products
    
    def get_product_by_name(self, product_name):
        """Get product by name"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM products WHERE product_name = ?', (product_name,))
        product = cursor.fetchone()
        conn.close()
        return product
    
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
    
    # ========== Truck Operations ==========
    
    def add_truck(self, truck_number, driver_name, driver_mobile, owner_name, owner_mobile):
        """Add new truck"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO trucks (truck_number, driver_name, driver_mobile, owner_name, owner_mobile)
                VALUES (?, ?, ?, ?, ?)
            ''', (truck_number, driver_name, driver_mobile, owner_name, owner_mobile))
            truck_id = cursor.lastrowid
            conn.commit()
            return truck_id
        except Exception as e:
            print(f"Error adding truck: {e}")
            conn.rollback()
            return None
        finally:
            conn.close()
    
    def get_all_trucks(self):
        """Get all trucks"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM trucks ORDER BY truck_number')
        trucks = cursor.fetchall()
        conn.close()
        return trucks
    
    def get_truck_by_number(self, truck_number):
        """Get truck by number"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM trucks WHERE truck_number = ?', (truck_number,))
        truck = cursor.fetchone()
        conn.close()
        return truck
    
    # ========== Builty Operations (Rake Point & Warehouse) ==========
    
    def add_builty(self, builty_number, rake_code, date, rake_point_name, account_id, warehouse_id,
                   truck_id, loading_point, unloading_point, goods_name, number_of_bags,
                   quantity_mt, kg_per_bag, rate_per_mt, total_freight, lr_number, 
                   lr_index, created_by_role):
        """Add new builty"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO builty (builty_number, rake_code, date, rake_point_name, account_id, warehouse_id,
                                   truck_id, loading_point, unloading_point, goods_name, number_of_bags,
                                   quantity_mt, kg_per_bag, rate_per_mt, total_freight, lr_number,
                                   lr_index, created_by_role)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (builty_number, rake_code, date, rake_point_name, account_id, warehouse_id, truck_id,
                  loading_point, unloading_point, goods_name, number_of_bags, quantity_mt,
                  kg_per_bag, rate_per_mt, total_freight, lr_number, lr_index, created_by_role))
            
            builty_id = cursor.lastrowid
            conn.commit()
            return builty_id
        except Exception as e:
            print(f"Error adding builty: {e}")
            conn.rollback()
            return None
        finally:
            conn.close()
    
    def get_all_builties(self):
        """Get all builties"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT b.*, a.account_name, w.warehouse_name, t.truck_number
            FROM builty b
            LEFT JOIN accounts a ON b.account_id = a.account_id
            LEFT JOIN warehouses w ON b.warehouse_id = w.warehouse_id
            LEFT JOIN trucks t ON b.truck_id = t.truck_id
            ORDER BY b.created_at DESC
        ''')
        builties = cursor.fetchall()
        conn.close()
        return builties
    
    def get_warehouse_builties(self):
        """Get only builties destined for warehouses (warehouse_id NOT NULL)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT b.*, a.account_name, w.warehouse_name, t.truck_number
            FROM builty b
            LEFT JOIN accounts a ON b.account_id = a.account_id
            LEFT JOIN warehouses w ON b.warehouse_id = w.warehouse_id
            LEFT JOIN trucks t ON b.truck_id = t.truck_id
            WHERE b.warehouse_id IS NOT NULL
            ORDER BY b.created_at DESC
        ''')
        builties = cursor.fetchall()
        conn.close()
        return builties
    
    def get_builty_by_id(self, builty_id):
        """Get builty by ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT b.*, a.account_name, w.warehouse_name, t.truck_number, 
                   t.driver_name, t.driver_mobile, t.owner_name, t.owner_mobile
            FROM builty b
            LEFT JOIN accounts a ON b.account_id = a.account_id
            LEFT JOIN warehouses w ON b.warehouse_id = w.warehouse_id
            LEFT JOIN trucks t ON b.truck_id = t.truck_id
            WHERE b.builty_id = ?
        ''', (builty_id,))
        builty = cursor.fetchone()
        conn.close()
        return builty
    
    # ========== Loading Slip Operations (Rake Point) ==========
    
    def add_loading_slip(self, rake_code, slip_number, loading_point_name, destination,
                        account_id, warehouse_id, quantity_bags, quantity_mt, truck_id, wagon_number, 
                        goods_name, truck_driver, truck_owner, mobile_1, mobile_2, truck_details, builty_id=None):
        """Add new loading slip with complete truck and goods details - supports both accounts and warehouses"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO loading_slips (rake_code, slip_number, loading_point_name, destination,
                                          account_id, warehouse_id, quantity_bags, quantity_mt, truck_id, 
                                          wagon_number, goods_name, truck_driver, truck_owner,
                                          mobile_number_1, mobile_number_2, truck_details, builty_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (rake_code, slip_number, loading_point_name, destination, account_id, warehouse_id,
                  quantity_bags, quantity_mt, truck_id, wagon_number, goods_name,
                  truck_driver, truck_owner, mobile_1, mobile_2, truck_details, builty_id))
            
            slip_id = cursor.lastrowid
            conn.commit()
            return slip_id
        except Exception as e:
            print(f"Error adding loading slip: {e}")
            conn.rollback()
            return None
        finally:
            conn.close()
    
    def get_loading_slips_by_rake(self, rake_code):
        """Get loading slips by rake code"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT ls.*, a.account_name, t.truck_number
            FROM loading_slips ls
            LEFT JOIN accounts a ON ls.account_id = a.account_id
            LEFT JOIN trucks t ON ls.truck_id = t.truck_id
            WHERE ls.rake_code = ?
            ORDER BY ls.slip_number
        ''', (rake_code,))
        slips = cursor.fetchall()
        conn.close()
        return slips
    
    def get_all_loading_slips(self):
        """Get all loading slips that haven't been used for builty yet - with all details (accounts & warehouses)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT ls.slip_id, ls.rake_code, ls.slip_number, ls.loading_point_name, 
                   ls.destination, 
                   COALESCE(a.account_name, w.warehouse_name) as destination_name,
                   ls.wagon_number, 
                   ls.quantity_bags, ls.quantity_mt, t.truck_number,
                   ls.goods_name, ls.truck_driver, ls.truck_owner,
                   ls.mobile_number_1, ls.mobile_number_2
            FROM loading_slips ls
            LEFT JOIN accounts a ON ls.account_id = a.account_id
            LEFT JOIN warehouses w ON ls.warehouse_id = w.warehouse_id
            LEFT JOIN trucks t ON ls.truck_id = t.truck_id
            WHERE ls.builty_id IS NULL
            ORDER BY ls.slip_id DESC
        ''')
        slips = cursor.fetchall()
        conn.close()
        return slips
    
    def get_all_loading_slips_with_status(self):
        """Get ALL loading slips (including those converted to builties) with status"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
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
            ORDER BY ls.slip_id DESC
        ''')
        slips = cursor.fetchall()
        conn.close()
        return slips
    
    def link_loading_slip_to_builty(self, slip_id, builty_id):
        """Link a loading slip to a builty (one-to-one relationship)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                UPDATE loading_slips 
                SET builty_id = ? 
                WHERE slip_id = ?
            ''', (builty_id, slip_id))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error linking loading slip to builty: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    # ========== Warehouse Stock Operations ==========
    
    def add_warehouse_stock_in(self, warehouse_id, builty_id, quantity_mt, 
                               unloader_employee, account_id, date, notes=''):
        """Add stock in to warehouse"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO warehouse_stock (warehouse_id, builty_id, transaction_type, 
                                            quantity_mt, unloader_employee, account_id, date, notes)
                VALUES (?, ?, 'IN', ?, ?, ?, ?, ?)
            ''', (warehouse_id, builty_id, quantity_mt, unloader_employee, account_id, date, notes))
            
            stock_id = cursor.lastrowid
            conn.commit()
            return stock_id
        except Exception as e:
            print(f"Error adding stock in: {e}")
            conn.rollback()
            return None
        finally:
            conn.close()
    
    def add_warehouse_stock_out(self, warehouse_id, builty_id, quantity_mt, 
                                account_id, date, notes=''):
        """Add stock out from warehouse"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO warehouse_stock (warehouse_id, builty_id, transaction_type, 
                                            quantity_mt, account_id, date, notes)
                VALUES (?, ?, 'OUT', ?, ?, ?, ?)
            ''', (warehouse_id, builty_id, quantity_mt, account_id, date, notes))
            
            stock_id = cursor.lastrowid
            conn.commit()
            return stock_id
        except Exception as e:
            print(f"Error adding stock out: {e}")
            conn.rollback()
            return None
        finally:
            conn.close()
    
    def get_warehouse_balance_stock(self, warehouse_id):
        """Get balance stock for warehouse"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT 
                COALESCE(SUM(CASE WHEN transaction_type = 'IN' THEN quantity_mt ELSE 0 END), 0) as stock_in,
                COALESCE(SUM(CASE WHEN transaction_type = 'OUT' THEN quantity_mt ELSE 0 END), 0) as stock_out
            FROM warehouse_stock
            WHERE warehouse_id = ?
        ''', (warehouse_id,))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            stock_in = result[0]
            stock_out = result[1]
            balance = stock_in - stock_out
            return {'stock_in': stock_in, 'stock_out': stock_out, 'balance': balance}
        return {'stock_in': 0, 'stock_out': 0, 'balance': 0}
    
    def get_warehouse_stock_transactions(self, warehouse_id):
        """Get all stock transactions for warehouse"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT ws.*, b.builty_number, a.account_name
            FROM warehouse_stock ws
            LEFT JOIN builty b ON ws.builty_id = b.builty_id
            LEFT JOIN accounts a ON ws.account_id = a.account_id
            WHERE ws.warehouse_id = ?
            ORDER BY ws.date DESC, ws.created_at DESC
        ''', (warehouse_id,))
        transactions = cursor.fetchall()
        conn.close()
        return transactions
    
    # ========== E-Bill Operations (Accountant) ==========
    
    def add_ebill(self, builty_id, ebill_number, amount, generated_date, eway_bill_pdf=None):
        """Add new e-bill"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO ebills (builty_id, ebill_number, amount, generated_date, eway_bill_pdf)
                VALUES (?, ?, ?, ?, ?)
            ''', (builty_id, ebill_number, amount, generated_date, eway_bill_pdf))
            
            ebill_id = cursor.lastrowid
            conn.commit()
            return ebill_id
        except Exception as e:
            print(f"Error adding e-bill: {e}")
            conn.rollback()
            return None
        finally:
            conn.close()
    
    def get_all_ebills(self):
        """Get all e-bills with complete builty details"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT e.ebill_id, e.ebill_number, e.amount, e.generated_date, 
                   e.eway_bill_pdf, e.created_at,
                   b.builty_number, b.goods_name, b.quantity_mt, b.lr_number,
                   t.truck_number,
                   COALESCE(a.account_name, 'N/A') as account_name
            FROM ebills e
            LEFT JOIN builty b ON e.builty_id = b.builty_id
            LEFT JOIN trucks t ON b.truck_id = t.truck_id
            LEFT JOIN accounts a ON b.account_id = a.account_id
            ORDER BY e.created_at DESC
        ''')
        ebills = cursor.fetchall()
        conn.close()
        return ebills
    
    def get_builties_without_ebills(self):
        """Get builties that don't have e-bills yet"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT b.*
            FROM builty b
            LEFT JOIN ebills e ON b.builty_id = e.builty_id
            WHERE e.ebill_id IS NULL
            ORDER BY b.date DESC
        ''')
        builties = cursor.fetchall()
        conn.close()
        return builties
    
    # ========== Dashboard Statistics ==========
    
    def get_admin_dashboard_stats(self):
        """Get admin dashboard statistics"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Total rakes
        cursor.execute('SELECT COUNT(*) FROM rakes')
        total_rakes = cursor.fetchone()[0]
        
        # Total builties
        cursor.execute('SELECT COUNT(*) FROM builty')
        total_builties = cursor.fetchone()[0]
        
        # Total stock in all warehouses
        cursor.execute('''
            SELECT 
                COALESCE(SUM(CASE WHEN transaction_type = 'IN' THEN quantity_mt ELSE 0 END), 0) as stock_in,
                COALESCE(SUM(CASE WHEN transaction_type = 'OUT' THEN quantity_mt ELSE 0 END), 0) as stock_out
            FROM warehouse_stock
        ''')
        result = cursor.fetchone()
        total_stock_in = result[0]
        total_stock_out = result[1]
        balance_stock = total_stock_in - total_stock_out
        
        # Total e-bills
        cursor.execute('SELECT COUNT(*), COALESCE(SUM(amount), 0) FROM ebills')
        result = cursor.fetchone()
        total_ebills = result[0]
        total_ebill_amount = result[1]
        
        conn.close()
        
        return {
            'total_rakes': total_rakes,
            'total_builties': total_builties,
            'total_stock_in': total_stock_in,
            'total_stock_out': total_stock_out,
            'balance_stock': balance_stock,
            'total_ebills': total_ebills,
            'total_ebill_amount': total_ebill_amount
        }
    
    def get_rake_summary(self):
        """Get rake-wise summary with stock in, stock out, balance"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT 
                r.rake_code,
                r.company_name,
                r.date,
                r.rr_quantity,
                COALESCE(SUM(CASE WHEN ws.transaction_type = 'IN' THEN ws.quantity_mt ELSE 0 END), 0) as stock_in,
                COALESCE(SUM(CASE WHEN ws.transaction_type = 'OUT' THEN ws.quantity_mt ELSE 0 END), 0) as stock_out
            FROM rakes r
            LEFT JOIN builty b ON r.rake_code = b.rake_code
            LEFT JOIN warehouse_stock ws ON b.builty_id = ws.builty_id
            GROUP BY r.rake_code, r.company_name, r.date, r.rr_quantity
            ORDER BY r.date DESC
        ''')
        summary = cursor.fetchall()
        conn.close()
        return summary
