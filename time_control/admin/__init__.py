# admin/ — 매니저 대리 신청/취소 핵심 로직
#
# [보안 설계 원칙]
#   이 모듈의 모든 함수는 진입 즉시 토큰의 role을 검증한다.
#   role != 'manager'이면 어떤 로직도 실행하지 않고 403을 반환한다.
#   시간 검증(time_handler)은 의도적으로 호출하지 않는다.
#   → 매니저는 신청·취소 가능 시간과 무관하게 항상 대리 처리 가능.
#
# 요청 처리 순서 — handle_admin_apply:
#   1. role == 'manager' 검증 (실패 시 즉시 403 반환)
#   2. (시간 검증 없음 — 의도적 생략)
#   3. target_user_id로 users.db 조회 → 회원 이름 확인 (존재하지 않으면 404)
#   4. target_guest_name 유무에 따라 entry 구성
#      - 있음: 게스트/잔여석 대리 신청 → name(신청자) + guest_name(게스트) 모두 기록
#      - 없음: 일반 카테고리 대리 신청 → DB 조회 이름으로 member entry 생성
#   5. board_store.apply_entry() 원자적 조작 + is_board_changed = True
#
# 요청 처리 순서 — handle_admin_cancel:
#   1. role == 'manager' 검증 (실패 시 즉시 403 반환)
#   2. (시간 검증 없음 — 의도적 생략)
#   3. target_user_id로 정확 일치 삭제 시도
#      → 실패(일반 항목 없음) 시 "guest_{target_user_id}_*" prefix 탐색 후 삭제
#   4. board_store.remove_entry() 원자적 조작 + is_board_changed = True

import html
import os
import sqlite3
import time

from flask import request

from ..board_store import apply_entry, get_board, remove_entry


# ── DB 경로 ──────────────────────────────────────────────────────────────────

_DB_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", "smash_db", "users.db"
)


# ── 내부 헬퍼 ────────────────────────────────────────────────────────────────

def _lookup_member(student_id: str) -> dict | None:
    """users.db에서 회원을 조회한다.

    Returns:
        {"student_id": str, "name": str} — 유효한 회원
        None — 존재하지 않는 회원
    """
    try:
        conn = sqlite3.connect(_DB_PATH)
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT student_id, name FROM users WHERE student_id = ?",
            (student_id,),
        ).fetchone()
        conn.close()
        if row:
            return {"student_id": row["student_id"], "name": row["name"]}
    except sqlite3.Error:
        pass
    return None


def _sanitize_name(name: str) -> str:
    """게스트·대리인 이름의 XSS 특수문자를 이스케이프한다."""
    return html.escape(name, quote=True)


# ── 핵심 로직 — 대리 신청 ────────────────────────────────────────────────────

def handle_admin_apply(category: str) -> tuple[dict, int]:
    """매니저 대리 신청 요청을 처리한다.

    /admin/apply 엔드포인트에서 호출된다.
    호출 전에 다음이 보장되어야 한다:
      - category는 유효한 Category enum 값
      - request.current_user가 설정됨 (token_required 통과)

    Args:
        category: 유효한 Category enum 값

    Returns:
        (response_dict, status_code)
    """
    # ── Step 1: Manager 권한 검증 ──────────────────────────────────────────────
    # 토큰은 token_required 데코레이터가 이미 검증했으므로 role만 확인한다.
    user = request.current_user
    if user["role"] != "manager":
        return {"error": "관리자 권한이 필요합니다."}, 403

    # ── Step 2: (시간 검증 없음 — 매니저 전용 엔드포인트이므로 의도적 생략) ───

    # ── Step 3: 요청 파라미터 파싱 ───────────────────────────────────────────
    data = request.get_json() or {}
    target_user_id = (data.get("target_user_id") or "").strip()
    target_guest_name = (data.get("target_guest_name") or "").strip()

    if not target_user_id:
        return {"error": "target_user_id가 필요합니다."}, 400

    # ── Step 4: DB 조회로 대상 회원 확인 ─────────────────────────────────────
    # 프론트엔드에서 넘어온 ID를 절대 신뢰하지 않고, DB에서 실제 이름을 조회한다.
    member = _lookup_member(target_user_id)
    if not member:
        return {"error": f"존재하지 않는 회원입니다: {target_user_id}"}, 404

    member_id = member["student_id"]
    member_name = member["name"]

    # ── Step 5: entry 구성 (target_guest_name 유무로 분기) ────────────────────
    ts = round(time.time(), 2)

    if target_guest_name:
        # [2-input 경우] 게스트/잔여석 대리 신청:
        #   신청자(회원) 이름과 게스트 이름을 모두 기록한다.
        #   게시판 표시 형태: No | member_name(신청자) | sanitized_guest(게스트) | 신청시간
        sanitized_guest = _sanitize_name(target_guest_name)
        entry = {
            "user_id":    f"guest_{member_id}_{sanitized_guest}",
            "name":       member_name,      # 게시판 '신청자' 열 — DB 조회 이름
            "guest_name": sanitized_guest,  # 게시판 '게스트/대리인' 열
            "type":       "guest",
            "timestamp":  ts,
        }
    else:
        # [1-input 경우] 일반 카테고리 대리 신청 (운동 · 레슨 등):
        #   DB에서 가져온 이름으로 member entry를 생성한다.
        entry = {
            "user_id":   member_id,
            "name":      member_name,  # DB 조회 이름 — 프론트 입력값 미사용
            "type":      "member",
            "timestamp": ts,
        }

    # ── Step 6: 동시성 제어 + 인메모리 조작 ───────────────────────────────────
    # apply_entry()가 단일 Lock 내에서 중복 검사 → append → 정렬 → 더티 플래그를 수행
    success, reason = apply_entry(category, entry)
    if not success:
        return {"error": reason}, 409

    # ── Step 7: 응답 반환 ─────────────────────────────────────────────────────
    return {"message": f"{member_name}({member_id}) 대리 신청이 완료되었습니다."}, 200


# ── 핵심 로직 — 대리 취소 ────────────────────────────────────────────────────

def handle_admin_cancel(category: str) -> tuple[dict, int]:
    """매니저 대리 취소 요청을 처리한다.

    /admin/cancel 엔드포인트에서 호출된다.
    호출 전에 다음이 보장되어야 한다:
      - category는 유효한 Category enum 값
      - request.current_user가 설정됨 (token_required 통과)

    취소 대상 탐색 전략:
      1) target_user_id 정확 일치 시도 (일반 회원 항목)
      2) 실패 시 "guest_{target_user_id}_*" prefix 탐색 (게스트 항목)
      → 매니저는 학번만 입력해도 일반/게스트 항목 모두 취소 가능

    Args:
        category: 유효한 Category enum 값

    Returns:
        (response_dict, status_code)
    """
    # ── Step 1: Manager 권한 검증 ──────────────────────────────────────────────
    user = request.current_user
    if user["role"] != "manager":
        return {"error": "관리자 권한이 필요합니다."}, 403

    # ── Step 2: (시간 검증 없음 — 매니저 전용 엔드포인트이므로 의도적 생략) ───

    # ── Step 3: 요청 파라미터 파싱 ───────────────────────────────────────────
    data = request.get_json() or {}
    target_user_id = (data.get("target_user_id") or "").strip()

    if not target_user_id:
        return {"error": "target_user_id가 필요합니다."}, 400

    # ── Step 4: 취소 대상 탐색 + 인메모리 조작 ───────────────────────────────
    # [1차 시도] 정확 일치: 일반 회원 항목 (user_id == target_user_id)
    if remove_entry(category, target_user_id):
        return {"message": f"{target_user_id} 대리 취소가 완료되었습니다."}, 200

    # [2차 시도] prefix 탐색: 게스트 항목 (user_id == "guest_{target_user_id}_*")
    # 매니저가 학번만 입력해도 해당 회원의 게스트 항목을 찾아 취소할 수 있도록 한다.
    prefix = f"guest_{target_user_id}_"
    entries = get_board(category)  # 얕은 복사본(snapshot)
    guest_user_id = next(
        (e["user_id"] for e in entries if e["user_id"].startswith(prefix)),
        None,
    )

    if guest_user_id is None:
        return {"error": "취소할 신청 내역이 존재하지 않습니다."}, 404

    success = remove_entry(category, guest_user_id)
    if not success:
        # snapshot과 실제 보드 사이에 동시 요청이 발생한 경우 (극히 드뭄)
        return {"error": "취소할 신청 내역이 존재하지 않습니다."}, 404

    # ── Step 5: 응답 반환 ─────────────────────────────────────────────────────
    return {"message": f"{target_user_id} 대리 취소가 완료되었습니다."}, 200
