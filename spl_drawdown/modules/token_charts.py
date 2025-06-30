import json
from datetime import datetime, timedelta, timezone
from statistics import mean, stdev
from time import sleep
from typing import List

import requests
from requests.exceptions import HTTPError, RequestException, SSLError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_fixed

from spl_drawdown.types.candle_data import CandleData
from spl_drawdown.types.token_data import TokenData
from spl_drawdown.utils.log import get_logger

logger = get_logger()


class TokenCharts:
    def __init__(self, BIRDEYE_API_TOKEN: str):
        self.BIRDEYE_API_TOKEN = BIRDEYE_API_TOKEN
        self.headers = {"accept": "application/json", "x-chain": "solana", "X-API-KEY": self.BIRDEYE_API_TOKEN}

    def set_token_list(self, token_list: List[TokenData] = None):
        self.token_list = token_list

    def populate_token_list(self):
        """Populates self.token_list: List[TokenData]"""
        self.populate_candle_data()
        logger.info("populate_candle_data done")

        for token in self.token_list:
            if len(token.candle_data) < 14:
                continue

            self.populate_ath_metrics(token=token)

            if not token.ath_price_usd or token.ath_price_usd < 0.006:
                continue

            self.populate_drawdown_metrics(token=token)

        filtered_list = list()
        for token in self.token_list:
            if (
                token.ath_price_time
                and token.ath_price_usd
                and token.drawdown_price_usd
                and token.drawdown_price_time
                and token.drawdown_percent
                and token.drawdown_consecutive_days_start
                and token.drawdown_percent >= 0.7
                and token.ath_price_usd >= 0.006
                and len(token.candle_data) >= 14
            ):
                token.candle_data = list()
                filtered_list.append(token)

        self.set_token_list(token_list=filtered_list)

    def populate_candle_data(self, candle_days: int = 365) -> List[TokenData]:
        """_summary_

            NOTE: Timestamp for candle is the beginning of the time period
        Args:
            token (TokenData): _description_
            filter_days (int, optional): _description_. Defaults to 14.
        """
        current_time = datetime.now(timezone.utc).replace(second=0, microsecond=0, minute=0)
        i = 0
        for token in self.token_list:
            i += 1
            logger.info(
                "{a} of {b}: {x} {y}".format(a=i, b=len(self.token_list), x=token.symbol, y=token.mint_address)
            )
            utc_from = max(
                current_time - timedelta(days=candle_days),
                token.create_date.replace(minute=0, second=0, microsecond=0),
            )
            logger.info("Create date: {t}".format(t=token.create_date))
            logger.info("Start date: {t}".format(t=utc_from))
            logger.info("End date: {t}".format(t=current_time))
            candle_data_hourly = self.get_candle_data(
                mint_address=token.mint_address, start_date=utc_from, end_date=current_time
            )

            if not self.verify_volume_authenticity(hourly_candles=candle_data_hourly[-24:]):
                logger.info("Volume volatility not met for {x} {y}".format(x=token.symbol, y=token.mint_address))
                continue

            calculated_results = self.condense_candles_to_days(candles_to_condense=candle_data_hourly)

            token.candle_data = calculated_results

    @staticmethod
    def _get_candle(candle_list: List[CandleData], time: datetime = None) -> CandleData:
        if time:
            value_list = [x for x in candle_list if x.time == time]
        if len(value_list) != 1:
            return None

        return value_list[0]

    @retry(
        stop=stop_after_attempt(3),  # Retry 3 times
        wait=wait_fixed(2),  # Wait 2 seconds between retries
        retry=retry_if_exception_type((RequestException, HTTPError, SSLError)),  # Retry on RequestException
        reraise=True,  # Reraise the last exception after retries
    )
    def get_candle_data(self, mint_address: str, start_date: datetime, end_date: datetime) -> List[CandleData]:
        """_summary_

        Args:
            start_date (datetime): _description_
            end_date (datetime): _description_
            interval_minutes (int): _description_

        Returns:
            List[CandleData]: _description_
        """

        temp_end_time = start_date
        results = []
        while temp_end_time < end_date:
            temp_end_time = min(start_date + timedelta(hours=99), end_date)

            time_from = int(start_date.timestamp())
            time_to = int(temp_end_time.timestamp())

            logger.info("Calling chart for {s}".format(s=mint_address))

            params = {
                "address": mint_address,
                "type": "1H",
                "currency": "usd",
                "time_from": time_from,
                "time_to": time_to,
            }
            url = "https://public-api.birdeye.so/defi/v3/ohlcv"
            response = requests.get(url, headers=self.headers, params=params)
            logger.info(f"Response Received. Params: {', '.join(f'{key}={value}' for key, value in params.items())}")
            sleep(0.2)
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
                results.append(
                    CandleData(
                        time=dt,
                        open=each["o"],
                        high=each["h"],
                        low=each["l"],
                        close=each["c"],
                        volume=each["v_usd"],
                    )
                )
            start_date = temp_end_time + timedelta(hours=1)

        return results

    def condense_candles_to_days(self, candles_to_condense: List[CandleData]) -> List[CandleData]:
        """ """
        distinct_days = sorted({dt.time.date() for dt in candles_to_condense})

        calculated_results = list()
        for day in distinct_days:
            candles_for_day = list()
            for x in candles_to_condense:
                if x.time.date() == day:
                    candles_for_day.append(x)
                if len(candles_for_day) == 24:
                    break

            high_close = max([x.close for x in candles_for_day])
            high_open = max([x.open for x in candles_for_day])
            high = max(high_close, high_open)

            low_close = min([x.close for x in candles_for_day])
            low_open = min([x.open for x in candles_for_day])
            low = min(low_close, low_open)

            min_hourly_candle = min([x.time for x in candles_for_day])
            open_candle = self._get_candle(candle_list=candles_for_day, time=min_hourly_candle)

            max_hourly_candle = max([x.time for x in candles_for_day])
            close_candle = self._get_candle(candle_list=candles_for_day, time=max_hourly_candle)

            volume_sum = round(sum([x.volume for x in candles_for_day]), 0)

            calculated_results.append(
                CandleData(
                    time=open_candle.time,
                    open=open_candle.open,
                    high=high,
                    low=low,
                    close=close_candle.close,
                    volume=volume_sum,
                )
            )
        return calculated_results

    def populate_ath_metrics(self, token: TokenData):
        """_summary_

        Args:
            token_list (List[TokenData]): _description_

        Returns:
            List[TokenData]: _description_
        """
        ath_price_usd = max([x.high for x in token.candle_data])
        ath_price_time = max([x.time for x in token.candle_data if x.high == ath_price_usd])

        token.ath_price_time = ath_price_time
        token.ath_price_usd = ath_price_usd

    def verify_volume_authenticity(self, hourly_candles: List[CandleData] = None) -> bool:
        """Verify volume data looks authentic

        Args:
            hourly_candles (List[CandleData]):

        Returns:
            List[TokenData]: _description_
        """
        volumes = [x.volume for x in hourly_candles][:-1]
        co_eff = self.coefficient_of_variation(numbers=volumes)
        logger.info("Volume coefficiency of variation: {f}".format(f=round(co_eff, 6)))
        if co_eff < 0.4:
            return False
        return True

    @staticmethod
    def coefficient_of_variation(numbers):
        if not numbers or mean(numbers) == 0:
            return 0  # Handle empty lists or zero mean
        return stdev(numbers) / mean(numbers)

    def populate_drawdown_metrics(self, token: TokenData):
        """_summary_

        Args:
            token_list (List[TokenData]): _description_

        Returns:
            List[TokenData]: _description_
        """
        if not token.ath_price_time or not token.ath_price_usd:
            return

        # if ath is latest candle
        if token.ath_price_time == max([x.time for x in token.candle_data]):
            return

        low_price_usd = min([x.low for x in token.candle_data if x.time > token.ath_price_time])
        low_price_time = max([x.time for x in token.candle_data if x.low == low_price_usd])

        token.drawdown_price_time = low_price_time
        token.drawdown_price_usd = low_price_usd
        token.drawdown_percent = (token.ath_price_usd - token.drawdown_price_usd) / token.ath_price_usd
        token.drawdown_consecutive_days_start = self.get_time_consecutive_below_percent(
            candle_list=token.candle_data, time_greater_than=token.ath_price_time, ath_price_usd=token.ath_price_usd
        )

    def get_time_consecutive_below_percent(
        self,
        percent_dip: float = 0.6,
        candle_list: List[CandleData] = None,
        time_greater_than: datetime = None,
        ath_price_usd: float = None,
    ) -> datetime:
        candles_in_scope = [x for x in candle_list if x.time > time_greater_than]
        threshold_price = ath_price_usd * (1.0 - percent_dip)
        for i in range(len(candles_in_scope) - 2):
            if (
                candles_in_scope[i].close < threshold_price
                and candles_in_scope[i + 1].close < threshold_price
                and candles_in_scope[i + 2].close < threshold_price
            ):
                return candles_in_scope[i].time
        return None

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

        params = {
            "address": mint,
            "type": "1m",
            "currency": "usd",
            "time_from": time_from,
            "time_to": time_from,
        }
        url = "https://public-api.birdeye.so/defi/ohlcv"
        response = requests.get(url, headers=self.headers, params=params)

        # Check if the request was successful
        if response.status_code != 200:
            logger.error("Response failed for {t}: {e}".format(t=mint, e=response.text))
            if mint == "So11111111111111111111111111111111111111112":
                logger.error("Returning 160 as default")
                return 160.0
            else:
                return None

        # Parse the JSON response
        response_json = json.loads(response.text)

        if "data" not in response_json or "items" not in response_json["data"]:
            logger.error("No OCLHV data for {t}: {e}".format(t=mint, e=response_json))
            if mint == "So11111111111111111111111111111111111111112":
                logger.error("Returning 160 as default")
                return 160.0
            else:
                return None

        for each in response_json["data"]["items"]:
            return (each["o"] + each["c"]) / 2.0

        logger.error("No Price found")
        if mint == "So11111111111111111111111111111111111111112":
            logger.error("Returning 160 as default")
            return 160.0

    def update_current_prices(self):
        """_summary_"""
        mints = [x.mint_address for x in self.token_list]
        quotes = self.get_quotes(mints=mints)
        current_time = datetime.now(timezone.utc)

        for token in self.token_list:
            # Update time held
            quote_values = quotes.get(token.mint_address)
            if quote_values is None:
                logger.info("Quote is None")
                logger.info(token)
                logger.info(quote_values)
                continue

            token.current_price_usd = quote_values["current_price_per_token_usd"]
            token.current_price_time = current_time

        # Must be within 200 million of ATH or current price > 100m
        self.token_list = [
            x
            for x in self.token_list
            if x.current_price_usd is None or x.ath_price_usd - x.current_price_usd < 0.2 or x.current_price_usd >= 0.1
        ]

    def get_quotes(self, mints: List[str]) -> dict:
        """_summary_

        Args:
            mints (List[str]): _description_

        Returns:
            dict: _description_
        """
        if not mints or len(mints) == 0:
            return dict()

        comma_separated = ",".join(mints)
        url = "https://public-api.birdeye.so/defi/multi_price?check_liquidity=100000&include_liquidity=false"

        payload = {"list_address": comma_separated}

        response = requests.post(url, json=payload, headers=self.headers)

        # Check if the request was successful
        if response.status_code != 200:
            logger.info("Response failed for {t}: {e}".format(t=mints, e=response.text))
            return dict()

        # Parse the JSON response
        response_json = json.loads(response.text)

        if "data" not in response_json:
            logger.info("No quotes data for {t}: {e}".format(t=mints, e=response_json))
            return dict()

        result_dict = dict()
        for key in response_json["data"]:
            result_dict[key] = {
                "current_price_per_token_usd": response_json["data"][key]["value"],
                "current_price_per_token_sol": response_json["data"][key]["priceInNative"],
            }

        return result_dict

    def _print_data(self):
        for each in self.token_list:
            logger.info(each)
        logger.info("Token Count: {f}".format(f=len(self.token_list)))


if __name__ == "__main__":
    import os

    from dotenv import load_dotenv

    load_dotenv()
    BIRDEYE_API_TOKEN = os.environ.get("BIRDEYE_API_TOKEN")
    current_utc = datetime.now(timezone.utc)
    threshold = current_utc - timedelta(days=20)
    S = TokenCharts(BIRDEYE_API_TOKEN=BIRDEYE_API_TOKEN)
    token_list = [
        TokenData(
            name="GRIFFIN",
            symbol="GRIFFIN",
            mint_address="KENJSUYLASHUMfHyy5o4Hp2FdNqZg1AsUPhfH2kYvEP",
            create_date=threshold,
        )
    ]
    S.set_token_list(token_list=token_list)
    S.populate_token_list()
    S._print_data()
    # prices = S.get_quotes(
    #     mints=["Dz9mQ9NzkBcCsuGPFJ3r1bS4wgqKMHBPiVuniW8Mbonk", "DtR4D9FtVoTX2569gaL837ZgrB6wNjj6tkmnX9Rdk9B2"]
    # )
    # print(prices)
