import requests
import json
import sys

# A simple, lightweight "oracle" to fetch cryptocurrency prices.
# It uses the CoinGecko API, which is free and doesn't require an API key.
# API Documentation: https://www.coingecko.com/en/api/documentation

# --- Configuration ---
# The IDs for the tokens on CoinGecko.
# You can find these on a token's page, e.g., https://www.coingecko.com/en/coins/akash-network
TOKEN_IDS = {
    "akash": "akash-network",
    "iexec": "rlc"
}

API_URL = "https://api.coingecko.com/api/v3/simple/price"

def get_prices():
    """
    Fetches the current USD price for the configured tokens.
    """
    try:
        params = {
            "ids": ",".join(TOKEN_IDS.values()),
            "vs_currencies": "usd"
        }
        response = requests.get(API_URL, params=params)
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)

        data = response.json()

        # Structure the output for clarity and machine readability.
        profitability_data = {
            "akash": {
                "token": "AKT",
                "price_usd": data.get(TOKEN_IDS["akash"], {}).get("usd")
            },
            "iexec": {
                "token": "RLC",
                "price_usd": data.get(TOKEN_IDS["iexec"], {}).get("usd")
            }
        }

        return profitability_data

    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from CoinGecko API: {e}", file=sys.stderr)
        return None

if __name__ == "__main__":
    prices = get_prices()
    if prices:
        # Print the data as a JSON string to stdout.
        # This makes it easy for other scripts to consume.
        print(json.dumps(prices, indent=2))
    else:
        # Exit with a non-zero status code to indicate failure.
        sys.exit(1)