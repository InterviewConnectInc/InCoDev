import time
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Dict, Optional, Tuple
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class AstonCarterAutomation:
    """
    Aston Carter automation for job board submissions.
    Handles the talent network form submission.
    """
    
    # IMPORTANT: This must match the site_name in your database
    HANDLES_SITE = "Aston Carter"
    
    def __init__(self):
        self.name = "Aston Carter Automation"
        self.board_name = "Aston Carter"
        self.base_url = None  # Will be set from job board data
        self.driver = None
        self.logger = self._setup_logger()
        self.submission_timeout = 300  # 5 minutes max per submission
        
    def _setup_logger(self) -> logging.Logger:
        """Setup logging for the automation"""
        logger = logging.getLogger(self.name)
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            
        return logger
        
    def _create_driver(self) -> webdriver.Chrome:
        """Create and configure Chrome driver"""
        chrome_options = Options()
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument("--start-maximized")
        
        # User agent to appear more human
        chrome_options.add_argument(
            "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
        try:
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # Execute scripts to hide automation
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            self.logger.info("Chrome driver created successfully")
            return driver
            
        except Exception as e:
            self.logger.error(f"Failed to create Chrome driver: {str(e)}")
            raise
    
    def _get_user_data_from_db(self, user_email: str) -> Dict:
        """
        Get user data directly from database including country field
        
        Args:
            user_email: User's email address
            
        Returns:
            dict: User data from database
        """
        try:
            db_config = {
                'host': os.getenv('DB_HOST', 'localhost'),
                'database': os.getenv('DB_NAME', 'postgres'),
                'user': os.getenv('DB_USER', 'InConAdmin'),
                'password': os.getenv('DB_PASSWORD', ''),
                'port': os.getenv('DB_PORT', '5432')
            }
            
            conn = psycopg2.connect(**db_config)
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            # Query user data including country column
            cur.execute("""
                SELECT id, email, first_name, last_name, phone, 
                       city, state, zip_code, country
                FROM users 
                WHERE email = %s
            """, (user_email,))
            
            user_data = cur.fetchone()
            conn.close()
            
            if user_data:
                return dict(user_data)
            else:
                self.logger.warning(f"No user found in database for email: {user_email}")
                return {}
                
        except Exception as e:
            self.logger.error(f"Database error getting user data: {str(e)}")
            return {}
            
    def submit_application(self, job_board: Dict, user_profile: Dict, 
                         stop_check_callback=None) -> Tuple[bool, str]:
        """
        Submit application to Aston Carter job board
        
        Args:
            job_board: Dictionary containing job board details (url, etc.)
            user_profile: Dictionary containing user profile data
            stop_check_callback: Optional callback to check if process should stop
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            user_email = user_profile.get('email', 'Unknown user')
            self.logger.info(f"Starting Aston Carter submission for {user_email}")
            
            # Get fresh user data from database
            db_user_data = self._get_user_data_from_db(user_email)
            
            # Merge database data with passed profile (DB takes precedence)
            if db_user_data:
                user_profile = {**user_profile, **db_user_data}
                self.logger.info(f"Updated user profile with database data")
            
            # Log the data we're working with
            self.logger.info(f"User profile data: First={user_profile.get('first_name')}, "
                           f"Last={user_profile.get('last_name')}, "
                           f"Email={user_profile.get('email')}, "
                           f"Phone={user_profile.get('phone')}, "
                           f"Country={user_profile.get('country', 'Not set')}")
            
            # Extract URL from job board data
            self.base_url = job_board.get('site_url', job_board.get('url', job_board.get('website_url')))
            if not self.base_url:
                return False, "No URL provided for job board"
                
            # Create driver
            self.driver = self._create_driver()
            
            # Check for stop signal
            if stop_check_callback and stop_check_callback():
                return False, "Process stopped by user"
                
            # Navigate to the form page
            self.logger.info(f"Navigating to {self.base_url}")
            self.driver.get(self.base_url)
            time.sleep(3)
            
            # Wait for page to load
            wait = WebDriverWait(self.driver, 20)
            
            # Fill in the form fields
            success = self._fill_talent_network_form(user_profile, job_board, wait, stop_check_callback)
            
            if not success:
                return False, "Failed to fill talent network form"
                
            # Check for stop signal before submission
            if stop_check_callback and stop_check_callback():
                return False, "Process stopped by user"
                
            # Submit the form
            submitted = self._submit_form(wait)
            
            if submitted:
                self.logger.info("Application submitted successfully")
                return True, "Application submitted successfully to Aston Carter"
            else:
                return False, "Failed to submit application form"
                
        except TimeoutException:
            self.logger.error("Timeout while processing Aston Carter application")
            return False, "Timeout: Page took too long to load or respond"
            
        except Exception as e:
            self.logger.error(f"Error during Aston Carter submission: {str(e)}")
            return False, f"Error: {str(e)}"
            
        finally:
            if self.driver:
                try:
                    self.driver.quit()
                    self.logger.info("Driver closed successfully")
                except:
                    pass
                    
    def _fill_talent_network_form(self, user_profile: Dict, job_board: Dict, wait: WebDriverWait, 
                                stop_check_callback=None) -> bool:
        """
        Fill in the Aston Carter Talent Network Form
        
        Returns:
            bool: Success status
        """
        try:
            self.logger.info("Starting Aston Carter form filling process")
            
            # Wait for form to be present
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "form")))
            
            # Track filled fields
            filled_fields = {}
            
            # 1. Fill First Name
            if self._fill_field_by_multiple_strategies(
                "First Name", 
                user_profile.get('first_name', ''),
                [
                    (By.ID, "ctl00_contentPlaceHolder_firstNameTextBox_textBox"),
                    (By.NAME, "ctl00$contentPlaceHolder$firstNameTextBox$textBox"),
                    (By.CSS_SELECTOR, "input[id*='firstName']"),
                    (By.CSS_SELECTOR, "input[name*='firstName']"),
                    (By.XPATH, "//label[contains(text(), 'First Name')]/following::input[1]"),
                    (By.XPATH, "//label[contains(text(), 'First name')]/following::input[1]"),
                    (By.CSS_SELECTOR, "input[placeholder*='First']")
                ],
                wait
            ):
                filled_fields['first_name'] = True
                
            # 2. Fill Last Name
            if self._fill_field_by_multiple_strategies(
                "Last Name",
                user_profile.get('last_name', ''),
                [
                    (By.ID, "ctl00_contentPlaceHolder_lastNameTextBox_textBox"),
                    (By.NAME, "ctl00$contentPlaceHolder$lastNameTextBox$textBox"),
                    (By.CSS_SELECTOR, "input[id*='lastName']"),
                    (By.CSS_SELECTOR, "input[name*='lastName']"),
                    (By.XPATH, "//label[contains(text(), 'Last Name')]/following::input[1]"),
                    (By.XPATH, "//label[contains(text(), 'Last name')]/following::input[1]"),
                    (By.CSS_SELECTOR, "input[placeholder*='Last']")
                ],
                wait
            ):
                filled_fields['last_name'] = True
                
            # 3. Fill Email
            if self._fill_field_by_multiple_strategies(
                "Email",
                user_profile.get('email', ''),
                [
                    (By.ID, "ctl00_contentPlaceHolder_emailTextBox_textBox"),
                    (By.NAME, "ctl00$contentPlaceHolder$emailTextBox$textBox"),
                    (By.CSS_SELECTOR, "input[type='email']"),
                    (By.CSS_SELECTOR, "input[id*='email']"),
                    (By.CSS_SELECTOR, "input[name*='email']"),
                    (By.XPATH, "//label[contains(text(), 'Email')]/following::input[1]"),
                    (By.CSS_SELECTOR, "input[placeholder*='email' i]")
                ],
                wait
            ):
                filled_fields['email'] = True
                
            # 4. Fill Phone
            if self._fill_field_by_multiple_strategies(
                "Phone",
                user_profile.get('phone', ''),
                [
                    (By.ID, "ctl00_contentPlaceHolder_phoneTextBox_textBox"),
                    (By.NAME, "ctl00$contentPlaceHolder$phoneTextBox$textBox"),
                    (By.CSS_SELECTOR, "input[type='tel']"),
                    (By.CSS_SELECTOR, "input[id*='phone']"),
                    (By.CSS_SELECTOR, "input[name*='phone']"),
                    (By.XPATH, "//label[contains(text(), 'Phone')]/following::input[1]"),
                    (By.CSS_SELECTOR, "input[placeholder*='phone' i]")
                ],
                wait
            ):
                filled_fields['phone'] = True
                
            # 5. Fill Country - Use from database or default to "United States"
            country_value = user_profile.get('country', 'United States')
            if not country_value:
                country_value = "United States"
                
            self.logger.info(f"Using country value: {country_value}")
            
            if self._fill_field_by_multiple_strategies(
                "Country",
                country_value,
                [
                    (By.ID, "ctl00_contentPlaceHolder_countryTextBox_textBox"),
                    (By.NAME, "ctl00$contentPlaceHolder$countryTextBox$textBox"),
                    (By.CSS_SELECTOR, "input[id*='country']"),
                    (By.CSS_SELECTOR, "input[name*='country']"),
                    (By.XPATH, "//label[contains(text(), 'Country')]/following::input[1]"),
                    (By.CSS_SELECTOR, "input[placeholder*='country' i]")
                ],
                wait
            ):
                filled_fields['country'] = True
                
            # 6. Select "Office and Clerical" from dropdown
            if self._select_office_and_clerical(wait):
                filled_fields['job_category'] = True
                
            # Check for stop signal
            if stop_check_callback and stop_check_callback():
                return False
                
            # Log summary
            self.logger.info(f"Form filling complete. Filled fields: {list(filled_fields.keys())}")
            
            # Check if minimum fields were filled
            required = ['first_name', 'last_name', 'email', 'phone', 'job_category']
            missing = [f for f in required if f not in filled_fields]
            
            if missing:
                self.logger.error(f"Missing required fields: {missing}")
                return len(missing) <= 1  # Allow if only 1 field is missing
                
            return True
            
        except Exception as e:
            self.logger.error(f"Error filling Aston Carter form: {str(e)}")
            return False
            
    def _fill_field_by_multiple_strategies(self, field_name: str, value: str, 
                                          selectors: list, wait: WebDriverWait) -> bool:
        """
        Try multiple strategies to fill a field
        
        Returns:
            bool: True if field was successfully filled
        """
        if not value:
            self.logger.warning(f"No value provided for {field_name}")
            return False
            
        for selector_type, selector_value in selectors:
            try:
                # Find element
                element = wait.until(
                    EC.presence_of_element_located((selector_type, selector_value)),
                    message=f"Looking for {field_name} with {selector_type}"
                )
                
                # Check if visible and enabled
                if element.is_displayed() and element.is_enabled():
                    # Scroll into view
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
                    time.sleep(0.5)
                    
                    # Clear and fill
                    element.clear()
                    element.send_keys(value)
                    
                    # Trigger change event
                    self.driver.execute_script("""
                        arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
                        arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
                    """, element)
                    
                    # Verify value was entered
                    entered_value = element.get_attribute('value')
                    if entered_value:
                        self.logger.info(f"Successfully filled {field_name} using {selector_type}:{selector_value}")
                        return True
                        
            except (TimeoutException, NoSuchElementException):
                continue
            except Exception as e:
                self.logger.debug(f"Error with {field_name} selector {selector_type}:{selector_value} - {str(e)}")
                continue
                
        self.logger.error(f"Could not fill {field_name} field")
        return False
        
    def _select_office_and_clerical(self, wait: WebDriverWait) -> bool:
        """
        Select "Office and Clerical" from dropdown
        
        Returns:
            bool: Success status
        """
        try:
            self.logger.info("Looking for job category dropdown")
            
            # Common dropdown selectors
            dropdown_selectors = [
                (By.ID, "ctl00_contentPlaceHolder_areasOfInterestDropDownList_dropDownList"),
                (By.NAME, "ctl00$contentPlaceHolder$areasOfInterestDropDownList$dropDownList"),
                (By.CSS_SELECTOR, "select[id*='areasOfInterest']"),
                (By.CSS_SELECTOR, "select[name*='areasOfInterest']"),
                (By.CSS_SELECTOR, "select[id*='category']"),
                (By.CSS_SELECTOR, "select[name*='category']"),
                (By.XPATH, "//label[contains(text(), 'Areas of Interest')]/following::select[1]"),
                (By.XPATH, "//label[contains(text(), 'Job Category')]/following::select[1]"),
                (By.CSS_SELECTOR, "select.form-control"),
                (By.TAG_NAME, "select")
            ]
            
            for selector_type, selector_value in dropdown_selectors:
                try:
                    # Find dropdown element
                    dropdown_element = self.driver.find_element(selector_type, selector_value)
                    
                    if dropdown_element.is_displayed() and dropdown_element.is_enabled():
                        # Scroll into view
                        self.driver.execute_script("arguments[0].scrollIntoView(true);", dropdown_element)
                        time.sleep(0.5)
                        
                        # Create Select object
                        select = Select(dropdown_element)
                        
                        # Try to select "Office and Clerical" by different methods
                        option_selected = False
                        
                        # Method 1: Select by visible text
                        try:
                            select.select_by_visible_text("Office and Clerical")
                            option_selected = True
                            self.logger.info("Selected 'Office and Clerical' by visible text")
                        except:
                            pass
                        
                        # Method 2: Select by partial text match
                        if not option_selected:
                            for option in select.options:
                                option_text = option.text.strip()
                                if "office" in option_text.lower() and "clerical" in option_text.lower():
                                    select.select_by_visible_text(option_text)
                                    option_selected = True
                                    self.logger.info(f"Selected '{option_text}' by partial match")
                                    break
                        
                        # Method 3: Select by value if text contains office/clerical
                        if not option_selected:
                            for option in select.options:
                                option_value = option.get_attribute('value')
                                option_text = option.text.strip()
                                if option_value and ("office" in option_value.lower() or 
                                                   "office" in option_text.lower()):
                                    select.select_by_value(option_value)
                                    option_selected = True
                                    self.logger.info(f"Selected '{option_text}' by value")
                                    break
                        
                        # Method 4: If still not found, select first non-empty option as fallback
                        if not option_selected and len(select.options) > 1:
                            # Skip first option if it's empty (often a placeholder)
                            first_option = select.options[0]
                            if not first_option.text.strip() or first_option.text.strip() == "Select" or first_option.get_attribute('value') == '':
                                select.select_by_index(1)
                                self.logger.warning(f"Selected first available option: {select.options[1].text}")
                            else:
                                select.select_by_index(0)
                                self.logger.warning(f"Selected first option: {first_option.text}")
                            option_selected = True
                        
                        if option_selected:
                            # Trigger change event
                            self.driver.execute_script("""
                                arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
                            """, dropdown_element)
                            return True
                        
                except Exception as e:
                    self.logger.debug(f"Error with dropdown selector {selector_type}:{selector_value} - {str(e)}")
                    continue
            
            self.logger.error("Could not find or select from job category dropdown")
            return False
            
        except Exception as e:
            self.logger.error(f"Error selecting job category: {str(e)}")
            return False
            
    def _submit_form(self, wait: WebDriverWait) -> bool:
        """
        Submit the application form
        
        Returns:
            bool: Success status
        """
        try:
            self.logger.info("Looking for submit button")
            
            # Scroll to bottom to ensure submit button is visible
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(1)
            
            # Look for submit button with various selectors
            submit_selectors = [
                # Specific ASP.NET style IDs
                (By.ID, "ctl00_contentPlaceHolder_submitImageButton"),
                (By.NAME, "ctl00$contentPlaceHolder$submitImageButton"),
                
                # Generic submit selectors
                (By.CSS_SELECTOR, "input[type='submit'][value='Submit']"),
                (By.CSS_SELECTOR, "button[type='submit']"),
                (By.CSS_SELECTOR, "input[type='image'][alt*='Submit']"),
                (By.CSS_SELECTOR, "input[type='button'][value='Submit']"),
                
                # Text-based selectors
                (By.XPATH, "//input[@type='submit' and @value='Submit']"),
                (By.XPATH, "//button[contains(text(), 'Submit')]"),
                (By.XPATH, "//input[@type='image' and contains(@alt, 'Submit')]"),
                
                # ID/name contains submit
                (By.CSS_SELECTOR, "input[id*='submit' i]"),
                (By.CSS_SELECTOR, "button[id*='submit' i]"),
                (By.CSS_SELECTOR, "*[class*='submit-btn' i]"),
                (By.CSS_SELECTOR, "*[class*='submit-button' i]")
            ]
            
            submit_clicked = False
            
            for selector_type, selector_value in submit_selectors:
                try:
                    elements = self.driver.find_elements(selector_type, selector_value)
                    
                    for element in elements:
                        if element.is_displayed() and element.is_enabled():
                            # Scroll to element
                            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
                            time.sleep(0.5)
                            
                            # Try to click
                            try:
                                element.click()
                                submit_clicked = True
                                self.logger.info(f"Clicked submit button using {selector_type}:{selector_value}")
                                break
                            except:
                                # Try JavaScript click
                                self.driver.execute_script("arguments[0].click();", element)
                                submit_clicked = True
                                self.logger.info(f"Clicked submit button via JavaScript using {selector_type}:{selector_value}")
                                break
                    
                    if submit_clicked:
                        break
                        
                except Exception as e:
                    self.logger.debug(f"Error with submit selector {selector_type}:{selector_value} - {str(e)}")
                    continue
            
            if not submit_clicked:
                self.logger.error("Could not find or click submit button")
                return False
            
            # Wait for submission to process
            self.logger.info("Waiting for form submission to process...")
            time.sleep(5)
            
            # Check for success indicators
            return self._check_submission_success()
            
        except Exception as e:
            self.logger.error(f"Error submitting form: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return False
            
    def _check_submission_success(self) -> bool:
        """Check if form was submitted successfully"""
        try:
            # Check for success indicators
            success_indicators = [
                "thank you",
                "thanks",
                "success",
                "received",
                "submitted",
                "confirmation",
                "we'll be in touch",
                "application received",
                "appreciate your interest",
                "successfully submitted",
                "we have received"
            ]
            
            page_source = self.driver.page_source.lower()
            
            for indicator in success_indicators:
                if indicator in page_source:
                    self.logger.info(f"Found success indicator: '{indicator}'")
                    return True
            
            # Check if URL changed (often indicates submission)
            current_url = self.driver.current_url
            if current_url != self.base_url:
                self.logger.info(f"URL changed from {self.base_url} to {current_url}")
                if any(term in current_url.lower() for term in ['success', 'thank', 'confirm', 'complete']):
                    return True
            
            # Check for specific success elements
            success_selectors = [
                ".success-message",
                ".confirmation-message",
                ".thank-you",
                "#success",
                "[class*='success']",
                "[class*='confirmation']",
                "[id*='success']",
                "[id*='confirmation']"
            ]
            
            for selector in success_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements and any(elem.is_displayed() for elem in elements):
                        self.logger.info(f"Found success element: {selector}")
                        return True
                except:
                    continue
            
            # Check if form is gone
            try:
                form = self.driver.find_element(By.TAG_NAME, "form")
                # Form still exists, check for validation errors
                error_indicators = ["error", "required", "invalid", "please fill"]
                errors_found = [ind for ind in error_indicators if ind in page_source]
                if errors_found:
                    self.logger.warning(f"Possible errors found: {errors_found}")
                    return False
            except:
                # Form is gone, likely submitted
                self.logger.info("Form no longer present, assuming submission success")
                return True
            
            # Default to success if no clear indicators
            self.logger.info("No clear success indicators, but no errors found")
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking submission success: {str(e)}")
            return False