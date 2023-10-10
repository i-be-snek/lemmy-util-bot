from dotenv import dotenv_values
from tinydb import TinyDB

from src.auth import lemmy_auth, reddit_oauth
from src.helper import Config
from src.mirror import get_threads_from_reddit, mirror_threads_to_lemmy
import datetime


def mirror(db_path: str = "db.json", limit: int = 10):
    print(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    config = Config(dotenv_values(".env"))

    reddit = reddit_oauth(config)

    DB = TinyDB(db_path)

    if not reddit:
        return

    threads = get_threads_from_reddit(reddit, config.REDDIT_SUBREDDIT, DB, limit=limit)

    if threads:
        lemmy = lemmy_auth(config)

        if not lemmy:
            return

        mirror_threads_to_lemmy(lemmy, threads, config.LEMMY_COMMUNITY, DB)

    DB.close()


if __name__ == "__main__":
    import schedule

    print(f"Scheduler started at {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    schedule.every(30).seconds.do(mirror, limit=10)

    while True:
        schedule.run_pending()
