#!/usr/bin/env python3
"""
remote_stress.py  (로컬 PC 또는 EC2에서 실행)
==============================================
역할: 서버를 향해 520건의 HTTP 요청을 동시에 폭격하고 결과를 집계한다.

사용법:
  1. EC2 서버에서 `python setup_db_and_tokens.py` 실행
  2. 콘솔에 출력된 VALID_TOKENS, INVALID_TOKENS 배열을 아래 변수에 붙여넣기
  3. 실행:
     - EC2 내부 테스트:  python remote_stress.py --local
     - 외부 도메인 테스트: python remote_stress.py

의존 패키지:
  pip install requests
"""

import sys
import time
import threading
import statistics

import requests as http_client

# ══════════════════════════════════════════════════════════════════════════════
#  [STEP 1] 여기에 EC2에서 출력된 토큰을 붙여넣으세요.
# ══════════════════════════════════════════════════════════════════════════════

VALID_TOKENS = [
    # EC2의 setup_db_and_tokens.py 출력 결과를 여기에 붙여넣기
    # 예시:
    # "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
]

INVALID_TOKENS = [
    # EC2의 setup_db_and_tokens.py 출력 결과를 여기에 붙여넣기
    # (label, token) 튜플 형식
    # 예시:
    # ("bad_signature", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."),
]

# ══════════════════════════════════════════════════════════════════════════════
#  [STEP 2] 타겟 설정
# ══════════════════════════════════════════════════════════════════════════════

# --local 플래그: EC2 내부에서 직접 테스트 (Node.js 프록시 경유)
# --flask 플래그: EC2 내부에서 Flask 직접 테스트 (프록시 완전 우회)
if "--flask" in sys.argv:
    TARGET_HOST = "http://127.0.0.1:5000"
elif "--local" in sys.argv:
    TARGET_HOST = "http://127.0.0.1:3000"
else:
    TARGET_HOST = "https://uos-smash.cloud"
APPLY_URL   = f"{TARGET_HOST}/api/apply"
BOARD_URL   = f"{TARGET_HOST}/api/all-boards"
CATEGORY    = "WED_REGULAR"

GET_REPEAT      = 4    # 유저당 GET 반복 횟수 (100명 x 4 = 400건)
BARRIER_TIMEOUT = 60   # 배리어 대기 최대 시간 (초) — 원격이므로 넉넉하게
REQUEST_TIMEOUT = 20   # 개별 HTTP 요청 타임아웃 (초)

# ══════════════════════════════════════════════════════════════════════════════
#  토큰 유효성 사전 검사
# ══════════════════════════════════════════════════════════════════════════════

if not VALID_TOKENS:
    print("[ERROR] VALID_TOKENS가 비어 있습니다.")
    print("        EC2에서 setup_db_and_tokens.py를 실행하고 출력을 붙여넣으세요.")
    sys.exit(1)

if not INVALID_TOKENS:
    print("[ERROR] INVALID_TOKENS가 비어 있습니다.")
    print("        EC2에서 setup_db_and_tokens.py를 실행하고 출력을 붙여넣으세요.")
    sys.exit(1)

# ══════════════════════════════════════════════════════════════════════════════
#  태스크 배열 구성
# ══════════════════════════════════════════════════════════════════════════════

# (group, method, url, headers, json_body, label)
tasks = []

# Group A: 유효 토큰으로 POST /api/apply (운동 신청) — 100건
for i, token in enumerate(VALID_TOKENS):
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    tasks.append(("A", "POST", APPLY_URL, headers, {"category": CATEGORY}, f"test{i+1}"))

# Group B: 유효 토큰으로 GET /api/all-boards (게시판 조회) — 100 x 4 = 400건
for repeat in range(GET_REPEAT):
    for i, token in enumerate(VALID_TOKENS):
        headers = {"Authorization": f"Bearer {token}"}
        tasks.append(("B", "GET", BOARD_URL, headers, None, f"test{i+1}_r{repeat+1}"))

# Group C: 비정상 토큰으로 POST /api/apply (401 유도) — 20건
for label, token in INVALID_TOKENS:
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    tasks.append(("C", "POST", APPLY_URL, headers, {"category": CATEGORY}, label))

TOTAL = len(tasks)

# ══════════════════════════════════════════════════════════════════════════════
#  배리어 + 워커 정의
# ══════════════════════════════════════════════════════════════════════════════

barrier          = threading.Barrier(TOTAL, timeout=BARRIER_TIMEOUT)
results          = [None] * TOTAL
fire_timestamps  = [0.0]  * TOTAL


def worker(index, group, method, url, headers, json_body, label):
    try:
        barrier.wait()
    except threading.BrokenBarrierError:
        results[index] = {
            "group": group, "status": 0, "time": 0,
            "label": label, "error": "BrokenBarrierError",
        }
        return

    fire_timestamps[index] = time.time()

    start = time.time()
    try:
        resp = http_client.request(
            method, url, headers=headers, json=json_body,
            timeout=REQUEST_TIMEOUT,
        )
        elapsed = time.time() - start
        results[index] = {
            "group": group, "status": resp.status_code,
            "time": elapsed, "label": label, "body": resp.text[:200],
        }
    except Exception as e:
        elapsed = time.time() - start
        results[index] = {
            "group": group, "status": 0,
            "time": elapsed, "label": label, "error": str(e)[:200],
        }


# ══════════════════════════════════════════════════════════════════════════════
#  발사
# ══════════════════════════════════════════════════════════════════════════════

print("=" * 70)
print("  Thundering Herd 원격 폭격 / remote_stress.py")
print("=" * 70)
print(f"\n  타겟  : {TARGET_HOST}")
print(f"  총 요청: {TOTAL}건")
print(f"  구성  : Group A(POST) {len(VALID_TOKENS)}건 | "
      f"Group B(GET) {len(VALID_TOKENS) * GET_REPEAT}건 | "
      f"Group C(401) {len(INVALID_TOKENS)}건")
print(f"\n  {TOTAL}개 스레드 생성 중...")

threads = []
for i, (group, method, url, headers, json_body, label) in enumerate(tasks):
    t = threading.Thread(
        target=worker,
        args=(i, group, method, url, headers, json_body, label),
        name=f"w{i}",
    )
    threads.append(t)

print(f"  스레드 시작 (배리어 대기 진입)...")
wall_start = time.time()

for t in threads:
    t.start()

print(f"  {TOTAL}번째 스레드 도착 대기 중 (timeout={BARRIER_TIMEOUT}s)...")

for t in threads:
    t.join(timeout=90)

wall_elapsed = time.time() - wall_start

# ══════════════════════════════════════════════════════════════════════════════
#  결과 집계
# ══════════════════════════════════════════════════════════════════════════════

print(f"\n{'=' * 70}")
print("  결과 리포트")
print(f"{'=' * 70}")

# 동시 발사 편차
valid_fires = [ts for ts in fire_timestamps if ts > 0]
if valid_fires:
    spread_ms = (max(valid_fires) - min(valid_fires)) * 1000
    print(f"\n[동시성 지표]")
    print(f"  전체 소요 시간    : {wall_elapsed:.3f}s")
    print(f"  발사 편차 (첫~끝) : {spread_ms:.1f}ms")
    print(f"  발사 완료 스레드  : {len(valid_fires)}/{TOTAL}")


def report_group(group_id, title, expected_ok=None):
    group = [r for r in results if r and r["group"] == group_id]
    if not group:
        print(f"\n[{title}] 결과 없음")
        return

    counts = {}
    for r in group:
        s = r["status"]
        counts[s] = counts.get(s, 0) + 1

    times = [r["time"] for r in group if r["time"] > 0]

    print(f"\n[{title}]  ({len(group)}건)")
    print("  상태 코드 분포:")
    for s in sorted(counts):
        note = ""
        if expected_ok and s == expected_ok:
            note = " ✓"
        elif s == 0:
            note = " (연결 실패)"
        print(f"    {s:>4}: {counts[s]}건{note}")

    if times:
        ts = sorted(times)
        n = len(ts)
        p50 = ts[n // 2]
        p95 = ts[min(int(n * 0.95), n - 1)]
        p99 = ts[min(int(n * 0.99), n - 1)]
        avg = statistics.mean(times)
        mx  = max(times)
        print(f"  응답 시간:")
        print(f"    평균 {avg:.3f}s | P50 {p50:.3f}s | P95 {p95:.3f}s | P99 {p99:.3f}s | 최대 {mx:.3f}s")

    if expected_ok:
        unexpected = [r for r in group if r["status"] != expected_ok]
        if unexpected:
            print(f"  예상 외 응답 샘플 (최대 5건):")
            for r in unexpected[:5]:
                detail = r.get("body", r.get("error", ""))[:100]
                print(f"    [{r['status']}] {r['label']}: {detail}")


report_group("A", "Group A — 유효 POST (운동 신청)", expected_ok=200)

# Group A 세부 분석
group_a = [r for r in results if r and r["group"] == "A"]
ok    = sum(1 for r in group_a if r["status"] == 200)
dup   = sum(1 for r in group_a if r["status"] == 409)
auth  = sum(1 for r in group_a if r["status"] == 401)
time_ = sum(1 for r in group_a if r["status"] == 400)
rate  = sum(1 for r in group_a if r["status"] == 429)
err   = sum(1 for r in group_a if r["status"] == 0)

print(f"  세부 분석:")
print(f"    신청 성공    (200): {ok}건")
print(f"    중복 차단    (409): {dup}건" + (" ← 유저당 1회이므로 0이어야 정상" if dup else ""))
print(f"    인증 실패    (401): {auth}건" + (" ← 0이어야 정상" if auth else ""))
print(f"    시간 오류    (400): {time_}건" + (" ← OPEN 시간대 밖에서 실행됨" if time_ else ""))
print(f"    Rate Limit   (429): {rate}건" + (" ← 유저당 1회이므로 0이어야 정상" if rate else ""))
print(f"    연결 실패      (0): {err}건")

report_group("B", "Group B — 유효 GET (게시판 조회)", expected_ok=200)
report_group("C", "Group C — 비정상 POST (401 유도)", expected_ok=401)

# Group C 유형별 분석
group_c = [r for r in results if r and r["group"] == "C"]
if group_c:
    type_map = {}
    for r in group_c:
        ft = r["label"]
        if ft not in type_map:
            type_map[ft] = {"total": 0, "ok": 0}
        type_map[ft]["total"] += 1
        if r["status"] == 401:
            type_map[ft]["ok"] += 1
    print("  유형별 401 달성률:")
    for ft, v in type_map.items():
        note = "정상" if v["ok"] == v["total"] else f"비정상 {v['total'] - v['ok']}건"
        print(f"    {ft:>20}: {v['ok']}/{v['total']}건 401 ({note})")

# 전체 요약
all_times  = [r["time"] for r in results if r and r["time"] > 0]
all_errors = [r for r in results if r and r["status"] == 0]

print(f"\n{'=' * 70}")
print("  전체 요약")
print(f"{'=' * 70}")
print(f"  총 요청: {TOTAL}건 | 완료: {sum(1 for r in results if r)}건 | 연결 실패: {len(all_errors)}건")
if all_times:
    throughput = len(all_times) / wall_elapsed
    print(f"  전체 소요: {wall_elapsed:.3f}s | 처리량: {throughput:.1f} req/s")
    print(f"  응답 시간: 평균 {statistics.mean(all_times):.3f}s | 최대 {max(all_times):.3f}s")

# 병목 진단
print(f"\n[병목 진단 힌트]")
if all_errors:
    print(f"  [!] 연결 실패 {len(all_errors)}건 -> 도메인/방화벽/서버 과부하 확인")
    for r in all_errors[:3]:
        print(f"      {r.get('error', 'unknown')[:100]}")
if time_:
    print(f"  [!] 400 오류 {time_}건 -> OPEN 시간대(토 22:00~일 10:00 KST) 밖에서 실행됨")

group_a_times = [r["time"] for r in group_a if r["time"] > 0]
group_b_times = [r["time"] for r in results if r and r["group"] == "B" and r["time"] > 0]
if group_a_times and group_b_times:
    a_avg = statistics.mean(group_a_times)
    b_avg = statistics.mean(group_b_times)
    if a_avg > b_avg * 2:
        ratio = a_avg / b_avg
        print(f"  [!] POST 평균({a_avg:.3f}s)이 GET 평균({b_avg:.3f}s)의 {ratio:.1f}배 -> board_store Lock 경합 의심")

print(f"\n{'=' * 70}")
print("  테스트 완료")
print(f"{'=' * 70}\n")
