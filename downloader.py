"""다운로드 제어 계층 — IMPLEMENTATION.md §2 참조."""

import re
from pathlib import Path
from typing import Callable

import yt_dlp


class DownloadError(Exception):
    """다운로드 실패. 메시지에 사용자에게 보여줄 원인 포함."""


_URL_RE = re.compile(
    r"(?:https?://)?(?:www\.|m\.)?"
    r"(?:youtube\.com/(?:watch\?(?:.*&)?v=|shorts/|live/)|youtu\.be/)"
    r"([A-Za-z0-9_-]{11})"
)


def validate_url(url: str) -> str:
    """YouTube URL 검증. 유효하면 11자리 영상 ID 반환, 무효하면 ValueError."""
    m = _URL_RE.search(url)
    if not m:
        raise ValueError(f"YouTube 영상 URL이 아닙니다: {url}")
    return m.group(1)


def build_format_selector(max_height: int | None, codec: str) -> str:
    """IMPLEMENTATION.md §2.3의 폴백 규칙 문자열 생성."""
    h = f"[height<={max_height}]" if max_height else ""
    if codec == "compat":
        return (
            f"bestvideo[ext=mp4][vcodec^=avc1]{h}+bestaudio[ext=m4a]"
            f"/bestvideo{h}+bestaudio/best{h}"
        )
    return f"bestvideo{h}+bestaudio/best{h}"


def download(
    url: str,
    output_dir: Path,
    max_height: int | None,
    codec: str,
    progress_hook: Callable[[dict], None],
) -> Path:
    """다운로드 실행. 성공 시 최종 파일 경로 반환, 실패 시 DownloadError."""
    ydl_opts = {
        "format": build_format_selector(max_height, codec),
        "outtmpl": str(output_dir / "%(title)s [%(id)s].%(ext)s"),
        "merge_output_format": "mp4",
        "noplaylist": True,
        "retries": 3,
        "fragment_retries": 3,
        "continuedl": True,
        "progress_hooks": [progress_hook],
        "quiet": True,
        "noprogress": True,
        "no_warnings": True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
    except yt_dlp.utils.DownloadError as e:
        raise DownloadError(str(e)) from e
    return Path(info["requested_downloads"][0]["filepath"])
