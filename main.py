from mirror_bot.mirror import mirror_threads_to_lemmy, get_threads_from_reddit
from mirror_bot.helper import check_configs
from mirror_bot.auth import reddit_oauth, lemmy_auth

from dotenv import dotenv_values
from tinydb import TinyDB

def mirror(db_path: str = "db.json"):
    config = dotenv_values(".env")
    if not check_configs(config):
        return

    LEMMY_USERNAME = config["LEMMY_USERNAME"]
    LEMMY_PASSWORD = config["LEMMY_PASSWORD"]
    LEMMY_INSTANCE = config["LEMMY_INSTANCE"]
    LEMMY_COMMUNITY = config["LEMMY_COMMUNITY"]

    REDDIT_CLIENT_ID = config["REDDIT_CLIENT_ID"]
    REDDIT_CLIENT_SECRET = config["REDDIT_CLIENT_SECRET"]
    REDDIT_PASSWORD = config["REDDIT_PASSWORD"]
    REDDIT_USER_AGENT = config["REDDIT_USER_AGENT"]
    REDDIT_USERNAME = config["REDDIT_USERNAME"]
    REDDIT_SUBREDDIT = config["REDDIT_SUBREDDIT"]

    reddit = reddit_oauth(
        REDDIT_CLIENT_ID,
        REDDIT_CLIENT_SECRET,
        REDDIT_PASSWORD,
        REDDIT_USER_AGENT,
        REDDIT_USERNAME,
    )

    DB = TinyDB(db_path)

    if not reddit:
        return

    threads = get_threads_from_reddit(reddit, REDDIT_SUBREDDIT, DB)
    
    if threads:
        lemmy = lemmy_auth(LEMMY_USERNAME, LEMMY_PASSWORD, LEMMY_INSTANCE)

        if not lemmy:
            return

        mirror_threads_to_lemmy(lemmy, threads, LEMMY_COMMUNITY, DB)
        
    DB.close()

if __name__ == "__main__":
    mirror()
