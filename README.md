# Twitter to Bluesky Bot

This project is a bot that automatically posts tweets from a specified Twitter account to a Bluesky account. It uses the Twitter API to fetch tweets and the Bluesky API to post them.

## Prerequisites

- Python 3.7 or higher
- A Twitter account (preferably an alternate account for security reasons)
- A Bluesky account
- A RapidAPI account

## Setup Instructions

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/twitter-to-bluesky-bot.git
cd twitter-to-bluesky-bot
```

### 2. Install Required Packages

Install the necessary Python packages using pip:

```bash
pip install -r requirements.txt
```

### 3. Obtain API Keys

#### Twitter API

- **Twitter Username and Password:** Use your Twitter account credentials. It's recommended to use an alternate account for security reasons.

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

## Troubleshooting

- **API Errors:** Check your API keys and ensure they are correctly entered in the `.env` file.
- **Login Issues:** Verify your Twitter and Bluesky credentials.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
