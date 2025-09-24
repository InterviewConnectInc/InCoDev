"""
Indeed Assistant v3 - Main orchestration with email verification support
"""

import time
import os
import sys
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

# Add indeed_assistant to path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Import Indeed assistant components
from indeed_assistant.credentials import IndeedCredentials
from indeed_assistant import (
    indeed_step_1_catalog_and_loop,
    indeed_step_2_apply_to_job,
    indeed_step_3_loop_return,
    indeed_step_4_scan_answer_questions,
    indeed_step_5_answer_and_continue,
    indeed_step_6_submit_application,
    EMAIL_VERIFICATION_AVAILABLE
)

# Import email verification if available
if EMAIL_VERIFICATION_AVAILABLE:
    from indeed_assistant import IndeedEmailVerification


class IndeedAssistant:
    """Main Indeed automation assistant with email verification support"""
    
    def __init__(self, user_email, keyword="", location=""):
        print(f"🔍 INDEED: Initializing Indeed Assistant v3")
        self.user_email = user_email
        self.keyword = keyword or "remote"  # Default if not provided
        self.location = location or "United States"  # Default if not provided
        self.credentials = IndeedCredentials(user_email)
        self.applications_submitted = 0
        self.max_applications = 10  # Configurable limit
        
    def run_automation(self, user_data, resume_data):
        """Main automation method - orchestrates all steps"""
        print(f"🚀 INDEED: Starting automation for {self.user_email}")
        print(f"🎯 INDEED: Keyword: {self.keyword}, Location: {self.location}")
        
        # Validate credentials
        if not self.credentials.is_valid():
            return {
                'success': False,
                'error': 'Invalid or missing Indeed credentials',
                'total_applications': 0
            }
        
        # Pre-flight check: Verify email access if email verification is available
        if EMAIL_VERIFICATION_AVAILABLE:
            print("📧 INDEED: Checking email access for verification...")
            if not self.credentials.verify_email_access():
                print("⚠️ INDEED: Email verification available but email access failed")
                print("⚠️ INDEED: Continuing without email verification support")
        
        # Create driver
        driver = self._create_driver()
        wait = WebDriverWait(driver, 10)
        
        try:
            # Phase 1: Login FIRST (ensure we're logged in before navigating)
            if not self._login_to_indeed(driver, wait):
                return {
                    'success': False,
                    'error': 'Failed to login to Indeed',
                    'total_applications': 0
                }
            
            # Small pause after login to ensure session is established
            time.sleep(2)
            
            # Phase 2: Navigate to filtered search results
            # Single URL with all filters - no tiers needed
            indeed_url = f"https://www.indeed.com/jobs?q={self.keyword}&l={self.location}&fromage=1&iafilter=1"
            print(f"🌐 INDEED: Navigating to filtered search: {indeed_url}")
            
            driver.get(indeed_url)
            time.sleep(3)  # Allow page to load
            
            # Verify we have job results
            if not self._verify_job_results(driver):
                print("❌ INDEED: No job results found with current filters")
                return {
                    'success': False,
                    'error': 'No job results found. Try different keywords or location.',
                    'total_applications': 0
                }
            
            # Phase 3: Execute automation using Step 1 (which handles the loop)
            print("🔄 INDEED: Starting job application loop...")
            
            # Step 1 handles cataloging and looping through all jobs
            success = indeed_step_1_catalog_and_loop(
                driver=driver,
                wait=wait,
                user_data=user_data,
                resume_data=resume_data,
                max_applications=self.max_applications,
                assistant=self  # Pass self to update application count
            )
            
            return {
                'success': success,
                'total_applications': self.applications_submitted,
                'platform': 'indeed'
            }
            
        except Exception as e:
            print(f"❌ INDEED: Fatal error: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'total_applications': self.applications_submitted
            }
        finally:
            print(f"🏁 INDEED: Closing browser. Submitted {self.applications_submitted} applications")
            driver.quit()
    
    def increment_applications(self):
        """Called by step functions when an application is successfully submitted"""
        self.applications_submitted += 1
        print(f"✅ INDEED: Application submitted! Total: {self.applications_submitted}")
    
    def _create_driver(self):
        """Create Chrome driver with Indeed-optimized settings"""
        chrome_options = Options()
        
        # Essential options
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # Indeed-specific optimizations
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument("--disable-plugins")
        chrome_options.add_argument("--disable-default-apps")
        
        # User agent to appear more human
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=chrome_options
        )
        
        # Hide automation indicators
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        driver.execute_script("Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]})")
        driver.execute_script("Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']})")
        
        print("✅ INDEED: Chrome driver created successfully")
        return driver
    
    def _login_to_indeed(self, driver, wait):
        """Login to Indeed with email verification support - UPDATED FLOW"""
        try:
            print("🔐 INDEED: Navigating to login page...")
            
            # Always start fresh on the login page
            driver.get("https://secure.indeed.com/auth")
            time.sleep(3)
            
            # Check if already logged in by looking for profile indicators
            if self._verify_login_success(driver):
                print("✅ INDEED: Already logged in!")
                return True
            
            # STEP 1: Enter email
            print("📧 INDEED: Entering email...")
            
            email_selectors = [
                "input[id='ifl-InputFormField-3']",
                "input[type='email']",
                "input[name='__email']",
                "input[data-testid='email-input']"
            ]
            
            email_input = None
            for selector in email_selectors:
                try:
                    email_input = wait.until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    break
                except:
                    continue
            
            if not email_input:
                print("❌ INDEED: Could not find email input field")
                return False
            
            email_input.clear()
            email_input.send_keys(self.credentials.email)
            time.sleep(1)
            
            # STEP 2: Click continue/next button
            print("🔄 INDEED: Clicking continue...")
            continue_selectors = [
                "button[type='submit']",
                "button[data-tn-element='auth-page-email-submit-button']",
                "button:contains('Continue')",
                "button.dd-privacy-allow"
            ]
            
            for selector in continue_selectors:
                try:
                    continue_btn = driver.find_element(By.CSS_SELECTOR, selector)
                    if continue_btn.is_displayed():
                        continue_btn.click()
                        break
                except:
                    continue
            
            time.sleep(3)
            
            # STEP 3: Handle "Sign in with your passkey" screen
            print("🔑 INDEED: Looking for passkey screen...")
            
            # Check if we're on the passkey screen
            passkey_indicators = [
                "sign in with your passkey",
                "passkey",
                "use your passkey",
                "passwordless"
            ]
            
            page_source_lower = driver.page_source.lower()
            on_passkey_screen = any(indicator in page_source_lower for indicator in passkey_indicators)
            
            if on_passkey_screen:
                print("🔄 INDEED: Found passkey screen, looking for 'Sign in another way'...")
                
                # Click "Sign in another way"
                alternative_signin_selectors = [
                    "a:contains('Sign in another way')",
                    "button:contains('Sign in another way')",
                    "a:contains('Use a different method')",
                    "button:contains('Use a different method')",
                    "a[href*='alternative']",
                    "button[aria-label*='alternative']",
                    "*:contains('another way')"
                ]
                
                clicked = False
                for selector in alternative_signin_selectors:
                    try:
                        if ":contains" in selector:
                            # Handle text-based selectors
                            elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'Sign in another way') or contains(text(), 'another way')]")
                            for element in elements:
                                if element.is_displayed():
                                    driver.execute_script("arguments[0].click();", element)
                                    clicked = True
                                    print("✅ INDEED: Clicked 'Sign in another way'")
                                    break
                        else:
                            element = driver.find_element(By.CSS_SELECTOR, selector)
                            if element.is_displayed():
                                element.click()
                                clicked = True
                                print("✅ INDEED: Clicked 'Sign in another way'")
                                break
                    except:
                        continue
                    
                    if clicked:
                        break
                
                if not clicked:
                    print("❌ INDEED: Could not find 'Sign in another way' button")
                    # Take a screenshot for debugging
                    driver.save_screenshot("passkey_screen_debug.png")
                    return False
                
                time.sleep(3)
            
            # STEP 4: Handle email verification code screen
            print("📧 INDEED: Checking for email verification screen...")
            
            # Check if we're now on the verification code screen
            if not self._check_needs_verification(driver):
                print("❌ INDEED: Expected email verification screen but didn't find it")
                # Take a screenshot for debugging
                driver.save_screenshot("after_passkey_debug.png")
                return False
            
            # STEP 5: Get and enter verification code
            print("📧 INDEED: Email verification required")
            if not self._handle_email_verification(driver, wait):
                return False
            
            # STEP 6: Verify login success
            time.sleep(3)
            if self._verify_login_success(driver):
                print("✅ INDEED: Login successful!")
                return True
            else:
                print("❌ INDEED: Login verification failed")
                return False
                
        except Exception as e:
            print(f"❌ INDEED: Login error: {str(e)}")
            # Take a screenshot for debugging
            driver.save_screenshot("login_error_debug.png")
            return False
    
    def _check_needs_verification(self, driver):
        """Check if Indeed is asking for email verification"""
        try:
            page_source = driver.page_source.lower()
            verification_indicators = [
                "verification code",
                "verify your identity",
                "we sent a code",
                "enter the code",
                "check your email",
                "verification email",
                "6-digit code",
                "sign in code"
            ]
            
            for indicator in verification_indicators:
                if indicator in page_source:
                    return True
            
            # Also check for specific elements
            verification_selectors = [
                "input[aria-label*='verification']",
                "input[aria-label*='code']",
                "input[placeholder*='code']",
                "[data-testid='verification-code-input']",
                "input[maxlength='6']",
                "input[type='text'][maxlength='6']"
            ]
            
            for selector in verification_selectors:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements and any(e.is_displayed() for e in elements):
                        return True
                except:
                    continue
                    
            return False
            
        except:
            return False
    
    def _handle_email_verification(self, driver, wait):
        """Handle email verification process"""
        try:
            if not EMAIL_VERIFICATION_AVAILABLE:
                print("❌ INDEED: Email verification required but module not available")
                print("💡 INDEED: Please enter the verification code manually")
                print("⏳ INDEED: Waiting 60 seconds for manual code entry...")
                time.sleep(60)
                return True
            
            print("📧 INDEED: Getting verification code from email...")
            
            # Create email verification instance - only pass email
            email_verifier = IndeedEmailVerification(self.credentials.email)
            
            # Get the verification code - pass driver and wait time
            code = email_verifier.get_verification_code(driver, wait_time=60)
            
            if not code:
                print("❌ INDEED: Could not retrieve verification code from email")
                print("💡 INDEED: Please enter the code manually if you received it")
                time.sleep(30)
                return False
            
            print(f"✅ INDEED: Retrieved verification code: {code}")
            
            # Find the code input field
            code_input = None
            code_selectors = [
                "input[type='text'][maxlength='6']",
                "input[aria-label*='verification']",
                "input[aria-label*='code']",
                "input[placeholder*='code']",
                "input[name*='code']",
                "[data-testid='verification-code-input']"
            ]
            
            for selector in code_selectors:
                try:
                    inputs = driver.find_elements(By.CSS_SELECTOR, selector)
                    for inp in inputs:
                        if inp.is_displayed():
                            code_input = inp
                            break
                    if code_input:
                        break
                except:
                    continue
            
            if not code_input:
                print("❌ INDEED: Could not find verification code input field")
                return False
            
            # Enter the code
            code_input.clear()
            code_input.send_keys(code)
            print("✅ INDEED: Entered verification code")
            
            # Submit the code
            submit_selectors = [
                "button[type='submit']",
                "button:contains('Verify')",
                "button:contains('Submit')",
                "button:contains('Continue')"
            ]
            
            for selector in submit_selectors:
                try:
                    if selector.startswith("button:contains"):
                        # Handle text-based selector
                        buttons = driver.find_elements(By.TAG_NAME, "button")
                        text_to_find = selector.split("'")[1]
                        for button in buttons:
                            if text_to_find.lower() in button.text.lower() and button.is_displayed():
                                button.click()
                                print("✅ INDEED: Submitted verification code")
                                time.sleep(3)
                                return True
                    else:
                        submit_btn = driver.find_element(By.CSS_SELECTOR, selector)
                        if submit_btn.is_displayed():
                            submit_btn.click()
                            print("✅ INDEED: Submitted verification code")
                            time.sleep(3)
                            return True
                except:
                    continue
            
            # If no submit button found, try pressing Enter
            code_input.send_keys("\n")
            print("✅ INDEED: Submitted verification code via Enter key")
            time.sleep(3)
            return True
            
        except Exception as e:
            print(f"❌ INDEED: Email verification error: {str(e)}")
            return False
    
    def _verify_login_success(self, driver):
        """Verify Indeed login was successful"""
        try:
            # Check URL - successful login usually redirects away from auth page
            current_url = driver.current_url
            if 'secure.indeed.com/auth' in current_url:
                # Still on login page, check for error messages
                error_indicators = [
                    "[data-testid='login-error']",
                    ".error-message",
                    "[role='alert']"
                ]
                for selector in error_indicators:
                    try:
                        error = driver.find_element(By.CSS_SELECTOR, selector)
                        if error.is_displayed():
                            print(f"❌ INDEED: Login error detected: {error.text}")
                            return False
                    except:
                        continue
            
            # Check for user menu or profile indicators
            success_indicators = [
                "div[data-gnav-element='profileMenu']",
                "button[aria-label*='account']",
                "a[href*='/myjobs']",
                "span[class*='UserName']",
                "button[id*='account-menu']",
                "nav a[href*='/profile']"
            ]
            
            for indicator in success_indicators:
                try:
                    element = driver.find_element(By.CSS_SELECTOR, indicator)
                    if element.is_displayed():
                        return True
                except:
                    continue
            
            # Check page content for user email
            page_text = driver.page_source
            if self.credentials.email in page_text:
                return True
                
            return False
            
        except Exception as e:
            print(f"❌ INDEED: Login verification error: {str(e)}")
            return False
    
    def _verify_job_results(self, driver):
        """Verify we have job results on the page"""
        try:
            # Multiple selectors for job cards
            job_selectors = [
                "[data-jk]",  # Job cards with data-jk attribute
                ".jobsearch-SerpJobCard",  # Classic job card class
                ".job_seen_beacon",  # New job card class
                "[data-testid='job-card']",  # Test ID for job cards
                "a[id^='job_']"  # Job links with ID pattern
            ]
            
            job_cards = []
            for selector in job_selectors:
                try:
                    cards = driver.find_elements(By.CSS_SELECTOR, selector)
                    if cards:
                        job_cards.extend(cards)
                        break
                except:
                    continue
            
            if job_cards:
                # Filter for visible cards
                visible_cards = [card for card in job_cards if card.is_displayed()]
                print(f"✅ INDEED: Found {len(visible_cards)} job listings")
                return len(visible_cards) > 0
            
            # Check for "no results" message
            no_results_indicators = [
                "[class*='no-results']",
                "[class*='jobsearch-NoResult']",
                "div:contains('No jobs found')"
            ]
            
            for indicator in no_results_indicators:
                try:
                    no_results = driver.find_element(By.CSS_SELECTOR, indicator)
                    if no_results.is_displayed():
                        print("❌ INDEED: No results message found")
                        return False
                except:
                    continue
                    
            return False
            
        except Exception as e:
            print(f"❌ INDEED: Error verifying job results: {str(e)}")
            return False