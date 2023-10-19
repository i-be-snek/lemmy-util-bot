from collections import OrderedDict

config_missing_keys = OrderedDict(
    {
        "LEMMY_USERNAME": "MagnificentPotato",
        "LEMMY_INSTANCE": "lemmy.test",
        "REDDIT_CLIENT_ID": "Fsh7AEAbXkpmiK0aseA93bjd7",
        "REDDIT_CLIENT_SECRET": "YfT586Ew9w8462SdvSSHh6G4dN07A",
        "REDDIT_USER_AGENT": "pytest u/MagnificentPotatoe",
        "REDDIT_USERNAME": "BurntSublime31",
        "REDDIT_SUBREDDIT": "all",
    }
)

config = OrderedDict(
    {
        "LEMMY_USERNAME": "MagnificentPotato",
        "LEMMY_PASSWORD": "test_password",
        "LEMMY_INSTANCE": "lemmy.test",
        "LEMMY_COMMUNITY": "bot_test",
        "REDDIT_CLIENT_ID": "Fsh7AEAbXkpmiK0aseA93bjd7",
        "REDDIT_CLIENT_SECRET": "YfT586Ew9w8462SdvSSHh6G4dN07A",
        "REDDIT_USER_AGENT": "pytest u/MagnificentPotatoe",
        "REDDIT_USERNAME": "BurntSublime31",
        "REDDIT_PASSWORD": "test_password",
        "REDDIT_SUBREDDIT": "all",
    }
)

thread = {
    "url": "https://example.com/some_page",
    "url_attr": "https://example.com/some_page",
    "title": "Example title",
    "body": "Example body",
    "permalink": "https://www.reddit.com/r/example/example_thread",
    "reddit_id": "test_150jhtj",
    "flair": None,
    "is_video": False,
    "is_pinned": False,
    "is_nswf": False,
    "is_poll": False,
    "is_locked": False,
}

thread_no_url = {
    "url": None,
    "url_attr": None,
    "title": "Example title",
    "body": "Example body",
    "permalink": "https://www.reddit.com/r/example/example_thread",
    "reddit_id": "test_150jhtj",
    "flair": None,
    "is_video": False,
    "is_pinned": False,
    "is_nswf": False,
    "is_poll": False,
    "is_locked": False,
}

test_db_path = "tests/test_db.json"
