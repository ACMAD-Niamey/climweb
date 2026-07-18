from celery.schedules import crontab
from celery.signals import task_prerun, worker_process_init, worker_ready
from celery_singleton import Singleton, clear_locks
from django.core.management import call_command
from loguru import logger
from opentelemetry import baggage, context

from django.conf import settings

from climweb.config.celery import app
from climweb.config.telemetry.telemetry import setup_telemetry, setup_logging
from climweb.config.telemetry.utils import otel_is_enabled

TASK_NAME_KEY = "celery.task_name"


@worker_process_init.connect
def initialize_otel(**kwargs):
    setup_telemetry(add_django_instrumentation=False)
    setup_logging()


@task_prerun.connect
def before_task(task_id, task, *args, **kwargs):
    if otel_is_enabled():
        context.attach(baggage.set_baggage(TASK_NAME_KEY, task.name))


@worker_ready.connect
def unlock_all(**kwargs):
    # Clear any singleton locks left behind by a previous worker crash.
    # Without this, a task killed mid-run (e.g. by CELERY_WORKER_MAX_MEMORY_PER_CHILD)
    # would leave its Redis lock open and all subsequent scheduled runs would be skipped.
    clear_locks(app)


@app.task(
    base=Singleton,
    bind=True
)
def run_backup(self):
    # Run the `dbbackup` command
    logger.info("[BACKUP] Running backup")
    call_command('dbbackup', '--clean', '--noinput')
    
    # Run the `mediabackup` command
    logger.info("[BACKUP] Running mediabackup")
    call_command('mediabackup', '--clean', '--noinput')


if "forecastmanager" in settings.INSTALLED_APPS:
    # lock_expiry prevents the singleton lock from persisting indefinitely if the
    # worker is killed (e.g. by CELERY_WORKER_MAX_MEMORY_PER_CHILD) before the
    # task completes and can release the lock normally.  Set to slightly longer
    # than the worst-case runtime so a legitimately-running task is never evicted,
    # but a stuck lock is cleared within a reasonable window.
    _FORECAST_LOCK_EXPIRY = 1800  # 30 minutes

    @app.task(
        base=Singleton,
        bind=True,
        lock_expiry=_FORECAST_LOCK_EXPIRY,
    )
    def download_forecast(self):
        # Run the `generate_forecast` command
        logger.info("[FORECAST] Running generate_forecast")
        try:
            call_command('generate_auto_forecast')
        except Exception as exc:
            logger.error(f"[FORECAST] generate_forecast failed: {exc}")
            raise  # re-raise so Celery records the failure and releases the lock

    @app.task(
        base=Singleton,
        bind=True,
        lock_expiry=_FORECAST_LOCK_EXPIRY,
    )
    def clear_old_forecasts(self):
        # Run the `clear_old_forecasts` command
        logger.info("[FORECAST] Running clear_old_forecasts")
        try:
            call_command('clear_old_forecasts')
        except Exception as exc:
            logger.error(f"[FORECAST] clear_old_forecasts failed: {exc}")
            raise


if "climweb_wdqms" in settings.INSTALLED_APPS:
    @app.task(base=Singleton, bind=True)
    def run_wdqms_stats(self, variable):
        # Log that the task is starting
        logger.info(f"[WDQMS] Running wdqms_stats for {variable}")

        # Run the `wdqms_stats` management command
        call_command('wdqms_stats', '-var', variable)


def _iter_review_enabled_pages():
    """Every live page of every form-page type that carries
    FormPageReviewSettingsMixin (see climweb.base.mixins) - discovered via
    __subclasses__() rather than a hardcoded import list, so a new form page
    type picks up the weekly digest / pre-deadline summary automatically
    the moment it adds the mixin, with no change needed here.
    """
    from climweb.base.mixins import FormPageReviewSettingsMixin

    for model in FormPageReviewSettingsMixin.__subclasses__():
        yield from model.objects.live()


def _submissions_admin_url(page):
    from django.conf import settings
    from django.urls import reverse

    path = reverse('wagtailforms:list_submissions', args=[page.id])
    base_url = settings.WAGTAILADMIN_BASE_URL or page.get_site().root_url
    return base_url.rstrip('/') + path


@app.task(base=Singleton)
def send_weekly_submission_digest():
    """Every Monday: email each notification address a submission-count
    summary for its form page (see setup_periodic_tasks below)."""
    from datetime import timedelta
    from django.utils import timezone
    from climweb.base.mail import send_mail

    week_ago = timezone.now() - timedelta(days=7)

    for page in _iter_review_enabled_pages():
        recipients = page.get_notification_emails()
        if not recipients:
            continue

        submissions = page.get_submissions()
        total = submissions.count()
        this_week = submissions.filter(submit_time__gte=week_ago).count()

        logger.info(f"[SUBMISSION_DIGEST] Weekly digest for '{page.title}': "
                   f"{this_week} new, {total} total")

        send_mail(
            f"Weekly submissions digest: {page.title}",
            (
                f"Weekly submissions summary for '{page.title}':\n\n"
                f"New submissions this week: {this_week}\n"
                f"Total submissions: {total}\n\n"
                f"View submissions: {_submissions_admin_url(page)}\n"
            ),
            recipients,
        )


@app.task(base=Singleton)
def send_pre_deadline_submission_summary():
    """Every day: for any form page whose closing date is tomorrow, email
    the notification addresses a summary + link to view submissions before
    it closes (see setup_periodic_tasks below)."""
    from datetime import timedelta
    from django.utils import timezone
    from climweb.base.mail import send_mail

    tomorrow = timezone.now().date() + timedelta(days=1)

    for page in _iter_review_enabled_pages():
        closing_date = page.get_submissions_closing_date()
        if closing_date != tomorrow:
            continue

        recipients = page.get_notification_emails()
        if not recipients:
            continue

        total = page.get_submissions().count()

        logger.info(f"[SUBMISSION_DIGEST] Pre-deadline summary for '{page.title}' "
                   f"(closes {closing_date}): {total} total submissions")

        send_mail(
            f"Closing tomorrow: {page.title} — {total} submission(s) so far",
            (
                f"'{page.title}' closes to new submissions tomorrow ({closing_date}).\n\n"
                f"Total submissions so far: {total}\n\n"
                f"View submissions: {_submissions_admin_url(page)}\n"
            ),
            recipients,
        )


@app.on_after_finalize.connect
def setup_periodic_tasks(sender, **kwargs):
    # run_backup every day at midnight
    sender.add_periodic_task(
        crontab(hour=0, minute=0),
        run_backup.s(),
        name="run-backup-every-day-midnight",
    )

    # weekly submissions digest every Monday at 07:00
    sender.add_periodic_task(
        crontab(hour=7, minute=0, day_of_week=1),
        send_weekly_submission_digest.s(),
        name="send-weekly-submission-digest-every-monday",
    )

    # pre-deadline submissions summary every day at 07:00
    sender.add_periodic_task(
        crontab(hour=7, minute=0),
        send_pre_deadline_submission_summary.s(),
        name="send-pre-deadline-submission-summary-every-day",
    )

    if "forecastmanager" in settings.INSTALLED_APPS:
        # download_forecast every hour
        sender.add_periodic_task(
            crontab(minute=0),
            download_forecast.s(),
            name="download-forecast-every-hour",
        )

        # clear_old_forecasts every day at midnight
        sender.add_periodic_task(
            crontab(hour=0, minute=0),
            clear_old_forecasts.s(),
            name="clear-old-forecasts-every-day-midnight",
        )

    if "climweb_wdqms" in settings.INSTALLED_APPS:
        # Schedule task for pressure at 00:00 and 12:00
        sender.add_periodic_task(
            crontab(hour='0,12', minute=0),
            run_wdqms_stats.s('pressure'),
            name='Run wdqms_stats for pressure at 00:00 and 12:00'
        )

        # Schedule task for temperature at 00:00 and 12:00
        sender.add_periodic_task(
            crontab(hour='0,12', minute=0),
            run_wdqms_stats.s('temperature'),
            name='Run wdqms_stats for temperature at 00:00 and 12:00'
        )

        # Schedule task for humidity at 00:00 and 12:00
        sender.add_periodic_task(
            crontab(hour='0,12', minute=0),
            run_wdqms_stats.s('humidity'),
            name='Run wdqms_stats for humidity at 00:00 and 12:00'
        )

        # Schedule task for meridional_wind at 00:00 and 12:00
        sender.add_periodic_task(
            crontab(hour='0,12', minute=0),
            run_wdqms_stats.s('meridional_wind'),
            name='Run wdqms_stats for meridional_wind at 00:00 and 12:00'
        )

        # Schedule task for zonal_wind at 00:00 and 12:00
        sender.add_periodic_task(
            crontab(hour='0,12', minute=0),
            run_wdqms_stats.s('zonal_wind'),
            name='Run wdqms_stats for zonal_wind at 00:00 and 12:00'
        )
