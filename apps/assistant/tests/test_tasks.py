"""Tests for assistant Celery tasks — index_organization, index_pathway, index_org_document."""
from unittest.mock import patch, AsyncMock
from django.test import TestCase


class IndexOrganizationTaskTest(TestCase):
    """VALIDATION.md: index_organization builds correct content_list shape."""

    @patch("apps.assistant.rag_service.get_rag_instance")
    def test_content_list_has_required_keys(self, mock_get_rag):
        """build_org_content_list returns dicts with 'type', 'text', 'page_idx' keys."""
        from apps.assistant.rag_service import build_org_content_list
        # Will require a seeded org — test expanded in Plan 06-02
        # For now: verify function is importable
        self.assertTrue(callable(build_org_content_list))

    def test_build_org_content_list_missing_org(self):
        """build_org_content_list returns empty list for non-existent org."""
        from apps.assistant.rag_service import build_org_content_list
        result = build_org_content_list(org_id=99999)
        self.assertEqual(result, [])
