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


def reddit_oauth(
    REDDIT_CLIENT_ID: str,
    REDDIT_CLIENT_SECRET: str,
    REDDIT_PASSWORD: str,
    REDDIT_USER_AGENT: str,
    REDDIT_USERNAME: str,
) -> Union[Reddit, None]:
    try:
        reddit = praw.Reddit(
            client_id=REDDIT_CLIENT_ID,
            client_secret=REDDIT_CLIENT_SECRET,
            password=REDDIT_PASSWORD,
            user_agent=REDDIT_USER_AGENT,
            redirect_url="http://localhost:8080",
            username=REDDIT_USERNAME,
        )
        logging.info(f"Logged into Reddit as {reddit.user.me()}")
    except Exception as e:
        reddit = None
        logging.error(f"Could not log into Reddit. Exception {e}.")
    return reddit


def lemmy_auth(
    LEMMY_USERNAME: str, LEMMY_PASSWORD: str, LEMMY_INSTANCE: str
) -> Union[Lemmy, None]:
    try:
        lemmy = Lemmy(LEMMY_INSTANCE)
        lemmy.log_in(LEMMY_USERNAME, LEMMY_PASSWORD)
        logging.info(f"Logged into Lemmy as {LEMMY_USERNAME}")

    except Exception as e:
        lemmy = None
        logging.error(f"Could not log into Lemmy. Exception {e}.")
    return lemmy
