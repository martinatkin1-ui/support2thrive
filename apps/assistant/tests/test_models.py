"""Tests for apps/assistant models — OrgDocument validation."""
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from apps.assistant.forms import OrgDocumentForm


class OrgDocumentFormTest(TestCase):
    """VALIDATION.md: PDF > 20MB rejected; non-PDF extension rejected."""

    def _make_pdf_upload(self, size_bytes: int, name: str = "test.pdf"):
        content = b"%PDF-1.4 " + b"x" * (size_bytes - 9)
        return SimpleUploadedFile(name, content, content_type="application/pdf")

    def test_pdf_under_20mb_passes(self):
        """A 1MB PDF passes validation."""
        f = self._make_pdf_upload(1 * 1024 * 1024)
        form = OrgDocumentForm(data={"title": "Test"}, files={"file": f})
        # Form requires org FK — check only file field error
        self.assertNotIn("file", form.errors)

    def test_pdf_over_20mb_rejected(self):
        """A 21MB PDF fails with size validation error."""
        f = self._make_pdf_upload(21 * 1024 * 1024)
        form = OrgDocumentForm(data={"title": "Test"}, files={"file": f})
        self.assertIn("file", form.errors)
        self.assertIn("20MB", str(form.errors["file"]))

    def test_non_pdf_extension_rejected(self):
        """A .docx file fails FileExtensionValidator."""
        f = SimpleUploadedFile("report.docx", b"content", content_type="application/vnd.openxmlformats")
        form = OrgDocumentForm(data={"title": "Test"}, files={"file": f})
        self.assertIn("file", form.errors)
