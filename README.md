# Twitter to Bluesky Bot

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![BuyMeACoffee](https://raw.githubusercontent.com/pachadotdev/buymeacoffee-badges/main/bmc-blue.svg)](https://buymeacoffee.com/adamr.bsky)
[![GitBook](https://img.shields.io/badge/GitBook-%23000000.svg?style=for-the-badge&logo=gitbook&logoColor=white)](https://bot-docs.yopro.studio/)

Documentation at [https://bot-docs.yopro.studio/](https://bot-docs.yopro.studio/)

## Prerequisites

- Python 3.7 or higher
- A Twitter account (**Highly recommend creating an alt account, wait a few days after creating it for highest chance of it not being banned**)
- A Bluesky account
- A RapidAPI account (only for translation)

## Setup Instructions

### 1. Clone the Repository

```bash
git clone https://github.com/Yoproo20/twitter-to-bluesky-template.git
cd twitter-to-bluesky-template
```

### 2. Install Required Packages

I recommend using [uv](https://docs.astral.sh/uv/getting-started/installation/) to install everything. You do you.

Install the necessary Python packages using pip:

```bash
pip install -r requirements.txt
```

or uv:

```bash
uv pip install -r requirements.txt
```

### 3. Obtain API Keys

#### Twitter Scraping

**Primary (recommended):** Use cookies from your browser to bypass Cloudflare blocks. 

**To know how to get the cookies, look at this guide for Firefox and Chrome based browsers:**  https://bot-docs.yopro.studio/getting-started/twitter-authentication#how-to-extract-cookies-from-your-browser

**Secondary:** Twitter username and password. May be blocked by Cloudflare (no way to bypass using this method).

#### RapidAPI Key (translation only)

- **Sign up for RapidAPI:** Go to [RapidAPI](https://rapidapi.com/) and create an account.
- **Subscribe to the Translate API:** Search for [https://rapidapi.com/joshimuddin8212/api/free-google-translator](https://rapidapi.com/joshimuddin8212/api/free-google-translator) and subscribe to the API. The free quota is 5,000 per month (means 5000 translations/post per month).
- **Get Your API Key:** Once subscribed, navigate to the API's dashboard to find your API key.

#### Bluesky API

- **Bluesky Handle/Username and App-Password:** Use your Bluesky account credentials. You may need to generate an app-password from your account settings.

### 4. Run the Setup Script

Run the setup script to configure the .env file:

```bash
python setup.py
```

This script will prompt you for the following information:

- auth_token (only if you are using the primary method)
- ct0 (only if you are using the primary method)
- guest_id (only if you are using the primary method)
- twid (only if you are using the primary method)
- Twitter account username (only if you are using the secondary method)
- Twitter account password (only if you are using the secondary method)
- Bluesky handle/username
- Bluesky app-password
- Target Twitter user handle (without the '@')
- Interval in **seconds** to check for new posts
- RapidAPI key (for translation only)

### 5. Running the Bot

After setting up the environment, you can run the bot using:

```bash
uv run main.py
or
python main.py
```

## Precautions

- **Security:** It's recommended to use alternate accounts for Twitter/X to avoid your main account being rate limited.
- **API Usage:** Be mindful of the API usage limits on RapidAPI to avoid your account being rate limited.
- **Environment Variables:** Ensure your `.env` file is not exposed publicly as it contains sensitive information.
- **Amazon Web Services (AWS):** With how Tweety (the scraper) handles getting posts, it is impossible to host the mirror on AWS **unless** you are using a proxy so the IP wont show as an AWS one. You have to set it up on your own if you use AWS.
- Setup a Python virtual environment and install the requirements in it.

```bash
python -m venv venv
```

or

```bash
uv venv venv
```

## Troubleshooting

- **API Errors:** Check your API keys and ensure they are correctly entered in the `.env` file.
- **Login Issues:** Verify your Twitter and Bluesky credentials.

## License

This project is licensed under the GNU General Public License v3.0. See the [LICENSE](LICENSE) file for details.