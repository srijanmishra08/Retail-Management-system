"""
Database module for FIMS - Supabase/PostgreSQL backend
Drop-in replacement for database.py (Turso/SQLite).
All tuple column indices intentionally preserved to avoid any app.py changes.

Required env var: DATABASE_URL  (Supabase direct connection string)
  e.g. postgresql://postgres:[password]@db.[ref].supabase.co:5432/postgres
"""

import os
import time
from datetime import datetime, date, timedelta
from werkzeug.security import generate_password_hash, check_password_hash

import psycopg2
import psycopg2.extensions


# ---------------------------------------------------------------------------
# Simple in-memory cache with TTL
# ---------------------------------------------------------------------------
class SimpleCache:
    def __init__(self, ttl=30):
        self._cache = {}
        self._ttl = ttl

    def get(self, key):
        if key in self._cache:
            value, ts = self._cache[key]
            if time.time() - ts < self._ttl:
                return value
            del self._cache[key]
        return None

    def set(self, key, value):
        self._cache[key] = (value, time.time())

    def clear(self):
        self._cache.clear()

    def delete(self, key):
        self._cache.pop(key, None)


_cache = SimpleCache(ttl=300)


# ---------------------------------------------------------------------------
# Explicit column projections (preserve original tuple index order for app.py)
# ---------------------------------------------------------------------------
_RAKE_COLS = """
    id            AS rake_id,
    rake_code,
    company_name,
    company_code,
    date,
    rr_quantity,
    product_name,
    product_code,
    rake_point_name,
    head          AS builty_head,
    is_closed,
    closed_at,
    shortage,
    created_at
"""

_ACCOUNT_COLS = """
    id            AS account_id,
    account_name,
    account_type,
    contact,
    address,
    distance,
    created_at
"""

_WAREHOUSE_COLS = """
    id            AS warehouse_id,
    warehouse_name,
    location,
    capacity,
    distance,
    created_at
"""

_TRUCK_COLS = """
    id            AS truck_id,
    truck_number,
    driver_name,
    driver_mobile,
    owner_name,
    owner_mobile,
    created_at
"""

_BUILTY_COLS = """
    id            AS builty_id,
    builty_number,
    rake_code,
    date,
    rake_point_name,
    account_id,
    warehouse_id,
    cgmf_id,
    truck_id,
    loading_point,
    unloading_point,
    goods_name,
    number_of_bags,
    quantity_mt,
    kg_per_bag,
    rate_per_mt,
    total_freight,
    advance,
    to_pay,
    lr_number,
    lr_index,
    created_by_role,
    sub_head,
    receiver_name,
    received_quantity,
    created_at
"""

_SLIP_COLS = """
    id                    AS slip_id,
    rake_code,
    slip_number,
    loading_point_name,
    destination,
    account_id,
    warehouse_id,
    cgmf_id,
    quantity_bags,
    quantity_mt,
    truck_id,
    wagon_number,
    goods_name,
    truck_driver,
    truck_owner,
    mobile_number_1,
    mobile_number_2,
    truck_details,
    builty_id,
    sub_head,
    warehouse_account_id,
    warehouse_account_type,
    created_at
"""

_STOCK_COLS = """
    ws.id            AS stock_id,
    ws.serial_number,
    ws.warehouse_id,
    ws.builty_id,
    ws.company_id,
    ws.product_id,
    ws.transaction_type,
    ws.quantity_mt,
    ws.employee_id,
    ws.account_id,
    ws.cgmf_id,
    ws.account_type,
    ws.dealer_name,
    ws.source_type,
    ws.truck_id,
    ws.date,
    ws.notes,
    ws.remark,
    ws.sub_head,
    ws.created_at
"""

_CGMF_COLS = """
    id            AS cgmf_id,
    district,
    destination,
    society_name,
    contact,
    distance,
    created_at
"""

_PRODUCT_COLS = """
    id            AS product_id,
    product_name,
    product_code,
    product_type,
    unit,
    unit_per_bag,
    unit_type,
    description,
    created_at
"""

_COMPANY_COLS = """
    id            AS company_id,
    company_name,
    company_code,
    contact_person,
    mobile,
    address,
    distance,
    created_at
"""

_EMPLOYEE_COLS = """
    id            AS employee_id,
    employee_name,
    employee_code,
    mobile,
    designation,
    created_at
"""


# ---------------------------------------------------------------------------
# Database class
# ---------------------------------------------------------------------------
class Database:
    _pg_conn = None
    _initialized = False

    def __init__(self, db_name='fims.db'):
        self.db_name = db_name
        self.database_url = (
            os.environ.get('DATABASE_URL') or
            os.environ.get('SUPABASE_DB_URL')
        )
        if self.database_url:
            print("Using Supabase PostgreSQL Database")
        else:
            print("WARNING: DATABASE_URL not set")

    @property
    def use_cloud(self):
        return bool(self.database_url)

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------
    @classmethod
    def reset_cloud_connection(cls):
        if cls._pg_conn is not None:
            try:
                cls._pg_conn.close()
            except Exception:
                pass
            cls._pg_conn = None

    _last_check = 0

    def get_connection(self):
        if not self.database_url:
            raise RuntimeError("DATABASE_URL not set. Cannot connect to Supabase.")

        conn = Database._pg_conn
        need_new = conn is None or conn.closed != 0

        # Periodically verify the connection is still alive (pooler may drop idle ones)
        if not need_new:
            try:
                if conn.info.transaction_status == psycopg2.extensions.TRANSACTION_STATUS_INERROR:
                    conn.rollback()
                # Ping only if last check was >30s ago to avoid round-trip on every call
                now = time.time()
                if now - Database._last_check > 30:
                    cur = conn.cursor()
                    cur.execute("SELECT 1")
                    cur.close()
                    Database._last_check = now
            except (psycopg2.OperationalError, psycopg2.DatabaseError):
                try:
                    conn.close()
                except Exception:
                    pass
                Database._pg_conn = None
                need_new = True

        if need_new:
            for attempt in range(3):
                try:
                    Database._pg_conn = psycopg2.connect(self.database_url, connect_timeout=10)
                    Database._pg_conn.autocommit = True
                    Database._last_check = time.time()
                    return Database._pg_conn
                except psycopg2.OperationalError:
                    if attempt < 2:
                        time.sleep(1 * (attempt + 1))
                    else:
                        raise

        return Database._pg_conn

    def close_connection(self, conn):
        # psycopg2 connection is reused — never close it here
        pass

    def invalidate_cache(self):
        _cache.clear()

    def _rows(self, cursor):
        return [tuple(row) for row in cursor.fetchall()]

    def execute_custom_query(self, query, params=None, _retry=True):
        """Execute a raw SQL query. Accepts ? or %s placeholders."""
        query = query.replace('?', '%s')
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(query, params or ())
            if query.strip().upper().startswith('SELECT'):
                return self._rows(cursor)
            else:
                conn.commit()
                return cursor.rowcount
        except Exception as e:
            print(f"Error executing query: {e}")
            try:
                conn.rollback()
            except Exception:
                Database.reset_cloud_connection()
            if _retry:
                return self.execute_custom_query(query, params, _retry=False)
            return None

    # ------------------------------------------------------------------
    # Schema initialisation
    # ------------------------------------------------------------------
    def initialize_database(self):
        if Database._initialized:
            return

        try:
            conn = self.get_connection()
        except Exception as e:
            print(f"WARNING: Could not connect to database during init: {e}")
            print("App will retry connection on first request.")
            return

        cursor = conn.cursor()
        try:
            conn.autocommit = False
            # Standalone users table for Flask-Login (separate from Supabase Auth)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id       SERIAL PRIMARY KEY,
                    username      TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    role          TEXT NOT NULL,
                    created_at    TIMESTAMPTZ DEFAULT NOW()
                )
            ''')
            cursor.execute("SELECT COUNT(*) FROM users")
            if cursor.fetchone()[0] == 0:
                default_users = [
                    ('admin',      generate_password_hash('admin123'),      'admin'),
                    ('rakepoint',  generate_password_hash('rake123'),       'rakepoint'),
                    ('warehouse',  generate_password_hash('warehouse123'),  'warehouse'),
                    ('accountant', generate_password_hash('account123'),    'accountant'),
                ]
                cursor.executemany(
                    'INSERT INTO users (username, password_hash, role) VALUES (%s, %s, %s)',
                    default_users
                )
            conn.commit()
            conn.autocommit = True
            
            # Ensure supply_term column exists on builty table
            cursor.execute("""
                ALTER TABLE builty ADD COLUMN IF NOT EXISTS supply_term TEXT
            """)
            conn.commit()

            # Ensure loading_slip_products table exists for multi-product warehouse slips
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS loading_slip_products (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    loading_slip_id UUID NOT NULL REFERENCES loading_slips(id) ON DELETE CASCADE,
                    product_id UUID REFERENCES products(id),
                    product_name TEXT NOT NULL,
                    quantity_bags INTEGER NOT NULL DEFAULT 0,
                    quantity_mt NUMERIC(10,2) NOT NULL DEFAULT 0,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                )
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_loading_slip_products_slip_id
                ON loading_slip_products(loading_slip_id)
            """)
            conn.commit()

            # Ensure WAREHOUSE sentinel rake exists for warehouse-created loading slips
            cursor.execute("SELECT 1 FROM rakes WHERE rake_code = 'WAREHOUSE'")
            if not cursor.fetchone():
                cursor.execute("""
                    INSERT INTO rakes (rake_code, company_name, company_code, product_name, product_code,
                                       rr_quantity, rake_point_name, is_closed, date)
                    VALUES ('WAREHOUSE', 'WAREHOUSE', 'WH', 'MISC', 'MISC', 0, 'WAREHOUSE', false, CURRENT_DATE)
                """)
            
            Database._initialized = True
            print("Database initialized successfully (Supabase/PostgreSQL)")
        except Exception as e:
            print(f"Error initializing database: {e}")
            try:
                conn.rollback()
                conn.autocommit = True
            except Exception:
                pass

    # ==================================================================
    # User Operations
    # ==================================================================

    def authenticate_user(self, username, password):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            'SELECT user_id, username, password_hash, role, created_at FROM users WHERE username = %s',
            (username,)
        )
        user = cursor.fetchone()
        if user and check_password_hash(user[2], password):
            return tuple(user)
        return None

    def get_user_by_id(self, user_id, _retry=True):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                'SELECT user_id, username, password_hash, role, created_at FROM users WHERE user_id = %s',
                (user_id,)
            )
            row = cursor.fetchone()
            return tuple(row) if row else None
        except (psycopg2.OperationalError, psycopg2.DatabaseError):
            Database.reset_cloud_connection()
            if _retry:
                return self.get_user_by_id(user_id, _retry=False)
            raise

    def get_all_users(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT user_id, username, role, created_at FROM users')
        return self._rows(cursor)

    # ==================================================================
    # Rake Operations
    # ==================================================================

    def add_rake(self, rake_code, company_name, company_code, date, rr_quantity,
                 product_name, product_code, rake_point_name, builty_head=None, products=None):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            conn.autocommit = False
            cursor.execute('SELECT id FROM rakes WHERE rake_code = %s', (rake_code,))
            if cursor.fetchone():
                conn.rollback()
                conn.autocommit = True
                print(f"Rake code {rake_code} already exists")
                return None

            cursor.execute('''
                INSERT INTO rakes
                    (rake_code, company_name, company_code, date, rr_quantity,
                     product_name, product_code, rake_point_name, head)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            ''', (rake_code, company_name, company_code, date, rr_quantity,
                  product_name, product_code, rake_point_name, builty_head))
            rake_id = cursor.fetchone()[0]

            if products and isinstance(products, list) and len(products) > 0:
                for prod in products:
                    cursor.execute('''
                        INSERT INTO rake_products
                            (rake_code, product_id, product_name, product_code, quantity_mt)
                        VALUES (%s, %s, %s, %s, %s)
                    ''', (rake_code, prod.get('product_id'), prod.get('product_name'),
                          prod.get('product_code'), prod.get('quantity_mt', 0)))
            elif product_name:
                cursor.execute('SELECT id FROM products WHERE product_name = %s', (product_name,))
                pr = cursor.fetchone()
                cursor.execute('''
                    INSERT INTO rake_products
                        (rake_code, product_id, product_name, product_code, quantity_mt)
                    VALUES (%s, %s, %s, %s, %s)
                ''', (rake_code, pr[0] if pr else None, product_name, product_code, rr_quantity))

            conn.commit()
            conn.autocommit = True
            print(f"Rake {rake_code} added with id {rake_id}")
            return rake_id
        except Exception as e:
            print(f"Error adding rake: {e}")
            import traceback; traceback.print_exc()
            try: conn.rollback()
            except Exception: pass
            conn.autocommit = True
            return None

    def update_rake(self, rake_code, company_name, company_code, date, rr_quantity,
                    product_name, product_code, rake_point_name, builty_head=None, products=None):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            conn.autocommit = False
            cursor.execute('''
                UPDATE rakes
                SET company_name=%s, company_code=%s, date=%s, rr_quantity=%s,
                    product_name=%s, product_code=%s, rake_point_name=%s, head=%s
                WHERE rake_code=%s
            ''', (company_name, company_code, date, rr_quantity,
                  product_name, product_code, rake_point_name, builty_head, rake_code))

            if products and isinstance(products, list) and len(products) > 0:
                cursor.execute('DELETE FROM rake_products WHERE rake_code = %s', (rake_code,))
                for prod in products:
                    cursor.execute('''
                        INSERT INTO rake_products
                            (rake_code, product_id, product_name, product_code, quantity_mt)
                        VALUES (%s, %s, %s, %s, %s)
                    ''', (rake_code, prod.get('product_id'), prod.get('product_name'),
                          prod.get('product_code'), prod.get('quantity_mt', 0)))

            conn.commit()
            conn.autocommit = True
            return True
        except Exception as e:
            print(f"Error updating rake: {e}")
            try: conn.rollback()
            except Exception: pass
            conn.autocommit = True
            return False

    def get_rake_products(self, rake_code):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT rp.id AS rake_product_id, rp.product_id, rp.product_name,
                   rp.product_code, rp.quantity_mt, p.unit_per_bag
            FROM rake_products rp
            LEFT JOIN products p ON rp.product_id = p.id
            WHERE rp.rake_code = %s
            ORDER BY rp.created_at
        ''', (rake_code,))
        return self._rows(cursor)

    def get_all_rakes(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(f'SELECT {_RAKE_COLS} FROM rakes ORDER BY created_at DESC')
        return self._rows(cursor)

    def get_active_rakes(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(f'SELECT {_RAKE_COLS} FROM rakes WHERE NOT is_closed ORDER BY created_at DESC')
        return self._rows(cursor)

    def get_rake_by_code(self, rake_code):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(f'SELECT {_RAKE_COLS} FROM rakes WHERE rake_code = %s', (rake_code,))
        row = cursor.fetchone()
        return tuple(row) if row else None

    def get_rake_balance(self, rake_code):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT r.rr_quantity, p.unit_per_bag
            FROM rakes r
            LEFT JOIN products p ON r.product_name = p.product_name
            WHERE r.rake_code = %s
        ''', (rake_code,))
        rake_result = cursor.fetchone()
        if not rake_result:
            return None
        total_quantity = rake_result[0]
        unit_per_bag = rake_result[1] if rake_result[1] else 50.0
        cursor.execute(
            'SELECT COALESCE(SUM(quantity_mt), 0) FROM loading_slips WHERE rake_code = %s',
            (rake_code,)
        )
        dispatched_quantity = cursor.fetchone()[0]
        return {
            'total': total_quantity,
            'dispatched': dispatched_quantity,
            'remaining': total_quantity - dispatched_quantity,
            'unit_per_bag': unit_per_bag
        }

    # ------------------------------------------------------------------
    # Optimised batch query methods
    # ------------------------------------------------------------------

    def get_all_rake_balances(self):
        cache_key = 'all_rake_balances'
        cached = _cache.get(cache_key)
        if cached is not None:
            return cached
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT r.rake_code, r.rr_quantity,
                   COALESCE(SUM(ls.quantity_mt), 0) AS dispatched
            FROM rakes r
            LEFT JOIN loading_slips ls ON r.rake_code = ls.rake_code
            GROUP BY r.rake_code, r.rr_quantity
        ''')
        results = {}
        for row in cursor.fetchall():
            rake_code, rr_quantity, dispatched = row[0], (row[1] or 0), (row[2] or 0)
            results[rake_code] = {
                'rr_quantity': rr_quantity,
                'dispatched': dispatched,
                'remaining': rr_quantity - dispatched
            }
        _cache.set(cache_key, results)
        return results

    def get_all_warehouse_balances(self):
        cache_key = 'all_warehouse_balances'
        cached = _cache.get(cache_key)
        if cached is not None:
            return cached
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT warehouse_id,
                   COALESCE(SUM(CASE WHEN transaction_type='IN'  THEN quantity_mt ELSE 0 END), 0),
                   COALESCE(SUM(CASE WHEN transaction_type='OUT' THEN quantity_mt ELSE 0 END), 0)
            FROM warehouse_stock
            WHERE (source_type IS NULL OR source_type::text != 'allotment')
            GROUP BY warehouse_id
        ''')
        results = {}
        for row in cursor.fetchall():
            wid, si, so = row[0], (row[1] or 0), (row[2] or 0)
            results[wid] = {'stock_in': si, 'stock_out': so, 'balance': si - so}
        _cache.set(cache_key, results)
        return results

    def get_rakes_with_balances(self, limit=None, _retry=True):
        cache_key = f'rakes_with_balances_{limit}'
        cached = _cache.get(cache_key)
        if cached is not None:
            return cached
        conn = self.get_connection()
        cursor = conn.cursor()
        limit_clause = f'LIMIT {int(limit)}' if limit else ''
        try:
            cursor.execute(f'''
                SELECT r.id AS rake_id, r.rake_code, r.company_name, r.company_code,
                       r.date, r.rr_quantity, r.product_name, r.product_code,
                       r.rake_point_name, r.head AS builty_head,
                       r.is_closed, r.closed_at, r.shortage,
                       COALESCE((SELECT SUM(ls.quantity_mt)
                                 FROM loading_slips ls WHERE ls.rake_code = r.rake_code), 0) AS dispatched,
                       COALESCE((SELECT SUM(b.quantity_mt)
                                 FROM builty b WHERE b.rake_code = r.rake_code), 0) AS builty_total
                FROM rakes r
                ORDER BY r.created_at DESC
                {limit_clause}
            ''')
            results = []
            for row in cursor.fetchall():
                rr_quantity  = row[5] or 0
                dispatched   = row[13] or 0
                builty_total = row[14] or 0
                results.append({
                    'rake_id':              row[0],
                    'rake_code':            row[1],
                    'company_name':         row[2],
                    'company_code':         row[3],
                    'date':                 row[4],
                    'rr_quantity':          rr_quantity,
                    'product_name':         row[6],
                    'product_code':         row[7],
                    'rake_point_name':      row[8],
                    'builty_head':          row[9],
                    'is_closed':            row[10] or False,
                    'closed_at':            row[11],
                    'shortage':             row[12] or 0,
                    'dispatched':           dispatched,
                    'builty_total':         builty_total,
                    'trucks_under_loading': dispatched - builty_total,
                    'remaining':            rr_quantity - dispatched,
                })
            _cache.set(cache_key, results)
            return results
        except Exception as e:
            print(f"Error in get_rakes_with_balances: {e}")
            if _retry:
                Database.reset_cloud_connection()
                return self.get_rakes_with_balances(limit, _retry=False)
            return []

    def get_dashboard_stats_optimized(self, _retry=True):
        cache_key = 'admin_dashboard_stats_optimized'
        cached = _cache.get(cache_key)
        if cached is not None:
            return cached
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                SELECT
                    (SELECT COUNT(*) FROM rakes)                                           AS total_rakes,
                    (SELECT COUNT(*) FROM rakes WHERE NOT is_closed OR is_closed IS NULL)  AS active_rakes,
                    (SELECT COUNT(*) FROM builty)                                          AS total_builties,
                    (SELECT COUNT(*) FROM loading_slips)                                   AS total_loading_slips,
                    (SELECT COUNT(*) FROM accounts)                                        AS total_accounts,
                    (SELECT COUNT(*) FROM warehouses)                                      AS total_warehouses,
                    (SELECT COALESCE(SUM(rr_quantity), 0) FROM rakes)                     AS total_stock,
                    (SELECT COALESCE(SUM(quantity_mt), 0) FROM loading_slips)             AS total_dispatched,
                    (SELECT COUNT(*) FROM ebills)                                          AS total_ebills,
                    (SELECT COALESCE(SUM(amount), 0) FROM ebills)                         AS total_ebill_amount
            ''')
            row = cursor.fetchone()
            stats = {
                'total_rakes':         row[0] or 0,
                'active_rakes':        row[1] or 0,
                'total_builties':      row[2] or 0,
                'total_loading_slips': row[3] or 0,
                'total_accounts':      row[4] or 0,
                'total_warehouses':    row[5] or 0,
                'total_stock':         row[6] or 0,
                'total_dispatched':    row[7] or 0,
                'total_ebills':        row[8] or 0,
                'total_ebill_amount':  row[9] or 0,
            }
            _cache.set(cache_key, stats)
            return stats
        except Exception as e:
            print(f"Error in get_dashboard_stats_optimized: {e}")
            if _retry:
                Database.reset_cloud_connection()
                return self.get_dashboard_stats_optimized(_retry=False)
            return {k: 0 for k in ('total_rakes', 'active_rakes', 'total_builties',
                'total_loading_slips', 'total_accounts', 'total_warehouses',
                'total_stock', 'total_dispatched', 'total_ebills', 'total_ebill_amount')}

    def count_active_rakes_optimized(self):
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
                WHERE NOT r.is_closed OR r.is_closed IS NULL
                GROUP BY r.rake_code, r.rr_quantity
                HAVING r.rr_quantity - COALESCE(SUM(ls.quantity_mt), 0) > 0
            ) sub
        ''')
        count = cursor.fetchone()[0] or 0
        _cache.set(cache_key, count)
        return count

    def get_logistic_bill_summary_optimized(self, selected_company='all', selected_rake='all',
                                             date_from='', date_to=''):
        cache_key = f'logistic_bill_{selected_company}_{selected_rake}_{date_from}_{date_to}'
        cached = _cache.get(cache_key)
        if cached is not None:
            return cached
        conn = self.get_connection()
        cursor = conn.cursor()
        conditions = ['1=1']
        params = []
        if selected_company != 'all':
            conditions.append('r.company_name = %s')
            params.append(selected_company)
        if selected_rake != 'all':
            conditions.append('r.rake_code = %s')
            params.append(selected_rake)
        if date_from:
            conditions.append('r.date >= %s')
            params.append(date_from)
        if date_to:
            conditions.append('r.date <= %s')
            params.append(date_to)
        where_clause = ' AND '.join(conditions)
        cursor.execute(f'''
            SELECT r.rake_code, r.company_name, r.rr_quantity, r.date,
                   COALESCE(rbp.total_bill_amount, COALESCE(SUM(b.total_freight), 0)) AS bill_amount,
                   COALESCE(rbp.received_amount, 0) AS received_payment
            FROM rakes r
            LEFT JOIN builty b               ON r.rake_code = b.rake_code
            LEFT JOIN rake_bill_payments rbp ON r.rake_code = rbp.rake_code
            WHERE {where_clause}
            GROUP BY r.rake_code, r.company_name, r.rr_quantity, r.date,
                     rbp.total_bill_amount, rbp.received_amount
            ORDER BY r.date DESC
        ''', tuple(params))
        results = []
        for row in cursor.fetchall():
            results.append({
                'rake_code':        row[0],
                'company_name':     row[1],
                'total_stock':      row[2] or 0,
                'date':             row[3],
                'bill_amount':      row[4] or 0,
                'received_payment': row[5] or 0,
            })
        _cache.set(cache_key, results)
        return results

    def get_warehouse_dashboard_stats(self):
        cache_key = 'warehouse_dashboard_stats'
        cached = _cache.get(cache_key)
        if cached is not None:
            return cached
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT
                (SELECT COUNT(*) FROM accounts) AS account_count,
                (SELECT COUNT(*) FROM builty)   AS builty_count,
                (SELECT COALESCE(SUM(quantity_mt), 0)
                   FROM warehouse_stock
                   WHERE transaction_type = 'IN'
                     AND date = CURRENT_DATE
                     AND (source_type IS NULL OR source_type::text != 'allotment')
                ) AS today_stock_in
        ''')
        row = cursor.fetchone()
        stats = {
            'account_count':   row[0] or 0,
            'builty_count':    row[1] or 0,
            'today_stock_in':  row[2] or 0,
        }
        _cache.set(cache_key, stats)
        return stats

    def get_recent_warehouse_movements(self, limit=10):
        cache_key = f'recent_warehouse_movements_{limit}'
        cached = _cache.get(cache_key)
        if cached is not None:
            return cached
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT ws.date, ws.transaction_type, b.builty_number, w.warehouse_name, ws.quantity_mt
            FROM warehouse_stock ws
            LEFT JOIN builty     b ON ws.builty_id    = b.id
            JOIN  warehouses     w ON ws.warehouse_id = w.id
            WHERE (ws.source_type IS NULL OR ws.source_type::text != 'allotment')
            ORDER BY ws.date DESC, ws.created_at DESC
            LIMIT %s
        ''', (limit,))
        results = self._rows(cursor)
        _cache.set(cache_key, results)
        return results

    # ------------------------------------------------------------------
    # Rake status
    # ------------------------------------------------------------------

    def close_rake(self, rake_code):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('SELECT rr_quantity FROM rakes WHERE rake_code = %s', (rake_code,))
            rake_result = cursor.fetchone()
            if not rake_result:
                return False, "Rake not found"
            cursor.execute(
                'SELECT COALESCE(SUM(quantity_mt), 0) FROM loading_slips WHERE rake_code = %s',
                (rake_code,)
            )
            shortage = rake_result[0] - cursor.fetchone()[0]
            cursor.execute('''
                UPDATE rakes SET is_closed=TRUE, closed_at=NOW(), shortage=%s
                WHERE rake_code=%s
            ''', (shortage, rake_code))
            conn.commit()
            self.invalidate_cache()
            return True, shortage
        except Exception as e:
            try: conn.rollback()
            except Exception: pass
            return False, str(e)

    def reopen_rake(self, rake_code):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('SELECT is_closed FROM rakes WHERE rake_code = %s', (rake_code,))
            result = cursor.fetchone()
            if not result:
                return False, "Rake not found"
            if not result[0]:
                return False, "Rake is not closed"
            cursor.execute('''
                UPDATE rakes SET is_closed=FALSE, closed_at=NULL, shortage=0
                WHERE rake_code=%s
            ''', (rake_code,))
            conn.commit()
            self.invalidate_cache()
            return True, "Rake reopened successfully"
        except Exception as e:
            try: conn.rollback()
            except Exception: pass
            return False, str(e)

    def get_total_shortage(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT COALESCE(SUM(shortage), 0) FROM rakes WHERE is_closed=TRUE')
        return cursor.fetchone()[0]

    def get_daywise_warehouse_stock(self, days=7, _retry=True):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cutoff = date.today() - timedelta(days=days)
            cursor.execute('''
                SELECT created_at::date AS day,
                       SUM(CASE WHEN transaction_type='IN'  THEN quantity_mt ELSE 0 END),
                       SUM(CASE WHEN transaction_type='OUT' THEN quantity_mt ELSE 0 END)
                FROM warehouse_stock
                WHERE created_at::date >= %s
                  AND (source_type IS NULL OR source_type::text != 'allotment')
                GROUP BY created_at::date
                ORDER BY created_at::date DESC
            ''', (cutoff,))
            rows = cursor.fetchall()
            db_data = {str(row[0]): {'stock_in': row[1] or 0, 'stock_out': row[2] or 0}
                       for row in rows}
            result = []
            today = date.today()
            for i in range(days):
                d_str = (today - timedelta(days=i)).isoformat()
                entry = db_data.get(d_str, {'stock_in': 0, 'stock_out': 0})
                result.append({'date': d_str, **entry})
            return result
        except Exception as e:
            print(f"Error in get_daywise_warehouse_stock: {e}")
            if _retry:
                Database.reset_cloud_connection()
                return self.get_daywise_warehouse_stock(days, _retry=False)
            return []

    def get_closed_rakes(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(f'SELECT {_RAKE_COLS} FROM rakes WHERE is_closed=TRUE ORDER BY closed_at DESC')
        return self._rows(cursor)

    def get_next_serial_number_for_rake(self, rake_code):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            'SELECT COALESCE(MAX(slip_number), 0) + 1 FROM loading_slips WHERE rake_code = %s',
            (rake_code,)
        )
        return cursor.fetchone()[0]

    def get_next_lr_number(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT MAX(lr_number::integer)
            FROM builty
            WHERE lr_number IS NOT NULL
              AND lr_number != ''
              AND lr_number ~ '^[0-9]+$'
        """)
        result = cursor.fetchone()[0]
        return str(int(result) + 1) if result else '1001'

    def get_next_warehouse_stock_serial(self, warehouse_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            'SELECT MAX(serial_number) FROM warehouse_stock WHERE warehouse_id = %s',
            (warehouse_id,)
        )
        result = cursor.fetchone()[0]
        return int(result) + 1 if result else 1

    # ==================================================================
    # Account Operations
    # ==================================================================

    def add_account(self, account_name, account_type, contact, address, distance=0):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO accounts (account_name, account_type, contact, address, distance)
                VALUES (%s, %s, %s, %s, %s) RETURNING id
            ''', (account_name, account_type, contact, address, distance))
            account_id = cursor.fetchone()[0]
            conn.commit()
            return account_id
        except Exception as e:
            print(f"Error adding account: {e}")
            try: conn.rollback()
            except Exception: pass
            return None

    def delete_account(self, account_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            for tbl, col, msg in [
                ('builty',          'account_id', 'builties'),
                ('loading_slips',   'account_id', 'loading slips'),
                ('warehouse_stock', 'account_id', 'warehouse stock records'),
            ]:
                cursor.execute(f'SELECT COUNT(*) FROM {tbl} WHERE {col} = %s', (account_id,))
                if cursor.fetchone()[0] > 0:
                    return False, f"Account is used in {msg} and cannot be deleted"
            cursor.execute('DELETE FROM accounts WHERE id = %s', (account_id,))
            conn.commit()
            return True, "Account deleted successfully"
        except Exception as e:
            try: conn.rollback()
            except Exception: pass
            return False, str(e)

    def get_all_accounts(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(f'SELECT {_ACCOUNT_COLS} FROM accounts ORDER BY account_name')
        return self._rows(cursor)

    def get_accounts_by_type(self, account_type):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            f'SELECT {_ACCOUNT_COLS} FROM accounts WHERE account_type = %s ORDER BY account_name',
            (account_type,)
        )
        return self._rows(cursor)

    def get_account_by_id(self, account_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(f'SELECT {_ACCOUNT_COLS} FROM accounts WHERE id = %s', (account_id,))
        row = cursor.fetchone()
        return tuple(row) if row else None

    def update_account(self, account_id, account_name, account_type, contact, address, distance=0):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                UPDATE accounts
                SET account_name=%s, account_type=%s, contact=%s, address=%s, distance=%s
                WHERE id=%s
            ''', (account_name, account_type, contact, address, distance, account_id))
            conn.commit()
            return True, "Account updated successfully"
        except Exception as e:
            try: conn.rollback()
            except Exception: pass
            return False, str(e)

    def update_company(self, company_id, company_name, company_code, contact_person,
                       mobile, address, distance=0):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                UPDATE companies
                SET company_name=%s, company_code=%s, contact_person=%s,
                    mobile=%s, address=%s, distance=%s
                WHERE id=%s
            ''', (company_name, company_code, contact_person, mobile, address, distance, company_id))
            conn.commit()
            return True, "Company updated successfully"
        except Exception as e:
            try: conn.rollback()
            except Exception: pass
            return False, str(e)

    def update_employee(self, employee_id, employee_name, employee_code, mobile, designation):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                UPDATE employees
                SET employee_name=%s, employee_code=%s, mobile=%s, designation=%s
                WHERE id=%s
            ''', (employee_name, employee_code, mobile, designation, employee_id))
            conn.commit()
            return True, "Employee updated successfully"
        except Exception as e:
            try: conn.rollback()
            except Exception: pass
            return False, str(e)

    def update_cgmf(self, cgmf_id, district, destination, society_name, contact, distance=0):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                UPDATE cgmf
                SET district=%s, destination=%s, society_name=%s, contact=%s, distance=%s
                WHERE id=%s
            ''', (district, destination, society_name, contact, distance, cgmf_id))
            conn.commit()
            return True, "CGMF updated successfully"
        except Exception as e:
            try: conn.rollback()
            except Exception: pass
            return False, str(e)

    # ==================================================================
    # Product Operations
    # ==================================================================

    def add_product(self, product_name, product_code, product_type='Fertilizer', unit='MT',
                    unit_per_bag=50.0, unit_type='kg', description=''):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO products
                    (product_name, product_code, product_type, unit, unit_per_bag, unit_type, description)
                VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id
            ''', (product_name, product_code, product_type, unit, unit_per_bag, unit_type, description))
            product_id = cursor.fetchone()[0]
            conn.commit()
            return product_id
        except Exception as e:
            print(f"Error adding product: {e}")
            try: conn.rollback()
            except Exception: pass
            return None

    def get_all_products(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(f'SELECT {_PRODUCT_COLS} FROM products ORDER BY product_name')
        return self._rows(cursor)

    def get_product_by_name(self, product_name):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            f'SELECT {_PRODUCT_COLS} FROM products WHERE product_name = %s',
            (product_name,)
        )
        row = cursor.fetchone()
        return tuple(row) if row else None

    # ==================================================================
    # Company Operations
    # ==================================================================

    def add_company(self, company_name, company_code='', contact_person='',
                    mobile='', address='', distance=0):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO companies
                    (company_name, company_code, contact_person, mobile, address, distance)
                VALUES (%s, %s, %s, %s, %s, %s) RETURNING id
            ''', (company_name, company_code, contact_person, mobile, address, distance))
            company_id = cursor.fetchone()[0]
            conn.commit()
            return company_id
        except Exception as e:
            print(f"Error adding company: {e}")
            try: conn.rollback()
            except Exception: pass
            return None

    def get_all_companies(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(f'SELECT {_COMPANY_COLS} FROM companies ORDER BY company_name')
        return self._rows(cursor)

    def get_company_by_id(self, company_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(f'SELECT {_COMPANY_COLS} FROM companies WHERE id = %s', (company_id,))
        row = cursor.fetchone()
        return tuple(row) if row else None

    # ==================================================================
    # Employee Operations
    # ==================================================================

    def add_employee(self, employee_name, employee_code='', mobile='', designation=''):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO employees (employee_name, employee_code, mobile, designation)
                VALUES (%s, %s, %s, %s) RETURNING id
            ''', (employee_name, employee_code, mobile, designation))
            employee_id = cursor.fetchone()[0]
            conn.commit()
            return employee_id
        except Exception as e:
            print(f"Error adding employee: {e}")
            try: conn.rollback()
            except Exception: pass
            return None

    def get_all_employees(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(f'SELECT {_EMPLOYEE_COLS} FROM employees ORDER BY employee_name')
        return self._rows(cursor)

    def get_employee_by_id(self, employee_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(f'SELECT {_EMPLOYEE_COLS} FROM employees WHERE id = %s', (employee_id,))
        row = cursor.fetchone()
        return tuple(row) if row else None

    # ==================================================================
    # CGMF Operations
    # ==================================================================

    def add_cgmf(self, district, destination, society_name, contact='', distance=0):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO cgmf (district, destination, society_name, contact, distance)
                VALUES (%s, %s, %s, %s, %s) RETURNING id
            ''', (district, destination, society_name, contact, distance))
            cgmf_id = cursor.fetchone()[0]
            conn.commit()
            return cgmf_id
        except Exception as e:
            print(f"Error adding CGMF: {e}")
            try: conn.rollback()
            except Exception: pass
            return None

    def get_all_cgmf(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(f'SELECT {_CGMF_COLS} FROM cgmf ORDER BY district, society_name')
        return self._rows(cursor)

    def get_cgmf_by_id(self, cgmf_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(f'SELECT {_CGMF_COLS} FROM cgmf WHERE id = %s', (cgmf_id,))
        row = cursor.fetchone()
        return tuple(row) if row else None

    # ==================================================================
    # Warehouse Operations
    # ==================================================================

    def get_all_warehouses(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(f'SELECT {_WAREHOUSE_COLS} FROM warehouses')
        return self._rows(cursor)

    def get_warehouse_by_id(self, warehouse_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(f'SELECT {_WAREHOUSE_COLS} FROM warehouses WHERE id = %s', (warehouse_id,))
        row = cursor.fetchone()
        return tuple(row) if row else None

    def add_warehouse(self, warehouse_name, location, capacity, distance=0):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO warehouses (warehouse_name, location, capacity, distance)
                VALUES (%s, %s, %s, %s) RETURNING id
            ''', (warehouse_name, location, capacity, distance))
            warehouse_id = cursor.fetchone()[0]
            conn.commit()
            return warehouse_id
        except Exception as e:
            print(f"Error adding warehouse: {e}")
            try: conn.rollback()
            except Exception: pass
            return None

    def update_warehouse(self, warehouse_id, warehouse_name, location, capacity):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                UPDATE warehouses SET warehouse_name=%s, location=%s, capacity=%s
                WHERE id=%s
            ''', (warehouse_name, location, capacity, warehouse_id))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error updating warehouse: {e}")
            try: conn.rollback()
            except Exception: pass
            return False

    def delete_warehouse(self, warehouse_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            for tbl, col, msg in [
                ('builty',          'warehouse_id', 'builties'),
                ('loading_slips',   'warehouse_id', 'loading slips'),
                ('warehouse_stock', 'warehouse_id', 'stock entries'),
            ]:
                cursor.execute(f'SELECT COUNT(*) FROM {tbl} WHERE {col} = %s', (warehouse_id,))
                if cursor.fetchone()[0] > 0:
                    return False, f"Warehouse has {msg} and cannot be deleted"
            cursor.execute('DELETE FROM warehouses WHERE id = %s', (warehouse_id,))
            conn.commit()
            return True, "Warehouse deleted successfully"
        except Exception as e:
            try: conn.rollback()
            except Exception: pass
            return False, str(e)

    # ==================================================================
    # Truck Operations
    # ==================================================================

    def add_truck(self, truck_number, driver_name, driver_mobile, owner_name, owner_mobile):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO trucks (truck_number, driver_name, driver_mobile, owner_name, owner_mobile)
                VALUES (%s, %s, %s, %s, %s) RETURNING id
            ''', (truck_number, driver_name, driver_mobile, owner_name, owner_mobile))
            truck_id = cursor.fetchone()[0]
            conn.commit()
            return truck_id
        except Exception as e:
            print(f"Error adding truck: {e}")
            try: conn.rollback()
            except Exception: pass
            return None

    def get_all_trucks(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(f'SELECT {_TRUCK_COLS} FROM trucks ORDER BY truck_number')
        return self._rows(cursor)

    def get_truck_by_number(self, truck_number):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            f'SELECT {_TRUCK_COLS} FROM trucks WHERE truck_number = %s',
            (truck_number,)
        )
        row = cursor.fetchone()
        return tuple(row) if row else None

    # ==================================================================
    # Builty Operations
    # ==================================================================

    def add_builty(self, builty_number, rake_code, date, rake_point_name, account_id,
                   warehouse_id, truck_id, loading_point, unloading_point, goods_name,
                   number_of_bags, quantity_mt, kg_per_bag, rate_per_mt, total_freight,
                   advance=0, to_pay=0, lr_number='', lr_index=0, created_by_role='',
                   cgmf_id=None, sub_head=None, receiver_name=None, received_quantity=None,
                   supply_term=None):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO builty
                    (builty_number, rake_code, date, rake_point_name,
                     account_id, warehouse_id, cgmf_id, truck_id,
                     loading_point, unloading_point, goods_name, number_of_bags,
                     quantity_mt, kg_per_bag, rate_per_mt, total_freight,
                     advance, to_pay, lr_number, lr_index,
                     created_by_role, sub_head, receiver_name, received_quantity,
                     supply_term)
                VALUES (%s,%s,%s,%s, %s,%s,%s,%s, %s,%s,%s,%s,
                        %s,%s,%s,%s, %s,%s,%s,%s, %s,%s,%s,%s, %s)
                RETURNING id
            ''', (builty_number, rake_code, date, rake_point_name,
                  account_id, warehouse_id, cgmf_id, truck_id,
                  loading_point, unloading_point, goods_name, number_of_bags,
                  quantity_mt, kg_per_bag, rate_per_mt, total_freight,
                  advance, to_pay, lr_number, lr_index,
                  created_by_role, sub_head, receiver_name, received_quantity,
                  supply_term))
            builty_id = cursor.fetchone()[0]
            conn.commit()
            self.invalidate_cache()
            return builty_id
        except Exception as e:
            print(f"Error adding builty: {e}")
            try: conn.rollback()
            except Exception: pass
            return None

    def get_all_builties(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT b.id AS builty_id, b.builty_number, b.rake_code, b.date, b.rake_point_name,
                   b.account_id, b.warehouse_id, b.cgmf_id, b.truck_id,
                   b.loading_point, b.unloading_point, b.goods_name, b.number_of_bags,
                   b.quantity_mt, b.kg_per_bag, b.rate_per_mt, b.total_freight,
                   b.advance, b.to_pay, b.lr_number, b.lr_index, b.created_by_role,
                   b.sub_head, b.receiver_name, b.received_quantity, b.created_at,
                   a.account_name, w.warehouse_name, t.truck_number,
                   c.society_name AS cgmf_name, c.district AS cgmf_district,
                   b.rake_code, b.account_id, b.warehouse_id, b.cgmf_id
            FROM builty b
            LEFT JOIN accounts   a  ON b.account_id  = a.id
            LEFT JOIN warehouses w  ON b.warehouse_id = w.id
            LEFT JOIN trucks     t  ON b.truck_id     = t.id
            LEFT JOIN cgmf       c  ON b.cgmf_id      = c.id
            ORDER BY b.created_at DESC
        ''')
        return self._rows(cursor)

    def get_warehouse_builties(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT b.id AS builty_id, b.builty_number, b.rake_code, b.date, b.rake_point_name,
                   b.account_id, b.warehouse_id, b.cgmf_id, b.truck_id,
                   b.loading_point, b.unloading_point, b.goods_name, b.number_of_bags,
                   b.quantity_mt, b.kg_per_bag, b.rate_per_mt, b.total_freight,
                   b.advance, b.to_pay, b.lr_number, b.lr_index, b.created_by_role,
                   b.sub_head, b.receiver_name, b.received_quantity, b.created_at,
                   a.account_name, w.warehouse_name, t.truck_number
            FROM builty b
            LEFT JOIN accounts   a  ON b.account_id  = a.id
            LEFT JOIN warehouses w  ON b.warehouse_id = w.id
            LEFT JOIN trucks     t  ON b.truck_id     = t.id
            WHERE b.warehouse_id IS NOT NULL
            ORDER BY b.created_at DESC
        ''')
        return self._rows(cursor)

    def get_builty_by_id(self, builty_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        # Indices: [0]=builty_id [1]=builty_number [2]=rake_code [3]=date [4]=rake_point_name
        # [5]=account_id [6]=warehouse_id [7]=cgmf_id [8]=truck_id
        # [9]=loading_point [10]=unloading_point [11]=goods_name [12]=number_of_bags
        # [13]=quantity_mt [14]=kg_per_bag [15]=rate_per_mt [16]=total_freight
        # [17]=advance [18]=to_pay [19]=lr_number [20]=lr_index [21]=created_by_role [22]=created_at
        # [23]=account_name [24]=warehouse_name [25]=truck_number
        # [26]=driver_name [27]=driver_mobile [28]=owner_name [29]=owner_mobile
        # [30]=builty_head [31]=receiver_name [32]=received_quantity
        # [33]=account_address [34]=company_name [35]=company_code [36]=account_type [37]=sub_head
        cursor.execute('''
            SELECT b.id AS builty_id, b.builty_number, b.rake_code, b.date, b.rake_point_name,
                   b.account_id, b.warehouse_id, b.cgmf_id, b.truck_id,
                   b.loading_point, b.unloading_point, b.goods_name, b.number_of_bags,
                   b.quantity_mt, b.kg_per_bag, b.rate_per_mt, b.total_freight,
                   b.advance, b.to_pay, b.lr_number, b.lr_index, b.created_by_role,
                   b.created_at,
                   a.account_name, w.warehouse_name, t.truck_number,
                   t.driver_name, t.driver_mobile, t.owner_name, t.owner_mobile,
                   r.head AS builty_head, b.receiver_name, b.received_quantity,
                   a.address AS account_address,
                   r.company_name, r.company_code, a.account_type, b.sub_head
            FROM builty b
            LEFT JOIN accounts   a  ON b.account_id  = a.id
            LEFT JOIN warehouses w  ON b.warehouse_id = w.id
            LEFT JOIN trucks     t  ON b.truck_id     = t.id
            LEFT JOIN rakes      r  ON b.rake_code    = r.rake_code
            WHERE b.id = %s
        ''', (builty_id,))
        row = cursor.fetchone()
        return tuple(row) if row else None

    # ==================================================================
    # Loading Slip Operations
    # ==================================================================

    def add_loading_slip(self, rake_code, slip_number, loading_point_name, destination,
                         account_id, warehouse_id, quantity_bags, quantity_mt, truck_id,
                         wagon_number, goods_name, truck_driver, truck_owner, mobile_1,
                         mobile_2, truck_details, builty_id=None, cgmf_id=None, sub_head=None,
                         warehouse_account_id=None, warehouse_account_type=None,
                         slip_date=None, _retry=True):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            # Narrow duplicate check: same slip_number + rake + loading_point + truck + quantity
            # (so two consecutive different slips with the same pre-fetched serial are distinct)
            cursor.execute(
                '''SELECT id FROM loading_slips
                   WHERE rake_code = %s AND slip_number = %s AND loading_point_name = %s
                     AND truck_id = %s AND quantity_mt = %s''',
                (rake_code, slip_number, loading_point_name, truck_id, quantity_mt)
            )
            existing = cursor.fetchone()
            if existing:
                print(f"Loading slip {slip_number} for rake {rake_code} at {loading_point_name} already exists")
                return existing[0]

            if slip_date:
                cursor.execute('''
                    INSERT INTO loading_slips
                        (rake_code, slip_number, loading_point_name, destination,
                         account_id, warehouse_id, cgmf_id, quantity_bags, quantity_mt, truck_id,
                         wagon_number, goods_name, truck_driver, truck_owner,
                         mobile_number_1, mobile_number_2, truck_details, builty_id, sub_head,
                         warehouse_account_id, warehouse_account_type, created_at)
                    VALUES (%s,%s,%s,%s, %s,%s,%s,%s,%s,%s, %s,%s,%s,%s, %s,%s,%s,%s,%s, %s,%s,%s)
                    RETURNING id
                ''', (rake_code, slip_number, loading_point_name, destination,
                      account_id, warehouse_id, cgmf_id, quantity_bags, quantity_mt, truck_id,
                      wagon_number, goods_name, truck_driver, truck_owner,
                      mobile_1, mobile_2, truck_details, builty_id, sub_head,
                      warehouse_account_id, warehouse_account_type, slip_date))
            else:
                cursor.execute('''
                    INSERT INTO loading_slips
                        (rake_code, slip_number, loading_point_name, destination,
                         account_id, warehouse_id, cgmf_id, quantity_bags, quantity_mt, truck_id,
                         wagon_number, goods_name, truck_driver, truck_owner,
                         mobile_number_1, mobile_number_2, truck_details, builty_id, sub_head,
                         warehouse_account_id, warehouse_account_type)
                    VALUES (%s,%s,%s,%s, %s,%s,%s,%s,%s,%s, %s,%s,%s,%s, %s,%s,%s,%s,%s, %s,%s)
                    RETURNING id
                ''', (rake_code, slip_number, loading_point_name, destination,
                      account_id, warehouse_id, cgmf_id, quantity_bags, quantity_mt, truck_id,
                      wagon_number, goods_name, truck_driver, truck_owner,
                      mobile_1, mobile_2, truck_details, builty_id, sub_head,
                      warehouse_account_id, warehouse_account_type))
            slip_id = cursor.fetchone()[0]
            conn.commit()
            self.invalidate_cache()
            print(f"Loading slip created with ID {slip_id}")
            return slip_id
        except Exception as e:
            print(f"Error adding loading slip: {e}")
            import traceback; traceback.print_exc()
            try: conn.rollback()
            except Exception: pass
            if _retry:
                time.sleep(0.3)
                Database.reset_cloud_connection()
                return self.add_loading_slip(
                    rake_code, slip_number, loading_point_name, destination,
                    account_id, warehouse_id, quantity_bags, quantity_mt, truck_id,
                    wagon_number, goods_name, truck_driver, truck_owner, mobile_1, mobile_2,
                    truck_details, builty_id, cgmf_id, sub_head,
                    warehouse_account_id, warehouse_account_type, slip_date, _retry=False)
            return None

    def get_loading_slips_by_rake(self, rake_code):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT ls.id AS slip_id, ls.rake_code, ls.slip_number, ls.loading_point_name,
                   ls.destination, ls.account_id, ls.warehouse_id, ls.cgmf_id,
                   ls.quantity_bags, ls.quantity_mt, ls.truck_id,
                   ls.wagon_number, ls.goods_name, ls.truck_driver, ls.truck_owner,
                   ls.mobile_number_1, ls.mobile_number_2, ls.truck_details,
                   ls.builty_id, ls.sub_head, ls.warehouse_account_id, ls.warehouse_account_type,
                   ls.created_at,
                   a.account_name, t.truck_number
            FROM loading_slips ls
            LEFT JOIN accounts a ON ls.account_id = a.id
            LEFT JOIN trucks   t ON ls.truck_id   = t.id
            WHERE ls.rake_code = %s
            ORDER BY ls.slip_number
        ''', (rake_code,))
        return self._rows(cursor)

    def get_all_loading_slips(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT ls.id AS slip_id, ls.rake_code, ls.slip_number, ls.loading_point_name,
                   ls.destination,
                   COALESCE(a.account_name, w.warehouse_name) AS destination_name,
                   ls.wagon_number, ls.quantity_bags, ls.quantity_mt, t.truck_number,
                   ls.goods_name, ls.truck_driver, ls.truck_owner,
                   ls.mobile_number_1, ls.mobile_number_2
            FROM loading_slips ls
            LEFT JOIN accounts   a  ON ls.account_id   = a.id
            LEFT JOIN warehouses w  ON ls.warehouse_id  = w.id
            LEFT JOIN trucks     t  ON ls.truck_id      = t.id
            WHERE ls.builty_id IS NULL
            ORDER BY ls.created_at DESC
        ''')
        return self._rows(cursor)

    def get_warehouse_loading_slips(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT ls.id AS slip_id, ls.rake_code, ls.slip_number, ls.loading_point_name,
                   ls.destination,
                   COALESCE(a.account_name, w.warehouse_name, cg.society_name) AS destination_name,
                   ls.wagon_number, ls.quantity_bags, ls.quantity_mt, t.truck_number,
                   ls.goods_name, ls.truck_driver, ls.truck_owner,
                   ls.mobile_number_1, ls.mobile_number_2
            FROM loading_slips ls
            LEFT JOIN accounts   a  ON ls.account_id   = a.id
            LEFT JOIN warehouses w  ON ls.warehouse_id  = w.id
            LEFT JOIN cgmf       cg ON ls.cgmf_id       = cg.id
            LEFT JOIN trucks     t  ON ls.truck_id      = t.id
            WHERE ls.builty_id IS NULL
              AND ls.loading_point_name IN
                  (SELECT warehouse_name FROM warehouses WHERE warehouse_name IS NOT NULL)
            ORDER BY ls.created_at DESC
        ''')
        return self._rows(cursor)

    def get_rakepoint_loading_slips(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                SELECT ls.id AS slip_id, ls.rake_code, ls.slip_number, ls.loading_point_name,
                       ls.destination,
                       COALESCE(a.account_name, w.warehouse_name, cg.society_name) AS destination_name,
                       ls.wagon_number, ls.quantity_bags, ls.quantity_mt, t.truck_number,
                       ls.goods_name, ls.truck_driver, ls.truck_owner,
                       ls.mobile_number_1, ls.mobile_number_2,
                       ls.account_id, ls.warehouse_id, ls.cgmf_id,
                       COALESCE(a.account_type::text, '') AS account_type,
                       COALESCE(ls.warehouse_account_type, '') AS warehouse_account_type
                FROM loading_slips ls
                LEFT JOIN accounts   a  ON ls.account_id   = a.id
                LEFT JOIN warehouses w  ON ls.warehouse_id  = w.id
                LEFT JOIN cgmf       cg ON ls.cgmf_id       = cg.id
                LEFT JOIN trucks     t  ON ls.truck_id      = t.id
                LEFT JOIN rakes      r  ON ls.rake_code     = r.rake_code
                WHERE ls.builty_id IS NULL
                  AND ls.loading_point_name NOT IN
                      (SELECT warehouse_name FROM warehouses WHERE warehouse_name IS NOT NULL)
                  AND (NOT r.is_closed OR r.is_closed IS NULL)
                ORDER BY ls.created_at DESC
            ''')
            slips = self._rows(cursor)
            print(f"DEBUG: Found {len(slips)} rakepoint loading slips")
            return slips
        except Exception as e:
            print(f"ERROR in get_rakepoint_loading_slips: {e}")
            return []

    def get_all_loading_slips_with_status(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT ls.id AS slip_id, ls.rake_code, ls.slip_number, ls.loading_point_name,
                   ls.destination,
                   COALESCE(a.account_name, w.warehouse_name, cg.society_name) AS destination_name,
                   ls.quantity_bags, ls.quantity_mt, t.truck_number,
                   ls.wagon_number, ls.builty_id, ls.created_at,
                   ls.goods_name, ls.truck_driver, ls.truck_owner,
                   ls.mobile_number_1, ls.mobile_number_2,
                   b.builty_number,
                   a.account_name, w.warehouse_name, cg.society_name,
                   ls.account_id, ls.warehouse_id, ls.cgmf_id
            FROM loading_slips ls
            LEFT JOIN accounts   a  ON ls.account_id   = a.id
            LEFT JOIN warehouses w  ON ls.warehouse_id  = w.id
            LEFT JOIN cgmf       cg ON ls.cgmf_id       = cg.id
            LEFT JOIN trucks     t  ON ls.truck_id      = t.id
            LEFT JOIN builty     b  ON ls.builty_id     = b.id
            ORDER BY ls.created_at DESC
        ''')
        return self._rows(cursor)

    def link_loading_slip_to_builty(self, slip_id, builty_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('SELECT id, builty_id FROM loading_slips WHERE id = %s', (slip_id,))
            slip = cursor.fetchone()
            if not slip:
                print(f"ERROR: Loading slip {slip_id} not found")
                return False
            if slip[1] is not None:
                print(f"WARNING: Loading slip {slip_id} already linked to builty {slip[1]}")
            cursor.execute(
                'UPDATE loading_slips SET builty_id=%s WHERE id=%s',
                (builty_id, slip_id)
            )
            conn.commit()
            print(f"DEBUG: Linked loading slip {slip_id} to builty {builty_id}")
            return True
        except Exception as e:
            print(f"Error linking loading slip to builty: {e}")
            try: conn.rollback()
            except Exception: pass
            return False

    def delete_loading_slip(self, slip_id, delete_builty=False):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            conn.autocommit = False
            cursor.execute(
                'SELECT id, builty_id FROM loading_slips WHERE id = %s',
                (slip_id,)
            )
            slip = cursor.fetchone()
            if not slip:
                conn.rollback()
                conn.autocommit = True
                return False, "Loading slip not found"
            builty_id = slip[1]
            if builty_id and delete_builty:
                cursor.execute('DELETE FROM warehouse_stock WHERE builty_id = %s', (builty_id,))
                cursor.execute('DELETE FROM builty WHERE id = %s', (builty_id,))
            elif builty_id and not delete_builty:
                conn.rollback()
                conn.autocommit = True
                return False, "Loading slip has an associated builty. Please confirm builty deletion."
            cursor.execute('DELETE FROM loading_slips WHERE id = %s', (slip_id,))
            conn.commit()
            conn.autocommit = True
            return True, "Loading slip deleted successfully"
        except Exception as e:
            try: conn.rollback()
            except Exception: pass
            conn.autocommit = True
            return False, str(e)

    def delete_builty(self, builty_id, delete_loading_slip=False):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            conn.autocommit = False
            cursor.execute('SELECT id FROM builty WHERE id = %s', (builty_id,))
            if not cursor.fetchone():
                conn.rollback()
                conn.autocommit = True
                return False, "Builty not found"
            cursor.execute('DELETE FROM warehouse_stock WHERE builty_id = %s', (builty_id,))
            cursor.execute('SELECT id FROM loading_slips WHERE builty_id = %s', (builty_id,))
            linked_slip = cursor.fetchone()
            if linked_slip and delete_loading_slip:
                cursor.execute('DELETE FROM loading_slips WHERE id = %s', (linked_slip[0],))
            elif linked_slip:
                cursor.execute(
                    'UPDATE loading_slips SET builty_id=NULL WHERE id=%s',
                    (linked_slip[0],)
                )
            cursor.execute('DELETE FROM builty WHERE id = %s', (builty_id,))
            conn.commit()
            conn.autocommit = True
            return True, "Builty deleted successfully"
        except Exception as e:
            try: conn.rollback()
            except Exception: pass
            conn.autocommit = True
            return False, str(e)

    def delete_rake(self, rake_code):
        """Delete a rake and ALL associated loading slips, builties, ebills, and warehouse stock."""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            conn.autocommit = False
            # Collect all builty IDs linked to this rake's loading slips
            cursor.execute(
                'SELECT DISTINCT builty_id FROM loading_slips WHERE rake_code = %s AND builty_id IS NOT NULL',
                (rake_code,)
            )
            builty_ids = [row[0] for row in cursor.fetchall()]

            if builty_ids:
                fmt = ','.join(['%s'] * len(builty_ids))
                # Delete ebills linked to those builties
                cursor.execute(f'DELETE FROM ebills WHERE builty_id IN ({fmt})', builty_ids)
                # Delete warehouse stock linked to those builties
                cursor.execute(f'DELETE FROM warehouse_stock WHERE builty_id IN ({fmt})', builty_ids)

            # Delete loading slips (unlink builty_id first to avoid FK issues, then delete builties)
            cursor.execute('DELETE FROM loading_slips WHERE rake_code = %s', (rake_code,))

            if builty_ids:
                fmt = ','.join(['%s'] * len(builty_ids))
                cursor.execute(f'DELETE FROM builty WHERE id IN ({fmt})', builty_ids)

            # Delete rake products and rake record
            cursor.execute('DELETE FROM rake_products WHERE rake_code = %s', (rake_code,))
            cursor.execute('DELETE FROM rakes WHERE rake_code = %s', (rake_code,))

            conn.commit()
            conn.autocommit = True
            return True, f"Rake {rake_code} and all associated records deleted successfully"
        except Exception as e:
            try: conn.rollback()
            except Exception: pass
            conn.autocommit = True
            return False, str(e)

    def get_loading_slip_by_id(self, slip_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT ls.id AS slip_id, ls.rake_code, ls.slip_number, ls.loading_point_name,
                   ls.destination, ls.account_id, ls.warehouse_id, ls.cgmf_id,
                   ls.quantity_bags, ls.quantity_mt, ls.truck_id,
                   ls.wagon_number, ls.goods_name, ls.truck_driver, ls.truck_owner,
                   ls.mobile_number_1, ls.mobile_number_2, ls.truck_details,
                   ls.builty_id, ls.sub_head, ls.warehouse_account_id, ls.warehouse_account_type,
                   ls.created_at,
                   a.account_name, w.warehouse_name, t.truck_number
            FROM loading_slips ls
            LEFT JOIN accounts   a  ON ls.account_id   = a.id
            LEFT JOIN warehouses w  ON ls.warehouse_id  = w.id
            LEFT JOIN trucks     t  ON ls.truck_id      = t.id
            WHERE ls.id = %s
        ''', (slip_id,))
        row = cursor.fetchone()
        return tuple(row) if row else None

    def update_loading_slip(self, slip_id, destination, quantity_bags, quantity_mt,
                            goods_name, account_id=None, warehouse_id=None,
                            cgmf_id=None, date=None):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('SELECT quantity_mt FROM loading_slips WHERE id = %s', (slip_id,))
            if not cursor.fetchone():
                return False, "Loading slip not found"
            if date:
                if account_id or warehouse_id or cgmf_id:
                    cursor.execute('''
                        UPDATE loading_slips
                        SET destination=%s, quantity_bags=%s, quantity_mt=%s, goods_name=%s,
                            account_id=%s, warehouse_id=%s, cgmf_id=%s, created_at=%s
                        WHERE id=%s
                    ''', (destination, quantity_bags, quantity_mt, goods_name,
                          account_id, warehouse_id, cgmf_id, date, slip_id))
                else:
                    cursor.execute('''
                        UPDATE loading_slips
                        SET destination=%s, quantity_bags=%s, quantity_mt=%s,
                            goods_name=%s, created_at=%s
                        WHERE id=%s
                    ''', (destination, quantity_bags, quantity_mt, goods_name, date, slip_id))
            else:
                if account_id or warehouse_id or cgmf_id:
                    cursor.execute('''
                        UPDATE loading_slips
                        SET destination=%s, quantity_bags=%s, quantity_mt=%s, goods_name=%s,
                            account_id=%s, warehouse_id=%s, cgmf_id=%s
                        WHERE id=%s
                    ''', (destination, quantity_bags, quantity_mt, goods_name,
                          account_id, warehouse_id, cgmf_id, slip_id))
                else:
                    cursor.execute('''
                        UPDATE loading_slips
                        SET destination=%s, quantity_bags=%s, quantity_mt=%s, goods_name=%s
                        WHERE id=%s
                    ''', (destination, quantity_bags, quantity_mt, goods_name, slip_id))
            conn.commit()
            self.invalidate_cache()
            return True, "Loading slip updated successfully"
        except Exception as e:
            try: conn.rollback()
            except Exception: pass
            return False, str(e)

    def update_builty(self, builty_id, unloading_point, number_of_bags, quantity_mt,
                      rate_per_mt, total_freight, advance, to_pay,
                      account_id=None, warehouse_id=None, cgmf_id=None, date=None):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            conn.autocommit = False
            cursor.execute('SELECT quantity_mt FROM builty WHERE id = %s', (builty_id,))
            old = cursor.fetchone()
            if not old:
                conn.rollback()
                conn.autocommit = True
                return False, "Builty not found"
            quantity_diff = quantity_mt - old[0]
            if date:
                if account_id or warehouse_id or cgmf_id:
                    cursor.execute('''
                        UPDATE builty
                        SET unloading_point=%s, number_of_bags=%s, quantity_mt=%s,
                            rate_per_mt=%s, total_freight=%s, advance=%s, to_pay=%s,
                            account_id=%s, warehouse_id=%s, cgmf_id=%s, date=%s
                        WHERE id=%s
                    ''', (unloading_point, number_of_bags, quantity_mt, rate_per_mt,
                          total_freight, advance, to_pay,
                          account_id, warehouse_id, cgmf_id, date, builty_id))
                else:
                    cursor.execute('''
                        UPDATE builty
                        SET unloading_point=%s, number_of_bags=%s, quantity_mt=%s,
                            rate_per_mt=%s, total_freight=%s, advance=%s, to_pay=%s, date=%s
                        WHERE id=%s
                    ''', (unloading_point, number_of_bags, quantity_mt, rate_per_mt,
                          total_freight, advance, to_pay, date, builty_id))
            else:
                if account_id or warehouse_id or cgmf_id:
                    cursor.execute('''
                        UPDATE builty
                        SET unloading_point=%s, number_of_bags=%s, quantity_mt=%s,
                            rate_per_mt=%s, total_freight=%s, advance=%s, to_pay=%s,
                            account_id=%s, warehouse_id=%s, cgmf_id=%s
                        WHERE id=%s
                    ''', (unloading_point, number_of_bags, quantity_mt, rate_per_mt,
                          total_freight, advance, to_pay,
                          account_id, warehouse_id, cgmf_id, builty_id))
                else:
                    cursor.execute('''
                        UPDATE builty
                        SET unloading_point=%s, number_of_bags=%s, quantity_mt=%s,
                            rate_per_mt=%s, total_freight=%s, advance=%s, to_pay=%s
                        WHERE id=%s
                    ''', (unloading_point, number_of_bags, quantity_mt, rate_per_mt,
                          total_freight, advance, to_pay, builty_id))
            if quantity_diff != 0:
                cursor.execute(
                    'UPDATE warehouse_stock SET quantity_mt = quantity_mt + %s WHERE builty_id = %s',
                    (quantity_diff, builty_id)
                )
            conn.commit()
            conn.autocommit = True
            self.invalidate_cache()
            return True, "Builty updated successfully"
        except Exception as e:
            try: conn.rollback()
            except Exception: pass
            conn.autocommit = True
            return False, str(e)

    # ==================================================================
    # Warehouse Stock Operations
    # ==================================================================

    def add_warehouse_stock_in(self, warehouse_id, builty_id, quantity_mt, employee_id=None,
                                account_id=None, date=None, notes='', company_id=None,
                                product_id=None, source_type='rake', truck_id=None,
                                serial_number=None, cgmf_id=None, sub_head=None):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            if serial_number is None:
                serial_number = self.get_next_warehouse_stock_serial(warehouse_id)
            cursor.execute('''
                INSERT INTO warehouse_stock
                    (serial_number, warehouse_id, builty_id, transaction_type,
                     quantity_mt, employee_id, account_id, cgmf_id,
                     date, notes, company_id, product_id, source_type, truck_id, sub_head)
                VALUES (%s,%s,%s,'IN', %s,%s,%s,%s, %s,%s,%s,%s,%s,%s,%s)
                RETURNING id
            ''', (serial_number, warehouse_id, builty_id,
                  quantity_mt, employee_id, account_id, cgmf_id,
                  date, notes, company_id, product_id, source_type, truck_id, sub_head))
            stock_id = cursor.fetchone()[0]
            conn.commit()
            self.invalidate_cache()
            return stock_id
        except Exception as e:
            print(f"Error adding stock in: {e}")
            try: conn.rollback()
            except Exception: pass
            return None

    def add_warehouse_stock_out(self, warehouse_id, builty_id, quantity_mt,
                                 account_id, date, notes=''):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO warehouse_stock
                    (warehouse_id, builty_id, transaction_type, quantity_mt, account_id, date, notes)
                VALUES (%s,%s,'OUT',%s,%s,%s,%s)
                RETURNING id
            ''', (warehouse_id, builty_id, quantity_mt, account_id, date, notes))
            stock_id = cursor.fetchone()[0]
            conn.commit()
            self.invalidate_cache()
            return stock_id
        except Exception as e:
            print(f"Error adding stock out: {e}")
            try: conn.rollback()
            except Exception: pass
            return None

    def update_warehouse_stock_allocation(self, stock_id, quantity_mt, account_type,
                                           dealer_name, remark):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                UPDATE warehouse_stock
                SET quantity_mt=%s, account_type=%s, dealer_name=%s, remark=%s
                WHERE id=%s
            ''', (quantity_mt, account_type, dealer_name, remark, stock_id))
            conn.commit()
            return True
        except Exception as e:
            try: conn.rollback()
            except Exception: pass
            return False

    def get_warehouse_stock_summary(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT c.company_name, p.product_name,
                   SUM(ws.quantity_mt) AS total_quantity,
                   w.warehouse_name,
                   c.id AS company_id, p.id AS product_id, w.id AS warehouse_id
            FROM warehouse_stock ws
            LEFT JOIN companies  c ON ws.company_id   = c.id
            LEFT JOIN products   p ON ws.product_id   = p.id
            LEFT JOIN warehouses w ON ws.warehouse_id = w.id
            WHERE ws.transaction_type = 'IN'
            GROUP BY c.id, p.id, w.id, c.company_name, p.product_name, w.warehouse_name
            ORDER BY c.company_name, p.product_name, w.warehouse_name
        ''')
        return self._rows(cursor)

    def get_warehouse_balance_stock(self, warehouse_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT
                COALESCE(SUM(CASE WHEN transaction_type='IN'  THEN quantity_mt ELSE 0 END), 0),
                COALESCE(SUM(CASE WHEN transaction_type='OUT' THEN quantity_mt ELSE 0 END), 0)
            FROM warehouse_stock
            WHERE warehouse_id = %s
        ''', (warehouse_id,))
        result = cursor.fetchone()
        si, so = result[0], result[1]
        return {'stock_in': si, 'stock_out': so, 'balance': si - so}

    def get_products_in_warehouse(self, warehouse_id):
        """Return products with positive balance in a warehouse, with their stock details."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT
                p.id AS product_id,
                p.product_name,
                p.unit_per_bag,
                COALESCE(SUM(CASE WHEN ws.transaction_type='IN'  THEN ws.quantity_mt ELSE 0 END), 0) AS stock_in,
                COALESCE(SUM(CASE WHEN ws.transaction_type='OUT' THEN ws.quantity_mt ELSE 0 END), 0) AS stock_out,
                COALESCE(SUM(CASE WHEN ws.transaction_type='IN'  THEN ws.quantity_mt ELSE 0 END), 0)
                - COALESCE(SUM(CASE WHEN ws.transaction_type='OUT' THEN ws.quantity_mt ELSE 0 END), 0) AS balance
            FROM warehouse_stock ws
            JOIN products p ON ws.product_id = p.id
            WHERE ws.warehouse_id = %s
            GROUP BY p.id, p.product_name, p.unit_per_bag
            HAVING COALESCE(SUM(CASE WHEN ws.transaction_type='IN'  THEN ws.quantity_mt ELSE 0 END), 0)
                   - COALESCE(SUM(CASE WHEN ws.transaction_type='OUT' THEN ws.quantity_mt ELSE 0 END), 0) > 0
            ORDER BY p.product_name
        ''', (warehouse_id,))
        rows = cursor.fetchall()
        return [
            {
                'product_id': str(r[0]),
                'product_name': r[1],
                'unit_per_bag': float(r[2]) if r[2] else 50.0,
                'balance': float(r[5])
            }
            for r in rows
        ]

    def add_loading_slip_products(self, slip_id, products):
        """Insert multiple product rows for a loading slip.
        products: list of dicts with keys product_id, product_name, quantity_bags, quantity_mt
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            for p in products:
                cursor.execute('''
                    INSERT INTO loading_slip_products
                        (loading_slip_id, product_id, product_name, quantity_bags, quantity_mt)
                    VALUES (%s, %s, %s, %s, %s)
                ''', (slip_id, p.get('product_id') or None,
                      p['product_name'], int(p['quantity_bags']), float(p['quantity_mt'])))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error adding loading slip products: {e}")
            try: conn.rollback()
            except Exception: pass
            return False

    def get_warehouse_stock_transactions(self, warehouse_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(f'''
            SELECT {_STOCK_COLS}, b.builty_number, a.account_name
            FROM warehouse_stock ws
            LEFT JOIN builty   b ON ws.builty_id  = b.id
            LEFT JOIN accounts a ON ws.account_id = a.id
            WHERE ws.warehouse_id = %s
            ORDER BY ws.date DESC, ws.created_at DESC
        ''', (warehouse_id,))
        return self._rows(cursor)

    # ==================================================================
    # E-Bill Operations
    # ==================================================================

    def add_ebill(self, builty_id, ebill_number, amount, generated_date,
                  bill_pdf=None, eway_bill_pdf=None):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO ebills (builty_id, ebill_number, amount, generated_date,
                                    bill_pdf, eway_bill_pdf)
                VALUES (%s,%s,%s,%s,%s,%s) RETURNING id
            ''', (builty_id, ebill_number, amount, generated_date, bill_pdf, eway_bill_pdf))
            ebill_id = cursor.fetchone()[0]
            conn.commit()
            return ebill_id
        except Exception as e:
            print(f"Error adding e-bill: {e}")
            try: conn.rollback()
            except Exception: pass
            return None

    def get_all_ebills(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT e.id AS ebill_id, e.ebill_number, e.amount, e.generated_date,
                   e.eway_bill_pdf, e.created_at,
                   b.builty_number, b.goods_name, b.quantity_mt, b.lr_number,
                   t.truck_number,
                   COALESCE(a.account_name, 'N/A') AS account_name,
                   e.bill_pdf, b.id AS builty_id, b.created_by_role
            FROM ebills e
            LEFT JOIN builty   b ON e.builty_id  = b.id
            LEFT JOIN trucks   t ON b.truck_id   = t.id
            LEFT JOIN accounts a ON b.account_id = a.id
            ORDER BY e.created_at DESC
        ''')
        return self._rows(cursor)

    def get_builties_without_ebills(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT b.id AS builty_id, b.builty_number, b.rake_code, b.date, b.rake_point_name,
                   b.account_id, b.warehouse_id, b.cgmf_id, b.truck_id,
                   b.loading_point, b.unloading_point, b.goods_name, b.number_of_bags,
                   b.quantity_mt, b.kg_per_bag, b.rate_per_mt, b.total_freight,
                   b.advance, b.to_pay, b.lr_number, b.lr_index, b.created_by_role,
                   b.sub_head, b.receiver_name, b.received_quantity, b.created_at,
                   COALESCE(t.truck_number, '') AS truck_number,
                   COALESCE(a.account_name, COALESCE(w.warehouse_name, COALESCE(cg.society_name, 'N/A'))) AS account_name
            FROM builty b
            LEFT JOIN ebills e ON b.id = e.builty_id
            LEFT JOIN trucks t ON b.truck_id = t.id
            LEFT JOIN accounts a ON b.account_id = a.id
            LEFT JOIN warehouses w ON b.warehouse_id = w.id
            LEFT JOIN cgmf cg ON b.cgmf_id = cg.id
            WHERE e.id IS NULL
            ORDER BY b.date DESC
        ''')
        return self._rows(cursor)

    def get_ebills_by_builty_creator(self, created_by_role):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT e.id AS ebill_id, e.ebill_number, e.amount, e.generated_date,
                   e.eway_bill_pdf, e.created_at,
                   b.builty_number, b.goods_name, b.quantity_mt, b.lr_number,
                   t.truck_number,
                   COALESCE(a.account_name, 'N/A') AS account_name,
                   e.bill_pdf, b.id AS builty_id, b.created_by_role
            FROM ebills e
            LEFT JOIN builty   b ON e.builty_id  = b.id
            LEFT JOIN trucks   t ON b.truck_id   = t.id
            LEFT JOIN accounts a ON b.account_id = a.id
            WHERE b.created_by_role = %s
            ORDER BY e.created_at DESC
        ''', (created_by_role,))
        return self._rows(cursor)

    # ==================================================================
    # Dashboard Statistics
    # ==================================================================

    def get_admin_dashboard_stats(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM rakes')
        total_rakes = cursor.fetchone()[0]
        cursor.execute('SELECT COUNT(*) FROM builty')
        total_builties = cursor.fetchone()[0]
        cursor.execute('''
            SELECT
                COALESCE(SUM(CASE WHEN transaction_type='IN'  THEN quantity_mt ELSE 0 END), 0),
                COALESCE(SUM(CASE WHEN transaction_type='OUT' THEN quantity_mt ELSE 0 END), 0)
            FROM warehouse_stock
        ''')
        result = cursor.fetchone()
        total_stock_in, total_stock_out = result[0], result[1]
        cursor.execute('SELECT COUNT(*), COALESCE(SUM(amount), 0) FROM ebills')
        result = cursor.fetchone()
        return {
            'total_rakes':        total_rakes,
            'total_builties':     total_builties,
            'total_stock_in':     total_stock_in,
            'total_stock_out':    total_stock_out,
            'balance_stock':      total_stock_in - total_stock_out,
            'total_ebills':       result[0],
            'total_ebill_amount': result[1],
        }

    def get_rake_summary(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT r.rake_code, r.company_name, r.date, r.rr_quantity,
                   COALESCE(SUM(CASE WHEN ws.transaction_type='IN'  THEN ws.quantity_mt ELSE 0 END), 0),
                   COALESCE(SUM(CASE WHEN ws.transaction_type='OUT' THEN ws.quantity_mt ELSE 0 END), 0)
            FROM rakes r
            LEFT JOIN builty          b  ON r.rake_code  = b.rake_code
            LEFT JOIN warehouse_stock ws ON b.id          = ws.builty_id
            GROUP BY r.rake_code, r.company_name, r.date, r.rr_quantity
            ORDER BY r.date DESC
        ''')
        return self._rows(cursor)

    # ==================================================================
    # Logistic Bill Operations
    # ==================================================================

    def get_rake_transport_data(self, rake_code):
        conn = self.get_connection()
        cursor = conn.cursor()
        result = []
        try:
            cursor.execute('''
                SELECT 'Warehouse' AS dest_type, w.warehouse_name, w.id,
                       SUM(ls.quantity_mt), COALESCE(w.distance, 0), NULL
                FROM loading_slips ls
                JOIN warehouses w ON ls.warehouse_id = w.id
                WHERE ls.rake_code=%s AND ls.warehouse_id IS NOT NULL
                GROUP BY w.id, w.warehouse_name
            ''', (rake_code,))
            for r in cursor.fetchall():
                result.append({
                    'dest_type': r[0], 'dest_name': r[1], 'dest_id': r[2],
                    'quantity': r[3] or 0, 'distance': r[4] or 0, 'supply_term': r[5]
                })
        except Exception as e:
            print(f"Error fetching warehouse data: {e}")
        try:
            cursor.execute('''
                SELECT a.account_type, a.account_name, a.id,
                       SUM(b.quantity_mt), COALESCE(a.distance, 0), b.supply_term
                FROM builty b
                JOIN accounts a ON b.account_id = a.id
                WHERE b.rake_code=%s AND b.account_id IS NOT NULL
                GROUP BY a.id, a.account_type, a.account_name, b.supply_term
            ''', (rake_code,))
            for r in cursor.fetchall():
                result.append({
                    'dest_type': r[0], 'dest_name': r[1], 'dest_id': r[2],
                    'quantity': r[3] or 0, 'distance': r[4] or 0, 'supply_term': r[5]
                })
        except Exception as e:
            print(f"Error fetching account data: {e}")
        try:
            cursor.execute('''
                SELECT 'CGMF', c.society_name || ' - ' || c.destination, c.id,
                       SUM(ls.quantity_mt), COALESCE(c.distance, 0), NULL
                FROM loading_slips ls
                JOIN cgmf c ON ls.cgmf_id = c.id
                WHERE ls.rake_code=%s AND ls.cgmf_id IS NOT NULL
                GROUP BY c.id, c.society_name, c.destination
            ''', (rake_code,))
            for r in cursor.fetchall():
                result.append({
                    'dest_type': r[0], 'dest_name': r[1], 'dest_id': r[2],
                    'quantity': r[3] or 0, 'distance': r[4] or 0, 'supply_term': r[5]
                })
        except Exception as e:
            print(f"Error fetching CGMF data: {e}")
        return result

    def get_warehouse_storage_data(self, warehouse_id=None):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            if warehouse_id:
                cursor.execute('''
                    SELECT ws.date, c.company_name, p.product_name, ws.quantity_mt,
                           ws.id, c.id, p.id
                    FROM warehouse_stock ws
                    LEFT JOIN companies c ON ws.company_id = c.id
                    LEFT JOIN products  p ON ws.product_id = p.id
                    WHERE ws.transaction_type='IN' AND ws.warehouse_id=%s
                    ORDER BY ws.date DESC
                ''', (warehouse_id,))
            else:
                cursor.execute('''
                    SELECT ws.date, c.company_name, p.product_name, ws.quantity_mt,
                           ws.id, c.id, p.id, w.warehouse_name
                    FROM warehouse_stock ws
                    LEFT JOIN companies  c ON ws.company_id   = c.id
                    LEFT JOIN products   p ON ws.product_id   = p.id
                    LEFT JOIN warehouses w ON ws.warehouse_id = w.id
                    WHERE ws.transaction_type='IN'
                    ORDER BY ws.date DESC
                ''')
            return self._rows(cursor)
        except Exception as e:
            print(f"Error fetching warehouse storage data: {e}")
            return []

    def get_warehouse_transport_data(self, warehouse_id=None):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            if warehouse_id:
                cursor.execute('''
                    SELECT ws.date, t.truck_number,
                           COALESCE(a.account_name, cg.society_name, 'Direct'),
                           p.product_name, ws.quantity_mt, 0, ws.id, b.builty_number
                    FROM warehouse_stock ws
                    LEFT JOIN builty   b  ON ws.builty_id  = b.id
                    LEFT JOIN trucks   t  ON b.truck_id    = t.id
                    LEFT JOIN accounts a  ON ws.account_id = a.id
                    LEFT JOIN cgmf     cg ON ws.cgmf_id    = cg.id
                    LEFT JOIN products p  ON ws.product_id = p.id
                    WHERE ws.transaction_type='OUT' AND ws.warehouse_id=%s
                    ORDER BY ws.date DESC
                ''', (warehouse_id,))
            else:
                cursor.execute('''
                    SELECT ws.date, t.truck_number,
                           COALESCE(a.account_name, cg.society_name, 'Direct'),
                           p.product_name, ws.quantity_mt, 0, ws.id, b.builty_number,
                           w.warehouse_name
                    FROM warehouse_stock ws
                    LEFT JOIN builty     b  ON ws.builty_id   = b.id
                    LEFT JOIN trucks     t  ON b.truck_id     = t.id
                    LEFT JOIN accounts   a  ON ws.account_id  = a.id
                    LEFT JOIN cgmf       cg ON ws.cgmf_id     = cg.id
                    LEFT JOIN products   p  ON ws.product_id  = p.id
                    LEFT JOIN warehouses w  ON ws.warehouse_id = w.id
                    WHERE ws.transaction_type='OUT'
                    ORDER BY ws.date DESC
                ''')
            return self._rows(cursor)
        except Exception as e:
            print(f"Error fetching warehouse transport data: {e}")
            return []

    # ==================================================================
    # Rake Bill Payments
    # ==================================================================

    def save_rake_bill_payment(self, rake_code, total_bill_amount, received_amount, username):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            remaining_amount = total_bill_amount - received_amount
            cursor.execute('''
                INSERT INTO rake_bill_payments
                    (rake_code, total_bill_amount, received_amount, remaining_amount, last_updated)
                VALUES (%s, %s, %s, %s, NOW())
                ON CONFLICT (rake_code) DO UPDATE SET
                    total_bill_amount = EXCLUDED.total_bill_amount,
                    received_amount   = EXCLUDED.received_amount,
                    remaining_amount  = EXCLUDED.remaining_amount,
                    last_updated      = NOW()
            ''', (rake_code, total_bill_amount, received_amount, remaining_amount))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error saving rake bill payment: {e}")
            try: conn.rollback()
            except Exception: pass
            return False

    def get_rake_bill_payment(self, rake_code):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT rake_code, total_bill_amount, received_amount,
                   remaining_amount, last_updated, updated_by
            FROM rake_bill_payments WHERE rake_code = %s
        ''', (rake_code,))
        result = cursor.fetchone()
        if result:
            return {
                'rake_code':         result[0],
                'total_bill_amount': result[1],
                'received_amount':   result[2],
                'remaining_amount':  result[3],
                'last_updated':      result[4],
                'updated_by':        result[5],
            }
        return None

    def get_all_rake_bill_payments(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT rake_code, total_bill_amount, received_amount,
                   remaining_amount, last_updated, updated_by
            FROM rake_bill_payments ORDER BY last_updated DESC
        ''')
        return [
            {
                'rake_code':         r[0],
                'total_bill_amount': r[1],
                'received_amount':   r[2],
                'remaining_amount':  r[3],
                'last_updated':      r[4],
                'updated_by':        r[5],
            }
            for r in cursor.fetchall()
        ]
