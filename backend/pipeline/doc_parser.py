"""Document parsing module.

Parses uploaded PDF, DOCX, PPTX files into structured text
for AI analysis.
"""
from pathlib import Path


async def parse_documents(file_paths: list[str]) -> list[dict]:
    """Parse uploaded documents and extract text content.

    Returns:
        [{"filename": str, "text": str, "tables": [...], "images": [...]}]
    """
    results = []

    for fp in file_paths:
        path = Path(fp)
        if not path.exists():
            continue

        suffix = path.suffix.lower()
        text = ""

        try:
            if suffix == ".pdf":
                text = _parse_pdf(path)
            elif suffix in (".docx", ".doc"):
                text = _parse_docx(path)
            elif suffix == ".txt":
                text = path.read_text(encoding="utf-8", errors="ignore")
            else:
                text = f"[Unsupported file type: {suffix}]"
        except Exception as e:
            text = f"[Parse error: {e}]"

        results.append({
            "filename": path.name,
            "text": text[:10000],
            "tables": [],
            "images": [],
        })

    return results


def _parse_pdf(path: Path) -> str:
    """Extract text from PDF using PyPDF2 or pdfplumber."""
    try:
        import pdfplumber
        text_parts = []
        with pdfplumber.open(str(path)) as pdf:
            for page in pdf.pages[:50]:
                t = page.extract_text()
                if t:
                    text_parts.append(t)
        return "\n\n".join(text_parts)
    except ImportError:
        pass

    try:
        from PyPDF2 import PdfReader
        reader = PdfReader(str(path))
        return "\n\n".join(
            page.extract_text() or "" for page in reader.pages[:50]
        )
    except ImportError:
        return "[Install pdfplumber or PyPDF2 to parse PDFs]"


def _parse_docx(path: Path) -> str:
    """Extract text from DOCX."""
    try:
        from docx import Document
        doc = Document(str(path))
        return "\n\n".join(p.text for p in doc.paragraphs if p.text.strip())
    except ImportError:
        return "[Install python-docx to parse DOCX files]"
