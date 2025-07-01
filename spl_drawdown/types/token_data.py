from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from spl_drawdown.types.candle_data import CandleData


@dataclass
class TokenData:
    name: Optional[str] = None
    symbol: Optional[str] = None
    mint_address: Optional[str] = None
    create_date: Optional[datetime] = None
    dex: Optional[str] = None
    volume_usd: Optional[float] = None
    trades_count: Optional[str] = None
    market: Optional[str] = None
    ath_price_usd: Optional[float] = None
    ath_price_time: Optional[datetime] = None
    drawdown_price_usd: Optional[float] = None
    drawdown_price_time: Optional[datetime] = None
    drawdown_percent: Optional[float] = None
    drawdown_consecutive_days_start: Optional[datetime] = None
    candle_data: List[CandleData] = field(default_factory=list)
    current_price_usd: Optional[float] = None
    current_price_time: Optional[datetime] = None

    def __str__(self):
        parts = []
        parts.append(f"Symbol: {self.symbol} - Name: {self.name} - Address: {self.mint_address} - Dex: {self.dex}")

        # Format datetime fields or use 'None' if not set
        ath_time_str = self.ath_price_time.strftime("%Y-%m-%d") if self.ath_price_time else "None"
        drawdown_time_str = self.drawdown_price_time.strftime("%Y-%m-%d") if self.drawdown_price_time else "None"
        drawdown_start_str = (
            self.drawdown_consecutive_days_start.strftime("%Y-%m-%d")
            if self.drawdown_consecutive_days_start
            else "None"
        )
        current_price_time = (
            self.current_price_time.strftime("%Y-%m-%d %H:%M:%S") if self.current_price_time else "None"
        )
        create_date = self.create_date.strftime("%Y-%m-%d %H:%M:%S") if self.create_date else "None"

        # Handle optional numeric fields with formatting
        ath_price_str = f"{self.ath_price_usd:.8f}" if self.ath_price_usd is not None else "None"
        drawdown_price_str = f"{self.drawdown_price_usd:.8f}" if self.drawdown_price_usd is not None else "None"
        drawdown_percent_str = f"{self.drawdown_percent:.8f}" if self.drawdown_percent is not None else "None"
        volume_usd_str = f"{int(self.volume_usd):,}" if self.volume_usd is not None else "None"
        current_price_usd = f"{self.current_price_usd:.8f}" if self.current_price_usd is not None else "None"

        # Summarize candle_data
        if self.candle_data is None:
            candle_count = 0
        else:
            candle_count = len(self.candle_data)

        # Append each field to the parts list
        parts.append(f"  create_date: {create_date}")
        parts.append(f"  volume_usd: {volume_usd_str}")
        parts.append(f"  trades_count: {self.trades_count or 'None'}")
        parts.append(f"  market: {self.market or 'None'}")
        parts.append(f"  ath_price_usd: {ath_price_str}")
        parts.append(f"  ath_price_time: {ath_time_str}")
        parts.append(f"  drawdown_price_usd: {drawdown_price_str}")
        parts.append(f"  drawdown_price_time: {drawdown_time_str}")
        parts.append(f"  drawdown_percent: {drawdown_percent_str}")
        parts.append(f"  drawdown_consecutive_days_start: {drawdown_start_str}")
        parts.append(f"  candle_count: {candle_count}")
        parts.append(f"  current_price_usd: {current_price_usd}")
        parts.append(f"  current_price_time: {current_price_time}")

        max_colon = max([text.find(":") for text in parts[1:]])

        final_parts = ["\n--", parts[0]]
        for each in parts[1:]:
            colon_placement = each.find(":")
            new_string = each[:colon_placement] + (" " * (max_colon - colon_placement)) + each[colon_placement:]
            final_parts.append(new_string)
        final_parts.append("--\n")
        # Join all parts with newlines
        return "\n".join(final_parts)

    def __short_str__(self):
        parts = []
        parts.append(f"Symbol: {self.symbol} - Name: {self.name} - Address: {self.mint_address}")

        # Format datetime fields or use 'None' if not set
        current_price_time = (
            self.current_price_time.strftime("%Y-%m-%d %H:%M:%S") if self.current_price_time else "None"
        )

        # Handle optional numeric fields with formatting
        ath_price_str = f"{self.ath_price_usd:.8f}" if self.ath_price_usd is not None else "None"
        volume_usd_str = f"{int(self.volume_usd):,}" if self.volume_usd is not None else "None"
        current_price_usd = f"{self.current_price_usd:.8f}" if self.current_price_usd is not None else "None"
        if self.current_price_usd is None or self.ath_price_time is None:
            percent_away = 0
        else:
            percent_away = round(((self.ath_price_usd - self.current_price_usd) / self.ath_price_usd) * 100, 2)

        # Append each field to the parts list
        parts.append(f"  volume_usd: {volume_usd_str}")
        parts.append(f"  ath_price_usd: {ath_price_str}")
        parts.append(f"  current_price_usd: {current_price_usd}")
        parts.append(f"  current_price_time: {current_price_time}")
        parts.append(f"  percent_away: {percent_away:.2f}")
        max_colon = max([text.find(":") for text in parts[1:]])

        final_parts = ["\n--", parts[0]]
        for each in parts[1:]:
            colon_placement = each.find(":")
            new_string = each[:colon_placement] + (" " * (max_colon - colon_placement)) + each[colon_placement:]
            final_parts.append(new_string)
        final_parts.append("--\n")
        # Join all parts with newlines
        return "\n".join(final_parts)
