from dotenv import dotenv_values
from tinydb import TinyDB
import schedule
import os

from src.auth import lemmy_auth, reddit_oauth
from src.helper import Config, DataBase, Thread
from src.mirror import get_threads_from_reddit, mirror_threads_to_lemmy
import datetime
import praw
import logging

logging.basicConfig(
    format="%(asctime)s %(levelname)-8s %(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S",
)


def mirror(
    reddit: praw.Reddit, database: TinyDB, filter: str, limit: int = 10, mirror_delay: int = 25,
) -> None:
    logging.info("Attempting to mirror threads")

    if not reddit:
        return

    threads = get_threads_from_reddit(
        reddit,
        config.REDDIT_SUBREDDIT,
        database,
        limit=limit,
        ignore=config.THREADS_TO_IGNORE,
        filter=filter
    )

    if threads:
        lemmy = lemmy_auth(config)

        if not lemmy:
            return

        # mirror_threads_to_lemmy(
        #    lemmy, threads, config.LEMMY_COMMUNITY, database, mirror_delay
        # )


if __name__ == "__main__":
    # get config
    config = Config(dotenv_values(".env"))

    backup_h = config.BACKUP_FILESTACK_EVERY_HOUR
    refresh_m = config.REFRESH_FILESTACK_EVERY_MINUTE
    mirror_s = config.MIRROR_THREADS_EVERY_SECOND
    mirror_delay_s = config.DELAY_BETWEEN_MIRRORED_THREADS_SECOND
    filter_limit = config.REDDIT_FILTER_THREAD_LIMIT

    # get latest backup of the database
    database_path = "data/mirrored_threads.json"
    filestack = DataBase(db_path=database_path)
    filestack.get_backup(
        app_secret=config.FILESTACK_APP_SECRET,
        apikey=config.FILESTACK_API_KEY,
        handle=config.FILESTACK_HANDLE_REFRESH,
    )

    def raiseError(e):
        raise e

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
        filter=config.FILTER_BY,
        limit=filter_limit,
        mirror_delay=mirror_delay_s,
    )
    logging.info(f"Scheduler started")
    logging.info(f"Mirroring every {mirror_s} seconds with a delay of {mirror_delay_s} seconds between threads; checking up to {filter_limit} threads at a time")
    logging.info(f"Refreshing the database file every {refresh_m} minutes; creating a backup copy every {backup_h} hours")

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

    # start scheduler
    with database:
        while True:
            schedule.run_pending()
