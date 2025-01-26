import os

def prompt_user_for_input(prompt):
    return input(prompt).strip()

def create_env_file():
    print("Welcome to the setup script for the Twitter to Bluesky bot.")

    twitter_username = prompt_user_for_input("Enter your Twitter account username: ")
    twitter_password = prompt_user_for_input("Enter your Twitter account password: ")
    rapidapi_key = prompt_user_for_input("Enter your RAPIDAPI key: ")
    bluesky_username = prompt_user_for_input("Enter your Bluesky handle/username: ")
    bluesky_password = prompt_user_for_input("Enter your Bluesky app-password: ")
    target_user = prompt_user_for_input("Enter the target Twitter user (without the @, ie: 'Yopro20_): ")

    env_content = f"""
TWITTER_USERNAME={twitter_username}
TWITTER_PASSWORD={twitter_password}
RAPIDAPI_KEY={rapidapi_key}
BLUESKY_USERNAME={bluesky_username}
BLUESKY_PASSWORD={bluesky_password}
TARGET_USER={target_user}
"""

    with open('.env', 'w') as env_file:
        env_file.write(env_content.strip())

    print("Environment setup complete. Configuration saved to .env file.")

if __name__ == "__main__":
    create_env_file()
