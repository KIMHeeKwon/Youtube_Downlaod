"""updater 단위 테스트 — 네트워크 불필요 (PHASE3 §8)."""

import updater


class TestVersionTuple:
    def test_기본_파싱(self):
        assert updater.version_tuple("0.1.0") == (0, 1, 0)

    def test_v접두사_제거(self):
        assert updater.version_tuple("v1.2.3") == (1, 2, 3)

    def test_자릿수_함정(self):
        # 문자열 비교였다면 "0.10.0" < "0.9.0"으로 잘못 판정된다
        assert updater.version_tuple("0.9.0") < updater.version_tuple("0.10.0")

    def test_오름차순(self):
        vt = updater.version_tuple
        assert vt("0.1.0") < vt("0.2.0") < vt("0.10.0") < vt("1.0.0")

    def test_숫자없음(self):
        assert updater.version_tuple("nightly") == ()


def _release_json(tag: str) -> dict:
    return {
        "tag_name": tag,
        "zipball_url": f"https://api.github.com/repos/x/y/zipball/{tag}",
        "body": "릴리스 노트",
    }


class TestParseRelease:
    def test_새_버전이면_Release_반환(self, monkeypatch):
        monkeypatch.setattr(updater, "CURRENT_VERSION", "0.1.0")
        rel = updater.parse_release(_release_json("v0.2.0"))
        assert rel is not None
        assert (rel.tag, rel.version) == ("v0.2.0", "0.2.0")
        assert rel.zip_url.endswith("v0.2.0")

    def test_같은_버전이면_None(self, monkeypatch):
        monkeypatch.setattr(updater, "CURRENT_VERSION", "0.2.0")
        assert updater.parse_release(_release_json("v0.2.0")) is None

    def test_구_버전이면_None(self, monkeypatch):
        monkeypatch.setattr(updater, "CURRENT_VERSION", "0.3.0")
        assert updater.parse_release(_release_json("v0.2.0")) is None

    def test_태그_없으면_None(self):
        assert updater.parse_release({}) is None

    def test_숫자_아닌_태그면_None(self):
        assert updater.parse_release(_release_json("nightly")) is None

    def test_노트_없으면_빈문자열(self, monkeypatch):
        monkeypatch.setattr(updater, "CURRENT_VERSION", "0.1.0")
        data = _release_json("v0.2.0")
        del data["body"]
        assert updater.parse_release(data).notes == ""


class TestSourceItems:
    def test_사용자_데이터는_교체_대상이_아님(self):
        """downloads/.venv/tools가 교체 목록에 없어야 한다 (PHASE3 §5.1)."""
        assert "downloads" not in updater.SOURCE_ITEMS
        assert ".venv" not in updater.SOURCE_ITEMS
        assert "tools" not in updater.SOURCE_ITEMS
