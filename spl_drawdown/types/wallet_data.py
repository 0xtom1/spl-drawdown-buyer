from dataclasses import dataclass
from solders.keypair import Keypair


@dataclass
class WalletInfo:
    public_key: str
    key_pair: Keypair

    def __str__(self):
        parts = []
        parts.append(f"public_key: {self.public_key[-10:]}")

        return "\n".join(parts) or "WalletInfo (empty)"
