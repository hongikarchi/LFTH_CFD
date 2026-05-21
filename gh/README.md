# gh/ — Grasshopper 연동

Rhino 8 (Grasshopper) ↔ leaflab Python CLI 의 통신 계층.

## 환경 전제

- **Rhino 8** (Grasshopper 1, **CPython 3.9** 임베디드 — `Python 3 Script` 컴포넌트)
- 이는 `leaflab/` 의 uv venv (Python 3.11+) 와 **다른 인터프리터**

## 절대 규칙

### 1. `gh/scripts/*.py` 는 `leaflab` import 금지

GH 임베디드 Python은 3.9. `leaflab/`은 3.11+ 문법(`X | Y` 타입, `match`, `Self` 등)을 사용함 → GH에서 import 시 SyntaxError.

대신 **파일 경계 통신** 사용:
- GH → `gh/scripts/export_*.py` → JSON/STL 파일
- 사용자가 터미널에서 `leaflab` 명령 실행 → 결과 JSON 파일
- GH → `gh/scripts/import_results.py` → 결과 JSON 읽어서 GH로

CI에서 강제: `gh/scripts/`에 `import leaflab` 발견 시 빌드 실패.

### 2. `gh/scripts/`는 Python 3.9 문법

금지:
- `X | Y` 타입 (대신 `Optional[X]`, `Union[X, Y]`)
- `match` 문
- `Self` 타입 (typing_extensions에서 import 가능하지만 가급적 피함)
- `*tuple[int, ...]` 같은 PEP 646

허용:
- type hints (`Optional`, `List`, `Dict`, `Tuple` 사용)
- f-strings
- pathlib
- dataclasses

### 3. `.gh` 파일 단일 owner 원칙

binary diff 불가. 동시 수정 금지. 작업 전 협업자에 알림.

큰 구조 변경 시 새 파일(`LeafGenerator_v2.gh`)로 분리 후 v1 삭제.

## 사용법 (Phase B 이후)

### Rhino 8 GH에서 외부 모듈 import

GH `Python 3 Script` 노드에서:

```python
import sys
from pathlib import Path

# repo 루트를 sys.path에 추가
REPO_ROOT = Path(r"C:\Users\user\Documents\LFTH_CFD")
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from gh.scripts.export_candidate import export_candidate

# GH 입력: mesh, params_dict
export_candidate(mesh, params_dict, REPO_ROOT / "runs" / "cand_0001")
```

### pip 패키지 설치 (`# r:` 매직)

trimesh 같은 PyPI 패키지가 GH 안에서 필요하면:

```python
# r: trimesh
# r: numpy

import trimesh
import numpy as np
```

처음 실행 시 GH가 자동으로 PyPI에서 설치.

### 워크플로우

1. GH 정의 열기 (`gh/LeafGenerator.gh`)
2. 파라미터 슬라이더 조정
3. Export 노드 트리거 → `runs/cand_xxxx/params.json` + `geometry/leaf.stl` 작성
4. 터미널에서:
   ```bash
   uv run leaflab check-geometry runs/cand_xxxx
   uv run leaflab fast-sim runs/cand_xxxx
   uv run leaflab score runs/cand_xxxx
   ```
5. GH `Import Results` 노드로 점수 시각화

## 파일

- `LeafGenerator.gh` — 메인 generator (Phase B에서 작성)
- `KarambaSetup.gh` — 구조 검토 (Phase E)
- `scripts/export_candidate.py` — params + mesh → JSON/STL (Phase B)
- `scripts/import_results.py` — 결과 JSON → GH 시각화 (Phase D 이후)
- `scripts/export_karamba_metrics.py` — Karamba 결과 export (Phase E)

## 의존성 격리 검증

CI가 자동 확인:
```bash
grep -rn "import leaflab" gh/scripts/  # 발견 시 실패
grep -rn "from leaflab" gh/scripts/    # 발견 시 실패
ruff check --target-version py39 gh/scripts/  # 3.9 호환 확인
```

로컬에서 확인하려면:
```bash
uv run ruff check --target-version py39 gh/scripts/
```
