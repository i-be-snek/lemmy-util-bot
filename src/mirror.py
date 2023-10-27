import logging
from time import sleep
from typing import List, Union
from unittest import mock

import praw
import pytest
from praw.models import ListingGenerator
from praw.reddit import Submission
from pythorhead import Lemmy
from pythorhead.types import LanguageType
from tinydb import Query, TinyDB

from src.helper import Thread

logging.basicConfig(
    format="%(asctime)s %(levelname)-8s %(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S",
)


def _check_thread_in_db(reddit_id: str, DB: TinyDB) -> bool:
    q = Query()
    if DB.search(q.reddit_id == reddit_id):
        logging.info(f"Post with id {reddit_id} has already been mirrored.")
        return True
    return False


def _insert_thread_into_db(thread: dict, DB: TinyDB) -> None:
    try:
        DB.insert(thread)
        logging.info(f"Inserted {thread['reddit_id']} into TinyDB")
    except Exception as e:
        logging.error(
            f"Could not insert {thread['reddit_id']} into TinyDB. Exception: {e}"
        )


def _extract_threads_to_mirror(
    listing: ListingGenerator,
    DB: TinyDB,
    ignore: list[Thread] = [
        Thread.mirrored,
        Thread.pinned,
        Thread.nsfw,
        Thread.poll,
        Thread.locked,
        Thread.video,
        Thread.url,
    ],
) -> List[dict]:
    logging.info(f"Ignoring: {', '.join([_.value for _ in ignore])}")

    threads_to_mirror = []

    for i in listing:
        ignoring_post = False

        reddit_id: str = _getattr_mod(i, "name")

        logging.info(f"Checking post {reddit_id}...")

        is_mirrored = True if _check_thread_in_db(reddit_id, DB) else False
        is_pinned: bool = False if _getattr_mod(i, "sitckied") == None else True
        is_nsfw: bool = _getattr_mod(i, "over_18")
        is_poll: bool = True if _getattr_mod(i, "poll_data") else False
        is_locked: bool = _getattr_mod(i, "locked")
        is_video: bool = _getattr_mod(i, "is_video")
        # if the reddit_id is in the url, it's the url to the reddit post
        # otherwise, it's the url to external content embedded into the thread
        # the same goes for reddit gallery links
        url_attr = _getattr_mod(i, "url")
        url: Union[str, None] = (
            None if reddit_id.split("_", 1)[1] in url_attr else url_attr
        )
        title: str = getattr(i, "title")
        body_attr = _getattr_mod(i, "selftext")
        body: Union[str, None] = None if body_attr == "" else body_attr
        permalink: str = f"https://www.reddit.com{_getattr_mod(i, 'permalink')}"
        flair: Union[str, None] = _getattr_mod(i, "link_flair_text")
        flair = flair.strip() if flair else None

        ignore_map = {
            Thread.mirrored: is_mirrored,
            Thread.pinned: is_pinned,
            Thread.nsfw: is_nsfw,
            Thread.poll: is_poll,
            Thread.locked: is_locked,
            Thread.video: is_video,
            Thread.url: url,
            Thread.flair: flair,
            Thread.body: body,
        }

        for t in ignore:
            print(t)
            if ignore_map[t]:
                logging.info(
                    f"Ignoring submission {i.name} with title {i.title}; {t.value} == {ignore_map[t]}"
                )
                ignoring_post = True

        if not ignoring_post:
            # only post threads with URL that are not a video
            # due to v.redd.it embedding video and sound separately
            data = {
                "url": url,
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
            }
            logging.info(f"Committing submission {i.name} with title {i.title}")
            threads_to_mirror.append(data)

    return threads_to_mirror


def _getattr_mod(__o: object, __name: str) -> Union[str, None]:
    try:
        return getattr(__o, __name)
    except AttributeError:
        return None


def get_threads_from_reddit(
    reddit: praw.Reddit,
    subreddit_name: str,
    DB: TinyDB,
    limit: int = 100,
    ignore: list[Thread] = [
        Thread.mirrored,
        Thread.pinned,
        Thread.nsfw,
        Thread.poll,
        Thread.locked,
        Thread.video,
        Thread.url,
    ],
) -> List[Submission]:
    if limit > 100:
        logging.info(
            f"Max limit of submissions to return is 100. The limit arg ({limit}) has now been set to 100."
        )
        limit = 100

    subreddit = reddit.subreddit(subreddit_name)
    logging.info(f"Searching subreddit r/{subreddit}")

    listing = subreddit.new(limit=limit)
    logging.info(f"Grabbed a list of threads from Reddit")

    threads_to_mirror = _extract_threads_to_mirror(
        listing=listing, DB=DB, ignore=ignore
    )
    logging.info(f"Found {len(threads_to_mirror)} threads to mirror")

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
        if not _check_thread_in_db(thread["reddit_id"], DB):
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

            # only mirror posts with links
            thread_url = thread["url"]

            try:
                lemmy.post.create(
                    community_id=community_id,
                    name=thread_title,
                    url=thread_url,
                    nsfw=None,
                    body=post_body,
                    language_id=LanguageType.EN,
                )
                posted = True
            except Exception as e:
                logging.error(
                    f"Lemmy cound not create a post for thread {thread['reddit_id']}. Exception {e}."
                )

            if posted:
                num_mirrored_posts += 1
                _insert_thread_into_db(thread, DB)
                logging.info(
                    f"Posted thread with reddit_id {thread['reddit_id']} in {community}"
                )

    return num_mirrored_posts
