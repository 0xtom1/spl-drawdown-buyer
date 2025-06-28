import json
from datetime import timedelta
from typing import List

import requests

from spl_drawdown.analyzer.types.cd import CandleData
from spl_drawdown.analyzer.types.td import TokenData
from spl_drawdown.analyzer.utils.log_analyzer import get_logger

logger = get_logger()


class AlgoRequirements1:
    def __init__(self, BIRDEYE_API_TOKEN: str):
        self.BIRDEYE_API_TOKEN = BIRDEYE_API_TOKEN
        self.headers = {"accept": "application/json", "x-chain": "solana", "X-API-KEY": self.BIRDEYE_API_TOKEN}

    def is_meets_reqs(self, token: TokenData):
        logger.info("--")
        logger.info("Requirements for {s} {t}".format(s=token.symbol, t=token.mint_address))
        logger.info(token)
        if len(token.candle_data) == 0:
            logger.info("No candle data")
            return False
        max_vol = self._get_max_vol3_candle(candle_data=token.candle_data)
        is_high = self._is_max_price_candle(candle_data=token.candle_data)
        candle = self._get_latest_candle(candle_data=token.candle_data)
        passed_security = True  # self.verify_security(token=token)
        # logger.info("Latest candle : {c}".format(c=candle))
        logger.info("Max Volume3 last 7 days: {v}".format(v=max_vol))
        len_candles = len([x.close for x in token.candle_data if x.close is not None])
        if (
            candle.vol_l3 is None
            or candle.vol_l3_24avg is None
            or candle.vol_l3_168avg is None
            or candle.ema24 is None
            or candle.ma24 is None
            or candle.per_l3 is None
            or candle.ma168 is None
            or is_high is None
            or candle.per_l24 is None
        ):
            logger.info("Does not meet reqs - values are None")
            return False
        if (
            candle.vol_l3 > candle.vol_l3_24avg * 2.5
            and candle.vol_l3 > candle.vol_l3_168avg * 2.5
            and candle.ema24 > candle.ma24
            and 0.02 < candle.per_l3 <= 10.0
            and 0.02 < candle.per_l24 <= 10.0
            and candle.vol_l3 >= max_vol
            and candle.ma24 > candle.ma168
            and is_high is True
            and candle.vol_l3 / candle.vol_l3_24avg < 40
            and candle.volume >= 2000000
            and len_candles >= 14 * 24 * 0.9
            and passed_security
        ):
            logger.info("Meets req")
            return True
        else:
            logger.info("Does not meet reqs")
            if len_candles < 14 * 24 * 0.9:
                logger.info("Reason: Not enough candles")
            if candle.vol_l3 <= candle.vol_l3_24avg * 2.5:
                logger.info("Reason: vol_l3 not 2.5x vol_l3_24avg")
            if candle.ema24 <= candle.ma24:
                logger.info("Reason: ema < ma")
            if candle.per_l3 <= 0.02 or candle.per_l3 > 10.0:
                logger.info("Reason: last 3 hour per")
            if candle.per_l24 <= 0.02 or candle.per_l24 > 10.0:
                logger.info("Reason: last 24 hour per")
            if candle.vol_l3 <= candle.vol_l3_168avg * 2.5:
                logger.info("Reason: vol_l3 not 2.5x vol_l3_168avg")
            if not token.mint_address.lower().endswith("pump") and not token.mint_address.lower().endswith("bonk"):
                logger.info("Reason: Not a pump coin")
            if candle.vol_l3 < max_vol:
                logger.info("Reason: vol_l3 not 7 day high")
            if candle.ma24 <= candle.ma168:
                logger.info("Reason: ma24 <= ma168")
            if is_high is False:
                logger.info("Reason: Price not high")
            if candle.vol_l3 / candle.vol_l3_24avg > 40:
                logger.info("Reason: Vol spike too high: {f}".format(f=round(candle.vol_l3 / candle.vol_l3_24avg, 2)))
            if candle.volume < 2000000:
                logger.info("Not enough volume")
            if not passed_security:
                logger.info("Did not pass security")
            return False

    @staticmethod
    def _get_latest_candle(candle_data: List[CandleData]) -> CandleData:
        max_time = max([x.time for x in candle_data])
        for candle in candle_data:
            if candle.time == max_time:
                return candle
        return None

    @staticmethod
    def _get_max_vol3_candle(candle_data: List[CandleData], hours=168) -> float:
        max_time = max([x.time for x in candle_data])
        min_time = max_time - timedelta(hours=hours)
        if max_time is None or min_time is None:
            return None
        max_vol_list = [
            x.vol_l3 for x in candle_data if x.time and x.vol_l3 and x.time < max_time and x.time >= min_time
        ]
        if len(max_vol_list) > 0:
            return max(max_vol_list)
        else:
            return None

    @staticmethod
    def _is_max_price_candle(candle_data: List[CandleData], hours=168) -> float:
        current_time = max([x.time for x in candle_data])
        max_time = current_time - timedelta(hours=2)
        min_time = current_time - timedelta(hours=hours)
        if current_time is None or min_time is None or max_time is None:
            return None
        previous_max_price_list = [
            (x.high + x.low) / 2.0
            for x in candle_data
            if x.time and x.high and x.time < max_time and x.time > min_time
        ]
        current_max_price_list = [
            (x.high + x.low) / 2.0 for x in candle_data if x.time and x.high and x.time >= max_time
        ]

        if (
            previous_max_price_list is None
            or current_max_price_list is None
            or len(previous_max_price_list) == 0
            or len(current_max_price_list) == 0
        ):
            return False
        current_max = max(current_max_price_list)
        previous_max = max(previous_max_price_list)

        logger.info("Last 3 hour max= {m} Previous week max= {p}".format(m=current_max, p=previous_max))
        if current_max > previous_max:
            return True
        else:
            return False

    def verify_security(self, token: TokenData) -> bool:
        """_summary_

        Args:
            token (TokenData): _description_

        Returns:
            bool: _description_
        """
        logger.info("Checking security for {x}: {a}".format(x=token.symbol, a=token.mint_address))
        params = {"address": token.mint_address}
        url = "https://public-api.birdeye.so/defi/token_security"
        response = requests.get(url, headers=self.headers, params=params)

        # Check if the request was successful
        if response.status_code != 200:
            logger.error("Response failed : {e}".format(e=response.text))
            return False

        response_json = json.loads(response.text)

        if "data" not in response_json:
            logger.error("Response not valid : {e}".format(e=response_json))
            return False

        update_authority = response_json["data"].get("metaplexUpdateAuthority")
        if update_authority is None or update_authority not in (
            "TSLvdd1pWpHVjahSpsvCXUbgwsL3JAcvokwaKt1eokM",
            "WLHv2UAZm6z4KyaaELi5pjdbJh6RESMva1Rnn8pJVVh",
        ):
            # self.ignore_tokens.append(token.mint_address)
            logger.error("Update authority wrong value")
            return False

        freezeable = response_json["data"].get("freezeable")
        if freezeable:
            logger.error("Freezable")
            return False

        logger.info("Passed security")
        return True
