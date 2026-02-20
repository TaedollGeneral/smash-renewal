# time_control 패키지 — 시간 기반 상태 제어 + 인메모리 게시판 관리
#
# 모듈 구성:
#   scheduler_logic.py  — 카테고리별 상태 전환 규칙 + 주간 초기화 스케줄러
#   time_handler.py     — 프론트엔드 폴링 API + 시간 검증 게이트키퍼
#   board_store.py      — 인메모리 딕셔너리 저장소 + 더티 플래그 배치 백업
#   rate_limiter.py     — 인메모리 슬라이딩 윈도우 Rate Limiter
#   apply/              — 운동 신청 핵심 로직 (handle_apply)
#   cancel/             — 취소 로직 (3단계 구현 예정)
