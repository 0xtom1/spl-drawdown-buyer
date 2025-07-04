from time import sleep
from typing import List

from heliuspy import HeliusAPI
from solana.rpc.api import Client

from spl_drawdown.types.holdings_data import HoldingData
from spl_drawdown.utils.log import get_logger

logger = get_logger()


class Wallet:
    def __init__(self, HELIUS_API_KEY: str, BIRDEYE_API_TOKEN: str):
        # Configuration
        self.RPC_ENDPOINT = f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"
        self.BIRDEYE_API_TOKEN = BIRDEYE_API_TOKEN
        self.Helius = HeliusAPI(api_key=HELIUS_API_KEY)
        self.COMMITMENT = "confirmed"  # Commitment level for RPC calls
        # Initialize Solana client
        try:
            self.client = Client(self.RPC_ENDPOINT, commitment=self.COMMITMENT)
        except Exception as e:
            raise Exception(f"Failed to connect to Helius RPC: {e}")

    def get_token_accounts(self, pub_key: str) -> List[HoldingData]:
        """Get token accounts for wallet

        Raises:
            Exception: _description_

        Returns:
            list: _description_
        """
        ignore_mints = [
            "BfSbstVpvUPaqEm57ZiPBN7fmkQ41NxdGCmARBNFpump",
            "3YQBXUDab4uEiMtRD4Y4Bhu1YJG9YD2ywYPMeyvAsJ23",
            "28ZDne7nY6eFtuENqeoYwuu4sgjpVtegt7SsEC4dDLE7",
            "7hBvn2dnqBoHYCh2vp7js3zaPSf6px2s4HMiPzw1pump",
            "3MnqzEH6JrWeHL1MmZPSr81i9Tto7mbuctH5Hvv1pump",
            "8Pg897t8NFe9sxGWsnAfnxP6NPu1ACUsgedSBacHpump",
        ]
        try:
            token_accounts = self.Helius.get_token_accounts(
                owner=pub_key,
                displayOptions={"showZeroBalance": False},
                page=1,
                limit=100,  # Adjust limit as needed
            )
        except Exception as e:
            logger.info("Error getting token accounts: {e}".format(e=e))
            sleep(2)
            return list()

        assert token_accounts

        expected_keys = sorted(["jsonrpc", "result", "id"])
        response_keys = sorted(token_accounts.keys())

        if expected_keys != response_keys:
            return list()

        response_result_keys = sorted(token_accounts["result"].keys())

        if (
            "token_accounts" not in response_result_keys
            or "total" not in response_result_keys
            or "limit" not in response_result_keys
        ):
            return list()

        token_list = list()
        for each in token_accounts["result"]["token_accounts"]:
            if each["mint"] in ignore_mints:
                continue

            if each["amount"] > 1000 and each["mint"]:
                token_list.append(HoldingData(public_key=pub_key, mint=each["mint"], address=each["address"]))
        return token_list


if __name__ == "__main__":
    from spl_drawdown.utils.settings import settings_key_values

    W = Wallet(
        HELIUS_API_KEY=settings_key_values["HELIUS_API_KEY"],
        BIRDEYE_API_TOKEN=settings_key_values["BIRDEYE_API_TOKEN"],
    )

    a = W.get_token_accounts()
    print(a)
