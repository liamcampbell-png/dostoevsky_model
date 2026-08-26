#!/usr/bin/env python3
"""
build_corpus.py

Cleans and merges Project Gutenberg .txt editions of Dostoevsky's works
into a single plain-text corpus suitable for training on his prose style.

What this does:
  1. Strips Project Gutenberg license header/footer boilerplate.
  2. Strips chapter/part/book headers (CHAPTER I, PART ONE, bare roman
     numeral section breaks, etc).
  3. Strips footnote markers ([1], [2], *, etc), [Illustration] tags,
     and standalone page-number lines.
  4. Leaves the actual prose (quotes, dashes, paragraph text) completely
     untouched — no normalization, no case changes, no punctuation
     stripping.
  5. Cleans up only blank-line runs and trailing whitespace between
     paragraphs (not within them).
  6. Concatenates all cleaned books into one corpus file, separated by
     lightweight `=== TITLE ===` markers so provenance is preserved.

Usage:
    python build_corpus.py --input ./books --output ./dostoevsky_corpus.txt

Input: a folder of .txt files, one per book, as downloaded from
       Project Gutenberg (predictable filenames, e.g. crime_and_punishment.txt)
"""

import argparse
import re
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# 1. Gutenberg boilerplate stripping
# ---------------------------------------------------------------------------

# Gutenberg has used a few slightly different marker formats over the years.
# These regexes cover old and new styles.
START_MARKERS = [
    r"\*\*\*\s*START OF (THE|THIS) PROJECT GUTENBERG EBOOK.*?\*\*\*",
    r"\*\*\*START OF (THE|THIS) PROJECT GUTENBERG EBOOK.*?\*\*\*",
]
END_MARKERS = [
    r"\*\*\*\s*END OF (THE|THIS) PROJECT GUTENBERG EBOOK.*?\*\*\*",
    r"\*\*\*END OF (THE|THIS) PROJECT GUTENBERG EBOOK.*?\*\*\*",
]


def strip_boilerplate(text: str) -> str:
    """Keep only the text between the START and END Gutenberg markers."""
    start_idx = None
    for pattern in START_MARKERS:
        m = re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL)
        if m:
            start_idx = m.end()
            break

    end_idx = None
    for pattern in END_MARKERS:
        m = re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL)
        if m:
            end_idx = m.start()
            break

    if start_idx is None or end_idx is None:
        # Markers not found in expected form — bail out loudly rather than
        # silently including license text in the corpus.
        raise ValueError(
            "Could not find Gutenberg START/END markers. "
            "Check this file's formatting manually."
        )

    return text[start_idx:end_idx]


# ---------------------------------------------------------------------------
# 2. Chapter / part / book header stripping
# ---------------------------------------------------------------------------

# Lines that are ONLY a header, nothing else on the line.
CHAPTER_HEADER_PATTERNS = [
    r"^\s*CHAPTER\s+[IVXLCDM0-9]+\.?\s*$",
    r"^\s*Chapter\s+[IVXLCDM0-9]+\.?\s*$",
    r"^\s*PART\s+(ONE|TWO|THREE|FOUR|FIVE|SIX|SEVEN|EIGHT|[IVXLCDM]+)\.?\s*$",
    r"^\s*Part\s+(One|Two|Three|Four|Five|Six|Seven|Eight|[IVXLCDM]+)\.?\s*$",
    r"^\s*BOOK\s+(THE\s+)?(FIRST|SECOND|THIRD|FOURTH|FIFTH|SIXTH|[IVXLCDM]+)\.?\s*$",
    r"^\s*Book\s+(the\s+)?(First|Second|Third|Fourth|Fifth|Sixth|[IVXLCDM]+)\.?\s*$",
    r"^\s*EPILOGUE\.?\s*$",
    r"^\s*Epilogue\.?\s*$",
]

# A bare roman numeral alone on its own line (common section-break style
# in these translations), e.g. a line containing only "I", "II", "III"...
BARE_ROMAN_NUMERAL = re.compile(r"^\s*[IVXLCDM]{1,6}\.?\s*$")


def is_chapter_header(line: str, prev_blank: bool, next_blank: bool) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    for pattern in CHAPTER_HEADER_PATTERNS:
        if re.match(pattern, stripped, flags=re.IGNORECASE):
            return True
    # Only treat a bare roman numeral as a header if it's isolated by
    # blank lines on both sides (avoids eating a stray "I" inside dialogue).
    if BARE_ROMAN_NUMERAL.match(stripped) and prev_blank and next_blank:
        return True
    return False


# ---------------------------------------------------------------------------
# 3. Footnotes, illustrations, page numbers
# ---------------------------------------------------------------------------

FOOTNOTE_MARKER = re.compile(r"\[\d+\]")           # inline [1], [2]...
ILLUSTRATION_LINE = re.compile(r"^\s*\[Illustration.*?\]\s*$", re.IGNORECASE)
STANDALONE_PAGE_NUMBER = re.compile(r"^\s*\d{1,4}\s*$")


def strip_noise(text: str) -> str:
    text = FOOTNOTE_MARKER.sub("", text)

    lines = text.split("\n")
    cleaned_lines = []
    for line in lines:
        if ILLUSTRATION_LINE.match(line):
            continue
        if STANDALONE_PAGE_NUMBER.match(line):
            continue
        cleaned_lines.append(line)
    return "\n".join(cleaned_lines)


# ---------------------------------------------------------------------------
# 4. Remove chapter headers, collapse blank-line runs, strip trailing WS
# ---------------------------------------------------------------------------

def clean_structure(text: str) -> str:
    lines = text.split("\n")
    n = len(lines)

    def is_blank(i):
        return i < 0 or i >= n or lines[i].strip() == ""

    kept = []
    for i, line in enumerate(lines):
        if is_chapter_header(line, is_blank(i - 1), is_blank(i + 1)):
            continue
        kept.append(line.rstrip())  # strip trailing whitespace only

    # Collapse 2+ consecutive blank lines down to exactly one blank line
    # (i.e. a single paragraph break). Does not touch text within paragraphs.
    collapsed = []
    blank_run = 0
    for line in kept:
        if line.strip() == "":
            blank_run += 1
            if blank_run <= 1:
                collapsed.append(line)
        else:
            blank_run = 0
            collapsed.append(line)

    return "\n".join(collapsed).strip("\n") + "\n"


# ---------------------------------------------------------------------------
# 5. Per-file pipeline + merge
# ---------------------------------------------------------------------------

def clean_book(raw_text: str) -> str:
    text = strip_boilerplate(raw_text)
    text = strip_noise(text)
    text = clean_structure(text)
    return text


def title_from_filename(path: Path) -> str:
    return path.stem.replace("_", " ").replace("-", " ").title()


def build_corpus(input_dir: Path, output_path: Path) -> None:
    txt_files = sorted(input_dir.glob("*.txt"))
    if not txt_files:
        print(f"No .txt files found in {input_dir}", file=sys.stderr)
        sys.exit(1)

    total_words = 0
    with open(output_path, "w", encoding="utf-8") as out:
        for i, path in enumerate(txt_files):
            print(f"Processing: {path.name}")
            try:
                raw = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                raw = path.read_text(encoding="latin-1")

            try:
                cleaned = clean_book(raw)
            except ValueError as e:
                print(f"  SKIPPED ({e})", file=sys.stderr)
                continue

            title = title_from_filename(path)
            word_count = len(cleaned.split())
            total_words += word_count
            print(f"  {word_count:,} words")

            if i > 0:
                out.write("\n\n")
            out.write(f"=== {title} ===\n\n")
            out.write(cleaned)

    print(f"\nDone. Wrote corpus to {output_path}")
    print(f"Total words: {total_words:,}")


# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Folder of Gutenberg .txt files")
    parser.add_argument("--output", required=True, help="Path for merged corpus .txt")
    args = parser.parse_args()

    input_dir = Path(args.input)
    output_path = Path(args.output)

    if not input_dir.is_dir():
        print(f"Input folder not found: {input_dir}", file=sys.stderr)
        sys.exit(1)

    build_corpus(input_dir, output_path)


if __name__ == "__main__":
    main()
    