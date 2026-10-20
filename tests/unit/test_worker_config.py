"""작업이 끝없이 '분석 중'에 남지 않게 하는 Celery·docker compose 설정."""

from pathlib import Path

from backend.workers.celery_app import celery_app

ROOT = Path(__file__).resolve().parents[2]


def test_tasks_have_time_limits_shorter_than_redelivery() -> None:
    conf = celery_app.conf
    assert conf.task_acks_late  # 끝난 뒤에 확인 → 죽은 worker의 작업은 다시 넘어온다
    # 부드러운 제한 < 강제 제한 < Redis 재전달: 살아 있는 작업이 두 번 돌지 않고, 죽은 작업은 15분 안에 다시 돈다
    redelivery = conf.broker_transport_options["visibility_timeout"]
    assert conf.task_soft_time_limit < conf.task_time_limit < redelivery <= 15 * 60
    assert conf.worker_soft_shutdown_timeout > 0


def test_compose_worker_requeues_unfinished_tasks_on_stop() -> None:
    for name in ("docker-compose.yml", "docker-compose.prod.yml"):
        text = (ROOT / name).read_text(encoding="utf-8")
        # SIGQUIT이어야 정해진 시간만 기다린 뒤 끝나지 않은 작업을 대기열로 돌려놓는다 (SIGTERM은 끝까지 기다림)
        assert "stop_signal: SIGQUIT" in text, name
        grace = int(text.split("stop_grace_period: ")[1].split("s")[0])
        assert grace > celery_app.conf.worker_soft_shutdown_timeout + 10, name
