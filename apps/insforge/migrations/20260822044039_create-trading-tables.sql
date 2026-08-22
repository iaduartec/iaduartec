CREATE TABLE IF NOT EXISTS public.trading_trades (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id UUID REFERENCES auth.users(id),
    asset_symbol TEXT NOT NULL,
    side TEXT NOT NULL CHECK (side IN ('BUY', 'SELL')),
    quantity NUMERIC NOT NULL CHECK (quantity > 0),
    price NUMERIC NOT NULL CHECK (price >= 0),
    currency TEXT NOT NULL DEFAULT 'USD',
    executed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    source TEXT NOT NULL DEFAULT 'revolut_email'
);

CREATE TABLE IF NOT EXISTS public.position_ots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id UUID REFERENCES auth.users(id),
    asset_symbol TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'OPEN' CHECK (status IN ('OPEN', 'AT_RISK', 'CLOSED')),
    avg_price NUMERIC NOT NULL,
    total_qty NUMERIC NOT NULL,
    ai_post_mortem TEXT,
    last_checked_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS position_ots_owner_asset_symbol_uidx
    ON public.position_ots (owner_id, asset_symbol);

GRANT SELECT, INSERT, UPDATE ON public.trading_trades TO authenticated;
GRANT SELECT, INSERT, UPDATE ON public.position_ots TO authenticated;

ALTER TABLE public.trading_trades ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.position_ots ENABLE ROW LEVEL SECURITY;

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
