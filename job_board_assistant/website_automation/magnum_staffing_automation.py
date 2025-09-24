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
from typing import Dict, Optional, Tuple
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class MagnumStaffingAutomation:
    """
    Optimized Magnum Staffing automation for maximum speed.
    """
    
    HANDLES_SITE = "Magnum Staffing"
    
    def __init__(self):
        self.name = "Magnum Staffing Automation"
        self.board_name = "Magnum Staffing"
        self.base_url = None
        self.driver = None
        self.logger = self._setup_logger()
        self.submission_timeout = 60
        
    def _setup_logger(self) -> logging.Logger:
        """Setup logging for the automation"""
        logger = logging.getLogger(self.name)
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            
        return logger
        
    def _create_driver(self) -> webdriver.Chrome:
        """Create optimized Chrome driver for speed"""
        chrome_options = Options()
        
        # Performance optimizations
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # Speed optimizations
        chrome_options.add_argument("--disable-images")
        chrome_options.add_argument("--disable-css")
        chrome_options.add_argument("--disable-javascript")
        chrome_options.add_argument("--disable-plugins")
        chrome_options.add_argument("--disable-animations")
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--disable-features=VizDisplayCompositor")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-first-run")
        chrome_options.add_argument("--disable-default-apps")
        chrome_options.add_argument("--disable-extensions")
        
        # Page load strategy
        chrome_options.page_load_strategy = 'eager'
        
        # Disable logging for speed
        chrome_options.add_argument("--log-level=3")
        chrome_options.add_argument("--silent")
        
        # Prefs for speed
        prefs = {
            "profile.default_content_setting_values": {
                "images": 2,
                "plugins": 2,
                "popups": 2,
                "geolocation": 2,
                "notifications": 2,
                "media_stream": 2,
                "media_stream_mic": 2,
                "media_stream_camera": 2,
                "protocol_handlers": 2,
                "ppapi_broker": 2,
                "automatic_downloads": 2,
                "midi_sysex": 2,
                "push_messaging": 2,
                "ssl_cert_decisions": 2,
                "metro_switch_to_desktop": 2,
                "protected_media_identifier": 2,
                "app_banner": 2,
                "site_engagement": 2,
                "durable_storage": 2
            }
        }
        chrome_options.add_experimental_option("prefs", prefs)
        
        try:
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # Set timeouts
            driver.implicitly_wait(2)
            driver.set_page_load_timeout(30)
            
            # Hide webdriver detection
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            return driver
            
        except Exception as e:
            self.logger.error(f"Failed to create Chrome driver: {str(e)}")
            raise
            
    def submit_application(self, job_board: Dict, user_profile: Dict, 
                         stop_check_callback=None) -> Tuple[bool, str]:
        """
        Optimized submit application for maximum speed
        """
        try:
            self.logger.info(f"Starting Magnum Staffing submission")
            
            # Extract URL
            self.base_url = job_board.get('site_url', job_board.get('url', job_board.get('website_url')))
            if not self.base_url:
                return False, "No URL provided"
                
            # Create driver
            self.driver = self._create_driver()
            
            # Navigate to form
            try:
                self.driver.get(self.base_url)
            except TimeoutException:
                self.logger.info("Page load timeout - continuing anyway")
            
            # Wait for page to stabilize
            time.sleep(3)
            
            # Minimal wait
            wait = WebDriverWait(self.driver, 10)
            
            # Fill form with optimized method
            form_data = self._prepare_form_data(user_profile)
            success = self._fill_form_fast(form_data, wait)
            
            if not success:
                return False, "Failed to fill form"
                
            # Submit immediately
            submitted = self._submit_form_fast(wait)
            
            if submitted:
                return True, "Application submitted successfully"
            else:
                return False, "Failed to submit form"
                
        except Exception as e:
            self.logger.error(f"Error: {str(e)}")
            return False, f"Error: {str(e)}"
            
        finally:
            if self.driver:
                try:
                    self.driver.quit()
                except:
                    pass
    
    def _prepare_form_data(self, user_profile: Dict) -> Dict:
        """Pre-process form data for speed"""
        return {
            'firstName': user_profile.get('first_name', ''),
            'lastName': user_profile.get('last_name', ''),
            'phone': user_profile.get('phone', ''),
            'email': user_profile.get('email', ''),
            'address': f"{user_profile.get('street_address', '')} {user_profile.get('address_2', '')}".strip() or "123 Main St",
            'city': user_profile.get('city', ''),
            'state': user_profile.get('state', ''),
            'zip': user_profile.get('zip_code', ''),
            'desiredJob': "Logistics, Supply Chain, Operations, or Management roles. Thanks."
        }
    
    def _fill_form_fast(self, form_data: Dict, wait: WebDriverWait) -> bool:
        """
        Ultra-fast form filling using JavaScript injection
        """
        try:
            # Wait for iframe to be present
            self.logger.info("Waiting for iframe...")
            iframe = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "iframe[src*='atswebcandidate']"))
            )
            
            # Switch to iframe
            self.driver.switch_to.frame(iframe)
            self.logger.info("Switched to iframe")
            
            # Now wait for form elements inside the iframe
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "input")))
            
            # JavaScript to fill all fields at once
            js_fill_script = """
            function fillForm(data) {
                // Function to set value with events
                function setValue(element, value) {
                    if (!element || !value) return;
                    
                    element.value = value;
                    element.dispatchEvent(new Event('input', { bubbles: true }));
                    element.dispatchEvent(new Event('change', { bubbles: true }));
                    element.dispatchEvent(new Event('blur', { bubbles: true }));
                }
                
                // Try multiple selectors for each field
                const fieldSelectors = {
                    firstName: ['input[name="firstName"]', 'input[name="FirstName"]', 'input[id="firstName"]', 'input[placeholder*="First"]'],
                    lastName: ['input[name="lastName"]', 'input[name="LastName"]', 'input[id="lastName"]', 'input[placeholder*="Last"]'],
                    phone: ['input[name="phone"]', 'input[type="tel"]', 'input[id="phone"]', 'input[placeholder*="Phone"]'],
                    email: ['input[name="email"]', 'input[type="email"]', 'input[id="email"]', 'input[placeholder*="Email"]'],
                    address: ['input[name="address"]', 'input[name="Address"]', 'input[id="address"]', 'input[placeholder*="Address"]'],
                    city: ['input[name="city"]', 'input[name="City"]', 'input[id="city"]', 'input[placeholder*="City"]'],
                    state: ['input[name="state"]', 'select[name="state"]', 'input[id="state"]', 'input[placeholder*="State"]'],
                    zip: ['input[name="zip"]', 'input[name="zipCode"]', 'input[id="zip"]', 'input[placeholder*="Zip"]'],
                    desiredJob: ['input[name="desiredJob"]', 'textarea[name="desiredJob"]', 'input[name*="job"]', 'textarea[name*="job"]']
                };
                
                let filledCount = 0;
                
                // Fill each field
                for (const [fieldName, selectors] of Object.entries(fieldSelectors)) {
                    if (!data[fieldName]) continue;
                    
                    let filled = false;
                    for (const selector of selectors) {
                        try {
                            const element = document.querySelector(selector);
                            if (element) {
                                if (element.tagName === 'SELECT') {
                                    // Handle select elements
                                    const option = Array.from(element.options).find(opt => 
                                        opt.text.includes(data[fieldName]) || opt.value === data[fieldName]
                                    );
                                    if (option) {
                                        element.value = option.value;
                                        element.dispatchEvent(new Event('change', { bubbles: true }));
                                    }
                                } else {
                                    setValue(element, data[fieldName]);
                                }
                                filled = true;
                                filledCount++;
                                break;
                            }
                        } catch (e) {
                            continue;
                        }
                    }
                }
                
                return filledCount;
            }
            
            return fillForm(arguments[0]);
            """
            
            # Execute the fill script
            filled_count = self.driver.execute_script(js_fill_script, form_data)
            self.logger.info(f"Filled {filled_count} fields via JavaScript")
            
            # Quick validation
            if filled_count >= 4:
                return True
            
            # Fallback: Try direct element access for critical fields only
            critical_fields = ['firstName', 'lastName', 'phone', 'email']
            for field_name in critical_fields:
                if field_name in form_data and form_data[field_name]:
                    try:
                        element = self.driver.find_element(By.NAME, field_name)
                        element.clear()
                        element.send_keys(form_data[field_name])
                    except:
                        pass
            
            return True
            
        except Exception as e:
            self.logger.error(f"Fast fill error: {str(e)}")
            # Make sure to switch back to main content if error occurs
            try:
                self.driver.switch_to.default_content()
            except:
                pass
            return False
    
    def _submit_form_fast(self, wait: WebDriverWait) -> bool:
        """
        Fast form submission
        """
        try:
            # Make sure we're still in the iframe
            # JavaScript to find and click submit button
            js_submit_script = """
            function submitForm() {
                // Try multiple ways to submit
                const submitSelectors = [
                    'input[type="submit"]',
                    'button[type="submit"]',
                    'input[value*="Submit"]',
                    'button:contains("Submit")',
                    '#submit',
                    '.submit-btn',
                    'button.btn'
                ];
                
                // Try selectors
                for (const selector of submitSelectors) {
                    try {
                        const element = document.querySelector(selector);
                        if (element && (element.offsetWidth > 0 || element.offsetHeight > 0)) {
                            element.click();
                            return true;
                        }
                    } catch (e) {
                        continue;
                    }
                }
                
                // Try finding by text content
                const buttons = document.querySelectorAll('button, input[type="button"], input[type="submit"]');
                for (const btn of buttons) {
                    const text = (btn.textContent || btn.value || '').toLowerCase();
                    if (text.includes('submit')) {
                        btn.click();
                        return true;
                    }
                }
                
                // Last resort - submit first form
                const form = document.querySelector('form');
                if (form) {
                    form.submit();
                    return true;
                }
                
                return false;
            }
            
            return submitForm();
            """
            
            # Try JavaScript submission first
            submitted = self.driver.execute_script(js_submit_script)
            
            if submitted:
                self.logger.info("Form submitted via JavaScript")
                time.sleep(2)
                return True
            
            # Fallback: Traditional selenium click
            try:
                submit_btn = wait.until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "input[type='submit'], button[type='submit']"))
                )
                submit_btn.click()
                self.logger.info("Form submitted via Selenium click")
                return True
            except:
                pass
            
            # Switch back to main content after submission attempt
            try:
                self.driver.switch_to.default_content()
            except:
                pass
            
            return False
            
        except Exception as e:
            self.logger.error(f"Submit error: {str(e)}")
            # Make sure to switch back to main content
            try:
                self.driver.switch_to.default_content()
            except:
                pass
            return False