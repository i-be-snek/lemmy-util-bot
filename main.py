from dotenv import dotenv_values
from tinydb import TinyDB

from src.auth import lemmy_auth, reddit_oauth
from src.helper import Config
from src.mirror import get_threads_from_reddit, mirror_threads_to_lemmy
import datetime
import praw
import logging

logging.basicConfig(
    format="%(asctime)s %(levelname)-8s %(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S",
)


def mirror(reddit: praw.Reddit, database: TinyDB, limit: int = 10, mirror_delay: int = 10) -> None:
    logging.info("Attempting to mirror threads")

    if not reddit:
        return

    threads = get_threads_from_reddit(
        reddit, config.REDDIT_SUBREDDIT, database, limit=limit
    )

    if threads:
        lemmy = lemmy_auth(config)

        if not lemmy:
            return

        mirror_threads_to_lemmy(lemmy, threads, config.LEMMY_COMMUNITY, database, mirror_delay)

    DB.close()


if __name__ == "__main__":
    import schedule

    # get config
    config = Config(dotenv_values(".env"))

    # authenticate with reddit once at the beginning
    reddit = reddit_oauth(config)
    DB = TinyDB("data/db.json")

    # if threads exist, authenticate with lemmy and mirror threads
    schedule.every(30).seconds.do(mirror, reddit=reddit, database=DB, limit=10)
    logging.info(
        f"Scheduler started"
    )

    while True:
        schedule.run_pending()
