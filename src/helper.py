import datetime
import logging
from dataclasses import dataclass, field
from enum import Enum, unique
from typing import Dict, Union

from filestack import Client, Filelink, Security
from requests import get, patch

logging.basicConfig(
    format="%(asctime)s %(levelname)-8s %(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S",
)


@unique
class Thread(Enum):
    mirrored: str = "mirrored"
    pinned: str = "pinned"
    nsfw: str = "nsfw"
    poll: str = "poll"
    locked: str = "locked"
    video: str = "video"
    url: str = "url"
    flair: str = ("flair",)
    body: str = "body"


@dataclass
class Config:
    config: dict
    vital_configs: tuple = (
        "LEMMY_USERNAME",
        "LEMMY_PASSWORD",
        "LEMMY_INSTANCE",
        "LEMMY_COMMUNITY",
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
    keys_missing: bool = False

    def __post_init__(self):
        for c in self.vital_configs:
            if c not in self.config.keys():
                logging.error(f"Variable {c} is missing")
                self.keys_missing = True

        if self.keys_missing:
            raise AssertionError("One or more variables are missing")
        else:
            self.LEMMY_USERNAME: str = self.config["LEMMY_USERNAME"]
            self.LEMMY_PASSWORD: str = self.config["LEMMY_PASSWORD"]
            self.LEMMY_INSTANCE: str = self.config["LEMMY_INSTANCE"]
            self.LEMMY_COMMUNITY: str = self.config["LEMMY_COMMUNITY"]
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


class FileUploadError(Exception):
    pass


class FileDownloadError(Exception):
    pass


@dataclass
class DataBase:
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

    def _upload_backup(self, app_secret: str, token: str, filename: str):
        security = Security(self.refresh_policy(), app_secret)
        client = Client(token, security=security)

        file = client.upload(
            filepath=self.db_path,
            store_params=self.store_params | {"filename": filename},
        )

        if not (file is None):
            logging.info(
                f"Uploading file {filename} to {file.url} with handle {file.handle}."
            )
        else:
            raise FileUploadError("Upload to filestack failed.")

    def get_backup(self, app_secret: str, token: str, handle: str):
        security = Security(self.refresh_policy(), app_secret)
        client = Client(token, security=security)
        filelink = Filelink(handle=handle, security=security)
        d = filelink.download(self.db_path)
        if not (d is None):
            logging.info(
                f"Downloading backup file from {filelink.url} to {self.db_path}"
            )
        else:
            raise FileDownloadError("Pulling backup from filestack failed")

    def refresh_backup(self, app_secret: str, token: str, handle: str):
        security = Security(self.refresh_policy(), app_secret)
        client = Client(token, security=security)
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
