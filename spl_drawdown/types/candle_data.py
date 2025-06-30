from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class CandleData:
    time: Optional[datetime] = None
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    close: Optional[float] = None
    volume: Optional[float] = None
