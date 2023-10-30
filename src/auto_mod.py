import logging
from dataclasses import dataclass
from typing import List

from pythorhead.types import LanguageType, SortType

logging.basicConfig(
    format="%(asctime)s %(levelname)-8s %(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S",
)


@dataclass
class LemmyThread:
    deleted: bool
    removed: bool
    locked: bool
    post_id: int
    bot_account: bool
    saved: bool
    by_automod: bool


class AutoMod:
    def __init__(self, lemmy, community, lemmy_username):
        self.auto_mod = lemmy
        self.community_id = lemmy.discover_community(community)
        self.auto_mod_name = lemmy_username

    def _comment_as_mod(
        self,
        post_id: int,
        content: str,
    ) -> int:
        print(content)
        print(type(content))
        comment = self.auto_mod.comment.create(
            post_id=post_id, content=content, language_id=LanguageType.EN
        )
        comment_id = comment["comment_view"]["comment"]["id"]
        distinguish = self.auto_mod.comment.distinguish(
            comment_id=comment_id, distinguished=True
        )

        return comment_id

    def _find_new_threads(self) -> List[LemmyThread]:
        new_threads = self.auto_mod.post.list(
            community_id=self.community_id, sort=SortType.New, limit=50
        )

        output = []

        for i in new_threads:
            # automod saves posts it already commented on
            if i["saved"] is False:
                output.append(
                    LemmyThread(
                        i["post"]["deleted"],
                        i["post"]["removed"],
                        i["post"]["locked"],
                        i["post"]["id"],
                        i["creator"]["bot_account"],
                        i["saved"],
                        True if i["creator"]["name"] == self.auto_mod_name else False,
                    )
                )
        logging.info(f"Found {len(output)} threads to add auto mod comment to.")
        return output

    def comment_on_new_threads(self, mod_message: str = None):
        new_threads: dict = self._find_new_threads()
        if mod_message is None:
            mod_message = open("src/mod_comment_new_threads.md", "r").read()

        for thread in new_threads:
            if not thread.deleted and not thread.removed and not thread.by_automod:
                # add mod comment
                comment = self._comment_as_mod(
                    post_id=thread.post_id, content=mod_message
                )
                logging.info(comment)
                # save thread
                self.auto_mod.post.save(post_id=thread.post_id, saved=True)
