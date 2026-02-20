# apply/ — 신청 로직 패키지 (2단계에서 구현 예정)
#
# 시간 검증 후 board_store에 신청 데이터를 추가하는 로직을 작성한다.
#
# 사용 예시:
#   from time_control.time_handler import validate_apply_time, is_apply_allowed, _now_kst
#   from time_control.board_store import add_entry
#
#   error = validate_apply_time(category, _now_kst())
#   if error:
#       return jsonify({"error": error}), 400
#   add_entry(category, {"user_id": ..., "name": ..., "type": ..., "timestamp": ...})
