"""단위 테스트 — IMPLEMENTATION.md §4.1 (네트워크 불필요)."""

import pytest

from downloader import build_format_selector, is_playlist_url, validate_url


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


class TestIsPlaylistUrl:
    @pytest.mark.parametrize("url", [
        "https://www.youtube.com/playlist?list=PL4lCao7KL_QFVb7Iudeipvc2BCavECqzc",
        "https://youtube.com/playlist?list=PL123abc_-",
        "https://m.youtube.com/playlist?app=desktop&list=PL123",
    ])
    def test_playlist(self, url):
        assert is_playlist_url(url) is True

    @pytest.mark.parametrize("url", [
        # watch URL에 list=가 있어도 단일 영상 모드 유지 (PHASE2.md §1)
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ&list=PL123",
        "https://youtu.be/dQw4w9WgXcQ",
        "https://vimeo.com/playlist?list=PL123",
    ])
    def test_not_playlist(self, url):
        assert is_playlist_url(url) is False


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
