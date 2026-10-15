from backend.services import notifications
from backend.workers import tasks


def send_emails() -> None:
    """상태를 바꾼 요청 뒤에 부른다. 메일 설정이 있을 때만 알림 메일 발송 작업을 큐에 넣는다."""
    if notifications.email_enabled():
        tasks.deliver_notifications.delay()
