import json
from datetime import datetime, timedelta, timezone
from time import sleep
from typing import List, Tuple

import requests
from requests.exceptions import HTTPError, RequestException, SSLError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_fixed

from spl_drawdown.types.token_data import TokenData
from spl_drawdown.utils.log import get_logger

logger = get_logger()


class TokenVolumes:
    def __init__(self, BIRDEYE_API_TOKEN: str):
        self.BIRDEYE_API_TOKEN = BIRDEYE_API_TOKEN
        self.headers = {"accept": "application/json", "x-chain": "solana", "X-API-KEY": self.BIRDEYE_API_TOKEN}
        ignore_tokens_seed = [
            "So11111111111111111111111111111111111111112",
            "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
            "6p6xgHyF7AeE6TZkSmFsko444wqoP15icUSqi2jfGiPN",
            "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",
            "3NZ9JMVBmGAqocybic2c7LQCJScmgsAZ6vQqTDzcqmJh",
            "8x5VqbHA8D7NkD52uNuS5nnt3PwA8pLD34ymskeSo2Wn",
            "2qEHjDLDLbuBgRYvsxhc5D6uDWAivNFZGan56P1tpump",
            "J1toso1uCk3RLmjorhTtrVwY9HJ7X8V9yYac6Y7kGCPn",
            "27G8MtK7VtTcCHkpASjSDdkWWYfoqT6ggEuKidVJidD4",
        ]
        self.ignore_tokens_dict = {token: True for token in ignore_tokens_seed}
        self.last_run_date = None

    def get_tokens(self, min_volume: int = 500000) -> List[TokenData]:
        """_summary_

        Args:
            min_volume (float, optional): _description_. Defaults to 1000000.0.
            timeframe_hours (int, optional): _description_. Defaults to 1.

        Returns:
            List[TokenData]: _description_
        """
        has_next = True
        offset = 0
        results = list()
        while has_next:
            params = {
                "sort_by": "volume_24h_usd",
                "sort_type": "desc",
                "min_volume_24h_usd": min_volume,
                "offset": offset,
                "limit": 100,
            }
            url = "https://public-api.birdeye.so/defi/v3/token/list"
            response = requests.get(url, headers=self.headers, params=params)
            offset += 100

            # Check if the request was successful
            if response.status_code != 200:
                logger.info("Response failed : {e}".format(e=response.text))
                return list()
            response_json = json.loads(response.text)

            if not response_json.get("data") or not response_json["data"].get("items"):
                logger.info("No results found")
                return list()
            has_next = response_json["data"]["has_next"]

            for each in response_json["data"]["items"]:
                if each["address"] in self.ignore_tokens_dict:
                    continue

                results.append(
                    TokenData(
                        name=each["name"],
                        symbol=each["symbol"],
                        mint_address=each["address"],
                        dex="",
                        volume_usd=round(each["volume_24h_usd"], 0),
                        trades_count=each["trade_24h_count"],
                        market="",
                    )
                )

        self.last_run_date = datetime.now(timezone.utc)
        filtered_list = list()
        logger.info("Tokens with volume: {t}".format(t=len(results)))
        for token in results:
            logger.info("Checking {t}: {s} {a}".format(t=token.symbol, s=token.name, a=token.mint_address))
            if not self.verify_ownership(token=token):
                continue

            if not self.verify_security(token=token):
                continue

            token, is_valid = self.verify_market(token=token)
            if not is_valid:
                logger.info("No Market passed for {x}: {a}".format(x=token.symbol, a=token.mint_address))
                continue

            filtered_list.append(token)

        logger.info("Tokens returned: {t}".format(t=[x.symbol for x in filtered_list]))

        return filtered_list

    @retry(
        stop=stop_after_attempt(3),  # Retry 3 times
        wait=wait_fixed(2),  # Wait 2 seconds between retries
        retry=retry_if_exception_type((RequestException, HTTPError, SSLError)),  # Retry on RequestException
        reraise=True,  # Reraise the last exception after retries
    )
    def verify_ownership(self, token: TokenData) -> bool:
        """Verify basic details such as ownership and create date

        ***this will not fail if no data is returned***

        Args:
            token (TokenData): _description_

        Returns:
            bool: _description_
        """
        params = {"address": token.mint_address}
        url = "https://public-api.birdeye.so/defi/token_creation_info"

        response = requests.get(url, headers=self.headers, params=params)
        sleep(0.5)
        # Check if the request was successful
        if response.status_code != 200:
            logger.error("Response failed : {e}".format(e=response.text))
            return True

        response_json = json.loads(response.text)

        if "data" not in response_json:
            logger.error("Response not valid : {e}".format(e=response_json))
            return True

        if response_json["data"] is None:
            return True

        owner = response_json["data"].get("owner")
        if owner is None or owner not in (
            "TSLvdd1pWpHVjahSpsvCXUbgwsL3JAcvokwaKt1eokM",
            "WLHv2UAZm6z4KyaaELi5pjdbJh6RESMva1Rnn8pJVVh",
        ):
            logger.error("Owner wrong value")
            return False

        creation_unix_time = response_json["data"].get("blockUnixTime")
        create_date = datetime.fromtimestamp(creation_unix_time, tz=timezone.utc)
        max_age = datetime.now(timezone.utc) - timedelta(days=14)
        if create_date > max_age:
            logger.error("Creation date not old enough")
            return False
        token.create_date = create_date

        return True

    @retry(
        stop=stop_after_attempt(3),  # Retry 3 times
        wait=wait_fixed(2),  # Wait 2 seconds between retries
        retry=retry_if_exception_type((RequestException, HTTPError, SSLError)),  # Retry on RequestException
        reraise=True,  # Reraise the last exception after retries
    )
    def verify_security(self, token: TokenData) -> bool:
        """_summary_redeploy

        Args:
            token (TokenData): _description_

        Returns:
            bool: _description_
        """
        params = {"address": token.mint_address}
        url = "https://public-api.birdeye.so/defi/token_security"

        response = requests.get(url, headers=self.headers, params=params)
        sleep(0.5)
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
            logger.error("Update authority wrong value")
            return False

        creation_time = response_json["data"].get("creationTime")
        if creation_time:
            max_age = datetime.now(timezone.utc) - timedelta(days=14)
            dt = datetime.fromtimestamp(creation_time, tz=timezone.utc)
            if not token.create_date:
                token.create_date = dt
            if dt > max_age:
                logger.error("Creation date not old enough")
                return False
        elif token.create_date is None:
            logger.error("No creation date found")
            return False

        freezeable = response_json["data"].get("freezeable")
        if freezeable:
            logger.error("Freezable")
            return False

        top10_per = response_json["data"].get("top10HolderPercent")
        if top10_per:
            logger.info("top10 per = {x}".format(x=top10_per))
        if top10_per and top10_per > 0.5:
            logger.error("top10_per > 0.5")
            return False
        logger.info("Passed security")
        return True

    def verify_market(self, token: TokenData, min_liquidity: int = 100000) -> Tuple[TokenData, bool]:
        """_summary_

        Args:
            token (TokenData): _description_

        Returns:
            bool: _description_
        """
        valid_markets = ["Pump Amm", "Raydium", "Raydium Cp", "Raydium CPMM"]
        valid_markets = [x.upper() for x in valid_markets]
        params = {
            "address": token.mint_address,
            "time_frame": "1h",
            "sort_type": "desc",
            "sort_by": "liquidity",
            "offset": 0,
            "limit": 10,
        }
        url = "https://public-api.birdeye.so/defi/v2/markets"
        response = requests.get(url, headers=self.headers, params=params)
        sleep(0.5)
        # Check if the request was successful
        if response.status_code != 200:
            logger.error("Response failed : {e}".format(e=response.text))
            return token, False

        response_json = json.loads(response.text)

        if "data" not in response_json or "items" not in response_json["data"]:
            logger.error("Response not valid : {e}".format(e=response_json))
            return token, False

        max_age = datetime.now(timezone.utc) - timedelta(days=14)

        for item in response_json["data"]["items"]:
            if item["source"].upper() not in valid_markets:
                continue
            logger.info("Market: {m}".format(m=item["source"]))
            if "createdAt" in item:
                date_string = item["createdAt"].replace("Z", "+00:00")
                dt = datetime.fromisoformat(date_string)
                if dt > max_age:
                    logger.info("Age not minimum value: {v}".format(v=dt))
                    continue
            if "volume24h" in item and (item["volume24h"] is None or item["volume24h"] < min_liquidity):
                logger.info("Volume not minimum value: {v}".format(v=item["volume24h"]))
                continue
            if "liquidity" in item and (item["liquidity"] is None or item["liquidity"] < min_liquidity):
                logger.info("Liquidity not minimum value: {v}".format(v=item["liquidity"]))
                continue
            token.market = item["address"]
            token.dex = item["source"]
            logger.info("Market Passed")
            return token, True

        return token, False

    def can_run(self, hours_between_runs: int = 24) -> bool:
        """Can get tokens procedure run
        or day of last run and current day are not the same and minute > 10
        Returns:
            bool: _description_
        """
        if self.last_run_date is None:
            return True

        current_utc = datetime.now(timezone.utc)
        threshold = current_utc - timedelta(hours=hours_between_runs)

        # Check if last_run_date is on a different day and current minute > 10
        is_different_day = self.last_run_date.date() != current_utc.date()
        is_minute_greater_than_10 = current_utc.minute > 10

        if threshold >= self.last_run_date or (is_different_day and is_minute_greater_than_10):
            return True

        return False


if __name__ == "__main__":
    import os

    from dotenv import load_dotenv

    load_dotenv()

    api_key = os.environ.get("BIRDEYE_API_TOKEN")
    a = TokenVolumes(BIRDEYE_API_TOKEN=api_key)
    tokens = a.get_tokens()

    for x in tokens:
        logger.info(x)
    # a.get_tokens()
    # tt, t = a.verify_market(
    #     token=TokenData(name="", symbol="", mint_address="ELM5N5hb3RVrHsDYgseNdxKaiaML13sasAa8ggYjpump")
    # )
    # print(tt)
    # print(t)
