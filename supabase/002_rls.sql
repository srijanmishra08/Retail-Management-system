-- Helper: check current user's role
-- Usage: (SELECT role FROM public.profiles WHERE id = auth.uid()) = 'rakepoint'

-- 1) profiles
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;

CREATE POLICY "profiles_select_own" ON public.profiles
  FOR SELECT TO authenticated
  USING (id = auth.uid());

-- 2) products
ALTER TABLE public.products ENABLE ROW LEVEL SECURITY;

CREATE POLICY "products_admin_all" ON public.products
  FOR ALL TO authenticated
  USING (
    EXISTS (
      SELECT 1
      FROM public.profiles
      WHERE id = auth.uid() AND role = 'admin'
    )
  )
  WITH CHECK (
    EXISTS (
      SELECT 1
      FROM public.profiles
      WHERE id = auth.uid() AND role = 'admin'
    )
  );

CREATE POLICY "products_select_non_admin_roles" ON public.products
  FOR SELECT TO authenticated
  USING (
    EXISTS (
      SELECT 1
      FROM public.profiles
      WHERE id = auth.uid() AND role IN ('rakepoint', 'warehouse', 'accountant')
    )
  );

-- 3) companies
ALTER TABLE public.companies ENABLE ROW LEVEL SECURITY;

CREATE POLICY "companies_admin_all" ON public.companies
  FOR ALL TO authenticated
  USING (
    EXISTS (
      SELECT 1
      FROM public.profiles
      WHERE id = auth.uid() AND role = 'admin'
    )
  )
  WITH CHECK (
    EXISTS (
      SELECT 1
      FROM public.profiles
      WHERE id = auth.uid() AND role = 'admin'
    )
  );

CREATE POLICY "companies_select_non_admin_roles" ON public.companies
  FOR SELECT TO authenticated
  USING (
    EXISTS (
      SELECT 1
      FROM public.profiles
      WHERE id = auth.uid() AND role IN ('rakepoint', 'warehouse', 'accountant')
    )
  );

-- 4) employees
ALTER TABLE public.employees ENABLE ROW LEVEL SECURITY;

CREATE POLICY "employees_admin_all" ON public.employees
  FOR ALL TO authenticated
  USING (
    EXISTS (
      SELECT 1
      FROM public.profiles
      WHERE id = auth.uid() AND role = 'admin'
    )
  )
  WITH CHECK (
    EXISTS (
      SELECT 1
      FROM public.profiles
      WHERE id = auth.uid() AND role = 'admin'
    )
  );

CREATE POLICY "employees_warehouse_select" ON public.employees
  FOR SELECT TO authenticated
  USING (
    EXISTS (
      SELECT 1
      FROM public.profiles
      WHERE id = auth.uid() AND role = 'warehouse'
    )
  );

CREATE POLICY "employees_warehouse_insert" ON public.employees
  FOR INSERT TO authenticated
  WITH CHECK (
    EXISTS (
      SELECT 1
      FROM public.profiles
      WHERE id = auth.uid() AND role = 'warehouse'
    )
  );

-- 5) cgmf
ALTER TABLE public.cgmf ENABLE ROW LEVEL SECURITY;

CREATE POLICY "cgmf_admin_all" ON public.cgmf
  FOR ALL TO authenticated
  USING (
    EXISTS (
      SELECT 1
      FROM public.profiles
      WHERE id = auth.uid() AND role = 'admin'
    )
  )
  WITH CHECK (
    EXISTS (
      SELECT 1
      FROM public.profiles
      WHERE id = auth.uid() AND role = 'admin'
    )
  );

CREATE POLICY "cgmf_rakepoint_select" ON public.cgmf
  FOR SELECT TO authenticated
  USING (
    EXISTS (
      SELECT 1
      FROM public.profiles
      WHERE id = auth.uid() AND role = 'rakepoint'
    )
  );

CREATE POLICY "cgmf_rakepoint_insert" ON public.cgmf
  FOR INSERT TO authenticated
  WITH CHECK (
    EXISTS (
      SELECT 1
      FROM public.profiles
      WHERE id = auth.uid() AND role = 'rakepoint'
    )
  );

CREATE POLICY "cgmf_other_roles_select" ON public.cgmf
  FOR SELECT TO authenticated
  USING (
    EXISTS (
      SELECT 1
      FROM public.profiles
      WHERE id = auth.uid() AND role IN ('warehouse', 'accountant')
    )
  );

-- 6) rakes
ALTER TABLE public.rakes ENABLE ROW LEVEL SECURITY;

CREATE POLICY "rakes_admin_all" ON public.rakes
  FOR ALL TO authenticated
  USING (
    EXISTS (
      SELECT 1
      FROM public.profiles
      WHERE id = auth.uid() AND role = 'admin'
    )
  )
  WITH CHECK (
    EXISTS (
      SELECT 1
      FROM public.profiles
      WHERE id = auth.uid() AND role = 'admin'
    )
  );

CREATE POLICY "rakes_select_non_admin_roles" ON public.rakes
  FOR SELECT TO authenticated
  USING (
    EXISTS (
      SELECT 1
      FROM public.profiles
      WHERE id = auth.uid() AND role IN ('rakepoint', 'warehouse', 'accountant')
    )
  );

-- 7) rake_products
ALTER TABLE public.rake_products ENABLE ROW LEVEL SECURITY;

CREATE POLICY "rake_products_admin_all" ON public.rake_products
  FOR ALL TO authenticated
  USING (
    EXISTS (
      SELECT 1
      FROM public.profiles
      WHERE id = auth.uid() AND role = 'admin'
    )
  )
  WITH CHECK (
    EXISTS (
      SELECT 1
      FROM public.profiles
      WHERE id = auth.uid() AND role = 'admin'
    )
  );

CREATE POLICY "rake_products_select_non_admin_roles" ON public.rake_products
  FOR SELECT TO authenticated
  USING (
    EXISTS (
      SELECT 1
      FROM public.profiles
      WHERE id = auth.uid() AND role IN ('rakepoint', 'warehouse', 'accountant')
    )
  );

-- 8) accounts
ALTER TABLE public.accounts ENABLE ROW LEVEL SECURITY;

CREATE POLICY "accounts_admin_all" ON public.accounts
  FOR ALL TO authenticated
  USING (
    EXISTS (
      SELECT 1
      FROM public.profiles
      WHERE id = auth.uid() AND role = 'admin'
    )
  )
  WITH CHECK (
    EXISTS (
      SELECT 1
      FROM public.profiles
      WHERE id = auth.uid() AND role = 'admin'
    )
  );

CREATE POLICY "accounts_rakepoint_select" ON public.accounts
  FOR SELECT TO authenticated
  USING (
    EXISTS (
      SELECT 1
      FROM public.profiles
      WHERE id = auth.uid() AND role = 'rakepoint'
    )
  );

CREATE POLICY "accounts_rakepoint_insert" ON public.accounts
  FOR INSERT TO authenticated
  WITH CHECK (
    EXISTS (
      SELECT 1
      FROM public.profiles
      WHERE id = auth.uid() AND role = 'rakepoint'
    )
  );

CREATE POLICY "accounts_other_roles_select" ON public.accounts
  FOR SELECT TO authenticated
  USING (
    EXISTS (
      SELECT 1
      FROM public.profiles
      WHERE id = auth.uid() AND role IN ('warehouse', 'accountant')
    )
  );

-- 9) warehouses
ALTER TABLE public.warehouses ENABLE ROW LEVEL SECURITY;

CREATE POLICY "warehouses_admin_all" ON public.warehouses
  FOR ALL TO authenticated
  USING (
    EXISTS (
      SELECT 1
      FROM public.profiles
      WHERE id = auth.uid() AND role = 'admin'
    )
  )
  WITH CHECK (
    EXISTS (
      SELECT 1
      FROM public.profiles
      WHERE id = auth.uid() AND role = 'admin'
    )
  );

CREATE POLICY "warehouses_select_non_admin_roles" ON public.warehouses
  FOR SELECT TO authenticated
  USING (
    EXISTS (
      SELECT 1
      FROM public.profiles
      WHERE id = auth.uid() AND role IN ('rakepoint', 'warehouse', 'accountant')
    )
  );

-- 10) trucks
ALTER TABLE public.trucks ENABLE ROW LEVEL SECURITY;

CREATE POLICY "trucks_admin_all" ON public.trucks
  FOR ALL TO authenticated
  USING (
    EXISTS (
      SELECT 1
      FROM public.profiles
      WHERE id = auth.uid() AND role = 'admin'
    )
  )
  WITH CHECK (
    EXISTS (
      SELECT 1
      FROM public.profiles
      WHERE id = auth.uid() AND role = 'admin'
    )
  );

CREATE POLICY "trucks_rakepoint_select" ON public.trucks
  FOR SELECT TO authenticated
  USING (
    EXISTS (
      SELECT 1
      FROM public.profiles
      WHERE id = auth.uid() AND role = 'rakepoint'
    )
  );

CREATE POLICY "trucks_rakepoint_insert" ON public.trucks
  FOR INSERT TO authenticated
  WITH CHECK (
    EXISTS (
      SELECT 1
      FROM public.profiles
      WHERE id = auth.uid() AND role = 'rakepoint'
    )
  );

CREATE POLICY "trucks_other_roles_select" ON public.trucks
  FOR SELECT TO authenticated
  USING (
    EXISTS (
      SELECT 1
      FROM public.profiles
      WHERE id = auth.uid() AND role IN ('warehouse', 'accountant')
    )
  );

-- 11) builty
ALTER TABLE public.builty ENABLE ROW LEVEL SECURITY;

CREATE POLICY "builty_admin_all" ON public.builty
  FOR ALL TO authenticated
  USING (
    EXISTS (
      SELECT 1
      FROM public.profiles
      WHERE id = auth.uid() AND role = 'admin'
    )
  )
  WITH CHECK (
    EXISTS (
      SELECT 1
      FROM public.profiles
      WHERE id = auth.uid() AND role = 'admin'
    )
  );

CREATE POLICY "builty_select_non_admin_roles" ON public.builty
  FOR SELECT TO authenticated
  USING (
    EXISTS (
      SELECT 1
      FROM public.profiles
      WHERE id = auth.uid() AND role IN ('rakepoint', 'warehouse', 'accountant')
    )
  );

CREATE POLICY "builty_rakepoint_insert" ON public.builty
  FOR INSERT TO authenticated
  WITH CHECK (
    EXISTS (
      SELECT 1
      FROM public.profiles
      WHERE id = auth.uid() AND role = 'rakepoint'
    )
    AND created_by_role = 'rakepoint'
  );

CREATE POLICY "builty_warehouse_insert" ON public.builty
  FOR INSERT TO authenticated
  WITH CHECK (
    EXISTS (
      SELECT 1
      FROM public.profiles
      WHERE id = auth.uid() AND role = 'warehouse'
    )
    AND created_by_role = 'warehouse'
  );

-- 12) loading_slips
ALTER TABLE public.loading_slips ENABLE ROW LEVEL SECURITY;

CREATE POLICY "loading_slips_admin_all" ON public.loading_slips
  FOR ALL TO authenticated
  USING (
    EXISTS (
      SELECT 1
      FROM public.profiles
      WHERE id = auth.uid() AND role = 'admin'
    )
  )
  WITH CHECK (
    EXISTS (
      SELECT 1
      FROM public.profiles
      WHERE id = auth.uid() AND role = 'admin'
    )
  );

CREATE POLICY "loading_slips_rakepoint_select" ON public.loading_slips
  FOR SELECT TO authenticated
  USING (
    EXISTS (
      SELECT 1
      FROM public.profiles
      WHERE id = auth.uid() AND role = 'rakepoint'
    )
  );

CREATE POLICY "loading_slips_rakepoint_insert" ON public.loading_slips
  FOR INSERT TO authenticated
  WITH CHECK (
    EXISTS (
      SELECT 1
      FROM public.profiles
      WHERE id = auth.uid() AND role = 'rakepoint'
    )
  );

-- 12b) loading_slip_products
ALTER TABLE public.loading_slip_products ENABLE ROW LEVEL SECURITY;

CREATE POLICY "loading_slip_products_admin_all" ON public.loading_slip_products
  FOR ALL TO authenticated
  USING (
    EXISTS (
      SELECT 1
      FROM public.profiles
      WHERE id = auth.uid() AND role = 'admin'
    )
  )
  WITH CHECK (
    EXISTS (
      SELECT 1
      FROM public.profiles
      WHERE id = auth.uid() AND role = 'admin'
    )
  );

CREATE POLICY "loading_slip_products_warehouse_select" ON public.loading_slip_products
  FOR SELECT TO authenticated
  USING (
    EXISTS (
      SELECT 1
      FROM public.profiles
      WHERE id = auth.uid() AND role IN ('warehouse', 'rakepoint', 'accountant')
    )
  );

CREATE POLICY "loading_slip_products_warehouse_insert" ON public.loading_slip_products
  FOR INSERT TO authenticated
  WITH CHECK (
    EXISTS (
      SELECT 1
      FROM public.profiles
      WHERE id = auth.uid() AND role = 'warehouse'
    )
  );

-- 13) warehouse_stock
ALTER TABLE public.warehouse_stock ENABLE ROW LEVEL SECURITY;

CREATE POLICY "warehouse_stock_admin_all" ON public.warehouse_stock
  FOR ALL TO authenticated
  USING (
    EXISTS (
      SELECT 1
      FROM public.profiles
      WHERE id = auth.uid() AND role = 'admin'
    )
  )
  WITH CHECK (
    EXISTS (
      SELECT 1
      FROM public.profiles
      WHERE id = auth.uid() AND role = 'admin'
    )
  );

CREATE POLICY "warehouse_stock_select_roles" ON public.warehouse_stock
  FOR SELECT TO authenticated
  USING (
    EXISTS (
      SELECT 1
      FROM public.profiles
      WHERE id = auth.uid() AND role IN ('warehouse', 'accountant')
    )
  );

CREATE POLICY "warehouse_stock_warehouse_insert" ON public.warehouse_stock
  FOR INSERT TO authenticated
  WITH CHECK (
    EXISTS (
      SELECT 1
      FROM public.profiles
      WHERE id = auth.uid() AND role = 'warehouse'
    )
  );

-- 14) ebills
ALTER TABLE public.ebills ENABLE ROW LEVEL SECURITY;

CREATE POLICY "ebills_admin_all" ON public.ebills
  FOR ALL TO authenticated
  USING (
    EXISTS (
      SELECT 1
      FROM public.profiles
      WHERE id = auth.uid() AND role = 'admin'
    )
  )
  WITH CHECK (
    EXISTS (
      SELECT 1
      FROM public.profiles
      WHERE id = auth.uid() AND role = 'admin'
    )
  );

CREATE POLICY "ebills_accountant_all" ON public.ebills
  FOR ALL TO authenticated
  USING (
    EXISTS (
      SELECT 1
      FROM public.profiles
      WHERE id = auth.uid() AND role = 'accountant'
    )
  )
  WITH CHECK (
    EXISTS (
      SELECT 1
      FROM public.profiles
      WHERE id = auth.uid() AND role = 'accountant'
    )
  );

CREATE POLICY "ebills_rakepoint_select" ON public.ebills
  FOR SELECT TO authenticated
  USING (
    EXISTS (
      SELECT 1
      FROM public.profiles
      WHERE id = auth.uid() AND role = 'rakepoint'
    )
  );

-- 15) rake_bill_payments
ALTER TABLE public.rake_bill_payments ENABLE ROW LEVEL SECURITY;

CREATE POLICY "rake_bill_payments_admin_all" ON public.rake_bill_payments
  FOR ALL TO authenticated
  USING (
    EXISTS (
      SELECT 1
      FROM public.profiles
      WHERE id = auth.uid() AND role = 'admin'
    )
  )
  WITH CHECK (
    EXISTS (
      SELECT 1
      FROM public.profiles
      WHERE id = auth.uid() AND role = 'admin'
    )
  );

CREATE POLICY "rake_bill_payments_rakepoint_select" ON public.rake_bill_payments
  FOR SELECT TO authenticated
  USING (
    EXISTS (
      SELECT 1
      FROM public.profiles
      WHERE id = auth.uid() AND role = 'rakepoint'
    )
  );

CREATE POLICY "rake_bill_payments_accountant_select" ON public.rake_bill_payments
  FOR SELECT TO authenticated
  USING (
    EXISTS (
      SELECT 1
      FROM public.profiles
      WHERE id = auth.uid() AND role = 'accountant'
    )
  );
