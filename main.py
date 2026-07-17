"""CLI 계층 — IMPLEMENTATION.md §3 참조."""

import argparse
import shutil
import sys
from pathlib import Path

from downloader import DownloadError, download, validate_url


def progress_hook(d: dict) -> None:
    if d["status"] == "downloading":
        total = d.get("total_bytes") or d.get("total_bytes_estimate")
        downloaded = d.get("downloaded_bytes", 0)
        speed = d.get("speed")
        eta = d.get("eta")
        speed_s = f"{speed / 1_000_000:.1f} MB/s" if speed else "-- MB/s"
        if total:
            eta_s = f"{int(eta) // 60:02d}:{int(eta) % 60:02d}" if eta is not None else "--:--"
            line = f"[다운로드] {downloaded / total * 100:5.1f}% │ {speed_s} │ 남은 시간 {eta_s}"
        else:
            line = f"[다운로드] {downloaded / 1_000_000:.1f} MB │ {speed_s}"
        print(f"\r{line}          ", end="", flush=True)
    elif d["status"] == "finished":
        print("\n[병합] ffmpeg 처리 중...", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="YouTube 고화질 다운로더")
    parser.add_argument("url", help="YouTube 영상 URL")
    parser.add_argument("-o", "--output-dir", type=Path, default=Path("./downloads"),
                        help="저장 디렉토리 (기본: ./downloads)")
    parser.add_argument("--max-height", type=int, default=None,
                        help="해상도 상한 (예: 1080)")
    parser.add_argument("--codec", choices=["best", "compat"], default="best",
                        help="best=최고화질(VP9/AV1 허용), compat=H.264 우선")
    args = parser.parse_args()

    if shutil.which("ffmpeg") is None:
        print("ffmpeg가 필요합니다: brew install ffmpeg", file=sys.stderr)
        sys.exit(1)

    try:
        validate_url(args.url)
    except ValueError as e:
        print(e, file=sys.stderr)
        sys.exit(1)

    args.output_dir.mkdir(parents=True, exist_ok=True)

    try:
        final_path = download(args.url, args.output_dir, args.max_height,
                              args.codec, progress_hook)
    except DownloadError as e:
        print(f"다운로드 실패: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"완료: {final_path}")
    sys.exit(0)


if __name__ == "__main__":
    main()
