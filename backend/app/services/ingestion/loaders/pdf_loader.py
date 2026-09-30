"""
backend/app/services/ingestion/loaders/pdf_loader.py

Extracts and splits cases from Cassation Court PDFs.
"""
import re
import pdfplumber

DIGIT_CLASS = r"[0-9ዐ]"

class CassationPDFLoader:
    def __init__(self):
        # Regex patterns adapted from extract_cases_fixed.py
        self.toc_case_pattern = re.compile(rf"\b({DIGIT_CLASS}{{5,6}})\b")
        self.header_pattern = re.compile(
            rf"(?:የ)?ሰ\s*[/.]\s*መ\s*[/.]\s*ቁ(?:ጥር)?[\s.:\-/]*({DIGIT_CLASS}{{5,6}})"
            rf"|የሰበር\s*መዝገብ\s*ቁጥር[\s.:\-]*({DIGIT_CLASS}{{5,6}})"
        )

    def normalize_case_number(self, raw: str) -> str:
        return raw.replace("ዐ", "0")

    def load_and_split(self, pdf_path: str, volume_number: int, toc_end_page: int) -> list[dict]:
        """
        Reads the PDF, splits it by case heading, and returns a list of case dictionaries 
        ready to be chunked and embedded (replaces Phase 4 JSON saving).
        """
        toc_metadata = {}
        full_body_parts = []
        page_char_map = []
        current_offset = 0

        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)

            # Phase 1: TOC Extraction (Pages 3-32)
            # (Assuming volume 15 structure for this example)
            current_category = "አጠቃላይ ፍትሐብሔር"
            
            for pno in range(3, min(toc_end_page, total_pages)):
                page_text = pdf.pages[pno].extract_text() or ""
                # Add logic here from extract_cases_fixed.py to populate toc_metadata...

            # Phase 2: Extract Body Text (Pages 33+)
            for pno in range(32, total_pages):
                printed_page = pno - 31
                p_text = (pdf.pages[pno].extract_text() or "") + "\n"
                full_body_parts.append(p_text)

                page_char_map.append({
                    "page": printed_page,
                    "start": current_offset,
                    "end": current_offset + len(p_text)
                })
                current_offset += len(p_text)

            full_body = "".join(full_body_parts)

        # Phase 3: Split by case heading
        raw_matches = list(self.header_pattern.finditer(full_body))
        matches = [m for m in raw_matches if "ዳኞች" in full_body[m.end(): m.end() + 200]]

        def get_page_number(char_idx):
            for entry in page_char_map:
                if entry["start"] <= char_idx < entry["end"]:
                    return entry["page"]
            return 1

        final_cases = []

        # Phase 4: Create Case Objects (Replaces JSON dumping)
        for i, match in enumerate(matches):
            case_number = self.normalize_case_number(match.group(1) or match.group(2))
            start_pos = match.start()
            end_pos = matches[i + 1].start() if i + 1 < len(matches) else len(full_body)

            start_page = get_page_number(start_pos)
            end_page = get_page_number(end_pos - 1)
            page_range_str = f"ገጽ {start_page}-{end_page}" if end_page > start_page else f"ገጽ {start_page}"

            meta = toc_metadata.get(case_number, {})

            # Instead of writing to a file, append to a list in memory!
            final_cases.append({
            "case_number": case_number,
            "volume": volume_number,  # <--- Now it uses the dynamic volume
            "legal_category": meta.get("legal_category", "አጠቃላይ ፍትሐብሔር"),
            "page_range": page_range_str,
            "context": full_body[start_pos:end_pos].strip()
        })

        return final_cases