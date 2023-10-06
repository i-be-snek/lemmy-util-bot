import praw
from pythorhead import Lemmy
from pythorhead.types import LanguageType
from dotenv import dotenv_values
from typing import Union
import logging
from tinydb import TinyDB, Query

logging.basicConfig(filename="mirror.log", encoding="utf-8", level=logging.DEBUG)

# load env vars (TODO: later, use praw.ini)

config = dotenv_values(".env")

logging.info(".env loaded")

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

DB = TinyDB("db.json")


def _getattr_mod(__o: object, __name: str):
    try:
        return getattr(__o, __name)
    except AttributeError:
        return None


# authenticate with reddit with OAuth
def get_reddit_threads(limit: int = 100):
    reddit = praw.Reddit(
        client_id=REDDIT_CLIENT_ID,
        client_secret=REDDIT_CLIENT_SECRET,
        password=REDDIT_PASSWORD,
        user_agent=REDDIT_USER_AGENT,
        redirect_url="http://localhost:8080",
        username=REDDIT_USERNAME,
    )

    logging.info(f"Logged into Reddit as {reddit.user.me()}")

    # validate limit
    if limit > 100:
        logging.info("Max limit is 100, limit now set to 100.")
        limit = 100

    # check every hour/minute:

    # grab latest reddit posts (sorted by "new")

    subreddit = reddit.subreddit(REDDIT_SUBREDDIT)
    logging.info(f"Subreddit: {subreddit}")
    listing = subreddit.new(limit=limit)

    # load a list of mirrored posts
    # TODO: filter out posts that have already been mirrored
    threads_to_mirror = []
    q = Query()

    for i in listing:
        reddit_id: str = _getattr_mod(i, "name")
        if DB.search(q.reddit_id == reddit_id):
            logging.info(f"Post with id {i} has already been mirrored.")
            is_mirrored = True
        else:
            is_mirrored = False

        is_pinned: bool = False if _getattr_mod(i, "sitckied") == None else True
        is_nswf: bool = _getattr_mod(i, "over_18")
        is_poll: bool = True if _getattr_mod(i, "poll_data") else False
        is_locked: bool = _getattr_mod(i, "locked")

        if is_pinned or is_nswf or is_poll or is_locked or is_mirrored:
            # ignore pinned, nsf, poll, and locked threads
            logging.info(
                f"""
                Ignoring submission {i.name} with title {i.title}; is_pinned: {is_pinned}; is_nswf: {is_nswf}; is_poll: {is_poll}; is_locked: {is_locked}; is_mirrored --> {is_mirrored}
            """
            )

        else:
            # if the reddit_id is in the url, it's the url to the reddit post
            # otherwise, it's the url to external content embedded into the thread
            url_attr = _getattr_mod(i, "url")
            url: Union[str, None] = (
                None if reddit_id.split("_", 1)[1] in url_attr else url_attr
            )
            title: str = getattr(i, "title")
            body_attr = _getattr_mod(i, "selftext")
            body: Union[str, None] = None if body_attr == "" else body_attr
            permalink: str = f"https://www.reddit.com{_getattr_mod(i, 'permalink')}"
            flair: Union[str, None] = _getattr_mod(i, "link_flair_text")
            is_video: bool = _getattr_mod(i, "is_video")

            data = {
                # "submission_obj": i,
                "url": url,
                "url_attr": url_attr,
                "title": title,
                "body": body,
                "permalink": permalink,
                "reddit_id": reddit_id,
                "flair": flair,
                "is_video": is_video,
                "is_pinned": is_pinned,
                "is_nswf": is_nswf,
                "is_poll": is_poll,
                "is_locked": is_locked,
            }
            logging.info(f"Committing submission {i.name} with title {i.title}")
            threads_to_mirror.append(data)

    logging.info(f"Found {len(threads_to_mirror)} threads to mirror")
    return threads_to_mirror


def to_lemmy(threads_to_mirror: dict):
    # authenticate with lemmy
    lemmy = Lemmy(LEMMY_INSTANCE)
    lemmy.log_in(LEMMY_USERNAME, LEMMY_PASSWORD)
    community_id = lemmy.discover_community(LEMMY_COMMUNITY)

    # TODO: add code to pythorhead to get the name of the user logged in
    logging.info(f"Logged into Lemmy as {LEMMY_USERNAME}")

    # create a mirror post on lemmy
    q = Query()

    # add the reddit permalink to the post
    for thread in threads_to_mirror:
        # double check if this thread has already been mirrored
        if DB.search(q.reddit_id == thread["reddit_id"]):
            logging.info(
                f"Post with id {thread['reddit_id']} has already been mirrored."
            )
            pass

        # generate a bot disclaimer
        bot_body = f"(This post was mirrored by a bot. [The original post can be found here]({thread['permalink']}))"

        # add the bot disclaimer to the post and link to the original content
        post_body = (
            thread["body"] + "\n\n" + bot_body
            if isinstance(thread["body"], str)
            else bot_body
        )

        # add flair if it exists
        thread_title = (
            f"{thread['flair']} {thread['title']}"
            if thread["flair"]
            else thread["title"]
        )

        try:
            lemmy.post.create(
                community_id=community_id,
                name=thread_title,
                url=thread["url"],
                nsfw=None,
                body=post_body,
                language_id=LanguageType.EN,
            )

            DB.insert(thread)
            logging.info(f"Inserted {thread['reddit_id']} into TinyDB")

        except Exception as e:
            logging.error(
                f"Lemmy cound not create a post for thread {thread['reddit_id']}. Exception {e}."
            )
