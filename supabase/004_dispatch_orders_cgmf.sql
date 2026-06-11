-- Migration: Add CGMF support to dispatch_orders
-- Allow dispatch orders to target a CGMF society instead of (or in addition to) an account

-- Make account_id nullable so CGMF-only DOs are allowed
ALTER TABLE public.dispatch_orders ALTER COLUMN account_id DROP NOT NULL;

-- Add cgmf_id column referencing the cgmf table
ALTER TABLE public.dispatch_orders
    ADD COLUMN IF NOT EXISTS cgmf_id UUID REFERENCES public.cgmf(id) ON DELETE SET NULL;

-- Index for faster lookups by cgmf
CREATE INDEX IF NOT EXISTS idx_dispatch_orders_cgmf ON public.dispatch_orders(cgmf_id);
