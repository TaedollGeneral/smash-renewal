# notifications/scheduler.py — 알림 인메모리 상태 주간 초기화
#
# 이 모듈은 별도 스레드를 시작하지 않는다.
# 실제 스케줄링(토요일 00:00 KST 트리거)은 time_control/scheduler_logic.py의
# weekly-reset 스레드(start_reset_scheduler)가 담당한다.
#
# 호출 흐름:
#   time_control/scheduler_logic._reset_scheduler_worker()
#     └─ notifications.scheduler.reset_weekly()
#          └─ notifications.store.reset_weekly_state()


def reset_weekly() -> None:
    """알림 인메모리 상태를 주간 초기화한다 (매주 토요일 00:00 KST 호출).

    순환 import 방지를 위해 notifications.store를 여기서 import하지 않고,
    실제 작업은 store.reset_weekly_state()에 위임한다.
    이 함수 자체는 진입점(entry point) 역할만 한다.
    """
    from notifications.store import reset_weekly_state
    reset_weekly_state()
