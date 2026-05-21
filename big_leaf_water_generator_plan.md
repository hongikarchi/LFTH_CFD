# Big Leaf 축소형 폭포 조형물: 커스텀 제네레이터 개발 계획

작성 목적: 이 문서는 현재 채팅에서 정리된 설계 방향, 시뮬레이션 워크플로우, 평가 요소, 데이터 schema, 프로그램 구성, Claude Code 기반 개발 계획을 하나의 실행 문서로 통합한 것이다.

---

## 0. 프로젝트 핵심 요약

### 기존 조건

기존 Big Leaf 안은 쇼핑몰 보이드 공간의 중심 조형물로 계획되었고, 다음 특징을 갖는다.

- 약 30m 높이까지 물을 올려 순환시키는 수직 수공간 시스템
- Big Leaf 조형물 자체는 약 24.7m급으로 읽히는 대형 금속 조형물
- 기존 파트 높이 기준: 약 1.7m / 5m / 9m / 13m / 19m / 24.7m
- 기존 협의안에서 상부 커튼형 분수 구간과 자연 배수 구간이 함께 계획됨
- 2중 폭포 반경: 약 1m / 2m
- 노즐 간격: 약 40mm
- 각 노즐 유량 검토값: 약 30~60 LPM
- 기존 Big Leaf는 모두가 좋아했지만 제작비와 금속 물량이 과도함

### 새 설계 방향

기존 Big Leaf의 조형적 인상은 유지하되, 비용과 제작 난이도를 낮추기 위해 다음 방향으로 재구성한다.

> **30m 수직 낙수 장면은 유지하고, 금속 조형물은 15m 이하로 압축한다.**

구체적으로는:

- 상부 약 30m 지점에서 물이 떨어진다.
- 약 30m → 15m 구간은 조형물 없이 자유낙수로 구성한다.
- 약 15m 이하 구간에 기존 Big Leaf와 유사한 리프 2~3개를 배치한다.
- 리프들은 독립 오브젝트처럼 보이기보다 하나의 연속된 싱글 서페스 또는 연속 쉘처럼 읽히게 한다.
- 첫 번째 리프는 15m 자유낙하한 물을 최대한 튀지 않게 받아야 한다.
- 하부 리프들은 물을 회전시키고, 모으고, 폰드로 유도한다.
- 조형물은 황동 캐스팅을 기본으로 하고, 자동차 페인트 계열의 고광택 마감으로 계획한다.
- 내부 구조를 드러내지 않고, 리프 자체의 곡률, 림, 두께 변화, 중앙 물길을 구조와 수리 기능으로 통합한다.

### 설계 핵심 문장

> 본 제안은 기존 Big Leaf의 유기적 리프 형상과 수직적 인상을 유지하되, 조형물의 물리적 높이를 15m 이하로 낮추고 상부 15m 구간을 자유낙수의 장면으로 전환한다. 기존의 다층 리프 구조는 2~3개의 압축된 리프 쉘로 재구성되며, 각 리프는 독립된 장식 요소가 아니라 물을 받고, 회전시키고, 다음 리프로 넘기는 연속적인 수공간 표면으로 작동한다.

---

## 1. 설계 문제 정의

이 프로젝트의 핵심은 “예쁜 리프”를 만드는 것이 아니라 다음 세 가지 목표를 동시에 만족하는 형상을 찾는 것이다.

### 1.1 물의 문제

15m 자유낙하한 물은 큰 속도로 첫 번째 리프에 도달한다. 공기저항을 무시하면 낙하 속도는 다음과 같다.

```text
v = sqrt(2gh)
  = sqrt(2 × 9.81 × 15)
  ≈ 17.2 m/s
```

따라서 첫 리프가 물을 정면으로 받으면 다음 문제가 발생한다.

- 물 튐
- 비산
- 소음
- 수막 파괴
- 외곽 이탈
- 보행자 또는 주변 마감에 물이 튀는 문제
- 하부 폰드 회수율 저하

첫 리프는 “받침 접시”가 아니라 **물의 방향을 부드럽게 바꾸는 착수면 / 활주면**이어야 한다.

### 1.2 구조의 문제

리프 2~3개가 15m 이하 높이에서 연결되는 조형물은 황동 캐스팅 기반이므로 자중이 크다. 내부 구조를 드러내지 않으려면 다음 요소가 구조적으로 작동해야 한다.

- 리프의 이중곡률
- 말린 가장자리 림
- 중앙 오목 홈 또는 워터 로드
- 리프 간 겹침 및 연결부
- 두께 변화
- 하부 매입 플레이트 및 앵커
- 숨겨진 접합부

“내부 구조 없음”은 실제 보강이 없다는 뜻이 아니라, **노출 구조체 없이 리프 자체가 구조 쉘처럼 작동하는 것**으로 정의한다.

### 1.3 시각의 문제

조형물과 물은 하나로 읽혀야 한다.

필수 시점은 다음이다.

- 유리 파사드 외부에서 백화점 안으로 들어갈 때 보이는 정면 시점
- 1층 eye level에서 보이는 하부 리프와 물의 장면
- 각 층 메자닌에서 내려다볼 때 보이는 수막, 소용돌이, 물길
- 보이드 사방에서 보이는 수직 실루엣

---

## 2. 전체 시스템 구조

권장 워크플로우는 다음과 같다.

```text
Rhino / Grasshopper
  ├─ 파라메트릭 리프 형상 생성
  ├─ 빠른 물 접촉 proxy 평가
  ├─ Karamba 구조 1차 검토
  ├─ Kangaroo 기반 form-finding / constraint solving
  └─ 후보 geometry export

Python CLI
  ├─ 후보 폴더 관리
  ├─ JSON schema 검증
  ├─ geometry 검사
  ├─ fast simulation 실행
  ├─ OpenFOAM case 생성
  ├─ OpenFOAM 실행 자동화
  ├─ ParaView postprocess 자동화
  └─ Blender render 자동화

OpenFOAM
  ├─ 상위 후보 CFD 정밀 검증
  ├─ 자유수면 / 물-공기 2상 유동
  ├─ 첫 리프 착수부 splash 검토
  └─ 물 회수율 및 비산 반경 검토

ParaView / pvpython
  ├─ alpha.water iso-surface 시각화
  ├─ pressure map
  ├─ velocity vector
  ├─ splash envelope
  └─ 검증용 영상 생성

Blender
  ├─ 최종 프레젠테이션 영상
  ├─ 유리 파사드 시점
  ├─ eye-level 시점
  ├─ top-view / mezzanine 시점
  ├─ 자동차 페인트 재질
  └─ 조명, 미스트, 수막 연출
```

---

## 3. 프로그램별 역할 분리

### 3.1 Rhino + Grasshopper

역할:

- 메인 디자인 엔진
- 파라메트릭 리프 형상 생성
- 높이 15m 이하 제약
- 2~3개 리프 연결
- 수막 경로 curve 생성
- 빠른 물 접촉 proxy
- Karamba / Kangaroo 연동
- 후보 export

Rhino/Grasshopper 안에 모든 계산을 넣지 않는다. Grasshopper는 **geometry UI와 빠른 평가 환경**으로 사용한다.

### 3.2 Python CLI

역할:

- 전체 시스템의 자동화 허브
- 후보 폴더 생성
- schema 검증
- mesh 검사
- OpenFOAM case 생성
- ParaView script 실행
- Blender script 실행
- metric 수집 및 ranking

CLI 중심으로 만들면 Claude Code가 모듈별로 구현하기 쉽고, Grasshopper 외부에서도 자동 batch를 돌릴 수 있다.

### 3.3 OpenFOAM

역할:

- 설계 검증용 CFD
- 모든 후보가 아니라 상위 후보만 검증
- 초기에는 15m 낙하를 압축한 local contact case 사용
- 최종 후보 1~3개에 한해 full-height case 검토

주의:

- OpenFOAM이 C++ 기반인 것은 맞지만, 초기 개발에서 C++ solver를 직접 작성할 필요는 없다.
- 기존 solver와 dictionary template을 이용해 case 자동 생성 방식으로 시작한다.
- 특수 boundary condition이나 custom solver가 필요해질 때만 C++ 확장으로 넘어간다.

### 3.4 ParaView

역할:

- OpenFOAM 결과의 과학적 시각화
- 검증용 영상 생성
- 수치 metric 추출 보조
- alpha.water, pressure, velocity, splash envelope 분석

### 3.5 Blender

역할:

- 최종 발표용 영상
- 물, 조명, 재질, 유리, 반사, 미스트 연출
- OpenFOAM 결과를 시각적으로 이해하기 쉽게 재구성
- 유리 파사드 / eye-level / mezzanine 카메라 구성

주의:

- Blender fluid simulation은 look-dev, 감각 테스트, 발표 영상용으로 좋다.
- 실제 튐 반경, 압력, 자유수면 CFD 검증 도구로 쓰지는 않는다.
- 검증은 OpenFOAM, 발표는 Blender로 역할을 분리한다.

### 3.6 Karamba3D

역할:

- Grasshopper 내 빠른 구조 검토
- shell mesh 기반 FEA 1차 검토
- 최대 변위, 응력, support reaction, mass 추정
- 형태 후보 필터링

### 3.7 Kangaroo

역할:

- form-finding
- constraint solving
- 리프 간 연결부 relaxation
- 서페스 연속성 조정
- 곡률과 support 조건을 만족하는 초기 형상 찾기

Kangaroo는 정밀 구조해석기가 아니라 형상 안정화와 제약 기반 조정 도구로 사용한다.

---

## 4. 데이터 흐름

```text
1. Grasshopper에서 후보 생성
2. params.json 저장
3. leaf.stl / leaf.obj 저장
4. water_path.json 저장
5. fast_metrics.json 저장
6. Karamba 구조 metric 저장
7. Python CLI가 후보 ranking
8. 상위 후보만 OpenFOAM case로 변환
9. OpenFOAM 실행
10. CFD metric 추출
11. ParaView 검증 영상 생성
12. 최종 후보를 Blender로 전달
13. 발표용 영상 생성
```

---

## 5. 추천 폴더 구조

```text
leaf-water-lab/
  README.md
  pyproject.toml

  configs/
    base_params.json
    openfoam_defaults.json
    render_defaults.json
    material_defaults.json

  gh/
    LeafGenerator.gh
    ExportCandidate.py
    ImportResults.py
    KarambaSetup.gh
    KangarooRelaxation.gh

  leaflab/
    schema/
      candidate_schema.py
      params_schema.py
      metrics_schema.py

    geometry/
      generate_leaf_surface.py
      spine_curve.py
      profile_generator.py
      rim_generator.py
      water_channel.py
      validate_mesh.py
      compute_normals.py
      compute_curvature.py
      compute_silhouette.py

    fast_sim/
      particle_drop.py
      impact_angle.py
      splash_proxy.py
      attachment_proxy.py
      edge_escape.py
      drain_target.py
      structure_proxy.py

    scoring/
      score_water.py
      score_structure.py
      score_visual.py
      pareto.py
      rank_candidates.py

    openfoam/
      templates/
        interFoam_leaf_contact_case/
          0/
          constant/
          system/
      make_case.py
      run_case.py
      mesh_case.py
      postprocess.py
      metrics.py

    paraview/
      extract_alpha_surface.py
      render_scientific_movie.py
      export_vtk_sequence.py
      pressure_map.py

    blender/
      import_geometry.py
      import_cfd_sequence.py
      setup_materials.py
      setup_cameras.py
      render_final_movie.py

    cli/
      main.py

  runs/
    candidate_0001/
      params.json
      geometry/
        leaf.stl
        leaf.obj
        water_path.json
        silhouette_curves.json
      fast_metrics.json
      karamba_metrics.json
      cfd_metrics.json
      visual_metrics.json
      score.json
      openfoam/
      paraview_frames/
      blender_render/
```

---

## 6. Candidate Parameter Schema

각 후보는 하나의 `params.json`으로 관리한다.

```json
{
  "candidate_id": "leaf_0001",
  "description": "15m 이하 3-leaf compressed Big Leaf",

  "global_constraints": {
    "max_height_m": 15.0,
    "min_height_m": 10.0,
    "max_plan_radius_m": 4.5,
    "target_visual_axis": "facade_to_void_center"
  },

  "geometry": {
    "leaf_count": 3,
    "single_surface_intent": true,
    "height_total_m": 14.5,
    "base_z_m": 0.0,
    "top_leaf_z_m": 14.2,

    "spine": {
      "type": "bezier_or_nurbs",
      "control_points": [
        [0.0, 0.0, 0.0],
        [0.5, -0.3, 4.5],
        [-0.4, 0.6, 9.5],
        [0.2, 0.1, 14.5]
      ],
      "twist_total_deg": 135.0
    },

    "leafs": [
      {
        "leaf_id": "L1_landing",
        "z_m": 14.2,
        "length_m": 5.2,
        "width_m": 3.4,
        "camber": 0.38,
        "twist_deg": 42.0,
        "pitch_deg": 18.0,
        "landing_angle_deg": 14.0,
        "landing_radius_m": 1.2,
        "rim_height_m": 0.12,
        "rim_thickness_m": 0.045,
        "channel_depth_m": 0.08,
        "channel_offset_m": 0.35,
        "overlap_to_next_m": 0.6
      },
      {
        "leaf_id": "L2_flow",
        "z_m": 8.4,
        "length_m": 4.6,
        "width_m": 2.8,
        "camber": 0.34,
        "twist_deg": -31.0,
        "pitch_deg": 24.0,
        "rim_height_m": 0.08,
        "rim_thickness_m": 0.04,
        "channel_depth_m": 0.06,
        "channel_offset_m": -0.25,
        "overlap_to_next_m": 0.4
      },
      {
        "leaf_id": "L3_discharge",
        "z_m": 3.8,
        "length_m": 3.2,
        "width_m": 2.1,
        "camber": 0.28,
        "twist_deg": 26.0,
        "pitch_deg": 35.0,
        "rim_height_m": 0.05,
        "rim_thickness_m": 0.035,
        "channel_depth_m": 0.045,
        "channel_offset_m": 0.15
      }
    ]
  },

  "water": {
    "fall_height_m": 15.0,
    "gravity_mps2": 9.81,
    "estimated_impact_velocity_mps": 17.2,
    "inlet_type": "double_ring_curtain",
    "curtain_radius_inner_m": 1.0,
    "curtain_radius_outer_m": 2.0,
    "nozzle_spacing_mm": 40.0,
    "flow_rate_per_nozzle_lpm": 45.0,
    "flow_rate_min_lpm": 30.0,
    "flow_rate_max_lpm": 60.0,
    "target_drain_position": [0.0, 0.0, 0.0],
    "pond_radius_m": 4.5
  },

  "material": {
    "base_material": "brass_casting",
    "finish": "automotive_paint",
    "density_kg_m3": 8500,
    "shell_thickness_mm": 18.0,
    "min_shell_thickness_mm": 12.0,
    "max_shell_thickness_mm": 45.0,
    "coating_note": "water-contact durability, scratch repair, and chemical resistance must be tested"
  },

  "structure": {
    "support_type": "hidden_base_plate_and_anchor",
    "visible_internal_frame": false,
    "base_plate_radius_m": 1.2,
    "anchor_count": 12,
    "rim_as_structural_edge": true,
    "channel_as_spine": true
  },

  "views": {
    "facade_camera": {
      "position": [12.0, -18.0, 2.0],
      "target": [0.0, 0.0, 7.0]
    },
    "eye_level_camera": {
      "position": [6.0, -7.0, 1.6],
      "target": [0.0, 0.0, 5.0]
    },
    "mezzanine_camera": {
      "position": [4.0, -3.0, 12.0],
      "target": [0.0, 0.0, 8.0]
    }
  }
}
```

---

## 7. Metrics Schema

### 7.1 fast_metrics.json

```json
{
  "candidate_id": "leaf_0001",
  "water_proxy": {
    "impact_angle_mean_deg": 12.5,
    "impact_angle_p95_deg": 21.0,
    "normal_impact_score": 0.18,
    "attachment_length_m": 8.4,
    "attachment_ratio": 0.74,
    "edge_escape_rate": 0.07,
    "edge_escape_risk": 0.18,
    "curvature_gradient_mean": 0.12,
    "drain_target_error_m": 0.35,
    "splash_proxy": 0.21
  },
  "geometry_proxy": {
    "height_total_m": 14.5,
    "surface_area_m2": 42.0,
    "volume_estimate_m3": 0.78,
    "mean_gaussian_curvature": 0.028,
    "mean_curvature_variation": 0.15,
    "rim_continuity_score": 0.84,
    "channel_continuity_score": 0.78
  }
}
```

### 7.2 karamba_metrics.json

```json
{
  "candidate_id": "leaf_0001",
  "structure": {
    "mass_kg": 6630,
    "max_displacement_mm": 18.0,
    "max_stress_mpa": 62.0,
    "stress_concentration_index": 0.32,
    "support_reaction_max_kn": 110.0,
    "overturning_ratio": 0.42,
    "buckling_proxy": 0.61,
    "min_thickness_mm": 14.0,
    "fabrication_thickness_ok": true
  }
}
```

### 7.3 cfd_metrics.json

```json
{
  "candidate_id": "leaf_0001",
  "openfoam": {
    "case_type": "local_contact",
    "solver": "interFoam",
    "mesh_cells": 2500000,
    "simulation_time_s": 4.0,
    "delta_t_max_s": 0.0005
  },
  "cfd_results": {
    "splash_volume_ratio": 0.08,
    "attachment_ratio": 0.71,
    "overspray_radius_95_m": 0.65,
    "pond_capture_ratio": 0.86,
    "peak_pressure_pa": 32000,
    "pressure_impulse_pa_s": 8400,
    "water_sheet_continuity_score": 0.77,
    "mist_risk_index": 0.22
  }
}
```

### 7.4 visual_metrics.json

```json
{
  "candidate_id": "leaf_0001",
  "visual": {
    "big_leaf_similarity": 0.82,
    "eye_level_silhouette_score": 0.76,
    "top_view_water_path_clarity": 0.81,
    "facade_visibility_score": 0.79,
    "mezzanine_360_visibility_score": 0.73,
    "visual_mass_score": 0.68,
    "surface_continuity_score": 0.84
  }
}
```

### 7.5 score.json

```json
{
  "candidate_id": "leaf_0001",
  "score_water": 0.78,
  "score_structure": 0.71,
  "score_visual": 0.80,
  "score_total_weighted": 0.765,
  "pareto_rank": 1,
  "notes": [
    "Good water attachment",
    "Moderate mass",
    "Strong facade silhouette"
  ]
}
```

---

## 8. 평가 요소

### 8.1 score_water

```text
score_water =
  낮은 충돌각
+ 긴 표면 부착 거리
+ 낮은 외곽 이탈률
+ 낮은 급격 곡률 변화
+ 안정적인 최종 배수 위치
```

구체 metric:

| 항목 | 설명 | 좋은 방향 |
|---|---|---|
| impact angle | 물 벡터와 리프 표면 사이의 접촉각 | 낮을수록 좋음 |
| normal impact score | `abs(dot(Vwater, Nsurface))` | 낮을수록 좋음 |
| attachment length | 물이 표면에 붙어 이동한 거리 | 길수록 좋음 |
| edge escape rate | 외곽으로 이탈한 입자 비율 | 낮을수록 좋음 |
| curvature gradient | 물길 방향의 곡률 변화량 | 낮을수록 좋음 |
| drain target error | 목표 폰드 위치와 실제 배수 위치 차이 | 낮을수록 좋음 |
| splash proxy | 간이 튐 위험도 | 낮을수록 좋음 |
| pond capture ratio | 최종 폰드 회수율 | 높을수록 좋음 |

권장 가중치:

```text
score_water =
  0.25 * low_impact_score
+ 0.20 * attachment_score
+ 0.20 * low_edge_escape_score
+ 0.15 * curvature_smoothness_score
+ 0.10 * drain_accuracy_score
+ 0.10 * pond_capture_score
```

첫 리프에서는 `normal_impact_score < 0.25`를 목표값으로 둔다. 이는 물이 표면을 정면으로 때리는 상태가 아니라, 표면에 낮은 각도로 붙는 상태를 유도하기 위한 기준이다.

### 8.2 score_structure

```text
score_structure =
  낮은 최대 변위
+ 낮은 응력 집중
+ 높은 전도 안정성
+ 낮은 자중
+ 제작 가능한 두께
```

구체 metric:

| 항목 | 설명 | 좋은 방향 |
|---|---|---|
| max displacement | 최대 변위 | 낮을수록 좋음 |
| max stress | 최대 응력 | 낮을수록 좋음 |
| stress concentration index | 연결부 응력 집중도 | 낮을수록 좋음 |
| overturning ratio | 전도 위험도 | 낮을수록 좋음 |
| support reaction | 앵커와 하부 플레이트 반력 | 제어 가능해야 함 |
| mass | 황동 캐스팅 자중 | 낮을수록 좋음 |
| thickness feasibility | 제작 가능한 두께 범위 충족 여부 | true |
| rim continuity | 가장자리 림의 구조 연속성 | 높을수록 좋음 |
| channel-as-spine score | 중앙 물길이 구조 spine으로 작동하는 정도 | 높을수록 좋음 |

권장 가중치:

```text
score_structure =
  0.25 * displacement_score
+ 0.20 * stress_score
+ 0.20 * overturning_score
+ 0.15 * mass_score
+ 0.10 * fabrication_thickness_score
+ 0.10 * shell_stiffness_score
```

### 8.3 score_visual

```text
score_visual =
  Big Leaf 유사도
+ eye-level 실루엣
+ top-view 물길 선명도
+ 파사드 방향 인지성
```

구체 metric:

| 항목 | 설명 | 좋은 방향 |
|---|---|---|
| Big Leaf similarity | 기존 Big Leaf의 유기적 리프 인상과 유사도 | 높을수록 좋음 |
| eye-level silhouette | 1층 눈높이에서 강한 실루엣 | 높을수록 좋음 |
| top-view water path clarity | 메자닌에서 물길이 선명하게 보이는 정도 | 높을수록 좋음 |
| facade visibility | 유리 파사드 외부에서 인지되는 정도 | 높을수록 좋음 |
| mezzanine 360 visibility | 보이드 사방에서의 인지성 | 높을수록 좋음 |
| visual mass | 15m 이하이지만 충분한 존재감 | 높을수록 좋음 |
| surface continuity | 2~3개 리프가 하나의 쉘처럼 읽히는 정도 | 높을수록 좋음 |

권장 가중치:

```text
score_visual =
  0.25 * big_leaf_similarity
+ 0.20 * eye_level_silhouette
+ 0.20 * top_view_water_path_clarity
+ 0.20 * facade_visibility
+ 0.10 * surface_continuity
+ 0.05 * visual_mass
```

### 8.4 전체 ranking

단일 점수도 만들 수 있지만, 최종 의사결정은 Pareto ranking이 더 적합하다.

```text
Pareto axes:
1. water performance
2. structural stability
3. visual presence
```

Weighted score 예시:

```text
score_total =
  0.40 * score_water
+ 0.35 * score_structure
+ 0.25 * score_visual
```

초기 단계에서는 물 성능을 가장 강하게 본다. 이유는 15m 자유낙수 착수부가 실패하면 조형적 성공도 무의미해지기 때문이다.

---

## 9. 리프 형상 생성 로직

### 9.1 기본 형상 방식

리프 형상은 다음 방식으로 생성한다.

```text
central spine curve
  ↓
leaf zone 배치
  ↓
각 leaf zone에 profile 생성
  ↓
profile scale / camber / twist 적용
  ↓
rim 생성
  ↓
water channel 생성
  ↓
leaf 간 blend / overlap / transition 생성
  ↓
single continuous shell 또는 joined shell 생성
```

### 9.2 주요 파라미터

```text
height_total
leaf_count
leaf_length
leaf_width
leaf_camber
leaf_twist
leaf_pitch
leaf_overlap
rim_height
rim_thickness
water_channel_depth
water_channel_offset
landing_angle
landing_radius
surface_thickness
base_support_radius
```

### 9.3 첫 리프 설계 원칙

첫 리프는 15m 자유낙하한 물을 받는 가장 중요한 부위다.

형상 원칙:

1. 물을 정면으로 받지 않는다.
2. 첫 접촉부의 접촉각을 낮춘다.
3. 첫 접촉부를 넓고 완만하게 만든다.
4. 얕은 오목면을 만들어 수막을 유도한다.
5. 낮은 림으로 외곽 이탈을 줄인다.
6. 중앙 워터 로드를 통해 물을 다음 리프로 보낸다.
7. 곡률 변화가 급격하지 않게 한다.

### 9.4 두 번째 / 세 번째 리프 설계 원칙

하부 리프는 물을 안정적으로 보여주는 장치다.

- 두 번째 리프: 물의 회전과 시각적 중심 형성
- 세 번째 리프: eye-level 장면과 하부 폰드 유도
- 세 번째 리프는 독립 리프가 아니라 중간 리프에서 이어지는 말린 끝단처럼 만들 수도 있다.
- 시각적으로는 3개처럼 보이지만 제작상 2개 캐스팅 파트로 나누는 전략도 가능하다.

---

## 10. 빠른 물 접촉 Proxy Simulation

### 10.1 목적

OpenFOAM 전에 수백~수천 개 후보를 빠르게 걸러내기 위한 간이 시뮬레이션이다.

정확한 CFD가 아니라 다음을 빠르게 평가한다.

- 첫 접촉 위치
- 충돌각
- 수막 부착 가능성
- 외곽 이탈 위험
- 물길 경로
- 최종 배수 위치

### 10.2 입력

```text
leaf mesh
water inlet points
water curtain radius
particle count
fall height
inlet velocity
gravity
surface friction coefficient
edge boundary
target pond position
```

### 10.3 출력

```text
impact_angle_mean
impact_angle_p95
normal_impact_score
attachment_length
edge_escape_rate
curvature_gradient_along_flow
drain_target_error
splash_proxy
water_path_polyline
```

### 10.4 기본 알고리즘

```text
1. water curtain 위에 입자 샘플링
2. 각 입자를 15m 낙하 속도 벡터로 초기화
3. mesh raycast로 첫 충돌점 계산
4. 충돌 지점의 surface normal 계산
5. impact angle 계산
6. velocity를 surface tangent 방향으로 투영
7. 중력 성분과 tangent flow 방향으로 입자 이동
8. 곡률 변화가 큰 지점에서 detachment risk 계산
9. rim 또는 edge에 도달하면 edge escape로 기록
10. target pond 영역에 도달하면 captured로 기록
11. 전체 입자의 metric 집계
```

### 10.5 충돌각 계산

```text
Vwater = normalized water velocity vector
Nsurface = normalized surface normal

normal_impact_score = abs(dot(Vwater, Nsurface))
```

해석:

```text
normal_impact_score ≈ 1.0  -> 정면 충돌, 매우 나쁨
normal_impact_score ≈ 0.0  -> 표면을 스치며 접촉, 좋음
```

목표:

```text
normal_impact_score < 0.25
```

---

## 11. OpenFOAM CFD 계획

### 11.1 CFD 접근 단계

#### 단계 A: Local Contact Case

전체 30m를 모두 시뮬레이션하지 않는다. 첫 리프 주변 4~6m 도메인만 만든다.

```text
목적:
15m 자유낙하 후 속도에 해당하는 물 curtain이 첫 리프에 닿을 때의 splash 검토

장점:
계산량 감소
형상 후보 비교 가능
mesh 관리 용이
```

#### 단계 B: Extended Leaf Flow Case

첫 리프부터 하부 리프까지 포함한다.

```text
목적:
첫 리프에서 안정화된 물이 2~3개 리프를 따라 흘러가는지 검토
```

#### 단계 C: Full Height Case

최종 후보 1~3개만 전체 낙수 영역을 포함한다.

```text
목적:
30m 상부 노즐부터 하부 폰드까지 전체 수공간 장면 검증
```

### 11.2 OpenFOAM pipeline

```text
Grasshopper export
  ↓
leaf.stl
  ↓
OpenFOAM case generator
  ↓
blockMesh
  ↓
surfaceFeatureExtract
  ↓
snappyHexMesh
  ↓
checkMesh
  ↓
setFields
  ↓
interFoam
  ↓
postProcess / foamToVTK
  ↓
ParaView
```

### 11.3 Boundary condition 개념

Local contact case 기준:

```text
top inlet:
  water curtain inlet
  velocity: 15~17.2 m/s
  alpha.water = 1 in curtain area

side / top open boundary:
  atmosphere / pressure outlet

leaf surface:
  wall
  no-slip or appropriate wall function
  wetting behavior는 초기에는 단순화

bottom:
  collection / outlet / pond proxy
```

### 11.4 CFD metric

```text
splash_volume_ratio
attachment_ratio
overspray_radius_95
pond_capture_ratio
peak_pressure_on_leaf
pressure_impulse
water_sheet_continuity_score
mist_risk_index
```

정의 예시:

```text
splash_volume_ratio =
  control volume 밖으로 이탈한 water volume / inlet water volume

pond_capture_ratio =
  target pond region에 도달한 water volume / inlet water volume

overspray_radius_95 =
  alpha.water가 일정 threshold 이상인 영역의 95 percentile 반경
```

---

## 12. 구조 해석 계획

### 12.1 Grasshopper + Karamba 1차 검토

입력:

```text
shell mesh
shell thickness
brass material properties
support points
hidden base plate
water pressure approximation
self-weight
maintenance load if needed
```

출력:

```text
max displacement
max stress
stress concentration
support reaction
mass estimate
overturning ratio
buckling proxy
```

### 12.2 Kangaroo 사용 위치

Kangaroo는 정밀 구조해석이 아니라 다음 용도로 사용한다.

```text
리프 간 연결부 smooth relaxation
single surface continuity adjustment
rim continuity adjustment
support constraint 기반 형태 안정화
곡률 분포 조정
```

### 12.3 최종 구조 검토

상위 후보는 다음 검토가 필요하다.

- 전문 구조기술자 검토
- 실물 재료 물성 반영
- 황동 캐스팅 자중 검토
- 앵커와 기초 검토
- 지진 / 진동 / 유지관리 하중 검토
- 표면 두께 변화에 따른 casting feasibility 검토
- 물 충돌 압력의 구조 하중 반영

---

## 13. 시각화 계획

### 13.1 Rhino / Grasshopper

목적:

- 디자인 개발 중 실시간 확인
- 형태 파라미터 조정
- 리프 실루엣 확인
- 물길 curve 확인
- 구조 proxy 결과 확인

### 13.2 ParaView 검증 영상

목적:

- 설계 검증용 영상
- 엔지니어 협의용
- 수치와 함께 보는 영상

내용:

```text
alpha.water iso-surface
splash envelope
velocity vectors
pressure map on first leaf
water capture region
time sequence
```

출력:

```text
candidate_0001_validation.mp4
candidate_0001_pressure_map.png
candidate_0001_splash_envelope.png
```

### 13.3 Blender 발표 영상

목적:

- 클라이언트 / 심의 / 프레젠테이션용
- 조형물과 물이 하나로 읽히는 장면 연출

필수 카메라:

```text
1. facade camera
   - 유리 파사드 밖에서 조형물과 낙수가 보이는 장면

2. eye-level camera
   - 1층에서 리프와 물이 만나는 장면

3. mezzanine camera
   - 위에서 내려다보는 소용돌이 물길

4. orbit camera
   - 보이드 사방에서 조형물의 존재감 확인
```

Blender에서 표현할 요소:

```text
brass casting mass
automotive paint gloss
thin water sheet
falling water curtain
mist
indirect lighting
reflection on pond
human scale
glass facade refraction/reflection
```

---

## 14. Claude Code 개발 계획

### Sprint 0 — Repository setup

목표:

- repo 구조 생성
- Python package 기본 설정
- CLI skeleton
- config 파일 생성

명령 예시:

```bash
mkdir leaf-water-lab
cd leaf-water-lab
python -m venv .venv
pip install pydantic typer numpy trimesh scipy
```

완료 기준:

```bash
leaflab --help
```

### Sprint 1 — Schema 구현

목표:

- candidate schema
- params schema
- metrics schema
- validation command

구현 파일:

```text
leaflab/schema/candidate_schema.py
leaflab/schema/params_schema.py
leaflab/schema/metrics_schema.py
leaflab/cli/main.py
```

명령 예시:

```bash
leaflab init-run candidate_0001
leaflab validate runs/candidate_0001/params.json
```

### Sprint 2 — Grasshopper export bridge

목표:

- Grasshopper에서 후보 저장
- params.json export
- STL / OBJ export
- water_path.json export

구현 파일:

```text
gh/ExportCandidate.py
leaflab/geometry/validate_mesh.py
```

완료 기준:

```bash
leaflab check-geometry runs/candidate_0001/geometry/leaf.stl
```

### Sprint 3 — Geometry validation

목표:

- mesh scale check
- normal direction check
- manifold check
- bounding box check
- 15m height constraint check

metric:

```json
{
  "height_ok": true,
  "is_manifold": true,
  "normal_consistency": 0.98,
  "bbox": {
    "height_m": 14.5,
    "radius_m": 4.1
  }
}
```

### Sprint 4 — Fast water proxy

목표:

- particle drop
- first contact raycast
- impact angle
- tangent sliding
- edge escape
- drain target

구현 파일:

```text
leaflab/fast_sim/particle_drop.py
leaflab/fast_sim/impact_angle.py
leaflab/fast_sim/edge_escape.py
leaflab/fast_sim/splash_proxy.py
```

명령 예시:

```bash
leaflab fast-sim runs/candidate_0001
```

### Sprint 5 — Visual metrics

목표:

- facade view silhouette
- eye-level silhouette
- top-view water path clarity
- Big Leaf similarity proxy

구현 파일:

```text
leaflab/geometry/compute_silhouette.py
leaflab/scoring/score_visual.py
```

### Sprint 6 — Structure proxy + Karamba bridge

목표:

- shell thickness data export
- Karamba metric export
- mass estimate
- overturning proxy

구현 파일:

```text
gh/KarambaSetup.gh
gh/ExportKarambaMetrics.py
leaflab/scoring/score_structure.py
```

### Sprint 7 — Scoring and ranking

목표:

- score_water
- score_structure
- score_visual
- weighted score
- pareto rank

명령 예시:

```bash
leaflab score runs/candidate_0001
leaflab rank runs/
```

### Sprint 8 — OpenFOAM local contact case

목표:

- case template
- STL insertion
- blockMeshDict generation
- snappyHexMeshDict generation
- interFoam run script

구현 파일:

```text
leaflab/openfoam/make_case.py
leaflab/openfoam/mesh_case.py
leaflab/openfoam/run_case.py
```

명령 예시:

```bash
leaflab foam make-case runs/candidate_0001
leaflab foam mesh runs/candidate_0001
leaflab foam run runs/candidate_0001
```

### Sprint 9 — CFD postprocess

목표:

- alpha.water extraction
- splash volume metric
- overspray radius
- pond capture ratio
- pressure map

구현 파일:

```text
leaflab/openfoam/postprocess.py
leaflab/openfoam/metrics.py
leaflab/paraview/extract_alpha_surface.py
```

명령 예시:

```bash
leaflab foam metrics runs/candidate_0001
leaflab paraview movie runs/candidate_0001
```

### Sprint 10 — Blender final render bridge

목표:

- leaf geometry import
- CFD water surface sequence import
- materials setup
- camera setup
- render output

구현 파일:

```text
leaflab/blender/import_geometry.py
leaflab/blender/import_cfd_sequence.py
leaflab/blender/setup_materials.py
leaflab/blender/setup_cameras.py
leaflab/blender/render_final_movie.py
```

명령 예시:

```bash
leaflab blender render runs/candidate_0001 --camera facade
leaflab blender render runs/candidate_0001 --camera eyelevel
leaflab blender render runs/candidate_0001 --camera mezzanine
```

---

## 15. MVP 정의

첫 번째 MVP는 OpenFOAM 없이도 완성 가능해야 한다.

### MVP 1

목표:

- Grasshopper에서 15m 이하 2~3개 리프 생성
- params.json export
- leaf.stl export
- 빠른 물 proxy 평가
- 구조 proxy 평가
- score_water / score_structure / score_visual 계산
- 후보 ranking

성공 기준:

```text
10~100개 후보를 생성하고,
각 후보에 대해 물 튐 위험과 구조 proxy, 시각 점수를 비교할 수 있다.
```

### MVP 2

목표:

- 상위 후보 1개를 OpenFOAM local contact case로 변환
- interFoam 실행
- splash metric 추출
- ParaView 검증 영상 생성

성공 기준:

```text
15m 자유낙하 후 속도에 해당하는 물 curtain이 첫 리프에 닿는 장면을 CFD로 확인한다.
```

### MVP 3

목표:

- Blender 발표 영상 자동 생성
- facade / eye-level / mezzanine 카메라 렌더
- 조형물 + 물 + 재질 + 조명 통합

성공 기준:

```text
하나의 후보에 대해 설계 검증 영상과 발표용 영상을 모두 생성한다.
```

---

## 16. 주요 리스크와 대응

### 16.1 OpenFOAM 계산량 과다

대응:

- 전체 30m domain은 최종 후보에만 사용
- 초기에는 local contact case 사용
- inlet velocity로 15m 낙하 효과를 대체
- mesh refinement 영역을 첫 리프 주변으로 제한

### 16.2 Blender 결과와 CFD 결과의 차이

대응:

- Blender는 presentation look-dev
- OpenFOAM은 engineering validation
- 둘을 동일한 “검증”으로 보지 않는다.
- Blender에는 OpenFOAM에서 추출한 water surface sequence를 활용한다.

### 16.3 첫 리프에서 물 튐

대응:

- landing angle 낮추기
- landing radius 키우기
- 접수부 오목면 형성
- 중앙 channel 강화
- rim height 조정
- nozzle / curtain 형태 조정
- 필요하면 상부 낙수 수막을 분할 또는 이중 링으로 조정

### 16.4 황동 캐스팅 자중

대응:

- shell thickness 최적화
- rib 역할을 하는 rim과 channel 통합
- 하부 접점 확대
- 숨겨진 base plate 설계
- 구조기술자 검토
- 필요하면 hollow casting 또는 분절 제작 검토

### 16.5 자동차 페인트 내구성

대응:

- 물 접촉, 스크래치, 약품, 청소 유지관리 검토
- 실제 샘플 테스트
- 표면 거칠기와 수막 부착성 테스트
- 접수부에는 coating 손상 위험 고려

### 16.6 싱글 서페스 제작성

대응:

- 시각적으로는 single surface
- 제작상으로는 2~3개 cast module 허용
- 접합부를 리프 overlap / fold / shadow line으로 숨김
- 운반, 설치, 유지보수 단위 고려

---

## 17. Claude Code에 줄 수 있는 초기 작업 지시문

### 지시문 1: Repository와 schema 생성

```text
Create a Python project named leaf-water-lab.
Implement a Typer CLI named leaflab.
Create Pydantic schemas for candidate params and metrics.
Generate the folder structure described in the project plan.
Add commands:
- leaflab init-run <candidate_id>
- leaflab validate <params_path>
- leaflab score <run_dir>
Use JSON as the primary interchange format.
```

### 지시문 2: Geometry validation 구현

```text
Implement geometry validation utilities using trimesh and numpy.
Input: runs/<candidate>/geometry/leaf.stl
Output: geometry_metrics.json
Check:
- bounding box height
- radius
- watertightness
- normal consistency
- approximate surface area
- approximate volume
- triangle count
- scale in meters
```

### 지시문 3: Fast water proxy 구현

```text
Implement a particle-based water contact proxy.
Input:
- leaf.stl
- params.json water section
Output:
- fast_metrics.json
Compute:
- first contact points by raycast
- surface normals
- normal impact score
- tangent projected velocity
- simplified sliding paths
- edge escape rate
- attachment length
- drain target error
```

### 지시문 4: Scoring 구현

```text
Implement score_water, score_structure, score_visual, and weighted score.
Use normalized metrics from fast_metrics.json, karamba_metrics.json, and visual_metrics.json.
Implement Pareto ranking for water, structure, and visual scores.
```

### 지시문 5: OpenFOAM case generator 구현

```text
Create a Python module that generates an OpenFOAM interFoam local contact case.
Input:
- run directory
- leaf.stl
- params.json
Output:
- openfoam case folder
Generate:
- blockMeshDict
- snappyHexMeshDict
- controlDict
- fvSchemes
- fvSolution
- initial and boundary field files
Do not implement custom C++ solver in phase 1.
```

---

## 18. 최종 판단

이 프로젝트의 최적 프로그램 구성은 다음이다.

```text
Rhino / Grasshopper:
  디자인 생성과 빠른 평가

Python CLI:
  전체 자동화와 데이터 관리

Karamba / Kangaroo:
  구조 1차 검토와 형태 안정화

OpenFOAM:
  최종 후보 CFD 검증

ParaView:
  검증용 시각화와 분석

Blender:
  발표용 영상과 재질/조명 연출
```

가장 중요한 개발 원칙은 다음이다.

1. OpenFOAM을 모든 후보에 돌리지 않는다.
2. Blender를 CFD 검증 도구로 쓰지 않는다.
3. Grasshopper 안에 모든 시스템을 넣지 않는다.
4. 후보별 JSON schema와 metric 파일을 엄격하게 관리한다.
5. 15m 자유낙하 물이 첫 리프에 닿는 순간을 최우선 평가 지점으로 둔다.
6. 리프는 조형물이자 물길이며 구조 쉘이다.
7. 최종 결과물은 “작아진 Big Leaf”가 아니라 “15m 이하로 압축된 Big Leaf + 15m 자유낙수”로 설명한다.

---

## 19. 외부 기술 문서 참고

개발 중 참고할 기술 문서:

- OpenFOAM standard solvers / interFoam: https://www.openfoam.com/documentation/user-guide/a-reference/a.1-standard-solvers
- OpenFOAM interFoam documentation: https://doc.openfoam.com/2306/tools/processing/solvers/rtm/multiphase/interFoam/
- OpenFOAM snappyHexMesh: https://www.openfoam.com/documentation/user-guide/4-mesh-generation-and-conversion/4.4-mesh-generation-with-the-snappyhexmesh-utility
- OpenFOAM paraFoam / post-processing: https://www.openfoam.com/documentation/user-guide/7-post-processing/7.1-parafoam
- Rhino / Grasshopper developer docs: https://developer.rhino3d.com/
- RhinoCommon API: https://developer.rhino3d.com/api/RhinoCommon/
- Karamba3D manual: https://manual.karamba3d.com/
- Kangaroo Physics: https://www.food4rhino.com/en/app/kangaroo-physics
- Blender fluid manual: https://docs.blender.org/manual/en/latest/physics/fluid/index.html
- Blender command-line rendering: https://docs.blender.org/manual/en/latest/advanced/command_line/render.html

---

## 20. 다음 액션

바로 시작한다면 다음 순서가 가장 안전하다.

```text
1. Claude Code로 repository / schema / CLI 생성
2. Grasshopper에서 단순 3-leaf generator 작성
3. params.json + STL export 연결
4. fast water proxy 구현
5. score_water 중심으로 후보 20개 비교
6. Karamba 구조 metric export
7. score_structure 통합
8. top 3 후보 선정
9. OpenFOAM local contact case 생성
10. ParaView 검증 영상 제작
11. Blender 최종 영상 제작
```

최초 구현 목표는 “정확한 CFD”가 아니라 다음 문장이어야 한다.

> 15m 자유낙하한 물이 첫 리프에 정면 충돌하지 않고, 낮은 각도로 접촉해 수막으로 전환되는 리프 형상을 빠르게 생성하고 비교한다.

이 목표가 달성되면 이후 OpenFOAM과 Blender는 정밀 검증 및 표현 단계로 자연스럽게 붙일 수 있다.
