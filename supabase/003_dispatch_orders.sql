-- 003_dispatch_orders.sql
-- Dispatch Orders: admin pre-commits quantity per account per rake
-- Run this migration on Supabase after 001_schema.sql

CREATE TABLE IF NOT EXISTS public.dispatch_orders (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  account_id    UUID NOT NULL REFERENCES public.accounts(id) ON DELETE CASCADE,
  rake_code     TEXT NOT NULL REFERENCES public.rakes(rake_code) ON DELETE CASCADE,
  product_name  TEXT NOT NULL,
  quantity_bags INTEGER NOT NULL DEFAULT 0,
  quantity_mt   NUMERIC(10,2) NOT NULL,
  notes         TEXT,
  created_by    TEXT,
  created_at    TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_dispatch_orders_account ON public.dispatch_orders(account_id);
CREATE INDEX IF NOT EXISTS idx_dispatch_orders_rake    ON public.dispatch_orders(rake_code);
CREATE INDEX IF NOT EXISTS idx_dispatch_orders_created ON public.dispatch_orders(created_at DESC);
