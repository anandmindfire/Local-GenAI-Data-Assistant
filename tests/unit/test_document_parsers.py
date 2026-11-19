"""Unit tests for document parsers (PDF, DOCX, TXT, MD)."""

import io

import docx
import pymupdf
import pytest

from app.core.exceptions import DocumentParsingFailureException
from app.infrastructure.document_parsers import (
    DOCXParser,
    MarkdownParser,
    PDFParser,
    TextParser,
    get_parser_for_file,
)


def test_get_parser_for_file():
    """Verify parser selection by file extension."""
    assert isinstance(get_parser_for_file("file.pdf"), PDFParser)
    assert isinstance(get_parser_for_file("file.docx"), DOCXParser)
    assert isinstance(get_parser_for_file("file.txt"), TextParser)
    assert isinstance(get_parser_for_file("file.md"), MarkdownParser)

    with pytest.raises(DocumentParsingFailureException):
        get_parser_for_file("file.csv")


def test_text_parser():
    """Test plain text parser."""
    parser = TextParser()
    content = "This is a company handbook.\nIt covers standard policies."
    parsed = parser.parse(content.encode("utf-8"), "handbook.txt")
    assert parsed.filename == "handbook.txt"
    assert parsed.file_type == "txt"
    assert len(parsed.pages) == 1
    assert "company handbook" in parsed.full_text

    # Empty text file
    with pytest.raises(DocumentParsingFailureException):
        parser.parse(b"   \n\n  ", "empty.txt")


def test_markdown_parser():
    """Test markdown parser."""
    parser = MarkdownParser()
    content = "# Leave Policy\n\nEmployees are entitled to 24 days annual leave."
    parsed = parser.parse(content.encode("utf-8"), "leave-policy.md")
    assert parsed.file_type == "md"
    assert len(parsed.pages) == 1
    assert "24 days" in parsed.full_text

    # Empty markdown file
    with pytest.raises(DocumentParsingFailureException):
        parser.parse(b"", "empty.md")


def test_docx_parser():
    """Test DOCX parser with paragraphs and tables."""
    doc = docx.Document()
    doc.add_heading("Expense Policy", level=1)
    doc.add_paragraph("Travel meals are reimbursed up to $50 per day.")

    table = doc.add_table(rows=2, cols=2)
    table.cell(0, 0).text = "Expense Type"
    table.cell(0, 1).text = "Limit"
    table.cell(1, 0).text = "Hotel"
    table.cell(1, 1).text = "$200"

    buffer = io.BytesIO()
    doc.save(buffer)
    docx_bytes = buffer.getvalue()

    parser = DOCXParser()
    parsed = parser.parse(docx_bytes, "expense.docx")
    assert parsed.file_type == "docx"
    assert "Travel meals are reimbursed" in parsed.full_text
    assert "Hotel | $200" in parsed.full_text


def test_pdf_parser():
    """Test PDF parser with page tracking using PyMuPDF."""
    doc = pymupdf.open()
    page1 = doc.new_page()
    page1.insert_text((50, 72), "Page 1: Overview of the onboarding procedure.")
    page2 = doc.new_page()
    page2.insert_text((50, 72), "Page 2: Security credentials and laptop setup.")

    pdf_bytes = doc.tobytes()
    doc.close()

    parser = PDFParser()
    parsed = parser.parse(pdf_bytes, "onboarding.pdf")
    assert parsed.file_type == "pdf"
    assert len(parsed.pages) == 2
    assert parsed.pages[0].page_number == 1
    assert "Page 1: Overview" in parsed.pages[0].text
    assert parsed.pages[1].page_number == 2
    assert "Page 2: Security credentials" in parsed.pages[1].text
