import asyncio
import os
import requests
import time
import re
import logging
import signal
from datetime import datetime, timezone
from tweety import TwitterAsync
from dotenv import load_dotenv
from atproto import Client, SessionEvent, Session, client_utils, models
from atproto_client.models.app.bsky.embed.video import Main as VideoEmbed
import http.client
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

# Shutdown flag for graceful exit
shutdown_flag = False

# print signales
def info(string: str):
    print(f"[INFO] {string}")
    logging.info(string)

def warning(string: str):
    print(f"[WARNING] {string}")
    logging.warning(string)

def error(string: str):
    print(f"[ERROR] {string}")
    logging.error(string)

def process(string: str):
    print(f"[PROCESS] {string}")
    logging.info(string)

def success(string: str):
    print(f"[SUCCESS] {string}")
    logging.info(string)


def signal_handler(sig, frame):
    """Handle shutdown signal (Ctrl+C)."""
    global shutdown_flag
    info("Shutdown signal received. Exiting gracefully...")
    shutdown_flag = True

# Register signal handler for Ctrl+C
signal.signal(signal.SIGINT, signal_handler)

def parse_bool(value: str, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")

def load_config() -> dict:
    return {
        "target_username": os.getenv("TARGET_USER"),
        "check_interval": int(os.getenv("CHECK_INTERVAL", 300)),
        "enable_translation": parse_bool(os.getenv("ENABLE_TRANSLATION"), default=False),
        "translation_from": os.getenv("TRANSLATION_FROM", "es"),
        "translation_to": os.getenv("TRANSLATION_TO", "en"),
    }

def get_session() -> str:
    try:
        with open('session.txt') as f:
            return f.read()
    except FileNotFoundError:
        return None

def save_session(session_string: str) -> None:
    with open('session.txt', 'w') as f:
        f.write(session_string)

def interruptible_sleep(seconds: int) -> None:
    """Sleep for specified seconds, but check shutdown flag every second."""
    for _ in range(seconds):
        if shutdown_flag:
            break
        time.sleep(1)

def on_session_change(event: SessionEvent, session: Session) -> None:
    if event in (SessionEvent.CREATE, SessionEvent.REFRESH):
        info(f'Session changed: {event} {repr(session)}')
        save_session(session.export())

def init_bluesky_client() -> Client:
    client = Client()
    client.on_session_change(on_session_change)

    session_string = get_session()
    if session_string:
        process('Reusing session')
        try:
            client.login(session_string=session_string)
            return client
        except Exception as e:
            warning(f"Failed to reuse session: {e}")    

    process('Creating new session')
    bluesky_username = os.getenv("BLUESKY_USERNAME")
    bluesky_password = os.getenv("BLUESKY_PASSWORD")
    if not bluesky_username or not bluesky_password:
        error_message = "BLUESKY_USERNAME or BLUESKY_PASSWORD is not set."
        error(error_message)
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

def translate_text(text: str, enable_translation: bool, from_lang: str, to_lang: str) -> str:
    """Translate Spanish text to English using RapidAPI Free Google Translator."""
    if not enable_translation:
        return None
    
    try:
        url = "https://free-google-translator.p.rapidapi.com/external-api/free-google-translator"
        
        querystring = {"from": from_lang, "to": to_lang, "query": text}
        payload = {"translate": "rapidapi"}
        
        translator_api_key = os.getenv("TRANSLATOR_RAPIDAPI_KEY")
        if not translator_api_key:
            error("TRANSLATOR_RAPIDAPI_KEY is not set.")
            return None

        headers = {
            "x-rapidapi-key": translator_api_key,
            "x-rapidapi-host": "free-google-translator.p.rapidapi.com",
            "Content-Type": "application/json"
        }
        
        response = requests.post(url, json=payload, headers=headers, params=querystring, timeout=15)
        if response.status_code == 200:
            result = response.json()
            translated = result.get("translation", "")
            success(f"Translated text: {translated}")
            return translated
        else:
            warning(f"Translation API returned status code {response.status_code}")
            return None
    except Exception as e:
        error(f"Failed to translate text: {e}")
        return None

def send_translation_reply(bluesky_client, original_post, translated_text: str):
    """Send a translation as a reply to the original post."""
    try:
        # Create a strong reference to the original post
        post_ref = models.create_strong_ref(original_post)
        
        # Create the reply with parent and root pointing to the original post
        reply = bluesky_client.send_post(
            text=f"Translation: {translated_text}",
            reply_to=models.AppBskyFeedPost.ReplyRef(parent=post_ref, root=post_ref)
        )
        success(f"Posted translation reply. Response: {reply}")
        return reply
    except Exception as e:
        error(f"Failed to post translation reply: {e}")
        return None

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
            success(f"Successfully uploaded {media_type} to Bluesky.")
            
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
        error(f"Failed to upload {media_type}: {e}")
    return None

async def get_tweets_with_retry(app, user, max_retries=3):
    for attempt in range(max_retries):
        try:
            return await app.get_tweets(user)
        except (http.client.RemoteDisconnected, http.client.HTTPException) as e:
            if attempt == max_retries - 1:
                raise
            wait_time = 2 ** (attempt + 1)  # Exponential backoff
            warning(f"Connection error (attempt {attempt + 1}/{max_retries}). Retrying in {wait_time} seconds...")
            await asyncio.sleep(wait_time)
        except Exception as e:
            error(f"Unexpected error: {e}")
            raise
    return None

async def download_tweet_media(tweet):
    images = []
    videos = []
    if hasattr(tweet, 'media') and tweet.media:
        for index, media in enumerate(tweet.media):
            try:
                media_type = media.type if hasattr(media, 'type') else 'photo'
                process(f"Downloading {media_type} media...")

                if media_type == "video":
                    best_stream = await media.best_stream()
                    if best_stream:
                        video_path = await best_stream.download(filename=f"video{index}.mp4")
                        if video_path:
                            videos.append(video_path)
                            success(f"Downloaded video as {video_path}")
                    else:
                        warning("No stream available for video")
                else:
                    image_path = await media.download(filename=f"image{index}.jpg")
                    if image_path:
                        images.append(image_path)
                        success(f"Downloaded image as {image_path}")
            except Exception as e:
                error(f"Failed to download media: {e}")
                continue
    return images, videos

async def post_to_bluesky(bluesky_client, post_text: str, images, videos, enable_translation: bool, from_lang: str, to_lang: str):
    try:
        if images or videos:
            process("Posting to BlueSky with media...")

            image_objects = []
            for image_path in images:
                embed = await upload_media(bluesky_client, image_path, "image")
                if embed:
                    image_objects.append(embed)

            video_embeds = []
            for video_path in videos:
                embed = await upload_media(bluesky_client, video_path, "video")
                if embed:
                    video_embeds.append(embed)

            if image_objects:
                image_embed = ImageEmbed(images=image_objects)
                response = bluesky_client.send_post(
                    text=post_text,
                    embed=image_embed
                )
                success(f"Posted images to BlueSky. Response: {response}")
                translated = translate_text(post_text, enable_translation, from_lang, to_lang)
                if translated:
                    send_translation_reply(bluesky_client, response, translated)

            if video_embeds:
                for video_embed in video_embeds:
                    response = bluesky_client.send_post(
                        text=post_text,
                        embed=video_embed
                    )
                    success(f"Posted video to BlueSky. Response: {response}")
                    translated = translate_text(post_text, enable_translation, from_lang, to_lang)
                    if translated:
                        send_translation_reply(bluesky_client, response, translated)
        else:
            process("Posting to BlueSky without media...")
            response = bluesky_client.send_post(text=post_text)
            success(f"Posted text to BlueSky. Response: {response}")
            translated = translate_text(post_text, enable_translation, from_lang, to_lang)
            if translated:
                send_translation_reply(bluesky_client, response, translated)
    except Exception as e:
        error(f"Failed to post to BlueSky: {e}")

async def process_tweet(tweet, bluesky_client, enable_translation: bool, from_lang: str, to_lang: str):
    tweet_text = tweet.text if hasattr(tweet, 'text') else "No text available"
    info(f"Original Tweet Message: {tweet_text}")

    cleaned_text = clean_tweet_text(tweet_text)
    info(f"Cleaned Tweet Message: {cleaned_text}")

    images, videos = await download_tweet_media(tweet)
    await post_to_bluesky(bluesky_client, cleaned_text, images, videos, enable_translation, from_lang, to_lang)

    for image_path in images:
        try:
            os.remove(image_path)
            info(f"Deleted {image_path}")
        except Exception as e:
            error(f"Failed to delete {image_path}: {e}")
    for video_path in videos:
        try:
            os.remove(video_path)
            info(f"Deleted {video_path}")
        except Exception as e:
            error(f"Failed to delete {video_path}: {e}")

async def monitor_tweets(app, bluesky_client, target_username: str, check_interval: int, enable_translation: bool, from_lang: str, to_lang: str):
    last_tweet_id = None

    while not shutdown_flag:
        process("Checking for new tweets...")

        try:
            user = await app.get_user_info(target_username)
            if not user:
                error(f"Could not retrieve user info for '{target_username}'.")
                interruptible_sleep(300)
                continue

            all_tweets = await get_tweets_with_retry(app, user)
            if all_tweets is None:
                error(f"Could not retrieve tweets for '{target_username}'.")
                interruptible_sleep(300)
                continue

            if all_tweets:
                latest_tweet = None
                for tweet in all_tweets:
                    if hasattr(tweet, 'id'):
                        latest_tweet = tweet
                        break

                if latest_tweet is None:
                    warning("No valid tweets found. Waiting for next check...")
                    interruptible_sleep(check_interval)
                    continue

                tweet_id = latest_tweet.id
                info(f"Latest Tweet ID: {tweet_id}")

                if tweet_id != last_tweet_id:
                    last_tweet_id = tweet_id
                    success(f"New Tweet ID: {tweet_id}")
                    try:
                        await process_tweet(latest_tweet, bluesky_client, enable_translation, from_lang, to_lang)
                    except Exception as e:
                        error(f"Failed to process tweet: {e}")
            else:
                warning(f"No tweets found for the user '{target_username}'.")

            info(f"Waiting for {check_interval} seconds before checking again...")
            interruptible_sleep(check_interval)

        except (http.client.RemoteDisconnected, http.client.HTTPException) as e:
            error(f"Connection error: {e}. Waiting {check_interval} seconds...")
            interruptible_sleep(check_interval)
            continue
        except Exception as e:
            error(f"Unexpected error: {e}. Waiting {check_interval} seconds...")
            interruptible_sleep(check_interval)
            continue

    info("Script stopped gracefully.")

async def main():
    config = load_config()
    target_username = config["target_username"]
    check_interval = config["check_interval"]
    enable_translation = config["enable_translation"]
    from_lang = config["translation_from"]
    to_lang = config["translation_to"]

    info(f"Target username: {target_username}")

    if not target_username:
        error("TARGET_USER is not set in the environment variables.")
        return

    app = TwitterAsync("session")
    username = os.getenv("TWITTER_USERNAME")
    password = os.getenv("TWITTER_PASSWORD")

    process("Signing in to Twitter...")
    await app.sign_in(username, password)

    process("Initializing BlueSky client...")
    bluesky_client = init_bluesky_client()

    await monitor_tweets(app, bluesky_client, target_username, check_interval, enable_translation, from_lang, to_lang)

# Run the async function
asyncio.run(main())
