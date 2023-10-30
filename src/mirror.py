import logging
from time import sleep
from typing import List, Union

import praw
import pytest
import requests
from praw.models import ListingGenerator
from praw.reddit import Submission
from pythorhead import Lemmy
from pythorhead.types import LanguageType
from tinydb import Query, TinyDB

from src.helper import Thread, Util

logging.basicConfig(
    format="%(asctime)s %(levelname)-8s %(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S",
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
        url: Union[str, None] = (
            None if reddit_id.split("_", 1)[1] in url_attr else url_attr
        )

        # check if the url is an image
        image = Util._check_if_image(url) if url else None

        # if it is, set the url to None
        url = None if image is not None else url

        title: str = getattr(i, "title")
        body_attr = Util._getattr_mod(i, "selftext")
        body: Union[str, None] = None if body_attr == "" else body_attr
        permalink: str = f"https://www.reddit.com{Util._getattr_mod(i, 'permalink')}"
        flair: Union[str, None] = Util._getattr_mod(i, "link_flair_text")
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
            Thread.image: True if image else None,
        }

        for t in ignore:
            if ignore_map[t]:
                logging.info(
                    f"Ignoring submission {i.name} with title {i.title}; {t.value} = {ignore_map[t]}"
                )
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
            }
            logging.info(f"Committing submission {i.name} with title {i.title}")
            threads_to_mirror.append(data)

    return threads_to_mirror


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
        if not Util._check_thread_in_db(thread["reddit_id"], DB):
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

            # add a url or image url if they exist
            thread_url = thread["url"]
            image_url = thread["image_url"]

            # link to the url or external content
            url = thread_url if not None else image_url

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
                logging.error(
                    f"Lemmy cound not create a post for thread {thread['reddit_id']}. Exception {e}."
                )

            if posted:
                num_mirrored_posts += 1
                Util._insert_thread_into_db(thread, DB)
                logging.info(
                    f"Posted thread with reddit_id {thread['reddit_id']} in {community}"
                )

    return num_mirrored_posts
