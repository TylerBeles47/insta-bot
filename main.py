import os
import sys
import io
import time
import logging
import atexit
from datetime import datetime
from dotenv import load_dotenv
from pathlib import Path
from instagram_poster import InstagramPoster

# Set console encoding to UTF-8
if sys.platform == 'win32':
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except Exception as e:
        print(f"Warning: Failed to set console encoding: {e}")

# Import our modules
from instagram_scraper import InstagramScraper
from ai_commenter import AICommenter
from instagram_poster import InstagramPoster
from scheduler import BotScheduler

def setup_logging():
    """Set up logging with file and console handlers"""
    # Create logs directory if it doesn't exist
    log_dir = Path('logs')
    log_dir.mkdir(exist_ok=True)
    
    # Create a unique log file for each session
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = log_dir / f'bot_{timestamp}.log'
    
    # Configure root logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # Clear any existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # File handler
    try:
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        print(f"Warning: Failed to set up file logging: {e}")
    
    # Console handler
    try:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    except Exception as e:
        print(f"Warning: Failed to set up console logging: {e}")
    
    # Ensure all handlers are properly closed on exit
    def cleanup():
        for handler in logger.handlers[:]:
            try:
                handler.flush()
                handler.close()
                logger.removeHandler(handler)
            except Exception as e:
                print(f"Error cleaning up logging handler: {e}")
    
    atexit.register(cleanup)
    return logger

# Initialize logging
logger = setup_logging()
logger.info("Starting Instagram Bot")

# Load environment variables
try:
    load_dotenv()
    logger.info("Environment variables loaded successfully")
except Exception as e:
    logger.error(f"Failed to load environment variables: {e}")
    raise

class InstaCommentBot:
    def __init__(self):
        # Reload environment variables to get the latest changes
        from dotenv import load_dotenv
        load_dotenv(override=True)
        
        # Initialize components
        self.scraper = InstagramScraper()
        self.ai_commenter = AICommenter(os.getenv('OPENAI_API_KEY'))
        self.poster = InstagramPoster(headless=False)  # Set to True for production
        self.scheduler = BotScheduler()
        
        # Load config with reloaded environment variables
        self.max_comments_per_day = int(os.getenv('MAX_COMMENTS_PER_DAY', 5))
        self.check_interval_hours = int(os.getenv('COMMENT_FREQUENCY_HOURS', 24))
        
        logger.info(f"Bot initialized with settings: {self.max_comments_per_day} max comments/day, "
                  f"check every {self.check_interval_hours} hours")
    
    def login(self) -> bool:
        """Log in to Instagram"""
        username = os.getenv('INSTAGRAM_USERNAME')
        password = os.getenv('INSTAGRAM_PASSWORD')
        
        if not username or not password:
            logger.error("Instagram credentials not found in .env file")
            return False
            
        logger.info("Logging in to Instagram...")
        return self.poster.login(username, password)
    
    def process_new_posts(self):
        """Check for new posts and comment on them"""
        import random
        import time
        from datetime import datetime
        
        try:
            logger.info("\n" + "="*50)
            logger.info(f"Starting post processing at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Check if we can post a comment
            logger.info("Checking if we can post a comment...")
            if not self.scheduler.can_post_comment(self.max_comments_per_day):
                logger.info("Cannot post comment right now (rate limited or daily limit reached)")
                return False
            
            # Get new posts
            logger.info("\nFetching new posts from target accounts...")
            try:
                posts = self.scraper.get_new_posts()
                if not posts:
                    logger.info("No new posts found to comment on.")
                    return False
                    
                logger.info(f"\nFound {len(posts)} new post(s) to process")
                
                # Process each post
                for idx, post in enumerate(posts, 1):
                    try:
                        logger.info("\n" + "-"*50)
                        logger.info(f"Processing post {idx}/{len(posts)} from @{post['account']}")
                        logger.info(f"URL: {post['url']}")
                        logger.info(f"Age: {post.get('age_hours', 'N/A'):.1f} hours old")
                        logger.info(f"Likes: {post.get('likes', 'N/A')}")
                        logger.info(f"Caption preview: {post.get('caption', 'No caption')[:150]}...")
                        
                        # Generate comment
                        logger.info("\nGenerating comment...")
                        try:
                            comment = self.ai_commenter.generate_comment(post.get('caption', ''))
                            if not comment or not isinstance(comment, str):
                                logger.error("Failed to generate comment: Invalid comment returned")
                                continue
                                
                            logger.info(f"Generated comment: {comment}")
                            
                            if not self.ai_commenter.is_comment_appropriate(comment):
                                logger.warning("Skipping comment: Generated comment was not appropriate")
                                continue
                                
                        except Exception as e:
                            logger.error(f"Error generating comment: {str(e)}", exc_info=True)
                            continue
                        
                        # Post the comment
                        logger.info("\nAttempting to post comment...")
                        try:
                            if self.poster.post_comment(post['url'], comment):
                                self.scraper.process_post(post)
                                self.scheduler.record_comment_posted()
                                logger.info("✅ Successfully posted comment")
                                
                                # Random delay between comments to mimic human behavior (longer delay after success)
                                delay = random.uniform(120, 300)  # 2-5 minutes
                                logger.info(f"Waiting {delay/60:.1f} minutes before next action...")
                                time.sleep(delay)
                                
                                return True  # Successfully posted a comment
                            else:
                                logger.error("❌ Failed to post comment")
                                # Shorter delay after failure
                                time.sleep(random.uniform(30, 60))
                                continue
                                
                        except Exception as e:
                            logger.error(f"Error posting comment: {str(e)}", exc_info=True)
                            time.sleep(random.uniform(30, 60))
                            continue
                            
                    except Exception as e:
                        logger.error(f"Unexpected error processing post: {str(e)}", exc_info=True)
                        time.sleep(10)
                        continue
                
                logger.warning("Processed all posts but couldn't post any comments")
                return False
                
            except Exception as e:
                logger.error(f"Error fetching posts: {str(e)}", exc_info=True)
                return False
                
        except Exception as e:
            logger.error(f"Critical error in process_new_posts: {str(e)}", exc_info=True)
            return False
        except Exception as e:
            logger.error(f"Error processing posts: {e}", exc_info=True)
    
    def run(self, run_once: bool = False):
        """Run the bot"""
        try:
            if not self.login():
                logger.error("Failed to log in. Check your credentials.")
                return
                
            logger.info("Bot started successfully!")
            
            # Run immediately first
            logger.info("Running initial check for new posts...")
            self.process_new_posts()
            
            # Then schedule future checks
            self.scheduler.schedule_job(
                self.process_new_posts,
                self.check_interval_hours
            )
            
            if run_once:
                logger.info("Run once completed. Exiting...")
            else:
                logger.info(f"Scheduler started. Next check in {self.check_interval_hours} hours.")
                logger.info(f"Max {self.max_comments_per_day} comments per day.")
                self.scheduler.run_continuously()
                
        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
        except Exception as e:
            logger.error(f"Error in bot: {e}", exc_info=True)
        finally:
            self.poster.close()
            logger.info("Bot stopped")

def parse_arguments():
    parser = argparse.ArgumentParser(description='Instagram Comment Bot')
    parser.add_argument('--once', action='store_true', help='Run once and exit')
    parser.add_argument('--continuous', action='store_true', help='Run in continuous mode (for web interface)')
    parser.add_argument('--config', type=str, help='Path to config file', default=None)
    return parser.parse_args()

def load_config_file(config_path):
    """Load configuration from a JSON file"""
    try:
        if config_path and os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = json.load(f)
                # Update environment variables
                for key, value in config.items():
                    os.environ[key] = str(value)
                logger.info(f"Loaded config from {config_path}")
                logger.info(f"Target accounts: {os.getenv('TARGET_ACCOUNTS')}")
                logger.info(f"Fitness keywords: {os.getenv('FITNESS_KEYWORDS')}")
    except Exception as e:
        logger.error(f"Error loading config file: {e}")

def main():
    args = parse_arguments()
    
    # Load environment variables
    load_dotenv()
    
    # Load config file if provided
    if args.config:
        load_config_file(args.config)
    
    # Initialize bot
    bot = InstaCommentBot()
    
    # Login
    if not bot.login():
        logger.error("Failed to log in to Instagram")
        return
    
    if args.continuous:
        logger.info("Running in continuous mode...")
        logger.info(f"Using target accounts: {os.getenv('TARGET_ACCOUNTS', '')}")
        logger.info(f"Using fitness keywords: {os.getenv('FITNESS_KEYWORDS', '')}")
        bot.run(run_once=False)
    else:
        logger.info("Running once...")
        logger.info(f"Using target accounts: {os.getenv('TARGET_ACCOUNTS', '')}")
        logger.info(f"Using fitness keywords: {os.getenv('FITNESS_KEYWORDS', '')}")
        bot.run(run_once=args.once)

if __name__ == "__main__":
    import argparse
    import json
    main()
