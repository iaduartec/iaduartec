CREATE TABLE IF NOT EXISTS public.trading_trades (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
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
    asset_symbol TEXT UNIQUE NOT NULL,
    status TEXT NOT NULL DEFAULT 'OPEN' CHECK (status IN ('OPEN', 'AT_RISK', 'CLOSED')),
    avg_price NUMERIC NOT NULL,
    total_qty NUMERIC NOT NULL,
    ai_post_mortem TEXT,
    last_checked_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

GRANT INSERT ON public.trading_trades TO anon;
GRANT SELECT, INSERT, UPDATE ON public.trading_trades TO authenticated;
GRANT SELECT, INSERT, UPDATE ON public.position_ots TO authenticated;

ALTER TABLE public.trading_trades ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.position_ots ENABLE ROW LEVEL SECURITY;

CREATE POLICY trading_trades_anon_insert
    ON public.trading_trades FOR INSERT TO anon
    WITH CHECK (true);

CREATE POLICY trading_trades_authenticated_read
    ON public.trading_trades FOR SELECT TO authenticated
    USING (true);

CREATE POLICY position_ots_authenticated_access
    ON public.position_ots FOR ALL TO authenticated
    USING (true) WITH CHECK (true);
