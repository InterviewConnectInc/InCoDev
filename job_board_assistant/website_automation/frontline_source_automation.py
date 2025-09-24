import time
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
from typing import Dict, Tuple

class FrontlineSourceAutomation:
    """Fast Frontline Source Group automation - optimized for speed"""
    
    HANDLES_SITE = "Frontline Source Group"
    
    def __init__(self):
        self.name = "Frontline Source Group Automation"
        self.driver = None
        self.logger = self._setup_logger()
        
    def _setup_logger(self) -> logging.Logger:
        logger = logging.getLogger(self.name)
        logger.setLevel(logging.INFO)
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        return logger
        
    def _create_driver(self) -> webdriver.Chrome:
        chrome_options = Options()
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument("--start-maximized")
        
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        return driver
            
    def submit_application(self, job_board: Dict, user_profile: Dict, stop_check_callback=None) -> Tuple[bool, str]:
        try:
            self.logger.info(f"Starting Frontline Source Group submission for {user_profile.get('email', 'Unknown user')}")
            
            url = job_board.get('site_url', job_board.get('url'))
            if not url:
                return False, "No URL provided"
                
            self.driver = self._create_driver()
            self.driver.get(url)
            
            # Fast wait - 0 seconds max
            wait = WebDriverWait(self.driver, 0)
            
            # Fill form quickly
            if self._fill_form_fast(user_profile, wait):
                if self._submit_fast(wait):
                    self.logger.info("Application submitted successfully")
                    return True, "Application submitted successfully to Frontline Source Group"
            
            return False, "Failed to complete form"
                
        except Exception as e:
            self.logger.error(f"Error: {str(e)}")
            return False, f"Error: {str(e)}"
        finally:
            if self.driver:
                self.driver.quit()
                    
    def _fill_form_fast(self, user_profile: Dict, wait: WebDriverWait) -> bool:
        try:
            # Wait for form to be present
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "form")))
            
            # First Name - multiple strategies
            first_name = user_profile.get('first_name', '')
            self._fill_field_strategies(wait, first_name, [
                "input[name*='first']",
                "input[id*='first']",
                "input[placeholder*='First']",
                "#firstName",
                "#first_name",
                "#fname"
            ])
            
            # Last Name - multiple strategies
            last_name = user_profile.get('last_name', '')
            self._fill_field_strategies(wait, last_name, [
                "input[name*='last']",
                "input[id*='last']",
                "input[placeholder*='Last']",
                "#lastName",
                "#last_name",
                "#lname"
            ])
            
            # Email - multiple strategies
            email = user_profile.get('email', '')
            self._fill_field_strategies(wait, email, [
                "input[type='email']",
                "input[name*='email']",
                "input[id*='email']",
                "#email",
                "#emailAddress"
            ])
            
            # Phone - multiple strategies
            phone = user_profile.get('phone', '')
            self._fill_field_strategies(wait, phone, [
                "input[type='tel']",
                "input[name*='phone']",
                "input[id*='phone']",
                "#phone",
                "#phoneNumber",
                "#mobile"
            ])
            
            # Resume upload
            resume_path = user_profile.get('resume_path')
            if resume_path and os.path.exists(resume_path):
                self._upload_file_strategies(wait, resume_path, [
                    "input[type='file']",
                    "input[name*='resume']",
                    "input[id*='resume']",
                    "input[name*='file']",
                    "#resume",
                    "#file"
                ])
            
            return True
            
        except Exception as e:
            self.logger.error(f"Form fill error: {str(e)}")
            return False
            
    def _fill_field_strategies(self, wait: WebDriverWait, value: str, selectors: list) -> bool:
        if not value:
            return False
            
        for selector in selectors:
            try:
                element = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
                if element.is_displayed() and element.is_enabled():
                    element.clear()
                    element.send_keys(value)
                    
                    # Trigger events
                    self.driver.execute_script("""
                        arguments[0].dispatchEvent(new Event('input', {bubbles: true}));
                        arguments[0].dispatchEvent(new Event('change', {bubbles: true}));
                    """, element)
                    
                    if element.get_attribute('value'):
                        self.logger.info(f"Filled field using: {selector}")
                        return True
            except:
                continue
                
        self.logger.warning(f"Could not fill field with value: {value}")
        return False
            
    def _upload_file_strategies(self, wait: WebDriverWait, file_path: str, selectors: list) -> bool:
        abs_path = os.path.abspath(file_path)
        
        for selector in selectors:
            try:
                element = self.driver.find_element(By.CSS_SELECTOR, selector)
                
                # Make visible if hidden
                self.driver.execute_script("""
                    arguments[0].style.display = 'block';
                    arguments[0].style.visibility = 'visible';
                    arguments[0].style.opacity = '1';
                """, element)
                
                element.send_keys(abs_path)
                time.sleep(1)
                
                if element.get_attribute('value'):
                    self.logger.info(f"File uploaded using: {selector}")
                    return True
            except:
                continue
                
        self.logger.warning("Could not upload file")
        return False
            
    def _submit_fast(self, wait: WebDriverWait) -> bool:
        try:
            # Scroll to bottom
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(0.5)
            
            # Try multiple submit button strategies
            submit_selectors = [
                "input[type='submit']",
                "button[type='submit']",
                "button[name*='submit']",
                "#submit",
                "#submitBtn",
                ".submit-btn",
                ".submit-button"
            ]
            
            for selector in submit_selectors:
                try:
                    submit_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
                    
                    # Remove disabled state
                    self.driver.execute_script("""
                        arguments[0].disabled = false;
                        arguments[0].classList.remove('disabled');
                    """, submit_button)
                    
                    # Click using JavaScript
                    self.driver.execute_script("arguments[0].click();", submit_button)
                    
                    self.logger.info(f"Submit clicked using: {selector}")
                    break
                except:
                    continue
            
            # Quick success check
            time.sleep(3)
            return self._check_success_fast()
            
        except Exception as e:
            self.logger.error(f"Submit failed: {str(e)}")
            return False
            
    def _check_success_fast(self) -> bool:
        try:
            # Check URL for success indicators
            current_url = self.driver.current_url.lower()
            url_indicators = ['thank', 'success', 'submitted', 'confirmation', 'complete']
            
            for indicator in url_indicators:
                if indicator in current_url:
                    self.logger.info(f"Success URL indicator: {indicator}")
                    return True
            
            # Check page content
            page_source = self.driver.page_source.lower()
            content_indicators = [
                'thank you', 'thanks', 'success', 'submitted', 'received',
                'application received', 'confirmation', 'message sent',
                'form submitted', 'successfully submitted'
            ]
            
            for indicator in content_indicators:
                if indicator in page_source:
                    self.logger.info(f"Success content indicator: {indicator}")
                    return True
            
            # Check if form disappeared
            try:
                forms = self.driver.find_elements(By.TAG_NAME, "form")
                visible_forms = [f for f in forms if f.is_displayed()]
                if not visible_forms:
                    self.logger.info("Form disappeared - assuming success")
                    return True
            except:
                pass
                
            return False
            
        except Exception as e:
            self.logger.error(f"Success check failed: {str(e)}")
            return False