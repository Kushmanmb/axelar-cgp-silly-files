#!/usr/bin/env python3
"""
generate_audit_pdf.py
---------------------
Converts AUDIT.md into a structured PDF report using fpdf2.
Produces:  audit/axelar-cgp-audit-report.pdf

Usage:
    python3 scripts/generate_audit_pdf.py
"""

import os
import re
import sys
import textwrap
from datetime import date
from fpdf import FPDF
from fpdf.enums import XPos, YPos

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUDIT_MD = os.path.join(REPO_ROOT, "AUDIT.md")
OUTPUT_DIR = os.path.join(REPO_ROOT, "audit")
OUTPUT_PDF = os.path.join(OUTPUT_DIR, "axelar-cgp-audit-report.pdf")

# Severity colour palette  (R, G, B)
SEVERITY_COLORS = {
    "critical": (180, 0, 0),
    "high":     (220, 60, 0),
    "medium":   (210, 130, 0),
    "low":      (40, 120, 200),
    "info":     (80, 80, 80),
    "informational": (80, 80, 80),
}

BRAND_BLUE  = (10, 60, 160)
BRAND_DARK  = (20, 20, 40)
LIGHT_GRAY  = (245, 245, 248)
MID_GRAY    = (180, 180, 190)
CODE_BG     = (30, 30, 50)
CODE_FG     = (220, 220, 255)


# ---------------------------------------------------------------------------
# PDF class
# ---------------------------------------------------------------------------
class AuditPDF(FPDF):
    def __init__(self):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.set_auto_page_break(auto=True, margin=20)
        self.set_margins(left=18, top=18, right=18)
        self._toc_entries = []   # (level, title, page)
        self._current_section = ""

    # ------------------------------------------------------------------
    # Header / Footer
    # ------------------------------------------------------------------
    def header(self):
        if self.page_no() == 1:
            return
        self.set_fill_color(*BRAND_DARK)
        self.rect(0, 0, 210, 10, "F")
        self.set_font("Helvetica", "B", 8)
        self.set_text_color(200, 200, 220)
        self.set_xy(18, 2)
        self.cell(0, 6, "Axelar CGP Solidity -- Security Audit Report  |  Confidential",
                  new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_text_color(*BRAND_DARK)

    def footer(self):
        self.set_y(-14)
        self.set_draw_color(*MID_GRAY)
        self.line(18, self.get_y(), 192, self.get_y())
        self.set_font("Helvetica", "", 8)
        self.set_text_color(120, 120, 130)
        self.cell(0, 8, f"Page {self.page_no()}  |  Generated {date.today().isoformat()}",
                  align="C")

    # ------------------------------------------------------------------
    # Cover page
    # ------------------------------------------------------------------
    def cover_page(self):
        self.add_page()
        # Full-bleed header block
        self.set_fill_color(*BRAND_DARK)
        self.rect(0, 0, 210, 80, "F")

        # Shield / logo placeholder
        self.set_fill_color(*BRAND_BLUE)
        self.rect(85, 18, 40, 40, "F")
        self.set_font("Helvetica", "B", 22)
        self.set_text_color(255, 255, 255)
        self.set_xy(85, 26)
        self.cell(40, 10, "0xCON", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_xy(85, 38)
        self.cell(40, 10, "AUDIT", align="C")

        # Title
        self.set_xy(18, 88)
        self.set_font("Helvetica", "B", 26)
        self.set_text_color(*BRAND_DARK)
        self.cell(0, 12, "Security Audit Report", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        self.set_font("Helvetica", "", 14)
        self.set_text_color(60, 60, 80)
        self.cell(0, 8, "Axelar Cross-chain Gateway Protocol (CGP) Solidity",
                  new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(4)

        # Meta table
        meta = [
            ("Repository",    "Kushmanmb/axelar-cgp-silly-files"),
            ("Audit Version", "1.0.0"),
            ("Date",          "2026-03-17"),
            ("Auditors",      "0xCon Automated + Manual Review"),
            ("Scope",         "contracts/ (excl. contracts/test/)"),
            ("Compiler",      "Solidity 0.8.9 / ^0.8.0"),
        ]
        self.ln(4)
        for key, val in meta:
            self.set_fill_color(*LIGHT_GRAY)
            self.set_font("Helvetica", "B", 10)
            self.set_text_color(*BRAND_DARK)
            self.cell(48, 8, f"  {key}", border=0, fill=True)
            self.set_font("Helvetica", "", 10)
            self.set_text_color(40, 40, 60)
            self.cell(0, 8, f"  {val}", border=0,
                      new_x=XPos.LMARGIN, new_y=YPos.NEXT, fill=True)
            self.ln(1)

        # Summary boxes
        self.ln(10)
        severities = [
            ("Critical", "0",  (180, 0, 0)),
            ("High",     "3",  (220, 60, 0)),
            ("Medium",   "4",  (210, 130, 0)),
            ("Low",      "5",  (40, 120, 200)),
            ("Info",     "4",  (80, 80, 80)),
        ]
        box_w = 33
        x_start = 18
        for i, (sev, cnt, color) in enumerate(severities):
            x = x_start + i * (box_w + 2)
            self.set_fill_color(*color)
            self.rect(x, self.get_y(), box_w, 18, "F")
            self.set_xy(x, self.get_y() + 2)
            self.set_font("Helvetica", "B", 16)
            self.set_text_color(255, 255, 255)
            self.cell(box_w, 8, cnt, align="C")
            self.set_xy(x, self.get_y() + 8)
            self.set_font("Helvetica", "", 8)
            self.cell(box_w, 6, sev, align="C")
        self.ln(30)

        # Disclaimer stripe
        self.set_fill_color(255, 240, 200)
        self.set_draw_color(220, 160, 0)
        self.rect(18, self.get_y(), 174, 14, "FD")
        self.set_xy(22, self.get_y() + 2)
        self.set_font("Helvetica", "BI", 9)
        self.set_text_color(120, 80, 0)
        self.multi_cell(
            166, 5,
            "This report is for informational purposes only and does not constitute a warranty "
            "of security. No critical vulnerabilities were found.",
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def section_title(self, number, title, level=1):
        self.ln(6)
        if level == 1:
            self.set_fill_color(*BRAND_BLUE)
            self.rect(18, self.get_y(), 174, 0.6, "F")
            self.ln(3)
            self.set_font("Helvetica", "B", 14)
            self.set_text_color(*BRAND_BLUE)
            label = f"{number}  {title}"
        else:
            self.set_font("Helvetica", "B", 11)
            self.set_text_color(*BRAND_DARK)
            label = f"{number}  {title}"

        self.cell(0, 8, label, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self._toc_entries.append((level, label, self.page_no()))
        self.set_text_color(*BRAND_DARK)
        self.ln(2)

    def severity_badge(self, severity: str):
        sev_lower = severity.lower()
        color = SEVERITY_COLORS.get(sev_lower, (100, 100, 100))
        self.set_fill_color(*color)
        self.set_text_color(255, 255, 255)
        self.set_font("Helvetica", "B", 8)
        self.cell(22, 6, severity.upper(), align="C", fill=True, border=0)
        self.set_text_color(*BRAND_DARK)

    def body_text(self, text: str, indent: int = 0):
        self.set_font("Helvetica", "", 10)
        self.set_text_color(40, 40, 60)
        if indent:
            self.set_x(self.l_margin + indent)
        lines = text.strip().split("\n")
        for line in lines:
            line = line.rstrip()
            if not line:
                self.ln(3)
                continue
            # Wrap long lines
            wrapped = textwrap.wrap(line, width=90) or [""]
            for wl in wrapped:
                if indent:
                    self.set_x(self.l_margin + indent)
                self.cell(0, 5, wl, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(2)

    def code_block(self, code: str):
        self.ln(2)
        lines = code.strip().split("\n")
        h_per_line = 5
        block_h = len(lines) * h_per_line + 6
        x0, y0 = self.get_x(), self.get_y()

        # Background
        self.set_fill_color(*CODE_BG)
        self.rect(18, y0, 174, block_h, "F")

        self.set_xy(22, y0 + 3)
        self.set_font("Courier", "", 8)
        self.set_text_color(*CODE_FG)
        for line in lines:
            self.set_x(22)
            self.cell(0, h_per_line, line[:100], new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_text_color(*BRAND_DARK)
        self.ln(4)

    def table_row(self, cells, widths, header=False):
        fill = BRAND_DARK if header else None
        self.set_fill_color(*(BRAND_DARK if header else LIGHT_GRAY))
        self.set_font("Helvetica", "B" if header else "", 9)
        self.set_text_color(255 if header else 40, 255 if header else 40, 255 if header else 60)
        for cell, w in zip(cells, widths):
            self.cell(w, 7, f" {cell}", border=0, fill=True)
        self.ln()
        self.set_text_color(*BRAND_DARK)

    def horizontal_rule(self):
        self.set_draw_color(*MID_GRAY)
        self.line(18, self.get_y(), 192, self.get_y())
        self.ln(3)


# ---------------------------------------------------------------------------
# Markdown -> PDF renderer  (simplified -- handles key patterns only)
# ---------------------------------------------------------------------------
def render_md_to_pdf(pdf: AuditPDF, md_text: str):
    in_code = False
    code_buf = []
    in_table = False
    table_header_done = False
    table_widths = []

    lines = md_text.split("\n")
    i = 0

    # Skip the H1 title -- rendered on cover page
    while i < len(lines) and not lines[i].startswith("## "):
        i += 1

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Fenced code blocks
        if stripped.startswith("```"):
            if not in_code:
                in_code = True
                code_buf = []
            else:
                in_code = False
                pdf.code_block("\n".join(code_buf))
                code_buf = []
            i += 1
            continue

        if in_code:
            code_buf.append(line.rstrip())
            i += 1
            continue

        # H2
        if line.startswith("## "):
            title = line[3:].strip()
            match = re.match(r"^(\d+)\.\s+(.*)", title)
            if match:
                num, rest = match.group(1), match.group(2)
                # Strip markdown links like [foo](#bar)
                rest = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", rest)
                pdf.section_title(num + ".", rest, level=1)
            else:
                pdf.section_title("", title, level=1)
            i += 1
            continue

        # H3
        if line.startswith("### "):
            title = line[4:].strip()
            # Parse finding ID and title
            pdf.section_title("", title, level=2)
            i += 1
            continue

        # H4 -- treat as bold paragraph
        if line.startswith("#### "):
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(*BRAND_DARK)
            pdf.cell(0, 6, line[5:].strip(), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.set_font("Helvetica", "", 10)
            i += 1
            continue

        # Horizontal rule
        if stripped.startswith("---"):
            pdf.horizontal_rule()
            i += 1
            continue

        # Tables
        if stripped.startswith("|"):
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            if not in_table:
                in_table = True
                table_header_done = False
                # Guess widths proportionally
                n = len(cells)
                table_widths = [int(174 / n)] * n
                # make last column absorb remainder
                table_widths[-1] = 174 - sum(table_widths[:-1])
                pdf.table_row(cells, table_widths, header=True)
                table_header_done = True
            elif all(c.startswith("-") or c == "" for c in cells):
                # Separator row -- skip
                pass
            else:
                pdf.table_row(cells, table_widths, header=False)
            i += 1
            continue
        else:
            if in_table:
                in_table = False
                table_header_done = False
                pdf.ln(2)

        # Bullet / list
        if stripped.startswith("- ") or stripped.startswith("* "):
            content = stripped[2:]
            content = re.sub(r"\*\*([^*]+)\*\*", r"\1", content)  # strip bold
            content = re.sub(r"`([^`]+)`", r"\1", content)          # strip code
            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(40, 40, 60)
            pdf.set_x(pdf.l_margin + 4)
            pdf.cell(4, 5, chr(149))  # bullet
            pdf.cell(0, 5, content[:110], new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            i += 1
            continue

        # Bold **Severity:** badge detection
        sev_match = re.match(r"\*\*Severity:\*\*\s+(\w+)", stripped)
        if sev_match:
            sev = sev_match.group(1)
            pdf.set_x(pdf.l_margin)
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(*BRAND_DARK)
            pdf.cell(28, 6, "Severity:")
            pdf.severity_badge(sev)
            pdf.ln(8)
            i += 1
            continue

        # Bold key: value lines
        bold_match = re.match(r"\*\*([^*]+):\*\*\s+(.*)", stripped)
        if bold_match:
            key, val = bold_match.group(1), bold_match.group(2)
            val = re.sub(r"`([^`]+)`", r"\1", val)
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(*BRAND_DARK)
            pdf.cell(38, 5, f"{key}:")
            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(40, 40, 60)
            pdf.cell(0, 5, val[:120], new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            i += 1
            continue

        # Empty line
        if not stripped:
            pdf.ln(2)
            i += 1
            continue

        # Normal paragraph text -- strip inline markdown
        text = stripped
        text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
        text = re.sub(r"`([^`]+)`", r"\1", text)
        text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
        pdf.body_text(text)
        i += 1


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main():
    if not os.path.isfile(AUDIT_MD):
        print(f"ERROR: {AUDIT_MD} not found. Run from the repo root.", file=sys.stderr)
        sys.exit(1)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    with open(AUDIT_MD, encoding="utf-8") as fh:
        md_text = fh.read()

    pdf = AuditPDF()

    # Cover page
    pdf.cover_page()

    # Main content
    pdf.add_page()
    render_md_to_pdf(pdf, md_text)

    pdf.output(OUTPUT_PDF)
    size_kb = os.path.getsize(OUTPUT_PDF) // 1024
    print(f"Generated: {OUTPUT_PDF}  ({size_kb} KB)")


if __name__ == "__main__":
    main()
