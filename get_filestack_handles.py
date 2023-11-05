from src.helper import DataBase

def get_handles():
    apikey = input("Enter Filestack API Key: ").strip()
    app_secret = input("Enter Filestack App Secret: ").strip()

    db_path = "data/db.json"

    backup_filename = "mirrored_threads_backup.json"
    refresh_filename = "mirrored_threads_refresh.json"
    db = DataBase()

    try:
        refresh_file = db._upload_backup(
            app_secret=app_secret,
            apikey=apikey,
            filename=refresh_filename,
            db_path=db_path,
        )
        backup_file = db._upload_backup(
            app_secret=app_secret,
            apikey=apikey,
            filename=backup_filename,
            db_path=db_path,
        )
        print("\n\n")
        print("Add these variables to the .env file")
        print(f'FILESTACK_HANDLE_REFRESH="{refresh_file.handle}"')
        print(f'FILESTACK_HANDLE_BACKUP="{backup_file.handle}"')

    except Exception as e:
        print("Could not create files, check your API Key and App Secret.")
        print(f"Exception: {e}")


if __name__ == "__main__":
    get_handles()
