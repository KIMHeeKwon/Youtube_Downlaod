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

### 4차 작업 (같은 날) — 구현 및 실검증 완료
- **목표**: IMPLEMENTATION.md 체크리스트 1~4단계 전체 구현·검증 (테스트 데이터: live URL 2건)
- **결정사항**:
  - 테스트 URL이 `youtube.com/live/<ID>` 형식이라 URL 정규식에 `live/` 패턴 추가 (명세 §2.2 갱신)
  - yt-dlp 2026.x의 JS 런타임 부재 경고("일부 포맷 누락 가능") 대응으로 deno 설치를 환경 요건에 추가
  - `quiet: True`만으로 네이티브 진행률 바가 억제되지 않는 결함 발견 → `noprogress: True` 추가 (명세 §2.4 갱신)
- **산출물**:
  - 코드: `downloader.py`, `main.py`, `tests/test_downloader.py`, `pyproject.toml`(pytest pythonpath)
  - 환경: Python 3.12.13(uv), yt-dlp 2026.7.4, pytest 9.1.1, ffmpeg 8.1.2, deno
  - 다운로드 검증 파일 2건: `downloads/` (E1M1-mkrfnA 1.6GB, IEfM972ODcU 1.9GB)
- **검증 결과**:
  - 단위 테스트 13/13 통과 (`uv run pytest`)
  - 통합: 4시간짜리 라이브 아카이브 2건 다운로드 성공, ffprobe로 h264 1920×1080(가용 최고 화질) 확인
  - 오류 경로(에이전트 검증): 무효 URL exit 1 / 미존재 영상 exit 1 + 원인 메시지 / 인자 누락 exit 2 — 3/3 PASS
- **현재 진행도**: MVP 완성 (체크리스트 4/4)
- **남은 미해결**: 기본 `codec=best`에서 음성이 opus로 선택되어 opus-in-MP4 산출 가능 — 일부 구형 플레이어 비호환 (필요 시 `--codec compat` 사용으로 회피, 방침 결정 대기)
- **다음 단계**: Phase 2 착수 여부 사용자 판단 (재생목록/웹 UI/자막 — DESIGN §7)

### 4차 작업 (같은 날)
- **목표**: git 저장소 연결
- **결정사항**: .gitignore에 다운로드 산출물(downloads/, *.mp4, *.part 등)·.venv·로컬 설정 제외
- **산출물**: 로컬 git 저장소 초기 커밋 (6264d02, 11개 파일 — 코드·문서·의존성 잠금)
- **현재 진행도**: 구현 완료(main.py, downloader.py, tests), 로컬 커밋 완료
- **남은 미해결**: GitHub 원격 저장소 연결 (저장소 URL 필요 또는 gh CLI 설치·인증 필요)
- **다음 단계**: 원격 저장소 URL 확보 → `git remote add origin` → `git push -u origin main`

### 5차 작업 (같은 날) — GitHub 연결 완료
- **목표**: 다중 GitHub 계정 체계 구축 및 원격 푸시
- **결정사항**: gh CLI 멀티 계정(`gh auth switch`)으로 KIMHeeKwon(개인)/ETRI-ULSOO(업무) 전환 관리, 전역 CLAUDE.md에 지침 명문화
- **산출물**: https://github.com/KIMHeeKwon/Youtube_Downlaod 에 main 브랜치 푸시 완료 (커밋 3건)
- **현재 진행도**: MVP 구현·검증·원격 연결 모두 완료
- **다음 단계**: Phase 2 착수 여부 판단 (재생목록/웹 UI/자막), opus-in-MP4 호환성 방침 결정
