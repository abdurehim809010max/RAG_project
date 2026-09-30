"""
backend/app/services/ingestion/loaders/docx_loader.py

Reads .docx files, extracts text by paragraph, and parses metadata.
"""
import docx
from backend.app.services.ingestion.parser import CassationParser

class DocxLoader:
    def __init__(self):
        self.parser = CassationParser()

    def load(self, file_path: str, volume: int = 15) -> list[dict]:
        """Reads a Word document and returns a standard case object."""
        doc = docx.Document(file_path)
        
        # Join all paragraphs with newlines
        text = "\n".join([para.text for para in doc.paragraphs])
        
        meta = self.parser.extract_metadata(text, default_volume=volume)
        
        return [{
            "case_number": meta["case_number"],
            "volume": meta["volume"],
            "legal_category": meta["legal_category"],
            "page_range": "N/A",
            "context": text
        }]