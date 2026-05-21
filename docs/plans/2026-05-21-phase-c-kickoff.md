# Phase C kickoff — Fast water proxy

## Context

Phase B 종료(B.1 schema/CLI, B.2 LeafGenerator.gh, B.3 export, B.4 check-geometry, +gap PR for cross-field validators / algorithm_version / migrate CLI). Phase C 진입.

목적: 후보 100~1000개를 OpenFOAM 전에 빠르게 걸러낼 particle-based water proxy. **정확 CFD 아님** — first contact location, impact angle, attachment, edge escape, drain target 까지 빠르게 평가.

원본 plan: `big_leaf_water_generator_plan.md §10`.

## Sub-tasks (`docs/plans/2026-05-21-setup.md §1`)

- **C.1** `leaflab/fast_sim/particle_drop.py` — water curtain 위 입자 샘플링 + 자유낙하 초기화
- **C.2** `leaflab/fast_sim/impact_angle.py` — trimesh raycast → first contact + surface normal + `normal_impact_score = abs(dot(Vwater, Nsurface))`
- **C.3** sliding tangent flow + edge escape — velocity tangent 투영, gravity 성분 + tangent flow, rim/edge 도달 시 escape 기록
- **C.4** `splash_proxy.py` + `drain_target.py` — 곡률 변화에 의한 detachment risk, target pond 영역 도달 비율
- **C.5** `leaflab/cli/fast_sim.py` — `leaflab fast-sim runs/<id>` 명령 → `fast_metrics.json` 생성

검증 (plan §13.C): 후보 1개에 `fast_metrics.json` 생성, `normal_impact_score < 0.25` 필터 동작 확인.

## Folder + 파일

```
leaflab/fast_sim/
  __init__.py
  particle_drop.py        # C.1
  impact_angle.py         # C.2
  sliding.py              # C.3 (sliding + edge escape)
  splash_proxy.py         # C.4
  drain_target.py         # C.4
  attachment_proxy.py     # C.3 (attachment_length)
  edge_escape.py          # C.3 (helper)

leaflab/cli/
  fast_sim.py             # C.5

tests/
  fixtures/
    flat_leaf.stl         # 1x1m 평면 (수평) — impact_angle 90° 검증
    angled_leaf.stl       # 30° 기울어진 평면 — normal_impact_score = sin(30°) = 0.5
    cylinder_leaf.stl     # 현재 build_mvp_mesh 와 비슷한 cylinder — 종합 smoke
  test_fast_sim_particle_drop.py
  test_fast_sim_impact.py
  test_fast_sim_sliding.py
  test_fast_sim_cli.py
```

## 의존성

이미 있음 (uv): `numpy`, `trimesh`, `scipy`.

추가 검토:
- `trimesh.ray.ray_triangle.RayMeshIntersector` (raycast — 기본 모듈)
- `trimesh.ray.ray_pyembree` (선택, 큰 mesh + 많은 ray 시 10x+ 빠름. `# r:` 매직 또는 uv add)

초기에는 stdlib raycast(`ray_triangle`)로 충분 (후보 1000개 × ray 500개 = 50만 raycast, 수 초).

## 기본 알고리즘 (plan §10.4)

```python
# 의사코드 — leaflab/fast_sim/run.py 의 top-level loop
def run_fast_sim(mesh: trimesh.Trimesh, params: ParamsV1) -> FastMetricsV1:
    particles = sample_water_curtain(
        params.water.curtain_radius_inner_m,
        params.water.curtain_radius_outer_m,
        n=PARTICLE_COUNT,  # default 500
        z_start=params.water.fall_height_m + params.geometry.top_leaf_z_m,
    )
    v_init = sqrt(2 * g * fall_height_m)  # 17.2 m/s @ 15m
    # raycast to first contact
    hits, normals, face_ids = raycast_down(mesh, particles, v_init)
    # impact metrics
    normal_impact = abs(einsum("ij,ij->i", v_water, normals))
    # tangent flow simulation — N steps along surface
    trajectories = slide_along_surface(mesh, hits, v_init, normals, n_steps=200)
    # classify endpoints
    escaped = is_off_edge(mesh, trajectories[:, -1])
    captured = in_target_pond(trajectories[:, -1], params.water.target_drain_position, params.water.pond_radius_m)
    # aggregate
    return FastMetricsV1(
        candidate_id=params.candidate_id,
        water_proxy=WaterProxyMetrics(
            impact_angle_mean_deg=degrees(arcsin(normal_impact.mean())),
            normal_impact_score=normal_impact.mean(),
            attachment_length_m=trajectory_lengths.mean(),
            edge_escape_rate=escaped.mean(),
            drain_target_error_m=median_distance_to_pond,
            splash_proxy=splash_score,
            ...
        ),
        geometry_proxy=geometry_proxy_metrics(mesh),
    )
```

## Sprint 분해 (PR 단위)

1. **PR-C1**: `particle_drop.py` + tests (curtain 샘플링, 결정론적 seed)
2. **PR-C2**: `impact_angle.py` + tests (flat/angled fixture 로 정확도 검증)
3. **PR-C3**: `sliding.py` + `edge_escape.py` + `attachment_proxy.py` + tests
4. **PR-C4**: `splash_proxy.py` + `drain_target.py` + tests
5. **PR-C5**: `leaflab/cli/fast_sim.py` + e2e test (runs/cand_x → fast_metrics.json round-trip via leaflab schema)

각 PR 작아야 review 쉬움. PR-C1 ~ PR-C5 순차 의존 (C5 가 C1-C4 다 사용).

## 위험 + mitigation

| 위험 | 대응 |
|------|------|
| `RayMeshIntersector` 대형 mesh 느림 | pyembree 옵션 + 후보당 PARTICLE_COUNT 조절 (CLI flag) |
| 곡률 변화 detachment 휴리스틱 brittle | C.4 에서 threshold만 calibrate, real validation 은 Phase F (OpenFOAM) 으로 미룸 |
| `normal_impact_score < 0.25` 너무 strict → 후보 다 fail | initial threshold 는 plan 권장, 실측 후 relax |
| sliding 알고리즘 수치 불안정 (step size, gravity 분해) | unit test 로 known 형상 (flat, sphere) 결과 검증 |
| pareto rank Phase D 이후 → 현재 단일 후보 평가만 | C.5 는 단일 후보 metric 만, ranking 은 Phase D |

## 첫 세션 (Phase C 시작) 시작 protocol

CLAUDE.md `세션 시작 protocol`:
1. plan mode 진입
2. `gh issue list --milestone "Phase C — Fast water proxy"` 확인 (gh CLI 없으면 web)
3. 이 문서 (`docs/plans/2026-05-21-phase-c-kickoff.md`) 인용
4. PR-C1 부터 시작

## Out of scope (Phase D 이후)

- score_water / score_structure / score_visual 통합 → Phase D
- Pareto ranking → Phase D
- Visual silhouette metric → Phase D
- Karamba 구조 metric → Phase E
- OpenFOAM CFD 검증 → Phase F
