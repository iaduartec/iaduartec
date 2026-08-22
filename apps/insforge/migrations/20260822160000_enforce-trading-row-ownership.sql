-- Close cross-user access left by the initial trading-table policies.
-- Existing rows without an owner remain inaccessible until they are explicitly
-- assigned by a trusted migration or service; they are never made public.

ALTER TABLE public.trading_trades
    ADD COLUMN IF NOT EXISTS owner_id UUID REFERENCES auth.users(id);

ALTER TABLE public.position_ots
    ADD COLUMN IF NOT EXISTS owner_id UUID REFERENCES auth.users(id);

ALTER TABLE public.position_ots
    DROP CONSTRAINT IF EXISTS position_ots_asset_symbol_key;

CREATE INDEX IF NOT EXISTS trading_trades_owner_id_idx
    ON public.trading_trades (owner_id);

CREATE INDEX IF NOT EXISTS position_ots_owner_id_idx
    ON public.position_ots (owner_id);

CREATE UNIQUE INDEX IF NOT EXISTS position_ots_owner_asset_symbol_uidx
    ON public.position_ots (owner_id, asset_symbol);

DROP POLICY IF EXISTS trading_trades_authenticated_read ON public.trading_trades;
DROP POLICY IF EXISTS trading_trades_authenticated_write ON public.trading_trades;
DROP POLICY IF EXISTS position_ots_authenticated_access ON public.position_ots;

CREATE POLICY trading_trades_authenticated_read
    ON public.trading_trades FOR SELECT TO authenticated
    USING (owner_id = auth.uid());

CREATE POLICY trading_trades_authenticated_write
    ON public.trading_trades FOR INSERT TO authenticated
    WITH CHECK (owner_id = auth.uid());

CREATE POLICY trading_trades_authenticated_update
    ON public.trading_trades FOR UPDATE TO authenticated
    USING (owner_id = auth.uid())
    WITH CHECK (owner_id = auth.uid());

CREATE POLICY position_ots_authenticated_access
    ON public.position_ots FOR ALL TO authenticated
    USING (owner_id = auth.uid())
    WITH CHECK (owner_id = auth.uid());
