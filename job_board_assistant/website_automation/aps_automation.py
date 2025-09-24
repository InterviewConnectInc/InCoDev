import time  # Add this import at the top
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import os
from typing import Dict, Optional, Tuple

class APSAutomation:
    """
    APS (Automation Personnel Services) automation for job board submissions.
    Handles the Job Candidate Form - Houston West location.
    """
    
    # IMPORTANT: This must match the site_name in your database
    HANDLES_SITE = "Automation Personnel Services"
    
    def __init__(self):
        self.name = "APS Automation"
        self.board_name = "Automation Personnel Services"
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
            
    def submit_application(self, job_board: Dict, user_profile: Dict, 
                         stop_check_callback=None) -> Tuple[bool, str]:
        """
        Submit application to APS job board
        
        Args:
            job_board: Dictionary containing job board details (url, etc.)
            user_profile: Dictionary containing user profile data
            stop_check_callback: Optional callback to check if process should stop
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            self.logger.info(f"Starting APS submission for {user_profile.get('email', 'Unknown user')}")
            
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
            success = self._fill_job_candidate_form(user_profile, job_board, wait, stop_check_callback)
            
            if not success:
                return False, "Failed to fill job candidate form"
                
            # Check for stop signal before submission
            if stop_check_callback and stop_check_callback():
                return False, "Process stopped by user"
                
            # Submit the form
            submitted = self._submit_form(wait)
            
            if submitted:
                self.logger.info("Application submitted successfully")
                return True, "Application submitted successfully to APS"
            else:
                return False, "Failed to submit application form"
                
        except TimeoutException:
            self.logger.error("Timeout while processing APS application")
            return False, "Timeout: Page took too long to load or respond"
            
        except Exception as e:
            self.logger.error(f"Error during APS submission: {str(e)}")
            return False, f"Error: {str(e)}"
            
        finally:
            if self.driver:
                try:
                    self.driver.quit()
                    self.logger.info("Driver closed successfully")
                except:
                    pass
                    
    def _fill_job_candidate_form(self, user_profile: Dict, job_board: Dict, wait: WebDriverWait, 
                                stop_check_callback=None) -> bool:
        """
        Fill in the Job Candidate Form - Houston West
        
        Returns:
            bool: Success status
        """
        try:
            self.logger.info("Starting Job Candidate Form filling process")
            
            # Wait for form to be present
            wait.until(EC.presence_of_element_located((By.ID, "gform_55")))
            
            # Track filled fields
            filled_fields = {}
            
            # 1. Fill First Name (input_55_1_3)
            if self._fill_field_by_multiple_strategies(
                "First Name", 
                user_profile.get('first_name', ''),
                [
                    (By.ID, "input_55_1_3"),
                    (By.NAME, "input_1.3"),
                    (By.CSS_SELECTOR, "input[placeholder='First Name']"),
                    (By.CSS_SELECTOR, "#input_55_1_3_container input")
                ],
                wait
            ):
                filled_fields['first_name'] = True
                
            # 2. Fill Last Name (input_55_1_6)
            if self._fill_field_by_multiple_strategies(
                "Last Name",
                user_profile.get('last_name', ''),
                [
                    (By.ID, "input_55_1_6"),
                    (By.NAME, "input_1.6"),
                    (By.CSS_SELECTOR, "input[placeholder='Last Name']"),
                    (By.CSS_SELECTOR, "#input_55_1_6_container input")
                ],
                wait
            ):
                filled_fields['last_name'] = True
                
            # 3. Fill Email (input_55_2)
            if self._fill_field_by_multiple_strategies(
                "Email",
                user_profile.get('email', ''),
                [
                    (By.ID, "input_55_2"),
                    (By.NAME, "input_2"),
                    (By.CSS_SELECTOR, "#field_55_2 input[type='email']"),
                    (By.CSS_SELECTOR, "input[type='email'].medium")
                ],
                wait
            ):
                filled_fields['email'] = True
                
            # 4. Fill Phone (input_55_3)
            if self._fill_field_by_multiple_strategies(
                "Phone",
                user_profile.get('phone', ''),
                [
                    (By.ID, "input_55_3"),
                    (By.NAME, "input_3"),
                    (By.CSS_SELECTOR, "#field_55_3 input[type='tel']"),
                    (By.CSS_SELECTOR, "input[type='tel'].medium")
                ],
                wait
            ):
                filled_fields['phone'] = True
                
            # 5. Fill "What type of job are you looking for?" field
            # Use the industry from job_board or default to "Manufacturing"
            industry = job_board.get('industry', 'Manufacturing')
            job_type_text = f"{industry} - Full-time opportunities"
            
            if self._fill_field_by_multiple_strategies(
                "Job Type",
                job_type_text,
                [
                    (By.ID, "input_55_5"),  # Try the specific ID first
                    (By.NAME, "input_5"),
                    (By.XPATH, "//label[contains(text(), 'What type of job')]/following::textarea[1]"),
                    (By.XPATH, "//label[contains(text(), 'What type of job')]/following::input[1]"),
                    (By.CSS_SELECTOR, "#field_55_5 textarea"),
                    (By.CSS_SELECTOR, "#field_55_5 input"),
                    (By.CSS_SELECTOR, "textarea.large"),
                    (By.XPATH, "//p[contains(text(), 'Full-time, part-time')]/preceding::textarea[1]"),
                    (By.XPATH, "//p[contains(text(), 'Full-time, part-time')]/preceding::input[1]")
                ],
                wait
            ):
                filled_fields['job_type'] = True
                
            # 6. Upload Resume if available
            if user_profile.get('resume_path'):
                if self._upload_resume(user_profile['resume_path'], wait):
                    filled_fields['resume'] = True
                    self.logger.info("Resume uploaded successfully")
                else:
                    self.logger.warning("Failed to upload resume")
            else:
                self.logger.info("No resume path provided, skipping upload")
                
            # Check for stop signal
            if stop_check_callback and stop_check_callback():
                return False
                
            # Log summary
            self.logger.info(f"Form filling complete. Filled fields: {list(filled_fields.keys())}")
            
            # Check if minimum fields were filled
            required = ['first_name', 'last_name', 'email', 'phone']
            missing = [f for f in required if f not in filled_fields]
            
            if missing:
                self.logger.error(f"Missing required fields: {missing}")
                return len(missing) <= 1  # Allow if only 1 field is missing
                
            return True
            
        except Exception as e:
            self.logger.error(f"Error filling job candidate form: {str(e)}")
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
                    EC.presence_of_element_located((selector_type, selector_value))
                )
                
                # Check if visible and enabled
                if element.is_displayed() and element.is_enabled():
                    # Scroll into view
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
                    time.sleep(0.5)
                    
                    # Clear and fill
                    element.clear()
                    element.send_keys(value)
                    
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
        
    def _upload_resume(self, resume_path: str, wait: WebDriverWait) -> bool:
        """
        Upload resume file
        
        Returns:
            bool: Success status
        """
        try:
            self.logger.info(f"Attempting to upload resume: {resume_path}")
            
            # Check if file exists
            if not os.path.exists(resume_path):
                self.logger.error(f"Resume file not found: {resume_path}")
                return False
                
            # Get absolute path
            abs_path = os.path.abspath(resume_path)
            
            # Look for the file input button or input field
            file_selectors = [
                (By.ID, "input_55_6"),  # Try specific Gravity Forms file input ID
                (By.NAME, "input_6"),
                (By.CSS_SELECTOR, "#field_55_6 input[type='file']"),
                (By.CSS_SELECTOR, "input[type='file']"),
                (By.XPATH, "//input[@type='file']"),
                (By.XPATH, "//label[contains(text(), 'Upload Your Resume')]/following::input[@type='file'][1]"),
                (By.XPATH, "//button[contains(text(), 'Choose File')]/../input[@type='file']"),
                (By.CSS_SELECTOR, "input[accept*='.pdf']"),
                (By.CSS_SELECTOR, "input[accept*='.doc']")
            ]
            
            for selector_type, selector_value in file_selectors:
                try:
                    # Find file input elements
                    elements = self.driver.find_elements(selector_type, selector_value)
                    
                    for element in elements:
                        try:
                            # Make element visible if hidden
                            self.driver.execute_script(
                                "arguments[0].style.display = 'block'; "
                                "arguments[0].style.visibility = 'visible';",
                                element
                            )
                            
                            # Send file path
                            element.send_keys(abs_path)
                            
                            # Wait a moment for upload to process
                            time.sleep(2)
                            
                            # Check if file was accepted
                            if element.get_attribute('value'):
                                self.logger.info("Resume uploaded successfully")
                                return True
                                
                        except Exception as e:
                            self.logger.debug(f"Failed to upload with element: {str(e)}")
                            continue
                            
                except Exception as e:
                    self.logger.debug(f"Error finding file input with {selector_type}:{selector_value} - {str(e)}")
                    continue
                    
            self.logger.warning("Could not find file upload input")
            return False
            
        except Exception as e:
            self.logger.error(f"Error uploading resume: {str(e)}")
            return False
            
    def _submit_form(self, wait: WebDriverWait) -> bool:
        """
        Submit the application form with Gravity Forms compatibility
        
        Returns:
            bool: Success status
        """
        try:
            self.logger.info("Looking for submit button")
            
            # First, trigger any field validation
            self._trigger_form_validation()
            
            # Scroll to bottom to ensure submit button is visible
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(1)
            
            # Try to find and click the submit button
            submit_clicked = False
            
            # Method 1: Direct approach with proper Gravity Forms handling
            try:
                submit_button = wait.until(
                    EC.element_to_be_clickable((By.ID, "gform_submit_button_55"))
                )
                
                # Remove any disabled state
                self.driver.execute_script("""
                    var btn = arguments[0];
                    btn.disabled = false;
                    btn.classList.remove('disabled');
                    btn.removeAttribute('disabled');
                """, submit_button)
                
                # Trigger Gravity Forms submission properly
                self.driver.execute_script("""
                    // Set form as submitting
                    window['gf_submitting_55'] = false;
                    
                    // Get the form
                    var form = document.getElementById('gform_55');
                    
                    // Set submission flag
                    var submitInput = form.querySelector('input[name="is_submit_55"]');
                    if (submitInput) {
                        submitInput.value = '1';
                    }
                    
                    // Clear any validation errors
                    var wrapper = document.getElementById('gform_wrapper_55');
                    if (wrapper) {
                        wrapper.classList.remove('gform_validation_error');
                    }
                    
                    // Remove validation messages
                    var validationMessages = form.querySelectorAll('.validation_message');
                    validationMessages.forEach(function(msg) {
                        msg.style.display = 'none';
                    });
                    
                    // Now trigger the submission
                    if (typeof gform !== 'undefined' && gform.submission) {
                        gform.submission.handleButtonClick(arguments[0]);
                    } else {
                        // Fallback: direct form submission
                        jQuery(form).trigger('submit', [true]);
                    }
                """, submit_button)
                
                submit_clicked = True
                self.logger.info("Triggered Gravity Forms submission")
                
            except Exception as e:
                self.logger.warning(f"Primary submission method failed: {str(e)}")
                
                # Method 2: Alternative submission approach
                try:
                    self.driver.execute_script("""
                        var form = document.getElementById('gform_55');
                        if (form) {
                            // Remove any blocking overlays
                            var overlays = document.querySelectorAll('.gform_ajax_spinner, .blockUI');
                            overlays.forEach(function(el) { el.remove(); });
                            
                            // Submit using jQuery if available
                            if (typeof jQuery !== 'undefined') {
                                jQuery(form).submit();
                            } else {
                                form.submit();
                            }
                        }
                    """)
                    submit_clicked = True
                    self.logger.info("Submitted form using alternative method")
                except Exception as e2:
                    self.logger.error(f"Alternative submission also failed: {str(e2)}")
            
            if not submit_clicked:
                return False
                
            # Wait for submission to process
            self.logger.info("Waiting for form submission to process...")
            time.sleep(3)
            
            # Check for AJAX submission completion
            ajax_complete = self.driver.execute_script("""
                return typeof window['gf_submitting_55'] === 'undefined' || 
                       window['gf_submitting_55'] === false;
            """)
            
            if not ajax_complete:
                self.logger.info("Waiting for AJAX submission to complete...")
                time.sleep(5)
            
            # Check for success indicators
            return self._check_submission_success()
            
        except Exception as e:
            self.logger.error(f"Error submitting form: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return False

    def _trigger_form_validation(self):
        """Trigger Gravity Forms field validation"""
        try:
            self.driver.execute_script("""
                // Trigger change events on all form fields to ensure validation
                var form = document.getElementById('gform_55');
                if (form) {
                    var inputs = form.querySelectorAll('input, textarea, select');
                    inputs.forEach(function(input) {
                        var event = new Event('change', { bubbles: true });
                        input.dispatchEvent(event);
                    });
                }
            """)
            time.sleep(0.5)
        except:
            pass

    def _check_submission_success(self) -> bool:
        """Enhanced success checking for Gravity Forms"""
        try:
            # Check for confirmation message
            confirmation_selectors = [
                ".gform_confirmation_message",
                "#gform_confirmation_message_55",
                ".gform_confirmation_wrapper",
                "[id^='gform_confirmation_']"
            ]
            
            for selector in confirmation_selectors:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if elements and elements[0].is_displayed():
                    self.logger.info(f"Found confirmation element: {selector}")
                    return True
            
            # Check page content
            page_source = self.driver.page_source.lower()
            success_indicators = [
                "thank you",
                "thanks",
                "success",
                "received",
                "submitted",
                "confirmation",
                "we'll be in touch",
                "application received",
                "appreciate your interest"
            ]
            
            for indicator in success_indicators:
                if indicator in page_source:
                    self.logger.info(f"Found success indicator: '{indicator}'")
                    return True
            
            # Check if form is gone
            try:
                form = self.driver.find_element(By.ID, "gform_55")
                # Form still exists, check if it has been replaced with confirmation
                wrapper = self.driver.find_element(By.ID, "gform_wrapper_55")
                wrapper_html = wrapper.get_attribute('innerHTML').lower()
                if 'confirmation' in wrapper_html or 'thank you' in wrapper_html:
                    return True
            except:
                # Form is gone, likely submitted
                self.logger.info("Form no longer present, assuming success")
                return True
                
            return False
            
        except Exception as e:
            self.logger.error(f"Error checking submission success: {str(e)}")
            return False