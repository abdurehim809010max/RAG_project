"""
backend/app/services/ingestion/loaders/text_loader.py

Reads simple .txt files and extracts metadata using the CassationParser.
"""
from backend.app.services.ingestion.parser import CassationParser

class TextLoader:
    def __init__(self):
        self.parser = CassationParser()

    def load(self, file_path: str, volume: int = 15) -> list[dict]:
        """Reads a text file and returns a standard case object."""
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()
            
        meta = self.parser.extract_metadata(text, default_volume=volume)
        
        # We return it as a list of 1 to match the PDF loader's format
        return [{
            "case_number": meta["case_number"],
            "volume": meta["volume"],
            "legal_category": meta["legal_category"],
            "page_range": "N/A",
            "context": text
        }]