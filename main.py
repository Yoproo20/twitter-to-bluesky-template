import asyncio
import os
import requests
import time
import re
import logging
import signal
import sys
import threading
import json
from datetime import datetime, timezone
from tweety import TwitterAsync
from dotenv import load_dotenv
from atproto import Client, SessionEvent, Session, client_utils, models
from atproto_client.models.app.bsky.embed.video import Main as VideoEmbed
from atproto_client.models.app.bsky.embed.defs import AspectRatio
import http.client
import json
from atproto_client.models.app.bsky.embed.images import Image, Main as ImageEmbed

try:
    from PIL import Image as PILImage
    _PIL_AVAILABLE = True
except ImportError:
    _PIL_AVAILABLE = False

# Load environment variables
load_dotenv()

# Data directory for persistent files (used by Docker; default current dir)
DATA_DIR = os.getenv("DATA_DIR", ".")
if DATA_DIR and not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR, exist_ok=True)

# Set up logging (after DATA_DIR so logs go to data dir in Docker)
logging.basicConfig(
    filename=os.path.join(DATA_DIR, "events.log"),
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# Shutdown flag for graceful exit
shutdown_flag = False
_shutdown_handled = False
_stopped_message_shown = False

# print signals
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
    # Handle shutdown signal (Ctrl+C)
    global shutdown_flag, _shutdown_handled
    if _shutdown_handled:
        return
    _shutdown_handled = True
    info("Shutdown signal received. Exiting gracefully...")
    shutdown_flag = True

# Register signal handler for Ctrl+C
signal.signal(signal.SIGINT, signal_handler)


def _input_listener():
    # Background thread: type 'check' and press Enter to trigger an immediate update check
    while True:
        try:
            user_input = input().strip().lower()
            if user_input == "check":
                info("User requested update check...")
                from updater import perform_update
                perform_update()
        except (EOFError, KeyboardInterrupt):
            break
        except Exception as e:
            error(f"Input listener error: {e}")


def start_update_input_listener():
    # Start background thread that listens for 'check' command to trigger updates
    if not sys.stdin.isatty():
        return
    thread = threading.Thread(target=_input_listener, daemon=True)
    thread.start()
    info("Type 'check' and press Enter to manually check for updates.")


def _build_cookie_string(config: dict) -> str | None:
    # Build cookie string from individual env vars. Returns None if auth_token missing
    auth_token = config.get("twitter_auth_token")
    if not auth_token:
        return None
    parts = []
    if config.get("twitter_guest_id"):
        parts.append(f"guest_id={config['twitter_guest_id']}")
    parts.append(f"auth_token={auth_token}")
    if config.get("twitter_ct0"):
        parts.append(f"ct0={config['twitter_ct0']}")
    if config.get("twitter_twid"):
        parts.append(f"twid={config['twitter_twid']}")
    return "; ".join(parts)


async def init_twitter_app(config: dict):
    # Initialize Twitter client. Prefers cookies/auth_token from .env, falls back to sign_in
    session_path = os.path.join(DATA_DIR, "session")
    app = TwitterAsync(session_path)

    cookies = config.get("twitter_cookies")
    if cookies:
        process("Signing in to Twitter via cookies (TWITTER_COOKIES)...")
        try:
            await app.load_cookies(cookies)
            success("Twitter session loaded from cookies.")
            return app
        except Exception as e:
            warning(f"Failed to load cookies: {e}. Trying other methods...")

    cookie_string = _build_cookie_string(config)
    if cookie_string:
        process("Signing in to Twitter via cookies (TWITTER_AUTH_TOKEN, etc.)...")
        try:
            await app.load_cookies(cookie_string)
            success("Twitter session loaded from cookies.")
            return app
        except Exception as e:
            warning(f"Failed to load cookies: {e}. Trying auth token only...")

    auth_token = config.get("twitter_auth_token")
    if auth_token:
        process("Signing in to Twitter via auth token...")
        try:
            await app.load_auth_token(auth_token)
            success("Twitter session loaded from auth token.")
            return app
        except Exception as e:
            warning(f"Failed to load auth token: {e}. Falling back to username/password...")

    username = config.get("twitter_username")
    password = config.get("twitter_password")
    if not username or not password:
        error(
            "No Twitter credentials found. Set TWITTER_AUTH_TOKEN (or TWITTER_COOKIES) "
            "in .env, or TWITTER_USERNAME and TWITTER_PASSWORD."
        )
        raise ValueError("Missing Twitter credentials")
    process("Signing in to Twitter via username/password...")
    await app.sign_in(username, password)
    success("Twitter session created.")
    return app


def parse_bool(value: str, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")

STATE_FILE = os.path.join(DATA_DIR, "state.json")


def get_default_state() -> dict:
    return {"last_tweet_id": None, "last_update_check": None}


def load_state() -> dict:
    try:
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return get_default_state()


def save_state(state: dict) -> None:
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def update_last_tweet_id(tweet_id) -> None:
    state = load_state()
    state["last_tweet_id"] = str(tweet_id)
    save_state(state)


def update_last_check_time() -> None:
    state = load_state()
    state["last_update_check"] = datetime.now(timezone.utc).isoformat()
    save_state(state)


def load_config() -> dict:
    return {
        "target_username": os.getenv("TARGET_USER"),
        "check_interval": int(os.getenv("CHECK_INTERVAL", 300)),
        "enable_translation": parse_bool(os.getenv("ENABLE_TRANSLATION"), default=False),
        "translation_from": os.getenv("TRANSLATION_FROM", "es"),
        "translation_to": os.getenv("TRANSLATION_TO", "en"),
        "auto_update": parse_bool(os.getenv("AUTO_UPDATE"), default=True),
        "update_interval": int(os.getenv("UPDATE_CHECK_INTERVAL", 86400)),
        "twitter_cookies": os.getenv("TWITTER_COOKIES"),
        "twitter_auth_token": os.getenv("TWITTER_AUTH_TOKEN"),
        "twitter_ct0": os.getenv("TWITTER_CT0"),
        "twitter_guest_id": os.getenv("TWITTER_GUEST_ID"),
        "twitter_twid": os.getenv("TWITTER_TWID"),
        "twitter_username": os.getenv("TWITTER_USERNAME"),
        "twitter_password": os.getenv("TWITTER_PASSWORD"),
    }

SESSION_FILE = os.path.join(DATA_DIR, "session.txt")


def get_session() -> str:
    try:
        with open(SESSION_FILE) as f:
            return f.read()
    except FileNotFoundError:
        return None


def save_session(session_string: str) -> None:
    with open(SESSION_FILE, "w") as f:
        f.write(session_string)

def interruptible_sleep(seconds: int) -> None:
    # Sleep for specified seconds, but check shutdown flag every second
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

def clean_tweet_text(text: str) -> str:
    # Replace 'RT ' at the beginning with '🔁'
    text = re.sub(r'^RT ', '🔁 ', text)
    return text

def translate_text(text: str, enable_translation: bool, from_lang: str, to_lang: str) -> str:
    # Translate one language text to another language using RapidAPI Free Google Translator
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
    # Send a translation as a reply to the original post
    try:
        # Create a strong reference to the original post
        post_ref = models.create_strong_ref(original_post)
        
        # Build text builder to parse hashtags in translation
        builder = build_post_text(f"Translation: {translated_text}")
        
        # Create the reply with parent and root pointing to the original post
        reply = bluesky_client.send_post(
            text=builder,
            reply_to=models.AppBskyFeedPost.ReplyRef(parent=post_ref, root=post_ref)
        )
        success(f"Posted translation reply. Response: {reply}")
        return reply
    except Exception as e:
        error(f"Failed to post translation reply: {e}")
        return None

def build_post_text(tweet_text: str) -> client_utils.TextBuilder:
    builder = client_utils.TextBuilder()
    
    # Split the text using regex to find hashtags, preserving the rest of the text
    # Pattern explanation: matches `#` followed by word characters or supported punctuation
    # and keeps the delimiters in the split result.
    parts = re.split(r'(#[^\s#]+)', tweet_text)
    
    for part in parts:
        if not part:
            continue
        if part.startswith('#'):
            # The atproto text builder expects the tag value without the hashtag
            tag_value = part[1:].strip('.,!?:;')
            if tag_value:
                builder.tag(part, tag_value)
            else:
                builder.text(part)
        else:
            builder.text(part)
            
    return builder

def get_image_aspect_ratio(media_path: str) -> AspectRatio | None:
    """Get image dimensions for Bluesky aspect_ratio. Returns None if Pillow unavailable or on failure."""
    if not _PIL_AVAILABLE:
        return None
    try:
        with PILImage.open(media_path) as img:
            w, h = img.size
            if w >= 1 and h >= 1:
                return AspectRatio(width=w, height=h)
    except Exception as e:
        warning(f"Could not read image dimensions for aspect ratio: {e}")
    return None


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
                aspect_ratio = get_image_aspect_ratio(media_path)
                return Image(
                    alt="Image uploaded from tweet",
                    image=upload_response.blob,
                    aspect_ratio=aspect_ratio
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
        builder = build_post_text(post_text)

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
                    text=builder,
                    embed=image_embed
                )
                success(f"Posted images to BlueSky. Response: {response}")
                translated = translate_text(post_text, enable_translation, from_lang, to_lang)
                if translated:
                    send_translation_reply(bluesky_client, response, translated)

            if video_embeds:
                for video_embed in video_embeds:
                    response = bluesky_client.send_post(
                        text=builder,
                        embed=video_embed
                    )
                    success(f"Posted video to BlueSky. Response: {response}")
                    translated = translate_text(post_text, enable_translation, from_lang, to_lang)
                    if translated:
                        send_translation_reply(bluesky_client, response, translated)
        else:
            process("Posting to BlueSky without media...")
            response = bluesky_client.send_post(text=builder)
            success(f"Posted text to BlueSky. Response: {response}")
            translated = translate_text(post_text, enable_translation, from_lang, to_lang)
            if translated:
                send_translation_reply(bluesky_client, response, translated)
    except Exception as e:
        error(f"Failed to post to BlueSky: {e}")
        raise

async def process_tweet(tweet, bluesky_client, enable_translation: bool, from_lang: str, to_lang: str):
    tweet_text = tweet.text if hasattr(tweet, 'text') else "No text available"
    info(f"Original Tweet Message: {tweet_text}")

    cleaned_text = clean_tweet_text(tweet_text)
    info(f"Cleaned Tweet Message: {cleaned_text}")

    images, videos = await download_tweet_media(tweet)

    try:
        await post_to_bluesky(bluesky_client, cleaned_text, images, videos, enable_translation, from_lang, to_lang)
    finally:
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

async def monitor_tweets(
    app,
    bluesky_client,
    target_username: str,
    check_interval: int,
    enable_translation: bool,
    from_lang: str,
    to_lang: str,
    auto_update: bool,
    update_interval: int,
):
    state = load_state()
    last_tweet_id = state.get("last_tweet_id")

    while not shutdown_flag:
        # Check for updates once per update_interval
        if auto_update:
            state = load_state()
            last_update_check_str = state.get("last_update_check")
            should_check_update = False

            if last_update_check_str:
                try:
                    last_update_check = datetime.fromisoformat(last_update_check_str)
                    elapsed = (datetime.now(timezone.utc) - last_update_check).total_seconds()
                    should_check_update = elapsed >= update_interval
                except Exception:
                    should_check_update = True
            else:
                should_check_update = True

            if should_check_update:
                info("Checking for script updates...")
                update_last_check_time()
                try:
                    from updater import perform_update
                    if perform_update():
                        success("Update applied. Script restarting...")
                        return
                    info("No update available.")
                except Exception as e:
                    warning(f"Update check failed: {e}")

        # Reload configuration on each iteration to pick up .env changes
        load_dotenv(override=True)
        config = load_config()
        
        new_target = config.get("target_username")
        if new_target and new_target != target_username:
            info(f"Target username changed from '{target_username}' to '{new_target}'. Resetting last_tweet_id.")
            target_username = new_target
            state = load_state()
            state["last_tweet_id"] = None
            save_state(state)
            last_tweet_id = None
            
        check_interval = config.get("check_interval", 300)
        enable_translation = config.get("enable_translation", False)
        from_lang = config.get("translation_from", "es")
        to_lang = config.get("translation_to", "en")
        auto_update = config.get("auto_update", True)
        update_interval = config.get("update_interval", 86400)

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
                # Pick the tweet with the highest ID (most recent)
                latest_tweet = None
                for tweet in all_tweets:
                    if hasattr(tweet, "id"):
                        if latest_tweet is None or tweet.id > latest_tweet.id:
                            latest_tweet = tweet

                if latest_tweet is None:
                    warning("No valid tweets found. Waiting for next check...")
                    interruptible_sleep(check_interval)
                    continue

                tweet_id = latest_tweet.id
                info(f"Latest Tweet ID: {tweet_id}")

                # Only post if this is a NEW tweet (not already posted)
                # tweet_id > last_tweet_id ensures we never repost; last_tweet_id None = first run
                is_new = last_tweet_id is None or str(tweet_id) > str(last_tweet_id)
                if not is_new:
                    info(f"Skipping already-posted tweet {tweet_id}.")
                else:
                    success(f"New Tweet ID: {tweet_id}")
                    # await process_tweet directly, it will raise to the outer try/except if it fails
                    await process_tweet(latest_tweet, bluesky_client, enable_translation, from_lang, to_lang)
                    update_last_tweet_id(tweet_id)
                    last_tweet_id = str(tweet_id)
            else:
                warning(f"No tweets found for the user '{target_username}'.")

            info(f"Waiting for {check_interval} seconds before checking again...")
            interruptible_sleep(check_interval)

        except (http.client.RemoteDisconnected, http.client.HTTPException) as e:
            error(f"Connection error: {e}. Waiting {check_interval} seconds...")
            interruptible_sleep(check_interval)
            continue
        except Exception as e:
            error(f"Unexpected error: {e}. Re-initializing clients before next check...")
            interruptible_sleep(check_interval)
            try:
                app = await init_twitter_app(config)
                bluesky_client = init_bluesky_client()
                success("Clients re-initialized successfully.")
            except Exception as init_e:
                error(f"Failed to re-initialize clients: {init_e}")
            continue

    global _stopped_message_shown
    if not _stopped_message_shown:
        _stopped_message_shown = True
        info("Script stopped gracefully.")

async def main():
    start_update_input_listener()
    config = load_config()
    target_username = config["target_username"]
    check_interval = config["check_interval"]
    enable_translation = config["enable_translation"]
    from_lang = config["translation_from"]
    to_lang = config["translation_to"]
    auto_update = config["auto_update"]
    update_interval = config["update_interval"]

    info(f"Target username: {target_username}")

    if not target_username:
        error("TARGET_USER is not set in the environment variables.")
        return

    app = await init_twitter_app(config)

    process("Initializing BlueSky client...")
    bluesky_client = init_bluesky_client()

    await monitor_tweets(
        app,
        bluesky_client,
        target_username,
        check_interval,
        enable_translation,
        from_lang,
        to_lang,
        auto_update,
        update_interval,
    )

# Run the async function
asyncio.run(main())
