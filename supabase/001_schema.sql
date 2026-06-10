CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Enums
CREATE TYPE user_role AS ENUM ('admin', 'rakepoint', 'warehouse', 'accountant');
CREATE TYPE builty_source AS ENUM ('rakepoint', 'warehouse');
CREATE TYPE stock_movement AS ENUM ('IN', 'OUT');
CREATE TYPE account_type AS ENUM ('Dealer', 'Retailer', 'Company', 'Government', 'Payal');
CREATE TYPE ebill_status AS ENUM ('pending', 'uploaded');
CREATE TYPE stock_source AS ENUM ('rake', 'transfer');

-- 1) profiles
CREATE TABLE public.profiles (
  id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  role user_role NOT NULL,
  full_name TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2) products
CREATE TABLE public.products (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  product_name TEXT NOT NULL UNIQUE,
  product_code TEXT,
  product_type TEXT DEFAULT 'Fertilizer',
  unit TEXT DEFAULT 'MT',
  unit_per_bag NUMERIC(10,3) DEFAULT 50.0,
  unit_type TEXT DEFAULT 'kg',
  description TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3) companies
CREATE TABLE public.companies (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  company_name TEXT NOT NULL UNIQUE,
  company_code TEXT,
  contact_person TEXT,
  mobile TEXT,
  address TEXT,
  distance NUMERIC(10,2) DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4) employees
CREATE TABLE public.employees (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  employee_name TEXT NOT NULL,
  employee_code TEXT,
  mobile TEXT,
  designation TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 5) cgmf
CREATE TABLE public.cgmf (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  district TEXT NOT NULL,
  destination TEXT NOT NULL,
  society_name TEXT NOT NULL,
  contact TEXT,
  distance NUMERIC(10,2) DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 6) rakes
CREATE TABLE public.rakes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  rake_code TEXT UNIQUE NOT NULL,
  company_name TEXT NOT NULL,
  company_code TEXT,
  product_name TEXT NOT NULL,
  product_code TEXT,
  rr_quantity NUMERIC(10,2) NOT NULL,
  rake_point_name TEXT NOT NULL,
  head TEXT,
  subhead TEXT,
  is_closed BOOLEAN DEFAULT FALSE,
  closed_at TIMESTAMPTZ,
  shortage NUMERIC(10,2) DEFAULT 0,
  date DATE NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 7) rake_products
CREATE TABLE public.rake_products (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  rake_code TEXT NOT NULL REFERENCES public.rakes(rake_code),
  product_id UUID NOT NULL REFERENCES public.products(id),
  product_name TEXT NOT NULL,
  product_code TEXT,
  quantity_mt NUMERIC(10,2) DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 8) accounts
CREATE TABLE public.accounts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  account_name TEXT NOT NULL,
  account_type account_type NOT NULL,
  contact TEXT,
  address TEXT,
  distance NUMERIC(10,2) DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 9) warehouses
CREATE TABLE public.warehouses (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  warehouse_name TEXT NOT NULL,
  location TEXT,
  capacity NUMERIC(10,2),
  distance NUMERIC(10,2) DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 10) trucks
CREATE TABLE public.trucks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  truck_number TEXT UNIQUE NOT NULL,
  driver_name TEXT,
  driver_mobile TEXT,
  owner_name TEXT,
  owner_mobile TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 11) builty
-- NOTE: rake_code is NULL for warehouse-outgoing (secondary) builties.
--       These are secondary dispatch events and must NOT count against the rake's RR balance.
CREATE TABLE public.builty (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  builty_number TEXT UNIQUE NOT NULL,
  rake_code TEXT REFERENCES public.rakes(rake_code),
  date DATE NOT NULL,
  rake_point_name TEXT,
  account_id UUID REFERENCES public.accounts(id),
  warehouse_id UUID REFERENCES public.warehouses(id),
  cgmf_id UUID REFERENCES public.cgmf(id),
  truck_id UUID NOT NULL REFERENCES public.trucks(id),
  loading_point TEXT NOT NULL,
  unloading_point TEXT NOT NULL,
  goods_name TEXT NOT NULL,
  number_of_bags INTEGER NOT NULL,
  quantity_mt NUMERIC(10,2) NOT NULL,
  kg_per_bag NUMERIC(10,3),
  rate_per_mt NUMERIC(10,2),
  total_freight NUMERIC(10,2),
  advance NUMERIC(10,2) DEFAULT 0,
  to_pay NUMERIC(10,2) DEFAULT 0,
  lr_number TEXT,
  lr_index INTEGER,
  created_by_role builty_source NOT NULL,
  sub_head TEXT,
  receiver_name TEXT,
  received_quantity NUMERIC(10,2),
  supply_term TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 12) loading_slips
-- NOTE: rake_code is NOT NULL with FK to rakes(rake_code).
--       Warehouse-generated loading slips use the sentinel value 'WAREHOUSE'
--       (a placeholder rake inserted at DB init) so the NOT NULL constraint is satisfied.
--       All balance queries filter this sentinel out: WHERE rake_code != 'WAREHOUSE'
--       or by querying specific rake codes that will never equal 'WAREHOUSE'.
CREATE TABLE public.loading_slips (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  rake_code TEXT NOT NULL REFERENCES public.rakes(rake_code),
  slip_number INTEGER NOT NULL,
  loading_point_name TEXT NOT NULL,
  destination TEXT NOT NULL,
  account_id UUID REFERENCES public.accounts(id),
  warehouse_id UUID REFERENCES public.warehouses(id),
  cgmf_id UUID REFERENCES public.cgmf(id),
  quantity_bags INTEGER NOT NULL,
  quantity_mt NUMERIC(10,2) NOT NULL,
  truck_id UUID NOT NULL REFERENCES public.trucks(id),
  wagon_number TEXT,
  goods_name TEXT,
  truck_driver TEXT,
  truck_owner TEXT,
  mobile_number_1 TEXT,
  mobile_number_2 TEXT,
  truck_details TEXT,
  builty_id UUID REFERENCES public.builty(id),
  sub_head TEXT,
  warehouse_account_id UUID REFERENCES public.accounts(id),
  warehouse_account_type TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 12b) loading_slip_products
CREATE TABLE public.loading_slip_products (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  loading_slip_id UUID NOT NULL REFERENCES public.loading_slips(id) ON DELETE CASCADE,
  product_id UUID REFERENCES public.products(id),
  product_name TEXT NOT NULL,
  quantity_bags INTEGER NOT NULL DEFAULT 0,
  quantity_mt NUMERIC(10,2) NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 13) warehouse_stock
CREATE TABLE public.warehouse_stock (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  serial_number INTEGER,
  warehouse_id UUID NOT NULL REFERENCES public.warehouses(id),
  builty_id UUID REFERENCES public.builty(id),
  company_id UUID REFERENCES public.companies(id),
  product_id UUID REFERENCES public.products(id),
  transaction_type stock_movement NOT NULL,
  quantity_mt NUMERIC(10,2) NOT NULL,
  employee_id UUID REFERENCES public.employees(id),
  account_id UUID REFERENCES public.accounts(id),
  cgmf_id UUID REFERENCES public.cgmf(id),
  account_type TEXT,
  dealer_name TEXT,
  source_type stock_source DEFAULT 'rake',
  truck_id UUID REFERENCES public.trucks(id),
  date DATE NOT NULL,
  notes TEXT,
  remark TEXT,
  sub_head TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 14) ebills
CREATE TABLE public.ebills (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  builty_id UUID NOT NULL UNIQUE REFERENCES public.builty(id),
  ebill_number TEXT UNIQUE NOT NULL,
  amount NUMERIC(12,2) NOT NULL,
  tax_amount NUMERIC(12,2),
  eway_bill_number TEXT,
  eway_bill_pdf TEXT,
  bill_pdf TEXT,
  generated_date DATE NOT NULL,
  status ebill_status DEFAULT 'pending',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 15) rake_bill_payments
CREATE TABLE public.rake_bill_payments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  rake_code TEXT NOT NULL UNIQUE REFERENCES public.rakes(rake_code),
  total_bill_amount NUMERIC(12,2) DEFAULT 0,
  received_amount NUMERIC(12,2) DEFAULT 0,
  remaining_amount NUMERIC(12,2) DEFAULT 0,
  last_updated TIMESTAMPTZ DEFAULT NOW(),
  updated_by UUID REFERENCES public.profiles(id),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Auto-profile trigger
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS trigger AS $$
BEGIN
  INSERT INTO public.profiles (id, role, full_name)
  VALUES (
    NEW.id,
    (NEW.raw_user_meta_data->>'role')::user_role,
    NEW.raw_user_meta_data->>'full_name'
  );
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE OR REPLACE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- Indexes
CREATE INDEX idx_rakes_company_name ON public.rakes(company_name);
CREATE INDEX idx_rakes_is_closed ON public.rakes(is_closed);

CREATE INDEX idx_builty_created_by_role ON public.builty(created_by_role);
CREATE INDEX idx_builty_warehouse_id ON public.builty(warehouse_id);
CREATE INDEX idx_builty_account_id ON public.builty(account_id);
CREATE INDEX idx_builty_rake_code ON public.builty(rake_code);

CREATE INDEX idx_loading_slips_cgmf_id ON public.loading_slips(cgmf_id);
CREATE INDEX idx_loading_slips_warehouse_id ON public.loading_slips(warehouse_id);
CREATE INDEX idx_loading_slips_account_id ON public.loading_slips(account_id);
CREATE INDEX idx_loading_slips_rake_code ON public.loading_slips(rake_code);

CREATE INDEX idx_warehouse_stock_account_id ON public.warehouse_stock(account_id);
CREATE INDEX idx_warehouse_stock_date ON public.warehouse_stock(date);
CREATE INDEX idx_warehouse_stock_transaction_type ON public.warehouse_stock(transaction_type);
CREATE INDEX idx_warehouse_stock_builty_id ON public.warehouse_stock(builty_id);
CREATE INDEX idx_warehouse_stock_warehouse_id ON public.warehouse_stock(warehouse_id);

CREATE INDEX idx_loading_slip_products_slip_id ON public.loading_slip_products(loading_slip_id);

CREATE INDEX idx_ebills_builty_id ON public.ebills(builty_id);

CREATE INDEX idx_rake_bill_payments_rake_code ON public.rake_bill_payments(rake_code);
