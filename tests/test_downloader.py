"""단위 테스트 — IMPLEMENTATION.md §4.1 (네트워크 불필요)."""

import pytest

from downloader import build_format_selector, validate_url


class TestValidateUrl:
    @pytest.mark.parametrize("url", [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://youtu.be/dQw4w9WgXcQ",
        "https://www.youtube.com/shorts/dQw4w9WgXcQ",
        "https://www.youtube.com/watch?list=PL123&v=dQw4w9WgXcQ",
        "https://youtube.com/live/dQw4w9WgXcQ",
        "https://youtube.com/live/dQw4w9WgXcQ?feature=share",
    ])
    def test_valid(self, url):
        assert validate_url(url) == "dQw4w9WgXcQ"

    @pytest.mark.parametrize("url", [
        "https://vimeo.com/12345",
        "https://www.youtube.com/playlist?list=PL123",
        "잘못된문자열",
    ])
    def test_invalid(self, url):
        with pytest.raises(ValueError):
            validate_url(url)


class TestBuildFormatSelector:
    def test_best_no_limit(self):
        assert build_format_selector(None, "best") == "bestvideo+bestaudio/best"

    def test_best_1080(self):
        assert build_format_selector(1080, "best") == (
            "bestvideo[height<=1080]+bestaudio/best[height<=1080]"
        )

    def test_compat_no_limit(self):
        assert build_format_selector(None, "compat") == (
            "bestvideo[ext=mp4][vcodec^=avc1]+bestaudio[ext=m4a]"
            "/bestvideo+bestaudio/best"
        )

    def test_compat_1080(self):
        assert build_format_selector(1080, "compat") == (
            "bestvideo[ext=mp4][vcodec^=avc1][height<=1080]+bestaudio[ext=m4a]"
            "/bestvideo[height<=1080]+bestaudio/best[height<=1080]"
        )
