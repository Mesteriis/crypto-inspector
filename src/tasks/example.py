from tasks.celery_app import celery_app


@celery_app.task
def example_task(x: int, y: int) -> int:
    """Example task that adds two numbers."""
    return x + y
