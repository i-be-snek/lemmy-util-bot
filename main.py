from dotenv import dotenv_values
from tinydb import TinyDB
import schedule
import os

from src.auth import lemmy_auth, reddit_oauth
from src.helper import Config, DataBase, Task
from src.mirror import get_threads_from_reddit, mirror_threads_to_lemmy
from src.auto_mod import AutoMod
import praw
import logging
from pythorhead import Lemmy
import random

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
    logging.info("Attempting to mirror threads")

    if not reddit:
        return

    threads = get_threads_from_reddit(
        reddit,
        config.REDDIT_SUBREDDIT,
        database,
        limit=reddit_filter_limit,
        ignore=config.THREADS_TO_IGNORE,
        filter=filter,
    )

    if threads:
        lemmy = lemmy_auth(config)

        if not lemmy:
            return

        thread_sample = random.sample(threads, mirror_threads_limit)
        logging.info(f"Cappting the number of threads to mirror at {mirror_threads_limit}")

        mirror_threads_to_lemmy(
            lemmy, thread_sample, config.LEMMY_COMMUNITY, database, mirror_delay
        )

    # if this is the first mirror job to run
    if cancel_after_first_run:
        return schedule.CancelJob


def automod_comment_on_new_threads(config: dict, lemmy: Lemmy):
    auto_mod = AutoMod(lemmy, config.LEMMY_COMMUNITY, config.LEMMY_USERNAME)
    auto_mod.comment_on_new_threads()


def raiseError(e):
    raise e


if __name__ == "__main__":
    # get config
    config = Config(dotenv_values(".env"))
    needs_database = [Task.mirror_threads]

    # authenticate with lemmy
    lemmy = lemmy_auth(config)

    # schedule tasks
    if Task.mod_comment_on_new_threads in config.TASKS:
        interval = 120
        schedule.every(interval).seconds.do(
            automod_comment_on_new_threads, config=config, lemmy=lemmy
        )
        logging.info(f"TASK: Checking for new posts every {interval} seconds")

    if Task.mirror_threads in config.TASKS:
        backup_h = config.BACKUP_FILESTACK_EVERY_HOUR
        refresh_m = config.REFRESH_FILESTACK_EVERY_MINUTE
        mirror_s = config.MIRROR_THREADS_EVERY_SECOND
        mirror_delay_s = config.DELAY_BETWEEN_MIRRORED_THREADS_SECOND
        filter_limit = config.REDDIT_FILTER_THREAD_LIMIT
        reddit_cap = config.REDDIT_CAP_NUMBER_OF_MIRRORED_THREADS

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

        # if threads exist, authenticate with lemmy and mirror threads
        schedule.every(mirror_s).seconds.do(
            mirror,
            reddit=reddit,
            database=database,
            mirror_threads_limit=reddit_cap,
            filter=config.FILTER_BY,
            reddit_filter_limit=filter_limit,
            mirror_delay=mirror_delay_s,
        )

        # the scheduler will run the first job after {mirror_s} seconds
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
            f"TASK: Mirroring threads every {mirror_s} seconds with a delay of {mirror_delay_s} seconds between threads")
        
        logging.info(f"Checking up to {filter_limit} threads at a time, posting {reddit_cap} at a time, starting now..."
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
