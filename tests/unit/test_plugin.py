from ckanext.query_dois.plugin import QueryDOIsPlugin
from unittest.mock import MagicMock, patch


class TestIntegrationWithIVersionedDatastoreDownloads:
    @patch('ckanext.query_dois.plugin.record_stat')
    def test_download_email_context_is_modified(self, record_stat_mock):
        plugin = QueryDOIsPlugin()

        request = MagicMock()
        context = {}
        doi = MagicMock(doi='some/doi')

        find_existing_doi_mock = MagicMock(return_value=doi)

        with patch(
            'ckanext.query_dois.plugin.find_existing_doi', find_existing_doi_mock
        ):
            ret_context = plugin.download_modify_notifier_template_context(
                request, context
            )

        assert ret_context is context
        assert context['doi'] == doi.doi

    @patch('ckanext.query_dois.plugin.record_stat')
    def test_download_email_context_is_always_returned_when_find_errors(
        self, record_stat_mock
    ):
        plugin = QueryDOIsPlugin()

        request = MagicMock()
        context = {}

        find_existing_doi_mock = MagicMock(side_effect=Exception)

        with patch(
            'ckanext.query_dois.plugin.find_existing_doi', find_existing_doi_mock
        ):
            ret_context = plugin.download_modify_notifier_template_context(
                request, context
            )

        assert ret_context is context
        assert 'doi' not in context

    def test_download_email_context_contains_doi_if_we_get_one_even_if_error(self):
        """
        If the DOI gets generated we should stick it in the context as soon as possible.

        This means that even if less important calls fail (like the record_stat call)
        we'll get a doi back in the context. This test checks that functionality.
        """
        plugin = QueryDOIsPlugin()

        request = MagicMock()
        context = {}
        doi = MagicMock(doi='some/doi')

        find_existing_doi_mock = MagicMock(return_value=doi)
        record_stat_mock = MagicMock(side_effect=Exception)

        with patch('ckanext.query_dois.plugin.record_stat', record_stat_mock):
            with patch(
                'ckanext.query_dois.plugin.find_existing_doi', find_existing_doi_mock
            ):
                ret_context = plugin.download_modify_notifier_template_context(
                    request, context
                )

        assert ret_context is context
        assert context['doi'] == doi.doi
