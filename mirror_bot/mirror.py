import praw
from pythorhead import Lemmy
from dotenv import dotenv_values
from typing import Union
import logging

logging.basicConfig(filename="mirror.log", encoding="utf-8", level=logging.DEBUG)

# load env vars (TODO: later, use praw.ini)

config = dotenv_values(".env")

print(".env loaded")

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

def _getattr_mod(__o: object, __name: str):
    try:
        return getattr(__o, __name)
    except AttributeError:
        return None

# authenticate with reddit with OAuth
def get_threads_to_mirror():
    reddit = praw.Reddit(
        client_id=REDDIT_CLIENT_ID,
        client_secret=REDDIT_CLIENT_SECRET,
        password=REDDIT_PASSWORD,
        user_agent=REDDIT_USER_AGENT,
        redirect_url="http://localhost:8080",
        username=REDDIT_USERNAME,
    )

    print("Logged into Reddit as", reddit.user.me())

    # check every hour/minute:

    # grab latest reddit posts (sorted by "new")

    subreddit = reddit.subreddit(REDDIT_SUBREDDIT)
    logging.info(f"Subreddit: {subreddit}")
    listing = subreddit.new(limit=100)

    # load a list of mirrored posts 
    # TODO: filter out posts that have already been mirrored
    threads_to_mirror = []
    for i in listing:
        url: str = _getattr_mod(i, "url")  # maybe they all have url??
        title: str = getattr(i, "title")
        body: Union[str, None] = _getattr_mod(i, "selftext")
        permalink: str = f"https://www.reddit.com/{_getattr_mod(i, 'permalink')}"
        reddit_id: str = _getattr_mod(i, "name")
        flairs: str = _getattr_mod(i, "link_flair_text")
        is_video: bool = _getattr_mod(i, "is_video")
        is_pinned: bool = _getattr_mod(i, "sitckied")
        is_nswf: bool = _getattr_mod(i, "over_18")
        is_poll: bool = True if _getattr_mod(i, "poll_data") else False
        is_locked: bool = _getattr_mod(i, "locked")

        data = {
            "submission_obj": i,
            "url": url,
            "title": title,
            "body": body,
            "permalink": permalink,
            "reddit_id": reddit_id,
            "flairs": flairs,
            "is_video": is_video,
            "is_pinned": is_pinned,
            "is_nswf": is_nswf,
            "is_poll": is_poll,
            "is_locked": is_locked,
        }

        if is_pinned or is_nswf or is_poll or is_locked:
            # ignore pinned, nsf, poll, and locked threads
            logging.info(f"Ignoring submission {i.name} with title {i.title}")
        else:
            logging.info(f"Committing submission {i.name} with title {i.title}")
            threads_to_mirror.append(data)

    return threads_to_mirror

def mirror_threads_on_lemmy(threads_to_mirror: dict):
    
    # authenticate with lemmy
    lemmy = Lemmy(LEMMY_INSTANCE)
    lemmy.log_in(LEMMY_USERNAME, LEMMY_PASSWORD)
    community_id = lemmy.discover_community(LEMMY_COMMUNITY)

    # TODO: add code to pythorhead to get the name of the user logged in
    print("Logged into Lemmy as", LEMMY_USERNAME)

    # create a mirror post on lemmy

    # add the reddit permalink to the post

    # concat the csv file with filtered out posts and add the reddit post id (aka 'name')
