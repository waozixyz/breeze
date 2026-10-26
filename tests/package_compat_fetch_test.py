"""Compatibility downloads tolerate transport outages without hiding bad data."""
import io
import socket
import unittest
from unittest.mock import patch
import urllib.error

from package_compat_test import fetch


class FetchTest(unittest.TestCase):
    def test_temporary_dns_recovers_and_payload_is_returned(self):
        outage = urllib.error.URLError(socket.gaierror(socket.EAI_AGAIN, "temporary DNS outage"))
        with (
            patch("package_compat_test.urllib.request.urlopen",
                  side_effect=[outage, outage, io.BytesIO(b"package")]) as request,
            patch("package_compat_test.time.sleep"),
        ):
            self.assertEqual(fetch("https://api.waozi.xyz/package.zx", 7), b"package")
            self.assertEqual(request.call_count, 3)

    def test_exhausted_dns_outage_is_still_a_failure(self):
        outage = urllib.error.URLError(socket.gaierror(socket.EAI_AGAIN, "temporary DNS outage"))
        with (
            patch("package_compat_test.urllib.request.urlopen", side_effect=outage) as request,
            patch("package_compat_test.time.sleep"),
        ):
            with self.assertRaises(urllib.error.URLError):
                fetch("https://api.waozi.xyz/package.zx", 7)
            self.assertEqual(request.call_count, 4)

    def test_absent_package_is_not_retried(self):
        absent = urllib.error.HTTPError("https://api.waozi.xyz/package.zx", 404, "not offered", {}, None)
        with patch("package_compat_test.urllib.request.urlopen", side_effect=absent) as request:
            with self.assertRaises(urllib.error.HTTPError) as failure:
                fetch("https://api.waozi.xyz/package.zx", 7)
            self.assertEqual(failure.exception.code, 404)
            request.assert_called_once()

    def test_oversized_payload_is_rejected_without_retry(self):
        with patch("package_compat_test.urllib.request.urlopen", return_value=io.BytesIO(b"too large")) as request:
            with self.assertRaises(ValueError):
                fetch("https://api.waozi.xyz/package.zx", 3)
            request.assert_called_once()

    def test_permanent_dns_error_is_not_retried(self):
        missing = urllib.error.URLError(socket.gaierror(socket.EAI_NONAME, "unknown host"))
        with patch("package_compat_test.urllib.request.urlopen", side_effect=missing) as request:
            with self.assertRaises(urllib.error.URLError):
                fetch("https://api.waozi.xyz/package.zx", 7)
            request.assert_called_once()

    def test_temporary_server_failure_recovers(self):
        unavailable = urllib.error.HTTPError("https://api.waozi.xyz/package.zx", 503, "unavailable", {}, None)
        with (
            patch("package_compat_test.urllib.request.urlopen",
                  side_effect=[unavailable, io.BytesIO(b"package")]) as request,
            patch("package_compat_test.time.sleep"),
        ):
            self.assertEqual(fetch("https://api.waozi.xyz/package.zx", 7), b"package")
            self.assertEqual(request.call_count, 2)


if __name__ == "__main__":
    unittest.main()
