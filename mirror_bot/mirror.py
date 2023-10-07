import logging
from typing import List, Union

import praw
from praw.reddit import Submission
from pythorhead import Lemmy
from pythorhead.types import LanguageType
from tinydb import Query, TinyDB

logging.basicConfig(
format='%(asctime)s %(levelname)-8s %(message)s',
level=logging.INFO,
datefmt='%Y-%m-%d %H:%M:%S')

# TODO: is this okay as a global var?
DB = TinyDB("db.json")

def _check_thread_in_db(reddit_id: str) -> bool:
    q = Query()
    if DB.search(q.reddit_id == reddit_id):
        logging.info(f"Post with id {reddit_id} has already been mirrored.")
        return True
    return False


def _insert_thread_into_db(thread: dict) -> None:
    try:
        DB.insert(thread)
        logging.info(f"Inserted {thread['reddit_id']} into TinyDB")
    except Exception as e:
        logging.error(f"Could not insert {thread['reddit_id']} into TinyDB. Exception: {e}")


def _extract_threads_to_mirror(listing: List[Submission]) -> List[dict]:
    threads_to_mirror = []

    for i in listing:
        print(i.title)
        reddit_id: str = _getattr_mod(i, "name")
        is_mirrored = True if _check_thread_in_db(reddit_id) else False
        is_pinned: bool = False if _getattr_mod(i, "sitckied") == None else True
        is_nsfw: bool = _getattr_mod(i, "over_18")
        is_poll: bool = True if _getattr_mod(i, "poll_data") else False
        is_locked: bool = _getattr_mod(i, "locked")

        logging.info(f"Checking post {reddit_id}...")
        
        if is_pinned or is_nsfw or is_poll or is_locked or is_mirrored:
            logging.info(
                f"""Ignoring submission {i.name} with title {i.title}; is_pinned: {is_pinned};\n
                is_nsfw: {is_nsfw}; is_poll: {is_poll}; is_locked: {is_locked}; is_mirrored --> {is_mirrored}
            """.replace(
                    "\n", " "
                )
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


def get_threads_from_reddit(reddit: praw.Reddit, subreddit_name: str, limit: int = 100) -> List[Submission]:
    if limit > 100:
        logging.info(
            f"Max limit of submissions to return is 100. The limit arg ({limit}) has now been set to 100."
        )
        limit = 100

    subreddit = reddit.subreddit(subreddit_name)
    logging.info(f"Searching subreddit r/{subreddit}")

    listing = subreddit.new(limit=limit)
    logging.info(f"Grabbed a list of threads from Reddit")

    threads_to_mirror = _extract_threads_to_mirror(listing=listing)
    logging.info(f"Found {len(threads_to_mirror)} threads to mirror")

    return threads_to_mirror


def mirror_threads_to_lemmy(lemmy: Lemmy, threads_to_mirror: dict, community: str) -> None:
    community_id = lemmy.discover_community(community)

    for thread in threads_to_mirror:
        if not _check_thread_in_db(thread["reddit_id"]):
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
                logging.info(f"Posted thread with reddit_id {thread['reddit_id']} in {community}")
                
                _insert_thread_into_db(thread)

            except Exception as e:
                logging.error(
                    f"Lemmy cound not create a post for thread {thread['reddit_id']}. Exception {e}."
                )
