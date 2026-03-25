import os


def prompt_user_for_input(prompt):
    return input(prompt).strip()


def prompt_for_integer(prompt):
    while True:
        try:
            value = int(prompt_user_for_input(prompt))
            return value
        except ValueError:
            print("[ERROR] Please enter a valid integer.")


def create_env_file():
    print(
        "Welcome to the setup script for the Twitter to Bluesky bot. \n Please read the README before setting up."
    )

    print("\n--- Twitter Login (choose one method) ---")
    print("Primary: Use cookies from your browser (bypasses Cloudflare blocks). ")
    print("Secondary: Username/password (may be blocked by Cloudflare)")
    use_cookies_input = prompt_user_for_input("Use cookie-based login? (yes/no) [recommended: yes]: ").lower()
    use_cookies = use_cookies_input in ["", "yes", "y", "true", "1"]

    twitter_auth_token = ""
    twitter_ct0 = ""
    twitter_guest_id = ""
    twitter_twid = ""
    twitter_username = ""
    twitter_password = ""

    if use_cookies:
        print("\nEnter cookie values from x.com (leave blank to skip):")
        twitter_auth_token = prompt_user_for_input("auth_token: ")
        twitter_ct0 = prompt_user_for_input("ct0: ")
        twitter_guest_id = prompt_user_for_input("guest_id: ")
        twitter_twid = prompt_user_for_input("twid: ")
        if not twitter_auth_token:
            print("[INFO] auth_token is required for cookie login. Falling back to username/password.")
            use_cookies = False

    if not use_cookies or not twitter_auth_token:
        twitter_username = prompt_user_for_input("Enter your Twitter account username: ")
        twitter_password = prompt_user_for_input("Enter your Twitter account password: ")
    rapidapi_key = prompt_user_for_input("Enter your RAPIDAPI key: ")
    bluesky_username = prompt_user_for_input("Enter your Bluesky handle/username (ie: user.bsky.social): ")
    bluesky_password = prompt_user_for_input("Enter your Bluesky app-password: ")
    target_user = prompt_user_for_input("Enter the target Twitter user (without the @, ie: 'Yopro20_): ")
    check_interval = prompt_for_integer("Enter the interval (in seconds) to check for new posts: ")

    enable_translation_input = prompt_user_for_input("Do you want to enable translation? (yes/no): ").lower()
    enable_translation = str(enable_translation_input in ["yes", "y", "true", "1"])

    translation_from = ""
    translation_to = ""
    translator_rapidapi_key = ""

    if enable_translation == "True":
        print("For language codes, please refer to: https://gist.github.com/Yoproo20/9c860565a61c589edf578112d1964277")
        translation_from = prompt_user_for_input("Enter the source language code (e.g., 'es'): ")
        translation_to = prompt_user_for_input("Enter the target language code (e.g., 'en'): ")
        translator_rapidapi_key = prompt_user_for_input("Enter your RAPIDAPI key for translation: ")

    print("\n--- Auto-Update Configuration ---")
    print("Auto-update allows the bot to automatically check for and install updates.")
    auto_update_input = prompt_user_for_input("Do you want to enable auto-updates? (yes/no) [default: yes]: ").lower()
    if auto_update_input in ["", "yes", "y", "true", "1"]:
        auto_update = "true"
    else:
        auto_update = "false"

    update_check_interval_input = prompt_user_for_input("Enter the update check interval in seconds [default: 86400 (24 hours)]: ").strip()
    if update_check_interval_input == "":
        update_check_interval = "86400"
    else:
        try:
            update_check_interval = str(int(update_check_interval_input))
        except ValueError:
            print("[INFO] Invalid input, using default value of 86400 seconds.")
            update_check_interval = "86400"

    env_content = f"""
TWITTER_AUTH_TOKEN={twitter_auth_token}
TWITTER_CT0={twitter_ct0}
TWITTER_GUEST_ID={twitter_guest_id}
TWITTER_TWID={twitter_twid}
TWITTER_USERNAME={twitter_username}
TWITTER_PASSWORD={twitter_password}
RAPIDAPI_KEY={rapidapi_key}
BLUESKY_USERNAME={bluesky_username}
BLUESKY_PASSWORD={bluesky_password}
TARGET_USER={target_user}
CHECK_INTERVAL={check_interval}
ENABLE_TRANSLATION={enable_translation}
TRANSLATION_FROM={translation_from}
TRANSLATION_TO={translation_to}
TRANSLATOR_RAPIDAPI_KEY={translator_rapidapi_key}
AUTO_UPDATE={auto_update}
UPDATE_CHECK_INTERVAL={update_check_interval}
"""

    with open(".env", "w") as env_file:
        env_file.write(env_content.strip())

    print(".env setup complete. Configuration saved to .env file.")


if __name__ == "__main__":
    create_env_file()
