"""KSPO&CO Public Data OpenAPI Collector (Zero external dependencies).

Verified endpoints (2026-11-23):
  - realtime_parking : https://www.ksponco.or.kr/online/main/parkingorsApi.do (public key, live JSON)
  - linked_2025      : https://api.kcisa.kr/openapi/API_CPM_009/request (culture.go.kr id=675, ~7,803 rows)
  - concerts_kr      : https://api.kcisa.kr/openapi/service/rest/meta/KSCperf (culture.go.kr id=96)
  - rentals          : https://api.kcisa.kr/openapi/service/rest/meta12/getKSCD0803 (culture.go.kr id=353)
  - lost_items       : https://api.kcisa.kr/openapi/service/rest/meta/KSClost (culture.go.kr id=420)
  - inout_2025       : https://api.kcisa.kr/openapi/API_CPM_008/request (culture.go.kr id=659, ~2.4M rows; capped)

Usage:
  python -X utf8 pipeline/fetch_openapi.py --only realtime_parking
  python -X utf8 pipeline/fetch_openapi.py --test
  python -X utf8 pipeline/fetch_openapi.py
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import math
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT_DIR / "data" / "api"

ENDPOINTS: dict[str, dict[str, Any]] = {
    "linked_2025": {
        "env_key": "KCISA_API_KEY_CPM009",
        "url": "https://api.kcisa.kr/openapi/API_CPM_009/request",
        "page_size": 1000,
        "max_pages": 20,
        "portal_url": "https://www.culture.go.kr/data/openapi/openapiView.do?id=675",
    },
    "concerts_kr": {
        "env_key": "KCISA_API_KEY_PERF",
        "url": "https://api.kcisa.kr/openapi/service/rest/meta/KSCperf",
        "page_size": 500,
        "max_pages": 20,
        "portal_url": "https://www.culture.go.kr/data/openapi/openapiView.do?id=96",
    },
    "rentals": {
        "env_key": "KCISA_API_KEY_RENTAL",
        "url": "https://api.kcisa.kr/openapi/service/rest/meta12/getKSCD0803",
        "page_size": 500,
        "max_pages": 10,
        "portal_url": "https://www.culture.go.kr/data/openapi/openapiView.do?id=353",
    },
    "lost_items": {
        "env_key": "KCISA_API_KEY_LOST",
        "url": "https://api.kcisa.kr/openapi/service/rest/meta/KSClost",
        "page_size": 500,
        "max_pages": 5,
        "portal_url": "https://www.culture.go.kr/data/openapi/openapiView.do?id=420",
    },
    "inout_2025": {
        "env_key": "KCISA_API_KEY_CPM008",
        "url": "https://api.kcisa.kr/openapi/API_CPM_008/request",
        "page_size": 1000,
        "max_pages": 5,  # Safety cap (5,000 rows by default; raise via --max-pages)
        "portal_url": "https://www.culture.go.kr/data/openapi/openapiView.do?id=659",
    },
}


def load_dotenv(env_path: Path) -> dict[str, str]:
    env = dict(os.environ)
    if not env_path.exists():
        return env
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        if v and not env.get(k):
            env[k] = v
    return env


def http_get(url: str, accept: str = "application/json", timeout: int = 60, retries: int = 5) -> tuple[bytes, str]:
    last_err: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (ksponco-2026-pipeline)",
                    "Accept": accept,
                },
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read(), resp.headers.get("Content-Type", "")
        except urllib.error.HTTPError as exc:
            last_err = exc
            if attempt < retries:
                wait = 3.0 * attempt if exc.code == 429 else 1.5 * attempt
                time.sleep(wait)
        except Exception as exc:
            last_err = exc
            if attempt < retries:
                time.sleep(1.5 * attempt)
    assert last_err is not None
    raise last_err


def fetch_realtime_parking(env: dict[str, str]) -> dict[str, Any]:
    api_key = env.get("KSPONCO_REALTIME_PARKING_KEY") or "PARKING21803504"
    url = f"https://www.ksponco.or.kr/online/main/parkingorsApi.do?apiKey={urllib.parse.quote(api_key)}"
    raw, ct = http_get(url, accept="application/json")
    data = json.loads(raw.decode("utf-8"))
    parking_sum = data[0].get("parking_sum") if isinstance(data, list) and data else None
    payload = {
        "fetched_at": dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).isoformat(),
        "endpoint": "https://www.ksponco.or.kr/online/main/parkingorsApi.do",
        "parking_sum": parking_sum,
        "raw": data,
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / "realtime_parking.json"
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] realtime_parking -> parking_sum={parking_sum} ({out_path.name})")
    return payload


def parse_kcisa_response(raw: bytes) -> tuple[str, str, int, list[dict[str, Any]]]:
    text = raw.decode("utf-8", errors="replace").strip()
    if text.startswith("{"):
        doc = json.loads(text)
        resp = doc.get("response", doc)
        header = resp.get("header", {})
        body = resp.get("body", {})
        code = str(header.get("resultCode", ""))
        msg = str(header.get("resultMsg", ""))
        total = int(body.get("totalCount") or 0)
        items_wrap = body.get("items") or {}
        if isinstance(items_wrap, dict):
            items = items_wrap.get("item") or []
        elif isinstance(items_wrap, list):
            items = items_wrap
        else:
            items = []
        if isinstance(items, dict):
            items = [items]
        return code, msg, total, items

    # XML fallback
    root = ET.fromstring(text)
    code = root.findtext(".//header/resultCode") or ""
    msg = root.findtext(".//header/resultMsg") or ""
    total = int(root.findtext(".//body/totalCount") or "0")
    items = []
    for elem in root.findall(".//body/items/item"):
        row = {child.tag: (child.text or "").strip() for child in elem}
        items.append(row)
    return code, msg, total, items


def parse_cpm009_description(desc: str) -> dict[str, Any]:
    """Parse structured fields from API_CPM_009 DESCRIPTION string.

    Example: '주차대수:19,방문객:57, 기온:-3.4, 풍향:3.6, 강수량:, 습도:27,휴일:,공연명:,공연관람객수:0'
    """
    keys = ["주차대수", "방문객", "기온", "풍향", "강수량", "습도", "휴일", "공연명", "공연관람객수"]
    pattern = r"(" + "|".join(re.escape(k) for k in keys) + r")\s*:"
    matches = list(re.finditer(pattern, desc or ""))
    parsed: dict[str, Any] = {}
    for idx, m in enumerate(matches):
        key = m.group(1)
        start = m.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(desc)
        val = desc[start:end].strip().rstrip(",").strip()
        parsed[key] = val

    def to_float(v: str) -> float | None:
        if not v:
            return None
        try:
            return float(v)
        except ValueError:
            return None

    def to_int(v: str) -> int | None:
        f = to_float(v)
        return int(round(f)) if f is not None else None

    return {
        "parking_count": to_int(parsed.get("주차대수", "")),
        "visitor_count": to_int(parsed.get("방문객", "")),
        "temp_c": to_float(parsed.get("기온", "")),
        "wind_dir_or_spd": to_float(parsed.get("풍향", "")),
        "precip_mm": to_float(parsed.get("강수량", "")) or 0.0,
        "humidity_pct": to_float(parsed.get("습도", "")),
        "holiday_name": parsed.get("휴일", ""),
        "is_holiday": 1 if parsed.get("휴일", "") else 0,
        "concert_name": parsed.get("공연명", ""),
        "concert_audience": to_int(parsed.get("공연관람객수", "")) or 0,
    }


def save_csv(rows: list[dict[str, Any]], path: Path) -> None:
    if not rows:
        return
    fieldnames: list[str] = []
    seen: set[str] = set()
    for r in rows:
        for k in r.keys():
            if k not in seen:
                seen.add(k)
                fieldnames.append(k)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)


def fetch_kcisa_dataset(
    name: str,
    cfg: dict[str, Any],
    api_key: str,
    test_mode: bool = False,
    override_max_pages: int | None = None,
) -> int:
    page_size = 5 if test_mode else cfg["page_size"]
    max_pages = 1 if test_mode else (override_max_pages or cfg["max_pages"])
    all_items: list[dict[str, Any]] = []
    total_count = 0

    for page in range(1, max_pages + 1):
        # serviceKey on Korean portals may already be URL-encoded or plain; keep safe encoding
        encoded_key = api_key if "%" in api_key else urllib.parse.quote(api_key, safe="")
        url = f"{cfg['url']}?serviceKey={encoded_key}&numOfRows={page_size}&pageNo={page}"
        # KCISA JSON serializer drops CDATA DESCRIPTION fields to null on API_CPM_008/009; use XML!
        accept = "application/xml" if name in ("linked_2025", "inout_2025") else "application/json"
        raw, _ = http_get(url, accept=accept)
        code, msg, total, items = parse_kcisa_response(raw)
        if code not in ("0000", "00", ""):
            raise RuntimeError(f"{name} page {page} failed: resultCode={code}, resultMsg={msg}")
        total_count = total or total_count
        if not items:
            break
        all_items.extend(items)
        print(f"  [{name}] page {page}: +{len(items)} rows (accum={len(all_items)}/{total_count})")
        if test_mode or (total_count and len(all_items) >= total_count):
            break
        if len(items) < page_size:
            break
        time.sleep(2.2)

    if name == "linked_2025":
        enriched = []
        for item in all_items:
            desc = " , ".join(
                str(item.get(k) or "")
                for k in ("DESCRIPTION", "description", "SUB_DESCRIPTION", "TITLE", "title")
                if item.get(k)
            )
            row = dict(item)
            row.update(parse_cpm009_description(desc))
            enriched.append(row)
        all_items = enriched

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    suffix = "_test" if test_mode else ""
    json_path = OUT_DIR / f"{name}{suffix}.json"
    csv_path = OUT_DIR / f"{name}{suffix}.csv"
    json_path.write_text(json.dumps(all_items, ensure_ascii=False, indent=2), encoding="utf-8")
    save_csv(all_items, csv_path)
    print(f"[OK] {name}: saved {len(all_items):,} rows -> {csv_path.name}")
    return len(all_items)


def main() -> int:
    parser = argparse.ArgumentParser(description="KSPO&CO Public Data OpenAPI Collector")
    parser.add_argument("--only", choices=["realtime_parking", *ENDPOINTS.keys()], help="Fetch a single target")
    parser.add_argument("--test", action="store_true", help="Fetch 5 sample rows per configured API to verify keys")
    parser.add_argument("--include-inout-2025", action="store_true", help="Also fetch 2025 full inout sample (API_CPM_008)")
    parser.add_argument("--max-pages", type=int, default=None, help="Override max pages per API")
    args = parser.parse_args()

    env = load_dotenv(ROOT_DIR / ".env")
    targets = [args.only] if args.only else ["realtime_parking", "linked_2025", "concerts_kr", "rentals", "lost_items"]
    if args.include_inout_2025 and "inout_2025" not in targets and not args.only:
        targets.append("inout_2025")

    ok, skipped, failed = 0, 0, 0
    for target in targets:
        if target == "realtime_parking":
            try:
                fetch_realtime_parking(env)
                ok += 1
            except Exception as exc:
                print(f"[FAIL] realtime_parking: {exc}")
                failed += 1
            continue

        cfg = ENDPOINTS[target]
        key = env.get(cfg["env_key"]) or env.get("KCISA_API_KEY") or ""
        if not key:
            print(f"[SKIP] {target}: missing {cfg['env_key']} in .env -> apply at {cfg['portal_url']}")
            skipped += 1
            continue
        try:
            fetch_kcisa_dataset(target, cfg, key, test_mode=args.test, override_max_pages=args.max_pages)
            ok += 1
        except Exception as exc:
            print(f"[FAIL] {target}: {exc}")
            failed += 1

    print(f"\nSummary: ok={ok}, skipped={skipped}, failed={failed}")
    return 1 if failed > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
