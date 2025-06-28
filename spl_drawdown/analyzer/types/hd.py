from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class HoldingData:
    name: Optional[str] = None
    symbol: Optional[str] = None
    address: Optional[str] = None
    mint: Optional[str] = None
    decimals: Optional[int] = None
    current_amount_raw: Optional[int] = None
    current_amount: Optional[float] = None
    current_price_per_token_usd: Optional[float] = None
    current_price_per_token_sol: Optional[float] = None
    current_value_sol: Optional[float] = None
    total_return_sol: Optional[float] = None
    buy_time: Optional[datetime] = None
    buy_duration_hours: Optional[int] = None
    buy_amount: Optional[int] = 0
    buy_price_per_token_usd: Optional[float] = None
    buy_price_per_token_sol: Optional[float] = None
    buy_price_usd_total: Optional[float] = 0
    buy_price_sol_total: Optional[float] = 0
    sell_count: Optional[int] = 0
    sell_amount_mint: Optional[float] = 0
    sell_amount_sol: Optional[float] = 0
    sell_percent: Optional[float] = None
    sell_percent_remaining: Optional[float] = None
    initial_stop_price_usd: Optional[float] = None
    stop_price_usd: Optional[float] = None

    def __str__(self):
        parts = []
        parts.append(f"Symbol: {self.symbol} - Name: {self.name} - Address: {self.address} - Mint: {self.mint}")
        parts.append(f"\tdecimals: {self.decimals}")
        parts.append(f"\tcurrent_amount_raw: {self.current_amount_raw}")
        if self.current_amount is not None:
            parts.append(f"\tcurrent_amount: {self.current_amount:.2f}")
        if self.current_price_per_token_usd is not None:
            parts.append(f"\tcurrent_price_per_token_usd: ${self.current_price_per_token_usd:.15f}")
        if self.current_price_per_token_sol is not None:
            parts.append(f"\tcurrent_price_per_token_sol: {self.current_price_per_token_sol:.15f}")
        if self.current_value_sol is not None:
            parts.append(f"\tcurrent_value_sol: {self.current_value_sol:.2f}")
        if self.total_return_sol is not None:
            parts.append(f"\ttotal_return_sol: {self.total_return_sol:.2f}")
        if self.buy_time:
            parts.append(f"\tbuy_time: {self.buy_time.strftime('%Y-%m-%d %H:%M:%S')}")
        if self.buy_duration_hours is not None:
            parts.append(f"\tbuy_duration_hours: {self.buy_duration_hours}")
        if self.buy_amount is not None:
            parts.append(f"\tbuy_amount: {self.buy_amount}")
        if self.buy_price_per_token_usd is not None:
            parts.append(f"\tbuy_price_per_token_usd: ${self.buy_price_per_token_usd:.15f}")
        if self.buy_price_per_token_sol is not None:
            parts.append(f"\tbuy_price_per_token_sol: {self.buy_price_per_token_sol:.15f}")
        if self.buy_price_usd_total is not None:
            parts.append(f"\tbuy_price_usd_total: ${self.buy_price_usd_total:.2f}")
        if self.buy_price_sol_total is not None:
            parts.append(f"\tbuy_price_sol_total: {self.buy_price_sol_total:.4f}")
        if self.sell_count is not None:
            parts.append(f"\tsell_count: {self.sell_count}")
        if self.sell_amount_mint is not None:
            parts.append(f"\tsell_amount_mint: {self.sell_amount_mint:.2f}")
        if self.sell_amount_sol is not None:
            parts.append(f"\tsell_amount_sol: {self.sell_amount_sol:.4f}")
        if self.sell_percent is not None:
            parts.append(f"\tsell_percent: {self.sell_percent*100:.2f}%")
        if self.sell_percent_remaining is not None:
            parts.append(f"\tsell_percent_remaining: {self.sell_percent_remaining*100:.2f}%")
        if self.initial_stop_price_usd is not None:
            parts.append(f"\tinitial_stop_price_usd: ${self.initial_stop_price_usd:.10f}")
        if self.stop_price_usd is not None:
            parts.append(f"\tstop_price_usd: ${self.stop_price_usd:.10f}")
        return "\n".join(parts) or "HoldingData (empty)"
