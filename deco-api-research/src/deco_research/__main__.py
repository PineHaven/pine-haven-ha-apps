"""Module entry point."""

import asyncio

from .service import run

if __name__ == "__main__":
    asyncio.run(run())
