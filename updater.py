import logging
import os
import sys
import requests

DATA_DIR = os.getenv("DATA_DIR", ".")
VERSION_FILE = os.path.join(DATA_DIR, "version.txt")

GITHUB_REPO = "Yoproo20/twitter-to-bluesky-template"


def get_latest_commit_sha() -> str | None:
    try:
        url = f"https://api.github.com/repos/{GITHUB_REPO}/commits/main"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            sha = data.get("sha")
            logging.info(f"Latest commit SHA: {sha}")
            return sha
        else:
            logging.warning(f"Failed to get latest commit: HTTP {response.status_code}")
            return None
    except requests.exceptions.Timeout:
        logging.error("Timeout while fetching latest commit SHA")
        return None
    except requests.exceptions.RequestException as e:
        logging.error(f"Network error while fetching latest commit SHA: {e}")
        return None
    except Exception as e:
        logging.error(f"Unexpected error while fetching latest commit SHA: {e}")
        return None


def get_current_version() -> str | None:
    try:
        with open("version.txt", "r") as f:
            sha = f.read().strip()
            logging.info(f"Current version: {sha}")
            return sha
    except FileNotFoundError:
        logging.info("version.txt not found, no current version recorded")
        return None
    except Exception as e:
        logging.error(f"Error reading version.txt: {e}")
        return None


def save_current_version(sha: str):
    try:
        with open(VERSION_FILE, "w") as f:
            f.write(sha)
        logging.info(f"Saved current version: {sha}")
    except Exception as e:
        logging.error(f"Error saving version.txt: {e}")


def download_file(file_path: str, sha: str) -> bytes | None:
    try:
        url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/{sha}/{file_path}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            logging.info(f"Downloaded file: {file_path}")
            return response.content
        else:
            logging.warning(
                f"Failed to download {file_path}: HTTP {response.status_code}"
            )
            return None
    except requests.exceptions.Timeout:
        logging.error(f"Timeout while downloading {file_path}")
        return None
    except requests.exceptions.RequestException as e:
        logging.error(f"Network error while downloading {file_path}: {e}")
        return None
    except Exception as e:
        logging.error(f"Unexpected error while downloading {file_path}: {e}")
        return None


def get_changed_files(sha: str) -> list[str]:
    current_sha = get_current_version()
    if not current_sha:
        logging.warning("No current version found, cannot determine changed files")
        return []

    try:
        url = (
            f"https://api.github.com/repos/{GITHUB_REPO}/compare/{current_sha}...{sha}"
        )
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            files = data.get("files", [])
            changed_files = []
            for file_info in files:
                file_path = file_info.get("filename", "")
                if file_path.endswith(".py") and "/" not in file_path:
                    changed_files.append(file_path)
            logging.info(f"Changed Python files in root: {changed_files}")
            return changed_files
        else:
            logging.warning(f"Failed to get changed files: HTTP {response.status_code}")
            return []
    except requests.exceptions.Timeout:
        logging.error("Timeout while fetching changed files")
        return []
    except requests.exceptions.RequestException as e:
        logging.error(f"Network error while fetching changed files: {e}")
        return []
    except Exception as e:
        logging.error(f"Unexpected error while fetching changed files: {e}")
        return []


def apply_update(files: list[str], sha: str) -> bool:
    if not files:
        logging.warning("No files to update")
        return False

    for file_path in files:
        content = download_file(file_path, sha)
        if content is None:
            logging.error(f"Failed to download {file_path}, aborting update")
            return False

        try:
            with open(file_path, "wb") as f:
                f.write(content)
            logging.info(f"Updated file: {file_path}")
            print(f"[SUCCESS] Updated {file_path}")
        except Exception as e:
            logging.error(f"Failed to write {file_path}: {e}")
            return False

    save_current_version(sha)
    logging.info(f"Update applied successfully, new version: {sha}")
    return True


def check_for_update() -> tuple[bool, str | None]:
    latest_sha = get_latest_commit_sha()
    if not latest_sha:
        logging.warning("Could not retrieve latest commit SHA")
        return (False, None)

    current_sha = get_current_version()
    if not current_sha:
        logging.info("No current version found, update available")
        return (True, latest_sha)

    if latest_sha != current_sha:
        logging.info(f"Update available: {current_sha} -> {latest_sha}")
        return (True, latest_sha)

    logging.info("Already up to date")
    return (False, None)


def restart_script():
    logging.info("Restarting script...")
    os.execv(sys.executable, [sys.executable] + sys.argv)


def perform_update() -> bool:
    logging.info("Checking for updates...")
    has_update, new_sha = check_for_update()

    if not has_update:
        logging.info("No update available")
        return False

    if not new_sha:
        logging.error("Update check failed")
        print("[ERROR] Update check failed.")
        return False

    logging.info(f"Update found: {new_sha}")
    print(f"[INFO] Update found: {new_sha[:8]}...")
    changed_files = get_changed_files(new_sha)

    if not changed_files:
        logging.warning("No Python files to update")
        print("[INFO] No Python files to update.")
        save_current_version(new_sha)
        return False

    print(f"[PROCESS] Applying update ({len(changed_files)} file(s))...")
    if apply_update(changed_files, new_sha):
        logging.info("Update applied successfully, restarting...")
        print("[SUCCESS] Update applied successfully. Restarting...")
        restart_script()
        return True
    else:
        logging.error("Failed to apply update, continuing with current version")
        print("[ERROR] Failed to apply update, continuing with current version.")
        return False
