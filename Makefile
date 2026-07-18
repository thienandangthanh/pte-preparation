# Build DIC-ACA-06-07-2026.pdf from the source spreadsheet.
# Pipeline: .xlsx --(extract-xlsx-to-csv.py)--> .csv --(generate-tex.py)--> .tex --(xelatex)--> .pdf
# Each step re-runs only when its prerequisites are newer (standard make timestamp logic).

NAME       := DIC-ACA-06-07-2026
PYTHON     := python3
XELATEX    := xelatex
LATEXFLAGS := -interaction=nonstopmode -halt-on-error

.PHONY: all clean

all: $(NAME).pdf

# Spreadsheet -> semicolon CSV (stdlib extractor, no external deps).
$(NAME).csv: $(NAME).xlsx extract-xlsx-to-csv.py
	$(PYTHON) extract-xlsx-to-csv.py --xlsx $< --out $@

# CSV -> LaTeX table (#, SENTENCE, MEANING).
$(NAME).tex: $(NAME).csv generate-tex.py
	$(PYTHON) generate-tex.py --csv $< --out $@

# LaTeX -> PDF in the project root. Two passes: longtable needs a rerun to
# settle column widths and page breaks.
$(NAME).pdf: $(NAME).tex
	$(XELATEX) $(LATEXFLAGS) $<
	$(XELATEX) $(LATEXFLAGS) $<

# Remove throwaway LaTeX auxiliary files (kept out of git via .gitignore).
# Leaves the .csv/.tex/.pdf deliverables in place.
clean:
	rm -f $(NAME).aux $(NAME).log $(NAME).out
