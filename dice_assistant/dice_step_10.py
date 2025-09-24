# dice_assistant/dice_step_10.py

import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

def step_10_handle_confirmation_and_return(driver, return_to_search=True):
    """
    Step 10: Click Submit button and handle confirmation
    
    Args:
        driver: Selenium WebDriver instance
        return_to_search: Whether to return to search results for more applications
        
    Returns:
        dict: Application results with confirmation details
    """
    try:
        print("\n" + "="*60)
        print("STEP 10: Submitting application")
        print("="*60)
        
        # Wait for page to load
        print("[STEP 10] Waiting for review page to load...")
        time.sleep(3)
        
        current_url = driver.current_url
        print(f"[STEP 10] Current URL: {current_url}")
        
        # Verify we're on the review page
        if _verify_review_page(driver):
            print("[STEP 10] Confirmed on application review page")
        
        # Find and click the Submit button
        print("[STEP 10] Looking for Submit button...")
        submit_button = _find_submit_button(driver)
        
        if submit_button:
            print("[STEP 10] Found Submit button")
            
            # Scroll button into view
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", submit_button)
            time.sleep(1)
            
            # Click the button
            print("[STEP 10] Clicking Submit button...")
            success = _click_button_safely(driver, submit_button)
            
            if success:
                print("[STEP 10] Successfully clicked Submit button")
                
                # Wait for submission to process
                print("[STEP 10] Waiting for application submission to process...")
                time.sleep(5)
                
                # Check for confirmation
                confirmation_details = _check_confirmation(driver, current_url)
                
                result = {
                    'submission_confirmed': confirmation_details['confirmed'],
                    'confirmation_details': confirmation_details,
                    'return_navigation': False,
                    'ready_for_next_application': False
                }
                
                if confirmation_details['confirmed']:
                    print("[STEP 10] SUCCESS: Application submitted successfully!")
                    
                    if return_to_search:
                        print("[STEP 10] Attempting to return to job search...")
                        if _return_to_job_search(driver):
                            result['return_navigation'] = True
                            result['ready_for_next_application'] = True
                            print("[STEP 10] Ready for next application")
                else:
                    print("[STEP 10] WARNING: Could not confirm submission")
                
                return result
            else:
                print("[STEP 10] ERROR: Failed to click Submit button")
                return {'submission_confirmed': False, 'error': 'Failed to click Submit button'}
        else:
            print("[STEP 10] ERROR: Could not find Submit button")
            _debug_page_state(driver)
            return {'submission_confirmed': False, 'error': 'Submit button not found'}
            
    except Exception as e:
        print(f"[STEP 10 ERROR] Unexpected error: {str(e)}")
        print(f"[STEP 10 ERROR] Error type: {type(e).__name__}")
        if hasattr(e, '__traceback__'):
            import traceback
            print(f"[STEP 10 ERROR] Traceback: {traceback.format_exc()}")
        return {'submission_confirmed': False, 'error': str(e)}

def _verify_review_page(driver):
    """Verify we're on the review/final submission page"""
    try:
        # Check for review indicators
        page_text = driver.page_source.lower()
        review_indicators = ['review application', 'review your application', 'step 2 of 2']
        
        for indicator in review_indicators:
            if indicator in page_text:
                print(f"[STEP 10] Found review indicator: '{indicator}'")
                return True
        
        # Check for review section
        review_sections = driver.find_elements(By.CSS_SELECTOR, ".application-review-wrapper, .resume-review-section")
        if review_sections:
            print("[STEP 10] Found review section elements")
            return True
            
    except:
        pass
    
    return False

def _find_submit_button(driver):
    """Find the Submit button using multiple strategies"""
    
    # Strategy 1: Direct selectors based on the provided HTML
    selectors = [
        # Exact class match with Submit text
        "button.seds-button-primary.btn-next span:contains('Submit')",
        "button.btn-next span:contains('Submit')",
        
        # Button classes
        "button.seds-button-primary.btn-next",
        "button.btn-next",
        
        # In navigation area
        ".navigation-buttons button.seds-button-primary",
        ".navigation-buttons button.btn-next",
        
        # Generic Submit button
        "button:contains('Submit')",
        
        # Data attribute
        "button[data-v-866481c4]"
    ]
    
    # Try CSS selectors
    for selector in selectors:
        try:
            # Skip :contains for CSS
            if ':contains' in selector:
                continue
                
            buttons = driver.find_elements(By.CSS_SELECTOR, selector)
            for button in buttons:
                if button.is_displayed() and button.is_enabled():
                    # Check if it's a Submit button
                    button_text = button.text.strip()
                    
                    # Direct text match
                    if 'submit' in button_text.lower():
                        print(f"[STEP 10] Found Submit button using selector: {selector}")
                        return button
                    
                    # Check spans inside for Submit text
                    spans = button.find_elements(By.TAG_NAME, "span")
                    for span in spans:
                        if 'submit' in span.text.lower():
                            print(f"[STEP 10] Found Submit button via span text using selector: {selector}")
                            return button
                    
                    # If it's btn-next on review page, it's likely Submit
                    if 'btn-next' in button.get_attribute('class') and _verify_review_page(driver):
                        print(f"[STEP 10] Found btn-next on review page, assuming Submit")
                        return button
        except:
            continue
    
    # Strategy 2: XPath selectors
    xpath_selectors = [
        # Button containing Submit text
        "//button[contains(text(),'Submit')]",
        "//button[.//span[contains(text(),'Submit')]]",
        "//button[@class='seds-button-primary btn-next'][.//span[contains(text(),'Submit')]]",
        
        # Button in navigation area with Submit
        "//div[contains(@class,'navigation-buttons')]//button[.//span[contains(text(),'Submit')]]",
        
        # Any button with Submit in span
        "//button//span[contains(text(),'Submit')]/parent::button"
    ]
    
    for xpath in xpath_selectors:
        try:
            buttons = driver.find_elements(By.XPATH, xpath)
            for button in buttons:
                if button.is_displayed() and button.is_enabled():
                    print(f"[STEP 10] Found Submit button using XPath: {xpath}")
                    return button
        except:
            continue
    
    # Strategy 3: Wait for clickable Submit button
    try:
        wait = WebDriverWait(driver, 10)
        # Wait for button containing Submit text
        submit_button = wait.until(
            EC.element_to_be_clickable((By.XPATH, "//button[.//span[contains(text(),'Submit')]]"))
        )
        print("[STEP 10] Found Submit button using WebDriverWait")
        return submit_button
    except TimeoutException:
        pass
    
    # Strategy 4: Find all buttons and check for Submit text
    try:
        all_buttons = driver.find_elements(By.TAG_NAME, "button")
        print(f"[STEP 10] Checking {len(all_buttons)} buttons for Submit text...")
        
        for button in all_buttons:
            if button.is_displayed() and button.is_enabled():
                button_text = button.text.strip()
                
                # Direct text match
                if button_text.lower() == 'submit':
                    print(f"[STEP 10] Found Submit button by text: '{button_text}'")
                    return button
                
                # Check spans inside button
                spans = button.find_elements(By.TAG_NAME, "span")
                for span in spans:
                    if span.text.strip().lower() == 'submit':
                        print(f"[STEP 10] Found Submit button by span text")
                        return button
    except:
        pass
    
    print("[STEP 10] Submit button not found with any strategy")
    return None

def _click_button_safely(driver, button):
    """Safely click the button using multiple methods"""
    click_methods = [
        ("JavaScript click", lambda: driver.execute_script("arguments[0].click();", button)),
        ("JavaScript with events", lambda: driver.execute_script("""
            var event = new MouseEvent('click', {
                view: window,
                bubbles: true,
                cancelable: true
            });
            arguments[0].dispatchEvent(event);
        """, button)),
        ("Regular click", lambda: button.click()),
        ("JavaScript focus and click", lambda: (
            driver.execute_script("arguments[0].focus();", button),
            time.sleep(0.3),
            driver.execute_script("arguments[0].click();", button)
        ))
    ]
    
    for method_name, click_method in click_methods:
        try:
            print(f"[STEP 10] Trying: {method_name}")
            click_method()
            
            # Wait to see if click worked
            time.sleep(2)
            
            # Check if button is still there
            try:
                if not button.is_displayed():
                    print(f"[STEP 10] {method_name} succeeded - button no longer visible")
                    return True
            except:
                # Element might be stale (page changed)
                print(f"[STEP 10] {method_name} succeeded - element state changed")
                return True
                
        except Exception as e:
            print(f"[STEP 10] {method_name} failed: {str(e)}")
            continue
    
    return True

def _check_confirmation(driver, previous_url):
    """Check if application was submitted successfully"""
    confirmation_details = {
        'confirmed': False,
        'message': None,
        'reference_number': None
    }
    
    try:
        # Check URL change
        current_url = driver.current_url
        if current_url != previous_url:
            print(f"[STEP 10] URL changed to: {current_url}")
            if any(term in current_url.lower() for term in ['success', 'confirm', 'thank']):
                confirmation_details['confirmed'] = True
        
        # Check for success messages
        page_text = driver.page_source.lower()
        success_indicators = [
            'application submitted',
            'thank you for applying',
            'successfully submitted',
            'application received',
            'we have received your application',
            'your application has been sent'
        ]
        
        for indicator in success_indicators:
            if indicator in page_text:
                print(f"[STEP 10] Found success indicator: '{indicator}'")
                confirmation_details['confirmed'] = True
                confirmation_details['message'] = indicator
                break
        
        # Look for confirmation elements
        confirmation_selectors = [
            "[class*='success']",
            "[class*='confirmation']",
            "[class*='thank']",
            "h1:contains('Thank')",
            "h1:contains('Success')",
            "h2:contains('Thank')",
            "h2:contains('Success')"
        ]
        
        for selector in confirmation_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if elements and any(el.is_displayed() for el in elements):
                    confirmation_details['confirmed'] = True
                    break
            except:
                continue
                
    except Exception as e:
        print(f"[STEP 10] Error checking confirmation: {str(e)}")
    
    return confirmation_details

def _return_to_job_search(driver):
    """Attempt to return to job search for next application"""
    try:
        # Look for "Search for more jobs" or similar links
        return_selectors = [
            "a:contains('Search for more jobs')",
            "a:contains('Find more jobs')",
            "a:contains('Back to search')",
            "button:contains('Search for more')"
        ]
        
        # Try XPath
        xpath_selectors = [
            "//a[contains(text(),'Search for more jobs')]",
            "//a[contains(text(),'Find more jobs')]",
            "//a[contains(text(),'Back to search')]",
            "//button[contains(text(),'Search for more')]"
        ]
        
        for xpath in xpath_selectors:
            try:
                elements = driver.find_elements(By.XPATH, xpath)
                for element in elements:
                    if element.is_displayed():
                        element.click()
                        print("[STEP 10] Clicked return to search link")
                        time.sleep(3)
                        return True
            except:
                continue
        
        # Try going back to main jobs page
        print("[STEP 10] Navigating directly to jobs page...")
        driver.get("https://www.dice.com/jobs")
        time.sleep(3)
        return True
        
    except Exception as e:
        print(f"[STEP 10] Error returning to search: {str(e)}")
        return False

def _debug_page_state(driver):
    """Debug helper to understand page state"""
    try:
        print("\n[DEBUG] Page State Analysis:")
        print(f"[DEBUG] Current URL: {driver.current_url}")
        print(f"[DEBUG] Page Title: {driver.title}")
        
        # Look for all buttons
        all_buttons = driver.find_elements(By.TAG_NAME, "button")
        print(f"[DEBUG] Found {len(all_buttons)} total buttons")
        
        # Show navigation buttons
        nav_buttons = driver.find_elements(By.CSS_SELECTOR, ".navigation-buttons button")
        print(f"[DEBUG] Found {len(nav_buttons)} navigation buttons:")
        
        for i, button in enumerate(nav_buttons):
            try:
                text = button.text.strip()
                classes = button.get_attribute('class')
                visible = button.is_displayed()
                print(f"[DEBUG] Nav button {i}: text='{text}', class='{classes}', visible={visible}")
            except:
                pass
                
    except Exception as e:
        print(f"[DEBUG ERROR] {str(e)}")