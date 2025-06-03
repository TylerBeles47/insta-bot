from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

import os
import time
from pathlib import Path
import json

from dotenv import load_dotenv


# Load environment variables
load_dotenv()


def remove_non_bmp_chars(text: str) -> str:
    """Remove non-BMP (Basic Multilingual Plane) characters from text.
   
    Args:
        text: The input string that may contain non-BMP characters
       
    Returns:
        A string with non-BMP characters removed
    """
    return ''.join(c for c in text if ord(c) <= 0xFFFF)


class InstagramPoster:
    def __init__(self, headless: bool = True):
        self.base_url = "https://www.instagram.com"
        # Try cookies in data/ first, then project root
        self.cookies_path = None
        for path in [Path("data/instagram_cookies.json"), Path("instagram_cookies.json")]:
            if path.exists():
                self.cookies_path = path
                break
        if not self.cookies_path:
            self.cookies_path = Path("data/instagram_cookies.json")  # Default to data/
        
        # Initialize WebDriver
        self.driver = None
        self.wait = None
        if not self.setup_driver(headless):
            raise RuntimeError("Failed to initialize WebDriver")

    def setup_driver(self, headless: bool = True):
        """Set up the Selenium WebDriver with system Chrome installation"""
        try:
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.chrome.service import Service
            import os
            
            print("Setting up Chrome WebDriver using system Chrome...")
            
            # Set up Chrome options
            options = Options()
            
            # Common options
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--disable-extensions')
            options.add_argument('--disable-infobars')
            options.add_argument('--disable-browser-side-navigation')
            options.add_argument('--disable-blink-features=AutomationControlled')
            
            # User agent
            options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36')
            
            # Disable automation flags
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            
            # Set window size
            options.add_argument('--window-size=1920,1080')
            
            # Set headless mode if specified
            if headless:
                options.add_argument('--headless=new')
            else:
                options.add_argument('--start-maximized')
                options.add_argument('--disable-notifications')
            
            # Find Chrome binary path
            chrome_paths = [
                os.path.expanduser("~" + os.sep + "AppData/Local/Google/Chrome/Application/chrome.exe"),
                os.path.expandvars("$PROGRAMFILES/Google/Chrome/Application/chrome.exe"),
                os.path.expandvars("$PROGRAMFILES(x86)/Google/Chrome/Application/chrome.exe")
            ]
            
            chrome_path = None
            for path in chrome_paths:
                if os.path.exists(path):
                    chrome_path = path
                    break
                    
            if not chrome_path:
                print("Error: Chrome browser not found in standard locations.")
                return False
                
            options.binary_location = chrome_path
            
            # Initialize WebDriver without service
            try:
                self.driver = webdriver.Chrome(options=options)
            except Exception as e:
                print(f"Error initializing WebDriver: {str(e)}")
                print("Please ensure you have Chrome browser installed and it's up to date.")
                return False
            
            # Set up wait
            self.wait = WebDriverWait(self.driver, 15)
            
            # Set script timeout
            self.driver.set_script_timeout(30)
            
            print("Test Chrome WebDriver initialized successfully")
            return True
            
        except Exception as e:
            print(f"Failed to initialize WebDriver: {e}")
            import traceback
            traceback.print_exc()
            return False

    def load_cookies(self):
        if self.cookies_path.exists():
            self.driver.get(self.base_url)
            with open(self.cookies_path, 'r') as f:
                cookies = json.load(f)
            for cookie in cookies:
                # Remove 'sameSite' if present, as it's not accepted by Selenium
                cookie.pop('sameSite', None)
                # Adjust domain if needed
                if 'domain' in cookie and cookie['domain'].startswith('.instagram.'):
                    cookie['domain'] = 'instagram.com'
                try:
                    self.driver.add_cookie(cookie)
                except Exception:
                    pass
            self.driver.refresh()
            return True
        return False

    def save_cookies(self):
        cookies = self.driver.get_cookies()
        with open(self.cookies_path, 'w') as f:
            json.dump(cookies, f, indent=2)

    def login(self, username: str, password: str) -> bool:
        try:
            print("Trying cookie-based login...")
            if self.load_cookies():
                self.driver.get(f"{self.base_url}/")
                time.sleep(3)

                if "/accounts/login" not in self.driver.current_url:
                    print("Logged in with cookies!")
                    return True
                else:
                    print("Cookie login failed, falling back to username/password.")
            
            self.driver.get(f"{self.base_url}/accounts/login/")

            try:
                accept_cookies = self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Accept')]"))
                )
                accept_cookies.click()
                time.sleep(1)
            except TimeoutException:
                pass

            username_field = self.wait.until(
                EC.presence_of_element_located((By.NAME, "username"))
            )
            password_field = self.driver.find_element(By.NAME, "password")
            username_field.clear()
            username_field.send_keys(username)
            time.sleep(1)
            password_field.clear()
            password_field.send_keys(password)
            time.sleep(1)

            login_button = self.driver.find_element(By.XPATH, "//button[@type='submit']")
            login_button.click()
            
            # Wait for login to complete
            try:
                self.wait.until(
                    EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Not Now')]"))
                )
                print("Successfully logged in!")
                # Save cookies for future runs
                self.save_cookies()
                return True
            except TimeoutException:
                print("Login might have failed. Check your credentials.")
                return False

        except Exception as e:
            print(f"Error during login: {e}")
            return False

    def post_comment(self, post_url: str, comment_text: str) -> bool:
        try:
            self.driver.get(post_url)
            time.sleep(3)  # Allow full page render

            print(f"About to post comment: {comment_text}")
           
            # Wait for any textarea to be present
            print("Waiting for comment box...")
            self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "textarea")))
           
            # Try multiple selectors for the comment box
            selectors = [
                (By.XPATH, "//textarea[contains(@placeholder, 'Add a comment')]"),
                (By.XPATH, "//textarea[@aria-label='Add a comment…']"),
                (By.CSS_SELECTOR, "textarea[aria-label^='Add a comment']"),
                (By.CSS_SELECTOR, "textarea[placeholder^='Add a comment']")
            ]
           
            comment_box = None
            for by, selector in selectors:
                try:
                    comment_box = self.driver.find_element(by, selector)
                    if comment_box:
                        print(f"Found comment box with {by}")
                        break
                except Exception as e:
                    print(f"Selector {by}={selector} failed: {e}")
           
            if not comment_box:
                print("Could not find comment box with any selector")
                self.driver.save_screenshot('comment_box_not_found.png')
                return False
           
            # Scroll to the comment box and click it
            print("Clicking comment box...")
            self.driver.execute_script("arguments[0].scrollIntoView();", comment_box)
            time.sleep(0.5)
            comment_box.click()
            time.sleep(0.5)
           
            # Re-find the comment box to avoid stale element reference
            comment_box = self.driver.find_element(By.XPATH, "//textarea[contains(@placeholder, 'Add a comment')]")
           
            # Sanitize and type the comment
            print("Sanitizing and typing comment...")
            # Remove non-BMP characters that might cause issues
            sanitized_comment = remove_non_bmp_chars(comment_text)
            if sanitized_comment != comment_text:
                print("Warning: Comment contained non-BMP characters that were removed")
           
            # Type the sanitized comment
            for char in sanitized_comment:
                comment_box.send_keys(char)
                time.sleep(0.05)  # Slight delay to mimic human typing
           
            time.sleep(0.5)  # Brief pause before posting
           
            # Find and click the Post button
            print("Looking for Post button...")
            post_button = None
           
            # Take a screenshot before trying to find the button
            self.driver.save_screenshot('before_post_button_search.png')
           
            # Try multiple selectors for the post button
            post_button_selectors = [
                (By.XPATH, "//div[contains(@role, 'button')][contains(., 'Post')][not(@disabled)]"),
                (By.XPATH, "//button[contains(., 'Post')][not(@disabled)]"),
                (By.XPATH, "//div[contains(text(), 'Post')]/ancestor-or-self::button[not(@disabled)]"),
                (By.CSS_SELECTOR, "div[role='button']:not([disabled]) > div:contains('Post')"),
                (By.CSS_SELECTOR, "button:not([disabled]) > div:contains('Post')"),
                (By.CSS_SELECTOR, "button[type='submit']:not([disabled])"),
                (By.CSS_SELECTOR, "div[role='button'][type='submit']:not([disabled])")
            ]
           
            for attempt in range(3):  # Try up to 3 times
                for by, selector in post_button_selectors:
                    try:
                        print(f"Attempt {attempt + 1}: Trying selector: {by} = {selector}")
                        elements = self.driver.find_elements(by, selector)
                        print(f"Found {len(elements)} elements with selector: {selector}")
                       
                        for element in elements:
                            try:
                                if element.is_displayed() and element.is_enabled():
                                    post_button = element
                                    print(f"Found visible and enabled post button with {by} = {selector}")
                                    break
                            except Exception as e:
                                print(f"Error checking element: {e}")
                       
                        if post_button:
                            break
                           
                    except Exception as e:
                        print(f"Selector {by}={selector} failed: {e}")
               
                if post_button:
                    break
                   
                # Wait a bit before retrying
                time.sleep(1)
           
            if not post_button:
                print("Post button not found with any selector after multiple attempts")
                # Save the page source for debugging
                with open('page_source.html', 'w', encoding='utf-8') as f:
                    f.write(self.driver.page_source)
                self.driver.save_screenshot('post_button_not_found.png')
                return False
               
            if not post_button.is_enabled():
                print("Post button found but not enabled")
                self.driver.save_screenshot('post_button_disabled.png')
                return False
           
            # Click the post button
            print("Clicking post button...")
            self.driver.execute_script("arguments[0].click();", post_button)
           
            # Wait for the comment to be posted
            time.sleep(3)
            print("Comment posted successfully!")
            return True
           
        except Exception as e:
            print(f"Error posting comment: {e}")
            import traceback
            traceback.print_exc()
            # Take a screenshot for debugging
            self.driver.save_screenshot('comment_error.png')
            return False

    def close(self):
        """Close the WebDriver"""
        if hasattr(self, 'driver'):
            self.driver.quit()
            print("Browser closed.")
