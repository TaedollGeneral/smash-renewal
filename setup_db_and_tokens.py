#!/usr/bin/env python3
"""
setup_db_and_tokens.py  (EC2 서버에서 실행)
=============================================
역할 1. test1~test100 유저를 DB에 세팅하고 token_version=1로 초기화
역할 2. 유효 JWT 100개 + 비정상 JWT 20개를 생성하여 콘솔에 출력

출력된 토큰 배열을 복사한 뒤, 로컬 PC의 remote_stress.py 상단에 붙여넣으세요.
"""

import os
import sys
import datetime
import sqlite3

# ── 환경 확인 ───────────────────────────────────────────────────────────────

print("=" * 60)
print("  EC2 토큰 생성기 / setup_db_and_tokens.py")
print("=" * 60)

# ── Phase 1: Flask 앱에서 SECRET_KEY 추출 ───────────────────────────────────

print("\n[Phase 1] Flask 앱 컨텍스트 로드 -> SECRET_KEY 추출")

try:
    from app import app
    import jwt
except ImportError as e:
    print(f"  [ERROR] 임포트 실패: {e}")
    print("  이 스크립트는 EC2 서버의 smash-renewal 디렉터리에서 실행해야 합니다.")
    sys.exit(1)

with app.app_context():
    SECRET_KEY = app.config['SECRET_KEY']

print(f"  SECRET_KEY 확보 완료 (길이: {len(SECRET_KEY)}자)")
print(f"  SECRET_KEY 앞8자: {SECRET_KEY[:8]}...")
print(f"  [확인] 운영 Flask 프로세스와 이 값이 동일해야 토큰이 유효합니다.")

# ── Phase 2: DB 유저 세팅 ─────────────────────────────────────────────────

BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
DB_PATH     = os.path.join(BASE_DIR, "smash_db", "users.db")
USER_COUNT  = 100

print(f"\n[Phase 2] DB 유저 세팅 (test1 ~ test{USER_COUNT})")
print(f"  DB 경로: {DB_PATH}")

conn    = sqlite3.connect(DB_PATH)
created = 0
updated = 0

for i in range(1, USER_COUNT + 1):
    uid = f"test{i}"
    try:
        conn.execute(
            "INSERT INTO users (student_id, password, name, role, token_version) "
            "VALUES (?, ?, ?, ?, ?)",
            (uid, "dummy_hash", f"tester{i}", "none", 1),
        )
        created += 1
    except sqlite3.IntegrityError:
        conn.execute(
            "UPDATE users SET role = 'none', token_version = 1 WHERE student_id = ?",
            (uid,),
        )
        updated += 1

conn.commit()
conn.close()
print(f"  신규 생성: {created}명 | 기존 리셋: {updated}명 | 합계: {USER_COUNT}명")

# ── Phase 3: 유효 JWT 100개 생성 ─────────────────────────────────────────

print(f"\n[Phase 3] 유효 JWT {USER_COUNT}개 생성")

exp = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=24)

valid_tokens = []
for i in range(1, USER_COUNT + 1):
    payload = {
        "id":   f"test{i}",
        "name": f"tester{i}",
        "role": "none",
        "ver":  1,
        "exp":  exp,
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
    valid_tokens.append(token)

print(f"  {len(valid_tokens)}개 생성 완료 (exp: +24h)")

# 셀프 검증: 첫 번째 토큰을 같은 SECRET_KEY로 디코딩
try:
    test_decoded = jwt.decode(valid_tokens[0], SECRET_KEY, algorithms=["HS256"])
    print(f"  [셀프 검증 OK] 토큰 디코딩 성공: id={test_decoded['id']}, role={test_decoded['role']}, ver={test_decoded['ver']}")
except Exception as e:
    print(f"  [셀프 검증 FAIL] {e} — SECRET_KEY 불일치 의심!")

# ── Phase 4: 비정상 JWT 20개 생성 (4가지 유형 x 5개) ─────────────────────

print(f"\n[Phase 4] 비정상 JWT 20개 생성 (4가지 실패 유형 x 5)")

invalid_tokens = []

# 유형 1: 잘못된 서명 (5개) — InvalidTokenError 유도
for i in range(1, 6):
    payload = {"id": f"test{i}", "name": f"tester{i}", "role": "none", "ver": 1, "exp": exp}
    token = jwt.encode(payload, "wrong_secret_key_for_testing", algorithm="HS256")
    invalid_tokens.append(("bad_signature", token))

# 유형 2: DB에 없는 유저 (5개) — token_version 조회 실패 유도
for i in range(1, 6):
    payload = {"id": f"ghost_{i}", "name": f"유령{i}", "role": "none", "ver": 1, "exp": exp}
    token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
    invalid_tokens.append(("nonexistent_user", token))

# 유형 3: 버전 불일치 (5개) — ver=999 vs DB ver=1
for i in range(1, 6):
    payload = {"id": f"test{i}", "name": f"tester{i}", "role": "none", "ver": 999, "exp": exp}
    token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
    invalid_tokens.append(("version_mismatch", token))

# 유형 4: 만료된 토큰 (5개) — ExpiredSignatureError 유도
for i in range(1, 6):
    expired_exp = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=1)
    payload = {"id": f"test{i}", "name": f"tester{i}", "role": "none", "ver": 1, "exp": expired_exp}
    token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
    invalid_tokens.append(("expired_token", token))

print(f"  잘못된 서명: 5개")
print(f"  존재하지 않는 유저: 5개")
print(f"  버전 불일치 (ver=999): 5개")
print(f"  만료된 토큰: 5개")
print(f"  합계: {len(invalid_tokens)}개")

# ── Phase 5: 콘솔 출력 (복사/붙여넣기용) ─────────────────────────────────

SEPARATOR = "=" * 60

print(f"\n{SEPARATOR}")
print("  아래 내용을 복사하여 remote_stress.py 상단에 붙여넣으세요.")
print(f"{SEPARATOR}")

# VALID_TOKENS 출력
print("\nVALID_TOKENS = [")
for token in valid_tokens:
    print(f'    "{token}",')
print("]")

# INVALID_TOKENS 출력: (label, token) 튜플 리스트
print("\nINVALID_TOKENS = [")
for label, token in invalid_tokens:
    print(f'    ("{label}", "{token}"),')
print("]")

print(f"\n{SEPARATOR}")
print(f"  출력 완료. 유효 토큰: {len(valid_tokens)}개 / 비정상 토큰: {len(invalid_tokens)}개")
print(f"{SEPARATOR}\n")
