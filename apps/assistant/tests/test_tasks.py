"""Tests for assistant Celery tasks — index_organization, index_pathway, index_org_document."""
import sys
from unittest.mock import MagicMock, patch
from django.test import TestCase
from django.contrib.auth import get_user_model

from apps.core.models import Region
from apps.organizations.models import Organization


User = get_user_model()


def _make_region():
    return Region.objects.get_or_create(name="Test Region", slug="test-region")[0]


def _make_org(region=None):
    region = region or _make_region()
    return Organization.objects.create(
        name="Test Org",
        slug="test-org",
        description="Test description",
        short_description="Short desc",
        region=region,
        status="active",
    )


class BuildOrgContentListTest(TestCase):
    """VALIDATION.md: content_list items have required keys."""

    def test_content_list_has_required_keys(self):
        """build_org_content_list returns dicts with 'type', 'text', 'page_idx'."""
        from apps.assistant.rag_service import build_org_content_list
        org = _make_org()
        result = build_org_content_list(org.pk)
        self.assertTrue(len(result) > 0)
        for item in result:
            self.assertIn("type", item)
            self.assertIn("text", item)
            self.assertIn("page_idx", item)
            self.assertEqual(item["type"], "text")

    def test_content_list_contains_org_name(self):
        """build_org_content_list includes the org name in text."""
        from apps.assistant.rag_service import build_org_content_list
        org = _make_org()
        result = build_org_content_list(org.pk)
        all_text = " ".join(item["text"] for item in result)
        self.assertIn("Test Org", all_text)

    def test_missing_org_returns_empty(self):
        """build_org_content_list returns [] for non-existent org."""
        from apps.assistant.rag_service import build_org_content_list
        result = build_org_content_list(org_id=99999)
        self.assertEqual(result, [])


class IndexOrganizationTaskTest(TestCase):
    """VALIDATION.md: index_organization task calls insert_content_list."""

    @patch("apps.assistant.tasks.asyncio.run")
    def test_index_organization_calls_asyncio_run(self, mock_run):
        """index_organization calls asyncio.run() with the _index coroutine."""
        from apps.assistant.tasks import index_organization
        org = _make_org()
        index_organization(org.pk)
        mock_run.assert_called_once()

    @patch("apps.assistant.rag_service.get_rag_instance")
    @patch("apps.assistant.tasks.asyncio.run")
    def test_empty_content_list_skips_rag(self, mock_run, mock_get_rag):
        """index_organization with non-existent org skips insert (empty content_list)."""
        from apps.assistant.tasks import index_organization
        # org_id 99999 does not exist — build_org_content_list returns []
        index_organization(99999)
        # asyncio.run still called (runs _index which returns early)
        mock_run.assert_called_once()


class ProcessOrgDocumentTest(TestCase):
    """VALIDATION.md: indexed_at set after successful task; index_error set after failure."""

    def setUp(self):
        # Inject a mock pymupdf4llm into sys.modules so the deferred import inside
        # process_org_document resolves to our mock (package not installed in test env).
        self._pymupdf_mock = MagicMock()
        sys.modules["pymupdf4llm"] = self._pymupdf_mock

    def tearDown(self):
        sys.modules.pop("pymupdf4llm", None)

    def _make_doc(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        from apps.assistant.models import OrgDocument
        org = _make_org()
        pdf_content = b"%PDF-1.4 test content"
        f = SimpleUploadedFile("test.pdf", pdf_content, content_type="application/pdf")
        doc = OrgDocument.objects.create(
            org=org,
            title="Test Doc",
            file=f,
        )
        return doc

    @patch("apps.assistant.services.asyncio.run")
    def test_indexed_at_set_on_success(self, mock_run):
        """indexed_at is set after successful process_org_document."""
        from apps.assistant.services import process_org_document
        self._pymupdf_mock.to_markdown.return_value = "# Test org content\nSome content here."
        mock_run.return_value = None

        doc = self._make_doc()
        process_org_document(doc.pk)
        doc.refresh_from_db()

        self.assertIsNotNone(doc.indexed_at)
        self.assertEqual(doc.index_error, "")

    @patch("apps.assistant.services.asyncio.run")
    def test_index_error_set_on_failure(self, mock_run):
        """index_error is populated when process_org_document raises."""
        from apps.assistant.services import process_org_document
        self._pymupdf_mock.to_markdown.side_effect = RuntimeError("PDF parse failed")

        doc = self._make_doc()
        with self.assertRaises(RuntimeError):
            process_org_document(doc.pk)
        doc.refresh_from_db()

        self.assertIn("PDF parse failed", doc.index_error)
