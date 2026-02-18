# apply/ — 신청 로직 디렉토리 (Placeholder)
#
# 추후 구현 시 time_handler의 validate_apply_time()으로 시간 검증 후
# DB 신청 처리 로직을 이 패키지에 작성한다.
#
# 사용 예시:
#   from renewal.time_control.time_handler import validate_apply_time, _now_kst
#   error = validate_apply_time(category, _now_kst())
#   if error:
#       return jsonify({"error": error}), 400
#   # ... DB 신청 처리
