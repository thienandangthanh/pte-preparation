#!/usr/bin/env python3
"""Convert dictation-list.csv -> dictation-list.tex (A4, single column, printable).
Keeps only SENTENCE and MEANING (plus a small index for reference)."""
import argparse
import csv
from pathlib import Path

DEFAULT_CSV = Path(__file__).parent / "dictation-list.csv"
DEFAULT_OUT = Path(__file__).parent / "dictation-list.tex"

# LaTeX special-character escaping (text mode, XeLaTeX/unicode)
_ESCAPE = {
    "\\": r"\textbackslash{}",
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
}


def escape(text: str) -> str:
    out = []
    for ch in text.strip():
        out.append(_ESCAPE.get(ch, ch))
    return "".join(out)


def load_rows(src):
    with src.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            sentence = (row.get("SENTENCE") or "").strip()
            meaning = (row.get("MEANING") or "").strip()
            if not sentence and not meaning:
                continue
            yield sentence, meaning


PREAMBLE = r"""\documentclass[11pt,a4paper]{article}
\usepackage{fontspec}
\setmainfont{Noto Serif}
\usepackage[a4paper,margin=1.8cm]{geometry}
\usepackage{longtable}
\usepackage{array}
\usepackage{xcolor}
\usepackage{booktabs}
\renewcommand{\arraystretch}{1.35}

% Alternating row shading for readability
\usepackage{colortbl}
\definecolor{rowgray}{gray}{0.93}

\setlength{\parindent}{0pt}
\setlength{\LTpre}{0pt}
\setlength{\LTpost}{0pt}

\begin{document}

\begin{center}
{\LARGE\bfseries PTE Write From Dictation}\\[2pt]
{\large Sentence \& Meaning Study List}
\end{center}
\vspace{0.6em}

% Column widths: index | English sentence | Vietnamese meaning
\newcolumntype{N}{>{\centering\arraybackslash}m{0.7cm}}
\newcolumntype{S}{>{\raggedright\arraybackslash}m{7.6cm}}
\newcolumntype{M}{>{\raggedright\arraybackslash}m{7.6cm}}

\begin{longtable}{N S M}
\toprule
\textbf{\#} & \textbf{SENTENCE} & \textbf{MEANING} \\
\midrule
\endfirsthead
\multicolumn{3}{l}{\itshape\small Continued from previous page}\\
\toprule
\textbf{\#} & \textbf{SENTENCE} & \textbf{MEANING} \\
\midrule
\endhead
\midrule
\multicolumn{3}{r}{\itshape\small Continued on next page}\\
\endfoot
\bottomrule
\endlastfoot
"""

FOOTER = r"""\end{longtable}

\end{document}
"""


def main():
    parser = argparse.ArgumentParser(description="Convert a dictation CSV to a printable LaTeX table.")
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV, help="Source CSV path")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="Output .tex path")
    args = parser.parse_args()

    rows = list(load_rows(args.csv))
    lines = [PREAMBLE]
    for i, (sentence, meaning) in enumerate(rows, start=1):
        shade = r"\rowcolor{rowgray}" if i % 2 == 0 else ""
        lines.append(
            f"{shade}{i} & {escape(sentence)} & {escape(meaning)} \\\\"
        )
    lines.append(FOOTER)
    args.out.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {args.out} with {len(rows)} entries.")


if __name__ == "__main__":
    main()
