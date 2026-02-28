# admin/ — 매니저 대리 신청/취소 핵심 로직
#
# [보안 설계]
#   1. 진입 즉시 토큰의 role 검증 → role != 'manager'이면 403 즉시 반환
#   2. 시간 검증(time_handler) 호출 없음 — 매니저는 시간 제한 없이 대리 처리 가능
#   3. target_user_id는 반드시 users.db에서 실존 여부 확인 (클라이언트 값 불신)
#
# handle_admin_apply 처리 순서:
#   1. role == 'manager' 검증 (실패 → 403)
#   2. 시간 검증 없음 (의도적 생략)
#   3. target_user_id → users.db 조회 → 실존 회원 이름 확인
#   4. target_guest_name 유무로 entry 구성 분기
#      - 있음(게스트/잔여석): name=회원이름, guest_name=게스트이름
#      - 없음(운동/레슨): name=회원이름, type=member
#   5. apply_entry() 원자적 조작 → is_board_changed = True
#
# handle_admin_cancel 처리 순서:
#   1. role == 'manager' 검증 (실패 → 403)
#   2. 시간 검증 없음 (의도적 생략)
#   3. target_user_id 정확 일치 삭제 시도
#      → 실패 시 "guest_{target_user_id}_*" prefix 탐색 후 삭제
#   3.5. 빈자리 감지를 위한 취소 전 보드 위치 기록
#   4. remove_entry() 원자적 조작 → is_board_changed = True
#   5. 빈자리 알림 트리거 (정원 확정 상태 + 정원 내 인원이었을 때만)

import html
import os
import sqlite3
import time

from flask import request

from ..board_store import apply_entry, get_board, remove_entry
from ..cancel import _check_and_notify_vacancy


_DB_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", "smash_db", "users.db"
)


def _lookup_member(student_id: str) -> dict | None:
    """users.db에서 회원을 조회한다. 없으면 None 반환."""
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
    return html.escape(name, quote=True)


def handle_admin_apply(category: str) -> tuple[dict, int]:
    """매니저 대리 신청 요청을 처리한다.

    /admin/apply 엔드포인트 전용.
    - 진입 즉시 role == 'manager' 검증 (실패 시 403)
    - 시간 검증 없이 DB 조회 후 코어 로직 실행
    """
    # Step 1: Manager 권한 검증 — 가장 먼저 실행
    user = request.current_user
    if user["role"] != "manager":
        return {"error": "관리자 권한이 필요합니다."}, 403

    # Step 2: 시간 검증 없음 (매니저 전용 엔드포인트, 의도적 생략)

    # Step 3: 요청 파라미터 파싱
    data = request.get_json() or {}
    target_user_id = (data.get("target_user_id") or "").strip()
    target_guest_name = (data.get("target_guest_name") or "").strip()

    if not target_user_id:
        return {"error": "target_user_id가 필요합니다."}, 400
    if len(target_user_id) > 20:
        return {"error": "유효하지 않은 target_user_id입니다."}, 400
    if target_guest_name and len(target_guest_name) > 20:
        return {"error": "게스트 이름은 20자 이하로 입력해주세요."}, 400

    # Step 4: DB 조회 — 클라이언트 값을 신뢰하지 않고 서버에서 직접 이름 조회
    member = _lookup_member(target_user_id)
    if not member:
        return {"error": "존재하지 않는 회원입니다."}, 404

    member_id = member["student_id"]
    member_name = member["name"]

    # Step 5: entry 구성 — target_guest_name 유무로 분기
    ts = round(time.time(), 2)

    if target_guest_name:
        # [2-input] 게스트/잔여석 대리 신청
        # 게시판 표시: No | member_name(신청자) | guest_name(게스트) | 신청시간
        sanitized_guest = _sanitize_name(target_guest_name)
        entry = {
            "user_id":    f"guest_{member_id}_{sanitized_guest}",
            "name":       member_name,       # 게시판 '신청자' 열
            "guest_name": sanitized_guest,   # 게시판 '게스트/대리인' 열
            "type":       "guest",
            "timestamp":  ts,
        }
    else:
        # [1-input] 일반 카테고리 대리 신청 (운동 · 레슨 등)
        # DB에서 조회한 이름만 사용 — 프론트 입력 이름 미사용
        entry = {
            "user_id":   member_id,
            "name":      member_name,
            "type":      "member",
            "timestamp": ts,
        }

    # Step 6: 동시성 제어 + 인메모리 조작 (is_board_changed = True 내부 처리)
    success, reason = apply_entry(category, entry)
    if not success:
        return {"error": reason}, 409

    return {"message": f"{member_name}({member_id}) 대리 신청이 완료되었습니다."}, 200


def handle_admin_cancel(category: str) -> tuple[dict, int]:
    """매니저 대리 취소 요청을 처리한다.

    /admin/cancel 엔드포인트 전용.
    - 진입 즉시 role == 'manager' 검증 (실패 시 403)
    - 시간 검증 없이 target_user_id로 삭제 처리

    탐색 전략:
      1) target_user_id 정확 일치 (일반 회원 항목)
      2) 실패 시 "guest_{target_user_id}_*" prefix 탐색 (게스트 항목)
      → 매니저는 학번만 입력해도 일반/게스트 항목 모두 취소 가능
    """
    # Step 1: Manager 권한 검증 — 가장 먼저 실행
    user = request.current_user
    if user["role"] != "manager":
        return {"error": "관리자 권한이 필요합니다."}, 403

    # Step 2: 시간 검증 없음 (매니저 전용 엔드포인트, 의도적 생략)

    # Step 3: 요청 파라미터 파싱
    data = request.get_json() or {}
    target_user_id = (data.get("target_user_id") or "").strip()

    if not target_user_id:
        return {"error": "target_user_id가 필요합니다."}, 400
    if len(target_user_id) > 20:
        return {"error": "유효하지 않은 target_user_id입니다."}, 400

    # Step 3.5: 빈자리 감지를 위한 취소 전 보드 스냅샷
    # remove_entry() 호출 후에는 위치 정보가 사라지므로 반드시 먼저 스냅샷한다.
    entries_pre = get_board(category)

    # Step 4: 취소 대상 탐색 + 인메모리 조작 (is_board_changed = True 내부 처리)
    # [1차] 정확 일치: 일반 회원 항목
    cancel_pos = next(
        (i for i, e in enumerate(entries_pre) if e["user_id"] == target_user_id),
        -1,
    )
    if remove_entry(category, target_user_id):
        _check_and_notify_vacancy(category, cancel_pos)
        return {"message": f"{target_user_id} 대리 취소가 완료되었습니다."}, 200

    # [2차] prefix 탐색: 게스트 항목 ("guest_{target_user_id}_*")
    prefix = f"guest_{target_user_id}_"
    guest_user_id = next(
        (e["user_id"] for e in entries_pre if e["user_id"].startswith(prefix)),
        None,
    )
    if guest_user_id is None:
        return {"error": "취소할 신청 내역이 존재하지 않습니다."}, 404

    cancel_pos = next(
        (i for i, e in enumerate(entries_pre) if e["user_id"] == guest_user_id),
        -1,
    )
    success = remove_entry(category, guest_user_id)
    if not success:
        return {"error": "취소할 신청 내역이 존재하지 않습니다."}, 404

    _check_and_notify_vacancy(category, cancel_pos)
    return {"message": f"{target_user_id} 대리 취소가 완료되었습니다."}, 200
