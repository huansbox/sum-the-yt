# sum-the-yt

把 YouTube 影片濃縮成**繁體中文（台灣用語）**摘要的 Python pipeline。
字幕優先、Whisper 備援、用本機 `claude` CLI 摘要（**不需 API key**）。

## 流程

1. **抓字幕**：用 `yt-dlp` 取得字幕。優先人工字幕；無人工字幕時抓**原始語言的自動字幕軌**（`*-orig`），因為 YouTube 對「機器翻譯字幕軌」會嚴重限流（HTTP 429），原始 ASR 軌則穩定，翻譯交給後面的 `claude`。
2. **Whisper 備援**：若完全沒有可用字幕，下載音訊並用 `faster-whisper`（CPU / int8）轉錄（可用 `--no-whisper` 關閉）。
3. **摘要**：把逐字稿丟給 `claude -p` 輸出繁中摘要；逐字稿過長時自動 **map-reduce**（分段摘要再彙整）。

## 產出

產物依**上傳日期**分層，再以標題 slug 命名：

```
videos/<yyyy-mm-dd>/<slug-of-title>/
├── subtitle.srt     # 帶時間軸的字幕（原始語言；Whisper 路徑則為轉錄結果）
├── transcript.txt   # 純逐字稿
└── summary.md       # 繁體中文摘要 + metadata（頻道/時長/上傳日期/ID）
```

> 取不到上傳日期時會落在 `videos/unknown-date/`。

## 需求

- [uv](https://docs.astral.sh/uv/)
- `claude` CLI（已登入 Claude Code）
- `ffmpeg`（僅 Whisper 備援路徑需要）

## 快速開始

```bash
uv sync                       # 建環境
cp .env.example .env          # 設定（會員影片建議填 SUMYT_COOKIES_FROM_BROWSER=firefox）

# 單部
uv run sum-yt "https://www.youtube.com/watch?v=VIDEO_ID"

# 多部（一次給多個 URL）
uv run sum-yt URL1 URL2 URL3

# 從檔案讀清單（每行一個 URL，# 開頭為註解）
uv run sum-yt -f urls.txt

# 強制重跑（預設會跳過已存在的 summary.md）
uv run sum-yt URL --force
```

## 設定（`.env` 或環境變數，CLI 旗標優先）

| 變數 | CLI 旗標 | 說明 | 預設 |
| --- | --- | --- | --- |
| `SUMYT_COOKIES_FROM_BROWSER` | `--cookies-from-browser` | 只有偵測到會員影片時才讀瀏覽器 cookies（`chrome`/`safari`/`firefox`/`brave`，支援 `chrome:Profile`） | 無 |
| `SUMYT_CLAUDE_MODEL` | `--claude-model` | 覆寫 claude CLI 模型 | CLI 預設 |
| `SUMYT_WHISPER_MODEL` | `--whisper-model` | 備援轉錄模型大小 | `small` |
| `SUMYT_VIDEOS_DIR` | `--videos-dir` | 產物根目錄 | `videos` |
| `SUMYT_MAX_CHARS` | `--max-chars` | 逐字稿超過此字數啟用 map-reduce | `120000` |
| `SUMYT_NO_WHISPER` | `--no-whisper` | 停用 Whisper 備援 | 關 |
| — | `-f, --urls-file` | 批次 URL 清單檔 | — |
| — | `--force` | 覆寫已存在產物 | 關 |

## 已知行為

- YouTube 對**翻譯字幕軌**限流很兇（常 429）；本工具改抓**原始語言軌**並讓 `claude` 翻成繁中，既穩定又更準確。
- 一般與不公開影片會匿名處理；只有 YouTube 標示為會員限定時，才會讀取 `--cookies-from-browser` 指定的瀏覽器 cookies。這個設定不會作為 HTTP 429、PO Token 或其他錯誤的通用重試手段。
- 完全無字幕的影片才會走 Whisper（較慢、首次需下載模型）；用 `--no-whisper` 可讓這類影片直接失敗。

## License

[MIT](LICENSE)
