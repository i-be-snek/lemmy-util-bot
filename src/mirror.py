import logging
import re
from time import sleep
from typing import List, Union

import praw
from praw.models import ListingGenerator
from praw.reddit import Submission
from pythorhead import Lemmy
from pythorhead.types import LanguageType
from tinydb import TinyDB

from src.helper import RedditThread, Util

logging.basicConfig(
    format="%(asctime)s %(levelname)-8s %(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S",
)


def _rule_1_check_funday_friday_flair(flair: str) -> Union[bool, None]:
    # if "Fun" in the flair and the day is not Friday
    from datetime import datetime

    if flair:
        if flair.find("Fun") == 1 and datetime.now().strftime("%A") != "Friday":
            # ...then ignore
            return True


def _extract_threads_to_mirror(
    listing: ListingGenerator,
    DB: TinyDB,
    ignore_thread_types: list[RedditThread] = [
        RedditThread.mirrored,
        RedditThread.pinned,
        RedditThread.nsfw,
        RedditThread.poll,
        RedditThread.locked,
        RedditThread.video,
        RedditThread.url,
    ],
) -> List[dict]:
    logging.info(f"Ignoring: {', '.join([_.value for _ in ignore_thread_types])}")

    threads_to_mirror = []
    reddit_domain = "https://www.reddit.com"

    for i in listing:
        ignoring_post = False

        reddit_id: str = Util._getattr_mod(i, "name")

        logging.info(f"Checking post {reddit_id}...")

        is_mirrored = True if Util._check_thread_in_db(reddit_id, DB) else False
        is_pinned: bool = False if Util._getattr_mod(i, "sitckied") == None else True
        is_nsfw: bool = Util._getattr_mod(i, "over_18")
        is_poll: bool = True if Util._getattr_mod(i, "poll_data") else False
        is_locked: bool = Util._getattr_mod(i, "locked")
        is_video: bool = Util._getattr_mod(i, "is_video")

        url_attr = Util._getattr_mod(i, "url")

        # if the reddit_id is in the url, it's the url to the reddit post
        # otherwise, it's the url to external content embedded into the thread
        # the same goes for reddit gallery links
        url: Union[str, None] = None if reddit_id.split("_", 1)[1] in url_attr else url_attr

        # add the missing reddit domain if missing in url from api
        if url is not None:
            if url.startswith("/r/"):
                url = f"{reddit_domain}{url}"

        # check if url is a reddit gallery
        if url:
            reddit_gallery: bool = True if re.match("^(https://v.redd.it/)\w+$", url) else False
        else:
            reddit_gallery: bool = False

        # check if the url is an image
        image = Util._check_if_image(url) if (url is not None and reddit_gallery is False) else None

        # if it is, set the url to None
        url = None if (image is not None and reddit_gallery is not False) else url

        title: str = getattr(i, "title")
        body_attr = Util._getattr_mod(i, "selftext")
        body: Union[str, None] = None if body_attr == "" else body_attr
        permalink: str = f"{reddit_domain}{Util._getattr_mod(i, 'permalink')}"
        flair: Union[str, None] = Util._getattr_mod(i, "link_flair_text")
        flair = flair.strip() if flair else None
        only_has_body = True if (body is not None and not url and not image and not is_video) else False

        ignore_map = {
            RedditThread.mirrored: is_mirrored,
            RedditThread.pinned: is_pinned,
            RedditThread.nsfw: is_nsfw,
            RedditThread.poll: is_poll,
            RedditThread.locked: is_locked,
            RedditThread.video: is_video,
            RedditThread.url: True if url else None,
            RedditThread.flair: True if flair else None,
            RedditThread.body: only_has_body,
            RedditThread.image: True if image else None,
            RedditThread.reddit_gallery: reddit_gallery,
            RedditThread.rule_1: _rule_1_check_funday_friday_flair(flair),
        }

        for t in ignore_thread_types:
            if ignore_map[t]:
                logging.info(f"Ignoring submission {i.name} with title {i.title}; {t.value} = {ignore_map[t]}")
                ignoring_post = True

        if not ignoring_post:
            # only post threads with URL that are not a video
            # due to v.redd.it embedding video and sound separately
            data = {
                "url": url,
                "image_url": image,
                "url_attr": url_attr,
                "title": title,
                "body_attr": body_attr,
                "body": body,
                "permalink": permalink,
                "reddit_id": reddit_id,
                "flair": flair,
                "is_video": is_video,
                "is_pinned": is_pinned,
                "is_nsfw": is_nsfw,
                "is_poll": is_poll,
                "is_locked": is_locked,
                "reddit_gallery": reddit_gallery,
            }
            logging.info(f"Committing submission {i.name} with title {i.title}")
            threads_to_mirror.append(data)

    return threads_to_mirror


def get_threads_from_reddit(
    reddit: praw.Reddit,
    subreddit_name: str,
    DB: TinyDB,
    limit: int = 100,
    ignore_thread_types: list[RedditThread] = [
        RedditThread.mirrored,
        RedditThread.pinned,
        RedditThread.nsfw,
        RedditThread.poll,
        RedditThread.locked,
        RedditThread.video,
        RedditThread.url,
    ],
    filter: str = "new",
) -> List[Submission]:
    if limit > 100:
        logging.info(f"Max limit of submissions to return is 100. The limit arg ({limit}) has now been set to 100.")
        limit = 100

    available_filters = ("new", "hot", "rising")
    if filter not in available_filters:
        filter = "new"
        logging.info(
            f"The selected filter '{filter}' is not available. Setting to default 'new'. Available filters: {', '.join(available_filters)}"
        )

    subreddit = reddit.subreddit(subreddit_name)
    logging.info(f"Searching subreddit r/{subreddit}")

    if filter == "new":
        listing = subreddit.new(limit=limit)
        logging.info(f"Grabbed a list of {filter} threads from Reddit")

    elif filter == "hot":
        listing = subreddit.hot(limit=limit)
        logging.info(f"Grabbed a list of {filter} threads from Reddit")

    elif filter == "rising":
        listing = subreddit.rising(limit=limit)
        logging.info(f"Grabbed a list of {filter} threads from Reddit")

    threads_to_mirror = _extract_threads_to_mirror(listing=listing, DB=DB, ignore_thread_types=ignore_thread_types)
    logging.info(f"Found {len(threads_to_mirror)} potential threads to mirror")

    return threads_to_mirror


def mirror_threads_to_lemmy(
    lemmy: Lemmy,
    threads_to_mirror: List[dict],
    community: str,
    DB: TinyDB,
    delay: int = 30,
) -> int:
    community_id = lemmy.discover_community(community)

    num_mirrored_posts = 0
    posted = False
    for thread in threads_to_mirror:
        sleep(delay)
        if not Util._check_thread_in_db(thread["reddit_id"], DB):
            # generate a bot disclaimer
            bot_body = (
                f"(This post was mirrored by a bot. [The original post can be found here]({thread['permalink']}))"
            )

            # add the bot disclaimer to the post and link to the original content
            post_body = thread["body"] + "\n\n" + bot_body if isinstance(thread["body"], str) else bot_body

            # add flair if it exists
            thread_title = f"{thread['flair']} | {thread['title']}" if thread["flair"] else thread["title"]

            # add a url or image url if they exist
            thread_url = thread["url"]
            image_url = thread["image_url"]

            # link to the url or external content
            url = thread_url if thread_url is not None else image_url

            try:
                lemmy.post.create(
                    community_id=community_id,
                    name=thread_title,
                    url=url,
                    nsfw=None,
                    body=post_body,
                    language_id=LanguageType.EN,
                )
                posted = True
            except Exception as e:
                logging.error(f"Lemmy cound not create a post for thread {thread['reddit_id']}. Exception {e}.")

            if posted:
                num_mirrored_posts += 1
                Util._insert_thread_into_db(thread, DB)
                logging.info(f"Posted thread with reddit_id {thread['reddit_id']} in {community}")

    return num_mirrored_posts
