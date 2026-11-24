"""Compile Official 2026 KSPO&CO Public Data Contest Submission Word (.docx) Package.

Generates two submission-ready .docx files strictly conforming to `공공데이터_활용_사례_공모전(안내문).hwp`:
  1. docs/01_참가신청서_및_개인정보동의서_OlparkFlowAI.docx
     - [붙임1] 참가 신청서 (개인 / 활용사례) + 참가 서약서 (제1~7항 원문)
     - [붙임1-1] 개인정보 수집 및 이용에 관한 동의서 (제1~5항 원문)
  2. docs/02_기획서_OlparkFlowAI_2026공공데이터경진대회.docx
     - 기획 요약서 (STRICTLY <= 1 page)
     - 상세 기획서 (STRICTLY <= 10 pages, verbatim sections 1~5, scannable QR codes,
       3 empirical matplotlib charts, and 4 live production 1440x900 screenshots)
"""

from __future__ import annotations

import json
from pathlib import Path

import qrcode
from docx import Document
from docx.enum.table import WD_ALIGN_VERTICAL, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn
from docx.shared import Inches, Mm, Pt, RGBColor

ROOT_DIR = Path(__file__).resolve().parent.parent
DOCS_DIR = ROOT_DIR / "docs"
CHARTS_DIR = DOCS_DIR / "charts"
SHOTS_DIR = DOCS_DIR / "screenshots"
QR_DIR = DOCS_DIR / "qr"
BUNDLE_PATH = ROOT_DIR / "data" / "processed" / "web_model_bundle.json"

LIVE_URL = "https://olpark-flow-ai.pages.dev"
LIVE_API_URL = "https://olpark-flow-ai.pages.dev/api/realtime-parking"
GITHUB_URL = "https://github.com/tejo1990/olpark-flow-ai"

NAVY = RGBColor(0x0F, 0x17, 0x2A)
BLUE = RGBColor(0x1D, 0x4E, 0xD8)
SLATE = RGBColor(0x33, 0x41, 0x55)
MUTED = RGBColor(0x64, 0x74, 0x8B)
EMERALD = RGBColor(0x04, 0x78, 0x57)
ROSE = RGBColor(0xBE, 0x12, 0x3C)


def generate_qr(url: str, out_path: Path) -> Path:
    QR_DIR.mkdir(parents=True, exist_ok=True)
    qr = qrcode.QRCode(version=2, box_size=8, border=2)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#0f172a", back_color="white")
    img.save(out_path)
    return out_path


def set_cell_shading(cell, fill_hex: str) -> None:
    tcPr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>')
    tcPr.append(shd)


def set_cell_margins(cell, top=60, bottom=60, left=100, right=100) -> None:
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = OxmlElement("w:tcMar")
    for m, val in (("top", top), ("bottom", bottom), ("left", left), ("right", right)):
        node = OxmlElement(f"w:{m}")
        node.set(qn("w:w"), str(val))
        node.set(qn("w:type"), "dxa")
        tcMar.append(node)
    tcPr.append(tcMar)


def set_table_borders(table, color="CBD5E1", sz="4") -> None:
    tblPr = table._tbl.tblPr
    borders = parse_xml(
        f'<w:tblBorders {nsdecls("w")}>'
        f'<w:top w:val="single" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'<w:bottom w:val="single" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'<w:left w:val="single" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'<w:right w:val="single" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'<w:insideH w:val="single" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'<w:insideV w:val="single" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f"</w:tblBorders>"
    )
    tblPr.append(borders)


def configure_doc(doc: Document, margin_mm: float = 15.5) -> None:
    sec = doc.sections[0]
    sec.page_width = Mm(210)
    sec.page_height = Mm(297)
    sec.top_margin = Mm(margin_mm)
    sec.bottom_margin = Mm(margin_mm)
    sec.left_margin = Mm(margin_mm)
    sec.right_margin = Mm(margin_mm)

    normal = doc.styles["Normal"]
    normal.font.name = "Malgun Gothic"
    normal._element.rPr.rFonts.set(qn("w:eastAsia"), "Malgun Gothic")
    normal.font.size = Pt(9.2)
    normal.font.color.rgb = SLATE
    normal.paragraph_format.space_after = Pt(3)
    normal.paragraph_format.line_spacing = 1.15


def add_header_footer(doc: Document, title_text: str) -> None:
    sec = doc.sections[0]
    sec.different_first_page_header_footer = False

    hp = sec.header.paragraphs[0]
    hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    hr = hp.add_run(title_text)
    hr.font.name = "Malgun Gothic"
    hr._element.rPr.rFonts.set(qn("w:eastAsia"), "Malgun Gothic")
    hr.font.size = Pt(7.8)
    hr.font.color.rgb = MUTED

    fp = sec.footer.paragraphs[0]
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    fr1 = fp.add_run(f"Olpark Flow AI  |  {LIVE_URL}  |  Page ")
    fr1.font.name = "Malgun Gothic"
    fr1._element.rPr.rFonts.set(qn("w:eastAsia"), "Malgun Gothic")
    fr1.font.size = Pt(7.8)
    fr1.font.color.rgb = MUTED

    fld = OxmlElement("w:fldSimple")
    fld.set(qn("w:instr"), "PAGE")
    fp._p.append(fld)


def add_section_heading(doc: Document, text: str) -> None:
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(8)
    p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.keep_with_next = True
    pPr = p._p.get_or_add_pPr()
    pBdr = parse_xml(
        f'<w:pBdr {nsdecls("w")}><w:bottom w:val="single" w:sz="12" w:space="3" w:color="1D4ED8"/></w:pBdr>'
    )
    pPr.append(pBdr)
    r = p.add_run(text)
    r.bold = True
    r.font.name = "Malgun Gothic"
    r._element.rPr.rFonts.set(qn("w:eastAsia"), "Malgun Gothic")
    r.font.size = Pt(12.2)
    r.font.color.rgb = NAVY


def add_sub_heading(doc: Document, text: str) -> None:
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after = Pt(2.5)
    p.paragraph_format.keep_with_next = True
    r = p.add_run(text)
    r.bold = True
    r.font.name = "Malgun Gothic"
    r._element.rPr.rFonts.set(qn("w:eastAsia"), "Malgun Gothic")
    r.font.size = Pt(10.0)
    r.font.color.rgb = BLUE


def add_bullet(doc: Document, lead: str, body: str) -> None:
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Mm(4.5)
    p.paragraph_format.first_line_indent = Mm(-3.0)
    p.paragraph_format.space_after = Pt(2.2)
    p.paragraph_format.line_spacing = 1.14
    r0 = p.add_run("• ")
    r0.bold = True
    r0.font.color.rgb = BLUE
    if lead:
        r1 = p.add_run(lead + " ")
        r1.bold = True
        r1.font.name = "Malgun Gothic"
        r1._element.rPr.rFonts.set(qn("w:eastAsia"), "Malgun Gothic")
        r1.font.size = Pt(8.9)
        r1.font.color.rgb = NAVY
    r2 = p.add_run(body)
    r2.font.name = "Malgun Gothic"
    r2._element.rPr.rFonts.set(qn("w:eastAsia"), "Malgun Gothic")
    r2.font.size = Pt(8.8)
    r2.font.color.rgb = SLATE


def add_callout(doc: Document, title: str, body: str, fill="EFF6FF", border_color="1D4ED8") -> None:
    tbl = doc.add_table(rows=1, cols=1)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell = tbl.cell(0, 0)
    set_cell_shading(cell, fill)
    set_cell_margins(cell, top=80, bottom=80, left=140, right=140)
    tcPr = cell._tc.get_or_add_tcPr()
    tcBorders = parse_xml(
        f'<w:tcBorders {nsdecls("w")}>'
        f'<w:top w:val="single" w:sz="4" w:space="0" w:color="CBD5E1"/>'
        f'<w:bottom w:val="single" w:sz="4" w:space="0" w:color="CBD5E1"/>'
        f'<w:right w:val="single" w:sz="4" w:space="0" w:color="CBD5E1"/>'
        f'<w:left w:val="single" w:sz="24" w:space="0" w:color="{border_color}"/>'
        f"</w:tcBorders>"
    )
    tcPr.append(tcBorders)
    p = cell.paragraphs[0]
    p.paragraph_format.space_after = Pt(1.5)
    rt = p.add_run(title + "\n")
    rt.bold = True
    rt.font.size = Pt(9.0)
    rt.font.color.rgb = NAVY
    rb = p.add_run(body)
    rb.font.size = Pt(8.5)
    rb.font.color.rgb = SLATE


def add_styled_table(
    doc: Document,
    headers: list[str],
    rows: list[list[str]],
    col_widths_mm: list[float] | None = None,
    highlight_row_idx: int | None = None,
    font_pt: float = 8.1,
) -> None:
    tbl = doc.add_table(rows=1 + len(rows), cols=len(headers))
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(tbl, color="CBD5E1", sz="4")

    # Header
    hdr_row = tbl.rows[0]
    for c_idx, h_text in enumerate(headers):
        cell = hdr_row.cells[c_idx]
        set_cell_shading(cell, "1E293B")
        set_cell_margins(cell, top=55, bottom=55, left=75, right=75)
        cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        p = cell.paragraphs[0]
        p.paragraph_format.space_after = Pt(0)
        r = p.add_run(h_text)
        r.bold = True
        r.font.name = "Malgun Gothic"
        r._element.rPr.rFonts.set(qn("w:eastAsia"), "Malgun Gothic")
        r.font.size = Pt(font_pt)
        r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)

    for r_idx, row_vals in enumerate(rows):
        row = tbl.rows[r_idx + 1]
        is_hl = highlight_row_idx is not None and r_idx == highlight_row_idx
        fill = "DBEAFE" if is_hl else ("F8FAFC" if r_idx % 2 == 1 else "FFFFFF")
        for c_idx, val in enumerate(row_vals):
            cell = row.cells[c_idx]
            set_cell_shading(cell, fill)
            set_cell_margins(cell, top=45, bottom=45, left=75, right=75)
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            p = cell.paragraphs[0]
            p.paragraph_format.space_after = Pt(0)
            p.paragraph_format.line_spacing = 1.12
            r = p.add_run(str(val))
            r.bold = is_hl or (c_idx == 0)
            r.font.name = "Malgun Gothic"
            r._element.rPr.rFonts.set(qn("w:eastAsia"), "Malgun Gothic")
            r.font.size = Pt(font_pt)
            r.font.color.rgb = NAVY if is_hl else SLATE

    if col_widths_mm:
        for row in tbl.rows:
            for c_idx, w in enumerate(col_widths_mm):
                row.cells[c_idx].width = Mm(w)


def add_figure(doc: Document, img_path: Path, width_in: float, caption: str) -> None:
    if not img_path.exists():
        return
    p_img = doc.add_paragraph()
    p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_img.paragraph_format.space_before = Pt(3)
    p_img.paragraph_format.space_after = Pt(1.5)
    p_img.paragraph_format.keep_with_next = True
    p_img.add_run().add_picture(str(img_path), width=Inches(width_in))

    p_cap = doc.add_paragraph()
    p_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_cap.paragraph_format.space_after = Pt(4.5)
    r = p_cap.add_run(caption)
    r.italic = True
    r.font.name = "Malgun Gothic"
    r._element.rPr.rFonts.set(qn("w:eastAsia"), "Malgun Gothic")
    r.font.size = Pt(7.9)
    r.font.color.rgb = MUTED


def build_application_form(out_path: Path) -> None:
    doc = Document()
    configure_doc(doc, margin_mm=16.0)

    # Page 1: [붙임1] 참가 신청서 & 참가 서약서
    p_top = doc.add_paragraph()
    p_top.alignment = WD_ALIGN_PARAGRAPH.LEFT
    r_top = p_top.add_run("[붙임1]")
    r_top.bold = True
    r_top.font.size = Pt(9.5)

    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_title.paragraph_format.space_after = Pt(8)
    rt = p_title.add_run("2026년도 공공데이터 활용 경진대회 참가 신청서")
    rt.bold = True
    rt.font.size = Pt(15)
    rt.font.color.rgb = NAVY

    rows = [
        ["참가구분", "☑ 개인    □ 팀", "참가분야", "☑ 활용 사례"],
        ["성명(대표자)", "[직접 기입: 성명]", "생년월일", "[직접 기입: YYYY-MM-DD]"],
        ["휴대전화번호", "[직접 기입: 010-0000-0000]", "이메일", "[직접 기입: email@domain.com]"],
        ["주소", "[직접 기입: 도로명 주소]", "소속(기업)", "[직접 기입: 개인 / 소속명]"],
        [
            "활용사례 제목",
            "Olpark Flow AI — 올림픽공원 공연·날씨·입출차 3D 혼잡 예측 및 게이트·ESG 분산 플랫폼",
            "",
            "",
        ],
        [
            "활용데이터",
            "한국체육산업개발(주) 개방 공공데이터 9종 (실시간 주차현황, 2025 차량입출차·공연·날씨 연계, 주차장 혼잡도, 입출차 정보, 월별주차현황, 국문/영문 공연정보, 대관정보, 잔디시설정보) + 타 기관 융합 3종 (송파구 시간별 실측 기상, 서울교통공사 5·8·9호선, 환경부 공회전 CO₂ 배출계수)",
            "",
            "",
        ],
        [
            "활용사례\n기획 개요",
            f"범용 지도앱(요일 평균)이 반영하지 못하는 올림픽공원 대형 공연·동시대관(최대 26,398명) 조건부 혼잡과 내부 11개 주차구역(P1A~P11) 공간 편중(26.5%p)을 해결하는 3D 디지털 트윈 웹 플랫폼. 방문객 3D 도착·귀가 가이드(한/영), 공단 B2G 동시대관·ESG 탄소 시뮬레이터, 2025 실측 무누수 AI 백테스트(RF+HGB 앙상블, 주차 MAE -29.0%, 방문객 R² 0.767), 원천 품질 감사(DQ-01~04)를 월 유지비 ₩0 서버리스 아키텍처로 구현하여 2028년까지 무중단 운영 가능. (라이브 URL: {LIVE_URL})",
            "",
            "",
        ],
    ]

    tbl = doc.add_table(rows=len(rows), cols=4)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(tbl, color="94A3B8", sz="4")
    widths = [32, 61, 28, 57]
    for r_idx, r_vals in enumerate(rows):
        row = tbl.rows[r_idx]
        if r_idx >= 4:
            # Merge cols 1..3
            c_merged = row.cells[1].merge(row.cells[3])
            c_label = row.cells[0]
            set_cell_shading(c_label, "EFF6FF")
            set_cell_margins(c_label, top=55, bottom=55, left=80, right=80)
            p0 = c_label.paragraphs[0]
            p0.paragraph_format.space_after = Pt(0)
            rl = p0.add_run(r_vals[0])
            rl.bold = True
            rl.font.size = Pt(8.8)
            rl.font.color.rgb = NAVY

            set_cell_margins(c_merged, top=55, bottom=55, left=90, right=90)
            p1 = c_merged.paragraphs[0]
            p1.paragraph_format.space_after = Pt(0)
            rv = p1.add_run(r_vals[1])
            rv.font.size = Pt(8.6)
            rv.font.color.rgb = SLATE
        else:
            for c_idx, val in enumerate(r_vals):
                cell = row.cells[c_idx]
                cell.width = Mm(widths[c_idx])
                is_lbl = c_idx in (0, 2)
                is_placeholder = "[직접 기입" in val
                if is_lbl:
                    set_cell_shading(cell, "EFF6FF")
                elif is_placeholder:
                    set_cell_shading(cell, "FEF9C3")
                set_cell_margins(cell, top=55, bottom=55, left=80, right=80)
                p = cell.paragraphs[0]
                p.paragraph_format.space_after = Pt(0)
                r = p.add_run(val)
                r.bold = is_lbl or is_placeholder
                r.font.size = Pt(8.8)
                r.font.color.rgb = ROSE if is_placeholder else (NAVY if is_lbl else SLATE)

    # 참가 서약서
    p_sw = doc.add_paragraph()
    p_sw.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_sw.paragraph_format.space_before = Pt(12)
    p_sw.paragraph_format.space_after = Pt(6)
    rsw = p_sw.add_run("참 가 서 약 서")
    rsw.bold = True
    rsw.font.size = Pt(12.5)
    rsw.font.color.rgb = NAVY

    p_intro = doc.add_paragraph(
        "본인은 한국체육산업개발(주)에서 개최하는 「2026년도 공공데이터 활용 경진대회」에 참가하면서, 다음 각 호의 규정을 지킬 것을 서약합니다."
    )
    p_intro.paragraph_format.space_after = Pt(4)

    pledges = [
        "1. 대회의 제반 규정을 준수하겠습니다.",
        "2. 참가신청서 및 기획서에 기재한 내용이 사실임을 확인하며, 허위 사실 기재 등으로 인하여 문제가 발생하면 모든 책임은 본인(팀)에게 있음을 확인합니다.",
        "3. 응모작에 대한 저작권으로 인하여 발생하는 민·형사상 책임은 참가자에게 있습니다.",
        "4. 동일·유사 응모작으로 타 경진대회에서 수상한 사실이 있거나, 타인의 저작권을 침해하거나, 제출 내용이 허위로 확인되는 경우 접수 및 수상이 취소될 수 있으며, 이미 지급 받은 시상금은 반환합니다.",
        "5. 응모작의 저작권은 참가자에게 귀속되며, 수상작에 한하여 한국체육산업개발(주)가 정책개선 및 공공 활용을 위하여 홈페이지 등에 게재·공개하는 것에 동의합니다.",
        "6. 수상작의 경우 웹/앱 등 원천 개발 소스 제공 및 2028년까지 서비스 운영에 협조하겠습니다.",
        "7. 심사 결과에 대해 이의를 제기하지 않으며, 원활한 대회 진행에 적극적으로 협조하겠습니다.",
    ]
    for pl in pledges:
        p = doc.add_paragraph(pl)
        p.paragraph_format.left_indent = Mm(4)
        p.paragraph_format.space_after = Pt(2.2)
        for r in p.runs:
            r.font.size = Pt(8.6)

    p_sign = doc.add_paragraph()
    p_sign.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_sign.paragraph_format.space_before = Pt(12)
    rs1 = p_sign.add_run("2026년   11월    일\n\n")
    rs1.font.size = Pt(10)
    rs2 = p_sign.add_run("신청인 :   [직접 기입: 성명]   (서명 또는 인)\n\n")
    rs2.bold = True
    rs2.font.size = Pt(10.5)
    rs3 = p_sign.add_run("한국체육산업개발주식회사 귀하")
    rs3.bold = True
    rs3.font.size = Pt(11.5)
    rs3.font.color.rgb = NAVY

    # Page 2: [붙임1-1] 개인정보 수집 및 이용 동의서
    doc.add_page_break()
    p_t2 = doc.add_paragraph()
    r_t2 = p_t2.add_run("[붙임1-1]")
    r_t2.bold = True
    r_t2.font.size = Pt(9.5)

    p_h2 = doc.add_paragraph()
    p_h2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_h2.paragraph_format.space_after = Pt(10)
    rh2 = p_h2.add_run("개인정보 수집 및 이용에 관한 동의서")
    rh2.bold = True
    rh2.font.size = Pt(14.5)
    rh2.font.color.rgb = NAVY

    privacy_items = [
        ("1. 개인정보 수집·이용 목적", "「2026년도 공공데이터 활용 경진대회」 참가자 관리, 수상자 선정, 진행 상황 안내, 수상작 활용 협약 체결 및 사후 관리를 위해 개인정보를 수집하며, 목적 이외의 용도로는 사용하지 않습니다."),
        ("2. 개인정보 처리자", "한국체육산업개발(주) 디지털혁신팀 (☎ 02-2180-3504)"),
        ("3. 개인정보 수집·이용 항목", "이름, 생년월일, 휴대전화번호, 이메일, 주소, 소속, 팀명\n※ 수상자의 시상금 지급을 위한 정보는 수상 확정 후 별도 동의를 받아 수집"),
        ("4. 동의 거부 권리 및 불이익", "신청자는 개인정보 수집·이용 동의에 대해 거부할 권리가 있습니다. 다만, 동의를 거부할 경우에는 「2026년도 공공데이터 활용 경진대회」 참가자에 대한 공정한 심사 등을 위해 참가가 제한됩니다."),
        ("5. 보유 및 이용기간", "일반참가자는 결과 발표 후 즉시 해당 정보 파기, 수상자의 경우 시상금 지급 완료 및 수상작 서비스 운영 협약 종료일(2028년)까지 보유합니다. 관련 법령에 따라 보존이 필요한 정보는 해당 기간 동안 보존하며, 보유기간 경과 시 지체 없이 파기합니다."),
    ]
    for head, desc in privacy_items:
        ph = doc.add_paragraph()
        ph.paragraph_format.space_before = Pt(6)
        ph.paragraph_format.space_after = Pt(2)
        rh = ph.add_run(head)
        rh.bold = True
        rh.font.size = Pt(9.8)
        rh.font.color.rgb = NAVY
        pd_p = doc.add_paragraph(desc)
        pd_p.paragraph_format.left_indent = Mm(4)
        pd_p.paragraph_format.space_after = Pt(4)

    p_ag = doc.add_paragraph()
    p_ag.paragraph_format.space_before = Pt(12)
    p_ag.alignment = WD_ALIGN_PARAGRAPH.CENTER
    rag = p_ag.add_run("본인은 개인정보 수집·이용에 관한 상기 내용을 확인하였으며, 아래와 같이 동의합니다.\n\n2026년   11월    일")
    rag.font.size = Pt(9.8)

    add_styled_table(
        doc,
        ["동의 여부", "성명", "서명"],
        [["☑ 동의   □ 거부", "[직접 기입: 성명]", "(서명)"]],
        col_widths_mm=[60, 60, 58],
        font_pt=9.5,
    )

    doc.save(out_path)
    print(f"[SAVED] {out_path}")


def build_proposal_doc(out_path: Path, bundle: dict) -> None:
    doc = Document()
    configure_doc(doc, margin_mm=13.0)
    add_header_footer(doc, "2026년도 한국체육산업개발(주) 공공데이터 활용 경진대회 기획서 — Olpark Flow AI")

    qr_live = generate_qr(LIVE_URL, QR_DIR / "qr_live_service.png")
    qr_git = generate_qr(GITHUB_URL, QR_DIR / "qr_github_repo.png")

    cv_p = bundle["benchmarks"]["parking_count"]["cv_5fold_day_grouped"]
    oot_p = bundle["benchmarks"]["parking_count"]["oot_oct_dec"]
    cv_v = bundle["benchmarks"]["visitor_count"]["cv_5fold_day_grouped"]
    stats = bundle["dataset_stats"]

    # =========================================================================
    # PAGE 1: 기획 요약서 (STRICTLY <= 1 PAGE)
    # =========================================================================
    p_tag = doc.add_paragraph()
    p_tag.paragraph_format.space_after = Pt(2)
    r_tag = p_tag.add_run("[붙임1] 2026년도 공공데이터 활용 경진대회 — 기획 요약서 (1장 이내)")
    r_tag.bold = True
    r_tag.font.size = Pt(9.0)
    r_tag.font.color.rgb = BLUE

    p_h1 = doc.add_paragraph()
    p_h1.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_h1.paragraph_format.space_before = Pt(2)
    p_h1.paragraph_format.space_after = Pt(6)
    rh1 = p_h1.add_run("Olpark Flow AI\n올림픽공원 공연·날씨·입출차 3D 혼잡 예측 및 게이트·ESG 분산 플랫폼")
    rh1.bold = True
    rh1.font.size = Pt(14.5)
    rh1.font.color.rgb = NAVY

    summary_rows = [
        ["1. 활용사례명", "Olpark Flow AI — 올림픽공원 공연·날씨·입출차 3D 혼잡 예측 및 게이트·ESG 분산 플랫폼"],
        [
            "2. 사용한\n공공데이터명\n(총 12종 융합)",
            "• 한국체육산업개발(주) 개방 공공데이터 9종 (필수 1종 조건 대비 9종 심층 융합):\n"
            "  ① 올림픽공원 실시간 주차현황(15168686, LIVE API)  ② 2025 차량입출차·공연·날씨 연계(15164822, 7,803건)\n"
            "  ③ 주차장 혼잡도 정보(15164156, P1A~P11 11개 구역)  ④ 입출차 정보(15138735, 215,528건)\n"
            "  ⑤ 월별주차현황(15131671, 2023~2025)  ⑥ 국문 공연정보(3037877, 2,502건)  ⑦ 대관정보(15015212, 717건)\n"
            "  ⑧ 영문 공연정보(15149169, 286건)  ⑨ 잔디시설정보(15143220)   ※ 품질감사 후 2종(15127487·15038496) 의도적 배제 및 개선제언\n"
            "• 타 기관·외부 공공데이터 3종: 송파구 시간별 실측 기상(19,008시간), 서울교통공사 5·8·9호선, 환경부 공회전 CO₂ 배출계수(21g/분)",
        ],
        [
            "3. 요약\n(배경·핵심기능·\n기술구현)",
            "• 배경: 올림픽공원 연간 주차는 2025년 950,695대로 역대 최고치이며 11개 주차구역 혼잡·만차율이 71.8%, P11(85.0%) vs P1A(58.5%) 간 26.5%p의 극심한 공간 편중이 실측됨. 그러나 네이버지도·티맵 등 범용 지도앱은 과거 단순 요일 평균만 제공해 대형 공연(최대 26,398명)·동시대관과 내부 구역별 분산을 해결하지 못함.\n"
            "• 해결책(4-Tab Dual-View 웹 3D 디지털 트윈): 로그인 없이 1초 만에 체험 가능한 단일 공개 URL 구축.\n"
            "  - [Tab 1 방문객 3D 도착 가이드] MapLibre GL JS 기반 3D 올림픽공원·11개 주차구역 혼잡 기둥 실시간 연동, 원클릭 시나리오 칩 4종, 안전 도착 마감 시각, 3개 지하철역 분산 비교, 글로벌 K-POP 팬 원클릭 한/영(EN) 전환.\n"
            "  - [Tab 2 공단 B2G 대관·ESG 시뮬레이터] 6개 공연장 동시 대관 조합 × 우천 × 시차 퇴장(0/30/60분) × 대중교통 전환 시 피크 부하 감축 및 공회전 CO₂ 절감량(소나무 환산) 즉시 시뮬레이션.\n"
            "  - [Tab 3 2025 실측 AI 검증실] 중계 게이트웨이 XML 파서 최적화(DQ-01) 및 8~9월 스케일 변동 구간 격리(DQ-02) 후 무누수 5-Fold Day-Grouped CV로 검증한 RF+HGB 앙상블 모델(주차 MAE 209.9대, Baseline 대비 -29.0% 개선, R² 0.7288 / 방문객 R² 0.7667) 투명 공개.\n"
            "  - [Tab 4 2028 무중단·품질 감사] 월 유지비 ₩0 서버리스 아키텍처(Cloudflare Pages + Edge Function + GitHub Actions 일일 스냅샷) 및 연계 최적화 인사이트 4건(DQ-01~04)·신규 개방 제언 5건 수록.",
        ],
        [
            "4. 기대효과\n(정량 성과 및\n사회적 가치)",
            "• [예측 정확도] 단순 시간·요일 평균(Baseline MAE 295.6대) 대비 오차 29.0% 감축(209.9대, 평일 표준일 MAE 35.9대).\n"
            "• [공간 분산·민원 해소] 병목 구역(P11·P5·P8) 집중 차량을 여유 구역(P1A·P1B·P2) 및 한성백제·몽촌토성역으로 분산 유도.\n"
            "• [환경·ESG 가치] 동시대관 시차·대중교통 분산 적용 시 공연 1회당 공회전 CO₂ 188~204kg 절감, 연간(113 공연일) 21.2~23.1 tCO₂ 저감(30년생 소나무 3,219~3,493그루 식재 효과).\n"
            "• [지속성·기관 평가 환류] 유지비 ₩0 설계로 2028년까지 무중단 운영 보장 + 공단 2026 신규 주력 데이터(실시간 주차·2025 연계) 실증 및 5대 품질 고도화 협업 제언으로 행안부·문체부 평가 우수 성과에 직접 기여.",
        ],
    ]
    add_styled_table(doc, ["구분", "핵심 내용"], summary_rows, col_widths_mm=[30, 151], font_pt=8.2)

    # Bottom QR + Live URL Box on Page 1
    p_sp = doc.add_paragraph()
    p_sp.paragraph_format.space_before = Pt(4)
    p_sp.paragraph_format.space_after = Pt(2)

    qr_tbl = doc.add_table(rows=1, cols=2)
    qr_tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(qr_tbl, color="93C5FD", sz="6")
    c_left, c_right = qr_tbl.cell(0, 0), qr_tbl.cell(0, 1)
    c_left.width = Mm(148)
    c_right.width = Mm(33)
    set_cell_shading(c_left, "EFF6FF")
    set_cell_shading(c_right, "FFFFFF")
    set_cell_margins(c_left, top=65, bottom=65, left=110, right=100)
    set_cell_margins(c_right, top=40, bottom=40, left=40, right=40)
    c_left.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
    c_right.vertical_alignment = WD_ALIGN_VERTICAL.CENTER

    pl = c_left.paragraphs[0]
    pl.paragraph_format.space_after = Pt(1)
    rl1 = pl.add_run("■ 실시간 라이브 서비스 즉시 확인 (로그인 불필요 · PC/모바일 지원)\n")
    rl1.bold = True
    rl1.font.size = Pt(9.0)
    rl1.font.color.rgb = BLUE
    rl2 = pl.add_run(
        f"• 서비스 URL: {LIVE_URL}\n"
        f"• 실시간 주차 Edge API: {LIVE_API_URL}\n"
        f"• 원천 소스코드 (MIT 공개): {GITHUB_URL}\n"
        f"• 배포 검증: 2026-11-24 프로덕션 배포 완료 (LIVE API 2,332~2,370대 실측 · 콘솔 에러 0건)"
    )
    rl2.font.size = Pt(8.1)
    rl2.font.color.rgb = NAVY

    pr = c_right.paragraphs[0]
    pr.alignment = WD_ALIGN_PARAGRAPH.CENTER
    pr.paragraph_format.space_after = Pt(0)
    pr.add_run().add_picture(str(qr_live), width=Inches(0.95))

    # =========================================================================
    # DETAILED PROPOSAL (PAGES 2 ~ 10: STRICTLY <= 10 PAGES)
    # =========================================================================
    doc.add_page_break()

    # ----- SECTION 1 (Page 2) -----
    add_section_heading(doc, "1. 활용사례 개요")
    add_sub_heading(doc, "1-1. 활용사례 명")
    p = doc.add_paragraph(
        "Olpark Flow AI — 올림픽공원 공연·날씨·입출차 3D 혼잡 예측 및 게이트·ESG 분산 플랫폼 (방문객 B2C · 공단 관제 B2G 통합 디지털 트윈)"
    )
    p.runs[0].bold = True

    add_sub_heading(doc, "1-2. 활용사례 기능, 특징 등 세부내용")
    add_styled_table(
        doc,
        ["탭 구분", "대상 사용자", "핵심 기능 및 데이터 기반 차별화"],
        [
            [
                "Tab 1\n방문객 3D 도착 가이드",
                "공연 관람객 · 공원 방문객 · 외국인 팬(EN)",
                "• 원클릭 대표 시나리오 칩 4종(KSPO DOME 콘서트·우천 동시대관·가을 피크닉·일반 평일) + 상세 조건 접이식 설정\n"
                "• MapLibre GL JS 3D 올림픽공원 지도 위 6개 공연장 볼륨 & P1A~P11 11개 주차구역 혼잡 3D 기둥 실시간 연동\n"
                "• 안전 주차 마감 시각, 추천 분산 구역(P1A·P1B·P2), 3개 지하철역(5·8·9호선) 귀가 비교, 2026 영문 공연 원클릭 시뮬레이션",
            ],
            [
                "Tab 2\n공단 B2G · ESG 시뮬레이터",
                "공단 대관·운영·ESG 담당자",
                "• 6개 공연장(KSPO DOME 15,000석 ~ 평화의광장) 동시 대관 조합 × 우천 스트레스 테스트\n"
                "• 정책 개입 레버(시차 입장/퇴장 0/30/60분 · 대중교통 전환율 · 가변전광판 P1A/P1B 분산율) 실시간 조정\n"
                "• 개입 전/후 24시간 부하 곡선, 피크 감축률(%), 출차 대기 단축(분), 공회전 CO₂ 절감량(kg/tCO₂ · 소나무 환산)",
            ],
            [
                "Tab 3\n2025 실측 AI 검증실",
                "외부 심사위원 · 데이터 전문가",
                "• Baseline / Ridge / RandomForest / HistGradientBoosting / Ensemble(RF+HGB) 5개 모델 정량 비교표\n"
                "• 2025년 실제 4대 대표 일자(대형 공연·우천 공연·성수기 주말·평일 기준일) 실측 vs AI 예측 오버레이\n"
                "• Permutation 변수 중요도 Top 8 및 11개 구역(P1A~P11) 실측 공간 편중 차트 투명 공개",
            ],
            [
                "Tab 4\n2028 무중단 · 품질 감사",
                "공단 디지털혁신팀 · 평가위원",
                "• 월 유지비 ₩0 서버리스 아키텍처 상태 & 실시간 주차 LIVE API / Snapshot Fallback 실시간 모니터링\n"
                "• 실데이터 전수 감사에서 적발한 원천 품질 이슈 4건(DQ-01~04) 및 공단 차년도 신규 개방·개선 제언 5건 수록",
            ],
        ],
        col_widths_mm=[34, 34, 113],
        font_pt=8.0,
    )

    add_sub_heading(doc, "1-3. 활용사례 서비스 확인 방법 (라이브 URL · 실시간 API · 오픈소스)")
    qr2_tbl = doc.add_table(rows=1, cols=3)
    qr2_tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(qr2_tbl, color="CBD5E1", sz="4")
    c0, c1, c2 = qr2_tbl.cell(0, 0), qr2_tbl.cell(0, 1), qr2_tbl.cell(0, 2)
    c0.width, c1.width, c2.width = Mm(119), Mm(31), Mm(31)
    set_cell_shading(c0, "F8FAFC")
    set_cell_margins(c0, top=55, bottom=55, left=90, right=80)
    set_cell_margins(c1, top=35, bottom=35, left=30, right=30)
    set_cell_margins(c2, top=35, bottom=35, left=30, right=30)
    p0 = c0.paragraphs[0]
    p0.paragraph_format.space_after = Pt(0)
    r0 = p0.add_run(
        f"• 라이브 웹 서비스: {LIVE_URL}\n"
        f"  (별도 앱 설치·로그인 없이 Chrome/Edge/Safari PC·모바일 즉시 실행)\n"
        f"• 실시간 주차 Edge API: {LIVE_API_URL}\n"
        f"  (공단 실시간 API CORS 우회 + 60초 Edge 캐시, 실시간 주차대수 JSON 반환)\n"
        f"• 원천 개발 소스코드 (MIT): {GITHUB_URL}\n"
        f"  (Python 수집·EDA·ML 파이프라인 + React/MapLibre 3D 웹 + GitHub Actions 포함)"
    )
    r0.font.size = Pt(8.0)

    for cell_q, qimg, lbl in ((c1, qr_live, "라이브 서비스"), (c2, qr_git, "GitHub 소스")):
        pq = cell_q.paragraphs[0]
        pq.alignment = WD_ALIGN_PARAGRAPH.CENTER
        pq.paragraph_format.space_after = Pt(0)
        pq.add_run().add_picture(str(qimg), width=Inches(0.82))
        rq = pq.add_run(f"\n{lbl}")
        rq.bold = True
        rq.font.size = Pt(7.2)
        rq.font.color.rgb = NAVY

    add_figure(
        doc,
        SHOTS_DIR / "tab1_visitor.png",
        5.7,
        "[그림 1] 라이브 배포 화면(https://olpark-flow-ai.pages.dev) — Tab 1 방문객 3D 도착 가이드 (실시간 2,332대 연동 · 11개 구역 3D 기둥)",
    )

    # ----- SECTION 2 -----
    add_section_heading(doc, "2. 활용사례의 독창성")
    add_sub_heading(doc, "2-1. 활용 공공데이터 목록 (한국체육산업개발 9종 + 외부 3종 융합 / 2종 감사 후 배제)")
    add_styled_table(
        doc,
        ["구분", "데이터명 (ID)", "제공형태 · 규모", "본 서비스 내 핵심 활용 역할"],
        [
            ["기관 필수 1", "올림픽공원 실시간 주차현황 (15168686)", "OpenAPI · 실시간 JSON", "상단 LIVE 주차대수 관제 및 60초 Edge 캐시·일일 스냅샷"],
            ["기관 필수 2", "2025 차량입출차·공연·날씨 연계 (15164822)", "OpenAPI(XML) · 7,803건", "주차·방문객·기상·관람객수(0~26,398명) ML 학습 코어"],
            ["기관 필수 3", "주차장 혼잡도 정보 (15164156)", "CSV · 699건 (11개 구역)", "P1A~P11 공간 편중 계수 산출 및 3D 기둥·분산 추천 근거"],
            ["기관 필수 4", "올림픽공원 입출차 정보 (15138735)", "CSV · 215,528건 (24.07)", "분 단위 체류(중앙값 74분, P90 196분)·야간 출차 CO₂ 산출"],
            ["기관 필수 5", "월별주차현황 (15131671)", "CSV · 72건 (2023~2025)", "3개년 계절성(1.79배) 분석 및 DQ-02 8~9월 이상치 교차검증"],
            ["기관 필수 6", "올림픽공원 영문 공연정보 (15149169)", "CSV · 286건 (2026년 70건)", "외국인 K-POP 팬 원클릭 시나리오 및 한/영 UI 연동"],
            ["기관 필수 7", "올림픽공원 공연정보 (3037877)", "OpenAPI · 2,502건", "공연장별 이력·페스티벌 키워드 및 외부 공연 피처 추출"],
            ["기관 필수 8", "올림픽공원 대관정보 (15015212)", "OpenAPI · 717건", "6개 주요 공연장 대관 패턴 및 B2G 동시대관 모델링 기준"],
            ["기관 필수 9", "잔디시설정보 (15143220)", "CSV · 8건", "88잔디마당·나홀로나무·피크닉장 개방 구역 지도 반영"],
            ["외부 융합", "송파구 시간별 실측 기상 / 5·8·9호선 / 환경부·산림청 계수", "OpenAPI·정적·공표치", "기상 19,008시간 실측 검증 · 3개 역 도보/병목 분산 가이드 · CO₂ 21g/분"],
            ["검토 후 배제*", "공연장 실감형 3D (15127487) · 유실물 (15038496)", "전수 실사 후 보류", "전문가용 고정밀 CAD(웹 경량본 병행 제언) & 기존 LOST112 중복 방지"],
        ],
        col_widths_mm=[22, 58, 36, 65],
        font_pt=7.7,
    )

    add_sub_heading(doc, "2-2. 활용 배경, 데이터 활용 빈도·비중·가공 가능성 및 기존 서비스 대비 차별성")
    add_bullet(
        doc,
        "[실측 배경 1 — 역대 최고 주차 수요 & 26.5%p 공간 편중]",
        "월별주차현황(15131671) 분석 결과 올림픽공원 연간 주차는 2023년 943,259대 → 2024년 930,324대 → 2025년 950,695대로 역대 최고치를 경신했고 성수기(10월 10.1만) vs 비수기(1월 5.7만) 편차가 1.79배에 달합니다. 특히 15164156(699건) 실측 결과 전체 기록의 71.8%가 혼잡·만차이며, P11(혼잡+만차 85.0%, 만차 45.0%)·P5(82.7%)·P8(80.3%)에 집중되는 반면 P1A(58.5%)·P1B(58.7%)·P2(59.3%)는 26.5%p 여유로운 극심한 공간 불균형이 확인되었습니다.",
    )
    add_bullet(
        doc,
        "[실측 배경 2 — 피크일 동시주차 2배 폭증 & 야간 출차 공회전]",
        "2024년 7월 215,528건 분 단위 입출차 분석 결과, 일평균 입차는 6,952.5대, 체류시간 중앙값 74분(상위 10% P90=196분, 3시간 이상 공연 체류)이며 피크일(7/21) 16시 최대 동시주차 2,975대로 평일 대비 약 1.9배 폭증합니다. 특히 19~22시 평균 1,836.2대가 집중 출차하며 40%가 15분 공회전할 경우 1회당 약 231.2 kg CO₂가 배출됩니다.",
    )
    add_bullet(
        doc,
        "[활용 빈도·비중·가공 가능성]",
        "서비스 전체 가치의 90% 이상이 공단 공공데이터에 기반합니다. ① 실시간 주차 API는 60초 Edge 캐시로 상시 호출(초고빈도), ② GitHub Actions는 매일 06:00 KST 스냅샷 자동 갱신(일일 빈도), ③ 2025 연계 7,803건과 11개 구역 혼잡도는 Python 파이프라인으로 22개 파생 피처로 가공 후 58.7KB 경량 JSON으로 컴파일되어 타 공원·지자체 체육시설로 즉시 수평 확장이 가능합니다.",
    )

    add_callout(
        doc,
        "★ 기존 범용 지도앱(네이버지도·티맵) 및 단순 공모작 대비 3대 구조적 차별점",
        "1) 조건부 공연 AI 예측: 일반 지도앱은 '과거 단순 요일 평균'만 보여줄 뿐 대형 콘서트(최대 26,398명)·동시대관 특수일을 구분하지 못합니다. 본 서비스는 공단 독점 공연관람객수 변수를 학습한 앙상블 AI로 조건부 예측을 제공합니다.\n"
        "2) 내부 11개 세부 구역(P1A~P11) 3D 미시 분산 + B2G ESG 시뮬레이터: 지도앱에 없는 공원 내부 구역별 편중 해소 및 공단 대관 담당자용 시차 편성·공회전 CO₂ 절감 시뮬레이터를 결합했습니다.\n"
        "3) 데이터 적합성 검증 & 연계 최적화 인사이트(DQ-01~04): 58종 전수 실사를 통해 전문 설계용 고정밀 3D CAD(웹 경량화 병행 제언)와 기존 LOST112 중복 유실물 API는 의도적으로 분리하고, MapLibre 3D 파크 트윈(0.5초 로딩)으로 완성도와 신뢰성을 극대화했습니다.",
    )

    add_sub_heading(doc, "2-3. 실데이터 연계 과정에서 도출한 품질 고도화 협업 인사이트 (DQ-01 ~ DQ-04)")
    add_styled_table(
        doc,
        ["코드", "유형", "연계·전처리 과정에서 확인된 특성", "본 서비스의 기술적 보완 및 공단 협업 환류"],
        [
            ["DQ-01", "게이트웨이", "문화포털 중계 API(API_CPM_009) JSON 직렬화 시 CDATA 미출력", "XML(application/xml) 파서 자동 전환으로 7,803건 100% 복원 + 중계 개선 제언"],
            ["DQ-02", "스케일변동", "2025년 8~9월 구간 집계 스케일 변동(평균 315 vs 정상 1,250)", "월별주차(15131671: 8월 76,408·9월 83,344대) 교차검증 후 1,447행 안전 격리"],
            ["DQ-03", "결측보완", "2025년 11~12월 시간대 레코드 일부 누락 (281·257건 수록)", "월별 백테스트 지표 분리 공개 및 차년도 수집 안정화 협업 제언"],
            ["DQ-04", "중복방지", "유실물 API(KSClost) 게시판 HTML 형식 & 공식센터·LOST112 중복", "서비스 집중도 유지를 위해 UI 탑재 배제 + 정형 JSON 개방 제언"],
        ],
        col_widths_mm=[16, 20, 71, 74],
        font_pt=7.8,
    )

    # ----- SECTION 3 (Pages 5~7) -----
    doc.add_page_break()
    add_section_heading(doc, "3. 활용사례의 구체성")
    add_sub_heading(doc, "3-1. 데이터 파이프라인 · 22개 피처 엔지니어링 및 무누수 검증 설계")
    add_bullet(
        doc,
        "[End-to-End 재현 가능 파이프라인]",
        "fetch_openapi.py(XML CDATA 복원·429 지수 백오프 수집) → run_csv_eda.py(215,528건 체류·CO₂ 및 11개 구역 편중 산출) → train_model.py(DQ-02 격리 후 정제 6,356시간·297일·공연일 113일 학습 및 58.7KB 웹 추론 번들 컴파일) 전 과정이 단일 명령으로 재현됩니다.",
    )
    add_bullet(
        doc,
        "[사전 가용 피처 22종 (Zero Target Leakage)]",
        "실제 운용 시점(D-1~D-7)에 확보 가능한 변수만 사용했습니다: 시간/월 순환 인코딩(sin/cos), 요일·주말·공휴일·금토일 여부, 기온·쾌적온도 편차((T-20)²), 강수량·우천여부·습도·풍속, 당일 최대 공연관람객수, 시간대별 관람객수, 공연 지속시간, 공연 시작 대비 상대시각(입장 램프·퇴장 테일 포착), 외부 국문/영문 공연 건수 및 페스티벌 플래그.",
    )
    add_bullet(
        doc,
        "[11개 구역(P1A~P11) 3D 부하 추정 모델 투명성]",
        "현재 공단 실시간 API는 공원 전체 합계(parking_sum)만 제공하므로, 3D 지도의 구역별 부하(%)는 15164156 실측 공간 편중 계수(구역 혼잡+만차율 ÷ 평균 71.8%)를 적용한 정량 추정치이며, 향후 [제언 2] 구역별 실시간 API 개방 시 코드 10줄 수정만으로 1:1 실측 매핑이 가능합니다.",
    )
    add_bullet(
        doc,
        "[무누수 이중 검증 (5-Fold Day-Grouped CV + Oct–Dec OOT Holdout)]",
        "동일 날짜의 인접 시간이 학습·검증에 섞이는 누수를 차단하기 위해 날짜 단위 그룹 교차검증(GroupKFold)과 완전 미래 시점(1~7월 학습 → 10~12월 테스트) OOT 검증을 병행했습니다.",
    )

    add_sub_heading(doc, "3-2. 5개 모델 정량 백테스트 비교표 (정제 6,356시간 · 297일 기준)")
    model_order = ["Baseline_HourWeekend", "Ridge", "RandomForest", "HistGradientBoosting", "Ensemble_RF_HGB"]
    model_names = {
        "Baseline_HourWeekend": "Baseline (시간×주말 평균)",
        "Ridge": "Ridge Regression (선형)",
        "RandomForest": "RandomForest (260 Trees)",
        "HistGradientBoosting": "HistGradientBoosting",
        "Ensemble_RF_HGB": "Ensemble (RF + HGB) ★ 최종 채택",
    }
    bench_rows = []
    for k in model_order:
        p = cv_p[k]
        o = oot_p[k]
        v = cv_v[k]
        bench_rows.append(
            [
                model_names[k],
                f"{p['mae']:.2f}",
                f"{p['rmse']:.2f}",
                f"{p['r2']:.4f}",
                f"{p['peak_mape_pct']:.1f}%",
                f"{o['r2']:.4f}",
                f"{v['mae']:.1f} / {v['r2']:.4f}",
            ]
        )
    add_styled_table(
        doc,
        ["모델", "주차 CV MAE", "주차 CV RMSE", "주차 CV R²", "Peak MAPE", "미래 OOT R²", "방문객 MAE / R²"],
        bench_rows,
        col_widths_mm=[48, 21, 22, 21, 20, 21, 28],
        highlight_row_idx=4,
        font_pt=7.8,
    )
    p_oot = doc.add_paragraph(
        "※ 미래 OOT(10~12월) 해석: 앙상블(R² 0.3557, Baseline 대비 +47.8%)·HGB(0.3715, +54.4%)가 크게 우세하나, 단일 연도(2025) 데이터 특성상 10~12월 계절 패턴 미학습 및 11~12월 결측(DQ-03)으로 절대 R²가 CV(0.7288)보다 낮음 → 2026년 2차 연도 누적 재학습 시 0.73+ 수렴."
    )
    p_oot.paragraph_format.space_before = Pt(2)
    p_oot.paragraph_format.space_after = Pt(2)
    p_oot.runs[0].font.size = Pt(7.5)
    p_oot.runs[0].font.color.rgb = MUTED

    add_figure(
        doc,
        CHARTS_DIR / "backtest_actual_vs_pred.png",
        4.75,
        "[그림 2] 2025 올림픽공원 4대 대표 시나리오(대형 공연·우천 공연·성수기 주말·평일 기준일) 실측 vs RF+HGB 앙상블 백테스트",
    )

    # Page 6: Feature Importance + 11-Zone Spatial Asymmetry
    doc.add_page_break()
    add_sub_heading(doc, "3-3. AI 예측 근거 설명력(XAI) 및 11개 구역 공간 편중 실증 차트")
    p_xai = doc.add_paragraph(
        "Permutation Importance 분석 결과 시간대(hour_cos)와 계절성(month_cos)에 이어 '당일 최대 공연관람객수(daily_max_audience)', '공휴일(is_holiday)', '시간대별 관람객수(concert_audience)', '습도·강수'가 핵심 예측 변수로 입증되었습니다. 이는 단순 요일 평균을 쓰는 기존 지도앱 대비 공연 정보 융합이 MAE를 29.0% 감축시킨 수학적 근거입니다."
    )
    p_xai.paragraph_format.space_after = Pt(3)

    add_figure(
        doc,
        CHARTS_DIR / "feature_importance.png",
        5.1,
        "[그림 3] 주차 혼잡 예측 앙상블 모델 주요 변수 중요도 Top 10 (Oct–Dec 2025 OOT R² 감소량 기준)",
    )
    add_figure(
        doc,
        CHARTS_DIR / "zone_congestion_asymmetry.png",
        5.1,
        "[그림 4] 11개 세부 주차구역(P1A~P11) 만차·혼잡 실측 비율 — 병목 P11(85.0%) vs 여유 P1A(58.5%) 26.5%p 편중",
    )

    # Page 7: Live UI Screenshots of Tab 2 & Tab 3
    doc.add_page_break()
    add_sub_heading(doc, "3-4. 주요 기능별 실제 구현 화면 (B2G ESG 시뮬레이터 · 2025 실측 AI 검증실)")
    add_figure(
        doc,
        SHOTS_DIR / "tab2_simulator.png",
        5.5,
        "[그림 5] Tab 2 공단 B2G 대관·ESG 탄소 시뮬레이터 — 6개 공연장 동시대관 조합 × 시차·대중교통 정책 레버 및 개입 전/후 곡선",
    )
    add_figure(
        doc,
        SHOTS_DIR / "tab3_backtest.png",
        5.5,
        "[그림 6] Tab 3 2025 실측 AI 검증실 — 5개 모델 벤치마크표, 실측 vs 예측 오버레이, 변수 중요도 및 구역 편중 대시보드",
    )

    # ----- SECTION 4 (Page 8) -----
    doc.add_page_break()
    add_section_heading(doc, "4. 사례의 활용 적절성 (사회적 가치 창출 및 공익성)")

    add_sub_heading(doc, "4-1. 대국민 편익 및 글로벌·교통약자 포용성 제고")
    add_bullet(
        doc,
        "[공연 관람객 도착 불확실성 해소]",
        "원클릭 시나리오 선택만으로 '안전 주차 마감 시각(예: 13:00 이전 도착 권장)'과 만차 위험 구역(P11·P5·P8) 회피 경로, 평화의광장 여유 구역(P1A·P1B·P2) 및 3개 지하철역(올림픽공원역 3번 출구 병목 회피 → 한성백제역·몽촌토성역 도보 분산) 가이드를 1초 만에 제공합니다.",
    )
    add_bullet(
        doc,
        "[외국인 K-POP 팬 정보 격차 해소]",
        "2026년 한 해만 70건이 등록된 영문 공연정보(15149169)를 연계하고 상단 원클릭 'EN / 한국어' 전환을 지원하여, 한국어 주차·지하철 안내에 취약한 글로벌 관람객이 언어 장벽 없이 올림픽공원 교통·분산 정보를 이용할 수 있습니다.",
    )

    add_sub_heading(doc, "4-2. 환경·ESG 공회전 탄소 저감 정량 효과 (실측 215,528건 기반)")
    add_styled_table(
        doc,
        ["평가 지표 (우천 동시대관 기준)", "현행 (미개입)", "기본 개입 (전환 15% · [그림 5])", "목표 개입 (전환 25% · 시차 30분)"],
        [
            ["피크 시간대 주차 부하", "2,379 대", "2,001 대 (-15.9%)", "1,766 대 (-25.8%)"],
            ["야간(19~22시) 평균 출차 대기시간", "22 분", "14 분 (-36.4%)", "14 분 (-36.4%)"],
            ["대형 공연 1회당 공회전 CO₂ 배출", "324 kg CO₂", "136 kg (-188 kg/회)", "120 kg (-204 kg/회)"],
            ["연간 누적 ESG 효과 (113 공연일)", "36.6 tCO₂", "21.2 tCO₂ 절감 (소나무 3,219그루)", "23.1 tCO₂ 절감 (소나무 3,493그루)"],
        ],
        col_widths_mm=[50, 29, 51, 51],
        highlight_row_idx=3,
        font_pt=7.9,
    )
    p_note = doc.add_paragraph(
        "※ 산출 근거: 환경부 승용차 공회전 배출계수(21g CO₂/분, 1.26kg/시간), 국립산림과학원 30년생 소나무 연간 탄소흡수량(6.6kg/그루), 공단 15138735 피크일 야간 출차량(1,836.2대) 및 API_CPM_009 2025년 실제 공연일(113일) 기준."
    )
    p_note.runs[0].font.size = Pt(7.8)
    p_note.runs[0].font.color.rgb = MUTED

    add_sub_heading(doc, "4-3. 주최 기관(한국체육산업개발) 대외 평가 및 데이터 기반 행정 환류 가치")
    add_bullet(
        doc,
        "[정부 공공데이터 평가 핵심 지표 직결]",
        "행안부 '공공데이터 제공 운영실태 평가'(개방·활용 48~50점, AI·고가치 데이터 융합 가점) 및 문체부 '문화공공데이터 개방 우수기관'(3년 연속 우수상 방어)에서 공단이 2026년 8~10월 집중 개방한 플래그십 데이터(실시간 주차·2025 연계·혼잡도)의 실동작 대국민 레퍼런스로 즉시 활용 가능합니다.",
    )
    add_bullet(
        doc,
        "[증거 기반(Evidence-Based) 대관·시설 행정 지원]",
        "B2G 시뮬레이터를 통해 KSPO DOME·핸드볼·올림픽홀 동시 대관 심사 단계에서 사전에 주차 포화 시각과 30분 시차 편성 효과를 정량 검토할 수 있어, 현장 민원 감축과 교통안전 확보에 기여합니다.",
    )

    # ----- SECTION 5 (Pages 9~10) -----
    doc.add_page_break()
    add_section_heading(doc, "5. 실현가능성 및 기타 (2028년 무중단 운영 및 추가 개방 제언)")

    add_sub_heading(doc, "5-1. 추진 일정 및 개발·운영 계획 (현재 100% 라이브 구축 완료)")
    add_styled_table(
        doc,
        ["단계", "기간", "주요 추진 내용", "현황"],
        [
            ["1단계 · 구축 및 실증", "2026.11 (완료)", "공공데이터 12종 수집·DQ 감사·RF+HGB 앙상블 학습·4-Tab 3D 웹 배포 및 LIVE API 검증", "완료 (100%)"],
            ["2단계 · 공단 연계", "2027.01 ~ 06", "올림픽공원 공식 홈페이지·모바일 배너 링크 연동, 2026년 신규 입출차 데이터 연차 재학습", "협조 준비"],
            ["3단계 · 고도화·유지", "2027.07 ~ 2028.12", "구역별 실시간 잔여면수 API 개방 시 즉각 매핑, GitHub Actions 자동 스냅샷 무중단 운영", "유지비 ₩0"],
        ],
        col_widths_mm=[34, 28, 97, 22],
        highlight_row_idx=0,
        font_pt=8.0,
    )

    add_sub_heading(doc, "5-2. 2028년까지 서비스 유지 계획 (유지비 ₩0 서버리스 · 장애 자가 복구)")
    add_bullet(
        doc,
        "[운영비 ₩0 구조로 개인 지속성 100% 확보]",
        "유료 GPU 서버·상용 DB·토큰 과금 LLM API를 일절 배제했습니다. ① 정적 웹 호스팅은 Cloudflare Pages 무료 플랜(무제한 대역폭), ② 실시간 주차 CORS 프록시는 Cloudflare Pages Function(일 10만 회 무료, 60초 Edge 캐시), ③ AI 추론은 58.7KB 사전 컴파일 JSON으로 브라우저 내 0ms 실행되어 2028년까지 월 운영비가 0원입니다.",
    )
    add_bullet(
        doc,
        "[404/장애 없는 이중 안전망(Graceful Fallback) & MIT 소스 이관]",
        "GitHub Actions(.github/workflows/refresh-data.yml)가 매일 06:00 KST 실시간 스냅샷을 자동 갱신하므로, 공단 원천 API 점검 시에도 최신 스냅샷으로 자동 전환되어 무중단 표시됩니다. 전체 소스는 MIT 라이선스로 GitHub에 공개되어 수상 시 공단 자체 인프라로도 10분 내 이관 가능합니다.",
    )

    add_figure(
        doc,
        SHOTS_DIR / "tab4_ops_audit.png",
        3.55,
        "[그림 7] Tab 4 2028 무중단 운영·품질 감사 — 월 유지비 ₩0 아키텍처, LIVE API 2,332대 상태, DQ-01~04 감사 및 제언 5건",
    )

    add_sub_heading(doc, "5-3. 향후 추가 개방 및 품질 개선이 필요한 공공데이터 실무 제언 (5건)")
    add_styled_table(
        doc,
        ["구분", "대상 데이터 / 신규 개방 항목", "현황 진단 및 기대 파급효과"],
        [
            ["제언 1", "API_CPM_009 JSON 직렬화 수정 및 8~9월·11~12월 결손 보정", "JSON 호출 시 CDATA(DESCRIPTION) null 유실 및 8~9월 75% 스케일 이탈 보완 시 민간 AI 활용성 즉시 정상화 및 품질인증 최우수 방어"],
            ["제언 2", "실시간 주차현황 API의 구역별(P1A~P11) 잔여면수 세분화 개방", "현재 총합계(parking_sum) 1개 값만 제공 → 11개 구역별 실시간 잔여면수 개방 시 내비게이션·전광판과 연동한 정밀 분산 완성"],
            ["제언 3", "KOPIS·예매처 연계 공연장별 예상 입장인원 익명 사전 개방", "사후 집계가 아닌 공연 D-7 시점 익명 예상 관객 수 개방 시 사전 혼잡 예보 R² 0.73 → 0.85+ 도약 및 선제적 교통 통제 가능"],
            ["제언 4", "실감형 3D 공연장(15127487) 웹용 경량 GLB 파생본 병행 개방", "현 설계 전문가용 고정밀 CAD(53~75MB)에 더해 웹·모바일 대중 서비스용 경량 본(Draco ≤5MB + 좌석 블록 ID) 병행 개방 시 3D 시야 생태계 확장"],
            ["제언 5", "유실물 API(KSClost) 정형 JSON 컬럼 분리 및 LOST112 실시간 연계", "HTML 게시판 덤프 대신 품목·습득구역·보관상태(보관중/이관) 정형 컬럼 개방 시 외국인·관람객 실시간 분실물 검색 생태계 구축"],
        ],
        col_widths_mm=[16, 62, 103],
        font_pt=7.8,
    )

    doc.save(out_path)
    print(f"[SAVED] {out_path}")


def main() -> int:
    bundle = json.loads(BUNDLE_PATH.read_text(encoding="utf-8"))
    app_out = DOCS_DIR / "01_참가신청서_및_개인정보동의서_OlparkFlowAI.docx"
    prop_out = DOCS_DIR / "02_기획서_OlparkFlowAI_2026공공데이터경진대회.docx"
    build_application_form(app_out)
    build_proposal_doc(prop_out, bundle)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
