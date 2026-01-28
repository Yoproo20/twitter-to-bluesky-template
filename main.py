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
from atproto_client.models.app.bsky.embed.video import Main as VideoEmbed
import http.client
import ssl
import json
from atproto_client.models.app.bsky.embed.images import Image, Main as ImageEmbed

# Set up logging
logging.basicConfig(
    filename='events.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Load environment variables
load_dotenv()

# Create an SSL context with a specific TLS version
context = ssl.create_default_context()
context.minimum_version = ssl.TLSVersion.TLSv1_2  # Use TLS 1.2 or higher

# Set up the connection directly to the API host
conn = http.client.HTTPSConnection("twitter-video-and-image-downloader.p.rapidapi.com", context=context)

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
        try:
            client.login(session_string=session_string)
            return client
        except Exception as e:
            print(f"[WARNING] Failed to reuse session: {e}")
            logging.warning("Failed to reuse session: %s", e)

    print('[PROCESS] Creating new session')
    logging.info('Creating new session')
    bluesky_username = os.getenv("BLUESKY_USERNAME")
    bluesky_password = os.getenv("BLUESKY_PASSWORD")
    if not bluesky_username or not bluesky_password:
        error_message = "BLUESKY_USERNAME or BLUESKY_PASSWORD is not set."
        print(f"[ERROR] {error_message}")
        logging.error(error_message)
        raise ValueError(error_message)

    client.login(bluesky_username, bluesky_password)

    return client

def remove_tco_links(text: str) -> str:
    # Updated pattern to match all HTTP/HTTPS links
    pattern = r'https?://\S+'
    cleaned_text = re.sub(pattern, '', text)
    cleaned_text = ' '.join(cleaned_text.split())
    return cleaned_text

def clean_tweet_text(text: str) -> str:
    # Use the remove_tco_links function to clean the text
    text = remove_tco_links(text)
    # Replace 'RT ' at the beginning with '🔁'
    text = re.sub(r'^RT ', '🔁 ', text)
    return text

def build_post_text(tweet_text: str) -> dict:
    builder = client_utils.TextBuilder().text(tweet_text)
    
    post_text = builder.build_text()
    post_facets = builder.build_facets()
    
    return {
        "text": post_text,
        "facets": post_facets
    }

async def upload_media(bluesky_client, media_path, media_type):
    try:
        with open(media_path, 'rb') as f:
            media_data = f.read()
        
        # Upload the media to Bluesky
        upload_response = bluesky_client.com.atproto.repo.upload_blob(media_data)
        
        if upload_response and hasattr(upload_response, "blob"):
            print(f"[SUCCESS] Successfully uploaded {media_type} to Bluesky.")
            logging.info(f"Successfully uploaded {media_type} to Bluesky.")
            
            if media_type == "video":
                return VideoEmbed(
                    video=upload_response.blob,
                    alt="Video uploaded from tweet"
                )
            elif media_type == "image":
                return Image(
                    alt="Image uploaded from tweet",
                    image=upload_response.blob
                )
    except Exception as e:
        print(f"[ERROR] Failed to upload {media_type}: {e}")
        logging.error(f"Failed to upload {media_type}: {e}")
    return None

async def make_request_with_retry(conn, target_url, headers, max_retries=3):
    for attempt in range(max_retries):
        try:
            conn.request("GET", target_url, headers=headers)
            res = conn.getresponse()
            if res.status == 200:
                return res
            else:
                print(f"[WARNING] Request failed with status {res.status}. Retrying...")
                logging.warning("Request failed with status %d. Retrying...", res.status)
        except http.client.RemoteDisconnected as e:
            print(f"[WARNING] Remote disconnected. Retrying... (Attempt {attempt + 1}/{max_retries})")
            logging.warning("Remote disconnected. Retrying... (Attempt %d/%d)", attempt + 1, max_retries)
            # Recreate the connection with the correct SSL context
            conn = http.client.HTTPSConnection("twitter-video-and-image-downloader.p.rapidapi.com", context=context)
        except ssl.SSLError as e:
            print(f"[ERROR] SSL error: {e}. Retrying... (Attempt {attempt + 1}/{max_retries})")
            logging.error("SSL error: %s. Retrying... (Attempt %d/%d)", e, attempt + 1, max_retries)
            # Recreate the connection with the correct SSL context
            conn = http.client.HTTPSConnection("twitter-video-and-image-downloader.p.rapidapi.com", context=context)
        except Exception as e:
            print(f"[ERROR] Unexpected error: {e}. Retrying... (Attempt {attempt + 1}/{max_retries})")
            logging.error("Unexpected error: %s. Retrying... (Attempt %d/%d)", e, attempt + 1, max_retries)
            # Recreate the connection with the correct SSL context
            conn = http.client.HTTPSConnection("twitter-video-and-image-downloader.p.rapidapi.com", context=context)
        time.sleep(2 ** attempt)  # Exponential backoff
    raise Exception("Max retries reached. Failed to make request.")

async def get_tweets_with_retry(app, user, max_retries=3):
    for attempt in range(max_retries):
        try:
            return await app.get_tweets(user)
        except (http.client.RemoteDisconnected, http.client.HTTPException) as e:
            if attempt == max_retries - 1:
                raise
            wait_time = 2 ** (attempt + 1)  # Exponential backoff
            print(f"[WARNING] Connection error (attempt {attempt + 1}/{max_retries}). Retrying in {wait_time} seconds...")
            logging.warning("Connection error (attempt %d/%d). Retrying in %d seconds...", attempt + 1, max_retries, wait_time)
            await asyncio.sleep(wait_time)
        except Exception as e:
            print(f"[ERROR] Unexpected error: {e}")
            logging.error("Unexpected error: %s", e)
            raise
    return None

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
    check_interval = int(os.getenv("CHECK_INTERVAL", 300))  # defaulted to 5 seconds

    while True:
        print("[PROCESS] Checking for new tweets...")
        logging.info("Checking for new tweets...")
        
        try:
            user = await app.get_user_info(target_username)
            if not user:
                print(f"[ERROR] Could not retrieve user info for '{target_username}'.")
                logging.error("Error: Could not retrieve user info for '%s'.", target_username)
                time.sleep(300)
                continue

            # Use the retry wrapper for get_tweets
            all_tweets = await get_tweets_with_retry(app, user)
            if all_tweets is None:
                print(f"[ERROR] Could not retrieve tweets for '{target_username}'.")
                logging.error("Error: Could not retrieve tweets for '%s'.", target_username)
                time.sleep(300)
                continue

            if all_tweets:
                # find most recent tweet by id
                latest_tweet = None
                for tweet in all_tweets:
                    if hasattr(tweet, 'id'):
                        latest_tweet = tweet
                        break
                
                if latest_tweet is None:
                    print("[WARNING] No valid tweets found. Waiting for next check...")
                    logging.warning("No valid tweets found. Waiting for next check...")
                    time.sleep(check_interval)
                    continue

                tweet_id = latest_tweet.id
                print(f"[INFO] Latest Tweet ID: {tweet_id}")
                logging.info("Latest Tweet ID: %s", tweet_id)

                if tweet_id != last_tweet_id:
                    last_tweet_id = tweet_id
                    print(f"[SUCCESS] New Tweet ID: {tweet_id}")
                    logging.info("New Tweet ID: %s", tweet_id)

                    # turn id into url for API
                    target_url = f"/twitter?url=https%3A%2F%2Fx.com%2F{target_username}%2Fstatus%2F{tweet_id}"
                    headers = {
                        'x-rapidapi-key': api_key,
                        'x-rapidapi-host': "twitter-video-and-image-downloader.p.rapidapi.com"
                    }

                    try:
                        # Send the request 
                        res = await make_request_with_retry(conn, target_url, headers)
                        data = res.read()

                        # decode bytes to string and parse as JSON
                        try:
                            json_data = json.loads(data.decode("utf-8"))
                            print(json_data)
                        except json.JSONDecodeError as e:
                            print(f"Failed to decode JSON: {e}")
                            json_data = {}

                        # print the tweet in console
                        if json_data.get("success"):
                            print("Success!")
                            tweet_text = json_data.get("text", "No text available")
                            print(f"[INFO] Original Tweet Message: {tweet_text}")
                            logging.info("Original Tweet Message: %s", tweet_text)

                            # clean the tweet text
                            cleaned_text = clean_tweet_text(tweet_text)
                            print(f"[INFO] Cleaned Tweet Message: {cleaned_text}")
                            logging.info("Cleaned Tweet Message: %s", cleaned_text)

                            post_text = cleaned_text
                            post_facets = []

                            # check for media in the JSON data
                            images = []
                            videos = []
                            if "media" in json_data:
                                for index, media in enumerate(json_data["media"]):
                                    media_url = media["url"]
                                    media_type = media.get("type", "image")  
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

                            # post to bluesky
                            if images or videos:
                                print("[PROCESS] Posting to BlueSky with media...")
                                logging.info("Posting to BlueSky with media...")

                                try:
                                    # upload and embed images
                                    image_objects = []
                                    for image_path in images:
                                        embed = await upload_media(bluesky_client, image_path, "image")
                                        if embed:
                                            image_objects.append(embed)

                                    # upload and embed videos
                                    video_embeds = []
                                    for video_path in videos:
                                        embed = await upload_media(bluesky_client, video_path, "video")
                                        if embed:
                                            video_embeds.append(embed)

                                    # post to bluesky
                                    if image_objects:
                                        # create an ImageEmbed with all images
                                        image_embed = ImageEmbed(images=image_objects)
                                        response = bluesky_client.send_post(
                                            text=post_text,
                                            embed=image_embed
                                        )
                                        print(f"[SUCCESS] Posted images to BlueSky. Response: {response}")
                                        logging.info("Posted images to BlueSky. Response: %s", response)
                                    
                                    if video_embeds:
                                        # if there are videos, post them in a separate post
                                        for video_embed in video_embeds:
                                            response = bluesky_client.send_post(
                                                text=post_text,
                                                embed=video_embed
                                            )
                                            print(f"[SUCCESS] Posted video to BlueSky. Response: {response}")
                                            logging.info("Posted video to BlueSky. Response: %s", response)

                                except Exception as e:
                                    print(f"[ERROR] Failed to post media to BlueSky: {e}")
                                    logging.error("Failed to post media to BlueSky: %s", e)

                            else:
                                # post text only if no media is present
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

                            # delete media files locally
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

                    except Exception as e:
                        print(f"[ERROR] Failed to make request: {e}")
                        logging.error("Failed to make request: %s", e)

            else:
                print(f"[WARNING] No tweets found for the user '{target_username}'.")
                logging.info("No tweets found for the user '%s'.", target_username)

            # wait for the specified interval before checking again
            print(f"[INFO] Waiting for {check_interval} seconds before checking again...")
            logging.info("Waiting for %d seconds before checking again...", check_interval)
            time.sleep(check_interval)

        except (http.client.RemoteDisconnected, http.client.HTTPException) as e:
            print(f"[ERROR] Connection error: {e}. Waiting {check_interval} seconds...")
            logging.error("Connection error: %s. Waiting %d seconds...", e, check_interval)
            time.sleep(check_interval)
            continue
        except Exception as e:
            print(f"[ERROR] Unexpected error: {e}. Waiting {check_interval} seconds...")
            logging.error("Unexpected error: %s. Waiting %d seconds...", e, check_interval)
            time.sleep(check_interval)
            continue

# Run the async function
asyncio.run(main())
