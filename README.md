# Twitter to Bluesky Bot
## Prerequisites

- Python 3.7 or higher
- A Twitter account (preferably an alternate account for security reasons)
- A Bluesky account
- A RapidAPI account

## Setup Instructions

### 1. Clone the Repository
```bash
git clone https://github.com/Yoproo20/twitter-to-bluesky-template.git
cd twitter-to-bluesky-bot
```

### 2. Install Required Packages

Install the necessary Python packages using pip:

```bash
pip install -r requirements.txt
```

### 3. Obtain API Keys

#### Twitter Scraping

- **Twitter Username and Password:** Use your Twitter account credentials. It's recommended to use an alternate account for security reasons. Do not create a new account and immediately use the script.

#### RapidAPI Key

- **Sign up for RapidAPI:** Go to [RapidAPI](https://rapidapi.com/) and create an account.
- **Subscribe to the Twitter Video and Image Downloader API:** Search for "Twitter Video and Image Downloader" on RapidAPI and subscribe to the API. The free quota is 1000 per month.
- **Get Your API Key:** Once subscribed, navigate to the API's dashboard to find your API key.

#### Bluesky API

- **Bluesky Handle/Username and App-Password:** Use your Bluesky account credentials. You may need to generate an app-password from your account settings.

### 4. Run the Setup Script

Run the setup script to configure your environment:

```bash
python setup.py
```

This script will prompt you for the following information:
- Twitter account username
- Twitter account password
- RapidAPI key
- Bluesky handle/username
- Bluesky app-password
- Target Twitter user handle (without the '@')
- Interval in seconds to check for new posts

### 5. Running the Bot

After setting up the environment, you can run the bot using:

```bash
python main.py
```

## Precautions

- **Security:** It's recommended to use alternate accounts for Twitter/X to avoid your main account being rate limited.
- **API Usage:** Be mindful of the API usage limits on RapidAPI to avoid your account being rate limited.
- **Environment Variables:** Ensure your `.env` file is not exposed publicly as it contains sensitive information.
- **Amazon Web Services (AWS):** With how Tweety (the scraper) handles getting posts, it is impossible to host the mirror on AWS **unless** you are using a proxy so the IP wont show as an AWS one. You have to set it up on your own if you use AWS.

## Things that don't work (as of now)
1. If the latest post is a reply then it won't work.
2. If the post contains a video, Bluesky blocks videos over 60 seconds.
3. NO VIDEO SUPPORT, I'm trying to make it easy and clean and videos are stupid on AT, so the only media supported is images right now

## Troubleshooting

- **API Errors:** Check your API keys and ensure they are correctly entered in the `.env` file.
- **Login Issues:** Verify your Twitter and Bluesky credentials.

## To-do
- [] Add video support

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
