import unittest

import sum_yt


class ChooseAutoLangTest(unittest.TestCase):
    def test_dubbed_video_uses_declared_language_orig_track(self):
        auto = {k: [] for k in ["ar-orig", "bn-orig", "en-orig", "fr-orig", "ar", "en", "zh-Hant"]}
        self.assertEqual(sum_yt._choose_auto_lang(auto, {"language": "en-US"}), "en-orig")

    def test_single_orig_track_wins_even_without_declared_language(self):
        auto = {k: [] for k in ["ja-orig", "en", "zh-Hant"]}
        self.assertEqual(sum_yt._choose_auto_lang(auto, {}), "ja-orig")

    def test_several_orig_tracks_without_declared_language_follow_preference(self):
        auto = {k: [] for k in ["ar-orig", "en-orig"]}
        self.assertEqual(sum_yt._choose_auto_lang(auto, {}), "en-orig")

    def test_no_orig_track_falls_back_to_declared_language(self):
        auto = {k: [] for k in ["ar", "ja", "fr"]}
        self.assertEqual(sum_yt._choose_auto_lang(auto, {"language": "ja"}), "ja")


if __name__ == "__main__":
    unittest.main()
