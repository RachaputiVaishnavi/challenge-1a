import fitz  # PyMuPDF
import os
import json
from collections import defaultdict, Counter
import re
import unicodedata

# ========== CONFIGURABLE PARAMETERS ==========
BUFFER_SIZE = 10  # Buffer around table for exclusion
VERTICAL_TOLERANCE = 5  # Merge tolerance for lines
MIN_HEADING_LEN = 2  # Lower for some languages
MAX_HEADING_CHARS = 120  # Instead of word limit for multilingual

# ---------- Normalize and validate heading ----------
def normalize_text(text):
    return unicodedata.normalize("NFC", text.strip())

def is_valid_heading(text):
    text = normalize_text(text)
    if not text or len(text) < MIN_HEADING_LEN:
        return False
    if all(c in ".·•-_" for c in text):  # Dotted/line filler
        return False
    if re.match(r"^(Page\s+\d+|May\s+\d{1,2},\s+\d{4}|Version\s+\d{4})$", text.strip(), re.IGNORECASE):
        return False
    if len(text) > MAX_HEADING_CHARS:
        return False
    # Remove only time/date formats for any language (safe check)
    if re.match(r"^\d{1,2}:\d{2}\s*(AM|PM|a\.m\.|p\.m\.)$", text, re.IGNORECASE):
        return False
    if re.match(r"^\d{1,2}/\d{1,2}/\d{4}$", text):
        return False
    return True

# ---------- Extract text spans excluding tables ----------
def extract_spans(doc):
    spans_by_page = defaultdict(list)

    for page_num in range(len(doc)):
        page = doc[page_num]
        blocks = page.get_text("dict")["blocks"]

        # Detect tables and their bounding boxes with buffer
        table_bboxes = []
        for table in page.find_tables():
            if table.bbox:
                x0, y0, x1, y1 = table.bbox
                buffered_bbox = fitz.Rect(x0 - BUFFER_SIZE, y0 - BUFFER_SIZE, x1 + BUFFER_SIZE, y1 + BUFFER_SIZE)
                table_bboxes.append(buffered_bbox)

        for block in blocks:
            if "lines" not in block or block.get("type") == 1:  # Skip images
                continue

            for line in block["lines"]:
                for span in line["spans"]:
                    text = normalize_text(span["text"])
                    if not is_valid_heading(text):
                        continue

                    span_bbox = fitz.Rect(span["bbox"])
                    # Skip if span overlaps with any table
                    if any(span_bbox.intersects(tb) for tb in table_bboxes):
                        continue

                    spans_by_page[page_num].append({
                        "text": text,
                        "font_size": round(span["size"], 1),
                        "is_bold": bool(span["flags"] & 2),
                        "bbox": span["bbox"],
                        "page": page_num
                    })

    return spans_by_page

# ---------- Extract Title (largest font at top) ----------
def extract_title(spans_page0):
    if not spans_page0:
        return "", []

    spans_page0.sort(key=lambda s: (-s["font_size"], s["bbox"][1]))  # Sort by font size desc, then top position
    max_size = spans_page0[0]["font_size"]
    title_spans = [s for s in spans_page0 if s["font_size"] == max_size]

    # Merge top-most title spans
    title_spans.sort(key=lambda s: (s["bbox"][1], s["bbox"][0]))
    lines = []
    current_line = ""
    prev_bottom = None

    for span in title_spans:
        top = span["bbox"][1]
        if prev_bottom is not None and abs(top - prev_bottom) > VERTICAL_TOLERANCE:
            lines.append(current_line.strip())
            current_line = ""
        current_line += " " + span["text"]
        prev_bottom = span["bbox"][3]
    if current_line.strip():
        lines.append(current_line.strip())

    title_text = " ".join(lines).strip()

    # ✅ Validate title (remove if only symbols or too short)
    if not title_text or len(title_text) < MIN_HEADING_LEN or re.match(r"^[\W_]+$", title_text):
        return "", []

    return title_text, title_spans

# ---------- Assign heading levels (H1, H2, H3) ----------
def assign_heading_levels(spans_by_page, title_lines):
    all_spans = []
    for spans in spans_by_page.values():
        all_spans.extend(spans)

    # Remove title spans
    title_texts = set(s["text"] for s in title_lines)
    filtered_spans = [s for s in all_spans if s["text"] not in title_texts]

    if not filtered_spans:
        return []

    size_counter = Counter([s["font_size"] for s in filtered_spans])
    sorted_sizes = sorted(size_counter.keys(), reverse=True)

    h1_size = sorted_sizes[0] if len(sorted_sizes) > 0 else 0
    h2_size = sorted_sizes[1] if len(sorted_sizes) > 1 else h1_size - 1
    h3_size = sorted_sizes[2] if len(sorted_sizes) > 2 else h2_size - 1

    headings = []
    for s in filtered_spans:
        level = None
        if s["font_size"] == h1_size and s["is_bold"]:
            level = "H1"
        elif s["font_size"] == h2_size:
            level = "H2"
        elif s["font_size"] == h3_size:
            level = "H3"

        if level and is_valid_heading(s["text"]):
            headings.append({
                "level": level,
                "text": s["text"],
                "page": s["page"]
            })

    # Remove duplicates
    seen = set()
    unique_headings = []
    for h in headings:
        key = (h["level"], h["text"], h["page"])
        if key not in seen:
            seen.add(key)
            unique_headings.append(h)

    unique_headings.sort(key=lambda x: (x["page"], {"H1": 1, "H2": 2, "H3": 3}[x["level"]]))
    return unique_headings

# ---------- Main extraction ----------
def extract_outline_from_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    spans_by_page = extract_spans(doc)

    page0_spans = spans_by_page.get(0, [])
    title, title_lines = extract_title(page0_spans)
    outline = assign_heading_levels(spans_by_page, title_lines)

    return {
        "title": title,
        "outline": outline
    }

# ---------- Main Runner ----------
def main():
    input_dir = "input"
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)

    pdf_files = [f for f in os.listdir(input_dir) if f.lower().endswith(".pdf")]

    if not pdf_files:
        print("⚠ No PDF files found in 'input/' folder.")
        return

    for pdf_file in pdf_files:
        input_path = os.path.join(input_dir, pdf_file)
        output_path = os.path.join(output_dir, pdf_file.replace(".pdf", ".json"))

        print(f"📄 Processing: {pdf_file}")
        result = extract_outline_from_pdf(input_path)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        print(f"✅ Saved to: {output_path}")

if _name_ == "_main_":
    main()
