"""
StudyMate AI - Document Parser Utility
Handles text extraction from PDF, DOCX, and TXT files.
"""
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class DocumentParseError(Exception):
    """Raised when text extraction fails."""
    pass


def extract_text_from_pdf(file_path: Path) -> tuple[str, int]:
    """
    Extract text from a PDF file using PyMuPDF (fitz).

    Returns:
        (extracted_text, page_count)
    Raises:
        DocumentParseError on failure.
    """
    try:
        import fitz  # PyMuPDF

        doc = fitz.open(str(file_path))
        page_count = len(doc)
        text_parts = []

        for page_num in range(page_count):
            page = doc[page_num]
            text = page.get_text("text")
            if text.strip():
                text_parts.append(f"[Page {page_num + 1}]\n{text.strip()}")

        doc.close()
        full_text = "\n\n".join(text_parts)

        if not full_text.strip():
            raise DocumentParseError(
                "No readable text found in PDF. It may be a scanned image-only document."
            )

        return full_text, page_count

    except ImportError as exc:
        raise DocumentParseError(
            "PyMuPDF is not installed. Run: pip install pymupdf"
        ) from exc
    except fitz.FileDataError as exc:
        raise DocumentParseError(f"Cannot open PDF: {exc}") from exc
    except Exception as exc:
        logger.error("PDF extraction error for %s: %s", file_path, exc)
        raise DocumentParseError(f"Failed to extract text from PDF: {exc}") from exc


def extract_text_from_docx(file_path: Path) -> tuple[str, int]:
    """
    Extract text from a DOCX file using python-docx.

    Returns:
        (extracted_text, paragraph_count_as_page_estimate)
    Raises:
        DocumentParseError on failure.
    """
    try:
        from docx import Document

        doc = Document(str(file_path))
        paragraphs = [para.text.strip() for para in doc.paragraphs if para.text.strip()]
        full_text = "\n\n".join(paragraphs)

        if not full_text.strip():
            raise DocumentParseError(
                "No readable text found in the DOCX file."
            )

        # Rough estimate: 40 paragraphs per "page"
        page_estimate = max(1, len(paragraphs) // 40)
        return full_text, page_estimate

    except ImportError as exc:
        raise DocumentParseError(
            "python-docx is not installed. Run: pip install python-docx"
        ) from exc
    except Exception as exc:
        logger.error("DOCX extraction error for %s: %s", file_path, exc)
        raise DocumentParseError(f"Failed to extract text from DOCX: {exc}") from exc


def extract_text_from_txt(file_path: Path) -> tuple[str, int]:
    """
    Read text from a plain text file.

    Returns:
        (text_content, estimated_page_count)
    Raises:
        DocumentParseError on failure.
    """
    encodings = ["utf-8", "utf-16", "latin-1", "cp1252"]

    for encoding in encodings:
        try:
            content = file_path.read_text(encoding=encoding)
            if content.strip():
                # Rough estimate: 3000 chars per "page"
                page_estimate = max(1, len(content) // 3000)
                return content, page_estimate
        except (UnicodeDecodeError, UnicodeError):
            continue
        except Exception as exc:
            raise DocumentParseError(f"Cannot read text file: {exc}") from exc

    raise DocumentParseError(
        "Could not decode the text file. Ensure it is a valid UTF-8 or Latin-1 file."
    )


def extract_text(file_path: Path) -> tuple[str, int]:
    """
    Dispatch to the correct extractor based on file extension.

    Returns:
        (extracted_text, page_count)
    Raises:
        DocumentParseError for unsupported or failed files.
    """
    suffix = file_path.suffix.lower()

    if suffix == ".pdf":
        return extract_text_from_pdf(file_path)
    elif suffix == ".docx":
        return extract_text_from_docx(file_path)
    elif suffix == ".txt":
        return extract_text_from_txt(file_path)
    else:
        raise DocumentParseError(
            f"Unsupported file type: '{suffix}'. Supported: .pdf, .docx, .txt"
        )


def count_words(text: str) -> int:
    """Count words in a text string."""
    return len(text.split())
