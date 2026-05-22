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

## LeafGenerator.gh — reference mesh + water sim + evaluator (PR-G)

PR-G 부터 절차적 mesh 생성 (`build_*_mesh`) 폐기. **mesh 는 Rhino reference geometry 에서 GH 로 입력**. 4 개 Py3 컴포넌트로 분리:

1. **mesh_loader** — Rhino Mesh → (verts, faces) JSON
2. **water_sim** — mesh + nozzles → polylines + nozzles JSON
3. **evaluator** — mesh + polylines → metrics JSON
4. **export** — mesh + params + metrics → `runs/<id>/{params.json, leaf.stl, fast_metrics.json}`

`.gh` 는 binary, 수동 빌드. 핵심 로직은 `gh/scripts/{mesh_io,water_sim,evaluator,leaf_generator,export_candidate}.py`. Py3 컴포넌트는 thin wrapper + `importlib.reload` 로 자동 hot-pickup.

### 컴포넌트 (캔버스 배치)

| 역할 | 컴포넌트 | 기본값 권장 |
|------|---------|------------|
| `reference_meshes` | Geometry param (list, Mesh) | Rhino layer 꽃_1 + 꽃대 의 mesh 들 reference |
| `height_total_m` | Number Slider | range 5–15, value 14.0 |
| `landing_radius_m` | Number Slider | range 0.5–3.0, value 1.2 |
| `twist_total_deg` | Number Slider | range -180–180, value 60.0 |
| `candidate_id` | Panel (text) | `cand_0001` |
| `nozzle_points` | Point param (multi-input) | Construct Point + 3 sliders 권장 |
| `flow_rate_lpm` | Number Slider | range 10–100, value 45.0 |
| `nozzle_tilt_deg` | Number Slider | range 0–60, value 0 (수직) |
| `nozzle_azimuth_deg` | Number Slider | range -180–180, value 0 |
| `mesh_loader` | Python 3 Script | 1 input → 3 output: `preview_mesh`, `mesh_json`, `mesh_summary` |
| `water_sim` | Python 3 Script | 5 input → 2 output: `curtain_curves`, `nozzles_json` |
| `evaluator` | Python 3 Script | 2 input → 2 output: `metrics_json`, `summary_text` |
| `export` | Python 3 Script | 5 input → 1 output: `export_summary` |
| `mesh_summary panel`, `metric panel`, `export panel` | Panel | 각 컴포넌트 출력 표시 |

### 와이어

```
reference_meshes ──→ mesh_loader.reference_meshes
                       ├── preview_mesh ──→ (Rhino preview)
                       ├── mesh_json    ──→ water_sim.mesh_json + evaluator.mesh_json + export.mesh_json
                       └── mesh_summary ──→ mesh_summary panel

nozzle_points ─────→ water_sim.nozzle_points
flow_rate_lpm ─────→ water_sim.flow_rate_lpm
nozzle_tilt_deg ───→ water_sim.tilt_deg
nozzle_azimuth_deg → water_sim.azimuth_deg
   water_sim.curtain_curves ──→ (Rhino preview polylines)
   water_sim.nozzles_json   ──→ evaluator.nozzles_json + export.nozzles_json

evaluator.metrics_json ──→ export.metrics_json
evaluator.summary_text ──→ metric panel

height_total_m, landing_radius_m, twist_total_deg, candidate_id ──→ export.*
export.export_summary ──→ export panel
```

### 1. `mesh_loader` 코드 (paste)

```python
import sys, pathlib, json, importlib
import Rhino, Rhino.Geometry as rg

REPO_ROOT = pathlib.Path(r"C:\Users\user\Documents\LFTH_CFD")
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import gh.scripts.mesh_io
importlib.reload(gh.scripts.mesh_io)
from gh.scripts.mesh_io import rhino_mesh_to_tri_data, mesh_summary

doc = Rhino.RhinoDoc.ActiveDoc
m_to_doc = Rhino.RhinoMath.UnitScale(Rhino.UnitSystem.Meters, doc.ModelUnitSystem)
m_to_doc = m_to_doc if m_to_doc != 0 else 1.0
doc_to_m = 1.0 / m_to_doc

# reference_meshes: List[rg.Mesh] (multi-input Geometry param)
meshes_dump = []
for m in reference_meshes:
    verts = [(v.X, v.Y, v.Z) for v in m.Vertices]
    faces = []
    for f in m.Faces:
        if f.IsQuad:
            faces.append((f.A, f.B, f.C))
            faces.append((f.A, f.C, f.D))
        else:
            faces.append((f.A, f.B, f.C))
    meshes_dump.append({"verts": verts, "faces": faces})

verts_m, faces_m = rhino_mesh_to_tri_data(meshes_dump, doc_to_m)
summary = mesh_summary(verts_m, faces_m)

# preview mesh in doc unit
preview = rg.Mesh()
for v in verts_m:
    preview.Vertices.Add(v[0] * m_to_doc, v[1] * m_to_doc, v[2] * m_to_doc)
for f in faces_m:
    preview.Faces.AddFace(f[0], f[1], f[2])
preview.Normals.ComputeNormals()
preview.Compact()

a = preview
b = json.dumps({"verts": verts_m, "faces": faces_m})
c = "verts={} faces={} bbox_m={}".format(
    summary["vert_count"], summary["face_count"], summary["bbox_m"]
)
```

### 2. `water_sim` 코드 (paste) — PR-H particle CFD

`reference_meshes` 를 GH Geometry param 으로 직접 받음 (mesh_json 우회 X).
입력 5개: `reference_meshes` (Mesh, List), `nozzle_points` (Point3d, List), `flow_rate_lpm`, `tilt_deg`, `azimuth_deg`.

```python
# r: trimesh
import sys, pathlib, importlib
import Rhino, Rhino.Geometry as rg
import trimesh
import numpy as np

REPO_ROOT = pathlib.Path(r"C:\Users\user\Documents\LFTH_CFD")
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import gh.scripts.water_sim
importlib.reload(gh.scripts.water_sim)
from gh.scripts.water_sim import simulate_water_curtain

doc = Rhino.RhinoDoc.ActiveDoc
m_to_doc = Rhino.RhinoMath.UnitScale(Rhino.UnitSystem.Meters, doc.ModelUnitSystem)
m_to_doc = m_to_doc if m_to_doc != 0 else 1.0
doc_to_m = 1.0 / m_to_doc

# extract trimesh inline from Rhino Mesh objects (no JSON middle step)
verts, faces = [], []
for m in reference_meshes:
    base = len(verts)
    for v in m.Vertices:
        verts.append((v.X * doc_to_m, v.Y * doc_to_m, v.Z * doc_to_m))
    for f in m.Faces:
        if f.IsQuad:
            faces.append((base + f.A, base + f.B, base + f.C))
            faces.append((base + f.A, base + f.C, base + f.D))
        else:
            faces.append((base + f.A, base + f.B, base + f.C))
tm = trimesh.Trimesh(
    vertices=np.asarray(verts, dtype=float),
    faces=np.asarray(faces, dtype=int),
    process=False,
)

# nozzle points -> meters
nozzles_m = [(p.X * doc_to_m, p.Y * doc_to_m, p.Z * doc_to_m) for p in nozzle_points]

# particle CFD: per nozzle, n_particles_from_flow_rate(flow_rate_lpm) droplets;
# each gets v = sqrt(2gh) in (tilt, azimuth) direction; mesh collisions
# choose specular / diffuse / slide based on impact speed.
trajectories = simulate_water_curtain(
    tm, nozzles_m,
    flow_rate_lpm=flow_rate_lpm,
    tilt_deg=tilt_deg,
    azimuth_deg=azimuth_deg,
    fall_height_m=15.0,
)

curves = []
for traj in trajectories:
    pts = [rg.Point3d(x * m_to_doc, y * m_to_doc, z * m_to_doc) for (x, y, z) in traj.points]
    if len(pts) >= 2:
        curves.append(rg.Polyline(pts).ToNurbsCurve())

a = curves
b = "particles={}, total_pts={}, ended_at_pond={}".format(
    len(trajectories),
    sum(len(t.points) for t in trajectories),
    sum(1 for t in trajectories if t.terminated_by == "pond"),
)
```

### 3. `evaluator` 코드 (paste)

```python
import sys, pathlib, json, importlib

REPO_ROOT = pathlib.Path(r"C:\Users\user\Documents\LFTH_CFD")
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import gh.scripts.evaluator
importlib.reload(gh.scripts.evaluator)
from gh.scripts.evaluator import evaluate

mesh_data = json.loads(mesh_json)
sim_data = json.loads(nozzles_json)

metrics = evaluate(
    mesh_data["verts"], mesh_data["faces"],
    sim_data["polylines_m"], sim_data["nozzles"],
)

a = json.dumps(metrics)
b = "drop_avg={:.2f}m, xy_spread={:.2f}m, pond_cap={:.2f}, impact={:.2f}".format(
    metrics["cascade_drop_m_avg"], metrics["xy_spread_m_avg"],
    metrics["pond_capture_ratio"], metrics["normal_impact_avg"],
)
```

### 4. `export` 코드 (paste)

```python
# r: trimesh
import sys, pathlib, json, importlib

REPO_ROOT = pathlib.Path(r"C:\Users\user\Documents\LFTH_CFD")
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import gh.scripts.leaf_generator
import gh.scripts.export_candidate
importlib.reload(gh.scripts.leaf_generator)
importlib.reload(gh.scripts.export_candidate)
from gh.scripts.leaf_generator import build_params_dict
from gh.scripts.export_candidate import export_candidate

mesh_data = json.loads(mesh_json)
sim_data = json.loads(nozzles_json)

params_dict = build_params_dict(
    candidate_id, height_total_m, landing_radius_m, twist_total_deg,
    nozzles=sim_data["nozzles"], source_mesh_path="rhino:reference_meshes",
)

out_dir = REPO_ROOT / "runs" / candidate_id
summary = export_candidate(mesh_data["verts"], mesh_data["faces"], params_dict, out_dir)

# also write metrics.json for fast-sim diff
if metrics_json:
    metrics = json.loads(metrics_json)
    (out_dir / "rough_cfd_metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")

a = "OK | {} | tri={} | vert={}".format(
    summary["stl_path"], summary["triangle_count"], summary["vertex_count"],
)
```

### 단위 변환 노트

- `params.json` + STL = **meters** (불변)
- Rhino preview = **doc unit** (mm/m 어느 쪽이든 자동 scale)
- `Rhino.RhinoMath.UnitScale(Rhino.UnitSystem.Meters, doc.ModelUnitSystem)` 가 m→doc 환산. `doc_to_m = 1 / m_to_doc`.
- 따라서: build wrapper 가 verts 를 doc unit 으로 곱해서 preview Mesh 생성. export wrapper 가 verts 를 다시 m 으로 환원해서 STL/params 작성.

### 사용자 수동 빌드 단계 (PR-B)

1. Rhino 8 + Grasshopper 열고 `gh/LeafGenerator.gh` 열기 (기존 cylinder 버전)
2. 신규 컴포넌트 추가: `Point` Param (multi-input), `Number Slider` (flow_rate, 10–100)
3. `build` 컴포넌트 입력 port 2개 추가 (`nozzle_points`, `flow_rate_lpm`), 출력 port 1개 추가 (`d`)
4. `build` / `export` Python 코드를 위 두 블록으로 paste
5. `File → Save` 로 `gh/LeafGenerator.gh` 덮어쓰기
6. `git add gh/LeafGenerator.gh && git commit -m "feat(gh): LeafGenerator water curtain + unit scale"`

### 동작 확인 (end-to-end)

```powershell
uv run leaflab init-run cand_water_v11
# Rhino에서 LeafGenerator.gh 열기, candidate_id panel을 "cand_water_v11"로 변경
# nozzle 점 3-5개 캔버스에 배치, flow_rate=45
# → runs/cand_water_v11/{params.json, geometry/leaf.stl} 자동 작성

uv run leaflab check-geometry runs/cand_water_v11
uv run leaflab fast-sim runs/cand_water_v11 -n 200
uv run leaflab validate runs/cand_water_v11/fast_metrics.json
```

세 단계 다 `ok:` 또는 exit 0 이면 성공.

### MVP 한계 (의도된 trade-off)

- 형상: 3-leaf dome stack. 실제 leaf 보다 단순 (no channel/spine NURBS — Phase D refine).
- 슬라이더 5개. 나머지 schema 필드는 `build_params_dict` 안에서 default.
- Parabolic fall (oblique velocity) 미지원 — vertical drop만.

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
