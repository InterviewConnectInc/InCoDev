# dice_assistant/dice_step_8.py

import time
import re
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException
from selenium.webdriver.common.action_chains import ActionChains

def step_8_click_next(driver):
    """
    Step 8: Click 'Apply now' button on the job detail page
    
    Args:
        driver: Selenium WebDriver instance
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        print("\n" + "="*60)
        print("STEP 8: Clicking Apply button on job detail page")
        print("="*60)
        
        # Wait for page to load
        print("[STEP 8] Waiting for page to load...")
        time.sleep(5)
        
        current_url = driver.current_url
        print(f"[STEP 8] Current URL: {current_url}")
        
        # Strategy 1: Find the apply-button-wc custom element
        print("\n[STEP 8] Strategy 1: Looking for apply-button-wc custom element...")
        apply_success = _handle_custom_apply_button(driver)
        
        if apply_success:
            print("[STEP 8] SUCCESS: Apply button handled")
            return True
        
        # Strategy 2: Look inside the applyButton div
        print("\n[STEP 8] Strategy 2: Looking inside applyButton div...")
        apply_button = _find_apply_button_in_container(driver)
        
        if apply_button:
            success = _click_element_safely(driver, apply_button)
            if success:
                print("[STEP 8] SUCCESS: Apply button clicked")
                return True
        
        # Strategy 3: Extract URL from job-id and navigate directly
        print("\n[STEP 8] Strategy 3: Extracting job ID and constructing apply URL...")
        apply_url = _extract_and_construct_apply_url(driver)
        
        if apply_url:
            print(f"[STEP 8] Navigating to apply URL: {apply_url}")
            driver.get(apply_url)
            time.sleep(3)
            
            new_url = driver.current_url
            if new_url != current_url:
                print("[STEP 8] SUCCESS: Navigated to application page")
                return True
        
        print("[STEP 8] ERROR: Could not handle Apply button")
        return False
        
    except Exception as e:
        print(f"[STEP 8 ERROR] Unexpected error: {str(e)}")
        print(f"[STEP 8 ERROR] Error type: {type(e).__name__}")
        if hasattr(e, '__traceback__'):
            import traceback
            print(f"[STEP 8 ERROR] Traceback: {traceback.format_exc()}")
        return False

def _handle_custom_apply_button(driver):
    """Handle the apply-button-wc custom web component"""
    try:
        # Wait for the custom element to be present
        wait = WebDriverWait(driver, 10)
        apply_element = wait.until(
            EC.presence_of_element_located((By.TAG_NAME, "apply-button-wc"))
        )
        
        print("[STEP 8] Found apply-button-wc element")
        
        # Get job information from the element
        job_id = apply_element.get_attribute('job-id')
        job_title = apply_element.get_attribute('job-title')
        print(f"[STEP 8] Job ID: {job_id}")
        print(f"[STEP 8] Job Title: {job_title}")
        
        # Try to find button inside the custom element (might be in shadow DOM)
        # First, try regular DOM
        try:
            buttons_inside = apply_element.find_elements(By.TAG_NAME, "button")
            if buttons_inside:
                print(f"[STEP 8] Found {len(buttons_inside)} buttons inside apply-button-wc")
                for button in buttons_inside:
                    if button.is_displayed():
                        return _click_element_safely(driver, button)
        except:
            pass
        
        # Try to access shadow DOM if it exists
        try:
            shadow_root = driver.execute_script("return arguments[0].shadowRoot", apply_element)
            if shadow_root:
                print("[STEP 8] Found shadow root in apply-button-wc")
                # Look for button in shadow DOM
                shadow_buttons = driver.execute_script("""
                    var shadowRoot = arguments[0].shadowRoot;
                    if (shadowRoot) {
                        var buttons = shadowRoot.querySelectorAll('button');
                        if (buttons.length > 0) {
                            buttons[0].click();
                            return true;
                        }
                    }
                    return false;
                """, apply_element)
                
                if shadow_buttons:
                    print("[STEP 8] Clicked button in shadow DOM")
                    time.sleep(3)
                    return True
        except:
            pass
        
        # Try clicking the custom element itself
        print("[STEP 8] Attempting to click the apply-button-wc element directly...")
        return _click_element_safely(driver, apply_element)
        
    except TimeoutException:
        print("[STEP 8] Timeout waiting for apply-button-wc element")
    except Exception as e:
        print(f"[STEP 8] Error handling custom apply button: {str(e)}")
    
    return False

def _find_apply_button_in_container(driver):
    """Look for Apply button inside the applyButton div"""
    try:
        # Find the applyButton div
        apply_div = driver.find_element(By.ID, "applyButton")
        print("[STEP 8] Found applyButton div")
        
        # Look for any clickable elements inside
        clickable_elements = []
        
        # Check for buttons
        buttons = apply_div.find_elements(By.TAG_NAME, "button")
        clickable_elements.extend(buttons)
        
        # Check for links
        links = apply_div.find_elements(By.TAG_NAME, "a")
        clickable_elements.extend(links)
        
        # Check for any element with onclick
        onclick_elements = apply_div.find_elements(By.XPATH, ".//*[@onclick]")
        clickable_elements.extend(onclick_elements)
        
        print(f"[STEP 8] Found {len(clickable_elements)} clickable elements in applyButton div")
        
        # Try each clickable element
        for element in clickable_elements:
            if element.is_displayed():
                element_text = element.text.strip()
                element_tag = element.tag_name
                print(f"[STEP 8] Found {element_tag}: '{element_text}'")
                
                if 'apply' in element_text.lower() or not element_text:
                    return element
        
        # If no obvious apply button, return the first visible clickable element
        for element in clickable_elements:
            if element.is_displayed():
                return element
                
    except NoSuchElementException:
        print("[STEP 8] applyButton div not found")
    except Exception as e:
        print(f"[STEP 8] Error finding button in container: {str(e)}")
    
    return None

def _extract_and_construct_apply_url(driver):
    """Extract job ID and construct the apply URL"""
    try:
        # Get job ID from various sources
        job_id = None
        
        # Try from apply-button-wc
        try:
            apply_element = driver.find_element(By.TAG_NAME, "apply-button-wc")
            job_id = apply_element.get_attribute('job-id')
            print(f"[STEP 8] Got job ID from apply-button-wc: {job_id}")
        except:
            pass
        
        # Try from dhi-job-search-save-job
        if not job_id:
            try:
                save_element = driver.find_element(By.TAG_NAME, "dhi-job-search-save-job")
                job_id = save_element.get_attribute('job-id')
                print(f"[STEP 8] Got job ID from save element: {job_id}")
            except:
                pass
        
        # Try from URL
        if not job_id:
            current_url = driver.current_url
            job_id_match = re.search(r'/job-detail/([a-f0-9-]+)', current_url)
            if job_id_match:
                job_id = job_id_match.group(1)
                print(f"[STEP 8] Got job ID from URL: {job_id}")
        
        if job_id:
            # Construct apply URL (common patterns)
            base_url = driver.current_url.split('/job-detail/')[0]
            possible_urls = [
                f"{base_url}/apply/{job_id}",
                f"{base_url}/job-apply/{job_id}",
                f"{base_url}/apply?jobId={job_id}",
                f"https://www.dice.com/apply/{job_id}",
                f"https://www.dice.com/job-apply/{job_id}"
            ]
            
            # Return the first URL (we could try each one if needed)
            return possible_urls[0]
            
    except Exception as e:
        print(f"[STEP 8] Error extracting job ID: {str(e)}")
    
    return None

def _click_element_safely(driver, element):
    """Safely click an element using multiple methods"""
    try:
        # Scroll into view
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
        time.sleep(1)
        
        # Method 1: JavaScript click
        try:
            driver.execute_script("arguments[0].click();", element)
            print("[STEP 8] Clicked using JavaScript")
            time.sleep(3)
            return True
        except:
            pass
        
        # Method 2: Regular click
        try:
            element.click()
            print("[STEP 8] Clicked using regular click")
            time.sleep(3)
            return True
        except:
            pass
        
        # Method 3: Action chains
        try:
            ActionChains(driver).move_to_element(element).click().perform()
            print("[STEP 8] Clicked using action chains")
            time.sleep(3)
            return True
        except:
            pass
        
        # Method 4: Send Enter key
        try:
            element.send_keys('\n')
            print("[STEP 8] Sent Enter key")
            time.sleep(3)
            return True
        except:
            pass
            
    except Exception as e:
        print(f"[STEP 8] Error clicking element: {str(e)}")
    
    return False