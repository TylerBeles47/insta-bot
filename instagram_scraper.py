import instaloader
import os
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from pathlib import Path
import json
from dotenv import load_dotenv

# Configure logger
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class InstagramScraper:
    def __init__(self):
        # Reload environment variables to get the latest changes
        from dotenv import load_dotenv
        load_dotenv(override=True)
        
        self.loader = instaloader.Instaloader(
            quiet=True,
            download_comments=False,
            download_geotags=False,
            download_video_thumbnails=False,
            download_pictures=False,
            download_videos=False,
            save_metadata=False,
            compress_json=False
        )
        
        # Load target accounts and keywords from environment
        target_accounts = os.getenv('TARGET_ACCOUNTS', '')
        fitness_keywords = os.getenv('FITNESS_KEYWORDS', '')
        
        self.target_accounts = [acc.strip() for acc in target_accounts.split(',') if acc.strip()]
        self.fitness_keywords = [kw.strip().lower() for kw in fitness_keywords.split(',') if kw.strip()]
        
        self.data_dir = Path("data")
        self.data_dir.mkdir(exist_ok=True)
        self.state_file = self.data_dir / "last_checked.json"
        self.processed_posts = set()
        self.load_processed_posts()
        self.logged_in = False
        
        logger.info(f"Scraper initialized with {len(self.target_accounts)} target accounts and "
                  f"{len(self.fitness_keywords)} fitness keywords")

    def load_processed_posts(self):
        try:
            with open(self.state_file, 'r') as f:
                data = json.load(f)
                self.processed_posts = set(data.get('processed_posts', []))
        except (FileNotFoundError, json.JSONDecodeError):
            pass

    def save_processed_posts(self):
        with open(self.state_file, 'w') as f:
            json.dump({'processed_posts': list(self.processed_posts)}, f)

    def is_fitness_related(self, caption: str) -> bool:
        """Check if the caption contains any fitness-related keywords.
        
        Args:
            caption: The post caption to check
            
        Returns:
            bool: True if the caption contains fitness-related keywords, False otherwise
        """
        if not caption or not caption.strip():
            return False
            
        if not self.fitness_keywords or not any(self.fitness_keywords):
            return True
            
        caption_lower = caption.lower()
        return any(keyword.lower() in caption_lower for keyword in self.fitness_keywords)

    def get_new_posts(self, hours: int = 24):
        """
        Fetch new posts from target Instagram accounts that match fitness keywords.
        
        Args:
            hours: Maximum age of posts to fetch in hours (default: 24)
            
        Returns:
            List of post dictionaries containing post details
        """
        import logging
        import time
        from itertools import islice
        from instaloader.exceptions import (
            QueryReturnedBadRequestException, 
            QueryReturnedForbiddenException,
            QueryReturnedNotFoundException,
            ConnectionException,
            TooManyRequestsException,
            LoginRequiredException
        )
        
        logger = logging.getLogger(__name__)
        new_posts = []
        
        if not self.target_accounts or not any(self.target_accounts):
            logger.warning("No target accounts specified in TARGET_ACCOUNTS")
            return new_posts
            
        logger.info(f"Checking {len(self.target_accounts)} target accounts for new posts...")
        
        # Login if not already logged in
        if not self.logged_in:
            username = os.getenv('INSTAGRAM_USERNAME')
            password = os.getenv('INSTAGRAM_PASSWORD')
            if username and password:
                if not self.login(username, password):
                    logger.error("Failed to log in to Instagram. Some features may be limited.")
                    return new_posts
        
        for account in self.target_accounts:
            account = account.strip()
            if not account:
                continue
                
            logger.info(f"\n👤 Checking account: @{account}")
            
            # Try to get profile with retries
            max_retries = 3
            profile = None
            
            for attempt in range(max_retries):
                try:
                    profile = instaloader.Profile.from_username(self.loader.context, account)
                    logger.info(f"  ✅ Profile found: {profile.full_name if hasattr(profile, 'full_name') else 'N/A'} ({getattr(profile, 'followers', 'N/A')} followers)")
                    break
                except (QueryReturnedBadRequestException, QueryReturnedForbiddenException,
                       QueryReturnedNotFoundException, ConnectionException, TooManyRequestsException) as e:
                    if attempt == max_retries - 1:  # Last attempt
                        logger.error(f"  ❌ Failed to fetch profile after {max_retries} attempts: {str(e)}")
                        break
                    wait_time = (attempt + 1) * 5  # 5, 10, 15 seconds
                    logger.warning(f"  ⏳ Error fetching profile. Retrying in {wait_time}s... (Attempt {attempt + 1}/{max_retries})")
                    time.sleep(wait_time)
                except Exception as e:
                    logger.error(f"  ❗ Unexpected error fetching profile: {str(e)}")
                    break
            
            if not profile:
                logger.error(f"  ❗ Could not fetch profile for @{account}, skipping...")
                continue
            
            # Get recent posts with error handling
            try:
                posts = []
                try:
                    # Try to get up to 10 most recent posts
                    posts = list(islice(profile.get_posts(), 10))
                    logger.info(f"  📥 Fetched {len(posts)} recent posts from @{account}")
                except (QueryReturnedBadRequestException, QueryReturnedForbiddenException,
                       QueryReturnedNotFoundException, ConnectionException, TooManyRequestsException) as e:
                    logger.error(f"  ❗ Error fetching posts (rate limited?): {str(e)}")
                    time.sleep(30)  # Wait before continuing to next account
                    continue
                except Exception as e:
                    logger.error(f"  ❗ Error fetching posts: {str(e)}")
                    continue
                
                post_count = 0
                for post in posts:
                    try:
                        post_id = post.shortcode
                        
                        # Skip if we've already processed this post
                        if post_id in self.processed_posts:
                            logger.debug(f"  ⏭ Already processed post {post_id}")
                            continue
                        
                        # Get post age
                        post_date = getattr(post, 'date_utc', None) or datetime.utcnow()
                        post_age_hours = (datetime.utcnow() - post_date).total_seconds() / 3600
                        
                        # Skip if post is too old
                        if post_age_hours > hours:
                            logger.debug(f"  ⏭ Post {post_id} is too old ({post_age_hours:.1f}h > {hours}h)")
                            continue
                        
                        # Get caption safely
                        caption = (getattr(post, 'caption', '') or '').lower()
                        
                        # Skip if no caption (videos/reels often don't have captions)
                        if not caption.strip():
                            logger.debug(f"  Post {post_id} has no caption")
                            continue
                        
                        # Check if post is relevant to fitness
                        if not self.is_fitness_related(caption):
                            logger.debug(f"  Post {post_id} is not fitness-related")
                            continue
                        
                        # Create post data
                        post_data = {
                            'id': post_id,
                            'shortcode': post_id,  # For backward compatibility
                            'url': f"https://www.instagram.com/p/{post_id}",
                            'account': account,
                            'caption': caption,
                            'likes': getattr(post, 'likes', 0),
                            'comments': getattr(post, 'comments', 0),
                            'timestamp': post_date.timestamp(),
                            'date_utc': post_date,  # For backward compatibility
                            'age_hours': post_age_hours
                        }
                        
                        new_posts.append(post_data)
                        post_count += 1
                        logger.info(f"  Found new post: {post_id} ({post_age_hours:.1f}h old, {post_data['likes']} likes)")
                        logger.debug(f"  Caption: {caption[:150]}...")
                        
                        # Limit number of posts per account to avoid rate limiting
                        if post_count >= 3:  # Max 3 posts per account
                            logger.info(f"  Reached maximum posts per account (3)")
                            break
                        
                    except Exception as post_error:
                        logger.error(f"  Error processing post: {str(post_error)}", exc_info=True)
                        continue
                
                logger.info(f"  Found {post_count} new posts from @{account}")
                
            except Exception as e:
                logger.error(f"  Error processing posts for @{account}: {str(e)}", exc_info=True)
                continue
        
        logger.info(f"\nFound {len(new_posts)} new posts from {len(self.target_accounts)} accounts")
        return new_posts

    def process_post(self, post_data: dict) -> bool:
        """Mark a post as processed.
        
        Args:
            post_data: Dictionary containing post information
            
        Returns:
            bool: True if the post was newly processed, False if it was already processed
        """
        post_id = post_data.get('id') or post_data.get('shortcode')
        if not post_id:
            logger.error("Cannot process post: No post ID found in post_data")
            return False
            
        if post_id not in self.processed_posts:
            self.processed_posts.add(post_id)
            self.save_processed_posts()
            logger.debug(f"✅ Marked post {post_id} as processed")
            return True
            
        logger.debug(f"ℹ️ Post {post_id} was already processed")
        return False
        
    def login(self, username: str, password: str) -> bool:
        """Log in to Instagram"""
        if self.logged_in:
            return True
            
        try:
            # Try to load session first
            try:
                self.loader.load_session_from_file(username)
                self.logged_in = True
                print(f"Successfully loaded session for {username}")
                return True
            except FileNotFoundError:
                # If no session file exists, log in with credentials
                print(f"No session found, logging in with credentials...")
            except Exception as e:
                print(f"Error loading session: {e}")
                print("Attempting to log in with credentials...")
                
            try:
                self.loader.login(username, password)
                # Save the session for future use
                self.loader.save_session_to_file()
                self.logged_in = True
                print(f"Successfully logged in as {username}")
                return True
            except Exception as e:
                print(f"Failed to log in: {e}")
                return False
                
        except Exception as e:
            print(f"Error during login: {e}")
            return False
    
    # Removed get_latest_post (single-account logic) as only multi-account logic is needed.
    
    def save_last_checked(self, post_shortcode: str):
        """Save the last checked post to avoid duplicates"""
        data = {
            'last_shortcode': post_shortcode,
            'last_checked': datetime.now().isoformat()
        }
        with open(self.state_file, 'w') as f:
            json.dump(data, f)
    
    def was_post_processed(self, post_shortcode: str) -> bool:
        """Check if a post was already processed"""
        if not self.state_file.exists():
            return False
            
        try:
            with open(self.state_file, 'r') as f:
                data = json.load(f)
                return data.get('last_shortcode') == post_shortcode
        except (json.JSONDecodeError, FileNotFoundError):
            return False
