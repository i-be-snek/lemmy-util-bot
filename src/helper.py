import datetime
import logging
from dataclasses import dataclass, field
from enum import Enum, unique
from typing import Dict, Union

import requests
from filestack import Client, Filelink, Security
from tinydb import Query, TinyDB

logging.basicConfig(
    format="%(asctime)s %(levelname)-8s %(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S",
)


@unique
class RedditThread(Enum):
    mirrored: str = "mirrored"
    pinned: str = "pinned"
    nsfw: str = "nsfw"
    poll: str = "poll"
    locked: str = "locked"
    video: str = "video"
    url: str = "url"
    flair: str = "flair"
    body: str = "body"
    image: str = "image"
    reddit_gallery: str = "reddit_gallery"


@unique
class Task(Enum):
    mirror_threads: str = "mirror_threads"
    mod_comment_on_new_threads: str = "mod_comment_on_new_threads"


@dataclass
class Config:
    config: dict
    main_configs: tuple = (
        "LEMMY_USERNAME",
        "LEMMY_PASSWORD",
        "LEMMY_INSTANCE",
        "LEMMY_COMMUNITY",
        "TASKS",
    )

    mirror_configs: tuple = (
        "THREADS_TO_IGNORE",
        "REDDIT_CLIENT_ID",
        "REDDIT_CLIENT_SECRET",
        "REDDIT_PASSWORD",
        "REDDIT_USER_AGENT",
        "REDDIT_USERNAME",
        "REDDIT_SUBREDDIT",
        "FILESTACK_API_KEY",
        "FILESTACK_APP_SECRET",
        "FILESTACK_HANDLE_REFRESH",
        "FILESTACK_HANDLE_BACKUP",
    )

    configs_with_defaults: tuple = (
        "BACKUP_FILESTACK_EVERY_MINUTE",
        "REFRESH_FILESTACK_EVERY_HOUR",
        "MIRROR_THREADS_EVERY_SECOND",
        "DELAY_BETWEEN_MIRRORED_THREADS_SECOND",
        "REDDIT_FILTER_THREAD_LIMIT",
        "FILTER_BY",
        "REDDIT_CAP_NUMBER_OF_MIRRORED_THREADS",
    )
    keys_missing: bool = False

    def __post_init__(self):
        for c in self.main_configs:
            if c not in self.config.keys():
                logging.error(f"Main variable {c} is missing")
                self.keys_missing = True

        self.TASKS: list = [
            Util._getattr_mod(Task, x)
            for x in Util._get_clean_list(self.config["TASKS"])
        ]

        if Task.mirror_threads in self.TASKS:
            for c in self.mirror_configs:
                if c not in self.mirror_configs:
                    logging.error(f"'mirror_threads' variable {c} is missing")
                    self.keys_missing = True

        if self.keys_missing:
            raise AssertionError("One or more variables are missing")

        self.LEMMY_USERNAME: str = self.config["LEMMY_USERNAME"]
        self.LEMMY_PASSWORD: str = self.config["LEMMY_PASSWORD"]
        self.LEMMY_INSTANCE: str = self.config["LEMMY_INSTANCE"]
        self.LEMMY_COMMUNITY: str = self.config["LEMMY_COMMUNITY"]

        if Task.mirror_threads in self.TASKS:
            self.REDDIT_CLIENT_ID: str = self.config["REDDIT_CLIENT_ID"]
            self.REDDIT_CLIENT_SECRET: str = self.config["REDDIT_CLIENT_SECRET"]
            self.REDDIT_PASSWORD: str = self.config["REDDIT_PASSWORD"]
            self.REDDIT_USER_AGENT: str = self.config["REDDIT_USER_AGENT"]
            self.REDDIT_USERNAME: str = self.config["REDDIT_USERNAME"]
            self.REDDIT_SUBREDDIT: str = self.config["REDDIT_SUBREDDIT"]
            self.FILESTACK_API_KEY: str = self.config["FILESTACK_API_KEY"]
            self.FILESTACK_APP_SECRET: str = self.config["FILESTACK_APP_SECRET"]
            self.FILESTACK_HANDLE_REFRESH: str = self.config["FILESTACK_HANDLE_REFRESH"]
            self.FILESTACK_HANDLE_BACKUP: str = self.config["FILESTACK_HANDLE_BACKUP"]
            self.THREADS_TO_IGNORE: list = [
                Util._getattr_mod(RedditThread, x)
                for x in Util._get_clean_list(self.config["THREADS_TO_IGNORE"])
            ]
            self.THREADS_TO_IGNORE = (
                self.THREADS_TO_IGNORE if self.THREADS_TO_IGNORE != [""] else []
            )
            self.BACKUP_FILESTACK_EVERY_HOUR: int = int(
                self.config.get("BACKUP_FILESTACK_EVERY_HOUR", 36)
            )
            self.REFRESH_FILESTACK_EVERY_MINUTE: int = int(
                self.config.get("REFRESH_FILESTACK_EVERY_MINUTE", 30)
            )
            self.MIRROR_THREADS_EVERY_SECOND: int = int(
                self.config.get("MIRROR_THREADS_EVERY_SECOND", 60)
            )
            self.DELAY_BETWEEN_MIRRORED_THREADS_SECOND: int = int(
                self.config.get("DELAY_BETWEEN_MIRRORED_THREADS_SECOND", 60)
            )
            self.REDDIT_FILTER_THREAD_LIMIT: int = int(
                self.config.get("REDDIT_FILTER_THREAD_LIMIT", 30)
            )
            self.REDDIT_CAP_NUMBER_OF_MIRRORED_THREADS: int = int(
                self.config.get("REDDIT_CAP_NUMBER_OF_MIRRORED_THREADS", 10)
            )

            self.FILTER_BY: str = self.config.get("FILTER_BY", "new")


class FileUploadError(Exception):
    pass


class FileDownloadError(Exception):
    pass


@dataclass
class DataBase:
    # filestack DataBase
    db_path: str = "data/mirrored_threads.json"

    store_params: Dict[str, str] = field(
        default_factory=lambda: {
            "access": "private",
            "upload_tags": {"backup": str(True)},
        }
    )

    @staticmethod
    def refresh_policy():
        return {
            "expiry": int(
                (datetime.datetime.now() + datetime.timedelta(minutes=15)).timestamp()
            )
        }

    def _upload_backup(
        self, app_secret: str, apikey: str, filename: str, db_path: str = None
    ):
        if db_path is None:
            db_path = self.db_path

        security = Security(self.refresh_policy(), app_secret)
        client = Client(apikey, security=security)

        file = client.upload(
            filepath=db_path,
            store_params=self.store_params | {"filename": filename},
        )

        if not (file is None):
            logging.info(
                f"Uploading file {filename} to {file.url} with handle {file.handle}."
            )
            return file
        else:
            raise FileUploadError("Upload to filestack failed.")

    def get_backup(self, app_secret: str, apikey: str, handle: str):
        security = Security(self.refresh_policy(), app_secret)
        client = Client(apikey, security=security)
        filelink = Filelink(handle=handle, security=security)
        d = filelink.download(self.db_path)
        if not (d is None):
            logging.info(
                f"Downloading backup file from {filelink.url} to {self.db_path}"
            )
        else:
            raise FileDownloadError("Pulling backup from filestack failed")

    def refresh_backup(self, app_secret: str, apikey: str, handle: str):
        security = Security(self.refresh_policy(), app_secret)
        client = Client(apikey, security=security)
        filelink = Filelink(handle=handle, security=security)
        o = filelink.overwrite(filepath=self.db_path, security=security)
        if not (o is None):
            logging.info(
                f"Storing {filelink.metadata()['filename']} backup at {filelink.url}"
            )
        else:
            raise FileUploadError(
                "Overwriting the database file from filestack failed."
            )


@dataclass
class Util:
    @staticmethod
    def _check_if_image(url: str):
        try:
            resp = requests.head(url)
            if resp.ok:
                content_type = resp.headers.get("content-type")
                if "image" in content_type:
                    return url
        except Exception as e:
            logging.error(f"Could not check image. {e}")
            return None

    @staticmethod
    def _getattr_mod(__o: object, __name: str) -> Union[str, None]:
        try:
            return getattr(__o, __name)
        except AttributeError:
            return None

    @staticmethod
    def _check_thread_in_db(reddit_id: str, DB: TinyDB) -> bool:
        q = Query()
        if DB.search(q.reddit_id == reddit_id):
            logging.info(f"Post with id {reddit_id} has already been mirrored.")
            return True
        return False

    @staticmethod
    def _insert_thread_into_db(thread: dict, DB: TinyDB) -> None:
        try:
            DB.insert(thread)
            logging.info(f"Inserted {thread['reddit_id']} into TinyDB")
        except Exception as e:
            logging.error(
                f"Could not insert {thread['reddit_id']} into TinyDB. Exception: {e}"
            )

    @staticmethod
    def _get_clean_list(text: str, sep: str = ",") -> list:
        split_list = text.split(sep)
        for i in range(len(split_list)):
            split_list[i] = split_list[i].strip()

        return split_list
