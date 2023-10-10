import logging
from dataclasses import dataclass

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
