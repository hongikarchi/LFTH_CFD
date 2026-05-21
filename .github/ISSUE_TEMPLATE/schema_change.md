---
name: Schema change
about: Pydantic schema 변경 — 마이그레이션 분석
title: "[schema] "
labels: "schema-change"
assignees: ""
---

## 변경 schema

<!-- params / metrics / candidate 중 어느 것 -->

## 변경 내용

<!-- 필드 추가/삭제/타입 변경 등 -->

## 이전 버전

`schema_version`: `1.X`

## 새 버전

`schema_version`: `1.Y`

## 마이그레이션 전략

<!-- 자동 마이그 가능? 기본값? lossless? -->

## 영향 받는 후보

<!-- runs/ 안에 몇 개 후보가 영향 받는지 -->

## 체크리스트

- [ ] 새 모델 작성 (구버전 보존)
- [ ] `MODELS` dispatch dict 업데이트
- [ ] `leaflab migrate` 함수 작성
- [ ] migration unit test
- [ ] README/CLAUDE.md 업데이트
