import unittest
import xml.etree.ElementTree as ET
from unittest.mock import patch

from update_dashboard import collect, language_values, render


class DashboardTests(unittest.TestCase):
    def test_language_grouping_preserves_total(self):
        data = {"languages": {str(i): i for i in range(9, 0, -1)}}
        grouped = language_values(data)
        self.assertEqual(len(grouped), 6)
        self.assertEqual(grouped[-1], ("Otros", 10))
        self.assertEqual(sum(v for _, v in grouped), 45)

    @patch("update_dashboard.api")
    def test_collection_excludes_forks_and_profile_from_languages(self, api):
        def repo(name, fork=False):
            return dict(name=name, fork=fork, private=False, stargazers_count=2, forks_count=3)
        api.side_effect = [dict(followers=4, following=5),
                           [repo("app"), repo("upstream", True), repo("benjaguerra192")],
                           {"Python": 60, "HTML": 40}]
        result = collect()
        self.assertEqual(result["public_repos"], 3)
        self.assertEqual(result["original_repos"], 2)
        self.assertEqual(result["forked_repos"], 1)
        self.assertEqual(result["stars"], 4)
        self.assertEqual(result["forks"], 6)
        self.assertEqual(result["languages"], {"Python": 60, "HTML": 40})
        self.assertEqual(api.call_count, 3)

    def test_empty_data_renders_valid_svg(self):
        data = dict(updated_at="test", languages={}, public_repos=0, original_repos=0,
                    forked_repos=0, stars=0, forks=0, followers=0, following=0)
        for mobile in (False, True):
            result = render(data, mobile)
            ET.fromstring(result)
            self.assertNotIn("nan", result)
            self.assertIn("Sin código", result)


if __name__ == "__main__":
    unittest.main()
