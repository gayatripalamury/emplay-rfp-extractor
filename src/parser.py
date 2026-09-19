"""PDF and HTML ingestion with page/source-preserving metadata."""
from dataclasses import dataclass
from pathlib import Path
from typing import List

from bs4 import BeautifulSoup


@dataclass(frozen=True)
class DocumentPage:
    source: str
    page: int
    text: str


def _parse_html_pages(file_path: Path) -> List[DocumentPage]:
    path = Path(file_path)
    try:
        html = path.read_text(encoding="utf-8", errors="ignore")
    except OSError as exc:
        raise OSError(f"Unable to read HTML document '{path}': {exc}") from exc
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "nav", "footer", "header", "noscript", "meta"]):
        tag.decompose()
    text = soup.get_text("\n", strip=True)
    return [DocumentPage(str(path), 1, text)] if text else []


def _parse_pdf_pages(file_path: Path) -> List[DocumentPage]:
    path = Path(file_path)
    try:
        from pypdf import PdfReader
        reader = PdfReader(str(path), strict=False)
        pages = [
            DocumentPage(str(path), number, page.extract_text() or "")
            for number, page in enumerate(reader.pages, 1)
        ]
        if any(page.text.strip() for page in pages):
            return pages
    except Exception:
        pass
    try:
        import pdfplumber
        with pdfplumber.open(path) as pdf:
            return [
                DocumentPage(str(path), number, page.extract_text() or "")
                for number, page in enumerate(pdf.pages, 1)
            ]
    except Exception as exc:
        raise OSError(f"Unable to read PDF document '{path}': {exc}") from exc


def parse_document(file_path: str | Path) -> List[DocumentPage]:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Document does not exist: {path}")
    if path.suffix.lower() in (".htm", ".html"):
        return _parse_html_pages(path)
    if path.suffix.lower() == ".pdf":
        return _parse_pdf_pages(path)
    raise ValueError(f"Unsupported file format: {path.suffix}")


def load_document(file_path: str | Path) -> str:
    """Compatibility helper returning the complete cleaned text."""
    return "\n\n".join(page.text for page in parse_document(file_path) if page.text)


def parse_html(file_path: Path) -> str:
    """Legacy text-only HTML API; use parse_document for source metadata."""
    return "\n\n".join(page.text for page in _parse_html_pages(Path(file_path)))


def parse_pdf(file_path: Path) -> str:
    """Legacy text-only PDF API; use parse_document for source/page metadata."""
    return "\n\n".join(page.text for page in _parse_pdf_pages(Path(file_path)) if page.text)