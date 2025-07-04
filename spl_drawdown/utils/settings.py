import os
from typing import List

import dotenv
from solders.keypair import Keypair

from spl_drawdown.types.wallet_data import WalletInfo

dotenv.load_dotenv()


def get_wallet_list() -> List[WalletInfo]:
    private_key_1 = os.environ.get("SOLANA_PRIVATE_KEY1")
    private_key_2 = os.environ.get("SOLANA_PRIVATE_KEY2")
    private_key_3 = os.environ.get("SOLANA_PRIVATE_KEY3")
    private_key_4 = os.environ.get("SOLANA_PRIVATE_KEY4")

    private_key_list = [private_key_1, private_key_2, private_key_3, private_key_4]

    wallets = list()
    for pv in private_key_list:
        if pv is None:
            continue
        key_pair = Keypair.from_base58_string(pv)
        public_key = str(key_pair.pubkey())
        wallets.append(WalletInfo(public_key=public_key, key_pair=key_pair))
    return wallets


settings_key_values = dict()
settings_key_values["wallets"] = get_wallet_list()
try:
    settings_key_values["HELIUS_API_KEY"] = os.environ.get("HELIUS_API_KEY")
    settings_key_values["BET_AMOUNT_SOL"] = float(os.environ.get("BET_AMOUNT_SOL"))
    settings_key_values["MIN_24HR_VOLUME"] = float(os.environ.get("MIN_24HR_VOLUME"))
    settings_key_values["BIRDEYE_API_TOKEN"] = os.environ.get("BIRDEYE_API_TOKEN")
except KeyError:
    raise ValueError("Environment variable is required but not set")
