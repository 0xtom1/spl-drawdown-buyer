import json
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from typing import List

import numpy as np
import pandas as pd
import requests

from spl_drawdown.analyzer.types.cd import CandleData
from spl_drawdown.analyzer.types.td import TokenData
from spl_drawdown.analyzer.utils.log_analyzer import get_logger

logger = get_logger()


class SolanaTracker:
    def __init__(self, BIRDEYE_API_TOKEN: str):
        self.BIRDEYE_API_TOKEN = BIRDEYE_API_TOKEN
        self.headers = {"accept": "application/json", "x-chain": "solana", "X-API-KEY": self.BIRDEYE_API_TOKEN}

    def set_token_list(self, token_list: List[TokenData] = None):
        self.token_list = token_list

    def run(self):
        """Populates self.token_list: List[TokenData]"""
        self.populate_candle_data()
        self.populate_candle_metrics()
        # self._print_data()
        # logger.info("Number of tokens pre-filter: {c}".format(c=len(self.token_list)))
        # self.filter_tokens_by_candles()
        # logger.info("Number of tokens post-filter: {c}".format(c=len(self.token_list)))

    def populate_candle_data(self, candle_days: int = 14) -> List[TokenData]:
        """_summary_

            NOTE: Timestamp for candle is the beginning of the time period
        Args:
            token (TokenData): _description_
            filter_days (int, optional): _description_. Defaults to 14.
        """

        for i, token in enumerate(self.token_list):
            if len(token.candle_data) > 0:
                continue
            current_time = token.buy_time.replace(minute=0, second=0, microsecond=0)
            utc_from = current_time - timedelta(hours=candle_days * 24)

            token.candle_data = self.get_candle_data(
                mint_address=token.mint_address, start_date=utc_from, end_date=current_time, interval_minutes=60
            )

    def get_candle_data(
        self, mint_address: str, start_date: datetime, end_date: datetime, interval_minutes: int
    ) -> List[CandleData]:
        """_summary_

        Args:
            start_date (datetime): _description_
            end_date (datetime): _description_
            interval_minutes (int): _description_

        Returns:
            List[CandleData]: _description_
        """
        end_date_unix = int(end_date.timestamp())

        temp_end_time = start_date
        results = []
        while temp_end_time < end_date:
            temp_end_time = min(start_date + timedelta(minutes=interval_minutes * 99), end_date)

            time_from = int(start_date.timestamp())
            time_to = int(temp_end_time.timestamp())

            logger.info(
                "Calling chart for {s} From: {f} To: {t}".format(s=mint_address, f=start_date, t=temp_end_time)
            )

            params = {
                "address": mint_address,
                "type": "1H",
                "currency": "usd",
                "time_from": time_from,
                "time_to": time_to,
            }
            url = "https://public-api.birdeye.so/defi/v3/ohlcv"
            response = requests.get(url, headers=self.headers, params=params)

            # Check if the request was successful
            if response.status_code != 200:
                logger.info("Response failed for {t}: {e}".format(t=mint_address, e=response.text))
                return results

            # Parse the JSON response
            response_json = json.loads(response.text)

            if "data" not in response_json or "items" not in response_json["data"]:
                logger.info("No OCLHV data for {t}: {e}".format(t=mint_address, e=response_json))
                return results

            for each in response_json["data"]["items"]:
                dt = datetime.fromtimestamp(each["unix_time"])
                date_string = dt.strftime("%Y-%m-%d %H:%M:%S")
                if each["unix_time"] == end_date_unix:
                    continue
                if date_string not in [x.time_str for x in results]:
                    results.append(
                        CandleData(
                            time=dt,
                            time_str=date_string,
                            time_unix=each["unix_time"],
                            open=each["o"],
                            high=each["h"],
                            low=each["l"],
                            close=each["c"],
                            volume=round(each["v_usd"], 0),
                        )
                    )
            start_date = temp_end_time + timedelta(minutes=interval_minutes)

        return results

    def populate_candle_metrics(self):
        """_summary_

        Args:
            token_list (List[TokenData]): _description_

        Returns:
            List[TokenData]: _description_
        """
        for token in self.token_list:
            for candle in token.candle_data:
                if candle.vol_l3 is not None:
                    continue
                candle.vol_l3 = self._populate_metric_volume(candle=candle, candle_list=token.candle_data)
                candle.vol_l3_24avg = self._populate_metric_volume_avg(
                    candle=candle, candle_list=token.candle_data, n=24
                )
                candle.vol_l3_168avg = self._populate_metric_volume_avg(
                    candle=candle, candle_list=token.candle_data, n=168
                )
                candle.ma24 = self._populate_metric_ma(candle=candle, candle_list=token.candle_data, n=24)
                candle.ema24 = self._populate_metric_ema(candle=candle, candle_list=token.candle_data, n=24)
                candle.ma168 = self._populate_metric_ma(candle=candle, candle_list=token.candle_data, n=168)
                candle.per_l3 = self._populate_metric_per(candle=candle, candle_list=token.candle_data, n=3)
                candle.per_l24 = self._populate_metric_per(candle=candle, candle_list=token.candle_data, n=24)

    def filter_tokens_by_candles(self, candle_days: int = 14):
        threshold = (candle_days * 24) * 0.95

        new_token_list = list()
        for token in self.token_list:
            if len(token.candle_data) >= threshold:
                new_token_list.append(token)
        self.token_list = new_token_list

        # Must have candle data from one of earliest 3 candles
        current_time = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
        utc_from = current_time - timedelta(hours=candle_days * 24)
        utc_from_minus1 = current_time - timedelta(hours=(candle_days * 24) - 1)
        utc_from_minus2 = current_time - timedelta(hours=(candle_days * 24) - 2)

        new_token_list = list()
        for token in self.token_list:
            value0 = self._get_candle_column(
                candle_list=token.candle_data, time_unix=utc_from.timestamp(), column="open"
            )
            value1 = self._get_candle_column(
                candle_list=token.candle_data, time_unix=utc_from_minus1.timestamp(), column="open"
            )
            value2 = self._get_candle_column(
                candle_list=token.candle_data, time_unix=utc_from_minus2.timestamp(), column="open"
            )

            if value0 or value1 or value2:
                new_token_list.append(token)
            else:
                logger.info("Removing {a}: Oldest candles not present".format(a=token.symbol))

        self.token_list = new_token_list

        # most recent candle must be within the last 2 hours
        new_token_list = list()
        for token in self.token_list:
            max_candle = max([x.time for x in token.candle_data])
            if current_time.timestamp() - max_candle.timestamp() <= 7140:
                new_token_list.append(token)
            else:
                logger.info("Removing {a}: Most recent candle too stale".format(a=token.symbol))
        self.token_list = new_token_list

    def _populate_metric_per(self, candle: CandleData, candle_list: List[CandleData], n: int = 3):
        first_time = candle.time - timedelta(hours=n - 1)
        open_price = self._get_candle_column(candle_list=candle_list, time=first_time, column="open")
        close_price = self._get_candle_column(candle_list=candle_list, time=candle.time, column="close")
        if open_price is None or close_price is None:
            return None
        else:
            return (close_price - open_price) / open_price

    def get_token_price_at_time(self, mint: str, start_time: datetime) -> float:
        """_summary_

        Args:
            mint (str): _description_
            time (datetime): _description_

        Returns:
            float: price
        """
        start_time = start_time.replace(second=0, microsecond=0)

        # From datetime object
        time_from = int(start_time.timestamp())
        time_to = int(start_time.timestamp())

        params = {
            "address": mint,
            "type": "1m",
            "currency": "usd",
            "time_from": time_from,
            "time_to": time_to,
        }
        url = "https://public-api.birdeye.so/defi/v3/ohlcv"
        response = requests.get(url, headers=self.headers, params=params)

        # Check if the request was successful
        if response.status_code != 200:
            logger.info("Response failed for {t}: {e}".format(t=mint, e=response.text))
            return None

        # Parse the JSON response
        response_json = json.loads(response.text)

        if "data" not in response_json or "items" not in response_json["data"]:
            logger.info("No OCLHV data for {t}: {e}".format(t=mint, e=response_json))
            return None

        for each in response_json["data"]["items"]:
            return (each["o"] + each["c"]) / 2.0

    def populate_next_candles(self, token_list: List[TokenData]) -> List[TokenData]:
        """_summary_

        Args:
            token_list (List[TokenData]): _description_

        Returns:
            List[TokenData]: _description_
        """
        for token in token_list:
            current_time = token.buy_time.replace(minute=0, second=0, microsecond=0)
            utc_from = current_time + timedelta(hours=0)
            utc_to = utc_from + timedelta(hours=480)

            token.next_candle_data = self.get_candle_data(
                mint_address=token.mint_address, start_date=utc_from, end_date=utc_to, interval_minutes=60
            )
        return token_list

    @staticmethod
    def _populate_metric_volume(candle: CandleData, candle_list: List[CandleData], n: int = 3):
        first_time = candle.time - timedelta(hours=n)
        sum_vol = [x.volume for x in candle_list if x.time > first_time and x.time <= candle.time]
        if len(sum_vol) == n:
            return sum(sum_vol)
        else:
            return None

    def scan_candles(self, token: TokenData, candle_days_forward: int = 90) -> List[TokenData]:
        """_summary_

        Args:
            candle_days_forward (int, optional): _description_. Defaults to 20.

        Returns:
            List[TokenData]: _description_
        """

        current_time = token.buy_time.replace(minute=0, second=0, microsecond=0) - timedelta(hours=24 * 16)
        utc_to = datetime.now().replace(minute=0, second=0, microsecond=0)
        # utc_to = token.buy_time.replace(minute=0, second=0, microsecond=0) + timedelta(hours=24 * 16)
        candle_data = self.get_candle_data(
            mint_address=token.mint_address, start_date=current_time, end_date=utc_to, interval_minutes=60
        )

        results = list()
        for candle in candle_data:
            candle.vol_l3 = self._populate_metric_volume(candle=candle, candle_list=candle_data)
            candle.vol_l3_24avg = self._populate_metric_volume_avg(candle=candle, candle_list=candle_data, n=24)
            candle.vol_l3_168avg = self._populate_metric_volume_avg(candle=candle, candle_list=candle_data, n=168)
            candle.ma24 = self._populate_metric_ma(candle=candle, candle_list=candle_data, n=24)
            candle.ema24 = self._populate_metric_ema(candle=candle, candle_list=candle_data, n=24)
            candle.ma168 = self._populate_metric_ma(candle=candle, candle_list=candle_data, n=168)
            candle.per_l3 = self._populate_metric_per(candle=candle, candle_list=candle_data, n=3)
            candle.per_l24 = self._populate_metric_per(candle=candle, candle_list=candle_data, n=24)

        for each in candle_data:
            if each.volume < 2000000:
                continue
            buy_time = each.time + timedelta(hours=1) + timedelta(minutes=1)
            min_candle_time = each.time - timedelta(hours=14 * 24)
            if buy_time not in [x.buy_time for x in results]:
                results.append(
                    TokenData(
                        name=token.name,
                        symbol=token.symbol,
                        buy_time=buy_time,
                        mint_address=token.mint_address,
                        buy_price_per_token_usd=each.close,
                        candle_data=[x for x in candle_data if x.time > min_candle_time and x.time <= each.time],
                    )
                )
        return results

    @staticmethod
    def _populate_metric_volume_avg(candle: CandleData, candle_list: List[CandleData], n: int = 24):
        first_time = candle.time - timedelta(hours=n)
        sum_vol = [
            x.vol_l3 for x in candle_list if x.time >= first_time and x.time < candle.time and x.vol_l3 is not None
        ]
        if len(sum_vol) / n >= 0.8:
            return round(sum(sum_vol) / (len(sum_vol) * 1.0), 0)
        else:
            return None

    @staticmethod
    def _populate_metric_ma(candle: CandleData, candle_list: List[CandleData], n: int = 24):
        first_time = candle.time - timedelta(hours=n)
        prices = [
            x.close for x in candle_list if x.time > first_time and x.time <= candle.time and x.close is not None
        ]
        if len(prices) / n >= 0.8:
            return sum(prices) / (len(prices) * 1.0)
        else:
            return None

    def _populate_metric_ema(self, candle: CandleData, candle_list: List[CandleData], n: int = 24):
        hours_to_subtract = (n * 2) - 1

        # Convert hours to seconds (1 hour = 3600 seconds)
        seconds_to_subtract = hours_to_subtract * 3600
        last_time = candle.time_unix - seconds_to_subtract

        prices = [x.close for x in candle_list if candle.time_unix >= x.time_unix >= last_time]
        if len(prices) / (n * 2) >= 0.7:
            window = int(len(prices) / 2)
            return self._exp_moving_avg(values=prices, window=window)
        else:
            return None

    @staticmethod
    def _get_candle_column(
        candle_list: List[CandleData], time: datetime = None, time_unix: int = None, column: str = ""
    ):
        if time:
            value_list = [x for x in candle_list if x.time == time]
        else:
            value_list = [x for x in candle_list if x.time_unix == time_unix]
        if len(value_list) != 1:
            return None

        try:
            return getattr(value_list[0], column)
        except AttributeError:
            return None

    @staticmethod
    def _exp_moving_avg(values, window):
        first_sma = np.mean(values[:window])
        emas = list()
        emas.append(first_sma)
        multiplier = 2 / (window + 1)
        for each in values[window::]:
            ema = (each - emas[-1]) * multiplier + emas[-1]
            emas.append(ema)
        return emas[-1]

    def _print_data(self):
        for each in self.token_list:
            print_token_dict = asdict(each)
            print_token_dict.pop("candle_data", None)
            print_token_dict["candle_len"] = len(each.candle_data)
            df = pd.DataFrame([print_token_dict])

            logger.info(f"\n{df.to_string()}")
            df = pd.DataFrame(each.candle_data)
            df = df.drop(columns=["time_str", "time_unix"], errors="ignore")
            logger.info(f"\n{df.to_string()}")
            df = pd.DataFrame(each.candle_data[:3])
            df = df.drop(columns=["time_str", "time_unix"], errors="ignore")
            # logger.info(f"\n{df.to_string()}")
            logger.info("-------------------------------")


if __name__ == "__main__":
    import os

    from dotenv import load_dotenv

    load_dotenv()
    BIRDEYE_API_TOKEN = os.environ.get("BIRDEYE_API_TOKEN")
    logger.info(BIRDEYE_API_TOKEN)
    S = SolanaTracker(BIRDEYE_API_TOKEN=BIRDEYE_API_TOKEN)
