# Instagram Bot - Web Interface

A modern web interface for the Instagram Comment Bot that allows you to easily manage and monitor your bot's activity.

## Features

- **Dashboard**: View bot status, last run, and next scheduled run
- **Configuration**: Update target accounts, fitness keywords, and bot settings
- **Activity Log**: Monitor bot activity in real-time
- **Start/Stop**: Control the bot directly from the web interface

## Prerequisites

- Python 3.7+
- Chrome or Firefox browser
- Instagram account credentials
- OpenAI API key

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd insta-bot
   ```

2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-web.txt
   ```

3. Create a `.env` file with your credentials:
   ```
   INSTAGRAM_USERNAME=your_username
   INSTAGRAM_PASSWORD=your_password
   OPENAI_API_KEY=your_openai_api_key
   ```

## Running the Web Interface

1. Start the web server:
   ```bash
   python app.py
   ```

2. Open your browser and navigate to:
   ```
   http://localhost:5000
   ```

3. Configure your bot settings through the web interface

## Usage

1. **Dashboard**
   - View the current status of the bot
   - See when the bot last ran and when it will run next
   - Start or stop the bot

2. **Configuration**
   - Add or remove target accounts
   - Set fitness-related keywords (optional)
   - Configure comment limits and frequency

3. **Activity Log**
   - Monitor the bot's activity in real-time
   - View any errors or issues that occur

## Troubleshooting

- If the bot doesn't start, check the terminal for error messages
- Make sure all required environment variables are set
- Ensure you have a stable internet connection
- Check that your Instagram account is not locked or requires verification

## License

This project is licensed under the MIT License - see the LICENSE file for details.
