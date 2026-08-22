DROP POLICY IF EXISTS trading_trades_anon_insert ON public.trading_trades;
REVOKE INSERT ON public.trading_trades FROM anon;
