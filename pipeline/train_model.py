"""Train & Backtest Olympic Park Hourly Parking & Visitor AI Forecasting Models (v2 Ensemble).

Upgrades over v1:
  - Fuses `concerts_en.csv` (96 real 2025 concerts) & `concerts_kr.csv` (2,502 venue/event records)
    with `linked_2025.csv` (API_CPM_009) to engineer pre-show/post-show audience ramps,
    festival/multi-event flags, and day-level concert intensity features.
  - Adds `Ensemble_RF_HGB` (VotingRegressor combining RandomForest + HistGradientBoosting)
    benchmarked on both 5-Fold Day-Grouped CV and Oct-Dec Chronological Out-of-Time Holdout.
  - Fixes 4-panel `backtest_actual_vs_pred.png` chart (guaranteed 4 distinct real 2025 scenarios).
  - Exports browser-ready `web_model_bundle.json` and `web_events_bundle.json` (concerts,
    lost items, lawn facilities) for 0-KRW client-side execution through 2028.
"""

from __future__ import annotations

import csv
import datetime as dt
import json
import math
import re
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor, VotingRegressor
from sklearn.inspection import permutation_importance
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, r2_score, root_mean_squared_error
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

ROOT_DIR = Path(__file__).resolve().parent.parent
API_DIR = ROOT_DIR / "data" / "api"
RAW_DIR = ROOT_DIR / "data" / "raw_csv"
PROC_DIR = ROOT_DIR / "data" / "processed"
CHART_DIR = ROOT_DIR / "docs" / "charts"

plt.rcParams["font.family"] = ["Malgun Gothic", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

FEATURE_COLS = [
    "hour",
    "hour_sin",
    "hour_cos",
    "month_sin",
    "month_cos",
    "dow",
    "is_weekend",
    "is_holiday",
    "is_fri_or_wknd",
    "temp_c",
    "temp_sq",
    "precip_mm",
    "is_rain",
    "humidity_pct",
    "wind_spd",
    "concert_audience",
    "daily_max_audience",
    "daily_concert_hours",
    "is_concert_day",
    "hours_from_concert_start",
    "ext_concert_count",
    "is_festival_day",
]

# Cross-checked against 15131671_parking_monthly.csv (2025):
# Aug (76,408 cars) & Sep (83,344 cars) were higher than Jul (68,505 cars),
# yet API_CPM_009 dropped by ~75% (mean ~315 vs ~1,250) -> confirmed aggregation scale anomaly.
ANOMALOUS_REGIME_MONTHS = (8, 9)

FESTIVAL_KEYWORDS = ("페스티벌", "festival", "파크뮤직", "민트", "재즈", "서울재즈", "올팍", "gmf", "sjf")


def extract_external_2025_concerts() -> tuple[dict[str, int], set[str]]:
    """Build daily concert count & festival-day flags from concerts_en.csv + concerts_kr.csv."""
    daily_counts: dict[str, int] = {}
    festival_days: set[str] = set()

    en_path = RAW_DIR / "15149169_concerts_en.csv"
    if en_path.exists():
        c_en = pd.read_csv(en_path, encoding="cp949")
        for r in c_en.itertuples():
            d = str(getattr(r, "공연일자", "") or "").strip()[:10]
            title = str(getattr(r, "공연제목", "") or "").lower()
            if d.startswith("2025-"):
                daily_counts[d] = daily_counts.get(d, 0) + 1
                if any(k in title for k in FESTIVAL_KEYWORDS):
                    festival_days.add(d)

    kr_path = API_DIR / "concerts_kr.csv"
    if kr_path.exists():
        c_kr = pd.read_csv(kr_path, encoding="utf-8-sig")
        date_pat = re.compile(r"(2025)[.\-/](\d{1,2})[.\-/](\d{1,2})")
        for r in c_kr.itertuples():
            blob = f"{getattr(r, 'title', '')} {getattr(r, 'description', '')}"
            found = set()
            for y, m, day in date_pat.findall(blob):
                mi, di = int(m), int(day)
                if 1 <= mi <= 12 and 1 <= di <= 31:
                    found.add(f"{y}-{mi:02d}-{di:02d}")
            low_title = str(getattr(r, "title", "") or "").lower()
            is_fest = any(k in low_title for k in FESTIVAL_KEYWORDS)
            for d in found:
                daily_counts[d] = daily_counts.get(d, 0) + 1
                if is_fest:
                    festival_days.add(d)

    return daily_counts, festival_days


def load_and_engineer_features(csv_path: Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path, encoding="utf-8-sig")
    df["dt"] = pd.to_datetime(df["ISSUED_DATE"], errors="coerce")
    df = df.dropna(subset=["dt", "parking_count", "visitor_count"]).copy()
    df = df.sort_values("dt").drop_duplicates(subset=["dt"]).reset_index(drop=True)

    df["date_str"] = df["dt"].dt.strftime("%Y-%m-%d")
    df["hour"] = df["dt"].dt.hour
    df["month"] = df["dt"].dt.month
    df["dow"] = df["dt"].dt.dayofweek
    df["is_weekend"] = (df["dow"] >= 5).astype(int)
    df["is_fri_or_wknd"] = (df["dow"] >= 4).astype(int)
    df["is_holiday"] = pd.to_numeric(df["is_holiday"], errors="coerce").fillna(0).astype(int)

    df["hour_sin"] = np.sin(2 * np.pi * df["hour"] / 24.0)
    df["hour_cos"] = np.cos(2 * np.pi * df["hour"] / 24.0)
    df["month_sin"] = np.sin(2 * np.pi * df["month"] / 12.0)
    df["month_cos"] = np.cos(2 * np.pi * df["month"] / 12.0)

    for col, src in [("temp_c", "temp_c"), ("humidity_pct", "humidity_pct"), ("wind_spd", "wind_dir_or_spd")]:
        s = pd.to_numeric(df[src], errors="coerce")
        df[col] = s.ffill().bfill().fillna(s.median())
    df["temp_sq"] = (df["temp_c"] - 20.0) ** 2  # Comfort optimum around 20C
    df["precip_mm"] = pd.to_numeric(df["precip_mm"], errors="coerce").fillna(0.0)
    df["is_rain"] = (df["precip_mm"] > 0.1).astype(int)

    df["concert_audience"] = pd.to_numeric(df["concert_audience"], errors="coerce").fillna(0.0)
    df["concert_name"] = df["concert_name"].fillna("").astype(str).str.strip()

    daily_max = df.groupby("date_str")["concert_audience"].transform("max")
    daily_c_hrs = df.groupby("date_str")["concert_audience"].transform(lambda s: int((s > 0).sum()))
    df["daily_max_audience"] = daily_max
    df["daily_concert_hours"] = daily_c_hrs
    df["is_concert_day"] = (daily_max > 0).astype(int)

    concert_rows = df[df["concert_audience"] > 0]
    first_concert_hour = concert_rows.groupby("date_str")["hour"].min().to_dict()
    df["concert_start_hour"] = df["date_str"].map(first_concert_hour)
    df["hours_from_concert_start"] = np.where(
        df["concert_start_hour"].notna(),
        df["hour"] - df["concert_start_hour"].fillna(0),
        -99.0,
    )

    ext_counts, ext_fest = extract_external_2025_concerts()
    df["ext_concert_count"] = df["date_str"].map(lambda d: ext_counts.get(d, 0)).astype(float)
    df["is_festival_day"] = [
        1
        if (d in ext_fest or any(k in cn.lower() for k in FESTIVAL_KEYWORDS))
        else 0
        for d, cn in zip(df["date_str"], df["concert_name"])
    ]

    df["parking_count"] = pd.to_numeric(df["parking_count"], errors="coerce")
    df["visitor_count"] = pd.to_numeric(df["visitor_count"], errors="coerce")

    raw_rows = len(df)
    anom_mask = df["month"].isin(ANOMALOUS_REGIME_MONTHS)
    anom_rows = int(anom_mask.sum())
    df_clean = df[~anom_mask].copy().reset_index(drop=True)
    df_clean.attrs["audit"] = {
        "raw_rows_loaded": raw_rows,
        "anomalous_months_excluded": list(ANOMALOUS_REGIME_MONTHS),
        "anomalous_rows_excluded": anom_rows,
        "clean_rows_used": len(df_clean),
        "ext_2025_concert_days_matched": int((df_clean["ext_concert_count"] > 0).groupby(df_clean["date_str"]).any().sum()),
        "findings": [
            {
                "id": "DQ-01",
                "severity": "HIGH",
                "title": "API_CPM_009 JSON 응답 시 CDATA(DESCRIPTION) 필드 null 유실",
                "detail": "Accept: application/json 호출 시 주차대수·방문객·기상 정보가 담긴 DESCRIPTION이 전량 null 반환됨. XML(application/xml) 파서 우회로 7,803건 100% 복원.",
            },
            {
                "id": "DQ-02",
                "severity": "HIGH",
                "title": "API_CPM_009 2025년 8~9월 주차대수 75% 스케일 급감 이상치",
                "detail": "월별주차현황(15131671) 실측은 2025년 8월 76,408대·9월 83,344대로 7월(68,505대)보다 높으나, API_CPM_009의 8~9월 시간평균만 318/313대(정상 1,250대의 25%)로 집계 기준 이탈 확인 -> 학습 전 자동 격리(1,447행).",
            },
            {
                "id": "DQ-03",
                "severity": "MEDIUM",
                "title": "API_CPM_009 2025년 11~12월 시간대 레코드 61~65% 결측",
                "detail": "11월 281건(정상 720건 대비 39%), 12월 257건(정상 744건 대비 35%)만 수록 -> 월말·야간 수집 누락 보완 제언 대상.",
            },
        ],
    }
    return df_clean


def eval_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    y_pred_clip = np.clip(y_pred, 0, None)
    mae = float(mean_absolute_error(y_true, y_pred_clip))
    rmse = float(root_mean_squared_error(y_true, y_pred_clip))
    r2 = float(r2_score(y_true, y_pred_clip))
    mask = y_true >= 50
    mape = float(np.mean(np.abs((y_true[mask] - y_pred_clip[mask]) / y_true[mask])) * 100.0) if mask.any() else 0.0
    return {
        "mae": round(mae, 2),
        "rmse": round(rmse, 2),
        "r2": round(r2, 4),
        "peak_mape_pct": round(mape, 2),
    }


def baseline_predict(train_df: pd.DataFrame, test_df: pd.DataFrame, target: str) -> np.ndarray:
    lut = train_df.groupby(["hour", "is_weekend"])[target].mean().to_dict()
    global_mean = float(train_df[target].mean())
    return np.array(
        [lut.get((int(h), int(w)), global_mean) for h, w in zip(test_df["hour"], test_df["is_weekend"])],
        dtype=float,
    )


def build_models() -> dict[str, Any]:
    rf = RandomForestRegressor(
        n_estimators=260, max_depth=16, min_samples_leaf=4, random_state=42, n_jobs=-1
    )
    hgb = HistGradientBoostingRegressor(
        max_iter=350,
        learning_rate=0.045,
        max_depth=7,
        min_samples_leaf=15,
        l2_regularization=1.5,
        random_state=42,
    )
    ens = VotingRegressor(
        estimators=[
            ("rf", RandomForestRegressor(n_estimators=260, max_depth=16, min_samples_leaf=4, random_state=42, n_jobs=-1)),
            ("hgb", HistGradientBoostingRegressor(max_iter=350, learning_rate=0.045, max_depth=7, min_samples_leaf=15, l2_regularization=1.5, random_state=42)),
        ],
        weights=[0.55, 0.45],
    )
    return {
        "Ridge": make_pipeline(StandardScaler(), Ridge(alpha=10.0)),
        "RandomForest": rf,
        "HistGradientBoosting": hgb,
        "Ensemble_RF_HGB": ens,
    }


def benchmark_target(df: pd.DataFrame, target: str) -> dict[str, Any]:
    X = df[FEATURE_COLS].values
    y = df[target].values
    groups = df["date_str"].values

    train_mask = df["month"] <= 9
    test_mask = df["month"] >= 10
    train_df, test_df = df[train_mask].copy(), df[test_mask].copy()
    X_tr, y_tr = train_df[FEATURE_COLS].values, train_df[target].values
    X_te, y_te = test_df[FEATURE_COLS].values, test_df[target].values

    oot_results: dict[str, Any] = {}
    oot_results["Baseline_HourWeekend"] = eval_metrics(y_te, baseline_predict(train_df, test_df, target))

    best_model_name = "Ensemble_RF_HGB"
    oot_best_pred = None

    for name, model in build_models().items():
        model.fit(X_tr, y_tr)
        pred = np.clip(model.predict(X_te), 0, None)
        oot_results[name] = eval_metrics(y_te, pred)
        if name == best_model_name:
            oot_best_pred = pred

    gkf = GroupKFold(n_splits=5)
    cv_results: dict[str, Any] = {}
    oof_preds: dict[str, np.ndarray] = {}

    b_oof = np.zeros_like(y, dtype=float)
    for tr_idx, va_idx in gkf.split(X, y, groups):
        b_oof[va_idx] = baseline_predict(df.iloc[tr_idx], df.iloc[va_idx], target)
    cv_results["Baseline_HourWeekend"] = eval_metrics(y, b_oof)

    for name, model in build_models().items():
        oof = np.zeros_like(y, dtype=float)
        for tr_idx, va_idx in gkf.split(X, y, groups):
            model.fit(X[tr_idx], y[tr_idx])
            oof[va_idx] = np.clip(model.predict(X[va_idx]), 0, None)
        cv_results[name] = eval_metrics(y, oof)
        oof_preds[name] = oof

    final_model = build_models()[best_model_name]
    final_model.fit(X, y)

    oot_model = build_models()[best_model_name]
    oot_model.fit(X_tr, y_tr)
    perm = permutation_importance(oot_model, X_te, y_te, n_repeats=10, random_state=42, scoring="r2")
    imp_list = sorted(
        [
            {"feature": f, "importance_r2": round(float(m), 4), "std": round(float(s), 4)}
            for f, m, s in zip(FEATURE_COLS, perm.importances_mean, perm.importances_std)
        ],
        key=lambda x: -x["importance_r2"],
    )

    return {
        "target": target,
        "train_rows": int(train_mask.sum()),
        "test_rows": int(test_mask.sum()),
        "oot_oct_dec_metrics": oot_results,
        "cv_5fold_day_grouped_metrics": cv_results,
        "feature_importance": imp_list,
        "final_model": final_model,
        "oot_best_pred": oot_best_pred,
        "oof_best_pred": oof_preds[best_model_name],
    }


def export_browser_prediction_grid(parking_model: Any, visitor_model: Any) -> dict[str, Any]:
    seasons = {
        "spring": {"month": 5, "temp_clear": 21.0, "temp_rain": 17.0, "hum_clear": 55.0, "hum_rain": 85.0},
        "summer": {"month": 7, "temp_clear": 29.0, "temp_rain": 25.0, "hum_clear": 68.0, "hum_rain": 90.0},
        "autumn": {"month": 10, "temp_clear": 18.0, "temp_rain": 14.0, "hum_clear": 55.0, "hum_rain": 85.0},
        "winter": {"month": 1, "temp_clear": 2.0, "temp_rain": 0.0, "hum_clear": 48.0, "hum_rain": 80.0},
    }
    day_types = {
        "weekday": {"dow": 2, "is_weekend": 0, "is_holiday": 0, "is_fri_or_wknd": 0},
        "weekend": {"dow": 5, "is_weekend": 1, "is_holiday": 0, "is_fri_or_wknd": 1},
        "holiday": {"dow": 5, "is_weekend": 1, "is_holiday": 1, "is_fri_or_wknd": 1},
    }
    concert_tiers = {
        "none": 0,
        "small_3k": 3000,
        "medium_8k": 8000,
        "large_15k": 15000,
        "mega_25k": 25000,
    }
    weathers = {
        "clear": {"precip_mm": 0.0, "is_rain": 0, "wind_spd": 2.0},
        "rain": {"precip_mm": 5.0, "is_rain": 1, "wind_spd": 4.2},
    }

    rows = []
    meta = []
    for s_key, s_cfg in seasons.items():
        m = s_cfg["month"]
        m_sin, m_cos = math.sin(2 * math.pi * m / 12.0), math.cos(2 * math.pi * m / 12.0)
        for d_key, d_cfg in day_types.items():
            for c_key, aud in concert_tiers.items():
                is_c = 1 if aud > 0 else 0
                c_hrs = 4 if is_c else 0
                ext_cnt = 1 if is_c else 0
                is_fest = 1 if aud >= 20000 else 0
                for w_key, w_cfg in weathers.items():
                    temp = s_cfg["temp_rain"] if w_key == "rain" else s_cfg["temp_clear"]
                    hum = s_cfg["hum_rain"] if w_key == "rain" else s_cfg["hum_clear"]
                    temp_sq = (temp - 20.0) ** 2
                    for h in range(24):
                        c_aud_h = aud if (is_c and 17 <= h <= 20) else 0
                        h_from = float(h - 17) if is_c else -99.0
                        rows.append(
                            [
                                h,
                                math.sin(2 * math.pi * h / 24.0),
                                math.cos(2 * math.pi * h / 24.0),
                                m_sin,
                                m_cos,
                                d_cfg["dow"],
                                d_cfg["is_weekend"],
                                d_cfg["is_holiday"],
                                d_cfg["is_fri_or_wknd"],
                                temp,
                                temp_sq,
                                w_cfg["precip_mm"],
                                w_cfg["is_rain"],
                                hum,
                                w_cfg["wind_spd"],
                                c_aud_h,
                                aud,
                                c_hrs,
                                is_c,
                                h_from,
                                ext_cnt,
                                is_fest,
                            ]
                        )
                        meta.append((s_key, d_key, c_key, w_key, h))

    X_grid = np.array(rows, dtype=float)
    p_pred = np.clip(parking_model.predict(X_grid), 0, None)
    v_pred = np.clip(visitor_model.predict(X_grid), 0, None)

    grid: dict[str, dict[str, list[int]]] = {}
    for (s_key, d_key, c_key, w_key, h), pp, vp in zip(meta, p_pred, v_pred):
        k = f"{s_key}|{d_key}|{c_key}|{w_key}"
        if k not in grid:
            grid[k] = {"parking": [0] * 24, "visitors": [0] * 24}
        grid[k]["parking"][h] = int(round(pp))
        grid[k]["visitors"][h] = int(round(vp))

    return {
        "schema_key": "season|day_type|concert_tier|weather",
        "model_used": "Ensemble_RF_HGB",
        "seasons": list(seasons.keys()),
        "day_types": list(day_types.keys()),
        "concert_tiers": concert_tiers,
        "weathers": list(weathers.keys()),
        "curves": grid,
    }


def extract_backtest_cases(df: pd.DataFrame, oof_parking: np.ndarray, oof_visitors: np.ndarray) -> dict[str, Any]:
    work = df.copy()
    work["pred_parking"] = np.clip(oof_parking, 0, None)
    work["pred_visitors"] = np.clip(oof_visitors, 0, None)

    day_stats = (
        work.groupby("date_str")
        .agg(
            hours=("hour", "count"),
            max_aud=("concert_audience", "max"),
            max_park=("parking_count", "max"),
            sum_rain=("precip_mm", "sum"),
            is_weekend=("is_weekend", "max"),
            month=("month", "first"),
            concert_name=("concert_name", lambda s: next((x for x in s if x), "")),
        )
        .reset_index()
    )
    full_days = day_stats[day_stats["hours"] >= 20].copy()

    used: set[str] = set()
    selected_days: list[tuple[str, str, str]] = []

    def pick(cid: str, label: str, subset: pd.DataFrame, sort_col: str, asc: bool = False) -> None:
        cand = subset[~subset["date_str"].isin(used)]
        if len(cand) > 0:
            row = cand.sort_values(sort_col, ascending=asc).iloc[0]
            used.add(row["date_str"])
            selected_days.append((cid, label, row["date_str"]))

    # 1. Mega concert day (peak audience)
    pick("mega_concert", "대형 공연 피크일", full_days[full_days["max_aud"] >= 15000], "max_aud", False)
    # 2. Rainy concert day
    pick("rainy_concert", "우천 공연일", full_days[(full_days["max_aud"] >= 3000) & (full_days["sum_rain"] >= 2.0)], "max_park", False)
    # 3. Spring/Autumn peak picnic weekend (no or minimal concert)
    spring_wknd = full_days[(full_days["is_weekend"] == 1) & (full_days["month"].isin([4, 5, 10]))]
    no_c_wknd = spring_wknd[spring_wknd["max_aud"] == 0]
    if len(no_c_wknd) > 0:
        pick("picnic_weekend", "성수기 비공연 주말", no_c_wknd, "max_park", False)
    else:
        pick("picnic_weekend", "성수기 주말 피크", spring_wknd, "max_park", False)
    # 4. Typical weekday (median traffic, no concert)
    wkdy = full_days[(full_days["max_aud"] == 0) & (full_days["is_weekend"] == 0)]
    if len(wkdy) > 0:
        med_p = wkdy["max_park"].median()
        wkdy = wkdy.assign(diff=(wkdy["max_park"] - med_p).abs())
        pick("normal_weekday", "평일 표준 기준일", wkdy, "diff", True)

    cases = []
    for cid, label, d_str in selected_days:
        sub = work[work["date_str"] == d_str].sort_values("hour")
        cname = next((x for x in sub["concert_name"] if x), "공연 없음")
        cases.append(
            {
                "id": cid,
                "label": label,
                "date": d_str,
                "concert_name": cname,
                "max_audience": int(sub["concert_audience"].max()),
                "total_precip_mm": round(float(sub["precip_mm"].sum()), 1),
                "day_mae": round(float(mean_absolute_error(sub["parking_count"], sub["pred_parking"])), 1),
                "series": [
                    {
                        "hour": int(r.hour),
                        "actual_parking": int(round(r.parking_count)),
                        "pred_parking": int(round(r.pred_parking)),
                        "actual_visitors": int(round(r.visitor_count)),
                        "pred_visitors": int(round(r.pred_visitors)),
                        "temp_c": round(float(r.temp_c), 1),
                        "precip_mm": round(float(r.precip_mm), 1),
                    }
                    for r in sub.itertuples()
                ],
            }
        )

    top_concerts = (
        day_stats[day_stats["max_aud"] > 0]
        .sort_values("max_aud", ascending=False)
        .head(15)
        .to_dict(orient="records")
    )
    for tc in top_concerts:
        tc["max_aud"] = int(tc["max_aud"])
        tc["max_park"] = int(tc["max_park"])
        tc["sum_rain"] = round(float(tc["sum_rain"]), 1)

    monthly_err = []
    for m, grp in work.groupby("month"):
        monthly_err.append(
            {
                "month": int(m),
                "rows": int(len(grp)),
                "avg_actual": round(float(grp["parking_count"].mean()), 1),
                "avg_pred": round(float(grp["pred_parking"].mean()), 1),
                "mae": round(float(mean_absolute_error(grp["parking_count"], grp["pred_parking"])), 1),
                "r2": round(float(r2_score(grp["parking_count"], grp["pred_parking"])), 3),
            }
        )

    return {"sample_days": cases, "top_2025_concerts": top_concerts, "monthly_backtest": monthly_err}


def export_web_events_bundle() -> Path:
    """Export compact concerts (2026 EN posters), lawn facilities, and recent lost items for the Web MVP."""
    concerts_2026 = []
    en_path = RAW_DIR / "15149169_concerts_en.csv"
    if en_path.exists():
        c_en = pd.read_csv(en_path, encoding="cp949")
        sub = c_en[c_en["공연일자"].astype(str) >= "2026-01-01"].sort_values("공연일자", ascending=False).head(24)
        for r in sub.itertuples():
            concerts_2026.append(
                {
                    "id": str(getattr(r, "일련번호", "")),
                    "title": str(getattr(r, "공연제목", "")).strip(),
                    "date": str(getattr(r, "공연일자", "")).strip(),
                    "views": int(getattr(r, "조회수", 0) or 0),
                    "poster": str(getattr(r, "공연이미지", "")).strip(),
                    "url": str(getattr(r, "상세주소", "")).strip(),
                }
            )

    lawns = []
    lawn_path = RAW_DIR / "15143220_lawn_facilities.csv"
    if lawn_path.exists():
        with lawn_path.open("r", encoding="cp949", newline="") as f:
            for row in csv.DictReader(f):
                lawns.append(
                    {
                        "name": row.get("장소", "").strip(),
                        "hours": row.get("개방내용", "").strip(),
                        "url": row.get("링크", "").strip(),
                    }
                )

    lost_items = []
    lost_path = API_DIR / "lost_items.csv"
    if lost_path.exists():
        l_df = pd.read_csv(lost_path, encoding="utf-8-sig")
        l_df = l_df.sort_values("regDate", ascending=False).head(60)
        for r in l_df.itertuples():
            lost_items.append(
                {
                    "title": str(getattr(r, "title", "") or "").strip(),
                    "place": str(getattr(r, "spatialCoverage", "") or getattr(r, "description", "") or "올림픽공원").strip()[:40],
                    "date": str(getattr(r, "regDate", "") or "")[:10],
                }
            )

    payload = {
        "generated_at": dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).isoformat(),
        "concerts_2026_en": concerts_2026,
        "lawn_facilities": lawns,
        "recent_lost_items": lost_items,
    }
    out_path = PROC_DIR / "web_events_bundle.json"
    out_path.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return out_path


def generate_charts(p_res: dict[str, Any], backtest_cases: dict[str, Any], eda_summary: dict[str, Any]) -> list[str]:
    CHART_DIR.mkdir(parents=True, exist_ok=True)
    saved = []

    days = backtest_cases["sample_days"][:4]
    if days:
        fig, axes = plt.subplots(2, 2, figsize=(12.5, 7.8), dpi=160)
        for ax, case in zip(axes.flat, days):
            hrs = [s["hour"] for s in case["series"]]
            act = [s["actual_parking"] for s in case["series"]]
            prd = [s["pred_parking"] for s in case["series"]]
            ax.plot(hrs, act, label="실측 주차대수", color="#0f172a", linewidth=2.2, marker="o", markersize=3.5)
            ax.plot(hrs, prd, label="AI 앙상블 예측 (RF+HGB)", color="#2563eb", linewidth=2.1, linestyle="--")
            ax.fill_between(hrs, act, prd, alpha=0.13, color="#3b82f6")
            ax.set_title(
                f"{case['label']} ({case['date']}) | 관객 {case['max_audience']:,}명 | MAE {case['day_mae']}대",
                fontsize=9.5,
                fontweight="bold",
            )
            ax.set_xlabel("시각 (시)")
            ax.set_ylabel("시간당 주차대수 (대)")
            ax.grid(alpha=0.25)
            ax.legend(fontsize=8)
        fig.suptitle("2025 올림픽공원 시간대별 주차대수 실측 vs RF+HGB 앙상블 AI 백테스트 (4대 시나리오)", fontsize=13, fontweight="bold")
        fig.tight_layout(rect=[0, 0, 1, 0.96])
        p1 = CHART_DIR / "backtest_actual_vs_pred.png"
        fig.savefig(p1)
        plt.close(fig)
        saved.append(str(p1))

    top_imp = p_res["feature_importance"][:10][::-1]
    fig, ax = plt.subplots(figsize=(8.8, 4.8), dpi=160)
    ax.barh([x["feature"] for x in top_imp], [x["importance_r2"] for x in top_imp], color="#2563eb")
    ax.set_xlabel("Permutation Importance (R² 감소량)")
    ax.set_title("주차 혼잡 예측 앙상블 AI 주요 변수 중요도 (Oct-Dec 2025 OOT 검증)", fontweight="bold")
    ax.grid(axis="x", alpha=0.25)
    fig.tight_layout()
    p2 = CHART_DIR / "feature_importance.png"
    fig.savefig(p2)
    plt.close(fig)
    saved.append(str(p2))

    zones = eda_summary.get("parking_congestion_15164156", {}).get("zones_ranked", [])
    if zones:
        fig, ax = plt.subplots(figsize=(9.5, 4.8), dpi=160)
        z_names = [z["zone"] for z in zones]
        full_r = [z["full_rate_pct"] for z in zones]
        cong_r = [z["busy_or_full_pct"] - z["full_rate_pct"] for z in zones]
        ax.bar(z_names, full_r, label="만차 (%)", color="#dc2626")
        ax.bar(z_names, cong_r, bottom=full_r, label="혼잡 (%)", color="#f59e0b")
        ax.axhline(71.8, color="#334155", linestyle="--", linewidth=1.2, label="전체 평균 (71.8%)")
        ax.set_ylabel("비율 (%)")
        ax.set_title("올림픽공원 11개 주차구역(P1A~P11) 만차·혼잡 공간 편중 실측 (2025~2026)", fontweight="bold")
        ax.legend()
        ax.grid(axis="y", alpha=0.25)
        fig.tight_layout()
        p3 = CHART_DIR / "zone_congestion_asymmetry.png"
        fig.savefig(p3)
        plt.close(fig)
        saved.append(str(p3))

    return saved


def main() -> int:
    csv_path = API_DIR / "linked_2025.csv"
    df = load_and_engineer_features(csv_path)
    print(f"[DATA] Clean rows={len(df):,} ({df['date_str'].nunique()} days) | ext_concert_days={df.attrs['audit']['ext_2025_concert_days_matched']}")

    p_res = benchmark_target(df, "parking_count")
    v_res = benchmark_target(df, "visitor_count")

    print("\n=== BENCHMARK: PARKING_COUNT (Oct-Dec 2025 OOT Holdout) ===")
    for m, met in p_res["oot_oct_dec_metrics"].items():
        print(f"  {m:22s}: MAE={met['mae']:6.2f} | RMSE={met['rmse']:6.2f} | R²={met['r2']:.4f}")

    print("\n=== BENCHMARK: PARKING_COUNT (5-Fold Day-Grouped CV) ===")
    for m, met in p_res["cv_5fold_day_grouped_metrics"].items():
        print(f"  {m:22s}: MAE={met['mae']:6.2f} | RMSE={met['rmse']:6.2f} | R²={met['r2']:.4f} | PeakMAPE={met['peak_mape_pct']:.1f}%")

    print("\n=== BENCHMARK: VISITOR_COUNT (5-Fold Day-Grouped CV) ===")
    for m, met in v_res["cv_5fold_day_grouped_metrics"].items():
        print(f"  {m:22s}: MAE={met['mae']:6.2f} | RMSE={met['rmse']:6.2f} | R²={met['r2']:.4f}")

    eda_path = PROC_DIR / "eda_summary.json"
    eda_summary = json.loads(eda_path.read_text(encoding="utf-8")) if eda_path.exists() else {}

    grid = export_browser_prediction_grid(p_res["final_model"], v_res["final_model"])
    backtest_cases = extract_backtest_cases(df, p_res["oof_best_pred"], v_res["oof_best_pred"])
    charts = generate_charts(p_res, backtest_cases, eda_summary)
    events_path = export_web_events_bundle()

    bundle = {
        "generated_at": dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).isoformat(),
        "data_quality_audit": df.attrs.get("audit", {}),
        "dataset_stats": {
            "source": "API_CPM_009 + 15164156 + 15138735 + 15131671 + 15149169 + KSCperf",
            "rows": int(len(df)),
            "unique_days": int(df["date_str"].nunique()),
            "date_range": [df["date_str"].min(), df["date_str"].max()],
            "concert_days": int(df[df["is_concert_day"] == 1]["date_str"].nunique()),
            "max_parking_hourly": int(df["parking_count"].max()),
            "max_visitors_hourly": int(df["visitor_count"].max()),
            "max_concert_audience": int(df["concert_audience"].max()),
        },
        "benchmarks": {
            "parking_count": {
                "train_rows": p_res["train_rows"],
                "test_rows": p_res["test_rows"],
                "oot_oct_dec": p_res["oot_oct_dec_metrics"],
                "cv_5fold_day_grouped": p_res["cv_5fold_day_grouped_metrics"],
                "feature_importance": p_res["feature_importance"],
            },
            "visitor_count": {
                "train_rows": v_res["train_rows"],
                "test_rows": v_res["test_rows"],
                "oot_oct_dec": v_res["oot_oct_dec_metrics"],
                "cv_5fold_day_grouped": v_res["cv_5fold_day_grouped_metrics"],
                "feature_importance": v_res["feature_importance"],
            },
        },
        "backtest": backtest_cases,
        "prediction_grid": grid,
        "zones_11_empirical": eda_summary.get("parking_congestion_15164156", {}).get("zones_ranked", []),
        "monthly_seasonality": eda_summary.get("parking_monthly_15131671", {}),
        "esg_baseline": eda_summary.get("parking_inout_202407_15138735", {}).get("esg_peak_evening_baseline", {}),
        "charts": charts,
    }

    PROC_DIR.mkdir(parents=True, exist_ok=True)
    out_path = PROC_DIR / "web_model_bundle.json"
    out_path.write_text(json.dumps(bundle, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"\n[SAVED] {out_path} ({out_path.stat().st_size/1024:.1f} KB) | {events_path.name} ({events_path.stat().st_size/1024:.1f} KB) | sample_days={len(backtest_cases['sample_days'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
