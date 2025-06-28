import os

import dotenv

dotenv.load_dotenv()
settings_key_values = dict()
try:
    settings_key_values["SOLANA_PRIVATE_KEY"] = os.environ.get("SOLANA_PRIVATE_KEY")
    settings_key_values["HELIUS_API_KEY"] = os.environ.get("HELIUS_API_KEY")
    settings_key_values["BET_AMOUNT_SOL"] = float(os.environ.get("BET_AMOUNT_SOL"))
    settings_key_values["MIN_24HR_VOLUME"] = float(os.environ.get("MIN_24HR_VOLUME"))
    settings_key_values["BIRDEYE_API_TOKEN"] = os.environ.get("BIRDEYE_API_TOKEN")
except KeyError:
    raise ValueError("Environment variable is required but not set")
