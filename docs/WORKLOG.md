# WORKLOG

## 2026-07-17

- **목표**: YouTube 고화질 다운로더 프로젝트 시스템 설계 수립
- **결정사항**:
  - 다운로드 엔진으로 yt-dlp(Python API) 채택 — 직접 구현·pytube 대비 유지보수성 우위
  - 고화질 핵심은 DASH 분리 스트림(bestvideo+bestaudio) 선택 + ffmpeg 무손실 병합
  - MVP는 CLI 2개 파일(main.py, downloader.py) 구조로 최소화, GUI/재생목록은 Phase 2로 보류
- **산출물**: `docs/DESIGN.md` (시스템 설계서)
- **현재 진행도**: 설계 완료, 구현 미착수
- **남은 미해결**: ffmpeg·yt-dlp 미설치 (환경 구성 필요), 시스템 Python 3.9 → 프로젝트 전용 venv 필요
- **다음 단계**: 설계 승인 후 1단계(환경 구성) → 2~4단계(구현·검증) 진행

### 2차 작업 (같은 날)
- **목표**: 설계서 시각화 및 라이선스/저작권 분석 보강
- **결정사항**:
  - ffmpeg(GPL v2+)는 동봉 배포하지 않고 시스템 설치 전제 → 본 코드 라이선스 자유 확보
  - 콘텐츠 저작권은 코드 라이선스와 분리 평가, 사용 범위를 본인 콘텐츠·CC·사적 이용으로 한정
- **산출물**: `docs/DESIGN.md` 6절(라이선스/저작권) 추가, 시각화 설계서 아티팩트 발행
  (https://claude.ai/code/artifact/76ff96b3-e366-4d02-ac35-1f895c76d9c0)
- **현재 진행도**: 설계 문서 완성, 구현 미착수

### 3차 작업 (같은 날)
- **목표**: 설계 기반 CLI 구현 명세서 작성 (함수 시그니처·yt-dlp 옵션·명령어 수준 구체화)
- **결정사항**:
  - 프로젝트 관리: uv + Python 3.12, 의존성은 yt-dlp / pytest(dev) 2개로 한정
  - 공개 인터페이스 확정: `validate_url`, `build_format_selector`, `download` + `DownloadError`
  - 파일명 규칙: `%(title)s [%(id)s].%(ext)s` (제목 충돌 방지), 출력 기본 경로 `./downloads`
  - CLI 옵션 확정: `url`, `-o/--output-dir`, `--max-height`, `--codec {best,compat}`
  - 단위 테스트는 네트워크 불필요 범위(URL 검증, 포맷 규칙)로 한정, 실 다운로드는 수동 통합 검증
- **산출물**: `docs/IMPLEMENTATION.md` (구현 명세서)
- **현재 진행도**: 설계·구현 명세 완료, 코드 미착수
- **남은 미해결**: ffmpeg·uv 환경 구성 필요 (명세 1단계)
- **다음 단계**: 명세 승인 후 1단계(환경 구성)부터 체크리스트 순서로 구현
