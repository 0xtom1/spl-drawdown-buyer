from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

import pandas as pd

from spl_drawdown.analyzer.types.cd import CandleData


@dataclass
class TokenData:
    name: Optional[str] = None
    symbol: Optional[str] = None
    mint_address: Optional[str] = None
    buy_time: Optional[datetime] = None
    buy_price_per_token_usd: Optional[float] = None
    candle_data: List[CandleData] = field(default_factory=list)
    next_candle_data: List[CandleData] = field(default_factory=list)

    def __str__(self):
        parts = []
        parts.append(f"Symbol: {self.symbol} - Name: {self.name} - Mint: {self.mint_address}")
        if self.buy_time:
            parts.append(f"\tbuy_time: {self.buy_time.strftime('%Y-%m-%d %H:%M:%S')}")
        if self.buy_price_per_token_usd is not None:
            parts.append(f"\tbuy_price_per_token_usd: ${self.buy_price_per_token_usd:.15f}")
        if self.candle_data:
            df = pd.DataFrame(self.candle_data[-3:])
            df = df.drop(columns=["time_str", "time_unix"], errors="ignore")
            parts.append(f"{df.to_string()}")
        if self.next_candle_data:
            df = pd.DataFrame(self.next_candle_data[:3])
            df = df.drop(columns=["time_str", "time_unix"], errors="ignore")
            parts.append(f"{df.to_string()}")
        return "\n".join(parts) or "HoldingData (empty)"
