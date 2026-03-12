"""
FIMS Comprehensive Testing Pipeline
Tests: Authentication, Authorization, Database, Performance, Security, Route Integration
Run with: python -m pytest test_pipeline.py -v
"""

import os
import sys
import time
import tempfile
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, date, timedelta

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from database import Database, SimpleCache, _cache


class BaseTestCase(unittest.TestCase):
    """Base test case with Flask test client setup"""

    @classmethod
    def setUpClass(cls):
        """Create a test database and configure the app for testing"""
        cls.test_db_fd, cls.test_db_path = tempfile.mkstemp(suffix='.db')
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        # Force local SQLite for tests
        cls.original_turso_url = os.environ.get('TURSO_DATABASE_URL')
        cls.original_turso_token = os.environ.get('TURSO_AUTH_TOKEN')
        os.environ.pop('TURSO_DATABASE_URL', None)
        os.environ.pop('TURSO_AUTH_TOKEN', None)

    @classmethod
    def tearDownClass(cls):
        os.close(cls.test_db_fd)
        os.unlink(cls.test_db_path)
        # Restore env vars
        if cls.original_turso_url:
            os.environ['TURSO_DATABASE_URL'] = cls.original_turso_url
        if cls.original_turso_token:
            os.environ['TURSO_AUTH_TOKEN'] = cls.original_turso_token

    def setUp(self):
        self.app = app
        self.client = app.test_client()
        self.ctx = app.app_context()
        self.ctx.push()
        # Re-init the DB for each test with a fresh local SQLite
        self.test_db = Database(self.test_db_path)
        self.test_db.use_cloud = False
        Database._initialized = False
        self.test_db.initialize_database()

    def tearDown(self):
        self.ctx.pop()

    def login(self, username='admin', password='admin123'):
        """Helper to login"""
        return self.client.post('/login', data={
            'username': username,
            'password': password
        }, follow_redirects=True)

    def logout(self):
        return self.client.get('/logout', follow_redirects=True)


# ===========================================================================
# 1. CACHE TESTS
# ===========================================================================
class TestSimpleCache(unittest.TestCase):
    """Test the SimpleCache implementation"""

    def test_cache_set_and_get(self):
        cache = SimpleCache(ttl=10)
        cache.set('key1', 'value1')
        self.assertEqual(cache.get('key1'), 'value1')

    def test_cache_ttl_expiry(self):
        cache = SimpleCache(ttl=0.1)  # 100ms TTL
        cache.set('key1', 'value1')
        time.sleep(0.15)
        self.assertIsNone(cache.get('key1'))

    def test_cache_clear(self):
        cache = SimpleCache(ttl=60)
        cache.set('a', 1)
        cache.set('b', 2)
        cache.clear()
        self.assertIsNone(cache.get('a'))
        self.assertIsNone(cache.get('b'))

    def test_cache_delete(self):
        cache = SimpleCache(ttl=60)
        cache.set('key1', 'value1')
        cache.delete('key1')
        self.assertIsNone(cache.get('key1'))

    def test_cache_miss_returns_none(self):
        cache = SimpleCache(ttl=60)
        self.assertIsNone(cache.get('nonexistent'))


# ===========================================================================
# 2. DATABASE TESTS
# ===========================================================================
class TestDatabase(unittest.TestCase):
    """Test database operations with local SQLite"""

    @classmethod
    def setUpClass(cls):
        cls.test_db_fd, cls.test_db_path = tempfile.mkstemp(suffix='.db')
        os.environ.pop('TURSO_DATABASE_URL', None)
        os.environ.pop('TURSO_AUTH_TOKEN', None)

    @classmethod
    def tearDownClass(cls):
        os.close(cls.test_db_fd)
        os.unlink(cls.test_db_path)

    def setUp(self):
        self.db = Database(self.test_db_path)
        self.db.use_cloud = False
        Database._initialized = False
        self.db.initialize_database()

    def test_initialize_creates_tables(self):
        """All core tables should exist after init"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
        self.db.close_connection(conn)

        expected = {
            'users', 'rakes', 'rake_products', 'accounts', 'products',
            'companies', 'employees', 'cgmf', 'warehouses', 'trucks',
            'builty', 'loading_slips', 'warehouse_stock', 'ebills',
            'rake_bill_payments'
        }
        for t in expected:
            self.assertIn(t, tables, f"Missing table: {t}")

    def test_initialize_idempotent(self):
        """Calling initialize twice should not fail or duplicate data"""
        Database._initialized = False
        self.db.initialize_database()
        # Should not raise
        users = self.db.get_all_users()
        self.assertEqual(len(users), 4)  # 4 default users

    def test_initialized_flag_prevents_re_init(self):
        """After first init, _initialized flag skips re-init"""
        self.assertTrue(Database._initialized)
        # Calling again should be a no-op
        self.db.initialize_database()
        self.assertTrue(Database._initialized)

    def test_authenticate_valid_user(self):
        user = self.db.authenticate_user('admin', 'admin123')
        self.assertIsNotNone(user)
        self.assertEqual(user[1], 'admin')
        self.assertEqual(user[3], 'Admin')

    def test_authenticate_invalid_password(self):
        user = self.db.authenticate_user('admin', 'wrongpass')
        self.assertIsNone(user)

    def test_authenticate_invalid_username(self):
        user = self.db.authenticate_user('nonexistent', 'admin123')
        self.assertIsNone(user)

    def test_get_user_by_id(self):
        user = self.db.get_user_by_id(1)
        self.assertIsNotNone(user)
        self.assertEqual(user[1], 'admin')

    def test_add_rake(self):
        rake_id = self.db.add_rake(
            'RAKE001', 'Test Company', 'TC01', '2025-01-15',
            100.0, 'Urea', 'URE01', 'TestPoint', 'TestHead',
            [{'product_id': 1, 'product_name': 'Urea', 'product_code': 'URE01', 'quantity_mt': 100.0}]
        )
        self.assertIsNotNone(rake_id)
        rake = self.db.get_rake_by_code('RAKE001')
        self.assertIsNotNone(rake)

    def test_add_duplicate_rake_fails(self):
        self.db.add_rake('DUPRAKE', 'Co', 'C1', '2025-01-15', 50.0, 'Urea', 'U1', 'RP')
        result = self.db.add_rake('DUPRAKE', 'Co', 'C1', '2025-01-15', 50.0, 'Urea', 'U1', 'RP')
        self.assertIsNone(result)

    def test_get_dashboard_stats_optimized(self):
        stats = self.db.get_dashboard_stats_optimized()
        self.assertIsInstance(stats, dict)
        self.assertIn('total_rakes', stats)
        self.assertIn('total_builties', stats)
        self.assertIn('total_ebills', stats)
        # total_stock_in/out removed from dashboard stats (only day-wise is used now)
        self.assertNotIn('total_stock_in', stats)
        self.assertNotIn('total_stock_out', stats)

    def test_get_rakes_with_balances_limit(self):
        # Add a few rakes
        for i in range(10):
            self.db.add_rake(f'RK{i:03d}', 'Co', 'C1', '2025-01-15', 50.0, 'Urea', 'U1', 'RP')
        results = self.db.get_rakes_with_balances(limit=5)
        self.assertEqual(len(results), 5)

    def test_get_daywise_warehouse_stock_always_7_days(self):
        """Even with no stock data, should return 7 days of zeros"""
        result = self.db.get_daywise_warehouse_stock(days=7)
        self.assertEqual(len(result), 7)
        for day in result:
            self.assertIn('date', day)
            self.assertIn('stock_in', day)
            self.assertIn('stock_out', day)
            self.assertEqual(day['stock_in'], 0)
            self.assertEqual(day['stock_out'], 0)

    def test_get_total_shortage(self):
        shortage = self.db.get_total_shortage()
        self.assertIsInstance(shortage, (int, float))

    def test_execute_custom_query_select(self):
        result = self.db.execute_custom_query("SELECT COUNT(*) FROM users")
        self.assertIsNotNone(result)
        self.assertEqual(result[0][0], 4)

    def test_execute_custom_query_invalid(self):
        result = self.db.execute_custom_query("SELECT * FROM nonexistent_table")
        self.assertIsNone(result)

    def test_cache_invalidation_on_write(self):
        _cache.set('test_key', 'test_value')
        self.db.invalidate_cache()
        self.assertIsNone(_cache.get('test_key'))


# ===========================================================================
# 3. AUTHENTICATION & AUTHORIZATION TESTS
# ===========================================================================
class TestAuthentication(BaseTestCase):
    """Test login/logout and role-based access"""

    def test_login_page_loads(self):
        response = self.client.get('/login')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Login', response.data)

    def test_login_success_admin(self):
        response = self.login('admin', 'admin123')
        self.assertEqual(response.status_code, 200)

    def test_login_success_rakepoint(self):
        response = self.login('rakepoint', 'rake123')
        self.assertEqual(response.status_code, 200)

    def test_login_success_warehouse(self):
        response = self.login('warehouse', 'warehouse123')
        self.assertEqual(response.status_code, 200)

    def test_login_success_accountant(self):
        response = self.login('accountant', 'account123')
        self.assertEqual(response.status_code, 200)

    def test_login_failure(self):
        response = self.client.post('/login', data={
            'username': 'admin',
            'password': 'wrongpassword'
        }, follow_redirects=True)
        self.assertIn(b'Invalid username or password', response.data)

    def test_logout(self):
        self.login()
        response = self.logout()
        self.assertEqual(response.status_code, 200)

    def test_unauthenticated_redirect(self):
        """Unauthenticated users should be redirected to login"""
        response = self.client.get('/admin/dashboard')
        self.assertIn(response.status_code, [302, 401])

    def test_index_redirects_to_login(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 302)


class TestAuthorization(BaseTestCase):
    """Test role-based access control"""

    def test_rakepoint_cannot_access_admin(self):
        self.login('rakepoint', 'rake123')
        response = self.client.get('/admin/dashboard', follow_redirects=True)
        self.assertIn(b'Unauthorized', response.data)

    def test_warehouse_cannot_access_admin(self):
        self.login('warehouse', 'warehouse123')
        response = self.client.get('/admin/dashboard', follow_redirects=True)
        self.assertIn(b'Unauthorized', response.data)

    def test_accountant_cannot_access_admin(self):
        self.login('accountant', 'account123')
        response = self.client.get('/admin/dashboard', follow_redirects=True)
        self.assertIn(b'Unauthorized', response.data)

    def test_admin_cannot_access_rakepoint(self):
        self.login('admin', 'admin123')
        response = self.client.get('/rakepoint/dashboard', follow_redirects=True)
        self.assertIn(b'Unauthorized', response.data)

    def test_admin_cannot_access_warehouse(self):
        self.login('admin', 'admin123')
        response = self.client.get('/warehouse/dashboard', follow_redirects=True)
        self.assertIn(b'Unauthorized', response.data)


# ===========================================================================
# 4. SECURITY TESTS
# ===========================================================================
class TestSecurity(BaseTestCase):
    """Test security measures"""

    def test_path_traversal_admin_bill(self):
        """Path traversal attack should be blocked"""
        self.login('admin', 'admin123')
        response = self.client.get('/admin/download-bill/../../etc/passwd')
        # Should NOT serve /etc/passwd; should 302 or 404
        self.assertNotEqual(response.status_code, 200)

    def test_path_traversal_admin_eway_bill(self):
        self.login('admin', 'admin123')
        response = self.client.get('/admin/download-eway-bill/../../database.py')
        self.assertNotEqual(response.status_code, 200)

    def test_path_traversal_rakepoint_bill(self):
        self.login('rakepoint', 'rake123')
        response = self.client.get('/rakepoint/download-bill/../../../etc/shadow')
        self.assertNotEqual(response.status_code, 200)

    def test_path_traversal_warehouse_bill(self):
        self.login('warehouse', 'warehouse123')
        response = self.client.get('/warehouse/download-bill/../../../app.py')
        self.assertNotEqual(response.status_code, 200)

    def test_path_traversal_accountant_bill(self):
        self.login('accountant', 'account123')
        response = self.client.get('/accountant/download-bill/../../../requirements.txt')
        self.assertNotEqual(response.status_code, 200)

    def test_sql_injection_login(self):
        """SQL injection in login should not bypass authentication"""
        response = self.client.post('/login', data={
            'username': "admin' OR '1'='1",
            'password': "anything' OR '1'='1"
        }, follow_redirects=True)
        self.assertIn(b'Invalid username or password', response.data)

    def test_xss_in_flash_messages(self):
        """XSS payload in login should be escaped"""
        response = self.client.post('/login', data={
            'username': '<script>alert("xss")</script>',
            'password': 'test'
        }, follow_redirects=True)
        self.assertNotIn(b'<script>alert("xss")</script>', response.data)


# ===========================================================================
# 5. PERFORMANCE TESTS (Timeout Detection)
# ===========================================================================
class TestPerformance(unittest.TestCase):
    """Test that critical routes execute within Vercel's 10s limit"""

    @classmethod
    def setUpClass(cls):
        cls.test_db_fd, cls.test_db_path = tempfile.mkstemp(suffix='.db')
        os.environ.pop('TURSO_DATABASE_URL', None)
        os.environ.pop('TURSO_AUTH_TOKEN', None)
        app.config['TESTING'] = True

    @classmethod
    def tearDownClass(cls):
        os.close(cls.test_db_fd)
        os.unlink(cls.test_db_path)

    def setUp(self):
        self.db = Database(self.test_db_path)
        self.db.use_cloud = False
        Database._initialized = False
        self.db.initialize_database()

    def test_initialize_database_speed(self):
        """DB initialization should complete in < 5 seconds"""
        Database._initialized = False
        start = time.time()
        self.db.initialize_database()
        elapsed = time.time() - start
        self.assertLess(elapsed, 5.0, f"initialize_database took {elapsed:.2f}s (limit: 5s)")

    def test_dashboard_stats_speed(self):
        """Dashboard stats query should be < 2 seconds"""
        _cache.clear()
        start = time.time()
        stats = self.db.get_dashboard_stats_optimized()
        elapsed = time.time() - start
        self.assertLess(elapsed, 2.0, f"get_dashboard_stats_optimized took {elapsed:.2f}s")

    def test_rakes_with_balances_speed(self):
        """Rakes with balances (limit 5) should be < 2 seconds"""
        _cache.clear()
        start = time.time()
        self.db.get_rakes_with_balances(limit=5)
        elapsed = time.time() - start
        self.assertLess(elapsed, 2.0, f"get_rakes_with_balances took {elapsed:.2f}s")

    def test_daywise_stock_speed(self):
        """Day-wise warehouse stock should be < 2 seconds"""
        start = time.time()
        self.db.get_daywise_warehouse_stock(days=7)
        elapsed = time.time() - start
        self.assertLess(elapsed, 2.0, f"get_daywise_warehouse_stock took {elapsed:.2f}s")

    def test_total_shortage_speed(self):
        start = time.time()
        self.db.get_total_shortage()
        elapsed = time.time() - start
        self.assertLess(elapsed, 1.0, f"get_total_shortage took {elapsed:.2f}s")

    def test_cache_hit_performance(self):
        """Cached responses should be < 1ms"""
        self.db.get_dashboard_stats_optimized()  # Prime cache
        start = time.time()
        self.db.get_dashboard_stats_optimized()  # Should hit cache
        elapsed = time.time() - start
        self.assertLess(elapsed, 0.01, f"Cache hit took {elapsed:.4f}s")


# ===========================================================================
# 6. ROUTE INTEGRATION TESTS
# ===========================================================================
class TestAdminRoutes(BaseTestCase):
    """Test admin routes end-to-end"""

    def test_admin_dashboard_loads(self):
        self.login('admin', 'admin123')
        response = self.client.get('/admin/dashboard')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Admin Dashboard', response.data)

    def test_admin_dashboard_has_daywise_stock(self):
        """Dashboard should show day-wise stock table even with no data"""
        self.login('admin', 'admin123')
        response = self.client.get('/admin/dashboard')
        self.assertIn(b'Day-wise Warehouse Stock', response.data)

    def test_admin_dashboard_no_total_stock_cards(self):
        """Dashboard should NOT show total warehouse stock IN/OUT cards"""
        self.login('admin', 'admin123')
        response = self.client.get('/admin/dashboard')
        self.assertNotIn(b'Total Warehouse Stock IN', response.data)
        self.assertNotIn(b'Total Warehouse Stock OUT', response.data)
        self.assertNotIn(b'Net Warehouse Balance', response.data)

    def test_admin_add_rake_page(self):
        self.login('admin', 'admin123')
        response = self.client.get('/admin/add-rake')
        self.assertEqual(response.status_code, 200)

    def test_admin_summary_page(self):
        self.login('admin', 'admin123')
        response = self.client.get('/admin/summary')
        self.assertEqual(response.status_code, 200)

    def test_admin_manage_accounts(self):
        self.login('admin', 'admin123')
        response = self.client.get('/admin/manage-accounts')
        self.assertEqual(response.status_code, 200)

    def test_admin_all_loading_slips(self):
        self.login('admin', 'admin123')
        response = self.client.get('/admin/all-loading-slips')
        self.assertEqual(response.status_code, 200)

    def test_admin_all_builties(self):
        self.login('admin', 'admin123')
        response = self.client.get('/admin/all-builties')
        self.assertEqual(response.status_code, 200)

    def test_admin_all_ebills(self):
        self.login('admin', 'admin123')
        response = self.client.get('/admin/all-ebills')
        self.assertEqual(response.status_code, 200)

    def test_admin_warehouse_transactions(self):
        self.login('admin', 'admin123')
        response = self.client.get('/admin/warehouse-transactions')
        self.assertEqual(response.status_code, 200)

    def test_admin_warehouse_summary(self):
        self.login('admin', 'admin123')
        response = self.client.get('/admin/warehouse-summary')
        self.assertEqual(response.status_code, 200)

    def test_admin_logistic_bill(self):
        self.login('admin', 'admin123')
        response = self.client.get('/admin/logistic-bill')
        self.assertEqual(response.status_code, 200)

    def test_admin_manage_warehouses(self):
        self.login('admin', 'admin123')
        response = self.client.get('/admin/manage-warehouses')
        self.assertEqual(response.status_code, 200)


class TestRakePointRoutes(BaseTestCase):
    """Test RakePoint routes"""

    def test_rakepoint_dashboard(self):
        self.login('rakepoint', 'rake123')
        response = self.client.get('/rakepoint/dashboard')
        self.assertEqual(response.status_code, 200)

    def test_rakepoint_create_builty_page(self):
        self.login('rakepoint', 'rake123')
        response = self.client.get('/rakepoint/create-builty')
        self.assertEqual(response.status_code, 200)

    def test_rakepoint_create_loading_slip_page(self):
        self.login('rakepoint', 'rake123')
        response = self.client.get('/rakepoint/create-loading-slip')
        self.assertEqual(response.status_code, 200)

    def test_rakepoint_loading_slips(self):
        self.login('rakepoint', 'rake123')
        response = self.client.get('/rakepoint/loading-slips')
        self.assertEqual(response.status_code, 200)

    def test_rakepoint_all_builties(self):
        self.login('rakepoint', 'rake123')
        response = self.client.get('/rakepoint/all-builties')
        self.assertEqual(response.status_code, 200)


class TestWarehouseRoutes(BaseTestCase):
    """Test Warehouse routes"""

    def test_warehouse_dashboard(self):
        self.login('warehouse', 'warehouse123')
        response = self.client.get('/warehouse/dashboard')
        self.assertEqual(response.status_code, 200)

    def test_warehouse_stock_in_page(self):
        self.login('warehouse', 'warehouse123')
        response = self.client.get('/warehouse/stock-in')
        self.assertEqual(response.status_code, 200)

    def test_warehouse_balance(self):
        self.login('warehouse', 'warehouse123')
        response = self.client.get('/warehouse/balance')
        self.assertEqual(response.status_code, 200)

    def test_warehouse_all_builties(self):
        self.login('warehouse', 'warehouse123')
        response = self.client.get('/warehouse/all-builties')
        self.assertEqual(response.status_code, 200)

    def test_warehouse_do_creation(self):
        self.login('warehouse', 'warehouse123')
        response = self.client.get('/warehouse/do-creation')
        self.assertEqual(response.status_code, 200)


class TestAccountantRoutes(BaseTestCase):
    """Test Accountant routes"""

    def test_accountant_dashboard(self):
        self.login('accountant', 'account123')
        response = self.client.get('/accountant/dashboard')
        self.assertEqual(response.status_code, 200)

    def test_accountant_create_ebill_page(self):
        self.login('accountant', 'account123')
        response = self.client.get('/accountant/create-ebill')
        self.assertEqual(response.status_code, 200)

    def test_accountant_all_ebills(self):
        self.login('accountant', 'account123')
        response = self.client.get('/accountant/ebills')
        self.assertEqual(response.status_code, 200)


# ===========================================================================
# 7. API ENDPOINT TESTS
# ===========================================================================
class TestAPIEndpoints(BaseTestCase):
    """Test JSON API endpoints"""

    def test_next_lr_number(self):
        self.login('rakepoint', 'rake123')
        response = self.client.get('/api/next-lr-number')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('next_lr', data)


# ===========================================================================
# 8. VERCEL TIMEOUT SIMULATION TESTS
# ===========================================================================
class TestVercelTimeoutRisk(BaseTestCase):
    """Identify routes at risk of Vercel 10s timeout.
    Each test confirms a route completes within the budget."""

    TIMEOUT_BUDGET = 8.0  # seconds - leave margin for cold start overhead

    def _timed_get(self, url, budget=None):
        budget = budget or self.TIMEOUT_BUDGET
        start = time.time()
        response = self.client.get(url)
        elapsed = time.time() - start
        self.assertLess(
            elapsed, budget,
            f"GET {url} took {elapsed:.2f}s (budget: {budget}s)"
        )
        return response, elapsed

    def test_login_page_timeout(self):
        """Login page (cold start path) should load quickly"""
        resp, t = self._timed_get('/login', budget=3.0)
        self.assertEqual(resp.status_code, 200)

    def test_admin_dashboard_timeout(self):
        self.login('admin', 'admin123')
        resp, t = self._timed_get('/admin/dashboard')
        self.assertEqual(resp.status_code, 200)

    def test_admin_summary_timeout(self):
        self.login('admin', 'admin123')
        resp, t = self._timed_get('/admin/summary')
        self.assertEqual(resp.status_code, 200)

    def test_admin_warehouse_transactions_timeout(self):
        self.login('admin', 'admin123')
        resp, t = self._timed_get('/admin/warehouse-transactions')
        self.assertEqual(resp.status_code, 200)

    def test_admin_warehouse_summary_timeout(self):
        self.login('admin', 'admin123')
        resp, t = self._timed_get('/admin/warehouse-summary')
        self.assertEqual(resp.status_code, 200)

    def test_rakepoint_dashboard_timeout(self):
        self.login('rakepoint', 'rake123')
        resp, t = self._timed_get('/rakepoint/dashboard')
        self.assertEqual(resp.status_code, 200)

    def test_warehouse_dashboard_timeout(self):
        self.login('warehouse', 'warehouse123')
        resp, t = self._timed_get('/warehouse/dashboard')
        self.assertEqual(resp.status_code, 200)

    def test_accountant_dashboard_timeout(self):
        self.login('accountant', 'account123')
        resp, t = self._timed_get('/accountant/dashboard')
        self.assertEqual(resp.status_code, 200)


if __name__ == '__main__':
    unittest.main(verbosity=2)
