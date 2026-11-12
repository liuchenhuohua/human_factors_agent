from io import BytesIO

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.domain.evidence import ParsedDocument, ParsedPage
from app.domain.evidence_ports import DocumentParsingError


class PypdfTextExtractor:
    """Extract page-addressable text from digitally generated PDFs."""

    def __init__(self, max_pages: int = 250) -> None:
        self._max_pages = max_pages

    def parse(self, content: bytes) -> ParsedDocument:
        try:
            reader = PdfReader(BytesIO(content), strict=False)
            if reader.is_encrypted and reader.decrypt("") == 0:
                raise DocumentParsingError("Password-protected PDFs are not supported")
            if not reader.pages:
                raise DocumentParsingError("The PDF has no pages")
            if len(reader.pages) > self._max_pages:
                raise DocumentParsingError(
                    f"The PDF exceeds the {self._max_pages}-page limit"
                )
            pages = [
                ParsedPage(
                    page_number=index,
                    text=(page.extract_text() or "").strip(),
                )
                for index, page in enumerate(reader.pages, start=1)
            ]
        except DocumentParsingError:
            raise
        except (PdfReadError, OSError, TypeError, ValueError) as error:
            raise DocumentParsingError(f"Could not parse PDF: {error}") from error
        if not any(page.text for page in pages):
            raise DocumentParsingError(
                "No selectable text was found; scanned PDFs need OCR before upload"
            )
        return ParsedDocument(pages=pages)
