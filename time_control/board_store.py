# board_store.py — 인메모리 게시판 저장소 + 더티 플래그 배치 저장
#
# AWS EC2 프리 티어(1 GB) 환경에서 2초 폴링과 선착순 신청의
# 디스크 I/O 부하를 방지하기 위해 DB 대신 인메모리 딕셔너리를 사용한다.
# 데이터 변경이 발생했을 때만 3초 주기로 로컬 JSON 파일에 백업한다.
#
# 모든 공개 함수는 threading.Lock으로 보호되어 Thread-safe하다.

import json
import os
import threading
import time
from pathlib import Path

from .scheduler_logic import Category

# ── 설정 ──────────────────────────────────────────────────────────────────────

_BASE_DIR = Path(__file__).resolve().parent.parent
_BACKUP_PATH = _BASE_DIR / "board_backup.json"
_SAVE_INTERVAL = 3  # 백그라운드 저장 주기 (초)

# ── 전역 상태 ─────────────────────────────────────────────────────────────────

_lock = threading.Lock()

# 카테고리별 신청 리스트 — 조회 O(1), DB 없이 인메모리 관리
# {
#   "WED_REGULAR": [
#       {"user_id": "1234", "name": "홍길동", "type": "member", "timestamp": 1716301234.56},
#       ...
#   ],
#   "WED_GUEST": [],
#   ...
# }
_board_data: dict[str, list[dict]] = {cat.value: [] for cat in Category}

# 더티 플래그: 변경 발생 시 True → 백그라운드 워커가 저장 후 False
_is_board_changed: bool = False


# ── 공개 API (읽기) ───────────────────────────────────────────────────────────

def get_board(category: str) -> list[dict]:
    """특정 카테고리의 신청 목록을 반환한다 (얕은 복사본).

    Args:
        category: Category enum 값 (예: "WED_REGULAR")

    Returns:
        해당 카테고리의 신청 항목 리스트. 카테고리가 없으면 빈 리스트.
    """
    with _lock:
        return list(_board_data.get(category, []))


def get_all_boards() -> dict[str, list[dict]]:
    """전체 게시판 데이터의 스냅샷을 반환한다."""
    with _lock:
        return {k: list(v) for k, v in _board_data.items()}


# ── 공개 API (쓰기) ───────────────────────────────────────────────────────────

def add_entry(category: str, entry: dict) -> bool:
    """카테고리에 신청 항목을 추가한다.

    Args:
        category: Category enum 값
        entry: {"user_id": str, "name": str, "type": str, "timestamp": float}

    Returns:
        True — 추가 성공, False — 유효하지 않은 카테고리
    """
    global _is_board_changed
    with _lock:
        if category not in _board_data:
            return False
        _board_data[category].append(entry)
        _is_board_changed = True
    return True


def apply_entry(category: str, entry: dict) -> tuple[bool, str | None]:
    """신청 항목을 원자적으로 추가한다 (중복 검사 + 추가 + 정렬).

    단일 Lock 내에서 중복 검사 → append → 타임스탬프 정렬 → 더티 플래그
    설정을 모두 수행하여 선착순 동시성을 보장한다.

    Args:
        category: Category enum 값
        entry: {"user_id": str, "name": str, "type": str, "timestamp": float}

    Returns:
        (True, None)   — 추가 성공
        (False, reason) — 실패 (중복 또는 유효하지 않은 카테고리)
    """
    global _is_board_changed
    with _lock:
        if category not in _board_data:
            return False, "유효하지 않은 카테고리입니다."

        # 중복 신청 검사
        for existing in _board_data[category]:
            if existing["user_id"] == entry["user_id"]:
                return False, "이미 신청되어 있습니다."

        _board_data[category].append(entry)
        _board_data[category].sort(
            key=lambda x: (
                not ("(ob)" in x["name"].lower() or "(교류전)" in x["name"].lower()),
                x["timestamp"],
            )
        )
        _is_board_changed = True

    return True, None


def remove_entry(category: str, user_id: str) -> bool:
    """카테고리에서 user_id에 해당하는 항목을 제거한다.

    Returns:
        True — 제거 성공, False — 항목 없음 또는 유효하지 않은 카테고리
    """
    global _is_board_changed
    with _lock:
        entries = _board_data.get(category)
        if entries is None:
            return False
        for i, entry in enumerate(entries):
            if entry.get("user_id") == user_id:
                entries.pop(i)
                _is_board_changed = True
                return True
    return False


def reset_all() -> None:
    """모든 카테고리의 데이터를 초기화하고 백업 파일을 삭제한다.

    매주 토요일 00:00 스케줄러에서 호출된다.
    """
    global _is_board_changed
    with _lock:
        for cat in _board_data:
            _board_data[cat].clear()
        _is_board_changed = False

    # 백업 파일 삭제
    try:
        _BACKUP_PATH.unlink(missing_ok=True)
    except OSError:
        pass


# ── 백업 / 복구 ──────────────────────────────────────────────────────────────

def load_from_backup() -> bool:
    """서버 시작 시 board_backup.json이 존재하면 인메모리에 로드한다.

    Returns:
        True — 복구 성공, False — 파일 없음 또는 파싱 실패
    """
    if not _BACKUP_PATH.exists():
        return False

    try:
        with open(_BACKUP_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return False

    with _lock:
        for cat in _board_data:
            _board_data[cat] = data.get(cat, [])
    return True


def _save_to_backup() -> None:
    """인메모리 데이터를 board_backup.json에 원자적으로 덮어쓴다.

    tmp 파일에 먼저 기록한 뒤 os.replace()로 교체하여
    쓰기 도중 장애 시 기존 백업이 훼손되지 않도록 한다.
    """
    with _lock:
        snapshot = {k: list(v) for k, v in _board_data.items()}

    tmp_path = _BACKUP_PATH.with_suffix(".tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, ensure_ascii=False)
    os.replace(str(tmp_path), str(_BACKUP_PATH))


# ── 백그라운드 세이브 워커 ────────────────────────────────────────────────────

def _save_worker() -> None:
    """_SAVE_INTERVAL(3초) 간격으로 깨어나 더티 플래그가 True이면 백업한다."""
    global _is_board_changed
    while True:
        time.sleep(_SAVE_INTERVAL)
        if _is_board_changed:
            try:
                _save_to_backup()
                _is_board_changed = False
            except Exception:
                pass  # 다음 주기에 재시도


def start_background_saver() -> None:
    """백그라운드 저장 데몬 스레드를 시작한다.

    데몬 스레드이므로 메인 프로세스 종료 시 자동으로 종료된다.
    """
    t = threading.Thread(target=_save_worker, daemon=True, name="board-saver")
    t.start()
