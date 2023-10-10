import logging
from typing import Union

import praw
from praw import Reddit
from pythorhead import Lemmy

logging.basicConfig(
    format="%(asctime)s %(levelname)-8s %(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S",
)


def reddit_oauth(config: dict) -> Union[Reddit, None]:
    try:
        reddit = praw.Reddit(
            client_id=config.REDDIT_CLIENT_ID,
            client_secret=config.REDDIT_CLIENT_SECRET,
            password=config.REDDIT_PASSWORD,
            user_agent=config.REDDIT_USER_AGENT,
            redirect_url="http://localhost:8080",
            username=config.REDDIT_USERNAME,
        )
        logging.info(f"Logged into Reddit as {reddit.user.me()}")
    except Exception as e:
        reddit = None
        logging.error(f"Could not log into Reddit. Exception {e}.")
    return reddit


def lemmy_auth(config: dict) -> Union[Lemmy, None]:
    lemmy = lemmy_init_instance(config.LEMMY_INSTANCE)

    if lemmy:
        lemmy_login(config.LEMMY_USERNAME, config.LEMMY_PASSWORD)
        return lemmy
    return None


def lemmy_init_instance(lemmy_instance: str) -> Lemmy:
    try:
        lemmy = Lemmy(lemmy_instance, raise_exceptions=True)
        return lemmy

    except Exception as e:
        logging.error(f"Could not find Lemmy instance. Exception {e}.")
        return None


def lemmy_login(lemmy_username: str, lemmy_password: str) -> Lemmy:
    try:
        lemmy.log_in(lemmy_username, lemmy_password)
        logging.info(f"Logged into Lemmy as {lemmy_username}")
        return lemmy

    except Exception as e:
        logging.error(f"Could not log into Lemmy. Exception {e}.")
        return None
