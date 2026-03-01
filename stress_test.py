#!/usr/bin/env python3
"""
Thundering Herd 동시성 스트레스 테스트
======================================
Node.js 리버스 프록시(3000) -> Flask/Waitress(5000) -> SQLite 전체 파이프라인 테스트

요청 구성 (총 520건):
  Group A: 유효 토큰 100개 -> POST /api/apply (수요일 운동 신청)
  Group B: 유효 토큰 100개 x 4회 -> GET /api/all-boards (게시판 조회)
  Group C: 비정상 토큰 20개 -> POST /api/apply (401 에러 유도)

동기화: threading.Barrier(520) -> 전 스레드 도착 후 일제 발사
"""

import os
import sys
import jwt
import time
import sqlite3
import threading
import datetime
import statistics

import requests as http_client

# ── Phase 1: 환경 준비 ──────────────────────────────────────────────────────

print("=" * 70)
print("  Thundering Herd 동시성 스트레스 테스트 (520건)")
print("=" * 70)

# Flask 앱 컨텍스트에서 SECRET_KEY를 추출 (환경변수 파싱 오류 원천 차단)
print("\n[Phase 1] 환경 준비")
print("  1-1. Flask 앱 컨텍스트 로드 -> SECRET_KEY 추출...")

from app import app

with app.app_context():
    SECRET_KEY = app.config['SECRET_KEY']

print(f"       SECRET_KEY 확보 완료 (길이: {len(SECRET_KEY)}자)")

# ── 설정 ──────────────────────────────────────────────────────────────────────

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "smash_db", "users.db")

# 전체 파이프라인 테스트: Node.js 프록시(3000) 경유
TARGET_HOST = "http://127.0.0.1:3000"
APPLY_URL = f"{TARGET_HOST}/api/apply"
BOARD_URL = f"{TARGET_HOST}/api/all-boards"
CATEGORY = "WED_REGULAR"

VALID_USER_COUNT = 100       # 유효 테스트 유저 수
FAKE_TOKEN_COUNT = 20        # 비정상 토큰 수
GET_REPEAT = 4               # 유저당 GET 반복 횟수
BARRIER_TIMEOUT = 30         # 배리어 대기 최대 시간 (초)
REQUEST_TIMEOUT = 15         # 개별 HTTP 요청 타임아웃 (초)

TOTAL_REQUESTS = VALID_USER_COUNT + (VALID_USER_COUNT * GET_REPEAT) + FAKE_TOKEN_COUNT
# 100 + 400 + 20 = 520

# ── Phase 2: DB 세팅 (test1 ~ test100) ──────────────────────────────────────

print(f"\n[Phase 2] DB 세팅 (test1 ~ test{VALID_USER_COUNT})")
print(f"  DB 경로: {DB_PATH}")

conn = sqlite3.connect(DB_PATH)
created = 0
updated = 0

for i in range(1, VALID_USER_COUNT + 1):
    user_id = f"test{i}"
    try:
        conn.execute(
            "INSERT INTO users (student_id, password, name, role, token_version) "
            "VALUES (?, ?, ?, ?, ?)",
            (user_id, "dummy_hash", f"tester{i}", "user", 1)
        )
        created += 1
    except sqlite3.IntegrityError:
        conn.execute(
            "UPDATE users SET token_version = 1 WHERE student_id = ?",
            (user_id,)
        )
        updated += 1

conn.commit()
conn.close()
print(f"  신규 생성: {created}명 | 기존 리셋: {updated}명 | 합계: {VALID_USER_COUNT}명")

# ── Phase 3: 토큰 생성 ─────────────────────────────────────────────────────

print(f"\n[Phase 3] 토큰 생성")

# 3-A. 유효 토큰 100개
print(f"  3-A. 유효 JWT {VALID_USER_COUNT}개 생성 (id, name, role, ver=1, exp=+24h)...")
valid_tokens = []
for i in range(1, VALID_USER_COUNT + 1):
    payload = {
        'id':   f"test{i}",
        'name': f"tester{i}",
        'role': 'user',
        'ver':  1,
        'exp':  datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=24)
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
    valid_tokens.append(token)

# 3-B. 비정상 토큰 20개 (4가지 실패 유형 x 5개)
print(f"  3-B. 비정상 JWT {FAKE_TOKEN_COUNT}개 생성 (4가지 실패 유형)...")
fake_tokens = []

# 유형 1: 잘못된 SECRET_KEY로 서명 (5개) -> InvalidTokenError
for i in range(1, 6):
    payload = {
        'id': f"test{i}", 'name': f"tester{i}", 'role': 'user', 'ver': 1,
        'exp': datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=24)
    }
    token = jwt.encode(payload, "wrong_secret_key_for_testing", algorithm="HS256")
    fake_tokens.append(("bad_signature", token))

# 유형 2: DB에 존재하지 않는 유저 (5개) -> token_version=None -> 401
for i in range(1, 6):
    payload = {
        'id': f"ghost_user_{i}", 'name': f"유령{i}", 'role': 'user', 'ver': 1,
        'exp': datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=24)
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
    fake_tokens.append(("nonexistent_user", token))

# 유형 3: token_version 불일치 (5개) -> ver=999 vs DB ver=1 -> 401
for i in range(1, 6):
    payload = {
        'id': f"test{i}", 'name': f"tester{i}", 'role': 'user', 'ver': 999,
        'exp': datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=24)
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
    fake_tokens.append(("version_mismatch", token))

# 유형 4: 만료된 토큰 (5개) -> ExpiredSignatureError -> 401
for i in range(1, 6):
    payload = {
        'id': f"test{i}", 'name': f"tester{i}", 'role': 'user', 'ver': 1,
        'exp': datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=1)
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
    fake_tokens.append(("expired", token))

print(f"       - 잘못된 서명: 5개")
print(f"       - 존재하지 않는 유저: 5개")
print(f"       - 버전 불일치 (ver=999): 5개")
print(f"       - 만료된 토큰: 5개")

# ── Phase 4: 태스크 배열 + 배리어 동기화 ────────────────────────────────────

print(f"\n[Phase 4] 태스크 배열 구성 ({TOTAL_REQUESTS}건)")

# 태스크 구조: (group, method, url, headers, json_body, label)
tasks = []

# Group A: 유효 POST x100 (운동 신청)
for i, token in enumerate(valid_tokens):
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    tasks.append(("A", "POST", APPLY_URL, headers, {"category": CATEGORY}, f"test{i+1}"))

# Group B: 유효 GET x400 (게시판 조회, 토큰 포함)
for repeat in range(GET_REPEAT):
    for i, token in enumerate(valid_tokens):
        headers = {"Authorization": f"Bearer {token}"}
        tasks.append(("B", "GET", BOARD_URL, headers, None, f"test{i+1}_r{repeat+1}"))

# Group C: 비정상 POST x20 (401 유도)
for fake_type, token in fake_tokens:
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    tasks.append(("C", "POST", APPLY_URL, headers, {"category": CATEGORY}, fake_type))

print(f"  Group A (유효 POST, 운동 신청): {VALID_USER_COUNT}건")
print(f"  Group B (유효 GET, 게시판 조회): {VALID_USER_COUNT * GET_REPEAT}건")
print(f"  Group C (비정상 POST, 401 유도): {FAKE_TOKEN_COUNT}건")
print(f"  합계: {len(tasks)}건")

# ── 배리어 + 스레드 준비 ──────────────────────────────────────────────────

barrier = threading.Barrier(TOTAL_REQUESTS, timeout=BARRIER_TIMEOUT)
results = [None] * TOTAL_REQUESTS
fire_timestamps = [0.0] * TOTAL_REQUESTS  # 각 스레드의 실제 발사 시각


def worker(index, group, method, url, headers, json_body, label):
    """배리어 대기 -> 일제 해제 -> HTTP 요청 -> 결과 기록"""
    try:
        # 배리어 대기: 520개 스레드 모두 도착할 때까지 블록
        barrier.wait()
    except threading.BrokenBarrierError:
        results[index] = {
            "group": group, "status": 0, "time": 0,
            "label": label, "error": "BrokenBarrierError"
        }
        return

    # 발사 시각 기록 (동시성 편차 측정용)
    fire_timestamps[index] = time.time()

    start = time.time()
    try:
        resp = http_client.request(
            method, url, headers=headers, json=json_body, timeout=REQUEST_TIMEOUT
        )
        elapsed = time.time() - start
        results[index] = {
            "group": group,
            "status": resp.status_code,
            "time": elapsed,
            "label": label,
            "body": resp.text[:200],
        }
    except Exception as e:
        elapsed = time.time() - start
        results[index] = {
            "group": group,
            "status": 0,
            "time": elapsed,
            "label": label,
            "error": str(e)[:200],
        }


# ── Phase 5: Thundering Herd 발사 ─────────────────────────────────────────

print(f"\n[Phase 5] Thundering Herd 발사 준비")
print(f"  스레드 {TOTAL_REQUESTS}개 생성 중...")

threads = []
for i, (group, method, url, headers, json_body, label) in enumerate(tasks):
    t = threading.Thread(
        target=worker,
        args=(i, group, method, url, headers, json_body, label),
        name=f"worker-{i}",
    )
    threads.append(t)

print(f"  스레드 {TOTAL_REQUESTS}개 시작 (배리어 대기 진입)...")
thread_start = time.time()

for t in threads:
    t.start()

print(f"  520번째 스레드 도착 대기 중... (timeout={BARRIER_TIMEOUT}s)")

# 모든 스레드 완료 대기
for t in threads:
    t.join(timeout=60)

total_elapsed = time.time() - thread_start

# ── Phase 6: 결과 집계 ─────────────────────────────────────────────────────

print(f"\n{'=' * 70}")
print("  스트레스 테스트 결과 리포트")
print(f"{'=' * 70}")

# 동시 발사 편차 계산
valid_fires = [ts for ts in fire_timestamps if ts > 0]
if valid_fires:
    fire_spread_ms = (max(valid_fires) - min(valid_fires)) * 1000
    print(f"\n[동시성 지표]")
    print(f"  전체 소요 시간     : {total_elapsed:.3f}s")
    print(f"  발사 편차 (첫~끝)  : {fire_spread_ms:.1f}ms")
    print(f"  발사 완료 스레드   : {len(valid_fires)}/{TOTAL_REQUESTS}")


def report_group(group_name, group_label, expected_status=None):
    """그룹별 결과를 집계하고 출력한다."""
    group_results = [r for r in results if r and r["group"] == group_name]
    if not group_results:
        print(f"\n[{group_label}] 결과 없음")
        return

    # 상태 코드 분포
    status_counts = {}
    for r in group_results:
        s = r["status"]
        status_counts[s] = status_counts.get(s, 0) + 1

    # 응답 시간 통계
    times = [r["time"] for r in group_results if r["time"] > 0]

    print(f"\n[{group_label}] ({len(group_results)}건)")
    print(f"  상태 코드 분포:")
    for status in sorted(status_counts.keys()):
        count = status_counts[status]
        marker = ""
        if expected_status and status == expected_status:
            marker = " (정상)"
        elif status == 0:
            marker = " (연결 실패)"
        print(f"    {status:>4}: {count}건{marker}")

    if times:
        times_sorted = sorted(times)
        p50 = times_sorted[len(times_sorted) // 2]
        p95_idx = int(len(times_sorted) * 0.95)
        p99_idx = int(len(times_sorted) * 0.99)
        p95 = times_sorted[min(p95_idx, len(times_sorted) - 1)]
        p99 = times_sorted[min(p99_idx, len(times_sorted) - 1)]
        avg = statistics.mean(times)
        mx = max(times)

        print(f"  응답 시간:")
        print(f"    평균: {avg:.3f}s | P50: {p50:.3f}s | P95: {p95:.3f}s | P99: {p99:.3f}s | 최대: {mx:.3f}s")

    # 예상과 다른 결과 샘플 출력
    if expected_status:
        unexpected = [r for r in group_results if r["status"] != expected_status]
        if unexpected:
            print(f"  예상 외 응답 샘플 (최대 5건):")
            for r in unexpected[:5]:
                detail = r.get("body", r.get("error", ""))[:100]
                print(f"    [{r['status']}] {r['label']}: {detail}")


# Group A: 유효 POST (운동 신청)
report_group("A", "Group A - 유효 POST (운동 신청)", expected_status=200)

# Group A 추가 분석: 200 vs 409
group_a = [r for r in results if r and r["group"] == "A"]
ok_count = sum(1 for r in group_a if r["status"] == 200)
dup_count = sum(1 for r in group_a if r["status"] == 409)
auth_fail = sum(1 for r in group_a if r["status"] == 401)
time_fail = sum(1 for r in group_a if r["status"] == 400)
rate_limit = sum(1 for r in group_a if r["status"] == 429)

print(f"  세부 분석:")
print(f"    신청 성공 (200): {ok_count}건")
print(f"    중복 차단 (409): {dup_count}건 {'(0이어야 정상 - 유저당 1회)' if dup_count > 0 else '(정상)'}")
print(f"    인증 실패 (401): {auth_fail}건 {'(0이어야 정상)' if auth_fail > 0 else '(정상)'}")
print(f"    시간 오류 (400): {time_fail}건 {'(OPEN 시간대 밖에서 실행됨)' if time_fail > 0 else '(정상)'}")
print(f"    Rate Limit(429): {rate_limit}건 {'(유저당 1회이므로 0이어야 정상)' if rate_limit > 0 else '(정상)'}")

# Group B: 유효 GET (게시판 조회)
report_group("B", "Group B - 유효 GET (게시판 조회)", expected_status=200)

# Group C: 비정상 POST (401 유도)
report_group("C", "Group C - 비정상 POST (401 유도)", expected_status=401)

# Group C 세부: 비정상 유형별 분석
group_c = [r for r in results if r and r["group"] == "C"]
if group_c:
    fake_types = {}
    for r in group_c:
        ft = r["label"]
        if ft not in fake_types:
            fake_types[ft] = {"total": 0, "401": 0, "other": 0}
        fake_types[ft]["total"] += 1
        if r["status"] == 401:
            fake_types[ft]["401"] += 1
        else:
            fake_types[ft]["other"] += 1

    print(f"  비정상 유형별 분석:")
    for ft, counts in fake_types.items():
        status_str = "OK" if counts["other"] == 0 else f"비정상 {counts['other']}건"
        print(f"    {ft:>20}: {counts['401']}/{counts['total']}건 401 ({status_str})")

# ── 전체 요약 ──────────────────────────────────────────────────────────────

all_times = [r["time"] for r in results if r and r["time"] > 0]
all_errors = [r for r in results if r and r["status"] == 0]

print(f"\n{'=' * 70}")
print(f"  전체 요약")
print(f"{'=' * 70}")
print(f"  총 요청: {TOTAL_REQUESTS}건 | 완료: {sum(1 for r in results if r)}건 | 연결 실패: {len(all_errors)}건")

if all_times:
    throughput = len(all_times) / total_elapsed
    print(f"  전체 소요: {total_elapsed:.3f}s | 처리량: {throughput:.1f} req/s")
    print(f"  응답 시간 (전체): 평균 {statistics.mean(all_times):.3f}s | 최대 {max(all_times):.3f}s")

# ── 병목 진단 힌트 ──────────────────────────────────────────────────────────

print(f"\n[병목 진단 힌트]")

if all_errors:
    print(f"  [!] 연결 실패 {len(all_errors)}건 발생 -> Node.js 프록시 또는 Waitress 과부하 의심")
    for r in all_errors[:3]:
        print(f"      {r.get('error', 'unknown')[:100]}")

group_a_times = [r["time"] for r in group_a if r["time"] > 0]
group_b_times = [r["time"] for r in results if r and r["group"] == "B" and r["time"] > 0]

if group_a_times and group_b_times:
    a_avg = statistics.mean(group_a_times)
    b_avg = statistics.mean(group_b_times)
    print(f"  POST 평균 ({a_avg:.3f}s) vs GET 평균 ({b_avg:.3f}s)")
    if a_avg > b_avg * 2:
        print(f"  [!] POST가 GET 대비 {a_avg/b_avg:.1f}배 느림 -> board_store Lock 경합 또는 SQLite 검증 병목")

if group_a_times:
    a_p99 = sorted(group_a_times)[int(len(group_a_times) * 0.99)]
    if a_p99 > 3.0:
        print(f"  [!] POST P99={a_p99:.3f}s -> Waitress 8 스레드 큐잉 대기 병목 의심")

if time_fail > 0:
    print(f"  [!] 400 에러 {time_fail}건 -> OPEN 시간대(토 22:00~일 10:00 KST) 밖에서 실행됨")
    print(f"      해결: 해당 시간대에 다시 실행하거나, 시간 검증 임시 우회 필요")

print(f"\n{'=' * 70}")
print(f"  테스트 완료")
print(f"{'=' * 70}")
