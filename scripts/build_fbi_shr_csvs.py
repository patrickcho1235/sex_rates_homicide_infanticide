#!/usr/bin/env python3
"""Build U.S. homicide and filicide offender-sex CSVs from FBI UCR data.

The broad homicide series comes from the current Crime Data Explorer (CDE)
Expanded Homicide API. The filicide cross-tabulations come from annual FBI
Supplementary Homicide Report (SHR) fixed-width master files because the API
does not expose victim age x relationship x offender sex jointly.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import time
import urllib.parse
import urllib.request
import zipfile
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


CDE_ROOT = "https://cde.ucr.cjis.gov/LATEST"
SIGNED_URL_ENDPOINT = f"{CDE_ROOT}/s3/signedurl"
SHR_API_ENDPOINT = f"{CDE_ROOT}/shr/national"
DOWNLOADS_PAGE = f"{CDE_ROOT}/webapp/#/pages/downloads"
FIRST_AVAILABLE_YEAR = 1985
DEFAULT_LAST_YEAR = 2025
RECORD_LENGTH = 268
MAX_ADDITIONAL_OFFENDERS_IN_LAYOUT = 10

FILICIDE_RELATIONSHIPS = {
    "SO": ("parent", "son"),
    "DA": ("parent", "daughter"),
    "SS": ("stepparent", "stepson"),
    "SD": ("stepparent", "stepdaughter"),
}

STANDARD_AGE_BINS = (
    "under 1 year",
    "1-4 years",
    "5-9 years",
    "10-14 years",
    "15-17 years",
)
DETAILED_AGE_BINS = (
    "0-6 days",
    "7-364 days",
    "1-4 years",
    "5-9 years",
    "10-14 years",
    "15-17 years",
)


@dataclass(frozen=True)
class FilicideRecord:
    year: int
    victim_age_code: str
    victim_age_label: str
    standard_age_bin: str
    detailed_age_bin: str
    offender_sex: str
    raw_offender_sex_code: str
    parent_type: str
    relationship_code: str
    relationship_label: str


def fetch_bytes(url: str, *, attempts: int = 5, timeout: int = 120) -> bytes:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "sex-rates-homicide-infanticide/1.0 (research)"},
    )
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.read()
        except Exception:
            if attempt == attempts - 1:
                raise
            time.sleep(2**attempt)
    raise AssertionError("unreachable")


def fetch_json(url: str, params: dict[str, str]) -> dict:
    encoded = urllib.parse.urlencode(params)
    return json.loads(fetch_bytes(f"{url}?{encoded}").decode("utf-8"))


def master_file_key(year: int) -> str:
    return f"master_files/shr/shr-{year}.zip"


def download_master_file(year: int, raw_dir: Path) -> Path:
    destination = raw_dir / f"shr-{year}.zip"
    if destination.exists() and zipfile.is_zipfile(destination):
        return destination

    key = master_file_key(year)
    signed = fetch_json(SIGNED_URL_ENDPOINT, {"key": key})
    if key not in signed:
        raise RuntimeError(f"FBI did not return a signed URL for {key}")
    payload = fetch_bytes(signed[key], timeout=240)
    if not payload.startswith(b"PK"):
        raise RuntimeError(f"Downloaded payload for {key} is not a ZIP archive")
    temporary = destination.with_suffix(".zip.part")
    temporary.write_bytes(payload)
    temporary.replace(destination)
    return destination


def read_master_lines(archive: Path) -> list[str]:
    with zipfile.ZipFile(archive) as zf:
        file_names = [name for name in zf.namelist() if not name.endswith("/")]
        text_names = [
            name
            for name in file_names
            if name.lower().endswith((".txt", ".dat"))
        ]
        if not text_names and len(file_names) == 1:
            # The official 2002 archive calls its fixed-width file SHR02.02.
            text_names = file_names
        if len(text_names) != 1:
            raise RuntimeError(
                f"Expected one TXT or DAT data file in {archive}; found {text_names}"
            )
        lines = zf.read(text_names[0]).decode("latin-1").splitlines()
        # Legacy DAT archives end with a DOS end-of-file control character.
        lines = [line for line in lines if line.strip("\x1a \t")]
    too_long = [len(line) for line in lines if len(line) > RECORD_LENGTH]
    if too_long:
        raise RuntimeError(
            f"{archive} contains records longer than {RECORD_LENGTH} characters: "
            f"{Counter(too_long)}"
        )
    # Some mid-2000s official files physically omit trailing blank fields.
    # Right-padding restores the documented logical fixed-width layout.
    return [line.ljust(RECORD_LENGTH) for line in lines]


def normalize_offender_sex(raw_code: str) -> str:
    if raw_code == "M":
        return "male"
    if raw_code == "F":
        return "female"
    return "unknown/not specified"


def age_fields(raw_code: str) -> tuple[str, str, str] | None:
    if raw_code == "NB":
        return "0-6 days", "under 1 year", "0-6 days"
    if raw_code == "BB":
        return "7-364 days", "under 1 year", "7-364 days"
    if not raw_code.isdigit() or raw_code == "00":
        return None
    age = int(raw_code)
    if 1 <= age <= 4:
        age_bin = "1-4 years"
    elif 5 <= age <= 9:
        age_bin = "5-9 years"
    elif 10 <= age <= 14:
        age_bin = "10-14 years"
    elif 15 <= age <= 17:
        age_bin = "15-17 years"
    else:
        return None
    return f"{age} years", age_bin, age_bin


def offender_segments(line: str) -> tuple[list[str], int]:
    reported_additional = int(line[95:98])
    represented_additional = min(
        reported_additional, MAX_ADDITIONAL_OFFENDERS_IN_LAYOUT
    )
    segments = [line[80:92]]
    segments.extend(
        line[148 + offset * 12 : 160 + offset * 12]
        for offset in range(represented_additional)
    )
    return segments, max(0, reported_additional - represented_additional)


def parse_master(year: int, lines: Iterable[str]) -> tuple[list[FilicideRecord], dict]:
    filicide_records: list[FilicideRecord] = []
    total_murder_incidents = 0
    total_murder_victims_represented = 0
    justifiable_incidents = 0
    extra_offenders_beyond_layout = 0
    raw_sex_codes: Counter[str] = Counter()

    for line in lines:
        # Position 71: A is murder/nonnegligent manslaughter. B is negligent.
        if line[70] != "A":
            continue
        total_murder_incidents += 1
        total_murder_victims_represented += 1 + int(line[92:95])

        segments, overflow = offender_segments(line)
        extra_offenders_beyond_layout += overflow
        if segments[0][9:11] in {"80", "81"}:
            justifiable_incidents += 1

        age = age_fields(line[75:77])
        if age is None:
            continue
        victim_age_label, standard_age_bin, detailed_age_bin = age

        for segment in segments:
            # SHR circumstance 80/81 denotes justifiable homicide, not murder.
            if segment[9:11] in {"80", "81"}:
                continue
            relationship_code = segment[7:9]
            if relationship_code not in FILICIDE_RELATIONSHIPS:
                continue
            parent_type, relationship_label = FILICIDE_RELATIONSHIPS[
                relationship_code
            ]
            raw_sex = segment[2]
            raw_sex_codes[raw_sex or "<blank>"] += 1
            filicide_records.append(
                FilicideRecord(
                    year=year,
                    victim_age_code=line[75:77],
                    victim_age_label=victim_age_label,
                    standard_age_bin=standard_age_bin,
                    detailed_age_bin=detailed_age_bin,
                    offender_sex=normalize_offender_sex(raw_sex),
                    raw_offender_sex_code=raw_sex or "<blank>",
                    parent_type=parent_type,
                    relationship_code=relationship_code,
                    relationship_label=relationship_label,
                )
            )

    stats = {
        "records_total": sum(1 for _ in lines) if not isinstance(lines, list) else len(lines),
        "murder_or_nonnegligent_incident_records_including_justifiable": total_murder_incidents,
        "victim_slots_in_those_records_including_justifiable": total_murder_victims_represented,
        "incident_records_coded_justifiable": justifiable_incidents,
        "reported_additional_offenders_beyond_fixed_layout": extra_offenders_beyond_layout,
        "qualifying_filicide_offender_records": len(filicide_records),
        "qualifying_filicide_raw_sex_codes": json.dumps(
            dict(sorted(raw_sex_codes.items())), sort_keys=True
        ),
    }
    return filicide_records, stats


def pct(numerator: int, denominator: int) -> str:
    return "" if denominator == 0 else f"{100 * numerator / denominator:.3f}"


def ratio(numerator: int, denominator: int) -> str:
    return "" if denominator == 0 else f"{numerator / denominator:.3f}"


def summarize_sex(records: Iterable[FilicideRecord]) -> dict[str, int | str]:
    counts = Counter(record.offender_sex for record in records)
    male = counts["male"]
    female = counts["female"]
    unknown = counts["unknown/not specified"]
    known = male + female
    total = known + unknown
    return {
        "male_offender_records": male,
        "female_offender_records": female,
        "unknown_or_not_specified_offender_records": unknown,
        "known_sex_offender_records": known,
        "total_offender_records": total,
        "male_percent_known_sex": pct(male, known),
        "female_percent_known_sex": pct(female, known),
        "male_percent_all_records": pct(male, total),
        "female_percent_all_records": pct(female, total),
        "unknown_or_not_specified_percent_all_records": pct(unknown, total),
        "male_to_female_ratio_known_sex": ratio(male, female),
    }


def write_csv(path: Path, rows: list[dict], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        if not rows:
            raise RuntimeError(f"Cannot infer CSV columns for empty output {path}")
        fieldnames = list(rows[0])
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def get_homicide_sex_row(year: int) -> dict:
    response = fetch_json(
        SHR_API_ENDPOINT,
        {"from": f"01-{year}", "to": f"12-{year}", "type": "totals"},
    )
    sex = response["offender"]["sex"]
    male = int(sex.get("Male", 0))
    female = int(sex.get("Female", 0))
    unknown = int(sex.get("Unknown", 0))
    not_specified = int(sex.get("Not Specified", 0))
    other = sum(
        int(value)
        for key, value in sex.items()
        if key not in {"Male", "Female", "Unknown", "Not Specified"}
    )
    known = male + female
    all_records = known + unknown + not_specified + other
    properties = response.get("cde_properties", {})
    return {
        "year": year,
        "male_offender_records": male,
        "female_offender_records": female,
        "unknown_offender_records": unknown,
        "not_specified_offender_records": not_specified,
        "other_offender_records": other,
        "known_sex_offender_records": known,
        "total_offender_records": all_records,
        "male_percent_known_sex": pct(male, known),
        "female_percent_known_sex": pct(female, known),
        "male_percent_all_records": pct(male, all_records),
        "female_percent_all_records": pct(female, all_records),
        "unknown_not_specified_other_percent_all_records": pct(
            unknown + not_specified + other, all_records
        ),
        "male_to_female_ratio_known_sex": ratio(male, female),
        "api_last_refresh_date": properties.get("last_refresh_date", {}).get(
            "UCR", ""
        ),
        "source": "FBI Crime Data Explorer Expanded Homicide API",
        "source_url": SHR_API_ENDPOINT,
    }


def build_homicide_rows(years: list[int], workers: int) -> list[dict]:
    rows: list[dict] = []
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(get_homicide_sex_row, year): year for year in years}
        for future in as_completed(futures):
            year = futures[future]
            rows.append(future.result())
            print(f"Fetched current FBI homicide totals for {year}")
    return sorted(rows, key=lambda row: int(row["year"]))


def tidy_filicide_rows(records: list[FilicideRecord]) -> list[dict]:
    counts: Counter[tuple] = Counter(
        (
            r.year,
            r.victim_age_code,
            r.victim_age_label,
            r.standard_age_bin,
            r.detailed_age_bin,
            r.offender_sex,
            r.raw_offender_sex_code,
            r.parent_type,
            r.relationship_code,
            r.relationship_label,
        )
        for r in records
    )
    rows = []
    for key, count in sorted(counts.items()):
        (
            year,
            victim_age_code,
            victim_age_label,
            standard_age_bin,
            detailed_age_bin,
            offender_sex,
            raw_offender_sex_code,
            parent_type,
            relationship_code,
            relationship_label,
        ) = key
        rows.append(
            {
                "year": year,
                "victim_age_code": victim_age_code,
                "victim_age_label": victim_age_label,
                "standard_age_bin": standard_age_bin,
                "detailed_age_bin": detailed_age_bin,
                "offender_sex": offender_sex,
                "raw_offender_sex_code": raw_offender_sex_code,
                "parent_type": parent_type,
                "relationship_code": relationship_code,
                "relationship_label": relationship_label,
                "offender_record_count": count,
            }
        )
    return rows


def age_summary_rows_by_year(
    records: list[FilicideRecord], years: list[int]
) -> list[dict]:
    rows: list[dict] = []
    for year in years:
        year_records = [record for record in records if record.year == year]
        for order, age_bin in enumerate(STANDARD_AGE_BINS, start=1):
            subset = [r for r in year_records if r.standard_age_bin == age_bin]
            rows.append(
                {
                    "year": year,
                    "age_bin_scheme": "standard_nonoverlap",
                    "age_bin_order": order,
                    "victim_age_bin": age_bin,
                    **summarize_sex(subset),
                }
            )
        rows.append(
            {
                "year": year,
                "age_bin_scheme": "overall",
                "age_bin_order": 1,
                "victim_age_bin": "under 18 years",
                **summarize_sex(year_records),
            }
        )
    return rows


def period_definitions(first_year: int, last_year: int) -> list[tuple[str, int, int]]:
    periods = [("full_available_series", first_year, last_year)]
    if first_year <= 2020:
        periods.append(("pre_2021_transition", first_year, min(2020, last_year)))
    if last_year >= 2021:
        periods.append(("2021_and_later", max(2021, first_year), last_year))
    decade_start = max(first_year, last_year - 9)
    periods.append(("latest_10_data_years", decade_start, last_year))
    # Remove duplicates that can arise with a short custom year range.
    unique: list[tuple[str, int, int]] = []
    seen: set[tuple[int, int]] = set()
    for period in periods:
        span = (period[1], period[2])
        if span[0] <= span[1] and span not in seen:
            unique.append(period)
            seen.add(span)
    return unique


def age_summary_rows_by_period(
    records: list[FilicideRecord], periods: list[tuple[str, int, int]]
) -> list[dict]:
    rows: list[dict] = []
    for period_id, start_year, end_year in periods:
        period_records = [r for r in records if start_year <= r.year <= end_year]
        for scheme, bins in (
            ("detailed_nonoverlap", DETAILED_AGE_BINS),
            ("standard_nonoverlap", STANDARD_AGE_BINS),
        ):
            field = "detailed_age_bin" if scheme.startswith("detailed") else "standard_age_bin"
            for order, age_bin in enumerate(bins, start=1):
                subset = [r for r in period_records if getattr(r, field) == age_bin]
                rows.append(
                    {
                        "period_id": period_id,
                        "start_year": start_year,
                        "end_year": end_year,
                        "age_bin_scheme": scheme,
                        "age_bin_order": order,
                        "victim_age_bin": age_bin,
                        **summarize_sex(subset),
                    }
                )
        rows.append(
            {
                "period_id": period_id,
                "start_year": start_year,
                "end_year": end_year,
                "age_bin_scheme": "overall",
                "age_bin_order": 1,
                "victim_age_bin": "under 18 years",
                **summarize_sex(period_records),
            }
        )
    return rows


def parent_type_period_rows(
    records: list[FilicideRecord], periods: list[tuple[str, int, int]]
) -> list[dict]:
    rows: list[dict] = []
    for period_id, start_year, end_year in periods:
        period_records = [r for r in records if start_year <= r.year <= end_year]
        for parent_type in ("parent", "stepparent"):
            parent_records = [r for r in period_records if r.parent_type == parent_type]
            for order, age_bin in enumerate(STANDARD_AGE_BINS, start=1):
                subset = [r for r in parent_records if r.standard_age_bin == age_bin]
                rows.append(
                    {
                        "period_id": period_id,
                        "start_year": start_year,
                        "end_year": end_year,
                        "parent_type": parent_type,
                        "age_bin_scheme": "standard_nonoverlap",
                        "age_bin_order": order,
                        "victim_age_bin": age_bin,
                        **summarize_sex(subset),
                    }
                )
            rows.append(
                {
                    "period_id": period_id,
                    "start_year": start_year,
                    "end_year": end_year,
                    "parent_type": parent_type,
                    "age_bin_scheme": "overall",
                    "age_bin_order": 1,
                    "victim_age_bin": "under 18 years",
                    **summarize_sex(parent_records),
                }
            )
    return rows


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start-year", type=int, default=FIRST_AVAILABLE_YEAR)
    parser.add_argument("--end-year", type=int, default=DEFAULT_LAST_YEAR)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw/fbi_shr"))
    parser.add_argument("--out-dir", type=Path, default=Path("data/processed"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.start_year < FIRST_AVAILABLE_YEAR or args.end_year < args.start_year:
        raise SystemExit(
            f"Year range must begin at {FIRST_AVAILABLE_YEAR} or later and be ordered"
        )
    years = list(range(args.start_year, args.end_year + 1))
    args.raw_dir.mkdir(parents=True, exist_ok=True)
    args.out_dir.mkdir(parents=True, exist_ok=True)

    archives: dict[int, Path] = {}
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(download_master_file, year, args.raw_dir): year
            for year in years
        }
        for future in as_completed(futures):
            year = futures[future]
            archives[year] = future.result()
            print(f"Ready: FBI SHR master file {year}")

    all_filicide_records: list[FilicideRecord] = []
    source_rows: list[dict] = []
    build_time = datetime.now(timezone.utc).isoformat(timespec="seconds")
    for year in years:
        archive = archives[year]
        lines = read_master_lines(archive)
        records, stats = parse_master(year, lines)
        all_filicide_records.extend(records)
        source_rows.append(
            {
                "year": year,
                "source_name": "FBI Supplementary Homicide Report master file",
                "stable_catalog_key": master_file_key(year),
                "download_catalog_url": DOWNLOADS_PAGE,
                "sha256": sha256(archive),
                "zip_size_bytes": archive.stat().st_size,
                "retrieved_or_verified_utc": build_time,
                **stats,
            }
        )
        print(f"Parsed {year}: {len(records)} qualifying offender records")

    homicide_rows = build_homicide_rows(years, args.workers)
    periods = period_definitions(args.start_year, args.end_year)

    write_csv(
        args.out_dir / "homicide_offender_sex_by_year.csv",
        homicide_rows,
    )
    write_csv(
        args.out_dir / "filicide_offender_sex_counts_tidy.csv",
        tidy_filicide_rows(all_filicide_records),
    )
    write_csv(
        args.out_dir / "filicide_offender_sex_by_age_year.csv",
        age_summary_rows_by_year(all_filicide_records, years),
    )
    write_csv(
        args.out_dir / "filicide_offender_sex_by_age_period.csv",
        age_summary_rows_by_period(all_filicide_records, periods),
    )
    write_csv(
        args.out_dir / "filicide_offender_sex_by_age_parent_type_period.csv",
        parent_type_period_rows(all_filicide_records, periods),
    )
    write_csv(args.out_dir / "source_inventory.csv", source_rows)
    print(f"Wrote CSV outputs to {args.out_dir}")


if __name__ == "__main__":
    main()
