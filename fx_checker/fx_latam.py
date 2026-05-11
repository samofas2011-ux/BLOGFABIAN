#!/usr/bin/env python3
"""
Daily LATAM FX checker — fetches currency rates vs USD from Frankfurter API
and writes results to LATAM_FX.md at the repo root.
"""

import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

FRANKFURTER_URL = "https://api.frankfurter.app"

# LATAM currencies with full names; Frankfurter/ECB may not carry all of them
LATAM_CURRENCIES = {
    "ARS": "Argentine Peso",
    "BOB": "Bolivian Boliviano",
    "BRL": "Brazilian Real",
    "CLP": "Chilean Peso",
    "COP": "Colombian Peso",
    "CRC": "Costa Rican Colón",
    "DOP": "Dominican Peso",
    "GTQ": "Guatemalan Quetzal",
    "HNL": "Honduran Lempira",
    "MXN": "Mexican Peso",
    "NIO": "Nicaraguan Córdoba",
    "PAB": "Panamanian Balboa",
    "PEN": "Peruvian Sol",
    "PYG": "Paraguayan Guaraní",
    "UYU": "Uruguayan Peso",
    "VES": "Venezuelan Bolívar Soberano",
}

OUTPUT_PATH = Path(__file__).resolve().parent.parent / "LATAM_FX.md"


def fetch_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode())


def get_available_currencies() -> set[str]:
    data = fetch_json(f"{FRANKFURTER_URL}/currencies")
    return set(data.keys())


def get_rates(symbols: list[str]) -> dict:
    joined = ",".join(symbols)
    data = fetch_json(f"{FRANKFURTER_URL}/latest?from=USD&to={joined}")
    return data


def build_markdown(rates: dict, date_str: str, missing: list[str]) -> str:
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        "# LATAM FX Rates vs USD",
        "",
        f"**Updated:** {now_utc}  ",
        f"**Rate date:** {date_str}  ",
        f"**Source:** [Frankfurter API](https://www.frankfurter.app) (ECB data)",
        "",
        "| Currency | Code | Units per 1 USD |",
        "|----------|------|----------------:|",
    ]

    for code, name in sorted(LATAM_CURRENCIES.items()):
        if code in rates:
            rate = rates[code]
            lines.append(f"| {name} | {code} | {rate:,.4f} |")

    if missing:
        lines += [
            "",
            "### Not available via Frankfurter/ECB",
            "",
            "| Currency | Code |",
            "|----------|------|",
        ]
        for code in sorted(missing):
            lines.append(f"| {LATAM_CURRENCIES[code]} | {code} |")
        lines.append("")
        lines.append(
            "> These currencies are not published by the European Central Bank."
        )

    lines += [
        "",
        "---",
        "*Generated automatically by [fx_latam.py](fx_checker/fx_latam.py)*",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    print("Fetching available currencies from Frankfurter...")
    try:
        available = get_available_currencies()
    except urllib.error.URLError as exc:
        print(f"ERROR: Could not reach Frankfurter API — {exc}", file=sys.stderr)
        return 1

    wanted = [c for c in LATAM_CURRENCIES if c in available]
    missing = [c for c in LATAM_CURRENCIES if c not in available]

    if not wanted:
        print("ERROR: No LATAM currencies found in Frankfurter.", file=sys.stderr)
        return 1

    print(f"Fetching rates for: {', '.join(wanted)}")
    if missing:
        print(f"Not available in ECB data: {', '.join(missing)}")

    try:
        result = get_rates(wanted)
    except urllib.error.URLError as exc:
        print(f"ERROR: Rate fetch failed — {exc}", file=sys.stderr)
        return 1

    rates = result.get("rates", {})
    date_str = result.get("date", "unknown")

    md = build_markdown(rates, date_str, missing)
    OUTPUT_PATH.write_text(md, encoding="utf-8")
    print(f"Written to {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
