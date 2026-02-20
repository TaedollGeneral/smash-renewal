# cancel/ — 취소 로직 패키지 (2단계에서 구현 예정)
#
# 시간 검증 후 board_store에서 신청 데이터를 제거하는 로직을 작성한다.
#
# 사용 예시:
#   from time_control.time_handler import validate_cancel_time, is_cancel_allowed, _now_kst
#   from time_control.board_store import remove_entry
#
#   error = validate_cancel_time(category, _now_kst())
#   if error:
#       return jsonify({"error": error}), 400
#   remove_entry(category, user_id)
