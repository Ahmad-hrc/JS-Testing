"""Local file connector — reads documents from a local directory (dev/test)."""

import io
import logging
import os

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".txt", ".md", ".csv", ".pdf"}


class LocalFileConnector:
    """Reads text documents from a local folder path."""

    def __init__(self, folder_path: str) -> None:
        self.folder_path = folder_path

    def list_documents(self) -> list[str]:
        """Return list of document file paths."""
        if not os.path.isdir(self.folder_path):
            logger.warning("LocalFileConnector: folder not found: %s", self.folder_path)
            return []
        docs = []
        for fname in sorted(os.listdir(self.folder_path)):
            _, ext = os.path.splitext(fname)
            if ext.lower() in SUPPORTED_EXTENSIONS:
                docs.append(os.path.join(self.folder_path, fname))
        return docs

    def read_document(self, path: str) -> str:
        """Read and return document text content."""
        _, ext = os.path.splitext(path)
        try:
            if ext.lower() == ".pdf":
                return self._read_pdf(path)
            with open(path, encoding="utf-8") as f:
                return f.read()
        except Exception as exc:
            logger.error("Failed to read %s: %s", path, exc)
            return ""

    def _read_pdf(self, path: str) -> str:
        """Extract text from a PDF file using pypdf."""
        try:
            from pypdf import PdfReader  # type: ignore
        except ImportError:
            logger.error("pypdf is not installed — cannot read PDF files. Run: pip install pypdf")
            return ""

        try:
            reader = PdfReader(path)
            pages: list[str] = []
            for page in reader.pages:
                text = page.extract_text() or ""
                if text.strip():
                    pages.append(text)
            full_text = "\n\n".join(pages)
            logger.info("Extracted %d pages from PDF: %s", len(pages), os.path.basename(path))
            return full_text
        except Exception as exc:
            logger.error("Failed to parse PDF %s: %s", path, exc)
            return ""

    def fetch_all(self) -> list[tuple[str, str]]:
        """Return list of (filename, content) tuples for all documents."""
        results = []
        for path in self.list_documents():
            content = self.read_document(path)
            if content:
                results.append((os.path.basename(path), content))
        return results
