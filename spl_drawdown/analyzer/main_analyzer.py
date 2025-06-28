import csv
from datetime import datetime, timedelta
from typing import List

from spl_drawdown.analyzer.modules.algo_requirements1_analyzer import AlgoRequirements1
from spl_drawdown.analyzer.modules.token_charts_analyzer import SolanaTracker
from spl_drawdown.analyzer.modules.wallet_info_analyzer import Wallet
from spl_drawdown.analyzer.types.cd import CandleData
from spl_drawdown.analyzer.types.hd import HoldingData
from spl_drawdown.analyzer.types.td import TokenData
from spl_drawdown.analyzer.utils.log_analyzer import get_logger
from spl_drawdown.utils.settings import settings_key_values

logger = get_logger()


class Spldrawdown:
    def __init__(self):
        try:
            self.BIRDEYE_API_TOKEN = settings_key_values["BIRDEYE_API_TOKEN"]
            self.SOLANA_PRIVATE_KEY = settings_key_values["SOLANA_PRIVATE_KEY"]
            self.HELIUS_API_KEY = settings_key_values["HELIUS_API_KEY"]
            self.BET_AMOUNT_SOL = settings_key_values["BET_AMOUNT_SOL"]
            self.MIN_VOLUME = settings_key_values["MIN_VOLUME"]
            self.VOLUME_FOR_FULL_BET = settings_key_values["VOLUME_FOR_FULL_BET"]
        except KeyError:
            raise ValueError("Environment variable is required but not set")

        self.SolTrack = SolanaTracker(BIRDEYE_API_TOKEN=self.BIRDEYE_API_TOKEN)
        self.Wallet = Wallet(
            WALLET_PRIVATE_KEY=self.SOLANA_PRIVATE_KEY,
            HELIUS_API_KEY=self.HELIUS_API_KEY,
            BIRDEYE_API_TOKEN=self.BIRDEYE_API_TOKEN,
        )

    def run(self):
        logger.info("----------------------------Starting Run----------------------------")
        tokens_in_scope = self._get_tokens_in_scope()
        logger.info("len of tokens in scope = {f}".format(f=len(tokens_in_scope)))
        self.SolTrack.set_token_list(token_list=tokens_in_scope)
        logger.info("Running run()")
        self.SolTrack.run()

        Algo = AlgoRequirements1(BIRDEYE_API_TOKEN=self.BIRDEYE_API_TOKEN)
        tokens_meet_reqs = list()
        for token in self.SolTrack.token_list:
            if Algo.is_meets_reqs(token=token):
                tokens_meet_reqs.append(token)
        logger.info("--")
        logger.info("Total tokens = {s}".format(s=len(self.SolTrack.token_list)))
        logger.info("Tokens meet req = {s}".format(s=len(tokens_meet_reqs)))

        filtered_for_time = list()
        for token in tokens_meet_reqs:
            filtered_for_time.append(token)
            continue
            threshold = token.buy_time - timedelta(hours=6)
            previous_buys = [
                x
                for x in tokens_meet_reqs
                if x.mint_address == token.mint_address and x.buy_time < token.buy_time and x.buy_time >= threshold
            ]
            if len(previous_buys) == 0:
                filtered_for_time.append(token)
        logger.info("After time filter len = {x}".format(x=len(filtered_for_time)))

        final_tokens = self.SolTrack.populate_next_candles(token_list=filtered_for_time)
        results = list()

        for t in final_tokens:
            logger.info("------------")
            print(t)
            exit_price = t.buy_price_per_token_usd * 0.7
            print(exit_price)
            exit_candles = [x for x in t.next_candle_data if x.low <= exit_price]
            exit_candle = None
            result = {
                "hours_to_exit": -1,
                "hours_to_high": -1,
                "high_percent": -1,
                "symbol": t.symbol,
                "volume": t.candle_data[-1].volume,
                "buy_price": t.buy_price_per_token_usd,
                "MC": int((t.buy_price_per_token_usd * 1000000000) / 1000000),
                "per_l3": 0.0,
                "per_l24": 0.0,
            }
            if len(exit_candles) > 0:
                exit_candle = exit_candles[0]
                # logger.info("Exit Candle: {h}".format(h=exit_candle))
                exit_time = exit_candles[0].time
                logger.info("Exit Candle Time: {h}".format(h=exit_time))
                time_to_exit = (exit_time - t.buy_time).total_seconds() / 3600
                logger.info("Hours to exit: {h}".format(h=time_to_exit))
                result["hours_to_exit"] = time_to_exit
            max_price_before_exit = max(
                [x.close for x in t.next_candle_data if exit_candle is None or x.time <= exit_candle.time]
            )

            high_candle = [x for x in t.next_candle_data if x.close == max_price_before_exit][0]
            # logger.info("High Candle: {h}".format(h=high_candle))
            logger.info("High Candle Time: {h}".format(h=high_candle.time))
            time_to_high = (high_candle.time - t.buy_time).total_seconds() / 3600
            logger.info("Hours to high: {h}".format(h=time_to_high))
            high_percent = (high_candle.close - t.buy_price_per_token_usd) / t.buy_price_per_token_usd
            logger.info("High Candle Price: {h}".format(h=high_candle.close))
            logger.info("High Percent: {p}".format(p=round(high_percent * 100, 2)))
            result["hours_to_high"] = time_to_high
            result["high_percent"] = high_percent
            result["buy_time"] = t.buy_time

            max_candle_before_buy = self._get_latest_candle(candle_data=t.candle_data)
            result["per_l3"] = max_candle_before_buy.per_l3
            result["per_l24"] = max_candle_before_buy.per_l24
            results.append(result)

        csv_file = "results_new.csv"
        with open(csv_file, "w", newline="") as f:
            # Get fieldnames from the first dictionary
            fieldnames = results[0].keys()

            # Create DictWriter
            writer = csv.DictWriter(f, fieldnames=fieldnames)

            # Write header
            writer.writeheader()

            # Write rows
            writer.writerows(results)

        print(f"Data written to {csv_file}")

        logger.info("----------------------------Run End----------------------------")

    @staticmethod
    def _get_latest_candle(candle_data: List[CandleData]) -> CandleData:
        max_time = max([x.time for x in candle_data])
        for candle in candle_data:
            if candle.time == max_time:
                return candle
        return None

    def _get_tokens_in_scope(self) -> List[TokenData]:
        """_summary_

        Returns:
            List[TokenData]: _description_
        return [
            TokenData(
                name="just buy $1 worth of this coin",
                symbol="$1",
                buy_time=datetime.strptime("2025-05-23 10:10:10", "%Y-%m-%d %H:%M:%S"),
                mint_address="GHichsGq8aPnqJyz6Jp1ASTK4PNLpB5KrD6XrfDjpump",
                buy_price_per_token_usd=0.011430083911244,
            )
        ]

        """
        tokens_in_scope = list()
        tokens_in_scope.append(
            TokenData(
                name="Fartcoin",
                symbol="FARTCOIN",
                buy_time=datetime.strptime("2024-11-14 07:10:10", "%Y-%m-%d %H:%M:%S"),
                # buy_time=datetime.strptime("2024-11-12 15:10:10", "%Y-%m-%d %H:%M:%S"),
                mint_address="9BB6NFEcjBCtnNLFko2FqVQBq8HHM13kCyYcdQbgpump",
                buy_price_per_token_usd=0.249444,
            )
        )
        holding_data = self._get_holding_data_buys()
        for token in holding_data:
            tokens_in_scope.append(
                TokenData(
                    name=token.name,
                    symbol=token.symbol,
                    buy_time=token.buy_time,
                    mint_address=token.mint,
                    buy_price_per_token_usd=token.buy_price_per_token_usd,
                )
            )
        return tokens_in_scope

    def _get_scanned_tokens(self) -> List[TokenData]:
        """_summary_

        Returns:
            List[TokenData]: _description_
        return [
            TokenData(
                name="just buy $1 worth of this coin",
                symbol="$1",
                buy_time=datetime.strptime("2025-05-23 10:10:10", "%Y-%m-%d %H:%M:%S"),
                mint_address="GHichsGq8aPnqJyz6Jp1ASTK4PNLpB5KrD6XrfDjpump",
                buy_price_per_token_usd=0.011430083911244,
            )
        ]

        """
        # tokens_in_scope = list()
        # tokens_in_scope.append(
        #     TokenData(
        #         name="Fartcoin",
        #         symbol="FARTCOIN",
        #         # buy_time=datetime.strptime("2024-11-14 07:10:10", "%Y-%m-%d %H:%M:%S"),
        #         buy_time=datetime.strptime("2024-11-14 07:10:10", "%Y-%m-%d %H:%M:%S"),
        #         # buy_time=datetime.strptime("2025-04-10 01:10:10", "%Y-%m-%d %H:%M:%S"),
        #         mint_address="9BB6NFEcjBCtnNLFko2FqVQBq8HHM13kCyYcdQbgpump",
        #         buy_price_per_token_usd=0.249444,
        #     )
        # )
        tokens_in_scope = list()
        tokens_in_scope.append(
            TokenData(
                name="Labubu",
                symbol="LABUBU",
                # buy_time=datetime.strptime("2024-11-14 07:10:10", "%Y-%m-%d %H:%M:%S"),
                buy_time=datetime.strptime("2025-05-12 07:10:10", "%Y-%m-%d %H:%M:%S"),
                # buy_time=datetime.strptime("2025-05-10 01:10:10", "%Y-%m-%d %H:%M:%S"),
                mint_address="JB2wezZLdzWfnaCfHxLg193RS3Rh51ThiXxEDWQDpump",
                buy_price_per_token_usd=0.249444,
            )
        )
        # tokens_in_scope = list()
        # tokens_in_scope.append(
        #     TokenData(
        #         name="USELESS",
        #         symbol="USELESS",
        #         # buy_time=datetime.strptime("2024-11-14 07:10:10", "%Y-%m-%d %H:%M:%S"),
        #         buy_time=datetime.strptime("2025-05-12 07:10:10", "%Y-%m-%d %H:%M:%S"),
        #         # buy_time=datetime.strptime("2025-05-10 01:10:10", "%Y-%m-%d %H:%M:%S"),
        #         mint_address="Dz9mQ9NzkBcCsuGPFJ3r1bS4wgqKMHBPiVuniW8Mbonk",
        #         buy_price_per_token_usd=0.249444,
        #     )
        # )
        results = list()
        for token in tokens_in_scope:
            a = self.SolTrack.scan_candles(token=token, candle_days_forward=120)
            results.extend(a)
        return results

    def _get_holding_data_buys(self) -> List[HoldingData]:
        address_list = ["gPZ8hnkJCYg1QhzUQA9b7W4hPZzYNKnyxpE6aPitTst", "Yw5urUXZ8Mj4dUFGdFxoBPdrrwhnjVWgrmJ1JfrKiNg"]
        results = list()
        for each in address_list:
            results.extend(self.Wallet.get_all_buy_swaps(wallet_address=each))
            print(len(results))
            print(each)
        return results


if __name__ == "__main__":
    S = Spldrawdown()
    S.run()
