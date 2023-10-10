from dotenv import dotenv_values
from tinydb import TinyDB

from src.auth import lemmy_auth, reddit_oauth
from src.helper import Config
from src.mirror import get_threads_from_reddit, mirror_threads_to_lemmy


def mirror(db_path: str = "db.json"):
    config = Config(dotenv_values(".env"))

    reddit = reddit_oauth(config)

    DB = TinyDB(db_path)

    if not reddit:
        return

    threads = get_threads_from_reddit(reddit, config.REDDIT_SUBREDDIT, DB, limit=10)

    if threads:
        lemmy = lemmy_auth(config)

        if not lemmy:
            return

        mirror_threads_to_lemmy(lemmy, threads, config.LEMMY_COMMUNITY, DB)

    DB.close()


if __name__ == "__main__":
    mirror()
