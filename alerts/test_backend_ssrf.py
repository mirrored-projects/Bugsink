import ipaddress
from unittest.mock import patch

from django.test import SimpleTestCase

from .service_backends.jira_cloud import jira_cloud_backend_send_test_message
from .service_backends.webhook import WebhookBackend


RESOLVED_IP = "93.184.216.34"


class WebhookSafeRequestTests(SimpleTestCase):
    @patch("alerts.service_backends.webhook.validate_webhook_destination",
           return_value=[ipaddress.ip_address(RESOLVED_IP)])
    @patch("requests.Session.request")
    def test_connects_to_validated_ip_without_redirects(self, request, _validate):
        WebhookBackend.safe_request(
            "PUT", "https://example.com/hook", data="{}", headers={"host": "internal", "X-Test": "1"})

        method, url = request.call_args.args
        kwargs = request.call_args.kwargs
        self.assertEqual(method, "PUT")
        self.assertIn(RESOLVED_IP, url)
        self.assertEqual(kwargs["headers"], {"X-Test": "1", "Host": "example.com"})
        self.assertIs(kwargs["allow_redirects"], False)

    @patch("alerts.service_backends.webhook.validate_webhook_destination", side_effect=ValueError("blocked"))
    @patch("requests.Session.request")
    def test_blocked_destination_sends_nothing(self, request, _validate):
        with self.assertRaises(ValueError):
            WebhookBackend.safe_request("POST", "https://internal.example/hook", headers={})

        request.assert_not_called()


class JiraCloudSafePostTests(SimpleTestCase):
    @patch("alerts.service_backends.jira_cloud._store_failure_info")
    @patch("alerts.service_backends.base.validate_webhook_destination", side_effect=ValueError("blocked"))
    @patch("requests.Session.post")
    def test_blocked_destination_is_recorded_and_sends_nothing(self, post, _validate, store_failure):
        jira_cloud_backend_send_test_message(
            "https://jira.internal", "user@example.com", "token", "PRJ", "Bug", [], "project", "display", 1)

        post.assert_not_called()
        store_failure.assert_called_once()
