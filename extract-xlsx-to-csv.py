#!/usr/bin/env python3
"""Extract a dictation sheet from an .xlsx workbook into a semicolon CSV.

Mirrors the format of dictation-list.csv (header STT;CODE;Đã thuộc;SENTENCE;MEANING,
UTF-8 with BOM) so the output is a drop-in source for generate-tex.py and generate-audio.py.

Reads the workbook with only the Python standard library (zipfile + ElementTree) — no
openpyxl/pandas dependency. Cells exported from Google Sheets keep their formula plus a
cached value; the cached string is what gets extracted.

Usage:
    python extract-xlsx-to-csv.py                        # DIC-ACA-06-07-2026.xlsx -> .csv
    python extract-xlsx-to-csv.py --xlsx other.xlsx --out other.csv --sheet Sheet1
"""
import argparse
import csv
import re
import sys
import zipfile
import xml.etree.ElementTree as ET  # input is a local, user-authored workbook (trusted)
from pathlib import Path

ROOT = Path(__file__).parent
DEFAULT_XLSX = ROOT / "DIC-ACA-06-07-2026.xlsx"
DEFAULT_OUT = ROOT / "DIC-ACA-06-07-2026.csv"
DEFAULT_SHEET = "Sheet1"

# OOXML namespaces
NS_MAIN = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
NS_REL = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"

# Output columns (fixed order matching dictation-list.csv). Source data columns are the
# first four spreadsheet columns: A=STT, B=Question ID, C=Sentence, D=Meaning.
HEADER = ["STT", "CODE", "Đã thuộc", "SENTENCE", "MEANING"]


def _cell_text(cell: ET.Element, shared: list[str]) -> str:
    """Resolve a worksheet <c> cell to its display string."""
    ctype = cell.get("t")
    if ctype == "s":  # shared-string index
        v = cell.find(f"{NS_MAIN}v")
        return shared[int(v.text)] if v is not None and v.text else ""
    if ctype == "inlineStr":  # inline string
        istr = cell.find(f"{NS_MAIN}is")
        return "".join(t.text or "" for t in istr.iter(f"{NS_MAIN}t")) if istr is not None else ""
    # number, boolean, or formula string result: the cached value lives in <v>
    v = cell.find(f"{NS_MAIN}v")
    return v.text if v is not None and v.text is not None else ""


def _resolve_worksheet_path(zf: zipfile.ZipFile, sheet_name: str) -> str:
    """Map a sheet name to its worksheet XML path via the workbook relationships."""
    workbook = ET.fromstring(zf.read("xl/workbook.xml"))
    rid = None
    for sheet in workbook.iter(f"{NS_MAIN}sheet"):
        if sheet.get("name") == sheet_name:
            rid = sheet.get(f"{NS_REL}id")
            break
    if rid is None:
        names = [s.get("name") for s in workbook.iter(f"{NS_MAIN}sheet")]
        raise SystemExit(f"Sheet {sheet_name!r} not found. Available: {names}")
    rels = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
    for rel in rels:
        if rel.get("Id") == rid:
            target = (rel.get("Target") or "").lstrip("/")
            return target if target.startswith("xl/") else f"xl/{target}"
    raise SystemExit(f"Relationship {rid!r} for sheet {sheet_name!r} not found")


def load_rows(xlsx_path: Path, sheet_name: str):
    """Yield [STT, CODE, Đã thuộc, SENTENCE, MEANING] lists from the sheet's data rows."""
    with zipfile.ZipFile(xlsx_path) as zf:
        shared = []
        if "xl/sharedStrings.xml" in zf.namelist():
            sst = ET.fromstring(zf.read("xl/sharedStrings.xml"))
            shared = ["".join(t.text or "" for t in si.iter(f"{NS_MAIN}t")) for si in sst.findall(f"{NS_MAIN}si")]

        sheet = ET.fromstring(zf.read(_resolve_worksheet_path(zf, sheet_name)))
        for row in sheet.iter(f"{NS_MAIN}row"):
            cells = {}
            for cell in row.findall(f"{NS_MAIN}c"):
                col_match = re.match(r"[A-Z]+", cell.get("r", ""))
                if col_match is None:
                    continue
                cells[col_match.group(0)] = _cell_text(cell, shared).strip()
            if row.get("r") == "1":  # header row
                continue
            stt, code, sentence, meaning = (cells.get(c, "") for c in ("A", "B", "C", "D"))
            if not sentence and not meaning:  # skip trailing blank rows
                continue
            code = f"#{code}" if code and not code.startswith("#") else code
            yield [stt, code, "FALSE", sentence, meaning]


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract a dictation sheet to a semicolon CSV.")
    parser.add_argument("--xlsx", type=Path, default=DEFAULT_XLSX, help="Source .xlsx workbook")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="Output CSV path")
    parser.add_argument("--sheet", default=DEFAULT_SHEET, help="Sheet name to extract")
    args = parser.parse_args()

    rows = list(load_rows(args.xlsx, args.sheet))
    if not rows:
        print(f"No data rows found in {args.xlsx} sheet {args.sheet!r}", file=sys.stderr)
        return 1

    # utf-8-sig writes a BOM, matching dictation-list.csv; QUOTE_MINIMAL keeps plain rows
    # unquoted while safely quoting any value containing ';', '"', or a newline.
    with args.out.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f, delimiter=";", quoting=csv.QUOTE_MINIMAL)
        writer.writerow(HEADER)
        writer.writerows(rows)

    print(f"Wrote {args.out} with {len(rows)} entries.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
