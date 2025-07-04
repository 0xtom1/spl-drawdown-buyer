from dataclasses import dataclass
from typing import Optional


@dataclass
class HoldingData:
    public_key: str
    address: Optional[str] = None
    mint: Optional[str] = None

    def __str__(self):
        parts = []
        if self.public_key is not None:
            parts.append(f"\tpublic_key: {self.public_key}")
        if self.address is not None:
            parts.append(f"\taddress: {self.address}")
        if self.mint is not None:
            parts.append(f"\tmint: {self.mint}")
        return "\n".join(parts) or "HoldingData (empty)"
