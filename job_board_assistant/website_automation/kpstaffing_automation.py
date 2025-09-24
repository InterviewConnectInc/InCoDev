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
from typing import Dict, Tuple

class KPStaffingAutomation:
    """Fast KP Staffing automation - optimized for speed"""
    
    HANDLES_SITE = "KP Staffing"
    
    def __init__(self):
        self.name = "KP Staffing Automation"
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
            self.logger.info(f"Starting KP Staffing submission for {user_profile.get('email', 'Unknown user')}")
            
            url = job_board.get('site_url', job_board.get('url'))
            if not url:
                return False, "No URL provided"
                
            self.driver = self._create_driver()
            self.driver.get(url)
            
            # Fast wait - 3 seconds max
            wait = WebDriverWait(self.driver, 3)
            
            # Fill form quickly
            if self._fill_form_fast(user_profile, wait):
                if self._submit_fast(wait):
                    self.logger.info("Application submitted successfully")
                    return True, "Application submitted successfully to KP Staffing"
            
            return False, "Failed to complete form"
                
        except Exception as e:
            self.logger.error(f"Error: {str(e)}")
            return False, f"Error: {str(e)}"
        finally:
            if self.driver:
                self.driver.quit()
                    
    def _fill_form_fast(self, user_profile: Dict, wait: WebDriverWait) -> bool:
        try:
            # First Name - exact ID from form
            self._fill_field(wait, "#input_20_1_3", user_profile.get('first_name', ''))
            
            # Last Name - exact ID from form
            self._fill_field(wait, "#input_20_1_6", user_profile.get('last_name', ''))
            
            # Email - exact ID from form
            self._fill_field(wait, "#input_20_3", user_profile.get('email', ''))
            
            # Phone - exact ID from form
            self._fill_field(wait, "#input_20_4", user_profile.get('phone', ''))
            
            # Postal Code - exact ID from form
            zip_code = user_profile.get('zip_code', '')
            if zip_code:
                self._fill_field(wait, "#input_20_5_5", zip_code)
            
            # Preferred Language - exact ID (defaults to English)
            self._select_dropdown(wait, "#input_20_11", "English")
            
            # How did you hear - exact ID, select Google
            self._select_dropdown(wait, "#input_20_6", "Google")
            
            # Work type - exact ID, select General Warehouse
            self._select_dropdown(wait, "#input_20_14", "General Warehouse")
            
            # Consent checkbox - exact ID
            self._check_box(wait, "#input_20_7_1")
            
            # Resume upload - exact ID
            resume_path = user_profile.get('resume_path')
            if resume_path and os.path.exists(resume_path):
                self._upload_file(wait, "#input_20_13", resume_path)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Form fill error: {str(e)}")
            return False
            
    def _fill_field(self, wait: WebDriverWait, selector: str, value: str, required: bool = True) -> bool:
        if not value:
            return not required
            
        try:
            element = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
            element.clear()
            element.send_keys(value)
            return True
        except:
            if required:
                self.logger.error(f"Required field not found: {selector}")
            return False
            
    def _select_dropdown(self, wait: WebDriverWait, selector: str, option_text: str, required: bool = True) -> bool:
        try:
            element = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
            select = Select(element)
            
            # Try exact match first
            try:
                select.select_by_visible_text(option_text)
                return True
            except:
                # Try partial match
                for option in select.options:
                    if option_text.lower() in option.text.lower():
                        select.select_by_visible_text(option.text)
                        return True
                        
                # Keep default if nothing found
                return not required
                
        except:
            if required:
                self.logger.error(f"Required dropdown not found: {selector}")
            return False
            
    def _check_box(self, wait: WebDriverWait, selector: str) -> bool:
        try:
            element = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
            if not element.is_selected():
                element.click()
            return True
        except:
            self.logger.error(f"Checkbox not found: {selector}")
            return False
            
    def _upload_file(self, wait: WebDriverWait, selector: str, file_path: str) -> bool:
        try:
            element = self.driver.find_element(By.CSS_SELECTOR, selector)
            element.send_keys(os.path.abspath(file_path))
            return True
        except:
            self.logger.error("File upload failed")
            return False
            
    def _submit_fast(self, wait: WebDriverWait) -> bool:
        try:
            # Submit button - exact ID from form
            submit_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "#gform_submit_button_20")))
            submit_button.click()
            
            # Quick success check
            time.sleep(2)
            page_source = self.driver.page_source.lower()
            return any(indicator in page_source for indicator in ['success', 'thank', 'submitted', 'received'])
            
        except:
            self.logger.error("Submit failed")
            return False