# Leaf Water Lab — Claude Code 메모

## 세션 시작 protocol

1. **항상 plan mode로 시작**. 첫 메시지에 plan mode 진입 권장.
2. 현재 phase / 진행 상태는 GitHub Issues + Milestone에서 확인:
   - `gh issue list --milestone "Phase A — 인프라"`
   - `gh issue list --label "in-progress"`
   - `gh issue list --assignee @me --state open`
3. plan 작성 후 작업 시작. 세션 내 잘게 쪼개기는 TaskCreate.

## 빌드 / 테스트 / 린트

- `uv sync` — 의존성 설치 (lockfile 기반)
- `uv run leaflab --help` — CLI 동작 확인
- `uv run pytest` — 테스트
- `uv run ruff check .` — 린트
- `uv run ruff format .` — 포맷
- `uv run mypy leaflab` — 타입 체크

## 핵심 규칙

- **Pydantic v2** 사용 (`model_validator`, `field_validator`)
- **schema_version 필드 필수** — 모든 `params.json` / `metrics.json`에
  - **rigid `Literal` 금지**. Discriminator 패턴 사용:
    1. raw JSON load → `schema_version` 필드 inspect
    2. version별 Pydantic 모델 dict로 dispatch (`MODELS = {"1.0": ParamsV1, "1.1": ParamsV2}`)
    3. 매칭 모델로 parse
  - migrate 위해 구버전 모델도 보존
- **`runs/`는 disposable**. schema가 진실의 원천.
- **Rhino 8 GH = CPython 3.9 임베디드** 가정.
  - `gh/scripts/*.py`는 **`leaflab/` import 절대 금지**
  - 통신은 JSON/STL 파일 경계로만
  - `gh/scripts/`는 Python 3.9 문법 (`match`, `X | Y` 타입, `Self` 등 금지)
  - `leaflab/`은 Python 3.11+ 자유롭게
- **`.gh` 파일 수정 전 사용자 confirm 필수** (binary diff 충돌 위험)
- **외부 stl/mp4는 `external_data/` (gitignore)**. 절대 git add 금지.

## 코드 스타일

- Type hints 필수
- docstring은 함수 의도/제약만, what 설명 금지
- pytest + fixtures (`tests/fixtures/`)
- 새 CLI 명령은 `leaflab/cli/<command>.py` 별도 파일

## 외부 도구

- Rhino/GH: `gh/` (외부 .py import 패턴, 파일 경계 통신)
- WSL2 OpenFOAM: Phase F 이후 (지금 없음)

## 작업 추적 (영구 문서 없음 정책)

- Phase 진행 상황 문서는 **만들지 않음** (stale 방지)
- 작업 단위 = **GitHub Issue**
- Phase 단위 = **GitHub Milestone**
- 세션 내 분해 = **`TaskCreate`** (비영구)
- 큰 설계 결정 스냅샷 = plan mode 출력물을 `docs/plans/<YYYY-MM-DD>-<topic>.md`로 보관 (역사 기록, 재로드 금지)

## 참고 문서

- `big_leaf_water_generator_plan.md` — 기술 설계 (원본 plan)
- `docs/plans/2026-05-21-setup.md` — 셋업/협업 plan (메타 결정)
- `gh/README.md` — Rhino 8 CPython 셋업 가이드
- `CONTRIBUTING.md` — git workflow + PR 규칙
