import asyncio
import os
import requests
import time
import re
import logging
from datetime import datetime, timezone
from tweety import TwitterAsync
from dotenv import load_dotenv
from atproto import Client, SessionEvent, Session, client_utils
from atproto_client.models.app.bsky.video.upload_video import Data

# Set up logging
logging.basicConfig(
    filename='events.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Load environment variables
load_dotenv()

def get_session() -> str:
    try:
        with open('session.txt') as f:
            return f.read()
    except FileNotFoundError:
        return None

def save_session(session_string: str) -> None:
    with open('session.txt', 'w') as f:
        f.write(session_string)

def on_session_change(event: SessionEvent, session: Session) -> None:
    logging.info('Session changed: %s %s', event, repr(session))
    if event in (SessionEvent.CREATE, SessionEvent.REFRESH):
        logging.info('Saving changed session')
        save_session(session.export())

def init_bluesky_client() -> Client:
    client = Client()
    client.on_session_change(on_session_change)

    session_string = get_session()
    if session_string:
        print('[PROCESS] Reusing session')
        logging.info('Reusing session')
        client.login(session_string=session_string)
    else:
        print('[PROCESS] Creating new session')
        logging.info('Creating new session')
        bluesky_username = os.getenv("BLUESKY_USERNAME")
        bluesky_password = os.getenv("BLUESKY_PASSWORD")
        client.login(bluesky_username, bluesky_password)

    return client

def clean_tweet_text(text: str) -> str:
    # Remove 'https://t.co' and the next 10 characters
    text = re.sub(r'https://t\.co.{10}', '', text)
    # Replace 'RT ' at the beginning with ''
    text = re.sub(r'^RT ', ' ', text)
    return text

def build_post_text(tweet_text: str) -> dict:
    builder = client_utils.TextBuilder().text(tweet_text)
    
    post_text = builder.build_text()
    post_facets = builder.build_facets()
    
    return {
        "text": post_text,
        "facets": post_facets
    }

async def main():
    app = TwitterAsync("session")
    username = os.getenv("TWITTER_USERNAME")
    password = os.getenv("TWITTER_PASSWORD")
    api_key = os.getenv("RAPIDAPI_KEY")
    target_username = os.getenv("TARGET_USER")
    print("[INFO] Target username:", target_username)
    logging.info("Target username: %s", target_username)

    if not target_username:
        print("[ERROR] TARGET_USER is not set in the environment variables.")
        logging.error("Error: TARGET_USER is not set in the environment variables.")
        return

    # Sign in to Twitter
    print("[PROCESS] Signing in to Twitter...")
    logging.info("Signing in to Twitter...")
    await app.sign_in(username, password)

    # Initialize BlueSky client
    print("[PROCESS] Initializing BlueSky client...")
    logging.info("Initializing BlueSky client...")
    bluesky_client = init_bluesky_client()

    last_tweet_id = None
    check_interval = int(os.getenv("CHECK_INTERVAL", 300))  # Default to 300 seconds if not set

    while True:
        print("[PROCESS] Checking for new tweets...")
        logging.info("Checking for new tweets...")
        user = await app.get_user_info(target_username)
        if not user:
            print(f"[ERROR] Could not retrieve user info for '{target_username}'.")
            logging.error("Error: Could not retrieve user info for '%s'.", target_username)
            time.sleep(300)
            continue

        all_tweets = await app.get_tweets(user)
        if all_tweets is None:
            print(f"[ERROR] Could not retrieve tweets for '{target_username}'.")
            logging.error("Error: Could not retrieve tweets for '%s'.", target_username)
            time.sleep(300)
            continue

        if all_tweets:
            latest_tweet = all_tweets[0]
            tweet_id = latest_tweet.id
            print(f"[INFO] Latest Tweet ID: {tweet_id}")
            logging.info("Latest Tweet ID: %s", tweet_id)

            if tweet_id != last_tweet_id:
                last_tweet_id = tweet_id
                print(f"[SUCCESS] New Tweet ID: {tweet_id}")
                logging.info("New Tweet ID: %s", tweet_id)

                # Construct the URL for the API request
                url = "https://twitter-video-and-image-downloader.p.rapidapi.com/twitter"
                querystring = {"url": f"https://x.com/{target_username}/status/{tweet_id}"}
                headers = {
                    "x-rapidapi-key": api_key,
                    "x-rapidapi-host": "twitter-video-and-image-downloader.p.rapidapi.com"
                }

                # Send request to the API
                print("[PROCESS] Sending request to the API...")
                logging.info("Sending request to the API...")
                response = requests.get(url, headers=headers, params=querystring)
                logging.info("API Response: %s", response.json())
                data = response.json()

                # Print the tweet message
                if data.get("success"):
                    tweet_text = data.get("text", "No text available")
                    print(f"[INFO] Original Tweet Message: {tweet_text}")
                    logging.info("Original Tweet Message: %s", tweet_text)

                    # Clean the tweet text
                    cleaned_text = clean_tweet_text(tweet_text)
                    print(f"[INFO] Cleaned Tweet Message: {cleaned_text}")
                    logging.info("Cleaned Tweet Message: %s", cleaned_text)

                    post_text = cleaned_text
                    post_facets = []

                    # Download media files
                    images = []
                    videos = []
                    if "media" in data:
                        for index, media in enumerate(data["media"]):
                            media_url = media["url"]
                            media_type = media.get("type", "image")  # Default to image if type not specified
                            print(f"[PROCESS] Downloading media from {media_url}...")
                            logging.info("Downloading media from %s...", media_url)
                            media_response = requests.get(media_url)
                            
                            if media_response.status_code != 200:
                                print(f"[ERROR] Failed to download media from {media_url}. Status code: {media_response.status_code}")
                                logging.error("Failed to download media from %s. Status code: %d", media_url, media_response.status_code)
                                continue

                            if media_type == "video":
                                video_path = f"video{index}.mp4"
                                with open(video_path, "wb") as file:
                                    file.write(media_response.content)
                                videos.append(video_path)
                                print(f"[SUCCESS] Downloaded {media_url} as {video_path}")
                                logging.info("Downloaded %s as %s", media_url, video_path)
                            else:
                                image_path = f"image{index}.jpg"
                                with open(image_path, "wb") as file:
                                    file.write(media_response.content)
                                images.append(image_path)
                                print(f"[SUCCESS] Downloaded {media_url} as {image_path}")
                                logging.info("Downloaded %s as %s", media_url, image_path)

                    # Post to BlueSky
                    if images or videos:
                        print("[PROCESS] Posting to BlueSky with media...")
                        logging.info("Posting to BlueSky with media...")

                        if images:
                            try:
                                image_data = []
                                image_alts = []
                                for image_path in images:
                                    with open(image_path, 'rb') as img_file:
                                        image_data.append(img_file.read())
                                    image_alts.append('Tweet image')

                                # Use send_images for multiple image posts
                                response = bluesky_client.send_images(
                                    text=post_text,
                                    images=image_data,
                                    image_alts=image_alts
                                )
                                print(f"[SUCCESS] Posted images to BlueSky. Response: {response}")
                                logging.info("Posted images to BlueSky. Response: %s", response)
                            except Exception as e:
                                print(f"[ERROR] Failed to post images to BlueSky: {e}")
                                logging.error("Failed to post images to BlueSky: %s", e)

                        if videos:
                            for video_path in videos:
                                try:
                                    with open(video_path, 'rb') as vid_file:
                                        vid_data = vid_file.read()
                                    
                                    # Use send_video for video posts
                                    response = bluesky_client.send_video(
                                        text=post_text,
                                        video=vid_data,
                                        video_alt="Tweet video"
                                    )
                                    print(f"[SUCCESS] Posted video to BlueSky. Response: {response}")
                                    logging.info("Posted video to BlueSky. Response: %s", response)
                                except Exception as e:
                                    print(f"[ERROR] Failed to post video to BlueSky: {e}")
                                    logging.error("Failed to post video to BlueSky: %s", e)

                    else:
                        # Post text only if no media is present
                        try:
                            print("[PROCESS] Posting to BlueSky without media...")
                            logging.info("Posting to BlueSky without media...")
                            response = bluesky_client.send_post(
                                text=post_text
                            )
                            print(f"[SUCCESS] Posted text to BlueSky. Response: {response}")
                            logging.info("Posted text to BlueSky. Response: %s", response)
                        except Exception as e:
                            print(f"[ERROR] Failed to post text to BlueSky: {e}")
                            logging.error("Failed to post text to BlueSky: %s", e)

                    # Delete media files locally
                    for image_path in images:
                        try:
                            os.remove(image_path)
                            print(f"[INFO] Deleted {image_path}")
                            logging.info("Deleted %s", image_path)
                        except Exception as e:
                            print(f"[ERROR] Failed to delete {image_path}: {e}")
                            logging.error("Failed to delete %s: %s", image_path, e)
                    for video_path in videos:
                        try:
                            os.remove(video_path)
                            print(f"[INFO] Deleted {video_path}")
                            logging.info("Deleted %s", video_path)
                        except Exception as e:
                            print(f"[ERROR] Failed to delete {video_path}: {e}")
                            logging.error("Failed to delete %s: %s", video_path, e)

        else:
            print(f"[WARNING] No tweets found for the user '{target_username}'.")
            logging.info("No tweets found for the user '%s'.", target_username)

        # Wait for the specified interval before checking again
        print(f"[INFO] Waiting for {check_interval} seconds before checking again...")
        logging.info("Waiting for %d seconds before checking again...", check_interval)
        time.sleep(check_interval)

# Run the async function
asyncio.run(main())
