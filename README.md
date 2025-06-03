# Instagram Comment Bot 🤖💬

An automated Instagram bot that generates and posts AI-powered comments on target accounts' posts.

## Features ✨

- 🕵️‍♂️ Scrapes Instagram for new posts from target accounts
- 🤖 Generates human-like comments using OpenAI's GPT
- ⏰ Schedules comments with configurable frequency
- 🔒 Secure credential management with environment variables
- 📊 Tracks comment history and rate limiting

## Prerequisites 📋

- Python 3.8+
- Chrome browser installed
- Instagram account (use a dedicated account, not your personal one)
- OpenAI API key

## Installation 🛠️

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/insta-comment-bot.git
   cd insta-comment-bot
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Copy the example environment file and update with your credentials:
   ```bash
   cp .env.example .env
   ```
   Edit the `.env` file with your Instagram credentials, OpenAI API key, and target account.

## Configuration ⚙️

Edit the `.env` file with your settings:

```env
# Instagram Credentials
INSTAGRAM_USERNAME=your_instagram_username
INSTAGRAM_PASSWORD=your_instagram_password

# OpenAI API Key
OPENAI_API_KEY=your_openai_api_key_here

# Instagram Target Account (competitor)
TARGET_ACCOUNT=target_instagram_username

# Comment Settings
COMMENT_FREQUENCY_HOURS=24  # How often to check for new posts
MAX_COMMENTS_PER_DAY=5      # Maximum comments per day to avoid rate limiting
```

## Usage 🚀

### Run once:
```bash
python main.py --once
```

### Run continuously:
```bash
python main.py
```

The bot will run in the background, checking for new posts at the specified interval.

## Logs 📝

Logs are saved to `bot.log` in the project directory.

## Safety & Best Practices 🔒

- **Use a dedicated Instagram account** for the bot, not your personal account
- **Start with conservative limits** (e.g., 2-3 comments per day)
- **Monitor the bot's behavior** regularly
- **Be respectful** - don't spam or post inappropriate comments
- **Comply with Instagram's Terms of Service**

## Troubleshooting 🐛

- **Login issues**: Make sure your credentials are correct and 2FA is disabled
- **Rate limiting**: If you get blocked, reduce the comment frequency
- **ChromeDriver issues**: Make sure Chrome is installed and up to date

## License 📄

MIT

## Disclaimer ⚠️

This bot is for educational purposes only. Use at your own risk. The developers are not responsible for any account bans or other consequences resulting from the use of this bot.
