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

- `LeafGenerator.gh` — 메인 generator (Phase B에서 작성, 아래 가이드)
- `KarambaSetup.gh` — 구조 검토 (Phase E)
- `scripts/export_candidate.py` — params + mesh → JSON/STL (Phase B)
- `scripts/leaf_generator.py` — MVP geometry + params dict builder (Phase B)
- `scripts/import_results.py` — 결과 JSON → GH 시각화 (Phase D 이후)
- `scripts/export_karamba_metrics.py` — Karamba 결과 export (Phase E)

---

## LeafGenerator.gh — Phase B MVP 빌드 가이드

`.gh`는 binary 라서 자동 생성 한계 있음(GH_MCP `add_component` 는 컴포넌트 placement만 지원, 코드 주입 불가). 한 번만 수동 빌드, 이후 git에 commit.

### 컴포넌트 (캔버스 배치)

| 역할 | 컴포넌트 | 기본값 권장 |
|------|---------|------------|
| `height_total_m` | Number Slider | range 5–15, value 14.0 |
| `landing_radius_m` | Number Slider | range 0.5–3.0, value 1.2 |
| `twist_total_deg` | Number Slider | range -180–180, value 60.0 |
| `candidate_id` | Panel (text) | `cand_0001` |
| `build` | Python 3 Script | 4 input: `height_total_m`, `landing_radius_m`, `twist_total_deg`, `candidate_id` / 3 output: `mesh`, `params_dict`, `candidate_id` |
| `export` | Python 3 Script | 3 input: `mesh`, `params_dict`, `candidate_id` / 1 output: `summary` |
| `summary` | Panel | (출력 표시) |

### 와이어

```
height_total_m ───┐
landing_radius_m ─┼→ build.input(0..2)
twist_total_deg ──┘
candidate_id ────→ build.candidate_id

build.mesh ──────→ export.mesh
build.params_dict → export.params_dict
build.candidate_id → export.candidate_id

export.summary ──→ summary panel
```

### `build` 컴포넌트 코드 (paste)

```python
# r: trimesh
import sys, pathlib
REPO_ROOT = pathlib.Path(r"C:\Users\user\Documents\LFTH_CFD")
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from gh.scripts.leaf_generator import build_mvp_mesh, build_params_dict
import Rhino.Geometry as rg

verts, faces = build_mvp_mesh(height_total_m, landing_radius_m, twist_total_deg)
params_dict = build_params_dict(candidate_id, height_total_m, landing_radius_m, twist_total_deg)

# verts/faces -> RhinoCommon Mesh for GH preview
mesh = rg.Mesh()
for v in verts:
    mesh.Vertices.Add(v[0], v[1], v[2])
for f in faces:
    mesh.Faces.AddFace(f[0], f[1], f[2])
mesh.Normals.ComputeNormals()
mesh.Compact()

a = mesh           # output 0: mesh
b = params_dict    # output 1: params_dict
c = candidate_id   # output 2: candidate_id (pass-through)
```

`REPO_ROOT` 절대경로는 각자 머신에 맞춰 수정 (TODO: 환경변수 LEAFLAB_REPO_ROOT로 빼는 게 깔끔 — Phase C 작업).

### `export` 컴포넌트 코드 (paste)

```python
# r: trimesh
import sys, pathlib
REPO_ROOT = pathlib.Path(r"C:\Users\user\Documents\LFTH_CFD")
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from gh.scripts.export_candidate import export_candidate

# convert RhinoCommon Mesh -> vert/face lists
verts = [(v.X, v.Y, v.Z) for v in mesh.Vertices]
faces = []
for f in mesh.Faces:
    if f.IsQuad:
        faces.append((f.A, f.B, f.C))
        faces.append((f.A, f.C, f.D))
    else:
        faces.append((f.A, f.B, f.C))

out_dir = REPO_ROOT / "runs" / candidate_id
summary = export_candidate(verts, faces, params_dict, out_dir)

a = "OK | {} | tri={} | vert={}".format(
    summary["stl_path"], summary["triangle_count"], summary["vertex_count"]
)
```

### 빌드 + commit

1. Rhino 8 + Grasshopper 열기 (`GH_MCP` 컴포넌트 없는 fresh 캔버스 권장 — 협업자 머신 호환성)
2. 위 컴포넌트 배치 + 와이어 + 코드 paste
3. `File → Save As...` → `C:\Users\user\Documents\LFTH_CFD\gh\LeafGenerator.gh`
4. `git add gh/LeafGenerator.gh && git commit -m "feat: Phase B.2 LeafGenerator.gh skeleton"`

### 동작 확인 (end-to-end)

```powershell
# 0. 후보 디렉토리 셋업 (init-run 은 template만 만들고, GH가 덮어씀)
uv run leaflab init-run cand_phaseb_e2e

# 1. Rhino에서 LeafGenerator.gh 열기, candidate_id panel을 "cand_phaseb_e2e"로 변경
#    -> 자동 recompute -> runs/cand_phaseb_e2e/{params.json, geometry/leaf.stl} 작성

# 2. STL 검증
uv run leaflab check-geometry runs/cand_phaseb_e2e

# 3. 결과 metrics 검증
uv run leaflab validate runs/cand_phaseb_e2e/geometry_metrics.json
```

세 단계 다 `ok:` 출력하면 Phase B 완료.

### MVP 한계 (의도된 trade-off)

- 형상: 단순 tapered + twisted cylinder. 실제 leaf 아님.
- 슬라이더 3개만. 모든 schema 필드 노출 X.
- Spine / leaf profile / rim / channel — Phase C 또는 후속 task.

이 단계 목표는 GH ↔ leaflab CLI **파이프라인 동작 검증** 이지 최종 형상 X.

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

---

## MCP 자동화 — alfredatnycu/grasshopper-mcp

이 프로젝트는 Claude Code가 Grasshopper 정의를 자동 빌드/수정할 수 있도록 `alfredatnycu/grasshopper-mcp` 사용 가능. 선택적, per-machine 설정.

### 무엇

- GH 안에 `GH_MCP` 컴포넌트 + Python bridge 서버
- Claude (MCP client) → bridge → GH 컴포넌트 생성/연결/Python 코드 주입
- 자세한 내용: https://github.com/alfredatnycu/grasshopper-mcp

### 설치 (per-machine)

#### A. Python bridge

leaflab venv 밖에서 (글로벌 또는 별도 venv):

```powershell
pip install grasshopper-mcp
# entry point 확인
python -m grasshopper_mcp.bridge --help
```

#### B. `.gha` 컴포넌트 찾아서 복사

```powershell
pip show grasshopper-mcp                                                # Location 라인 확인
$loc = (pip show grasshopper-mcp | Select-String "^Location:").ToString().Split(":",2)[1].Trim()
Get-ChildItem -Path $loc -Recurse -Filter "GH_MCP.gha"                  # 정확한 경로 찾기
Copy-Item "<found-path>\GH_MCP.gha" "$env:APPDATA\Grasshopper\Libraries\"
```

`.gha`가 pip 패키지에 없으면 GitHub releases에서 직접: https://github.com/alfredatnycu/grasshopper-mcp/releases

Rhino 8 재시작 → GH 열고 컴포넌트 검색 (`GH_MCP`).

#### C. `.mcp.json` 로컬 (gitignore'd, 커밋 X)

repo 루트에 `.mcp.json` 작성:

```json
{
  "mcpServers": {
    "grasshopper": {
      "command": "<python.exe in pip env>",
      "args": ["-m", "grasshopper_mcp.bridge"]
    }
  }
}
```

`<python.exe in pip env>`는 Step A pip 실행 환경의 python 절대경로. 예:
`C:\Users\<user>\AppData\Local\Programs\Python\Python312\python.exe` 또는 venv path.

#### D. Claude Code 재시작 + 검증

1. Claude Code 종료 후 재시작
2. Claude tool 목록에 `mcp__grasshopper__*` 등장 확인
3. Rhino 8 + Grasshopper 열기
4. 빈 GH 캔버스에 `GH_MCP` 컴포넌트 배치
5. Claude로 trivial MCP call 시도 (예: 캔버스 상태 조회) → 응답 정상이면 OK

### 사용 패턴 (Claude 측)

Claude가 MCP tool 사용해서:
1. 새 GH 정의 (또는 기존 .gh 수정)
2. Python 3 Script 컴포넌트 생성 + 코드 텍스트 주입
3. 컴포넌트 간 wire 연결
4. 결과를 `.gh` 파일로 저장

사용자는 Rhino에서 시각 확인 + slider 조정.

### 트러블슈팅

- **Claude 재시작 후 mcp tool 안 보임**: `.mcp.json` 의 command 경로 확인. PATH 통과 안 됐을 가능성.
- **GH_MCP 컴포넌트 안 보임**: `%APPDATA%\Grasshopper\Libraries\` 에 .gha 있는지 확인. Rhino 완전 종료 후 재시작.
- **bridge 연결 실패**: GH_MCP 컴포넌트가 활성화돼있는지 확인. 컴포넌트 우클릭 → enable.
- **Python 3.9 호환성**: bridge는 별도 Python 환경. Rhino 8 임베디드 CPython 과 무관.

### 협업자 노트

협업자 머신에 Rhino 없으면 MCP 사용 불가. `.mcp.json` 은 gitignore — 각자 설치 시 작성. 협업자가 Rhino 사용 시 위 가이드 따라 셋업.
