import os
import jwt
import time
import sqlite3
import requests
import concurrent.futures
import datetime

# Flask 앱 환경을 완벽하게 동기화합니다.
from app import app

BASE_DIR = "/home/ubuntu/smash-renewal"
DB_PATH = os.path.join(BASE_DIR, "smash_db", "users.db")

# 🚨 프록시(3000)를 거치지 않고 파이썬 서버(5000)로 직행합니다! (변수 원천 차단)
TARGET_URL = "http://127.0.0.1:5000/api/apply"
CATEGORY = "WED_REGULAR"

print("🔄 1. 서버와 동일한 시크릿 키 로드 중...")
with app.app_context():
    secret_key = app.config['SECRET_KEY']

print("👤 2. DB 테스트 유저 강제 세팅 중...")
conn = sqlite3.connect(DB_PATH)
for i in range(1, 51):
    user_id = f"test{i}"
    try:
        conn.execute(
            "INSERT INTO users (student_id, password, name, role, token_version) VALUES (?, ?, ?, ?, ?)",
            (user_id, "dummy", f"테스터{i}", "user", 1)
        )
    except sqlite3.IntegrityError:
        # 이미 존재하면 버전만 1로 덮어씌웁니다.
        conn.execute(
            "UPDATE users SET token_version = 1 WHERE student_id = ?",
            (user_id,)
        )
conn.commit()
conn.close()

print("🎫 3. 100% 순정 토큰 50개 즉석 생성 중...")
tokens = []
for i in range(1, 51):
    payload = {
        'id': f"test{i}",
        'name': f"테스터{i}",
        'role': 'user',
        'ver': 1,
        'exp': datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=24)
    }
    # 서버와 100% 동일한 로직으로 서명
    token = jwt.encode(payload, secret_key, algorithm="HS256")
    tokens.append(token)

def send_apply_request(token):
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    payload = {"category": CATEGORY}
    start_time = time.time()
    try:
        response = requests.post(TARGET_URL, json=payload, headers=headers, timeout=5)
        elapsed = time.time() - start_time
        return {
            "status": str(response.status_code),
            "time": elapsed,
            "text": response.text
        }
    except Exception as e:
        return {"status": "ERROR", "time": 0, "text": str(e)}

print(f"\n🚀 {len(tokens)}명의 유저로 서버 직통 스트레스 테스트 발사!\n")
results = {"200": 0, "409": 0, "401": 0, "400": 0, "500": 0, "502": 0, "ERROR": 0}
response_times = []

start_total = time.time()
with concurrent.futures.ThreadPoolExecutor(max_workers=len(tokens)) as executor:
    futures = [executor.submit(send_apply_request, t) for t in tokens]
    for future in concurrent.futures.as_completed(futures):
        res = future.result()
        status = res["status"]
        
        # 에러가 나면 서버의 진짜 대답을 출력
        if status not in ["200", "409"]:
            print(f"[{status} 에러] {res['text']}")
            
        if status in results:
            results[status] += 1
        else:
            results[status] = 1
            
        if res["time"] > 0:
            response_times.append(res["time"])

end_total = time.time()
avg_time = sum(response_times) / len(response_times) if response_times else 0
max_time = max(response_times) if response_times else 0

print("\n=== 📊 서버 직통 스트레스 테스트 최종 결과 ===")
print(f"⏱️ 전체 소요 시간: {end_total - start_total:.3f}초")
print(f"⚡ 평균 응답 시간: {avg_time:.3f}초 (최대: {max_time:.3f}초)\n")
print(f"✅ 성공 (200 OK): {results['200']}명 (선착순 성공)")
print(f"🚫 정원 초과 (409): {results['409']}명 (선착순 탈락)")
print(f"🔒 인증 실패 (401): {results['401']}명")
print(f"⚠️ 기타 에러: 400({results['400']}), 502({results['502']}), ERROR({results['ERROR']})")