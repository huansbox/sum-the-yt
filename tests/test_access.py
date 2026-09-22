import argparse
import tempfile
import unittest
from unittest.mock import call, patch

import sum_yt


URL = "https://www.youtube.com/watch?v=test"


def video_info(availability: str, *, playable: bool) -> dict:
    formats = [{"acodec": "mp4a", "vcodec": "none"}] if playable else []
    return {
        "id": "test",
        "title": "Test video",
        "availability": availability,
        "formats": formats,
        "upload_date": "20260713",
    }


class ProbeAccessTests(unittest.TestCase):
    @patch("sum_yt.probe")
    def test_public_video_stays_anonymous(self, probe):
        public = video_info("public", playable=True)
        probe.return_value = public

        info, cookies = sum_yt.probe_access(URL, "firefox")

        self.assertIs(info, public)
        self.assertIsNone(cookies)
        probe.assert_called_once_with(URL, None, allow_no_formats=True)

    @patch("sum_yt.probe")
    def test_members_only_video_retries_with_configured_browser(self, probe):
        anonymous = video_info("subscriber_only", playable=False)
        authenticated = video_info("subscriber_only", playable=True)
        probe.side_effect = [anonymous, authenticated]

        info, cookies = sum_yt.probe_access(URL, "firefox")

        self.assertIs(info, authenticated)
        self.assertEqual(cookies, "firefox")
        self.assertEqual(
            probe.call_args_list,
            [call(URL, None, allow_no_formats=True), call(URL, "firefox")],
        )

    @patch("sum_yt.probe")
    def test_members_only_video_requires_cookie_configuration(self, probe):
        probe.return_value = video_info("subscriber_only", playable=False)

        with self.assertRaisesRegex(RuntimeError, "SUMYT_COOKIES_FROM_BROWSER"):
            sum_yt.probe_access(URL, None)

        probe.assert_called_once_with(URL, None, allow_no_formats=True)

    @patch("sum_yt.probe")
    def test_authenticated_retry_failure_is_not_hidden(self, probe):
        failure = RuntimeError("browser cookie extraction failed")
        probe.side_effect = [video_info("subscriber_only", playable=False), failure]

        with self.assertRaisesRegex(RuntimeError, "cookie extraction failed"):
            sum_yt.probe_access(URL, "firefox")

    @patch("sum_yt.probe")
    def test_other_availability_does_not_send_cookies(self, probe):
        probe.return_value = video_info("private", playable=False)

        with self.assertRaisesRegex(RuntimeError, "availability=private"):
            sum_yt.probe_access(URL, "firefox")

        probe.assert_called_once_with(URL, None, allow_no_formats=True)

    @patch("sum_yt.probe")
    def test_unrelated_probe_failure_does_not_send_cookies(self, probe):
        failure = RuntimeError("network unavailable")
        probe.side_effect = failure

        with self.assertRaisesRegex(RuntimeError, "network unavailable"):
            sum_yt.probe_access(URL, "firefox")

        probe.assert_called_once_with(URL, None, allow_no_formats=True)


class EffectiveCookieTests(unittest.TestCase):
    def config(self, videos_dir: str, *, no_whisper: bool = False) -> argparse.Namespace:
        return argparse.Namespace(
            cookies_from_browser="firefox",
            videos_dir=videos_dir,
            force=False,
            no_whisper=no_whisper,
            whisper_model="small",
            claude_model=None,
            max_chars=120_000,
            transcript_only=False,
        )

    @patch("sum_yt.summarize_with_claude", return_value="## 一句話總結\n完成")
    @patch("sum_yt.fetch_subtitles", return_value="1\n00:00:00,000 --> 00:00:01,000\nhello\n")
    @patch("sum_yt.probe_access")
    def test_effective_cookies_reach_subtitle_download(self, access, fetch, summarize):
        access.return_value = (video_info("subscriber_only", playable=True), "firefox")
        with tempfile.TemporaryDirectory() as tmp:
            result = sum_yt.process_video(URL, self.config(tmp))

        self.assertEqual(result["status"], "ok")
        self.assertEqual(fetch.call_args.args[3], "firefox")

    @patch("sum_yt.summarize_with_claude", return_value="## 一句話總結\n完成")
    @patch(
        "sum_yt.transcribe_with_whisper",
        return_value="1\n00:00:00,000 --> 00:00:01,000\nhello\n",
    )
    @patch("sum_yt.fetch_subtitles", return_value=None)
    @patch("sum_yt.probe_access")
    def test_effective_cookies_reach_whisper_download(
        self, access, fetch, transcribe, summarize
    ):
        access.return_value = (video_info("subscriber_only", playable=True), "firefox")
        with tempfile.TemporaryDirectory() as tmp:
            result = sum_yt.process_video(URL, self.config(tmp))

        self.assertEqual(result["status"], "ok")
        self.assertEqual(transcribe.call_args.args[3], "firefox")


if __name__ == "__main__":
    unittest.main()
