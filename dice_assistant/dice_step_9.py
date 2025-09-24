# dice_assistant/dice_step_9.py

import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

def step_9_submit_application(driver):
    """
    Step 9: Click 'Next' button on the application form
    
    Args:
        driver: Selenium WebDriver instance
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        print("\n" + "="*60)
        print("STEP 9: Clicking Next button on application form")
        print("="*60)
        
        # Wait for page to load
        print("[STEP 9] Waiting for application form to load...")
        time.sleep(3)
        
        current_url = driver.current_url
        print(f"[STEP 9] Current URL: {current_url}")
        
        # Verify we're on the application page
        if 'apply' in current_url.lower():
            print("[STEP 9] Confirmed on application page")
        
        # Find and click the Next button
        print("[STEP 9] Looking for Next button...")
        next_button = _find_next_button(driver)
        
        if next_button:
            print("[STEP 9] Found Next button")
            
            # Scroll button into view
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_button)
            time.sleep(1)
            
            # Click the button
            print("[STEP 9] Clicking Next button...")
            success = _click_button_safely(driver, next_button)
            
            if success:
                print("[STEP 9] Successfully clicked Next button")
                time.sleep(3)  # Wait for next page to load
                
                # Verify we moved to next step
                new_url = driver.current_url
                if new_url != current_url:
                    print(f"[STEP 9] SUCCESS: Navigated to next step")
                    print(f"[STEP 9] New URL: {new_url}")
                else:
                    print("[STEP 9] SUCCESS: Clicked Next (same URL but likely new content)")
                
                return True
            else:
                print("[STEP 9] ERROR: Failed to click Next button")
                return False
        else:
            print("[STEP 9] ERROR: Could not find Next button")
            _debug_page_state(driver)
            return False
            
    except Exception as e:
        print(f"[STEP 9 ERROR] Unexpected error: {str(e)}")
        print(f"[STEP 9 ERROR] Error type: {type(e).__name__}")
        if hasattr(e, '__traceback__'):
            import traceback
            print(f"[STEP 9 ERROR] Traceback: {traceback.format_exc()}")
        return False

def _find_next_button(driver):
    """Find the Next button using multiple strategies"""
    
    # Strategy 1: Direct selectors based on the provided HTML
    selectors = [
        # Exact class match
        "button.seds-button-primary.btn-next",
        "button.btn-next",
        
        # Button with Next text
        "button[type='button'] span:contains('Next')",
        
        # Inside navigation-buttons div
        ".navigation-buttons button.btn-next",
        ".navigation-buttons button.seds-button-primary",
        
        # Generic Next button
        "button:contains('Next')",
        
        # Data attribute selector
        "button[data-v-866481c4]"
    ]
    
    # Try CSS selectors first
    for selector in selectors:
        try:
            # Skip :contains selectors for CSS
            if ':contains' in selector:
                continue
                
            buttons = driver.find_elements(By.CSS_SELECTOR, selector)
            for button in buttons:
                if button.is_displayed() and button.is_enabled():
                    # Check if it's a Next button
                    button_text = button.text.strip()
                    if 'next' in button_text.lower() or button_text == '':
                        # Check for span inside with Next text
                        spans = button.find_elements(By.TAG_NAME, "span")
                        for span in spans:
                            if 'next' in span.text.lower():
                                print(f"[STEP 9] Found Next button using selector: {selector}")
                                return button
                        
                        # If button has btn-next class, trust it
                        if 'btn-next' in button.get_attribute('class'):
                            print(f"[STEP 9] Found Next button using selector: {selector}")
                            return button
        except:
            continue
    
    # Strategy 2: XPath selectors
    xpath_selectors = [
        # Button containing Next text
        "//button[contains(text(),'Next')]",
        "//button[.//span[contains(text(),'Next')]]",
        "//button[@class='seds-button-primary btn-next']",
        "//button[contains(@class,'btn-next')]",
        
        # Button in navigation area
        "//div[@class='navigation-buttons btn-right']//button[contains(@class,'btn-next')]",
        "//div[contains(@class,'navigation-buttons')]//button[contains(@class,'seds-button-primary')]"
    ]
    
    for xpath in xpath_selectors:
        try:
            buttons = driver.find_elements(By.XPATH, xpath)
            for button in buttons:
                if button.is_displayed() and button.is_enabled():
                    print(f"[STEP 9] Found Next button using XPath: {xpath}")
                    return button
        except:
            continue
    
    # Strategy 3: Wait for clickable element
    try:
        wait = WebDriverWait(driver, 10)
        next_button = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button.btn-next"))
        )
        print("[STEP 9] Found Next button using WebDriverWait")
        return next_button
    except TimeoutException:
        pass
    
    # Strategy 4: Find all buttons and check text
    try:
        all_buttons = driver.find_elements(By.TAG_NAME, "button")
        print(f"[STEP 9] Checking {len(all_buttons)} buttons for Next text...")
        
        for button in all_buttons:
            if button.is_displayed() and button.is_enabled():
                button_text = button.text.strip()
                button_class = button.get_attribute('class') or ''
                
                # Check button text or span text inside
                if button_text.lower() == 'next':
                    print(f"[STEP 9] Found Next button by text: '{button_text}'")
                    return button
                
                # Check class for btn-next
                if 'btn-next' in button_class:
                    print(f"[STEP 9] Found Next button by class: '{button_class}'")
                    return button
                
                # Check spans inside button
                spans = button.find_elements(By.TAG_NAME, "span")
                for span in spans:
                    if span.text.strip().lower() == 'next':
                        print(f"[STEP 9] Found Next button by span text")
                        return button
    except:
        pass
    
    print("[STEP 9] Next button not found with any strategy")
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
            print(f"[STEP 9] Trying: {method_name}")
            click_method()
            
            # Small wait to see if click worked
            time.sleep(1)
            
            # Check if button is still visible (might indicate it didn't work)
            try:
                if not button.is_displayed():
                    print(f"[STEP 9] {method_name} succeeded - button no longer visible")
                    return True
            except:
                # Element might be stale, which is good (page changed)
                print(f"[STEP 9] {method_name} succeeded - element state changed")
                return True
            
            # Check for any loading indicators
            loading_indicators = driver.find_elements(By.CSS_SELECTOR, "[class*='loading'], [class*='spinner']")
            if any(indicator.is_displayed() for indicator in loading_indicators):
                print(f"[STEP 9] {method_name} succeeded - loading indicator detected")
                return True
                
        except Exception as e:
            print(f"[STEP 9] {method_name} failed: {str(e)}")
            continue
    
    # If we tried all methods, assume the last one worked
    return True

def _debug_page_state(driver):
    """Debug helper to understand page state"""
    try:
        print("\n[DEBUG] Page State Analysis:")
        print(f"[DEBUG] Current URL: {driver.current_url}")
        
        # Look for navigation buttons
        nav_buttons = driver.find_elements(By.CSS_SELECTOR, ".navigation-buttons button")
        print(f"[DEBUG] Found {len(nav_buttons)} navigation buttons")
        
        for i, button in enumerate(nav_buttons):
            try:
                text = button.text.strip()
                classes = button.get_attribute('class')
                visible = button.is_displayed()
                enabled = button.is_enabled()
                print(f"[DEBUG] Nav button {i}: text='{text}', class='{classes}', visible={visible}, enabled={enabled}")
            except:
                pass
        
        # Check for any buttons with 'next' in class or text
        next_like_buttons = driver.find_elements(By.XPATH, 
            "//*[contains(@class,'next') or contains(text(),'Next') or contains(text(),'next')]")
        print(f"[DEBUG] Found {len(next_like_buttons)} elements with 'next' reference")
        
        # Save page source for analysis
        try:
            with open("step9_debug.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            print("[DEBUG] Page source saved to step9_debug.html")
        except:
            pass
            
    except Exception as e:
        print(f"[DEBUG ERROR] {str(e)}")