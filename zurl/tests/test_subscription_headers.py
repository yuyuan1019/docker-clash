import unittest

from app.api.subscription_headers import build_subscription_response_headers


class SubscriptionHeadersTest(unittest.TestCase):
    def test_forwards_upstream_profile_name_and_metadata(self):
        upstream = {
            "Content-Disposition": "attachment; filename=\"upstream\"",
            "Subscription-Userinfo": "upload=1; download=2",
            "Profile-Update-Interval": "24",
            "X-Unrelated": "ignored",
        }

        headers = build_subscription_response_headers(
            upstream, {}
        )

        self.assertEqual(
            "attachment; filename=\"upstream\"", headers["content-disposition"]
        )
        self.assertEqual("upload=1; download=2", headers["subscription-userinfo"])
        self.assertEqual("24", headers["profile-update-interval"])
        self.assertNotIn("x-unrelated", headers)

    def test_generates_rfc5987_filename_when_upstream_omits_it(self):
        headers = build_subscription_response_headers({}, {"filename": ["我的合集"]})

        self.assertEqual(
            "attachment; filename=\"subscription\"; "
            "filename*=UTF-8''%E6%88%91%E7%9A%84%E5%90%88%E9%9B%86",
            headers["content-disposition"],
        )

    def test_rejects_control_characters_in_fallback_filename(self):
        headers = build_subscription_response_headers(
            {}, {"filename": ["bad\r\nheader"]}
        )

        self.assertNotIn("content-disposition", headers)

    def test_replaces_non_latin1_upstream_filename_with_safe_page_name(self):
        headers = build_subscription_response_headers(
            {"Content-Disposition": 'attachment; filename="旧名称"'},
            {"filename": ["新名称"]},
        )

        self.assertEqual(
            "attachment; filename=\"subscription\"; "
            "filename*=UTF-8''%E6%96%B0%E5%90%8D%E7%A7%B0",
            headers["content-disposition"],
        )


if __name__ == "__main__":
    unittest.main()
