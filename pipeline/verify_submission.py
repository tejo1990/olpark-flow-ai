"""0-LLM Deterministic Static Verifier (Zone B Gate) for Olpark Flow AI Submission.

Mechanically audits the entire submission package without LLM self-verification:
  Gate 1: SSOT Cross-Numeric Consistency (JSON ground truth <-> 02_기획서.docx text)
  Gate 2: Document Integrity (page budget <=1+10, zero blank pages, >=9 images, 0 leaked placeholders)
  Gate 3: Live Production & Repo Reachability (Cloudflare Pages, Edge API JSON, GitHub HTTP 200)
  Gate 4: Git Secret Hygiene (.env ignored & untracked)

Exit code 0 = ALL PASS; Exit code 1 = FAIL (prints exact mismatched keys).
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path
from typing import Any

import docx
import pypdf

ROOT_DIR = Path(__file__).resolve().parent.parent
DOCS_DIR = ROOT_DIR / "docs"
PROC_DIR = ROOT_DIR / "data" / "processed"

PROPOSAL_DOCX = DOCS_DIR / "02_기획서_OlparkFlowAI_2026공공데이터경진대회.docx"
PROPOSAL_PDF = DOCS_DIR / "02_기획서_OlparkFlowAI_2026공공데이터경진대회.pdf"
APP_DOCX = DOCS_DIR / "01_참가신청서_및_개인정보동의서_OlparkFlowAI.docx"
BUNDLE_JSON = PROC_DIR / "web_model_bundle.json"
EDA_JSON = PROC_DIR / "eda_summary.json"

LIVE_URL = "https://olpark-flow-ai.pages.dev"
LIVE_API = "https://olpark-flow-ai.pages.dev/api/realtime-parking"
LIVE_BUNDLE = "https://olpark-flow-ai.pages.dev/data/web_model_bundle.json"
GITHUB_URL = "https://github.com/tejo1990/olpark-flow-ai"


def extract_docx_text(path: Path) -> str:
    d = docx.Document(str(path))
    parts = [p.text for p in d.paragraphs]
    for tbl in d.tables:
        for row in tbl.rows:
            for cell in row.cells:
                parts.append(cell.text)
    return "\n".join(parts)


def compute_esg_scenario(bundle: dict[str, Any], stagger: int, transit: int, signage: int) -> dict[str, Any]:
    curve = bundle["prediction_grid"]["curves"]["autumn|weekend|mega_25k|rain"]["parking"]
    esg_base = bundle["esg_baseline"]["avg_exits_19_22_on_peak_day"]
    shift = 1 - transit / 100.0
    alpha = 0.0 if stagger == 0 else (0.22 if stagger == 30 else 0.36)
    after = [
        round((curve[h] * (1 - alpha) + ((curve[max(0, h - 1)] + curve[min(23, h + 1)]) / 2.0) * alpha) * shift)
        for h in range(24)
    ]
    pb, pa = max(curve), max(after)
    drop = round(((pb - pa) / pb) * 1000) / 10.0
    est_exit = round(esg_base * (pb / 2800.0))
    base_q = 22
    red_q = max(3, round(base_q * (1 - (stagger / 120.0) - signage / 160.0)))
    c_before = round(est_exit * 0.45 * base_q * 0.021)
    c_after = round(est_exit * (1 - transit / 100.0) * 0.35 * red_q * 0.021)
    saved = max(0, c_before - c_after)
    ann_t = round((saved * 113) / 1000.0, 1)
    trees = round((saved * 113) / 6.6)
    return {
        "peak_before": pb,
        "peak_after": pa,
        "drop_pct": drop,
        "wait_before": base_q,
        "wait_after": red_q,
        "co2_before": c_before,
        "co2_after": c_after,
        "co2_saved": saved,
        "annual_tco2": ann_t,
        "trees": trees,
    }


def main() -> int:
    failures: list[str] = []
    checks_passed = 0

    def check(cond: bool, label: str, detail: str = "") -> None:
        nonlocal checks_passed
        if cond:
            checks_passed += 1
            print(f"  [PASS] {label}" + (f" ({detail})" if detail else ""))
        else:
            failures.append(f"{label}: {detail}")
            print(f"  [FAIL] {label}" + (f" -> {detail}" if detail else ""))

    bundle = json.loads(BUNDLE_JSON.read_text(encoding="utf-8"))
    eda = json.loads(EDA_JSON.read_text(encoding="utf-8"))
    prop_text = extract_docx_text(PROPOSAL_DOCX)
    app_text = extract_docx_text(APP_DOCX)

    print("=== GATE 1: SSOT Cross-Numeric Consistency (JSON <-> 02_기획서.docx) ===")
    cv_p = bundle["benchmarks"]["parking_count"]["cv_5fold_day_grouped"]
    oot_p = bundle["benchmarks"]["parking_count"]["oot_oct_dec"]
    cv_v = bundle["benchmarks"]["visitor_count"]["cv_5fold_day_grouped"]
    stats = bundle["dataset_stats"]
    audit = bundle["data_quality_audit"]
    esg15 = compute_esg_scenario(bundle, 30, 15, 20)
    esg25 = compute_esg_scenario(bundle, 30, 25, 20)

    expected_tokens = {
        "Ensemble Parking CV MAE": f"{cv_p['Ensemble_RF_HGB']['mae']:.2f}",
        "Ensemble Parking CV RMSE": f"{cv_p['Ensemble_RF_HGB']['rmse']:.2f}",
        "Ensemble Parking CV R2": f"{cv_p['Ensemble_RF_HGB']['r2']:.4f}",
        "Ensemble Parking OOT R2": f"{oot_p['Ensemble_RF_HGB']['r2']:.4f}",
        "Baseline Parking CV MAE": f"{cv_p['Baseline_HourWeekend']['mae']:.2f}",
        "Ensemble Visitor CV R2": f"{cv_v['Ensemble_RF_HGB']['r2']:.4f}",
        "Clean training rows": f"{stats['rows']:,}",
        "Unique days": str(stats["unique_days"]),
        "Concert days": str(stats["concert_days"]),
        "Quarantined Aug-Sep rows": f"{audit['anomalous_rows_excluded']:,}",
        "2025 annual parking": f"{eda['parking_monthly_15131671']['annual_totals']['올림픽공원']['2025']:,}",
        "11-zone busy+full avg": f"{eda['parking_congestion_15164156']['overall_busy_or_full_pct']}%",
        "P11 worst busy+full": f"{eda['parking_congestion_15164156']['zones_ranked'][0]['busy_or_full_pct']}%",
        "P1A best busy+full": f"{eda['parking_congestion_15164156']['zones_ranked'][-1]['busy_or_full_pct']}%",
        "2024.07 inout rows": f"{eda['parking_inout_202407_15138735']['rows']:,}",
        "ESG baseline CO2 (324 kg)": f"{esg15['co2_before']} kg",
        "ESG 15% saved CO2 (188 kg)": f"{esg15['co2_saved']} kg",
        "ESG 15% annual tCO2 (21.2)": f"{esg15['annual_tco2']} tCO₂",
        "ESG 15% pine trees (3,219)": f"{esg15['trees']:,}",
        "ESG 25% saved CO2 (204 kg)": f"{esg25['co2_saved']} kg",
        "ESG 25% annual tCO2 (23.1)": f"{esg25['annual_tco2']} tCO₂",
        "ESG 25% pine trees (3,493)": f"{esg25['trees']:,}",
    }
    for name, tok in expected_tokens.items():
        check(tok in prop_text, f"Metric match: {name}", f"expected '{tok}'")

    # Guard against previously caught stale/hallucinated tokens
    banned_tokens = ["384 kg", "43.4 tCO₂", "TBD", "TODO", "[배포 URL", "[직접 기입", "Lorem ipsum"]
    for btok in banned_tokens:
        check(btok not in prop_text, f"No stale/leaked token in proposal: '{btok}'")

    print("\n=== GATE 2: Document Format, Pagination & Embedded Media ===")
    reader = pypdf.PdfReader(str(PROPOSAL_PDF))
    total_pages = len(reader.pages)
    check(total_pages <= 11, "Proposal total page budget (<= 1 summary + 10 detail)", f"actual={total_pages}p")

    p1_text = reader.pages[0].extract_text() or ""
    p2_text = reader.pages[1].extract_text() or "" if total_pages >= 2 else ""
    check("기획 요약서" in p1_text and "1. 활용사례 개요" not in p1_text, "Summary strictly <= 1 page (Page 1 only)")
    check("1. 활용사례 개요" in p2_text, "Detailed proposal starts cleanly on Page 2")

    blank_pages = []
    for idx, pg in enumerate(reader.pages, 1):
        body = [
            ln.strip()
            for ln in (pg.extract_text() or "").splitlines()
            if ln.strip() and "Olpark Flow AI  |" not in ln and "경진대회 기획서 — Olpark" not in ln
        ]
        if not body:
            blank_pages.append(idx)
    check(len(blank_pages) == 0, "Zero blank pages in rendered PDF", f"blank={blank_pages}")

    with zipfile.ZipFile(PROPOSAL_DOCX) as zf:
        media = [n for n in zf.namelist() if n.startswith("word/media/")]
    check(len(media) >= 9, "Embedded media count (2 QR + 3 charts + 4 live shots)", f"found={len(media)}")

    app_placeholders = re.findall(r"\[직접 기입[^\]]*\]", app_text)
    check(len(app_placeholders) >= 1, "Application form flags user personal fields clearly", f"{len(app_placeholders)} fields to fill")

    print("\n=== GATE 3: Live Production URL & Edge API Reachability ===")
    for label, url in [
        ("Cloudflare Pages App", LIVE_URL),
        ("Live Realtime Parking Edge API", LIVE_API),
        ("Deployed ML Model Bundle JSON", LIVE_BUNDLE),
        ("GitHub Public Source Repo", GITHUB_URL),
    ]:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "OlparkStaticGate/1.0"})
            with urllib.request.urlopen(req, timeout=15) as r:
                body = r.read().decode("utf-8", errors="replace")
                ok = r.status == 200
                detail = f"HTTP {r.status}, {len(body):,}B"
                if url == LIVE_API:
                    parsed = json.loads(body)
                    psum = parsed[0].get("parking_sum") if isinstance(parsed, list) and parsed else None
                    ok = ok and isinstance(psum, int) and psum >= 0
                    detail += f", parking_sum={psum}"
                check(ok, label, detail)
        except Exception as exc:
            check(False, label, str(exc))

    print("\n=== GATE 4: Git Secret Hygiene ===")
    tracked = subprocess.check_output(["git", "ls-files"], cwd=str(ROOT_DIR), text=True).splitlines()
    check(".env" not in tracked, ".env is NOT tracked in Git")
    check(not any("참가신청서" in f for f in tracked), "Personal application form NOT tracked in Git")
    check(not any("3d_raw" in f for f in tracked), "Heavy 3d_raw CAD zips NOT tracked in Git")

    print("\n" + "=" * 68)
    if not failures:
        print(f"ALL ZONE-B STATIC GATES PASSED ({checks_passed}/{checks_passed}) — ZERO HALLUCINATION DRIFT")
        print("\n[Zone C: 인간 5분 최종 검수 체크리스트 (이것만 보세요)]")
        print("  1. 01_참가신청서*.docx 노란색 [직접 기입] 칸 입력 및 서명 (약 1분)")
        print("  2. 02_기획서*.pdf 1~9쪽 1회 스크롤 육안 확인 + 스마트폰 QR 스캔 (약 2분)")
        print("  3. https://olpark-flow-ai.pages.dev 접속 후 3D 지도·Tab 1~4 1회 클릭 (약 1분)")
        print("  4. data@ksponco.or.kr 이메일 발송 및 02-2180-3504 접수 확인 (약 1분)")
        return 0
    else:
        print(f"ZONE-B STATIC GATE FAILED: {len(failures)} issue(s) found:")
        for f in failures:
            print(f"  - {f}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
