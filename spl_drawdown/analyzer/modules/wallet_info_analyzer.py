import os
from datetime import datetime, timezone
from typing import List

from dotenv import load_dotenv
from heliuspy import HeliusAPI
from solana.rpc.api import Client
from solders.keypair import Keypair

from spl_drawdown.analyzer.modules.token_charts_analyzer import SolanaTracker
from spl_drawdown.analyzer.types.hd import HoldingData
from spl_drawdown.analyzer.utils.log_analyzer import get_logger

logger = get_logger()


class Wallet:
    def __init__(self, WALLET_PRIVATE_KEY: str, HELIUS_API_KEY: str, BIRDEYE_API_TOKEN: str):
        # Configuration
        self.RPC_ENDPOINT = f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"
        self.BIRDEYE_API_TOKEN = BIRDEYE_API_TOKEN
        self.WALLET_PRIVATE_KEY = WALLET_PRIVATE_KEY
        self.Helius = HeliusAPI(api_key=HELIUS_API_KEY)
        self.COMMITMENT = "confirmed"  # Commitment level for RPC calls
        self.holdings = list()
        self.sol_mint = "So11111111111111111111111111111111111111112"  # SOL
        self.usdc_mint = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"

        # Initialize Solana client
        try:
            self.client = Client(self.RPC_ENDPOINT, commitment=self.COMMITMENT)
        except Exception as e:
            raise Exception(f"Failed to connect to Helius RPC: {e}")

        # Validate and initialize wallet
        try:
            self.wallet = Keypair.from_base58_string(WALLET_PRIVATE_KEY)
        except ValueError as e:
            raise ValueError(f"Invalid private key: {e}")
        self.wallet_pub_key = str(self.wallet.pubkey())
        self.exclusion_list = list()

    def get_token_info(self, token: HoldingData) -> HoldingData:
        """Populates:
                symbol
                name
                decimals
                current_amount

        Args:
            mint_address (str): _description_

        Returns:
            dict: _description_
        """
        asset_info = self.Helius.get_asset(id=token.mint)
        expected_keys = sorted(["jsonrpc", "result", "id"])
        response_keys = sorted(asset_info.keys())

        if expected_keys != response_keys or "token_info" not in asset_info["result"]:
            return token

        try:
            token.symbol = asset_info["result"]["content"]["metadata"]["symbol"]
            token.name = asset_info["result"]["content"]["metadata"]["name"]
            token.decimals = asset_info["result"]["token_info"]["decimals"]
            # token.current_amount = token.current_amount_raw / ((10**token.decimals) * 1.0)
            """
            quote_currency = asset_info["result"]["token_info"]["price_info"]["currency"]
            if quote_currency in ["USDC", "USDT"]:
                token.current_price_per_token_usd = asset_info["result"]["token_info"]["price_info"]["price_per_token"]
            if quote_currency in ["SOL", "WSOL"]:
                token.current_price_per_token_sol = asset_info["result"]["token_info"]["price_info"]["price_per_token"]
            """
        except KeyError as e:
            logger.info("Error getting token info: {e}".format(e=e))

        return token

    def get_all_buy_swaps(self, wallet_address: str = None) -> List[HoldingData]:
        """Populate the buy fields of HoldingData and return the object

            Populates:
                    buy_time
                    buy_amount
                    buy_price_sol_total
                    buy_price_usd_total
        Args:
            token (HoldingData): _description_

        Returns:
            HoldingData: _description_
        """
        if wallet_address is None:
            wallet_address = self.wallet_pub_key
        tokens_list = list()
        last_signature = None
        results = ["s"]
        S = SolanaTracker(BIRDEYE_API_TOKEN=self.BIRDEYE_API_TOKEN)
        while len(results) > 0:
            if not last_signature:
                results = self.Helius.get_parsed_transactions(address=wallet_address, type="SWAP")
            else:
                results = self.Helius.get_parsed_transactions(
                    address=wallet_address, type="SWAP", before=last_signature
                )
            for swap in results:
                last_signature = swap["signature"]
                if not self.contains_mint_address_account(
                    mint_address=self.sol_mint,
                    transfers=swap["tokenTransfers"],
                    address=wallet_address,
                    is_buy=True,
                ):
                    continue

                holding = HoldingData()

                for transfer in swap["tokenTransfers"]:
                    if (
                        transfer["toUserAccount"] == wallet_address
                        and transfer["mint"] != self.sol_mint
                        and transfer["mint"] != "9BB6NFEcjBCtnNLFko2FqVQBq8HHM13kCyYcdQbgpump"
                    ):
                        holding.mint = transfer["mint"]
                        holding.address = transfer["toTokenAccount"]
                        holding.buy_amount = transfer["tokenAmount"]
                        holding.buy_time = datetime.fromtimestamp(swap["timestamp"])

                    elif transfer["mint"] == self.sol_mint and transfer["fromUserAccount"] == wallet_address:
                        holding.buy_price_sol_total += transfer["tokenAmount"]

                if holding.buy_price_sol_total == 0 or holding.buy_amount == 0:
                    logger.error("Could not find buy amount for token: {t}".format(t=swap["description"]))
                    continue

                sol_price = S.get_token_price_at_time(
                    mint=self.sol_mint, start_time=datetime.fromtimestamp(swap["timestamp"], tz=timezone.utc)
                )
                if sol_price:
                    holding.buy_price_usd_total = holding.buy_price_sol_total * sol_price

                holding.buy_price_per_token_sol = holding.buy_price_sol_total / holding.buy_amount
                holding.buy_price_per_token_usd = holding.buy_price_usd_total / holding.buy_amount
                tokens_list.append(holding)

        for token in tokens_list:
            self.get_token_info(token=token)
        return tokens_list

    @staticmethod
    def contains_mint_address_account(
        mint_address: str, transfers: list = None, address: str = None, is_buy: bool = None, is_sell: bool = None
    ):
        for transfer in transfers:
            if transfer["mint"] == mint_address:
                if not is_buy and not is_sell:
                    return True
                if is_buy and transfer["fromUserAccount"] == address and len(transfers) >= 2:
                    return True
                if is_sell and transfer["toUserAccount"] == address and len(transfers) >= 2:
                    return True
        return False


if __name__ == "__main__":
    load_dotenv()
    SOLANA_PRIVATE_KEY = os.environ.get("SOLANA_PRIVATE_KEY")
    if not SOLANA_PRIVATE_KEY:
        raise ValueError("SOLANA_PRIVATE_KEY not found in environment variables")
    HELIUS_API_KEY = os.environ.get("HELIUS_API_KEY")
    if not HELIUS_API_KEY:
        raise ValueError("HELIUS_API_KEY not found in environment variables")
    BIRDEYE_API_TOKEN = os.environ.get("BIRDEYE_API_TOKEN")
    W = Wallet(
        WALLET_PRIVATE_KEY=SOLANA_PRIVATE_KEY,
        HELIUS_API_KEY=HELIUS_API_KEY,
        BIRDEYE_API_TOKEN=BIRDEYE_API_TOKEN,
    )

    a = W.get_all_buy_swaps()
    for each in a:
        print(each)
    print(len(a))
