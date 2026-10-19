from backend.services import notifications, push
from backend.workers import tasks


def send_notifications() -> None:
    """상태를 바꾼 요청 뒤에 부른다. 메일·웹 푸시 설정이 있을 때만 알림 발송 작업을 큐에 넣는다."""
    if notifications.email_enabled() or push.push_enabled():
        tasks.deliver_notifications.delay()
