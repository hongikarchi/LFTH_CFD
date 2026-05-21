# Leaf Water Lab

Big Leaf 축소형 폭포 조형물 — 파라메트릭 리프 형상 생성 + 빠른 물 접촉 평가 + 구조/시각 점수.

## 프로젝트 개요

기존 30m 수직 수공간 Big Leaf 안을 **15m 자유낙수 + 15m 이하 압축 리프** 구성으로 재설계.
- 약 15m 자유낙하한 물 (≈17.2 m/s) 을 첫 리프가 낮은 각도로 받아 수막으로 전환
- 2~3개 리프가 연속 쉘처럼 작동 (조형 + 물길 + 구조 통합)
- Rhino/Grasshopper로 형상 생성 → Python CLI로 평가/스코어링 → OpenFOAM/Blender (Phase F 이후)

자세한 설계 배경은 `big_leaf_water_generator_plan.md`, 셋업/협업 방침은 `docs/plans/2026-05-21-setup.md` 참조.

## 셋업

전제: Python 3.11+, [uv](https://docs.astral.sh/uv/), Rhino 8 (선택, GH 작업 시).

```bash
git clone <repo-url>
cd LFTH_CFD
uv sync --all-groups
uv run leaflab --help
uv run pytest
```

## 사용

### 후보 초기화

```bash
uv run leaflab init-run cand_0001
```

→ `runs/cand_0001/params.json` (템플릿) + `runs/cand_0001/geometry/` 디렉토리 생성.

### 검증

```bash
uv run leaflab validate runs/cand_0001/params.json
```

### Grasshopper 연동 (Phase B 이후)

`gh/LeafGenerator.gh` 열고, `params.json` 경로 입력 → `leaf.stl` export.
자세한 내용 `gh/README.md`.

## 폴더 구조

```text
LFTH_CFD/
├── leaflab/              # Python 패키지 (uv venv, Python 3.11+)
│   ├── schema/           # Pydantic v2 모델 (params, metrics, candidate)
│   ├── cli/              # Typer 명령
│   ├── geometry/         # (Phase C 이후)
│   ├── fast_sim/         # (Phase C)
│   └── scoring/          # (Phase D)
├── gh/                   # Grasshopper (Rhino 8 CPython 3.9 임베디드)
│   ├── LeafGenerator.gh
│   └── scripts/          # 외부 .py — leaflab import 금지, 파일 경계 통신
├── tests/                # pytest
├── configs/              # 기본 설정 JSON
├── docs/plans/           # 설계 결정 스냅샷
├── runs/                 # gitignore — 후보별 데이터 (재생성 가능)
└── external_data/        # gitignore — 대용량 외부 스토리지 (rclone 동기화)
```

## 핵심 규칙

- **Pydantic v2** 사용
- 모든 `params.json` / `metrics.json`에 **`schema_version`** 필수
- `leaflab/`은 Python 3.11+, `gh/scripts/`는 Python 3.9 (Rhino 8 임베디드 호환)
- `gh/scripts/`에서 `leaflab` import 금지 (CI 강제)
- `.gh` 파일 수정 전 단일 owner 확인 (binary diff 충돌 위험)
- 대용량 파일 (STL, MP4, OpenFOAM 결과) 은 `external_data/` 경유, git에 안 올림

## 개발

`CONTRIBUTING.md` 참조.

## Phase / 작업 추적

GitHub Issues + Milestones로 추적. 영구 phase 문서는 만들지 않음 (stale 방지).

```bash
gh issue list --milestone "Phase A — 인프라"
gh issue list --label in-progress
```

## 라이선스

Internal — 협의 전 공개 배포 금지.
