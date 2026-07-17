"""CLI 계층 — IMPLEMENTATION.md §3 참조."""

import argparse
import shutil
import sys
from pathlib import Path

from downloader import (
    DownloadError,
    download,
    download_playlist,
    is_playlist_url,
    validate_url,
)


def progress_hook(d: dict) -> None:
    info = d.get("info_dict") or {}
    idx, count = info.get("playlist_index"), info.get("playlist_count")
    prefix = f"[{idx}/{count}] " if idx and count else ""
    if d["status"] == "downloading":
        total = d.get("total_bytes") or d.get("total_bytes_estimate")
        downloaded = d.get("downloaded_bytes", 0)
        speed = d.get("speed")
        eta = d.get("eta")
        speed_s = f"{speed / 1_000_000:.1f} MB/s" if speed else "-- MB/s"
        if total:
            eta_s = f"{int(eta) // 60:02d}:{int(eta) % 60:02d}" if eta is not None else "--:--"
            line = f"{prefix}[다운로드] {downloaded / total * 100:5.1f}% │ {speed_s} │ 남은 시간 {eta_s}"
        else:
            line = f"{prefix}[다운로드] {downloaded / 1_000_000:.1f} MB │ {speed_s}"
        print(f"\r{line}          ", end="", flush=True)
    elif d["status"] == "finished":
        print(f"\n{prefix}[병합] ffmpeg 처리 중...", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="YouTube 고화질 다운로더")
    parser.add_argument("url", help="YouTube 영상 URL")
    parser.add_argument("-o", "--output-dir", type=Path, default=Path("./downloads"),
                        help="저장 디렉토리 (기본: ./downloads)")
    parser.add_argument("--max-height", type=int, default=None,
                        help="해상도 상한 (예: 1080)")
    parser.add_argument("--codec", choices=["best", "compat"], default="best",
                        help="best=최고화질(VP9/AV1 허용), compat=H.264 우선")
    parser.add_argument("--subs", default=None, metavar="LANGS",
                        help="자막(.srt) 동시 다운로드, 쉼표 구분 (예: ko,en)")
    args = parser.parse_args()

    if shutil.which("ffmpeg") is None:
        print("ffmpeg가 필요합니다: brew install ffmpeg", file=sys.stderr)
        sys.exit(1)

    playlist = is_playlist_url(args.url)
    if not playlist:
        try:
            validate_url(args.url)
        except ValueError as e:
            print(e, file=sys.stderr)
            sys.exit(1)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    subs_langs = args.subs.split(",") if args.subs else None

    try:
        if playlist:
            paths, failed = download_playlist(args.url, args.output_dir,
                                              args.max_height, args.codec,
                                              progress_hook, subs_langs)
            summary = f"완료: {len(paths)}건 저장"
            if failed:
                summary += f" (실패 {failed}건)"
            print(f"{summary} → {paths[0].parent}")
        else:
            final_path = download(args.url, args.output_dir, args.max_height,
                                  args.codec, progress_hook, subs_langs)
            print(f"완료: {final_path}")
    except DownloadError as e:
        print(f"다운로드 실패: {e}", file=sys.stderr)
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
