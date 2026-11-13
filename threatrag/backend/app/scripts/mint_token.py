"""Mint a development bearer token:  python -m app.scripts.mint_token --sub alice --hours 8"""
import argparse

from app.api.identity import mint_token

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sub", required=True, help="identity the token is issued to")
    parser.add_argument("--hours", type=float, default=8.0)
    args = parser.parse_args()
    print(mint_token(args.sub, args.hours))
