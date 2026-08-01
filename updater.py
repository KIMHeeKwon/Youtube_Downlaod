"""갱신 — yt-dlp 자동 / 앱 본체 원클릭 (PHASE3 §3.2, §5).

고장 원인의 대부분은 YouTube 내부 변경에 따른 yt-dlp 노후화이므로 무인 갱신하고,
드물고 위험한 앱 본체 교체는 사용자가 버튼을 눌렀을 때만 수행한다 (DECISIONS D3).
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
REPO = "KIMHeeKwon/Youtube_Downlaod"
API_LATEST = f"https://api.github.com/repos/{REPO}/releases/latest"
_UA = {"User-Agent": "youtube-downloader-updater"}

# 교체 대상 — downloads/(사용자 데이터) .venv/ tools/(무거운 의존성)는 제외 (PHASE3 §5.1)
SOURCE_ITEMS = ["*.py", "static", "windows", "docs", "README.md", "LICENSE",
                "pyproject.toml", "uv.lock"]
REQUIRED_IN_RELEASE = ["gui.py", "downloader.py", "pyproject.toml"]


class UpdateError(Exception):
    """업데이트 실패. 메시지에 사용자에게 보여줄 원인 포함."""


@dataclass
class Release:
    tag: str
    version: str
    zip_url: str
    notes: str


def _read_version() -> str:
    m = re.search(r'^version\s*=\s*"([^"]+)"',
                  (_ROOT / "pyproject.toml").read_text(encoding="utf-8"), re.M)
    return m.group(1) if m else "0.0.0"


CURRENT_VERSION = _read_version()


def version_tuple(v: str) -> tuple[int, ...]:
    """'v0.10.0' → (0, 10, 0). 자릿수 함정(0.9 < 0.10)을 문자열 비교 없이 처리."""
    return tuple(int(p) for p in re.findall(r"\d+", v))


def _uv() -> str:
    """uv 실행 파일 경로. 바탕화면 바로가기는 PATH가 좁을 수 있어 설치 위치도 확인."""
    found = shutil.which("uv")
    if found:
        return found
    for cand in (Path.home() / ".local/bin/uv.exe", Path.home() / ".local/bin/uv"):
        if cand.exists():
            return str(cand)
    raise UpdateError("uv를 찾을 수 없습니다. install.bat을 다시 실행해 주세요.")


# --- yt-dlp 자동 갱신 (D3, 무인) -----------------------------------------

def update_ytdlp(timeout: float = 180) -> tuple[str, str] | None:
    """최신 yt-dlp 설치. 버전이 바뀌면 (이전, 이후), 변화 없으면 None."""
    import yt_dlp

    before = yt_dlp.version.__version__
    r = subprocess.run([_uv(), "pip", "install", "--upgrade", "yt-dlp"],
                       cwd=_ROOT, capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        raise UpdateError(r.stderr.strip() or "yt-dlp 갱신 실패")
    # 이미 import된 모듈은 갱신되지 않으므로 새 프로세스에서 확인한다
    out = subprocess.run(
        [sys.executable, "-c", "import yt_dlp; print(yt_dlp.version.__version__)"],
        cwd=_ROOT, capture_output=True, text=True, timeout=60)
    after = out.stdout.strip() or before
    return (before, after) if after != before else None


# --- 앱 본체 업데이트 (D3·D4, 원클릭) ------------------------------------

def parse_release(data: dict) -> Release | None:
    """GitHub API 응답 → Release. 현재 버전 이하면 None (네트워크 없이 테스트 가능)."""
    tag = data.get("tag_name") or ""
    version = tag.lstrip("vV")
    if not version_tuple(version):
        return None
    if version_tuple(version) <= version_tuple(CURRENT_VERSION):
        return None
    return Release(tag=tag, version=version,
                   zip_url=data.get("zipball_url") or "",
                   notes=data.get("body") or "")


def check_app_update(timeout: float = 3.0) -> Release | None:
    req = urllib.request.Request(API_LATEST, headers={
        **_UA, "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
        return parse_release(json.load(resp))


def apply_app_update(release: Release, on_progress=lambda _m: None) -> None:
    """새 버전을 준비하고 교체 스크립트를 띄운다. 성공 시 이 프로세스는 종료되어야 한다."""
    tmp = Path(tempfile.mkdtemp(prefix="ytdl_update_"))

    on_progress("새 버전을 내려받는 중...")
    zip_path = tmp / "release.zip"
    req = urllib.request.Request(release.zip_url, headers=_UA)
    with urllib.request.urlopen(req, timeout=120) as resp:  # noqa: S310
        zip_path.write_bytes(resp.read())

    on_progress("압축을 푸는 중...")
    with zipfile.ZipFile(zip_path) as z:
        z.extractall(tmp / "src")
    roots = [p for p in (tmp / "src").iterdir() if p.is_dir()]
    if len(roots) != 1:
        raise UpdateError("릴리스 압축 구조가 예상과 다릅니다.")
    new_root = roots[0]

    # 무결성 확인 — 하나라도 없으면 아무것도 바꾸지 않는다 (PHASE3 §5.2)
    for name in REQUIRED_IN_RELEASE:
        if not (new_root / name).exists():
            raise UpdateError(f"릴리스에 {name}이(가) 없어 업데이트를 중단했습니다.")

    on_progress("기존 버전을 백업하는 중...")
    backup = _ROOT / f"_backup_{CURRENT_VERSION}"
    shutil.rmtree(backup, ignore_errors=True)
    _copy_sources(_ROOT, backup)

    on_progress("교체 후 재시작합니다...")
    script = _write_replace_script(tmp, new_root, backup)
    subprocess.Popen([sys.executable, str(script)], cwd=str(tmp),
                     start_new_session=True)


def _copy_sources(src: Path, dst: Path) -> None:
    """SOURCE_ITEMS만 복사. downloads/.venv/tools는 대상에 없으므로 보존된다."""
    dst.mkdir(parents=True, exist_ok=True)
    for pattern in SOURCE_ITEMS:
        for item in src.glob(pattern):
            target = dst / item.name
            if item.is_dir():
                shutil.copytree(item, target, dirs_exist_ok=True)
            else:
                shutil.copy2(item, target)


_REPLACE_SCRIPT = '''\
"""업데이트 교체 스크립트 — 앱 종료 후 실행되며 소스 파일만 교체한다."""
import json, shutil, subprocess, sys, time
from pathlib import Path

cfg = json.loads(Path(__file__).with_name("replace.json").read_text(encoding="utf-8"))
root, new_root, backup = Path(cfg["root"]), Path(cfg["new_root"]), Path(cfg["backup"])

def copy_sources(src, dst):
    for pattern in cfg["items"]:
        for item in src.glob(pattern):
            target = dst / item.name
            if item.is_dir():
                shutil.copytree(item, target, dirs_exist_ok=True)
            else:
                shutil.copy2(item, target)

time.sleep(2)                       # 앱이 종료될 여유
try:
    copy_sources(new_root, root)
    if cfg["uv"]:
        subprocess.run([cfg["uv"], "sync"], cwd=str(root), timeout=600)
except Exception as e:              # 실패 시 백업에서 복원 (PHASE3 §5.2)
    (root / "update-error.log").write_text(f"업데이트 실패: {e}\\n", encoding="utf-8")
    copy_sources(backup, root)

subprocess.Popen([cfg["launcher"], "gui.py"], cwd=str(root))
'''


def _write_replace_script(tmp: Path, new_root: Path, backup: Path) -> Path:
    launcher = sys.executable
    win_gui = Path(launcher).with_name("pythonw.exe")   # 콘솔 창 없이 재시작
    if os.name == "nt" and win_gui.exists():
        launcher = str(win_gui)
    (tmp / "replace.json").write_text(json.dumps({
        "root": str(_ROOT), "new_root": str(new_root), "backup": str(backup),
        "items": SOURCE_ITEMS, "launcher": launcher,
        "uv": shutil.which("uv") or "",
    }), encoding="utf-8")
    script = tmp / "replace.py"
    script.write_text(_REPLACE_SCRIPT, encoding="utf-8")
    return script
