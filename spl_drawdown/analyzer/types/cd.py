from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class CandleData:
    time: Optional[datetime] = None
    time_str: Optional[str] = None
    time_unix: Optional[int] = None
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    close: Optional[float] = None
    volume: Optional[float] = None
    vol_l3: Optional[float] = None
    vol_l3_24avg: Optional[float] = None
    vol_l3_168avg: Optional[float] = None
    ema24: Optional[float] = None
    ma24: Optional[float] = None
    ma168: Optional[float] = None
    per_l3: Optional[float] = None
    per_l24: Optional[float] = None
