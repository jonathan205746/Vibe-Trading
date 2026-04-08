"""Backtest engines.

- BaseEngine: ABC for bar-by-bar execution with market rules
- ChinaAEngine: A-share (T+1, no short, price limits)
- GlobalEquityEngine: US / HK equities
- CryptoEngine: Crypto perpetuals (funding fees, liquidation)
- options_portfolio: European options (Black-Scholes)
"""
