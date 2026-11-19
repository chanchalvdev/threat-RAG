"""Refresh the knowledge base from its feeds.

    python -m app.scripts.refresh_feeds                 # one run; exit 1 = a feed failed, 2 = eval regressed
    python -m app.scripts.refresh_feeds --every 24h     # loop (the compose `scheduler` service)
    python -m app.scripts.refresh_feeds --force-mitre   # re-index ATT&CK even if the bundle is unchanged

Needs Qdrant, the embedder and REDIS_URL (shared with the API, so its KEV copy and status update).
"""
import argparse
import asyncio
import re

from app.core.logging import configure_logging, get_logger
from app.feeds.runner import run_once

log = get_logger(__name__)
_UNITS = {"m": 60, "h": 3600, "d": 86400}


def parse_every(text: str) -> int:
    match = re.fullmatch(r"(\d+)([mhd])", text.strip())
    if not match or int(match.group(1)) == 0:
        raise argparse.ArgumentTypeError("use a number and m, h or d, e.g. 30m, 24h, 7d")
    return int(match.group(1)) * _UNITS[match.group(2)]


async def main(args: argparse.Namespace) -> int:
    configure_logging()
    while True:
        status = await run_once(force_mitre=args.force_mitre)
        code = 0 if status is None else 2 if status.regressed else 0 if status.ok else 1
        if not args.every:
            return code
        log.info("feeds_sleeping", seconds=args.every)
        await asyncio.sleep(args.every)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--every", type=parse_every, default=0, help="repeat at this interval, e.g. 24h")
    parser.add_argument("--force-mitre", action="store_true")
    raise SystemExit(asyncio.run(main(parser.parse_args())))
