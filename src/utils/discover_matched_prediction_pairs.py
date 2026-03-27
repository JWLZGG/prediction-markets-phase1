from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import pandas as pd
import yaml


POLYMARKET_PATH = Path("data/processed/current_polymarket_features.parquet")
KALSHI_PATH = Path("data/processed/kalshi_current_features.parquet")
OUTPUT_CONFIG_PATH = Path("configs/matched_prediction_markets.yaml")
OUTPUT_REPORT_PATH = Path("reports/matched_pair_candidates.md")


WIN_RE = re.compile(r"^Will (?P<subject>.+?) win (?:the )?(?P<event>.+?)\?$", re.IGNORECASE)
QUALIFY_RE = re.compile(
    r"^Will (?P<subject>.+?) qualify for (?:the )?(?P<event>.+?)\?$",
    re.IGNORECASE,
)
THRESHOLD_RE = re.compile(
    r"^Will (?P<subject>.+?) be (?P<comparator>above|below|between) (?P<event>.+?)\?$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ParsedQuestion:
    family: str
    subject: str
    event: str
    normalized_question: str


@dataclass(frozen=True)
class CandidatePair:
    pair_id: str
    label: str
    confidence: str
    reason: str
    polymarket_market_id: str
    polymarket_question: str
    kalshi_ticker: str
    kalshi_question: str
    side: str = "yes"


def _norm(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9 ]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _slug(text: str) -> str:
    text = _norm(text)
    return re.sub(r"[^a-z0-9]+", "_", text).strip("_")


def _parse_question(question: str) -> ParsedQuestion | None:
    text = question.strip()
    normalized_question = _norm(text)

    for family, regex in (
        ("win", WIN_RE),
        ("qualify", QUALIFY_RE),
        ("threshold", THRESHOLD_RE),
    ):
        match = regex.match(text)
        if not match:
            continue

        groups = match.groupdict()
        subject = _norm(groups.get("subject", ""))
        event_parts = [groups.get("event", "")]
        comparator = groups.get("comparator")
        if comparator:
            event_parts.insert(0, comparator)
        event = _norm(" ".join(event_parts))

        if subject and event:
            return ParsedQuestion(
                family=family,
                subject=subject,
                event=event,
                normalized_question=normalized_question,
            )

    return None


def _load_polymarket_rows(path: Path = POLYMARKET_PATH) -> list[dict[str, Any]]:
    if not path.exists():
        return []

    df = pd.read_parquet(path).copy()
    if "question" not in df.columns or "market_id" not in df.columns:
        return []

    rows: list[dict[str, Any]] = []
    for _, row in df.iterrows():
        question = str(row.get("question", "")).strip()
        market_id = str(row.get("market_id", "")).strip()
        if not question or not market_id:
            continue

        parsed = _parse_question(question)
        if parsed is None:
            continue

        rows.append(
            {
                "market_id": market_id,
                "question": question,
                "parsed": parsed,
            }
        )

    return rows


def _load_kalshi_rows(path: Path = KALSHI_PATH) -> list[dict[str, Any]]:
    if not path.exists():
        return []

    df = pd.read_parquet(path).copy()
    required = {"ticker", "question", "volume_num", "open_interest_num"}
    if not required.issubset(df.columns):
        return []

    df = df[(df["volume_num"].fillna(0) > 0) | (df["open_interest_num"].fillna(0) > 0)].copy()

    rows: list[dict[str, Any]] = []
    for _, row in df.iterrows():
        question = str(row.get("question", "")).strip()
        ticker = str(row.get("ticker", "")).strip()
        if not question or not ticker:
            continue

        parsed = _parse_question(question)
        if parsed is None:
            continue

        rows.append(
            {
                "ticker": ticker,
                "question": question,
                "parsed": parsed,
            }
        )

    return rows


def discover_candidate_pairs() -> tuple[list[CandidatePair], list[CandidatePair]]:
    polymarket_rows = _load_polymarket_rows()
    kalshi_rows = _load_kalshi_rows()

    high_confidence: list[CandidatePair] = []
    manual_review: list[CandidatePair] = []
    seen_keys: set[tuple[str, str]] = set()

    for poly in polymarket_rows:
        p = poly["parsed"]
        for kal in kalshi_rows:
            k = kal["parsed"]
            if p.family != k.family:
                continue

            key = (poly["market_id"], kal["ticker"])
            if key in seen_keys:
                continue

            if p.subject == k.subject and p.event == k.event:
                seen_keys.add(key)
                label = poly["question"]
                high_confidence.append(
                    CandidatePair(
                        pair_id=_slug(label),
                        label=label,
                        confidence="high",
                        reason="exact parsed subject + event match",
                        polymarket_market_id=poly["market_id"],
                        polymarket_question=poly["question"],
                        kalshi_ticker=kal["ticker"],
                        kalshi_question=kal["question"],
                    )
                )
                continue

            same_subject = p.subject == k.subject
            event_overlap = set(p.event.split()) & set(k.event.split())
            if same_subject and len(event_overlap) >= 2:
                seen_keys.add(key)
                label = poly["question"]
                manual_review.append(
                    CandidatePair(
                        pair_id=_slug(label),
                        label=label,
                        confidence="manual_review",
                        reason="same parsed subject with partial event-token overlap",
                        polymarket_market_id=poly["market_id"],
                        polymarket_question=poly["question"],
                        kalshi_ticker=kal["ticker"],
                        kalshi_question=kal["question"],
                    )
                )

    # Deduplicate manual review rows if a high-confidence row already exists.
    high_ids = {(row.polymarket_market_id, row.kalshi_ticker) for row in high_confidence}
    manual_review = [
        row
        for row in manual_review
        if (row.polymarket_market_id, row.kalshi_ticker) not in high_ids
    ]

    high_confidence.sort(key=lambda row: row.label)
    manual_review.sort(key=lambda row: row.label)
    return high_confidence, manual_review


def write_outputs(
    high_confidence: list[CandidatePair],
    manual_review: list[CandidatePair],
    *,
    output_config_path: Path = OUTPUT_CONFIG_PATH,
    output_report_path: Path = OUTPUT_REPORT_PATH,
) -> None:
    config_payload = {
        "pairs": [
            {
                "pair_id": row.pair_id,
                "label": row.label,
                "polymarket": {
                    "market_id": row.polymarket_market_id,
                    "side": row.side,
                },
                "kalshi": {
                    "ticker": row.kalshi_ticker,
                    "side": row.side,
                },
            }
            for row in high_confidence
        ],
        "candidate_pairs_manual_review": [asdict(row) for row in manual_review[:25]],
    }

    output_config_path.parent.mkdir(parents=True, exist_ok=True)
    with output_config_path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(config_payload, f, sort_keys=False, allow_unicode=True)

    lines = [
        "# Matched Prediction Pair Candidates",
        "",
        f"- High-confidence active pairs: {len(high_confidence)}",
        f"- Manual-review candidates: {len(manual_review)}",
        "",
        "## High-confidence pairs",
        "",
    ]

    if not high_confidence:
        lines.append("No high-confidence Polymarket-Kalshi pairs were found from the current local datasets.")
    else:
        lines.extend(
            [
                "| Pair ID | Label | Polymarket market_id | Kalshi ticker | Reason |",
                "|---|---|---|---|---|",
            ]
        )
        for row in high_confidence:
            lines.append(
                f"| {row.pair_id} | {row.label} | {row.polymarket_market_id} | "
                f"{row.kalshi_ticker} | {row.reason} |"
            )

    lines.extend(
        [
            "",
            "## Manual-review candidates",
            "",
        ]
    )
    if not manual_review:
        lines.append("No manual-review candidates cleared the conservative matching heuristics.")
    else:
        lines.extend(
            [
                "| Label | Polymarket question | Kalshi question | Reason |",
                "|---|---|---|---|",
            ]
        )
        for row in manual_review[:25]:
            lines.append(
                f"| {row.label} | {row.polymarket_question} | {row.kalshi_question} | {row.reason} |"
            )

    output_report_path.parent.mkdir(parents=True, exist_ok=True)
    output_report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_discover_matched_prediction_pairs() -> None:
    high_confidence, manual_review = discover_candidate_pairs()
    write_outputs(high_confidence, manual_review)
    print(f"[INFO] High-confidence pairs: {len(high_confidence)}")
    print(f"[INFO] Manual-review candidates: {len(manual_review)}")
    print(f"[INFO] Wrote config: {OUTPUT_CONFIG_PATH}")
    print(f"[INFO] Wrote report: {OUTPUT_REPORT_PATH}")


if __name__ == "__main__":
    run_discover_matched_prediction_pairs()
