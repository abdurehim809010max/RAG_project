"""
backend/app/services/ingestion/parser.py

Extracts Ethiopian Cassation Court metadata from raw document text.
"""
import re

class CassationParser:
    def __init__(self):
        # Regex patterns adapted from scratch_archive/parser_fixed.py
        self.case_no_pattern = re.compile(r"መዝገብ\s*ቁጥር[:\-\s]*(\d{4,6})")
        self.volume_pattern = re.compile(r"ቅጽ\s*(\d{1,3})")
        self.category_pattern = re.compile(r"ጉዳዩ[:\-\s]*([^\n]+)")
        
    def extract_metadata(self, text: str, default_volume: int = 15) -> dict:
        """Parses the text chunk to find legal metadata."""
        
        # Extract Case Number
        case_match = self.case_no_pattern.search(text)
        case_number = case_match.group(1) if case_match else "Unknown"
        
        # Extract Volume
        vol_match = self.volume_pattern.search(text)
        volume = int(vol_match.group(1)) if vol_match else default_volume
        
        # Extract Category
        cat_match = self.category_pattern.search(text)
        legal_category = cat_match.group(1).strip() if cat_match else "ጠቅላላ ሕግ"
        
        # In a real PDF loader, page ranges are tracked per page during extraction.
        # Here we provide a fallback for plain text uploads.
        return {
            "case_number": case_number,
            "volume": volume,
            "legal_category": legal_category,
            "page_range": "N/A" 
        }