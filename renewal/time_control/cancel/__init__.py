# cancel/ — 취소 로직 디렉토리 (Placeholder)
#
# 추후 구현 시 time_handler의 validate_cancel_time()으로 시간 검증 후
# DB 취소 처리 로직을 이 패키지에 작성한다.
#
# 사용 예시:
#   from renewal.time_control.time_handler import validate_cancel_time, _now_kst
#   error = validate_cancel_time(category, _now_kst())
#   if error:
#       return jsonify({"error": error}), 400
#   # ... DB 취소 처리
