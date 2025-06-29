#!/usr/bin/env python3
"""Run the Google Ads MCP server."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.__main__ import main
import asyncio

if __name__ == "__main__":
    asyncio.run(main())