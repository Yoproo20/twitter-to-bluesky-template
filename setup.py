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
    print("Welcome to the setup script for the Twitter to Bluesky bot. \n Please read the README before setting up.")

    twitter_username = prompt_user_for_input("Enter your Twitter account username: ")
    twitter_password = prompt_user_for_input("Enter your Twitter account password: ")
    rapidapi_key = prompt_user_for_input("Enter your RAPIDAPI key: ")
    bluesky_username = prompt_user_for_input("Enter your Bluesky handle/username (ie: user.bsky.social): ")
    bluesky_password = prompt_user_for_input("Enter your Bluesky app-password: ")
    target_user = prompt_user_for_input("Enter the target Twitter user (without the @, ie: 'Yopro20_): ")
    check_interval = prompt_for_integer("Enter the interval (in seconds) to check for new posts: ")

    enable_translation_input = prompt_user_for_input("Do you want to enable translation? (yes/no): ").lower()
    enable_translation = str(enable_translation_input in ['yes', 'y', 'true', '1'])

    translation_from = ""
    translation_to = ""
    translator_rapidapi_key = ""

    if enable_translation == "True":
        print("For language codes, please refer to: https://gist.github.com/Yoproo20/9c860565a61c589edf578112d1964277")
        translation_from = prompt_user_for_input("Enter the source language code (e.g., 'es'): ")
        translation_to = prompt_user_for_input("Enter the target language code (e.g., 'en'): ")
        translator_rapidapi_key = prompt_user_for_input("Enter your RAPIDAPI key for translation: ")

    env_content = f"""
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
"""

    with open('.env', 'w') as env_file:
        env_file.write(env_content.strip())

    print("Environment setup complete. Configuration saved to .env file.")

if __name__ == "__main__":
    create_env_file()
