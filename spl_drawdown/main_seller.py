import http.server
import os
import socketserver
import threading
import time
from datetime import datetime, timezone
from typing import List

from spl_drawdown.modules.swap import Swapper
from spl_drawdown.modules.wallet_info import Wallet
from spl_drawdown.types.exit_strategy import ExitStrategy
from spl_drawdown.types.holdings_data import HoldingData
from spl_drawdown.utils.log import get_logger
from spl_drawdown.utils.settings import settings_key_values

logger = get_logger()  # Get the logger instance


class SplSeller:
    def __init__(self):
        try:
            self.BIRDEYE_API_TOKEN = settings_key_values["BIRDEYE_API_TOKEN"]
            self.SOLANA_PRIVATE_KEY = settings_key_values["SOLANA_PRIVATE_KEY"]
            self.HELIUS_API_KEY = settings_key_values["HELIUS_API_KEY"]
            self.EXIT_STRATEGY = [
                {
                    "amount_remaining_percent_gt": 0.51,
                    "amount_remaining_percent_lte": 1.0,
                    "stop_price_per_token_percent_change": -0.5,
                    "profit_price_per_token_percent_change": 0.5,
                    "profit_sell_amount_percent": 0.5,
                },
                {
                    "amount_remaining_percent_gt": 0.35,
                    "amount_remaining_percent_lte": 0.51,
                    "stop_price_per_token_percent_change": 0.0,
                    "profit_price_per_token_percent_change": 1.0,
                    "profit_sell_amount_percent": 0.25,
                },
                {
                    "amount_remaining_percent_gt": 0.0,
                    "amount_remaining_percent_lte": 0.35,
                    "stop_price_per_token_percent_change": 0.5,
                    "profit_price_per_token_percent_change": 2.0,
                    "profit_sell_amount_percent": 0.25,
                },
            ]
        except KeyError:
            raise ValueError("Environment variable is required but not set")

        self.WalletInterface = Wallet(
            WALLET_PRIVATE_KEY=self.SOLANA_PRIVATE_KEY,
            HELIUS_API_KEY=self.HELIUS_API_KEY,
            BIRDEYE_API_TOKEN=self.BIRDEYE_API_TOKEN,
        )

        self.SwapInterface = Swapper(WALLET_PRIVATE_KEY=self.SOLANA_PRIVATE_KEY, HELIUS_API_KEY=self.HELIUS_API_KEY)
        self.prices_list = list()

    def run(self):
        current_time = datetime.now(timezone.utc)
        if current_time.second <= 15:
            is_print = True
        else:
            is_print = False

        print_list = list()
        print_list.append("----------------------------Starting Run----------------------------")
        self.WalletInterface.update_holdings(is_print=is_print)

        holdings = self.get_holdings()

        for token in holdings:
            if not token.current_price_per_token_usd or not token.current_price_per_token_sol:
                logger.info("Quote not found for token: {t}".format(t=token))
                continue
            exit_strategy = self._get_exit_strategy(percent_remaining=token.sell_percent_remaining)
            if not exit_strategy:
                logger.info("Exit Strategy is None")

            token.stop_price_usd = max(
                (1 + exit_strategy.stop_price_per_token_percent_change) * token.buy_price_per_token_usd,
                token.initial_stop_price_usd,
            )

            print_list.append(token)
            print_list.append(exit_strategy)

            original_buy_amount = int(token.current_amount_raw / token.sell_percent_remaining)
            print_list.append("Original Buy Amount: {t}".format(t=original_buy_amount))

            profit_sell_amount = min(
                int(original_buy_amount * exit_strategy.profit_sell_amount_percent) - 1, token.current_amount_raw
            )
            print_list.append("Profit Sell Amount: {t}".format(t=profit_sell_amount))

            profit_price_per_token = (
                1 + exit_strategy.profit_price_per_token_percent_change
            ) * token.buy_price_per_token_usd

            print_list.append("Profit Price per token: {t}".format(t=profit_price_per_token))

            if token.current_price_per_token_usd <= token.stop_price_usd:
                for each in print_list:
                    logger.info(each)
                logger.info("***Below stop price, sell all***")
                self.sell_tokens(token_to_sell=token, amount=token.current_amount_raw)
            elif token.buy_duration_hours >= 240 and abs(token.current_amount - token.buy_amount) < 0.01:
                for each in print_list:
                    logger.info(each)
                logger.info("***Duration Elapsed, Sell all***")
                self.sell_tokens(token_to_sell=token, amount=token.current_amount_raw)
            elif token.current_price_per_token_usd >= profit_price_per_token:
                for each in print_list:
                    logger.info(each)
                logger.info("***Profit Price reached***")
                self.sell_tokens(token_to_sell=token, amount=profit_sell_amount)
            print_list.append("-------")

            # Add token prices to print list
            if not is_print:
                self.prices_list.append(
                    "{time} {symbol} USD: {usd} SOL: {sol}".format(
                        time=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                        symbol=token.symbol,
                        usd=round(token.current_price_per_token_usd, 6),
                        sol=round(token.current_price_per_token_sol, 6),
                    )
                )

        if is_print:
            for each in self.prices_list:
                logger.info(each)
            self.prices_list = list()
            for each in print_list:
                logger.info(each)
            balance = self.SwapInterface.get_balance_with_retry() / 1e9
            total_portfolio_sol = sum([x.current_value_sol for x in holdings])
            logger.info(
                "Sol Balance: {s} | Port Balance: {p} | Total Sol: {t}".format(
                    s=balance, p=total_portfolio_sol, t=balance + total_portfolio_sol
                )
            )
            logger.info("----------------------------Run End----------------------------")

    def get_holdings(self) -> List[HoldingData]:
        return self.WalletInterface.holdings

    def sell_tokens(self, token_to_sell: HoldingData, amount: int):
        """Sell token

        Args:
            tokens_to_buy (List[TokenData]): _description_
        """
        logger.info("Selling token {s}: {t}".format(s=token_to_sell.symbol, t=token_to_sell.name))
        try:
            self.SwapInterface.place_sell_order(INPUT_MINT=token_to_sell.mint, AMOUNT=amount)
        except Exception as e:
            logger.error("Error Selling {e}".format(e=e))

    def _get_exit_strategy(self, percent_remaining: float) -> ExitStrategy:
        for strat in self.EXIT_STRATEGY:
            if strat["amount_remaining_percent_lte"] >= percent_remaining > strat["amount_remaining_percent_gt"]:
                return ExitStrategy(
                    amount_remaining_percent_gt=strat["amount_remaining_percent_gt"],
                    amount_remaining_percent_lte=strat["amount_remaining_percent_lte"],
                    stop_price_per_token_percent_change=strat["stop_price_per_token_percent_change"],
                    profit_price_per_token_percent_change=strat["profit_price_per_token_percent_change"],
                    profit_sell_amount_percent=strat["profit_sell_amount_percent"],
                )
        return None

    def get_sleep_time(self) -> int:
        """_summary_

        Returns:
            int: _description_
        """
        number_of_holdings = len(self.get_holdings())
        utc_minute = datetime.now(timezone.utc).minute

        if number_of_holdings == 0 and utc_minute <= 59 and utc_minute >= 25:
            return 60 * 5
        else:
            return 15


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

    Seller = SplSeller()
    while True:
        try:
            Seller.run()
            seconds_to_sleep = Seller.get_sleep_time()
            if seconds_to_sleep > 15:
                logger.info("Sleeping {x} seconds".format(x=seconds_to_sleep))
            time.sleep(seconds_to_sleep)
        except KeyboardInterrupt:
            logger.info("\nStopped by user")
            break
