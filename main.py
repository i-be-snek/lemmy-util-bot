import logging
import os
import random
import threading

import praw
import schedule
from pythorhead import Lemmy
from tinydb import TinyDB

from src.auth import lemmy_auth, reddit_oauth
from src.auto_mod import AutoMod
from src.helper import Config, DataBase, ScheduleType, Task
from src.mirror import get_threads_from_reddit, mirror_threads_to_lemmy

logging.basicConfig(
    format="%(asctime)s %(levelname)-8s %(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S",
)

schedule_logger = logging.getLogger("schedule")
# set to logging.DEBUG when debugging
# be careful: will reveal .env secrets
schedule_logger.setLevel(level=logging.INFO)


def mirror(
    reddit: praw.Reddit,
    database: TinyDB,
    mirror_threads_limit: int,
    filter: str,
    reddit_filter_limit: int = 10,
    mirror_delay: int = 25,
    cancel_after_first_run: bool = False,
) -> None:
    show_job_thread()

    if not reddit:
        return

    threads = get_threads_from_reddit(
        reddit,
        config.REDDIT_SUBREDDIT,
        database,
        limit=reddit_filter_limit,
        ignore_thread_types=config.REDDIT_THREADS_TO_IGNORE,
        filter=filter,
    )

    if threads:
        lemmy = lemmy_auth(config)

        if not lemmy:
            return

        thread_sample = random.sample(threads, mirror_threads_limit)
        logging.info(f"Capping the number of threads to mirror at {mirror_threads_limit}")

        mirror_threads_to_lemmy(lemmy, thread_sample, config.LEMMY_COMMUNITY, database, mirror_delay)

    logging.info(f"Posted {mirror_threads_limit} threads in total")

    # if this is the first mirror job to run
    if cancel_after_first_run:
        return schedule.CancelJob


def show_job_thread():
    logging.info("Task is running on thread %s" % threading.current_thread())


def automod_comment_on_new_threads(config: dict, lemmy: Lemmy):
    show_job_thread()
    auto_mod = AutoMod(lemmy, config.LEMMY_COMMUNITY, config.LEMMY_USERNAME)
    auto_mod.comment_on_new_threads(mod_message=config.LEMMY_MOD_MESSAGE_NEW_THREADS)


def raiseError(e):
    raise e


def run_threaded(thread_func, kwargs):
    job_thread = threading.Thread(target=thread_func, kwargs=kwargs)
    job_thread.start()


if __name__ == "__main__":
    # get config
    env_values = dict(os.environ)
    config = Config(env_values)
    needs_database = [Task.mirror_threads]

    # authenticate with lemmy
    lemmy = lemmy_auth(config)

    # schedule tasks
    if Task.mod_comment_on_new_threads in config.TASKS:
        interval = 60 * 3
        schedule.every(interval).seconds.do(
            run_threaded,
            thread_func=automod_comment_on_new_threads,
            kwargs={
                "config": config,
                "lemmy": lemmy,
            },
        )
        logging.info(f"TASK: Checking for new posts every {interval} seconds")

    if Task.mirror_threads in config.TASKS:
        backup_h = config.BACKUP_FILESTACK_EVERY_HOUR
        refresh_m = config.REFRESH_FILESTACK_EVERY_MINUTE
        mirror_delay_s = config.DELAY_BETWEEN_MIRRORED_THREADS_SECOND
        filter_limit = config.REDDIT_FILTER_THREAD_LIMIT
        reddit_cap = config.REDDIT_CAP_NUMBER_OF_MIRRORED_THREADS
        schedule_type = config.REDDIT_MIRROR_SCHEDULE_TYPE

        # get latest backup of the database
        database_path = "data/mirrored_threads.json"
        filestack = DataBase(db_path=database_path)
        filestack.get_backup(
            app_secret=config.FILESTACK_APP_SECRET,
            apikey=config.FILESTACK_API_KEY,
            handle=config.FILESTACK_HANDLE_REFRESH,
        )

        # confirm the file has been downloaded
        assert os.path.exists(database_path) or raiseError(FileNotFoundError)

        # initialize database
        database = TinyDB(database_path)

        # authenticate with reddit once at the beginning
        reddit = reddit_oauth(config)

        if schedule_type == ScheduleType.daily:
            time_utc = config.MIRROR_EVERY_DAY_AT
            # schedule to mirror every day at {time_utc}
            schedule.every().day.at(time_utc, "UTC").do(
                run_threaded,
                thread_func=mirror,
                kwargs={
                    "reddit": reddit,
                    "database": database,
                    "mirror_threads_limit": reddit_cap,
                    "filter": config.FILTER_BY,
                    "reddit_filter_limit": filter_limit,
                    "mirror_delay": mirror_delay_s,
                    "cancel_after_first_run": False,
                },
            )
            logging.info(
                f"TASK: Mirroring threads every every day at {time_utc} UTC with a delay of {mirror_delay_s} seconds between threads"
            )
            logging.info(
                f"Checking up to {filter_limit} threads at a time, posting {reddit_cap} at a time, at {time_utc} UTC.."
            )
        elif schedule_type == ScheduleType.every_x_seconds:
            # schedule to mirror every {mirror_s} seconds
            mirror_s = config.MIRROR_THREADS_EVERY_SECOND
            schedule.every(mirror_s).seconds.do(
                run_threaded,
                thread_func=mirror,
                kwargs={
                    "reddit": reddit,
                    "database": database,
                    "mirror_threads_limit": reddit_cap,
                    "filter": config.FILTER_BY,
                    "reddit_filter_limit": filter_limit,
                    "mirror_delay": mirror_delay_s,
                    "cancel_after_first_run": False,
                },
            )

            # the scheduler will run the first job after {mirror_delay_s} seconds
            # but for the bot to activate immediately, we can run the function
            # first as a separate job and cancel it after the first run
            schedule.every().seconds.do(
                mirror,
                reddit=reddit,
                database=database,
                mirror_threads_limit=reddit_cap,
                filter=config.FILTER_BY,
                reddit_filter_limit=filter_limit,
                mirror_delay=mirror_delay_s,
                cancel_after_first_run=True,
            )
            logging.info(
                f"TASK: Mirroring threads every {mirror_s} seconds with a delay of {mirror_delay_s} seconds between threads"
            )

            logging.info(
                f"Checking up to {filter_limit} threads at a time, posting {reddit_cap} at a time, starting now..."
            )

        # refresh the database file in filestack
        schedule.every(refresh_m).minutes.do(
            filestack.refresh_backup,
            app_secret=config.FILESTACK_APP_SECRET,
            apikey=config.FILESTACK_API_KEY,
            handle=config.FILESTACK_HANDLE_REFRESH,
        )

        # refresh the database backup in filestack
        schedule.every(backup_h).hours.do(
            filestack.refresh_backup,
            app_secret=config.FILESTACK_APP_SECRET,
            apikey=config.FILESTACK_API_KEY,
            handle=config.FILESTACK_HANDLE_BACKUP,
        )

        logging.info(
            f"Refreshing the database file every {refresh_m} minutes; creating a backup copy every {backup_h} hours"
        )

    if any([x in needs_database for x in config.TASKS]):
        # start scheduler with database
        logging.info(f"Scheduler started")
        with database:
            while True:
                schedule.run_pending()

    else:
        # otherwise, run without database
        logging.info(f"Scheduler started")
        while True:
            schedule.run_pending()
