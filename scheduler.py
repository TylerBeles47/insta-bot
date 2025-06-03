import time
import schedule
import logging
from datetime import datetime, timedelta
from typing import Optional
from pathlib import Path
import json
import random
import os

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class BotScheduler:
    def __init__(self):
        self.data_dir = Path("data")
        self.data_dir.mkdir(exist_ok=True)
        self.stats_file = self.data_dir / "bot_stats.json"
        self.stats = self._load_stats()
    
    def _load_stats(self) -> dict:
        """Load bot statistics from file"""
        if self.stats_file.exists():
            try:
                with open(self.stats_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                pass
        return {
            'comments_posted': 0,
            'last_comment_time': None,
            'comments_today': 0,
            'last_reset_date': datetime.now().strftime('%Y-%m-%d')
        }
    
    def _save_stats(self):
        """Save bot statistics to file"""
        with open(self.stats_file, 'w') as f:
            json.dump(self.stats, f, indent=2)
    
    def _reset_daily_counters(self):
        """Reset daily counters if it's a new day"""
        today = datetime.now().strftime('%Y-%m-%d')
        if self.stats.get('last_reset_date') != today:
            self.stats['comments_today'] = 0
            self.stats['last_reset_date'] = today
            self._save_stats()
    
    def can_post_comment(self, max_per_day: int) -> bool:
        """Check if we can post another comment based on rate limits"""
        self._reset_daily_counters()
        
        # Get current stats
        comments_today = self.stats.get('comments_today', 0)
        last_time = self.stats.get('last_comment_time')
        
        # Check daily limit
        if comments_today >= max_per_day:
            logger.warning(f"Daily comment limit reached: {comments_today}/{max_per_day} comments used")
            next_reset = (datetime.now().replace(hour=0, minute=0, second=0) + timedelta(days=1)).strftime('%Y-%m-%d %H:%M')
            logger.info(f"Next reset at: {next_reset}")
            return False
            
        # Check time since last comment
        if last_time:
            last_time = datetime.fromisoformat(last_time)
            time_since_last = (datetime.now() - last_time).total_seconds() / 60  # in minutes
            
            # Calculate required delay (longer delays as we approach daily limit)
            base_delay = 30  # minutes
            scaling_factor = 1 + (comments_today / max_per_day) * 2  # Increases delay as we approach limit
            required_delay = base_delay * scaling_factor
            
            if time_since_last < required_delay:
                remaining = (required_delay - time_since_last)
                logger.warning(f"⏳ Rate limited: {time_since_last:.1f} minutes since last comment")
                logger.info(f"Waiting {remaining:.1f} more minutes (required: {required_delay:.1f} min)")
                return False
        
        logger.info(f"Can post comment ({comments_today}/{max_per_day} used today)")
        return True
    
    def record_comment_posted(self):
        """Update stats after posting a comment"""
        now = datetime.now()
        
        # Update stats
        self.stats['comments_posted'] = self.stats.get('comments_posted', 0) + 1
        self.stats['comments_today'] = self.stats.get('comments_today', 0) + 1
        self.stats['last_comment_time'] = now.isoformat()
        
        # Calculate time until next allowed comment
        comments_today = self.stats['comments_today']
        max_per_day = int(os.getenv('MAX_COMMENTS_PER_DAY', 5))
        
        # Save stats
        self._save_stats()
        
        logger.info("\n" + "Comment Statistics " + "="*30)
        logger.info(f"Comment posted successfully")
        logger.info(f"Today's comments: {comments_today}/{max_per_day}")
        logger.info(f"Total comments: {self.stats['comments_posted']}")
        logger.info(f"Last comment at: {now.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Calculate next available time
        if comments_today >= max_per_day:
            next_available = (now.replace(hour=0, minute=0, second=0) + timedelta(days=1)).strftime('%Y-%m-%d %H:%M')
            logger.info(f"⏳ Next available comment: {next_available} (daily limit reached)")
        else:
            # Calculate delay based on number of comments already made today
            base_delay = 30  # minutes
            scaling_factor = 1 + (comments_today / max_per_day) * 2
            next_available = now + timedelta(minutes=base_delay * scaling_factor)
            logger.info(f"Next available comment: {next_available.strftime('%Y-%m-%d %H:%M')} (in ~{base_delay * scaling_factor:.0f} min)")
            
        logger.info("="*50 + "\n")
    
    def schedule_job(self, job_func, interval_hours: int, *args, **kwargs):
        """Schedule a job to run at the given interval"""
        schedule.every(interval_hours).hours.do(job_func, *args, **kwargs)
        logger.info(f"Scheduled job to run every {interval_hours} hours")
    
    def run_pending(self):
        """Run pending scheduled jobs"""
        schedule.run_pending()
    
    def run_continuously(self, interval=1):
        """Run the scheduler continuously"""
        logger.info("Starting scheduler...")
        try:
            while True:
                self.run_pending()
                time.sleep(interval)
        except KeyboardInterrupt:
            logger.info("Scheduler stopped by user")
        except Exception as e:
            logger.error(f"Error in scheduler: {e}")
            raise
