"""CSV EDA & Baseline Metrics Extractor for KSPO&CO 2026 Contest.

Analyzes already-downloaded raw CSV datasets (zero external packages required):
  1. 15164156_parking_congestion.csv  (699 rows, 11 zones P1A~P11, 2025-02~2026-08)
  2. 15138735_parking_inout_202407.csv (215,528 rows, minute-level entry/exit, 2024-07)
  3. 15131671_parking_monthly.csv      (72 rows, 2023~2025 monthly totals)
  4. 15149169_concerts_en.csv          (286 rows, English concert records up to 2026-10)
  5. 15143220_lawn_facilities.csv      (8 rows, Olympic Park lawn opening info)

Outputs:
  - data/processed/eda_summary.json  (structured JSON ready for Web Dashboard & Report)
"""

from __future__ import annotations

import csv
import datetime as dt
import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT_DIR / "data" / "raw_csv"
OUT_DIR = ROOT_DIR / "data" / "processed"

# Ministry of Environment (Korea) standard passenger-car idling CO2 factor:
# Gasoline/diesel average ~21 g CO2/min (~1.26 kg CO2/hour) during congestion queueing
IDLING_CO2_KG_PER_MIN = 0.021


def read_csv_cp949(filename: str) -> list[dict[str, str]]:
    path = RAW_DIR / filename
    for enc in ("cp949", "utf-8-sig", "euc-kr", "utf-8"):
        try:
            with path.open("r", encoding=enc, newline="") as f:
                return list(csv.DictReader(f))
        except UnicodeDecodeError:
            continue
    raise ValueError(f"Could not decode {path}")


def analyze_congestion() -> dict[str, Any]:
    rows = read_csv_cp949("15164156_parking_congestion.csv")
    zone_counts: dict[str, Counter[str]] = defaultdict(Counter)
    hour_counts: dict[int, Counter[str]] = defaultdict(Counter)
    overall = Counter()
    dates = set()

    for r in rows:
        z = r["주차구역"].strip()
        lvl = r["혼잡도"].strip()
        d = r["등록일"].strip()
        t = r["등록시간"].strip()
        dates.add(d)
        zone_counts[z][lvl] += 1
        overall[lvl] += 1
        if ":" in t:
            h = int(t.split(":")[0])
            hour_counts[h][lvl] += 1

    zone_summary = []
    for z, c in zone_counts.items():
        tot = sum(c.values())
        full_rate = round(c["만차"] / tot * 100, 1)
        busy_rate = round((c["만차"] + c["혼잡"]) / tot * 100, 1)
        zone_summary.append(
            {
                "zone": z,
                "total": tot,
                "full": c["만차"],
                "congested": c["혼잡"],
                "smooth": c["원활"],
                "full_rate_pct": full_rate,
                "busy_or_full_pct": busy_rate,
            }
        )
    zone_summary.sort(key=lambda x: (-x["full_rate_pct"], -x["busy_or_full_pct"]))

    hourly_summary = []
    for h in sorted(hour_counts.keys()):
        c = hour_counts[h]
        tot = sum(c.values())
        hourly_summary.append(
            {
                "hour": h,
                "total": tot,
                "full": c["만차"],
                "congested": c["혼잡"],
                "smooth": c["원활"],
                "busy_or_full_pct": round((c["만차"] + c["혼잡"]) / tot * 100, 1),
            }
        )

    return {
        "rows": len(rows),
        "unique_days": len(dates),
        "date_range": [min(dates), max(dates)],
        "overall_levels": dict(overall),
        "overall_busy_or_full_pct": round((overall["만차"] + overall["혼잡"]) / len(rows) * 100, 1),
        "zones_ranked": zone_summary,
        "by_hour": hourly_summary,
    }


def analyze_inout_202407() -> dict[str, Any]:
    rows = read_csv_cp949("15138735_parking_inout_202407.csv")
    daily_entries: Counter[str] = Counter()
    dwell_minutes: list[float] = []
    # Hourly entry/exit & simultaneous occupancy per day
    day_hour_in: dict[str, list[int]] = defaultdict(lambda: [0] * 24)
    day_hour_out: dict[str, list[int]] = defaultdict(lambda: [0] * 24)
    day_hour_occ: dict[str, list[int]] = defaultdict(lambda: [0] * 24)
    invalid_ts = 0

    for r in rows:
        d_str = r["입차일"].strip()
        in_str = r["입차일시"].strip()
        out_str = r["출차일시"].strip()
        try:
            t_in = dt.datetime.strptime(in_str, "%Y-%m-%d %H:%M")
            t_out = dt.datetime.strptime(out_str, "%Y-%m-%d %H:%M")
        except ValueError:
            invalid_ts += 1
            continue

        dur = (t_out - t_in).total_seconds() / 60.0
        if 0 <= dur <= 1440:
            dwell_minutes.append(dur)

        daily_entries[d_str] += 1
        day_hour_in[d_str][t_in.hour] += 1
        if t_out.strftime("%Y-%m-%d") == d_str:
            day_hour_out[d_str][t_out.hour] += 1

        # Approximate simultaneous occupancy on entry date across hours [t_in.hour .. end_h]
        end_h = t_out.hour if t_out.date() == t_in.date() else 23
        for h in range(t_in.hour, min(end_h, 23) + 1):
            day_hour_occ[d_str][h] += 1

    # Classify days: Peak Event-like days (top 5 by entries) vs Weekend vs Normal Weekday
    sorted_days = sorted(daily_entries.items(), key=lambda x: -x[1])
    top5_days = {d for d, _ in sorted_days[:5]}

    groups: dict[str, list[str]] = {"peak_top5": [], "weekend": [], "weekday": []}
    for d_str in sorted(daily_entries.keys()):
        wd = dt.datetime.strptime(d_str, "%Y-%m-%d").weekday()
        if d_str in top5_days:
            groups["peak_top5"].append(d_str)
        elif wd >= 5:
            groups["weekend"].append(d_str)
        else:
            groups["weekday"].append(d_str)

    hourly_profiles: dict[str, list[dict[str, Any]]] = {}
    for gname, dlist in groups.items():
        if not dlist:
            continue
        prof = []
        for h in range(24):
            prof.append(
                {
                    "hour": h,
                    "avg_in": round(sum(day_hour_in[d][h] for d in dlist) / len(dlist), 1),
                    "avg_out": round(sum(day_hour_out[d][h] for d in dlist) / len(dlist), 1),
                    "avg_occ": round(sum(day_hour_occ[d][h] for d in dlist) / len(dlist), 1),
                }
            )
        hourly_profiles[gname] = prof

    dwell_sorted = sorted(dwell_minutes)
    p90_dwell = dwell_sorted[int(len(dwell_sorted) * 0.90)] if dwell_sorted else 0.0

    # Peak exit surge calculation (19:00~22:00 on peak days)
    peak_evening_exits = round(
        sum(hourly_profiles["peak_top5"][h]["avg_out"] for h in (19, 20, 21, 22)), 1
    )
    # Example ESG baseline: if 15 min avg queueing delay affects 40% of peak evening exits
    est_queue_cars = round(peak_evening_exits * 0.4)
    est_idling_co2_kg_per_event = round(est_queue_cars * 15 * IDLING_CO2_KG_PER_MIN, 1)

    return {
        "rows": len(rows),
        "invalid_timestamps": invalid_ts,
        "days_count": len(daily_entries),
        "daily_avg": round(statistics.mean(daily_entries.values()), 1),
        "top5_peak_days": [
            {
                "date": d,
                "weekday": dt.datetime.strptime(d, "%Y-%m-%d").strftime("%a"),
                "entries": cnt,
                "max_hourly_occ": max(day_hour_occ[d]),
                "peak_occ_hour": day_hour_occ[d].index(max(day_hour_occ[d])),
            }
            for d, cnt in sorted_days[:5]
        ],
        "bottom3_days": [{"date": d, "entries": cnt} for d, cnt in sorted_days[-3:]],
        "dwell_minutes": {
            "mean": round(statistics.mean(dwell_minutes), 1),
            "median": round(statistics.median(dwell_minutes), 1),
            "p90": round(p90_dwell, 1),
        },
        "hourly_profiles": hourly_profiles,
        "esg_peak_evening_baseline": {
            "avg_exits_19_22_on_peak_day": peak_evening_exits,
            "assumed_queued_vehicles_40pct": est_queue_cars,
            "assumed_avg_queue_min": 15,
            "co2_kg_per_min_factor": IDLING_CO2_KG_PER_MIN,
            "est_idling_co2_kg_per_peak_evening": est_idling_co2_kg_per_event,
        },
    }


def analyze_monthly_parking() -> dict[str, Any]:
    rows = read_csv_cp949("15131671_parking_monthly.csv")
    by_place_year: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    olympic_by_month: dict[str, list[int]] = defaultdict(list)

    for r in rows:
        yr = r["연도"].strip()
        mo = r["월"].strip()
        place = r["주차장소"].strip()
        cnt = int(r["주차대수"].replace(",", "").strip())
        by_place_year[place][yr] += cnt
        if place == "올림픽공원":
            olympic_by_month[mo].append(cnt)

    seasonality = [
        {"month": mo, "avg_vehicles": round(statistics.mean(vals))}
        for mo, vals in sorted(olympic_by_month.items())
    ]
    return {
        "rows": len(rows),
        "annual_totals": {p: dict(sorted(y.items())) for p, y in by_place_year.items()},
        "olympic_monthly_seasonality": seasonality,
    }


def analyze_concerts_en() -> dict[str, Any]:
    rows = read_csv_cp949("15149169_concerts_en.csv")
    by_year = Counter()
    with_poster = 0
    recent = []
    for r in rows:
        d = r["공연일자"].strip()
        if len(d) >= 4:
            by_year[d[:4]] += 1
        if r.get("공연이미지", "").strip():
            with_poster += 1
        if d >= "2026-01-01":
            recent.append(
                {
                    "date": d,
                    "title": r["공연제목"].strip(),
                    "views": int(r["조회수"] or 0),
                    "poster": r["공연이미지"].strip(),
                    "detail_url": r["상세주소"].strip(),
                }
            )
    recent.sort(key=lambda x: x["date"], reverse=True)
    return {
        "rows": len(rows),
        "by_year": dict(sorted(by_year.items())),
        "with_poster_count": with_poster,
        "recent_2026_count": len(recent),
        "latest_5": recent[:5],
    }


def main() -> int:
    summary = {
        "generated_at": dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).isoformat(),
        "parking_congestion_15164156": analyze_congestion(),
        "parking_inout_202407_15138735": analyze_inout_202407(),
        "parking_monthly_15131671": analyze_monthly_parking(),
        "concerts_en_15149169": analyze_concerts_en(),
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / "eda_summary.json"
    out_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    # Print crisp terminal report
    cg = summary["parking_congestion_15164156"]
    io = summary["parking_inout_202407_15138735"]
    mo = summary["parking_monthly_15131671"]
    en = summary["concerts_en_15149169"]

    print("=== 1. 주차장 혼잡도 (15164156, 11개 구역) ===")
    print(f"  기간: {cg['date_range'][0]} ~ {cg['date_range'][1]} ({cg['unique_days']}일, {cg['rows']}건) | 혼잡+만차 비율: {cg['overall_busy_or_full_pct']}%")
    print("  [만차율 Top 4 병목 구역]")
    for z in cg["zones_ranked"][:4]:
        print(f"    - {z['zone']:3s}: 만차 {z['full_rate_pct']:5.1f}% | 혼잡+만차 {z['busy_or_full_pct']:5.1f}% (n={z['total']})")
    print("  [상대적 여유 분산 후보 Bottom 3 구역]")
    for z in cg["zones_ranked"][-3:]:
        print(f"    - {z['zone']:3s}: 만차 {z['full_rate_pct']:5.1f}% | 혼잡+만차 {z['busy_or_full_pct']:5.1f}% (n={z['total']})")

    print("\n=== 2. 2024.07 입출차 215,528건 정밀 분석 (15138735) ===")
    print(f"  일평균 입차: {io['daily_avg']:,.1f}대 | 체류시간 중앙값: {io['dwell_minutes']['median']}분 (평균 {io['dwell_minutes']['mean']}분, P90 {io['dwell_minutes']['p90']}분)")
    print("  [피크 Top 5일]")
    for d in io["top5_peak_days"]:
        print(f"    - {d['date']} ({d['weekday']}): 입차 {d['entries']:,}대 | 최대 동시주차 {d['max_hourly_occ']:,}대 ({d['peak_occ_hour']:02d}시)")
    esg = io["esg_peak_evening_baseline"]
    print(f"  [피크일 야간(19~22시) 출차 폭주] 평균 {esg['avg_exits_19_22_on_peak_day']:,.1f}대 -> 40%가 15분 공회전 시 약 {esg['est_idling_co2_kg_per_peak_evening']} kg CO2/회")

    print("\n=== 3. 3개년 월별 주차 추이 (15131671) ===")
    print(f"  올림픽공원 연간 주차대수: {mo['annual_totals'].get('올림픽공원')}")
    top_mo = sorted(mo["olympic_monthly_seasonality"], key=lambda x: -x["avg_vehicles"])[:3]
    low_mo = sorted(mo["olympic_monthly_seasonality"], key=lambda x: x["avg_vehicles"])[:2]
    print(f"  성수기 Top 3: {top_mo} | 비수기 Bottom 2: {low_mo}")

    print("\n=== 4. 영문 공연정보 (15149169) ===")
    print(f"  총 {en['rows']}건 (포스터 포함 {en['with_poster_count']}건) | 2026년 등록 공연: {en['recent_2026_count']}건")
    print(f"\n[SAVED] {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
