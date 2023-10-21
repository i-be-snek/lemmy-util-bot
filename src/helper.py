import datetime
import logging
from dataclasses import dataclass, field
from typing import Dict, Union

from filestack import Client, Filelink, Security
from requests import get, patch

logging.basicConfig(
    format="%(asctime)s %(levelname)-8s %(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S",
)


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
        "FILESTACK_HANDLE",
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
            self.FILETSACK_HANDLE: str = self.config["FILESTACK_HANDLE"]


class FileUploadError(Exception):
    pass


class FileDownloadError(Exception):
    pass


@dataclass
class DataBase:
    db_path: str = "data/mirrored_threads.json"

    store_params: Dict[str, str] = field(
        default_factory=lambda: {
            "filename": "mirrored_threads.json",
            "access": "private",
            "upload_tags": {"backup": str(True)},
        }
    )

    store_params_solid_backup: Dict[str, str] = field(
        default_factory=lambda: {
            "access": "private",
            "upload_tags": {"backup": str(True)},
        }
    )

    solid_copies = []

    @staticmethod
    def refresh_policy():
        return {
            "expiry": int(
                (datetime.datetime.now() + datetime.timedelta(minutes=15)).timestamp()
            )
        }

    def _upload_backup(self, app_secret: str, token: str, solid_copy=False):
        security = Security(self.refresh_policy(), app_secret)
        client = Client(token, security=security)
        if not solid_copy:
            file = client.upload(filepath=self.db_path, store_params=self.store_params)
        elif solid_copy:
            file = client.upload(
                filepath=self.db_path,
                store_params=self.store_params_solid_backup
                | {
                    "filename": f"mirrored_threads_{datetime.datetime.now().isoformat()}.json"
                },
            )

        if not (file is None):
            logging.info(
                f"Uploading file to {file.url} with handle {file.handle}. Solid copy? {solid_copy}"
            )
            if solid_copy:
                self.solid_copies.append(file)
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
            logging.info(f"Storing refreshed backup at {filelink.url}")
        else:
            raise FileUploadError(
                "Overwriting the database file from filestack failed."
            )

    def delete_old_solid_copies(self, app_secret: str, max: int = 10):
        security = Security(self.refresh_policy(), app_secret)
        logging.info("Checking solid compies to erase old ones...")
        print(self.solid_copies)
        if len(self.solid_copies) > max:
            for c in range(0, len(self.solid_copies) - max):
                self.solid_copies[c].delete(security=security)
                logging.info(
                    f"Erased {self.solid_copies[c].handle} from filestack server."
                )
        else:
            logging.info(f"Number of solid copies is still under {max}.")
