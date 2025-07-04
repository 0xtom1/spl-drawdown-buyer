import http.server
import os
import socketserver
import threading
import time
from datetime import datetime, timedelta, timezone
from functools import reduce
from typing import List

from spl_drawdown.modules.swap import Swapper
from spl_drawdown.modules.token_charts import TokenCharts
from spl_drawdown.modules.token_volumes import TokenVolumes
from spl_drawdown.modules.wallet_info import Wallet
from spl_drawdown.types.token_data import TokenData
from spl_drawdown.types.wallet_data import WalletInfo
from spl_drawdown.utils.log import get_logger
from spl_drawdown.utils.settings import settings_key_values

logger = get_logger()


class SplDrawdown:
    def __init__(self):
        try:
            self.BIRDEYE_API_TOKEN = settings_key_values["BIRDEYE_API_TOKEN"]
            self.wallets = settings_key_values["wallets"]
            self.HELIUS_API_KEY = settings_key_values["HELIUS_API_KEY"]
            self.BET_AMOUNT_SOL = settings_key_values["BET_AMOUNT_SOL"]
            self.MIN_24HR_VOLUME = settings_key_values["MIN_24HR_VOLUME"]
        except KeyError:
            raise ValueError("Environment variable is required but not set")

        self.TokenCharter = TokenCharts(BIRDEYE_API_TOKEN=self.BIRDEYE_API_TOKEN)
        self.bought_tokens = dict()
        for w in self.wallets:
            self.bought_tokens[w.public_key] = dict()

        self.TokenVols = TokenVolumes(BIRDEYE_API_TOKEN=self.BIRDEYE_API_TOKEN)
        self.W = Wallet(
            HELIUS_API_KEY=self.HELIUS_API_KEY,
            BIRDEYE_API_TOKEN=self.BIRDEYE_API_TOKEN,
        )

    @property
    def wallets(self) -> List[WalletInfo]:
        return self._wallets

    @wallets.setter
    def wallets(self, value: List[WalletInfo]):
        self._wallets = value

    def run(self):
        logger.info("----------------------------Starting Run----------------------------")
        if self.TokenVols.can_run():
            tokens_in_scope = self.TokenVols.get_tokens(min_volume=self.MIN_24HR_VOLUME)
            logger.info("Len tokens = {t}".format(t=len(tokens_in_scope)))
            self.TokenCharter.token_list = tokens_in_scope
            self.TokenCharter.populate_token_list()
            self.TokenCharter.update_current_prices()
            self.TokenCharter._print_data()
            self.TokenCharter.clean_token_list()

        self.TokenCharter.update_current_prices()
        self.TokenCharter._print_data_short()

        tokens_to_buy = [
            x for x in self.TokenCharter.token_list if x.current_price_usd and x.current_price_usd > x.ath_price_usd
        ]

        self.buy_tokens(tokens_to_buy=tokens_to_buy)
        logger.info("----------------------------Run End----------------------------")

    def buy_tokens(self, tokens_to_buy: List[TokenData]):
        """Buy tokens in tokens_to_buy

        Args:
            tokens_to_buy (List[TokenData]): _description_
        """
        if not tokens_to_buy or len(tokens_to_buy) == 0:
            return
        logger.info("Tokens to Buy")

        self._prune_bought_tokens()

        Swap = Swapper(HELIUS_API_KEY=self.HELIUS_API_KEY)

        for wallet in self.wallets:
            holding_tokens = self.W.get_token_accounts(pub_key=wallet.public_key)
            holding_tokens = [x.mint for x in holding_tokens]
            logger.info("Holding Tokens: {l}".format(l=holding_tokens))

            for token in tokens_to_buy:
                balance = Swap.get_balance_with_retry(pubkey=wallet.key_pair.pubkey()) / 1e9
                logger.info(f"Wallet balance: {balance} SOL")
                if token.mint_address in holding_tokens or token.mint_address in self.bought_tokens[wallet.public_key]:
                    logger.info("Skipping {t}, purchased already".format(t=token.symbol))
                    continue

                if balance <= 2.0:
                    logger.error("Insufficient balance")
                    buy_amount = 0.001
                elif self.BET_AMOUNT_SOL + 2.0 > balance:
                    logger.error("Insufficient balance")
                    buy_amount = round(balance - 2.0, 2)
                elif balance / 2.0 > self.BET_AMOUNT_SOL:
                    logger.error("Balance more than double")
                    buy_amount = round(balance / 2.0, 2)
                else:
                    buy_amount = self.BET_AMOUNT_SOL
                logger.info("Buying token {s}: {t}. Amount: {a}".format(s=token.symbol, t=token.name, a=buy_amount))
                try:
                    is_successful = Swap.place_buy_order(
                        OUTPUT_MINT=token.mint_address, AMOUNT_IN_SOL=buy_amount, KEY_PAIR=wallet.key_pair
                    )
                    if is_successful:
                        self.bought_tokens[wallet.public_key][token.mint_address] = datetime.now(timezone.utc)
                except Exception as e:
                    logger.error("Error buying {e}".format(e=e))
                    continue

        time.sleep(30)
        self.remove_common_holdings()

    def remove_common_holdings(self):
        all_holdings = list()
        for wallet in self.wallets:
            holding_tokens = self.W.get_token_accounts(pub_key=wallet.public_key)
            holding_tokens = [x.mint for x in holding_tokens]
            all_holdings.append(holding_tokens)
        common_items = list(reduce(lambda x, y: set(x).intersection(y), all_holdings))
        logger.info("Common Holdings: {f}".format(f=common_items))
        self.TokenCharter.remove_from_token_list(mints_to_remove=common_items)

    def _prune_bought_tokens(self, minutes_til_stale: int = 90):
        """Remove tokens purchased more than 6 hours ago"""
        current_utc = datetime.now(timezone.utc)
        threshold = current_utc - timedelta(minutes=minutes_til_stale)
        for pub_key in self.bought_tokens:
            self.bought_tokens[pub_key] = {k: v for k, v in self.bought_tokens[pub_key].items() if v >= threshold}


def run_server():
    port = int(os.getenv("PORT", 8080))
    handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", port), handler) as httpd:
        logger.info(f"Serving HTTP on port {port}")
        httpd.serve_forever()


if __name__ == "__main__":
    # Start HTTP server in a separate thread
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

    S = SplDrawdown()
    while True:
        try:
            S.run()
            time.sleep(60)
        except KeyboardInterrupt:
            logger.info("\nStopped by user")
            break
