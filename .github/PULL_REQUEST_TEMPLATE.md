## 요약

<!-- 변경 사항 1~3줄 -->

Closes #<issue-number>

## 변경 유형

- [ ] 새 기능 (feat)
- [ ] 버그 수정 (fix)
- [ ] 리팩터 (refactor)
- [ ] 문서 (docs)
- [ ] 인프라/설정 (chore)
- [ ] **Schema 변경** (`schema-change` 라벨 추가 + 둘 다 approve 필요)
- [ ] **GH 바이너리 수정** (`.gh` 파일, `gh-binary` 라벨 추가)

## 테스트

<!-- 어떻게 검증했는지 -->

- [ ] `uv run pytest` 통과
- [ ] `uv run ruff check .` 통과
- [ ] `uv run mypy leaflab` 통과

## Schema 변경 시 추가 체크

- [ ] `schema_version` 증가
- [ ] migrate 함수 추가 (`leaflab/cli/migrate.py`)
- [ ] 기존 `runs/` 후보 migration 테스트
- [ ] README/CHANGELOG 노트

## GH 바이너리 수정 시 추가 체크

- [ ] PR description에 GH 변경 요약 (added port X, renamed cluster Y 등)
- [ ] `gh/scripts/` 외부 .py 모듈이 정상 작동
- [ ] 다른 협업자에 사전 알림 (단일 owner 원칙)
