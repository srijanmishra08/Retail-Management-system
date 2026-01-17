"""
Database module for FIMS - Redesigned for specific workflows
Handles all database operations with SQLite (local) or Turso/LibSQL (cloud)
OPTIMIZED: Connection reuse, caching, and batch queries for Vercel performance
"""

import sqlite3
import os
import time
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

# Try to import libsql for Turso cloud database
try:
    import libsql_experimental as libsql
    LIBSQL_AVAILABLE = True
except ImportError:
    LIBSQL_AVAILABLE = False


# Simple in-memory cache with TTL for reducing database calls
class SimpleCache:
    """Thread-safe simple cache with TTL support"""
    def __init__(self, ttl=30):
        self._cache = {}
        self._ttl = ttl
    
    def get(self, key):
        if key in self._cache:
            value, timestamp = self._cache[key]
            if time.time() - timestamp < self._ttl:
                return value
            del self._cache[key]
        return None
    
    def set(self, key, value):
        self._cache[key] = (value, time.time())
    
    def clear(self):
        self._cache.clear()
    
    def delete(self, key):
        if key in self._cache:
            del self._cache[key]


# Global cache instance with 30 second TTL
_cache = SimpleCache(ttl=30)


class Database:
    _cloud_connection = None  # Reusable connection for cloud database
    _connection_time = None   # Track when connection was created
    
    def __init__(self, db_name='fims.db'):
        self.db_name = db_name
        
        # Check for Turso cloud database configuration
        self.turso_url = os.environ.get('TURSO_DATABASE_URL')
        self.turso_token = os.environ.get('TURSO_AUTH_TOKEN')
        
        # Determine if we should use cloud database
        self.use_cloud = (
            LIBSQL_AVAILABLE and 
            self.turso_url and 
            self.turso_token
        )
        
        if self.use_cloud:
            print("🌐 Using Turso Cloud Database")
        else:
            print("💾 Using Local SQLite Database")
    
    @classmethod
    def reset_cloud_connection(cls):
        """Reset the cloud connection - call when connection is stale"""
        cls._cloud_connection = None
        cls._connection_time = None
    
    def get_connection(self):
        """Get database connection - reuse connection for cloud to reduce latency"""
        if self.use_cloud:
            # Check if connection is too old (older than 60 seconds) - Vercel serverless can have stale connections
            if Database._connection_time and (time.time() - Database._connection_time > 60):
                print("[DEBUG] Connection too old, resetting...")
                Database.reset_cloud_connection()
            
            # Reuse connection for cloud database to avoid TCP/TLS overhead
            if Database._cloud_connection is None:
                Database._cloud_connection = libsql.connect(
                    self.turso_url,
                    auth_token=self.turso_token
                )
                Database._connection_time = time.time()
            return Database._cloud_connection
        else:
            # Use local SQLite database
            conn = sqlite3.connect(self.db_name)
            conn.row_factory = sqlite3.Row
            return conn
    
    def close_connection(self, conn):
        """Safely close database connection (don't close reusable cloud connections)"""
        if not self.use_cloud:
            try:
                conn.close()
            except:
                pass
    
    def invalidate_cache(self):
        """Clear all cached data - call after write operations"""
        _cache.clear()
    
    def execute_custom_query(self, query, params=None, _retry=True):
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
            # Reset connection and retry once if this is a cloud connection error
            if self.use_cloud and _retry:
                print("[DEBUG] Retrying with fresh connection...")
                Database.reset_cloud_connection()
                return self.execute_custom_query(query, params, _retry=False)
            try:
                conn.rollback()
            except:
                pass
            return None
        finally:
            self.close_connection(conn)
    
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
                builty_head TEXT,
                is_closed INTEGER DEFAULT 0,
                closed_at TIMESTAMP,
                shortage REAL DEFAULT 0,
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
                distance REAL DEFAULT 0,
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
                unit_per_bag REAL DEFAULT 50.0,
                unit_type TEXT DEFAULT 'kg',
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Companies table (Product suppliers)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS companies (
                company_id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_name TEXT UNIQUE NOT NULL,
                company_code TEXT,
                contact_person TEXT,
                mobile TEXT,
                address TEXT,
                distance REAL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Employees table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS employees (
                employee_id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_name TEXT NOT NULL,
                employee_code TEXT,
                mobile TEXT,
                designation TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # CGMF (CG Markfed) table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cgmf (
                cgmf_id INTEGER PRIMARY KEY AUTOINCREMENT,
                district TEXT NOT NULL,
                destination TEXT NOT NULL,
                society_name TEXT NOT NULL,
                contact TEXT,
                distance REAL DEFAULT 0,
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
                distance REAL DEFAULT 0,
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
                cgmf_id INTEGER,
                truck_id INTEGER NOT NULL,
                loading_point TEXT NOT NULL,
                unloading_point TEXT NOT NULL,
                goods_name TEXT NOT NULL,
                number_of_bags INTEGER NOT NULL,
                quantity_mt REAL NOT NULL,
                kg_per_bag REAL,
                rate_per_mt REAL,
                total_freight REAL,
                advance REAL DEFAULT 0,
                to_pay REAL DEFAULT 0,
                lr_number TEXT,
                lr_index INTEGER,
                created_by_role TEXT,
                sub_head TEXT,
                receiver_name TEXT,
                received_quantity REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (account_id) REFERENCES accounts(account_id),
                FOREIGN KEY (warehouse_id) REFERENCES warehouses(warehouse_id),
                FOREIGN KEY (cgmf_id) REFERENCES cgmf(cgmf_id),
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
                cgmf_id INTEGER,
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
                sub_head TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (account_id) REFERENCES accounts(account_id),
                FOREIGN KEY (warehouse_id) REFERENCES warehouses(warehouse_id),
                FOREIGN KEY (cgmf_id) REFERENCES cgmf(cgmf_id),
                FOREIGN KEY (truck_id) REFERENCES trucks(truck_id),
                FOREIGN KEY (builty_id) REFERENCES builty(builty_id)
            )
        ''')
        
        # Stock table (Warehouse operations)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS warehouse_stock (
                stock_id INTEGER PRIMARY KEY AUTOINCREMENT,
                serial_number INTEGER,
                warehouse_id INTEGER NOT NULL,
                builty_id INTEGER,
                company_id INTEGER,
                product_id INTEGER,
                transaction_type TEXT NOT NULL,
                quantity_mt REAL NOT NULL,
                employee_id INTEGER,
                account_id INTEGER,
                cgmf_id INTEGER,
                account_type TEXT,
                dealer_name TEXT,
                source_type TEXT DEFAULT 'rake',
                truck_id INTEGER,
                date DATE NOT NULL,
                notes TEXT,
                remark TEXT,
                sub_head TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (warehouse_id) REFERENCES warehouses(warehouse_id),
                FOREIGN KEY (builty_id) REFERENCES builty(builty_id),
                FOREIGN KEY (company_id) REFERENCES companies(company_id),
                FOREIGN KEY (product_id) REFERENCES products(product_id),
                FOREIGN KEY (employee_id) REFERENCES employees(employee_id),
                FOREIGN KEY (account_id) REFERENCES accounts(account_id),
                FOREIGN KEY (cgmf_id) REFERENCES cgmf(cgmf_id),
                FOREIGN KEY (truck_id) REFERENCES trucks(truck_id)
            )
        ''')
        
        # E-Bills table (Accountant)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ebills (
                ebill_id INTEGER PRIMARY KEY AUTOINCREMENT,
                builty_id INTEGER NOT NULL,
                ebill_number TEXT UNIQUE NOT NULL,
                amount REAL NOT NULL,
                bill_pdf TEXT,
                eway_bill_pdf TEXT,
                generated_date DATE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (builty_id) REFERENCES builty(builty_id)
            )
        ''')
        
        # Rake Bill Payments table - stores received payments for each rake
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS rake_bill_payments (
                payment_id INTEGER PRIMARY KEY AUTOINCREMENT,
                rake_code TEXT NOT NULL UNIQUE,
                total_bill_amount REAL DEFAULT 0,
                received_amount REAL DEFAULT 0,
                remaining_amount REAL DEFAULT 0,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_by TEXT,
                FOREIGN KEY (rake_code) REFERENCES rakes(rake_code),
                FOREIGN KEY (updated_by) REFERENCES users(username)
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
                ('Urea', 'URE01', 'Fertilizer', 'MT', 50.0, 'kg', 'Nitrogen fertilizer'),
                ('DAP', 'DAP01', 'Fertilizer', 'MT', 50.0, 'kg', 'Diammonium Phosphate'),
                ('MOP', 'MOP01', 'Fertilizer', 'MT', 50.0, 'kg', 'Muriate of Potash'),
                ('NPK', 'NPK01', 'Fertilizer', 'MT', 50.0, 'kg', 'NPK Complex fertilizer'),
            ]
            cursor.executemany('INSERT INTO products (product_name, product_code, product_type, unit, unit_per_bag, unit_type, description) VALUES (?, ?, ?, ?, ?, ?, ?)', default_products)
        
        # Migrate old 'Company' account type to 'Payal'
        cursor.execute("UPDATE accounts SET account_type = 'Payal' WHERE account_type = 'Company'")
        
        # Migration: Add cgmf_id column to builty table if it doesn't exist
        try:
            cursor.execute("SELECT cgmf_id FROM builty LIMIT 1")
        except (sqlite3.OperationalError, ValueError, Exception) as e:
            if 'no such column' in str(e).lower() or 'cgmf_id' in str(e).lower():
                cursor.execute("ALTER TABLE builty ADD COLUMN cgmf_id INTEGER REFERENCES cgmf(cgmf_id)")
                print("Migration: Added cgmf_id column to builty table")
        
        # Migration: Add cgmf_id column to loading_slips table if it doesn't exist
        try:
            cursor.execute("SELECT cgmf_id FROM loading_slips LIMIT 1")
        except (sqlite3.OperationalError, ValueError, Exception) as e:
            if 'no such column' in str(e).lower() or 'cgmf_id' in str(e).lower():
                cursor.execute("ALTER TABLE loading_slips ADD COLUMN cgmf_id INTEGER REFERENCES cgmf(cgmf_id)")
                print("Migration: Added cgmf_id column to loading_slips table")
        
        # Migration: Add cgmf_id column to warehouse_stock table if it doesn't exist
        try:
            cursor.execute("SELECT cgmf_id FROM warehouse_stock LIMIT 1")
        except (sqlite3.OperationalError, ValueError, Exception) as e:
            if 'no such column' in str(e).lower() or 'cgmf_id' in str(e).lower():
                cursor.execute("ALTER TABLE warehouse_stock ADD COLUMN cgmf_id INTEGER REFERENCES cgmf(cgmf_id)")
                print("Migration: Added cgmf_id column to warehouse_stock table")
        
        # Migration: Add sub_head column to loading_slips table if it doesn't exist
        try:
            cursor.execute("SELECT sub_head FROM loading_slips LIMIT 1")
        except (sqlite3.OperationalError, ValueError, Exception) as e:
            if 'no such column' in str(e).lower() or 'sub_head' in str(e).lower():
                cursor.execute("ALTER TABLE loading_slips ADD COLUMN sub_head TEXT")
                print("Migration: Added sub_head column to loading_slips table")
        
        # Migration: Add sub_head column to builty table if it doesn't exist
        try:
            cursor.execute("SELECT sub_head FROM builty LIMIT 1")
        except (sqlite3.OperationalError, ValueError, Exception) as e:
            if 'no such column' in str(e).lower() or 'sub_head' in str(e).lower():
                cursor.execute("ALTER TABLE builty ADD COLUMN sub_head TEXT")
                print("Migration: Added sub_head column to builty table")
        
        # Migration: Add sub_head column to warehouse_stock table if it doesn't exist
        try:
            cursor.execute("SELECT sub_head FROM warehouse_stock LIMIT 1")
        except (sqlite3.OperationalError, ValueError, Exception) as e:
            if 'no such column' in str(e).lower() or 'sub_head' in str(e).lower():
                cursor.execute("ALTER TABLE warehouse_stock ADD COLUMN sub_head TEXT")
                print("Migration: Added sub_head column to warehouse_stock table")
        
        # Migration: Add is_closed column to rakes table if it doesn't exist
        try:
            cursor.execute("SELECT is_closed FROM rakes LIMIT 1")
        except (sqlite3.OperationalError, ValueError, Exception) as e:
            if 'no such column' in str(e).lower() or 'is_closed' in str(e).lower():
                cursor.execute("ALTER TABLE rakes ADD COLUMN is_closed INTEGER DEFAULT 0")
                print("Migration: Added is_closed column to rakes table")
        
        # Migration: Add closed_at column to rakes table if it doesn't exist
        try:
            cursor.execute("SELECT closed_at FROM rakes LIMIT 1")
        except (sqlite3.OperationalError, ValueError, Exception) as e:
            if 'no such column' in str(e).lower() or 'closed_at' in str(e).lower():
                cursor.execute("ALTER TABLE rakes ADD COLUMN closed_at TIMESTAMP")
                print("Migration: Added closed_at column to rakes table")
        
        # Migration: Add shortage column to rakes table if it doesn't exist
        try:
            cursor.execute("SELECT shortage FROM rakes LIMIT 1")
        except (sqlite3.OperationalError, ValueError, Exception) as e:
            if 'no such column' in str(e).lower() or 'shortage' in str(e).lower():
                cursor.execute("ALTER TABLE rakes ADD COLUMN shortage REAL DEFAULT 0")
                print("Migration: Added shortage column to rakes table")
        
        # Migration: Add bill_pdf column to ebills table if it doesn't exist
        try:
            cursor.execute("SELECT bill_pdf FROM ebills LIMIT 1")
        except (sqlite3.OperationalError, ValueError, Exception) as e:
            if 'no such column' in str(e).lower() or 'bill_pdf' in str(e).lower():
                cursor.execute("ALTER TABLE ebills ADD COLUMN bill_pdf TEXT")
                print("Migration: Added bill_pdf column to ebills table")
        
        # Migration: Add builty_head column to rakes table
        try:
            cursor.execute("SELECT builty_head FROM rakes LIMIT 1")
        except (sqlite3.OperationalError, ValueError, Exception) as e:
            if 'no such column' in str(e).lower() or 'builty_head' in str(e).lower():
                cursor.execute("ALTER TABLE rakes ADD COLUMN builty_head TEXT")
                print("Migration: Added builty_head column to rakes table")
        
        # Migration: Add receiver_name column to builty table
        try:
            cursor.execute("SELECT receiver_name FROM builty LIMIT 1")
        except (sqlite3.OperationalError, ValueError, Exception) as e:
            if 'no such column' in str(e).lower() or 'receiver_name' in str(e).lower():
                cursor.execute("ALTER TABLE builty ADD COLUMN receiver_name TEXT")
                print("Migration: Added receiver_name column to builty table")
        
        # Migration: Add received_quantity column to builty table
        try:
            cursor.execute("SELECT received_quantity FROM builty LIMIT 1")
        except (sqlite3.OperationalError, ValueError, Exception) as e:
            if 'no such column' in str(e).lower() or 'received_quantity' in str(e).lower():
                cursor.execute("ALTER TABLE builty ADD COLUMN received_quantity REAL")
                print("Migration: Added received_quantity column to builty table")
        
        # Migration: Add distance column to accounts table
        try:
            cursor.execute("SELECT distance FROM accounts LIMIT 1")
        except (sqlite3.OperationalError, ValueError, Exception) as e:
            if 'no such column' in str(e).lower() or 'distance' in str(e).lower():
                cursor.execute("ALTER TABLE accounts ADD COLUMN distance REAL DEFAULT 0")
                print("Migration: Added distance column to accounts table")
        
        # Migration: Add distance column to warehouses table
        try:
            cursor.execute("SELECT distance FROM warehouses LIMIT 1")
        except (sqlite3.OperationalError, ValueError, Exception) as e:
            if 'no such column' in str(e).lower() or 'distance' in str(e).lower():
                cursor.execute("ALTER TABLE warehouses ADD COLUMN distance REAL DEFAULT 0")
                print("Migration: Added distance column to warehouses table")
        
        # Migration: Add distance column to companies table
        try:
            cursor.execute("SELECT distance FROM companies LIMIT 1")
        except (sqlite3.OperationalError, ValueError, Exception) as e:
            if 'no such column' in str(e).lower() or 'distance' in str(e).lower():
                cursor.execute("ALTER TABLE companies ADD COLUMN distance REAL DEFAULT 0")
                print("Migration: Added distance column to companies table")
        
        # Migration: Add distance column to cgmf table
        try:
            cursor.execute("SELECT distance FROM cgmf LIMIT 1")
        except (sqlite3.OperationalError, ValueError, Exception) as e:
            if 'no such column' in str(e).lower() or 'distance' in str(e).lower():
                cursor.execute("ALTER TABLE cgmf ADD COLUMN distance REAL DEFAULT 0")
                print("Migration: Added distance column to cgmf table")
        
        # Migration: Add warehouse_account_id column to loading_slips table for tracking whose stock is stored in warehouse
        try:
            cursor.execute("SELECT warehouse_account_id FROM loading_slips LIMIT 1")
        except (sqlite3.OperationalError, ValueError, Exception) as e:
            if 'no such column' in str(e).lower() or 'warehouse_account_id' in str(e).lower():
                cursor.execute("ALTER TABLE loading_slips ADD COLUMN warehouse_account_id INTEGER REFERENCES accounts(account_id)")
                print("Migration: Added warehouse_account_id column to loading_slips table")
        
        # Migration: Add warehouse_account_type column to loading_slips table
        try:
            cursor.execute("SELECT warehouse_account_type FROM loading_slips LIMIT 1")
        except (sqlite3.OperationalError, ValueError, Exception) as e:
            if 'no such column' in str(e).lower() or 'warehouse_account_type' in str(e).lower():
                cursor.execute("ALTER TABLE loading_slips ADD COLUMN warehouse_account_type TEXT")
                print("Migration: Added warehouse_account_type column to loading_slips table")
        
        conn.commit()
        self.close_connection(conn)
        print("Database initialized successfully!")
    
    # ========== User Operations ==========
    
    def authenticate_user(self, username, password):
        """Authenticate user and return user data"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        user = cursor.fetchone()
        self.close_connection(conn)
        
        if user and check_password_hash(user[2], password):
            return user
        return None
    
    def get_user_by_id(self, user_id):
        """Get user by ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        user = cursor.fetchone()
        self.close_connection(conn)
        return user
    
    def get_all_users(self):
        """Get all users"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT user_id, username, role, created_at FROM users')
        users = cursor.fetchall()
        self.close_connection(conn)
        return users
    
    # ========== Rake Operations (Admin) ==========
    
    def add_rake(self, rake_code, company_name, company_code, date, rr_quantity, 
                 product_name, product_code, rake_point_name, builty_head=None):
        """Add new rake"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO rakes (rake_code, company_name, company_code, date, rr_quantity,
                                  product_name, product_code, rake_point_name, builty_head)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (rake_code, company_name, company_code, date, rr_quantity, 
                  product_name, product_code, rake_point_name, builty_head))
            
            rake_id = cursor.lastrowid
            conn.commit()
            return rake_id
        except Exception as e:
            print(f"Error adding rake: {e}")
            conn.rollback()
            return None
        finally:
            self.close_connection(conn)
    
    def get_all_rakes(self):
        """Get all rakes"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM rakes ORDER BY created_at DESC')
        rakes = cursor.fetchall()
        self.close_connection(conn)
        return rakes
    
    def get_active_rakes(self):
        """Get only active (not closed) rakes"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM rakes WHERE is_closed = 0 ORDER BY created_at DESC')
        rakes = cursor.fetchall()
        self.close_connection(conn)
        return rakes
    
    def get_rake_by_code(self, rake_code):
        """Get rake by code"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM rakes WHERE rake_code = ?', (rake_code,))
        rake = cursor.fetchone()
        self.close_connection(conn)
        return rake
    
    def get_rake_balance(self, rake_code):
        """Get rake quantity balance (total - dispatched via loading slips)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Get total rake quantity and product details
        cursor.execute('''
            SELECT r.rr_quantity, p.unit_per_bag 
            FROM rakes r
            LEFT JOIN products p ON r.product_name = p.product_name
            WHERE r.rake_code = ?
        ''', (rake_code,))
        rake_result = cursor.fetchone()
        if not rake_result:
            self.close_connection(conn)
            return None
        
        total_quantity = rake_result[0]
        unit_per_bag = rake_result[1] if rake_result[1] else 50.0  # Default to 50 if not found
        
        # Get total dispatched via loading slips
        cursor.execute('''
            SELECT COALESCE(SUM(quantity_mt), 0)
            FROM loading_slips
            WHERE rake_code = ?
        ''', (rake_code,))
        dispatched_quantity = cursor.fetchone()[0]
        
        self.close_connection(conn)
        
        return {
            'total': total_quantity,
            'dispatched': dispatched_quantity,
            'remaining': total_quantity - dispatched_quantity,
            'unit_per_bag': unit_per_bag
        }
    
    # ========== OPTIMIZED BATCH QUERY METHODS ==========
    # These methods reduce N+1 query problems by fetching all data in single queries
    
    def get_all_rake_balances(self):
        """Get balances for ALL rakes in a single query - eliminates N+1 problem"""
        cache_key = 'all_rake_balances'
        cached = _cache.get(cache_key)
        if cached is not None:
            return cached
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Single query to get all rake balances
        cursor.execute('''
            SELECT r.rake_code, r.rr_quantity,
                   COALESCE(SUM(ls.quantity_mt), 0) as dispatched
            FROM rakes r
            LEFT JOIN loading_slips ls ON r.rake_code = ls.rake_code
            GROUP BY r.rake_code, r.rr_quantity
        ''')
        
        results = {}
        for row in cursor.fetchall():
            rake_code = row[0]
            rr_quantity = row[1] or 0
            dispatched = row[2] or 0
            results[rake_code] = {
                'rr_quantity': rr_quantity,
                'dispatched': dispatched,
                'remaining': rr_quantity - dispatched
            }
        
        self.close_connection(conn)
        _cache.set(cache_key, results)
        return results
    
    def get_all_warehouse_balances(self):
        """Get balances for ALL warehouses in a single query"""
        cache_key = 'all_warehouse_balances'
        cached = _cache.get(cache_key)
        if cached is not None:
            return cached
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT warehouse_id,
                   COALESCE(SUM(CASE WHEN transaction_type = 'IN' THEN quantity_mt ELSE 0 END), 0) as stock_in,
                   COALESCE(SUM(CASE WHEN transaction_type = 'OUT' THEN quantity_mt ELSE 0 END), 0) as stock_out
            FROM warehouse_stock
            GROUP BY warehouse_id
        ''')
        
        results = {}
        for row in cursor.fetchall():
            warehouse_id = row[0]
            stock_in = row[1] or 0
            stock_out = row[2] or 0
            results[warehouse_id] = {
                'stock_in': stock_in,
                'stock_out': stock_out,
                'balance': stock_in - stock_out
            }
        
        self.close_connection(conn)
        _cache.set(cache_key, results)
        return results
    
    def get_rakes_with_balances(self, limit=None, _retry=True):
        """Get all rakes with their balances in a single optimized query"""
        cache_key = f'rakes_with_balances_{limit}'
        cached = _cache.get(cache_key)
        if cached is not None:
            return cached
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        limit_clause = f"LIMIT {limit}" if limit else ""
        
        try:
            cursor.execute(f'''
                SELECT r.rake_id, r.rake_code, r.company_name, r.company_code,
                       r.date, r.rr_quantity, r.product_name, r.product_code,
                       r.rake_point_name, r.builty_head, r.is_closed, r.closed_at, r.shortage,
                       COALESCE(SUM(ls.quantity_mt), 0) as dispatched
                FROM rakes r
                LEFT JOIN loading_slips ls ON r.rake_code = ls.rake_code
                GROUP BY r.rake_id, r.rake_code, r.company_name, r.company_code,
                         r.date, r.rr_quantity, r.product_name, r.product_code,
                         r.rake_point_name, r.builty_head, r.is_closed, r.closed_at, r.shortage
                ORDER BY r.rake_id DESC
                {limit_clause}
            ''')
            
            results = []
            for row in cursor.fetchall():
                rr_quantity = row[5] or 0
                dispatched = row[13] or 0
                results.append({
                    'rake_id': row[0],
                    'rake_code': row[1],
                    'company_name': row[2],
                    'company_code': row[3],
                    'date': row[4],
                    'rr_quantity': rr_quantity,
                    'product_name': row[6],
                    'product_code': row[7],
                    'rake_point_name': row[8],
                    'builty_head': row[9],
                    'is_closed': row[10] or 0,
                    'closed_at': row[11],
                    'shortage': row[12] or 0,
                    'dispatched': dispatched,
                    'remaining': rr_quantity - dispatched
                })
            
            self.close_connection(conn)
            _cache.set(cache_key, results)
            return results
        except Exception as e:
            print(f"Error in get_rakes_with_balances: {e}")
            if self.use_cloud and _retry:
                print("[DEBUG] Retrying get_rakes_with_balances with fresh connection...")
                Database.reset_cloud_connection()
                return self.get_rakes_with_balances(limit, _retry=False)
            return []
        return results
    
    def get_dashboard_stats_optimized(self, _retry=True):
        """Get all admin dashboard stats in a SINGLE query"""
        cache_key = 'admin_dashboard_stats_optimized'
        cached = _cache.get(cache_key)
        if cached is not None:
            return cached
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Single query for all counts and stats
            cursor.execute('''
                SELECT 
                    (SELECT COUNT(*) FROM rakes) as total_rakes,
                    (SELECT COUNT(*) FROM rakes WHERE is_closed = 0 OR is_closed IS NULL) as active_rakes,
                    (SELECT COUNT(*) FROM builty) as total_builties,
                    (SELECT COUNT(*) FROM loading_slips) as total_loading_slips,
                    (SELECT COUNT(*) FROM accounts) as total_accounts,
                    (SELECT COUNT(*) FROM warehouses) as total_warehouses,
                    (SELECT COALESCE(SUM(rr_quantity), 0) FROM rakes) as total_stock,
                    (SELECT COALESCE(SUM(quantity_mt), 0) FROM loading_slips) as total_dispatched,
                    (SELECT COALESCE(SUM(CASE WHEN transaction_type = 'IN' THEN quantity_mt ELSE 0 END), 0) FROM warehouse_stock) as total_stock_in,
                    (SELECT COALESCE(SUM(CASE WHEN transaction_type = 'OUT' THEN quantity_mt ELSE 0 END), 0) FROM warehouse_stock) as total_stock_out,
                    (SELECT COUNT(*) FROM ebills) as total_ebills,
                    (SELECT COALESCE(SUM(amount), 0) FROM ebills) as total_ebill_amount
            ''')
            
            row = cursor.fetchone()
            total_stock_in = row[8] or 0
            total_stock_out = row[9] or 0
            
            stats = {
                'total_rakes': row[0] or 0,
                'active_rakes': row[1] or 0,
                'total_builties': row[2] or 0,
                'total_loading_slips': row[3] or 0,
                'total_accounts': row[4] or 0,
                'total_warehouses': row[5] or 0,
                'total_stock': row[6] or 0,
                'total_dispatched': row[7] or 0,
                'total_stock_in': total_stock_in,
                'total_stock_out': total_stock_out,
                'balance_stock': total_stock_in - total_stock_out,
                'total_ebills': row[10] or 0,
                'total_ebill_amount': row[11] or 0
            }
            
            self.close_connection(conn)
            _cache.set(cache_key, stats)
            return stats
        except Exception as e:
            print(f"Error in get_dashboard_stats_optimized: {e}")
            if self.use_cloud and _retry:
                print("[DEBUG] Retrying get_dashboard_stats_optimized with fresh connection...")
                Database.reset_cloud_connection()
                return self.get_dashboard_stats_optimized(_retry=False)
            # Return default stats on error
            return {
                'total_rakes': 0, 'active_rakes': 0, 'total_builties': 0,
                'total_loading_slips': 0, 'total_accounts': 0, 'total_warehouses': 0,
                'total_stock': 0, 'total_dispatched': 0, 'total_stock_in': 0,
                'total_stock_out': 0, 'balance_stock': 0, 'total_ebills': 0,
                'total_ebill_amount': 0
            }
    
    def count_active_rakes_optimized(self):
        """Count active rakes (with remaining stock) in a single query instead of loop"""
        cache_key = 'active_rakes_count'
        cached = _cache.get(cache_key)
        if cached is not None:
            return cached
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT COUNT(*) FROM (
                SELECT r.rake_code
                FROM rakes r
                LEFT JOIN loading_slips ls ON r.rake_code = ls.rake_code
                WHERE r.is_closed = 0 OR r.is_closed IS NULL
                GROUP BY r.rake_code, r.rr_quantity
                HAVING r.rr_quantity - COALESCE(SUM(ls.quantity_mt), 0) > 0
            )
        ''')
        
        count = cursor.fetchone()[0] or 0
        self.close_connection(conn)
        _cache.set(cache_key, count)
        return count
    
    def get_logistic_bill_summary_optimized(self, selected_company='all', selected_rake='all'):
        """Get logistic bill summary with all data in optimized queries"""
        cache_key = f'logistic_bill_summary_{selected_company}_{selected_rake}'
        cached = _cache.get(cache_key)
        if cached is not None:
            return cached
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Build filter conditions
        conditions = ["1=1"]
        params = []
        
        if selected_company != 'all':
            conditions.append("r.company_name = ?")
            params.append(selected_company)
        if selected_rake != 'all':
            conditions.append("r.rake_code = ?")
            params.append(selected_rake)
        
        where_clause = " AND ".join(conditions)
        
        # Single optimized query for bill summary with all data
        query = f'''
            SELECT 
                r.rake_code,
                r.company_name,
                r.rr_quantity,
                r.date,
                COALESCE(rbp.total_bill_amount, COALESCE(SUM(b.total_freight), 0)) as bill_amount,
                COALESCE(rbp.received_amount, 0) as received_payment
            FROM rakes r
            LEFT JOIN builty b ON r.rake_code = b.rake_code
            LEFT JOIN rake_bill_payments rbp ON r.rake_code = rbp.rake_code
            WHERE {where_clause}
            GROUP BY r.rake_code, r.company_name, r.rr_quantity, r.date, 
                     rbp.total_bill_amount, rbp.received_amount
            ORDER BY r.date DESC
        '''
        
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        
        results = []
        for row in cursor.fetchall():
            results.append({
                'rake_code': row[0],
                'company_name': row[1],
                'total_stock': row[2] or 0,
                'date': row[3],
                'bill_amount': row[4] or 0,
                'received_payment': row[5] or 0
            })
        
        self.close_connection(conn)
        _cache.set(cache_key, results)
        return results
    
    def get_warehouse_dashboard_stats(self):
        """Get all warehouse dashboard statistics in optimized queries"""
        cache_key = 'warehouse_dashboard_stats'
        cached = _cache.get(cache_key)
        if cached is not None:
            return cached
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Get all stats in one query
        cursor.execute('''
            SELECT 
                (SELECT COUNT(*) FROM accounts) as account_count,
                (SELECT COUNT(*) FROM builty) as builty_count,
                (SELECT COALESCE(SUM(quantity_mt), 0) FROM warehouse_stock 
                 WHERE transaction_type = 'IN' AND date = date('now')) as today_stock_in
        ''')
        
        row = cursor.fetchone()
        stats = {
            'account_count': row[0] or 0,
            'builty_count': row[1] or 0,
            'today_stock_in': row[2] or 0
        }
        
        self.close_connection(conn)
        _cache.set(cache_key, stats)
        return stats
    
    def get_recent_warehouse_movements(self, limit=10):
        """Get recent warehouse stock movements"""
        cache_key = f'recent_warehouse_movements_{limit}'
        cached = _cache.get(cache_key)
        if cached is not None:
            return cached
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT ws.date, ws.transaction_type, b.builty_number, w.warehouse_name, ws.quantity_mt
            FROM warehouse_stock ws
            LEFT JOIN builty b ON ws.builty_id = b.builty_id
            JOIN warehouses w ON ws.warehouse_id = w.warehouse_id
            ORDER BY ws.date DESC, ws.stock_id DESC
            LIMIT ?
        ''', (limit,))
        
        results = [tuple(row) for row in cursor.fetchall()]
        self.close_connection(conn)
        _cache.set(cache_key, results)
        return results
    
    # ========== END OPTIMIZED BATCH QUERY METHODS ==========

    def close_rake(self, rake_code):
        """Close a rake and calculate shortage (rr_quantity - total dispatched)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Get rake's rr_quantity
            cursor.execute('SELECT rr_quantity FROM rakes WHERE rake_code = ?', (rake_code,))
            rake_result = cursor.fetchone()
            if not rake_result:
                self.close_connection(conn)
                return False, "Rake not found"
            
            rr_quantity = rake_result[0]
            
            # Get total dispatched via loading slips
            cursor.execute('''
                SELECT COALESCE(SUM(quantity_mt), 0)
                FROM loading_slips
                WHERE rake_code = ?
            ''', (rake_code,))
            dispatched_quantity = cursor.fetchone()[0]
            
            # Calculate shortage
            shortage = rr_quantity - dispatched_quantity
            
            # Update rake as closed
            cursor.execute('''
                UPDATE rakes 
                SET is_closed = 1, closed_at = CURRENT_TIMESTAMP, shortage = ?
                WHERE rake_code = ?
            ''', (shortage, rake_code))
            
            conn.commit()
            self.close_connection(conn)
            return True, shortage
        except Exception as e:
            conn.rollback()
            self.close_connection(conn)
            return False, str(e)
    
    def reopen_rake(self, rake_code):
        """Reopen a closed rake"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Check if rake is currently closed
            cursor.execute('SELECT is_closed FROM rakes WHERE rake_code = ?', (rake_code,))
            result = cursor.fetchone()
            if not result:
                self.close_connection(conn)
                return False, "Rake not found"
            
            if not result[0]:
                self.close_connection(conn)
                return False, "Rake is not closed"
            
            # Reopen the rake
            cursor.execute('''
                UPDATE rakes 
                SET is_closed = 0, closed_at = NULL, shortage = 0
                WHERE rake_code = ?
            ''', (rake_code,))
            
            conn.commit()
            self.close_connection(conn)
            return True, "Rake reopened successfully"
        except Exception as e:
            conn.rollback()
            self.close_connection(conn)
            return False, str(e)
    
    def get_total_shortage(self):
        """Get total shortage from all closed rakes"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT COALESCE(SUM(shortage), 0) FROM rakes WHERE is_closed = 1
        ''')
        total_shortage = cursor.fetchone()[0]
        self.close_connection(conn)
        return total_shortage
    
    def get_closed_rakes(self):
        """Get all closed rakes with shortage info"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM rakes WHERE is_closed = 1 ORDER BY closed_at DESC
        ''')
        rakes = cursor.fetchall()
        self.close_connection(conn)
        return rakes
    
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
        
        self.close_connection(conn)
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
        
        self.close_connection(conn)
        
        if result:
            return str(int(result) + 1)
        else:
            return "1001"  # Starting LR number
    
    def get_next_warehouse_stock_serial(self, warehouse_id):
        """Get the next serial number for warehouse stock"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT MAX(serial_number)
            FROM warehouse_stock
            WHERE warehouse_id = ?
        ''', (warehouse_id,))
        result = cursor.fetchone()[0]
        
        self.close_connection(conn)
        
        if result:
            return int(result) + 1
        else:
            return 1  # Starting serial number
    
    # ========== Account Operations ==========
    
    def add_account(self, account_name, account_type, contact, address, distance=0):
        """Add new account"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO accounts (account_name, account_type, contact, address, distance)
                VALUES (?, ?, ?, ?, ?)
            ''', (account_name, account_type, contact, address, distance))
            account_id = cursor.lastrowid
            conn.commit()
            return account_id
        except Exception as e:
            print(f"Error adding account: {e}")
            conn.rollback()
            return None
        finally:
            self.close_connection(conn)
    
    def delete_account(self, account_id):
        """Delete an account by ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            # Check if account is used in any builties
            cursor.execute('SELECT COUNT(*) FROM builty WHERE account_id = ?', (account_id,))
            if cursor.fetchone()[0] > 0:
                return False, "Account is used in builties and cannot be deleted"
            
            # Check if account is used in any loading slips
            cursor.execute('SELECT COUNT(*) FROM loading_slips WHERE account_id = ?', (account_id,))
            if cursor.fetchone()[0] > 0:
                return False, "Account is used in loading slips and cannot be deleted"
            
            # Check if account is used in any warehouse stock
            cursor.execute('SELECT COUNT(*) FROM warehouse_stock WHERE account_id = ?', (account_id,))
            if cursor.fetchone()[0] > 0:
                return False, "Account is used in warehouse stock records and cannot be deleted"
            
            cursor.execute('DELETE FROM accounts WHERE account_id = ?', (account_id,))
            conn.commit()
            return True, "Account deleted successfully"
        except Exception as e:
            print(f"Error deleting account: {e}")
            conn.rollback()
            return False, str(e)
        finally:
            self.close_connection(conn)
    
    def get_all_accounts(self):
        """Get all accounts"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM accounts ORDER BY account_name')
        accounts = cursor.fetchall()
        self.close_connection(conn)
        return accounts
    
    def get_accounts_by_type(self, account_type):
        """Get accounts by type"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM accounts WHERE account_type = ? ORDER BY account_name', (account_type,))
        accounts = cursor.fetchall()
        self.close_connection(conn)
        return accounts
    
    def get_account_by_id(self, account_id):
        """Get account by ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM accounts WHERE account_id = ?', (account_id,))
        account = cursor.fetchone()
        self.close_connection(conn)
        return account
    
    def update_account(self, account_id, account_name, account_type, contact, address, distance=0):
        """Update an existing account"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                UPDATE accounts 
                SET account_name = ?, account_type = ?, contact = ?, address = ?, distance = ?
                WHERE account_id = ?
            ''', (account_name, account_type, contact, address, distance, account_id))
            conn.commit()
            return True, "Account updated successfully"
        except Exception as e:
            conn.rollback()
            return False, str(e)
        finally:
            self.close_connection(conn)
    
    def update_company(self, company_id, company_name, company_code, contact_person, mobile, address, distance=0):
        """Update an existing company"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                UPDATE companies 
                SET company_name = ?, company_code = ?, contact_person = ?, mobile = ?, address = ?, distance = ?
                WHERE company_id = ?
            ''', (company_name, company_code, contact_person, mobile, address, distance, company_id))
            conn.commit()
            return True, "Company updated successfully"
        except Exception as e:
            conn.rollback()
            return False, str(e)
        finally:
            self.close_connection(conn)
    
    def update_employee(self, employee_id, employee_name, employee_code, mobile, designation):
        """Update an existing employee"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                UPDATE employees 
                SET employee_name = ?, employee_code = ?, mobile = ?, designation = ?
                WHERE employee_id = ?
            ''', (employee_name, employee_code, mobile, designation, employee_id))
            conn.commit()
            return True, "Employee updated successfully"
        except Exception as e:
            conn.rollback()
            return False, str(e)
        finally:
            self.close_connection(conn)
    
    def update_cgmf(self, cgmf_id, district, destination, society_name, contact, distance=0):
        """Update an existing CGMF society"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                UPDATE cgmf 
                SET district = ?, destination = ?, society_name = ?, contact = ?, distance = ?
                WHERE cgmf_id = ?
            ''', (district, destination, society_name, contact, distance, cgmf_id))
            conn.commit()
            return True, "CGMF updated successfully"
        except Exception as e:
            conn.rollback()
            return False, str(e)
        finally:
            self.close_connection(conn)
    
    # ========== Product Operations ==========
    
    def add_product(self, product_name, product_code, product_type='Fertilizer', unit='MT', unit_per_bag=50.0, unit_type='kg', description=''):
        """Add new product"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO products (product_name, product_code, product_type, unit, unit_per_bag, unit_type, description)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (product_name, product_code, product_type, unit, unit_per_bag, unit_type, description))
            product_id = cursor.lastrowid
            conn.commit()
            return product_id
        except Exception as e:
            print(f"Error adding product: {e}")
            conn.rollback()
            return None
        finally:
            self.close_connection(conn)
    
    def get_all_products(self):
        """Get all products"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM products ORDER BY product_name')
        products = cursor.fetchall()
        self.close_connection(conn)
        return products
    
    def get_product_by_name(self, product_name):
        """Get product by name"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM products WHERE product_name = ?', (product_name,))
        product = cursor.fetchone()
        self.close_connection(conn)
        return product
    
    # ========== Company Operations ==========
    
    def add_company(self, company_name, company_code='', contact_person='', mobile='', address='', distance=0):
        """Add new company"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO companies (company_name, company_code, contact_person, mobile, address, distance)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (company_name, company_code, contact_person, mobile, address, distance))
            company_id = cursor.lastrowid
            conn.commit()
            return company_id
        except Exception as e:
            print(f"Error adding company: {e}")
            conn.rollback()
            return None
        finally:
            self.close_connection(conn)
    
    def get_all_companies(self):
        """Get all companies"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM companies ORDER BY company_name')
        companies = cursor.fetchall()
        self.close_connection(conn)
        return companies
    
    def get_company_by_id(self, company_id):
        """Get company by ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM companies WHERE company_id = ?', (company_id,))
        company = cursor.fetchone()
        self.close_connection(conn)
        return company
    
    # ========== Employee Operations ==========
    
    def add_employee(self, employee_name, employee_code='', mobile='', designation=''):
        """Add new employee"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO employees (employee_name, employee_code, mobile, designation)
                VALUES (?, ?, ?, ?)
            ''', (employee_name, employee_code, mobile, designation))
            employee_id = cursor.lastrowid
            conn.commit()
            return employee_id
        except Exception as e:
            print(f"Error adding employee: {e}")
            conn.rollback()
            return None
        finally:
            self.close_connection(conn)
    
    def get_all_employees(self):
        """Get all employees"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM employees ORDER BY employee_name')
        employees = cursor.fetchall()
        self.close_connection(conn)
        return employees
    
    def get_employee_by_id(self, employee_id):
        """Get employee by ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM employees WHERE employee_id = ?', (employee_id,))
        employee = cursor.fetchone()
        self.close_connection(conn)
        return employee
    
    # ========== CGMF (CG Markfed) Operations ==========
    
    def add_cgmf(self, district, destination, society_name, contact='', distance=0):
        """Add new CGMF society"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO cgmf (district, destination, society_name, contact, distance)
                VALUES (?, ?, ?, ?, ?)
            ''', (district, destination, society_name, contact, distance))
            cgmf_id = cursor.lastrowid
            conn.commit()
            return cgmf_id
        except Exception as e:
            print(f"Error adding CGMF: {e}")
            conn.rollback()
            return None
        finally:
            self.close_connection(conn)
    
    def get_all_cgmf(self):
        """Get all CGMF societies"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM cgmf ORDER BY district, society_name')
        cgmf_list = cursor.fetchall()
        self.close_connection(conn)
        return cgmf_list
    
    def get_cgmf_by_id(self, cgmf_id):
        """Get CGMF by ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM cgmf WHERE cgmf_id = ?', (cgmf_id,))
        cgmf = cursor.fetchone()
        self.close_connection(conn)
        return cgmf
    
    # ========== Warehouse Operations ==========
    
    def get_all_warehouses(self):
        """Get all warehouses"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM warehouses')
        warehouses = cursor.fetchall()
        self.close_connection(conn)
        return warehouses
    
    def get_warehouse_by_id(self, warehouse_id):
        """Get warehouse by ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM warehouses WHERE warehouse_id = ?', (warehouse_id,))
        warehouse = cursor.fetchone()
        self.close_connection(conn)
        return warehouse
    
    def add_warehouse(self, warehouse_name, location, capacity, distance=0):
        """Add new warehouse"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO warehouses (warehouse_name, location, capacity, distance)
                VALUES (?, ?, ?, ?)
            ''', (warehouse_name, location, capacity, distance))
            warehouse_id = cursor.lastrowid
            conn.commit()
            return warehouse_id
        except Exception as e:
            print(f"Error adding warehouse: {e}")
            conn.rollback()
            return None
        finally:
            self.close_connection(conn)
    
    def update_warehouse(self, warehouse_id, warehouse_name, location, capacity):
        """Update warehouse details"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                UPDATE warehouses 
                SET warehouse_name = ?, location = ?, capacity = ?
                WHERE warehouse_id = ?
            ''', (warehouse_name, location, capacity, warehouse_id))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error updating warehouse: {e}")
            conn.rollback()
            return False
        finally:
            self.close_connection(conn)
    
    def delete_warehouse(self, warehouse_id):
        """Delete a warehouse by ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            # Check if warehouse is used in any builties
            cursor.execute('SELECT COUNT(*) FROM builty WHERE warehouse_id = ?', (warehouse_id,))
            if cursor.fetchone()[0] > 0:
                return False, "Warehouse is used in builties and cannot be deleted"
            
            # Check if warehouse is used in any loading slips
            cursor.execute('SELECT COUNT(*) FROM loading_slips WHERE warehouse_id = ?', (warehouse_id,))
            if cursor.fetchone()[0] > 0:
                return False, "Warehouse is used in loading slips and cannot be deleted"
            
            # Check if warehouse has stock entries
            cursor.execute('SELECT COUNT(*) FROM warehouse_stock WHERE warehouse_id = ?', (warehouse_id,))
            if cursor.fetchone()[0] > 0:
                return False, "Warehouse has stock entries and cannot be deleted"
            
            cursor.execute('DELETE FROM warehouses WHERE warehouse_id = ?', (warehouse_id,))
            conn.commit()
            return True, "Warehouse deleted successfully"
        except Exception as e:
            print(f"Error deleting warehouse: {e}")
            conn.rollback()
            return False, str(e)
        finally:
            self.close_connection(conn)
    
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
            
            # Reset connection after write to ensure subsequent operations see the new truck
            if self.use_cloud:
                Database.reset_cloud_connection()
            
            return truck_id
        except Exception as e:
            print(f"Error adding truck: {e}")
            conn.rollback()
            return None
        finally:
            self.close_connection(conn)
    
    def get_all_trucks(self):
        """Get all trucks"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM trucks ORDER BY truck_number')
        trucks = cursor.fetchall()
        self.close_connection(conn)
        return trucks
    
    def get_truck_by_number(self, truck_number):
        """Get truck by number"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM trucks WHERE truck_number = ?', (truck_number,))
        truck = cursor.fetchone()
        self.close_connection(conn)
        return truck
    
    # ========== Builty Operations (Rake Point & Warehouse) ==========
    
    def add_builty(self, builty_number, rake_code, date, rake_point_name, account_id, warehouse_id,
                   truck_id, loading_point, unloading_point, goods_name, number_of_bags,
                   quantity_mt, kg_per_bag, rate_per_mt, total_freight, advance=0, to_pay=0, lr_number='', 
                   lr_index=0, created_by_role='', cgmf_id=None, sub_head=None, receiver_name=None, received_quantity=None):
        """Add new builty - supports accounts, warehouses, and CGMF"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO builty (builty_number, rake_code, date, rake_point_name, account_id, warehouse_id, cgmf_id,
                                   truck_id, loading_point, unloading_point, goods_name, number_of_bags,
                                   quantity_mt, kg_per_bag, rate_per_mt, total_freight, advance, to_pay, lr_number,
                                   lr_index, created_by_role, sub_head, receiver_name, received_quantity)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (builty_number, rake_code, date, rake_point_name, account_id, warehouse_id, cgmf_id, truck_id,
                  loading_point, unloading_point, goods_name, number_of_bags, quantity_mt,
                  kg_per_bag, rate_per_mt, total_freight, advance, to_pay, lr_number, lr_index, created_by_role, sub_head,
                  receiver_name, received_quantity))
            
            conn.commit()
            
            # Get the builty_id - handle both sqlite and libsql
            builty_id = cursor.lastrowid
            if not builty_id or builty_id == 0:
                # For libsql/Turso, try to get the last inserted id differently
                cursor.execute('SELECT builty_id FROM builty WHERE builty_number = ? ORDER BY builty_id DESC LIMIT 1', (builty_number,))
                result = cursor.fetchone()
                builty_id = result[0] if result else None
            
            # CRITICAL: Invalidate cache and reset connection after write
            self.invalidate_cache()
            if self.use_cloud:
                Database.reset_cloud_connection()
            
            return builty_id
        except Exception as e:
            print(f"Error adding builty: {e}")
            conn.rollback()
            return None
        finally:
            self.close_connection(conn)
    
    def get_all_builties(self):
        """Get all builties"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT b.*, a.account_name, w.warehouse_name, t.truck_number,
                   c.society_name as cgmf_name, c.district as cgmf_district
            FROM builty b
            LEFT JOIN accounts a ON b.account_id = a.account_id
            LEFT JOIN warehouses w ON b.warehouse_id = w.warehouse_id
            LEFT JOIN trucks t ON b.truck_id = t.truck_id
            LEFT JOIN cgmf c ON b.cgmf_id = c.cgmf_id
            ORDER BY b.created_at DESC
        ''')
        builties = cursor.fetchall()
        self.close_connection(conn)
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
        self.close_connection(conn)
        return builties
    
    def get_builty_by_id(self, builty_id):
        """Get builty by ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT b.builty_id, b.builty_number, b.rake_code, b.date, b.rake_point_name,
                   b.account_id, b.warehouse_id, b.cgmf_id, b.truck_id, 
                   b.loading_point, b.unloading_point, b.goods_name, b.number_of_bags,
                   b.quantity_mt, b.kg_per_bag, b.rate_per_mt, b.total_freight,
                   b.advance, b.to_pay, b.lr_number, b.lr_index, b.created_by_role, b.created_at,
                   a.account_name, w.warehouse_name, t.truck_number, 
                   t.driver_name, t.driver_mobile, t.owner_name, t.owner_mobile,
                   r.builty_head, b.receiver_name, b.received_quantity, a.address as account_address
            FROM builty b
            LEFT JOIN accounts a ON b.account_id = a.account_id
            LEFT JOIN warehouses w ON b.warehouse_id = w.warehouse_id
            LEFT JOIN trucks t ON b.truck_id = t.truck_id
            LEFT JOIN rakes r ON b.rake_code = r.rake_code
            WHERE b.builty_id = ?
        ''', (builty_id,))
        builty = cursor.fetchone()
        self.close_connection(conn)
        return builty
    
    # ========== Loading Slip Operations (Rake Point) ==========
    
    def add_loading_slip(self, rake_code, slip_number, loading_point_name, destination,
                        account_id, warehouse_id, quantity_bags, quantity_mt, truck_id, wagon_number, 
                        goods_name, truck_driver, truck_owner, mobile_1, mobile_2, truck_details, builty_id=None, cgmf_id=None, sub_head=None, warehouse_account_id=None, warehouse_account_type=None):
        """Add new loading slip with complete truck and goods details - supports accounts, warehouses, and CGMF"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO loading_slips (rake_code, slip_number, loading_point_name, destination,
                                          account_id, warehouse_id, cgmf_id, quantity_bags, quantity_mt, truck_id, 
                                          wagon_number, goods_name, truck_driver, truck_owner,
                                          mobile_number_1, mobile_number_2, truck_details, builty_id, sub_head,
                                          warehouse_account_id, warehouse_account_type)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (rake_code, slip_number, loading_point_name, destination, account_id, warehouse_id, cgmf_id,
                  quantity_bags, quantity_mt, truck_id, wagon_number, goods_name,
                  truck_driver, truck_owner, mobile_1, mobile_2, truck_details, builty_id, sub_head,
                  warehouse_account_id, warehouse_account_type))
            
            conn.commit()
            
            # Get the slip_id - handle both sqlite and libsql
            slip_id = cursor.lastrowid
            if not slip_id or slip_id == 0:
                # For libsql/Turso, try to get the last inserted id differently
                cursor.execute('SELECT slip_id FROM loading_slips WHERE rake_code = ? AND slip_number = ? ORDER BY slip_id DESC LIMIT 1', (rake_code, slip_number))
                result = cursor.fetchone()
                slip_id = result[0] if result else None
            
            # CRITICAL: Invalidate cache after successful write
            self.invalidate_cache()
            
            # CRITICAL: Reset cloud connection after write to ensure subsequent reads see the new data
            if self.use_cloud:
                Database.reset_cloud_connection()
            
            return slip_id
        except Exception as e:
            print(f"Error adding loading slip: {e}")
            conn.rollback()
            return None
        finally:
            self.close_connection(conn)
    
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
        self.close_connection(conn)
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
        self.close_connection(conn)
        return slips
    
    def get_warehouse_loading_slips(self):
        """Get loading slips created FROM warehouses (not from rakes) that haven't been converted to builty yet"""
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
            AND ls.loading_point_name IN (SELECT warehouse_name FROM warehouses)
            ORDER BY ls.slip_id DESC
        ''')
        slips = cursor.fetchall()
        self.close_connection(conn)
        return slips
    
    def get_rakepoint_loading_slips(self):
        """Get loading slips created FROM rakes (not from warehouses) that haven't been converted to builty yet - for rakepoint users. Excludes loading slips from closed rakes."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Get loading slips that don't have a builty, are not from warehouses, and are from active (not closed) rakes
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
                LEFT JOIN rakes r ON ls.rake_code = r.rake_code
                WHERE (ls.builty_id IS NULL OR ls.builty_id = 0)
                AND ls.loading_point_name NOT IN (SELECT warehouse_name FROM warehouses WHERE warehouse_name IS NOT NULL)
                AND (r.is_closed IS NULL OR r.is_closed = 0)
                ORDER BY ls.slip_id DESC
            ''')
            
            slips = cursor.fetchall()
            print(f"DEBUG: Found {len(slips)} rakepoint loading slips without builty (from active rakes only)")
            return slips
        except Exception as e:
            print(f"ERROR in get_rakepoint_loading_slips: {e}")
            return []
        finally:
            self.close_connection(conn)
    
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
        self.close_connection(conn)
        return slips
    
    def link_loading_slip_to_builty(self, slip_id, builty_id):
        """Link a loading slip to a builty (one-to-one relationship)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            # First check if slip exists and is not already linked
            cursor.execute('SELECT slip_id, builty_id FROM loading_slips WHERE slip_id = ?', (slip_id,))
            slip = cursor.fetchone()
            
            if not slip:
                print(f"ERROR: Loading slip {slip_id} not found")
                return False
            
            if slip[1] is not None and slip[1] != 0:
                print(f"WARNING: Loading slip {slip_id} already linked to builty {slip[1]}")
            
            # Update the builty_id
            cursor.execute('''
                UPDATE loading_slips 
                SET builty_id = ? 
                WHERE slip_id = ?
            ''', (builty_id, slip_id))
            
            rows_affected = cursor.rowcount
            conn.commit()
            
            print(f"DEBUG: Successfully linked loading slip {slip_id} to builty {builty_id}, rows affected: {rows_affected}")
            return True
        except Exception as e:
            print(f"Error linking loading slip to builty: {e}")
            conn.rollback()
            return False
        finally:
            self.close_connection(conn)
    
    def delete_loading_slip(self, slip_id, delete_builty=False):
        """Delete a loading slip and optionally its associated builty"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            # Get loading slip details
            cursor.execute('SELECT * FROM loading_slips WHERE slip_id = ?', (slip_id,))
            slip = cursor.fetchone()
            if not slip:
                return False, "Loading slip not found"
            
            builty_id = slip[18]  # builty_id column
            
            # If there's a linked builty and delete_builty is True, delete it first
            if builty_id and delete_builty:
                # Delete warehouse stock records for this builty
                cursor.execute('DELETE FROM warehouse_stock WHERE builty_id = ?', (builty_id,))
                # Delete the builty
                cursor.execute('DELETE FROM builty WHERE builty_id = ?', (builty_id,))
            elif builty_id and not delete_builty:
                return False, "Loading slip has an associated builty. Please confirm builty deletion."
            
            # Delete the loading slip
            cursor.execute('DELETE FROM loading_slips WHERE slip_id = ?', (slip_id,))
            
            conn.commit()
            return True, "Loading slip deleted successfully"
        except Exception as e:
            print(f"Error deleting loading slip: {e}")
            conn.rollback()
            return False, str(e)
        finally:
            self.close_connection(conn)
    
    def delete_builty(self, builty_id, delete_loading_slip=False):
        """Delete a builty and optionally its associated loading slip"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            # Get builty details
            cursor.execute('SELECT * FROM builty WHERE builty_id = ?', (builty_id,))
            builty = cursor.fetchone()
            if not builty:
                return False, "Builty not found"
            
            # Delete warehouse stock records for this builty
            cursor.execute('DELETE FROM warehouse_stock WHERE builty_id = ?', (builty_id,))
            
            # Find and handle linked loading slip
            cursor.execute('SELECT slip_id FROM loading_slips WHERE builty_id = ?', (builty_id,))
            linked_slip = cursor.fetchone()
            
            if linked_slip and delete_loading_slip:
                cursor.execute('DELETE FROM loading_slips WHERE slip_id = ?', (linked_slip[0],))
            elif linked_slip:
                # Unlink the loading slip
                cursor.execute('UPDATE loading_slips SET builty_id = NULL WHERE slip_id = ?', (linked_slip[0],))
            
            # Delete the builty
            cursor.execute('DELETE FROM builty WHERE builty_id = ?', (builty_id,))
            
            conn.commit()
            return True, "Builty deleted successfully"
        except Exception as e:
            print(f"Error deleting builty: {e}")
            conn.rollback()
            return False, str(e)
        finally:
            self.close_connection(conn)
    
    def get_loading_slip_by_id(self, slip_id):
        """Get loading slip by ID with all details"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT ls.*, a.account_name, w.warehouse_name, t.truck_number
            FROM loading_slips ls
            LEFT JOIN accounts a ON ls.account_id = a.account_id
            LEFT JOIN warehouses w ON ls.warehouse_id = w.warehouse_id
            LEFT JOIN trucks t ON ls.truck_id = t.truck_id
            WHERE ls.slip_id = ?
        ''', (slip_id,))
        slip = cursor.fetchone()
        self.close_connection(conn)
        return slip
    
    def update_loading_slip(self, slip_id, destination, quantity_bags, quantity_mt, goods_name, account_id=None, warehouse_id=None, cgmf_id=None, date=None):
        """Update loading slip details"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            # Get the original quantity to calculate difference
            cursor.execute('SELECT quantity_mt FROM loading_slips WHERE slip_id = ?', (slip_id,))
            old_slip = cursor.fetchone()
            if not old_slip:
                return False, "Loading slip not found"
            
            # Update with account/warehouse/cgmf IDs and date if provided
            if date:
                if account_id or warehouse_id or cgmf_id:
                    cursor.execute('''
                        UPDATE loading_slips 
                        SET destination = ?, quantity_bags = ?, quantity_mt = ?, goods_name = ?,
                            account_id = ?, warehouse_id = ?, cgmf_id = ?, created_at = ?
                        WHERE slip_id = ?
                    ''', (destination, quantity_bags, quantity_mt, goods_name, account_id, warehouse_id, cgmf_id, date, slip_id))
                else:
                    cursor.execute('''
                        UPDATE loading_slips 
                        SET destination = ?, quantity_bags = ?, quantity_mt = ?, goods_name = ?, created_at = ?
                        WHERE slip_id = ?
                    ''', (destination, quantity_bags, quantity_mt, goods_name, date, slip_id))
            else:
                if account_id or warehouse_id or cgmf_id:
                    cursor.execute('''
                        UPDATE loading_slips 
                        SET destination = ?, quantity_bags = ?, quantity_mt = ?, goods_name = ?,
                            account_id = ?, warehouse_id = ?, cgmf_id = ?
                        WHERE slip_id = ?
                    ''', (destination, quantity_bags, quantity_mt, goods_name, account_id, warehouse_id, cgmf_id, slip_id))
                else:
                    cursor.execute('''
                        UPDATE loading_slips 
                        SET destination = ?, quantity_bags = ?, quantity_mt = ?, goods_name = ?
                        WHERE slip_id = ?
                    ''', (destination, quantity_bags, quantity_mt, goods_name, slip_id))
            
            conn.commit()
            self.invalidate_cache()  # Clear cache after update
            # Reset cloud connection after write to ensure subsequent reads see the new data
            if self.use_cloud:
                Database.reset_cloud_connection()
            return True, "Loading slip updated successfully"
        except Exception as e:
            print(f"Error updating loading slip: {e}")
            conn.rollback()
            return False, str(e)
        finally:
            self.close_connection(conn)
    
    def update_builty(self, builty_id, unloading_point, number_of_bags, quantity_mt, rate_per_mt, total_freight, advance, to_pay, account_id=None, warehouse_id=None, cgmf_id=None, date=None):
        """Update builty details"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('SELECT * FROM builty WHERE builty_id = ?', (builty_id,))
            old_builty = cursor.fetchone()
            if not old_builty:
                return False, "Builty not found"
            
            old_quantity = old_builty[13]  # quantity_mt
            quantity_diff = quantity_mt - old_quantity
            
            # Update builty with account/warehouse/cgmf IDs and date if provided
            if date:
                if account_id or warehouse_id or cgmf_id:
                    cursor.execute('''
                        UPDATE builty 
                        SET unloading_point = ?, number_of_bags = ?, quantity_mt = ?, 
                            rate_per_mt = ?, total_freight = ?, advance = ?, to_pay = ?,
                            account_id = ?, warehouse_id = ?, cgmf_id = ?, date = ?
                        WHERE builty_id = ?
                    ''', (unloading_point, number_of_bags, quantity_mt, rate_per_mt, total_freight, advance, to_pay, account_id, warehouse_id, cgmf_id, date, builty_id))
                else:
                    cursor.execute('''
                        UPDATE builty 
                        SET unloading_point = ?, number_of_bags = ?, quantity_mt = ?, 
                            rate_per_mt = ?, total_freight = ?, advance = ?, to_pay = ?, date = ?
                        WHERE builty_id = ?
                    ''', (unloading_point, number_of_bags, quantity_mt, rate_per_mt, total_freight, advance, to_pay, date, builty_id))
            else:
                if account_id or warehouse_id or cgmf_id:
                    cursor.execute('''
                        UPDATE builty 
                        SET unloading_point = ?, number_of_bags = ?, quantity_mt = ?, 
                            rate_per_mt = ?, total_freight = ?, advance = ?, to_pay = ?,
                            account_id = ?, warehouse_id = ?, cgmf_id = ?
                        WHERE builty_id = ?
                    ''', (unloading_point, number_of_bags, quantity_mt, rate_per_mt, total_freight, advance, to_pay, account_id, warehouse_id, cgmf_id, builty_id))
                else:
                    cursor.execute('''
                        UPDATE builty 
                        SET unloading_point = ?, number_of_bags = ?, quantity_mt = ?, 
                            rate_per_mt = ?, total_freight = ?, advance = ?, to_pay = ?
                        WHERE builty_id = ?
                    ''', (unloading_point, number_of_bags, quantity_mt, rate_per_mt, total_freight, advance, to_pay, builty_id))
            
            # Update warehouse stock if there was a quantity change
            if quantity_diff != 0:
                cursor.execute('''
                    UPDATE warehouse_stock 
                    SET quantity_mt = quantity_mt + ?
                    WHERE builty_id = ?
                ''', (quantity_diff, builty_id))
            
            conn.commit()
            self.invalidate_cache()  # Clear cache after update
            # Reset cloud connection after write to ensure subsequent reads see the new data
            if self.use_cloud:
                Database.reset_cloud_connection()
            return True, "Builty updated successfully"
        except Exception as e:
            print(f"Error updating builty: {e}")
            conn.rollback()
            return False, str(e)
        finally:
            self.close_connection(conn)
    
    # ========== Warehouse Stock Operations ==========
    
    def add_warehouse_stock_in(self, warehouse_id, builty_id, quantity_mt, employee_id=None,
                               account_id=None, date=None, notes='', company_id=None, product_id=None,
                               source_type='rake', truck_id=None, serial_number=None, cgmf_id=None, sub_head=None):
        """Add stock in to warehouse"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            # Auto-generate serial number if not provided
            if serial_number is None:
                serial_number = self.get_next_warehouse_stock_serial(warehouse_id)
            
            cursor.execute('''
                INSERT INTO warehouse_stock (serial_number, warehouse_id, builty_id, transaction_type, 
                                            quantity_mt, employee_id, account_id, cgmf_id, date, notes,
                                            company_id, product_id, source_type, truck_id, sub_head)
                VALUES (?, ?, ?, 'IN', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (serial_number, warehouse_id, builty_id, quantity_mt, employee_id, account_id, cgmf_id, date, notes,
                  company_id, product_id, source_type, truck_id, sub_head))
            
            stock_id = cursor.lastrowid
            conn.commit()
            
            # CRITICAL: Invalidate cache and reset connection after write
            self.invalidate_cache()
            if self.use_cloud:
                Database.reset_cloud_connection()
            
            return stock_id
        except Exception as e:
            print(f"Error adding stock in: {e}")
            conn.rollback()
            return None
        finally:
            self.close_connection(conn)
    
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
            
            # CRITICAL: Invalidate cache and reset connection after write
            self.invalidate_cache()
            if self.use_cloud:
                Database.reset_cloud_connection()
            
            return stock_id
        except Exception as e:
            print(f"Error adding stock out: {e}")
            conn.rollback()
            return None
        finally:
            self.close_connection(conn)
    
    def update_warehouse_stock_allocation(self, stock_id, quantity_mt, account_type, dealer_name, remark):
        """Update warehouse stock allocation details"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                UPDATE warehouse_stock
                SET quantity_mt = ?, account_type = ?, dealer_name = ?, remark = ?
                WHERE stock_id = ?
            ''', (quantity_mt, account_type, dealer_name, remark, stock_id))
            
            conn.commit()
            return True
        except Exception as e:
            print(f"Error updating warehouse stock allocation: {e}")
            conn.rollback()
            return False
        finally:
            self.close_connection(conn)
    
    def get_warehouse_stock_summary(self):
        """Get warehouse stock summary with company, product, quantity, and warehouse"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT 
                c.company_name,
                p.product_name,
                SUM(ws.quantity_mt) as total_quantity,
                w.warehouse_name,
                c.company_id,
                p.product_id,
                w.warehouse_id
            FROM warehouse_stock ws
            LEFT JOIN companies c ON ws.company_id = c.company_id
            LEFT JOIN products p ON ws.product_id = p.product_id
            LEFT JOIN warehouses w ON ws.warehouse_id = w.warehouse_id
            WHERE ws.transaction_type = 'IN'
            GROUP BY c.company_id, p.product_id, w.warehouse_id
            ORDER BY c.company_name, p.product_name, w.warehouse_name
        ''')
        summary = cursor.fetchall()
        self.close_connection(conn)
        return summary
    
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
        self.close_connection(conn)
        
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
        self.close_connection(conn)
        return transactions
    
    # ========== E-Bill Operations (Accountant) ==========
    
    def add_ebill(self, builty_id, ebill_number, amount, generated_date, bill_pdf=None, eway_bill_pdf=None):
        """Add new e-bill"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO ebills (builty_id, ebill_number, amount, generated_date, bill_pdf, eway_bill_pdf)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (builty_id, ebill_number, amount, generated_date, bill_pdf, eway_bill_pdf))
            
            ebill_id = cursor.lastrowid
            conn.commit()
            return ebill_id
        except Exception as e:
            print(f"Error adding e-bill: {e}")
            conn.rollback()
            return None
        finally:
            self.close_connection(conn)
    
    def get_all_ebills(self):
        """Get all e-bills with complete builty details"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT e.ebill_id, e.ebill_number, e.amount, e.generated_date, 
                   e.eway_bill_pdf, e.created_at,
                   b.builty_number, b.goods_name, b.quantity_mt, b.lr_number,
                   t.truck_number,
                   COALESCE(a.account_name, 'N/A') as account_name,
                   e.bill_pdf, b.builty_id, b.created_by_role
            FROM ebills e
            LEFT JOIN builty b ON e.builty_id = b.builty_id
            LEFT JOIN trucks t ON b.truck_id = t.truck_id
            LEFT JOIN accounts a ON b.account_id = a.account_id
            ORDER BY e.created_at DESC
        ''')
        ebills = cursor.fetchall()
        self.close_connection(conn)
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
        self.close_connection(conn)
        return builties
    
    def get_ebills_by_builty_creator(self, created_by_role):
        """Get e-bills for builties created by a specific role"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT e.ebill_id, e.ebill_number, e.amount, e.generated_date, 
                   e.eway_bill_pdf, e.created_at,
                   b.builty_number, b.goods_name, b.quantity_mt, b.lr_number,
                   t.truck_number,
                   COALESCE(a.account_name, 'N/A') as account_name,
                   e.bill_pdf, b.builty_id, b.created_by_role
            FROM ebills e
            LEFT JOIN builty b ON e.builty_id = b.builty_id
            LEFT JOIN trucks t ON b.truck_id = t.truck_id
            LEFT JOIN accounts a ON b.account_id = a.account_id
            WHERE b.created_by_role = ?
            ORDER BY e.created_at DESC
        ''', (created_by_role,))
        ebills = cursor.fetchall()
        self.close_connection(conn)
        return ebills
    
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
        
        self.close_connection(conn)
        
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
        self.close_connection(conn)
        return summary
    
    # ========== Logistic Bill Operations ==========
    
    def get_rake_transport_data(self, rake_code):
        """Get transport data for rake bill - dispatches grouped by destination type with distances"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        result = []
        
        try:
            # Get dispatches to warehouses
            cursor.execute('''
                SELECT 'Warehouse' as dest_type, w.warehouse_name as dest_name, w.warehouse_id as dest_id,
                       SUM(ls.quantity_mt) as total_qty, COALESCE(w.distance, 0) as distance
                FROM loading_slips ls
                JOIN warehouses w ON ls.warehouse_id = w.warehouse_id
                WHERE ls.rake_code = ? AND ls.warehouse_id IS NOT NULL
                GROUP BY w.warehouse_id, w.warehouse_name
            ''', (rake_code,))
            warehouses = cursor.fetchall()
            
            for row in warehouses:
                result.append({'dest_type': row[0], 'dest_name': row[1], 'dest_id': row[2], 
                              'quantity': row[3] or 0, 'distance': row[4] or 0})
        except Exception as e:
            print(f"Error fetching warehouse data: {e}")
        
        try:
            # Get dispatches to accounts (Dealers, Retailers, Payal)
            cursor.execute('''
                SELECT a.account_type as dest_type, a.account_name as dest_name, a.account_id as dest_id,
                       SUM(ls.quantity_mt) as total_qty, COALESCE(a.distance, 0) as distance
                FROM loading_slips ls
                JOIN accounts a ON ls.account_id = a.account_id
                WHERE ls.rake_code = ? AND ls.account_id IS NOT NULL
                GROUP BY a.account_id, a.account_type, a.account_name
            ''', (rake_code,))
            accounts = cursor.fetchall()
            
            for row in accounts:
                result.append({'dest_type': row[0], 'dest_name': row[1], 'dest_id': row[2], 
                              'quantity': row[3] or 0, 'distance': row[4] or 0})
        except Exception as e:
            print(f"Error fetching account data: {e}")
        
        try:
            # Get dispatches to CGMF
            cursor.execute('''
                SELECT 'CGMF' as dest_type, c.society_name || ' - ' || c.destination as dest_name, c.cgmf_id as dest_id,
                       SUM(ls.quantity_mt) as total_qty, COALESCE(c.distance, 0) as distance
                FROM loading_slips ls
                JOIN cgmf c ON ls.cgmf_id = c.cgmf_id
                WHERE ls.rake_code = ? AND ls.cgmf_id IS NOT NULL
                GROUP BY c.cgmf_id, c.society_name, c.destination
            ''', (rake_code,))
            cgmf = cursor.fetchall()
            
            for row in cgmf:
                result.append({'dest_type': row[0], 'dest_name': row[1], 'dest_id': row[2], 
                              'quantity': row[3] or 0, 'distance': row[4] or 0})
        except Exception as e:
            print(f"Error fetching CGMF data: {e}")
        
        self.close_connection(conn)
        return result
    
    def get_warehouse_storage_data(self, warehouse_id=None):
        """Get warehouse stock in data for warehouse bill - storage section"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            if warehouse_id:
                cursor.execute('''
                    SELECT ws.date, c.company_name, p.product_name, ws.quantity_mt,
                           ws.stock_id, c.company_id, p.product_id
                    FROM warehouse_stock ws
                    LEFT JOIN companies c ON ws.company_id = c.company_id
                    LEFT JOIN products p ON ws.product_id = p.product_id
                    WHERE ws.transaction_type = 'IN' AND ws.warehouse_id = ?
                    ORDER BY ws.date DESC
                ''', (warehouse_id,))
            else:
                cursor.execute('''
                    SELECT ws.date, c.company_name, p.product_name, ws.quantity_mt,
                           ws.stock_id, c.company_id, p.product_id, w.warehouse_name
                    FROM warehouse_stock ws
                    LEFT JOIN companies c ON ws.company_id = c.company_id
                    LEFT JOIN products p ON ws.product_id = p.product_id
                    LEFT JOIN warehouses w ON ws.warehouse_id = w.warehouse_id
                    WHERE ws.transaction_type = 'IN'
                    ORDER BY ws.date DESC
                ''')
            
            data = cursor.fetchall()
        except Exception as e:
            print(f"Error fetching warehouse storage data: {e}")
            data = []
        
        self.close_connection(conn)
        return data
    
    def get_warehouse_transport_data(self, warehouse_id=None):
        """Get warehouse stock out data for warehouse bill - transportation section (builty-wise)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            if warehouse_id:
                cursor.execute('''
                    SELECT ws.date, t.truck_number, 
                           COALESCE(a.account_name, cg.society_name, 'Direct') as account_name,
                           p.product_name, ws.quantity_mt, 
                           0 as distance,
                           ws.stock_id, b.builty_number
                    FROM warehouse_stock ws
                    LEFT JOIN builty b ON ws.builty_id = b.builty_id
                    LEFT JOIN trucks t ON b.truck_id = t.truck_id
                    LEFT JOIN accounts a ON ws.account_id = a.account_id
                    LEFT JOIN cgmf cg ON ws.cgmf_id = cg.cgmf_id
                    LEFT JOIN products p ON ws.product_id = p.product_id
                    WHERE ws.transaction_type = 'OUT' AND ws.warehouse_id = ?
                    ORDER BY ws.date DESC
                ''', (warehouse_id,))
            else:
                cursor.execute('''
                    SELECT ws.date, t.truck_number, 
                           COALESCE(a.account_name, cg.society_name, 'Direct') as account_name,
                           p.product_name, ws.quantity_mt, 
                           0 as distance,
                           ws.stock_id, b.builty_number, w.warehouse_name
                    FROM warehouse_stock ws
                    LEFT JOIN builty b ON ws.builty_id = b.builty_id
                    LEFT JOIN trucks t ON b.truck_id = t.truck_id
                    LEFT JOIN accounts a ON ws.account_id = a.account_id
                    LEFT JOIN cgmf cg ON ws.cgmf_id = cg.cgmf_id
                    LEFT JOIN products p ON ws.product_id = p.product_id
                    LEFT JOIN warehouses w ON ws.warehouse_id = w.warehouse_id
                    WHERE ws.transaction_type = 'OUT'
                    ORDER BY ws.date DESC
                ''')
            
            data = cursor.fetchall()
        except Exception as e:
            print(f"Error fetching warehouse transport data: {e}")
            data = []
        
        self.close_connection(conn)
        return data
    
    # Rake Bill Payment functions
    def save_rake_bill_payment(self, rake_code, total_bill_amount, received_amount, username):
        """Save or update rake bill payment information"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            remaining_amount = total_bill_amount - received_amount
            cursor.execute('''
                INSERT INTO rake_bill_payments (rake_code, total_bill_amount, received_amount, remaining_amount, updated_by, last_updated)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(rake_code) DO UPDATE SET
                    total_bill_amount = excluded.total_bill_amount,
                    received_amount = excluded.received_amount,
                    remaining_amount = excluded.remaining_amount,
                    updated_by = excluded.updated_by,
                    last_updated = CURRENT_TIMESTAMP
            ''', (rake_code, total_bill_amount, received_amount, remaining_amount, username))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error saving rake bill payment: {e}")
            conn.rollback()
            return False
        finally:
            self.close_connection(conn)
    
    def get_rake_bill_payment(self, rake_code):
        """Get rake bill payment information"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT rake_code, total_bill_amount, received_amount, remaining_amount, last_updated, updated_by
            FROM rake_bill_payments
            WHERE rake_code = ?
        ''', (rake_code,))
        result = cursor.fetchone()
        self.close_connection(conn)
        if result:
            return {
                'rake_code': result[0],
                'total_bill_amount': result[1],
                'received_amount': result[2],
                'remaining_amount': result[3],
                'last_updated': result[4],
                'updated_by': result[5]
            }
        return None
    
    def get_all_rake_bill_payments(self):
        """Get all rake bill payment records"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT rake_code, total_bill_amount, received_amount, remaining_amount, last_updated, updated_by
            FROM rake_bill_payments
            ORDER BY last_updated DESC
        ''')
        results = cursor.fetchall()
        self.close_connection(conn)
        payments = []
        for row in results:
            payments.append({
                'rake_code': row[0],
                'total_bill_amount': row[1],
                'received_amount': row[2],
                'remaining_amount': row[3],
                'last_updated': row[4],
                'updated_by': row[5]
            })
        return payments
