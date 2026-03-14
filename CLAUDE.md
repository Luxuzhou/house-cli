# House CLI - AI Agent Development Rules

## Project Overview
A CLI tool for searching houses (buy/rent) across multiple Chinese real estate platforms.
Tech stack: Python 3.12, Click, httpx, Rich, PyYAML.

## Architecture
- All platform adapters implement `BaseClient` (src/house_cli/client/base.py)
- All adapters return unified `House`/`HouseDetail` models (src/house_cli/models/house.py)
- Commands use adapters through the base class interface, never directly
- Rich formatting goes to stderr, structured data (JSON/YAML) goes to stdout

## File Ownership Rules (CRITICAL)

### Agent 1: Client Adapters - Core Platforms
**Owns:** `src/house_cli/client/` (entire directory)
- `http.py` - HTTP client wrapper with anti-detection headers, Gaussian jitter delays, exponential backoff retry
- `auth.py` - Browser cookie extraction (Chrome/Edge), credential storage at ~/.config/house-cli/credential.json, 7-day TTL refresh
- `adapters/beike.py` - Beike/Lianjia adapter (buy + rent)
- `adapters/ziroom.py` - Ziroom adapter (rent only)
**DO NOT modify any files outside `src/house_cli/client/`**

### Agent 2: Client Adapters - Secondary Platforms
**Owns:** `src/house_cli/client/adapters/` (4 files only)
- `adapters/anjuke.py` - Anjuke adapter
- `adapters/tongcheng.py` - 58 Tongcheng adapter
- `adapters/fang.py` - Fang.com adapter
- `adapters/zhuge.py` - Zhuge Zhaofang adapter
**DO NOT modify:** `http.py`, `auth.py`, `beike.py`, `ziroom.py`, or any files outside `src/house_cli/client/adapters/`
**MUST USE:** `BaseClient` from `base.py`, `HttpClient` from `http.py` for all HTTP requests

### Agent 3: Commands + Models + Utils
**Owns:**
- `src/house_cli/commands/` (all 7 command files)
- `src/house_cli/models/` (house.py, filter.py, output.py)
- `src/house_cli/utils/` (cache.py, config.py, formatter.py)
**DO NOT modify any files in `src/house_cli/client/`**
**For adapter calls, use mock data initially.** Integration with real adapters happens in the merge phase.

## Anti-Detection Standards (All adapters must follow)
- User-Agent: Chrome latest on macOS
- Request delay: Gaussian jitter (mean=0.3s, sigma=0.15s)
- 5% random long pause (2-5s) simulating human browsing
- Retry on 429/5xx: exponential backoff (10s -> 20s -> 40s), max 3 attempts
- Headers: sec-ch-ua, DNT, Priority, proper Referer

## Data Model Contract
All adapters MUST return `House` or `HouseDetail` dataclass instances.
- `price` field: total price in 万元 (buy) or monthly rent in 元 (rent)
- `price_unit`: "万" for buy, "元/月" for rent
- `platform` field: one of "beike", "anjuke", "tongcheng", "ziroom", "fang", "zhuge"
- `id` field: platform-specific listing ID

## Dependency Management
All dependencies are pre-installed. DO NOT run `uv add` or `pip install`.
