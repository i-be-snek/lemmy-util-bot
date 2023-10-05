from mirror_bot import mirror

if __name__ == "__main__":
    threads = mirror.get_reddit_threads(10)
    mirror.to_lemmy(threads)
