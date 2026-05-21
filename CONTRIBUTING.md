# Contributing — Leaf Water Lab

## 협업 모델 (2인 풀스택)

- `main` 브랜치 보호: 직접 push 금지, PR 필수, 최소 1명 approve
- feature 브랜치: `feature/phaseA-cli-skeleton`, `fix/schema-validation` 등
- Conventional Commits 권장: `feat:`, `fix:`, `refactor:`, `docs:`, `chore:`, `test:`
- 매일 작업 전: `git fetch && git rebase origin/main`
- PR 사이즈: 한 Issue = 한 PR (작게)

## 작업 단위 = GitHub Issue

영구 phase/task 문서는 만들지 않음. 모든 작업 추적은 GitHub:

- Milestone: `Phase A`, `Phase B`, ...
- Label: `phase-A`, `schema-change`, `gh-binary`, `bug`, `infra`, `in-progress`
- PR description에 `Closes #<issue>` 명시

세션 시작 시:
```bash
gh issue list --milestone "Phase A — 인프라" --state open
gh issue list --assignee @me --state open
```

## 브랜치 / PR 흐름

1. Issue 선택 → `in-progress` 라벨 + 본인 assign
2. 브랜치 생성: `git checkout -b feature/<short-desc>`
3. 커밋 (Conventional Commits)
4. push → PR open
5. CI 통과 확인
6. (옵션) Claude의 `cavecrew-reviewer` 실행 → 발견 사항 처리
7. 사람 리뷰 → approve → merge
8. Issue 자동 close

## Schema 변경 PR (`schema-change` 라벨)

둘 다 approve 필요. 추가 체크:
- 새 모델 추가 (구버전 보존, deprecate 주석)
- `MODELS` dispatch dict 업데이트
- `leaflab migrate` 함수 작성
- migration unit test 추가
- PR description에 영향받는 후보 수 명시

## `.gh` 바이너리 PR (`gh-binary` 라벨)

- **단일 owner 원칙**: 동시 수정 금지. 작업 전 다른 사람에 알림.
- PR description에 변경 요약: "added port `landing_radius_m`", "renamed cluster X → Y"
- merge 즉시 (장기 보관 금지 — 충돌 위험)
- 큰 구조 변경은 `LeafGenerator_v2.gh` 새 파일로

## 코드 스타일

- Python 3.11+ (leaflab), Python 3.9 호환 (gh/scripts)
- `uv run ruff check .` / `uv run ruff format .` 통과
- `uv run mypy leaflab` 통과
- `uv run pytest` 통과
- type hints 필수, docstring은 의도/제약만
- 새 CLI 명령은 `leaflab/cli/<command>.py` 별도 파일

## 대용량 파일 정책

- `runs/` 와 `external_data/` 는 gitignore
- STL/MP4/CFD 결과는 회사 SMB share에 보관
- **SMB host는 머신마다 다를 수 있음**:
  - DNS 풀리는 머신: `\\Lifethings\Lifethings_02\PROJECTS\2026 Project\2605-서부티앤디 건축물 미술작품\06_3D`
  - DNS 안 풀리는 머신: `\\192.168.0.100\Lifethings_02\PROJECTS\2026 Project\...`
  - (정확한 하위 폴더는 TBD)
- **per-machine 환경 변수 사용 권장**:
  ```powershell
  [Environment]::SetEnvironmentVariable("LEAFLAB_EXTERNAL_ROOT", "<자기 머신에서 풀리는 경로>", "User")
  ```
- 코드/스크립트는 `$env:LEAFLAB_EXTERNAL_ROOT` 만 참조 (하드코딩 금지)
- 접근:
  - UNC 경로 직접 사용, 또는
  - 네트워크 드라이브 매핑: `net use Z: \\<host>\Lifethings_02`, 또는
  - 오프라인 작업 시 로컬 미러: `scripts/sync_external.ps1 pull`
- 후보 부산물 구조: `$LEAFLAB_EXTERNAL_ROOT/leaf-water-lab/<candidate_id>/{leaf.stl,openfoam_run,blender_renders,...}`
- 절대 git LFS / git add 금지

## Conflict 처리

- `.gh` 충돌: 일찍 머지한 쪽 우선, 늦은 쪽이 Rhino 열고 재작업
- `.py` 충돌: 표준 git merge
- schema 충돌: 둘 다 모여 토의 (15분)

## 매일 끝 / 주간

- WIP 라도 본인 브랜치에 push
- 작업 중인 Issue에 짧은 진행 코멘트
- 주간: 15~30분 동기화 (schema 변경, 큰 디자인 결정, 후보 비교)

## Claude Code 사용

- 세션 시작 시 plan mode 진입 (`.claude/CLAUDE.md` 참조)
- 큰 설계 결정은 plan 파일을 `docs/plans/<date>-<topic>.md`로 보관
- 일상 작업은 `TaskCreate`로 세션 내 분해
- 작업 유형별 추천 agent:
  - `cavecrew-builder` — 1~2 파일 수술적 수정
  - `cavecrew-investigator` — read-only 코드 위치
  - `cavecrew-reviewer` — PR/diff 리뷰
  - `Plan` — 구현 전략 설계
