import argparse
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import sum_yt


URL = "https://www.youtube.com/watch?v=abcdefghijk"
SRT = "1\n00:00:00,000 --> 00:00:01,000\nhello\n"


def video_info() -> dict:
    return {
        "id": "abcdefghijk",
        "title": "A Test Video",
        "uploader": "Test Channel",
        "duration": 3723,
        "upload_date": "20260922",
    }


def config(videos_dir: str, *, transcript_only: bool):
    return argparse.Namespace(
        cookies_from_browser=None,
        videos_dir=videos_dir,
        force=False,
        no_whisper=True,
        whisper_model="small",
        claude_model=None,
        max_chars=120_000,
        transcript_only=transcript_only,
    )


class TranscriptOnlyTests(unittest.TestCase):
    @patch("sum_yt.summarize_with_claude")
    @patch("sum_yt.fetch_subtitles", return_value=SRT)
    @patch("sum_yt.probe_access", return_value=(video_info(), None))
    def test_writes_contract_without_summary(self, access, fetch, summarize):
        with tempfile.TemporaryDirectory() as tmp:
            result = sum_yt.process_video(URL, config(tmp, transcript_only=True))
            out = Path(result["dir"])

            self.assertEqual(result["status"], "ok")
            self.assertTrue((out / "subtitle.srt").exists())
            self.assertTrue((out / "transcript.txt").exists())
            self.assertFalse((out / "summary.md").exists())
            self.assertEqual(
                json.loads((out / "metadata.json").read_text()),
                {
                    "id": "abcdefghijk",
                    "url": URL,
                    "title": "A Test Video",
                    "channel": "Test Channel",
                    "duration": "1:02:03",
                    "uploaded": "2026-09-22",
                },
            )
        summarize.assert_not_called()

    @patch("sum_yt.summarize_with_claude")
    @patch("sum_yt.fetch_subtitles")
    @patch("sum_yt.probe_access", return_value=(video_info(), None))
    def test_complete_transcript_cache_is_resumable(self, access, fetch, summarize):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "2026-09-22" / "old-title"
            out.mkdir(parents=True)
            (out / "metadata.json").write_text(
                json.dumps({"id": "abcdefghijk"}), encoding="utf-8"
            )
            (out / "subtitle.srt").write_text(SRT, encoding="utf-8")
            (out / "transcript.txt").write_text("hello\n", encoding="utf-8")

            result = sum_yt.process_video(URL, config(tmp, transcript_only=True))

            self.assertEqual(result["status"], "skip")
            self.assertEqual(Path(result["dir"]), out)
            metadata = json.loads((out / "metadata.json").read_text())
            self.assertEqual(metadata["title"], "A Test Video")
        fetch.assert_not_called()
        summarize.assert_not_called()

    @patch("sum_yt.summarize_with_claude", return_value="## 一句話總結\n完成")
    @patch("sum_yt.fetch_subtitles", return_value=SRT)
    @patch("sum_yt.probe_access", return_value=(video_info(), None))
    def test_normal_flow_still_summarizes(self, access, fetch, summarize):
        with tempfile.TemporaryDirectory() as tmp:
            result = sum_yt.process_video(URL, config(tmp, transcript_only=False))
            out = Path(result["dir"])

            self.assertEqual(result["status"], "ok")
            self.assertTrue((out / "summary.md").exists())
            self.assertTrue((out / "metadata.json").exists())
        summarize.assert_called_once()

    @patch("sum_yt.summarize_with_claude")
    @patch("sum_yt.fetch_subtitles", return_value=SRT)
    @patch("sum_yt.probe_access", return_value=(video_info(), None))
    def test_existing_summary_is_preserved(self, access, fetch, summarize):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "2026-09-22" / "a-test-video"
            out.mkdir(parents=True)
            summary = out / "summary.md"
            summary.write_text("existing summary\n", encoding="utf-8")

            result = sum_yt.process_video(URL, config(tmp, transcript_only=True))

            self.assertEqual(result["status"], "ok")
            self.assertEqual(summary.read_text(), "existing summary\n")
            self.assertTrue((out / "metadata.json").exists())
        summarize.assert_not_called()


if __name__ == "__main__":
    unittest.main()
