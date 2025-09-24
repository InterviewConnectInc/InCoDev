# dice_assistant/dice_step_4_apply_to_job_index.py

import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException


def step_4_apply_to_job_index(driver, job_index):
    """
    Step 4: Click on job card at specified index from search results to navigate to job detail page
    
    Args:
        driver: Selenium WebDriver instance
        job_index: Zero-based index of which job to click (0 = first job, 1 = second job, etc.)
        
    Returns:
        dict: Result of the operation
              Format: {
                  'success': bool,
                  'job_index': int,
                  'error': str (if failed),
                  'job_url': str (if successful)
              }
    """
    try:
        print("\n" + "="*60)
        print(f"STEP 4: Clicking on job at index {job_index}")
        print("="*60)
        
        # Store the original window handle
        original_window = driver.current_window_handle
        original_windows = driver.window_handles
        current_url = driver.current_url
        
        print(f"[STEP 4] Current URL: {current_url}")
        print(f"[STEP 4] Target job index: {job_index}")
        print(f"[STEP 4] Original window handle: {original_window}")
        print(f"[STEP 4] Number of windows before click: {len(original_windows)}")
        
        # Wait for page to be stable
        time.sleep(2)
        
        # Find all job elements (using same logic as catalog step)
        print("[STEP 4] Finding all job elements...")
        job_elements = _find_all_job_elements(driver)
        
        if not job_elements:
            error_msg = "No job elements found on page"
            print(f"[STEP 4] ERROR: {error_msg}")
            return {
                'success': False,
                'job_index': job_index,
                'error': error_msg
            }
        
        # Check if requested index exists
        if job_index >= len(job_elements):
            error_msg = f"Requested index {job_index} but only {len(job_elements)} jobs available"
            print(f"[STEP 4] ERROR: {error_msg}")
            return {
                'success': False,
                'job_index': job_index,
                'error': error_msg
            }
        
        # Get the target job element
        target_element = job_elements[job_index]
        
        # Check if this job might already be applied to
        if _check_if_already_applied(driver, target_element, job_index):
            error_msg = f"Job at index {job_index} appears to be already applied to"
            print(f"[STEP 4] WARNING: {error_msg}")
            return {
                'success': False,
                'job_index': job_index,
                'error': error_msg
            }
        
        # Get job info before clicking
        try:
            job_text = target_element.text.strip() if target_element.text else "No title"
            href = target_element.get_attribute('href')
            print(f"[STEP 4] Target job: {job_text[:60]}...")
            print(f"[STEP 4] Job URL: {href[:80]}...")
        except:
            job_text = "Unknown"
            href = "Unknown"
        
        # Attempt to click the job
        click_success = _click_job_element(driver, target_element, job_index)
        
        if not click_success:
            return {
                'success': False,
                'job_index': job_index,
                'error': 'Failed to click job element'
            }
        
        # Wait for navigation
        print("[STEP 4] Waiting for page navigation...")
        time.sleep(4)
        
        # Check if a new window/tab was opened
        new_windows = driver.window_handles
        print(f"[STEP 4] Number of windows after click: {len(new_windows)}")
        
        # Handle new tab scenario
        if len(new_windows) > len(original_windows):
            print("[STEP 4] New tab detected, switching to it...")
            
            # Find the new window handle
            new_window = None
            for window in new_windows:
                if window not in original_windows:
                    new_window = window
                    break
            
            if new_window:
                # Switch to the new tab
                driver.switch_to.window(new_window)
                print(f"[STEP 4] Switched to new tab: {new_window}")
                
                # Wait for the new page to load
                time.sleep(2)
                
                # Verify we're on a job detail page
                new_url = driver.current_url
                if '/job-detail/' in new_url:
                    print(f"[STEP 4] SUCCESS: Navigated to job detail page in new tab")
                    print(f"[STEP 4] Job detail URL: {new_url}")
                    
                    # Store the original window handle for later use
                    driver.original_window = original_window
                    
                    return {
                        'success': True,
                        'job_index': job_index,
                        'job_url': new_url
                    }
                else:
                    print(f"[STEP 4] New tab opened but not on job detail page: {new_url}")
                    # Switch back to original window
                    driver.switch_to.window(original_window)
                    return {
                        'success': False,
                        'job_index': job_index,
                        'error': 'New tab opened but not on job detail page'
                    }
        
        # Check if navigation happened in same window
        else:
            new_url = driver.current_url
            if new_url != current_url and '/job-detail/' in new_url:
                print(f"[STEP 4] SUCCESS: Navigated to job detail page in same window")
                print(f"[STEP 4] Job detail URL: {new_url}")
                
                return {
                    'success': True,
                    'job_index': job_index,
                    'job_url': new_url
                }
            elif new_url != current_url:
                print(f"[STEP 4] Page changed but not to expected job detail format")
                print(f"[STEP 4] New URL: {new_url}")
                # Still consider it potential success
                return {
                    'success': True,
                    'job_index': job_index,
                    'job_url': new_url
                }
            else:
                error_msg = "Failed to navigate - URL unchanged"
                print(f"[STEP 4] ERROR: {error_msg}")
                return {
                    'success': False,
                    'job_index': job_index,
                    'error': error_msg
                }
                
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        print(f"[STEP 4 ERROR] {error_msg}")
        print(f"[STEP 4 ERROR] Error type: {type(e).__name__}")
        if hasattr(e, '__traceback__'):
            import traceback
            print(f"[STEP 4 ERROR] Traceback: {traceback.format_exc()}")
        
        return {
            'success': False,
            'job_index': job_index,
            'error': error_msg
        }


def _find_all_job_elements(driver):
    """Find all unique job card elements on the page - same as catalog step"""
    
    job_card_selectors = [
        # Primary selectors for job cards
        "a.card-title-link[href*='/job-detail/']",
        "a[data-testid='job-card-title-link'][href*='/job-detail/']",
        "h3 a[href*='/job-detail/']",
        "h2 a[href*='/job-detail/']",
        # Broader selectors if specific ones fail
        "a[class*='job-title'][href*='/job-detail/']",
        "a[class*='job-link'][href*='/job-detail/']",
        ".job-card a[href*='/job-detail/']",
        "[data-testid*='job-card'] a[href*='/job-detail/']",
        # Generic job detail links
        "a[href*='/job-detail/']"
    ]
    
    # Collect all unique job elements
    all_job_elements = []
    seen_hrefs = set()
    
    for selector in job_card_selectors:
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            for element in elements:
                try:
                    if element.is_displayed():
                        href = element.get_attribute('href')
                        if href and '/job-detail/' in href and href not in seen_hrefs:
                            seen_hrefs.add(href)
                            all_job_elements.append(element)
                except:
                    continue
        except:
            continue
    
    # Sort by position on page (top to bottom)
    try:
        all_job_elements.sort(key=lambda elem: (elem.location['y'], elem.location['x']))
    except:
        pass
    
    return all_job_elements


def _check_if_already_applied(driver, job_element, job_index):
    """Check if a job has already been applied to"""
    try:
        # Get the parent job card container
        job_card = job_element
        for _ in range(3):  # Go up to 3 levels to find job card container
            try:
                parent = job_card.find_element(By.XPATH, "./..")
                if any(cls in parent.get_attribute('class') or '' for cls in ['job-card', 'job-listing', 'job-item']):
                    job_card = parent
                    break
            except:
                break
        
        # Check for "Applied" indicators in the job card
        job_card_text = job_card.text.lower() if job_card.text else ""
        
        applied_indicators = [
            'applied',
            'already applied',
            'application submitted',
            'you applied',
            'application sent'
        ]
        
        for indicator in applied_indicators:
            if indicator in job_card_text:
                print(f"[STEP 4] Found '{indicator}' indicator in job card")
                return True
        
        # Check for disabled apply buttons
        try:
            apply_buttons = job_card.find_elements(By.XPATH, ".//button[contains(text(), 'Apply') or contains(text(), 'Applied')]")
            for button in apply_buttons:
                if button.get_attribute('disabled') or 'applied' in button.text.lower():
                    print(f"[STEP 4] Found disabled/applied button in job card")
                    return True
        except:
            pass
        
        return False
        
    except Exception as e:
        print(f"[STEP 4] Error checking if already applied: {str(e)}")
        return False


def _click_job_element(driver, element, job_index):
    """Attempt to click the job element using multiple strategies"""
    try:
        # Scroll element into view
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
        time.sleep(1)
        
        # Highlight the element briefly for debugging
        try:
            driver.execute_script("arguments[0].style.border='3px solid green'", element)
            time.sleep(0.5)
            driver.execute_script("arguments[0].style.border=''", element)
        except:
            pass
        
        # Try multiple click strategies
        click_strategies = [
            # Strategy 1: JavaScript click
            lambda: driver.execute_script("arguments[0].click();", element),
            # Strategy 2: Regular click
            lambda: element.click(),
            # Strategy 3: Action chains
            lambda: _click_with_action_chains(driver, element),
            # Strategy 4: Click parent if link is nested
            lambda: _click_parent_element(driver, element)
        ]
        
        for i, strategy in enumerate(click_strategies):
            try:
                print(f"[STEP 4] Trying click strategy {i+1}...")
                strategy()
                print(f"[STEP 4] Click strategy {i+1} executed")
                time.sleep(1)  # Brief pause to see if navigation starts
                
                # Check if URL changed (quick success check)
                if driver.current_url != element.get_attribute('href'):
                    return True
                    
            except Exception as e:
                print(f"[STEP 4] Click strategy {i+1} failed: {str(e)}")
                continue
        
        # If we get here, assume the last strategy worked
        return True
        
    except Exception as e:
        print(f"[STEP 4] Error clicking job element: {str(e)}")
        return False


def _click_with_action_chains(driver, element):
    """Click using ActionChains"""
    from selenium.webdriver.common.action_chains import ActionChains
    actions = ActionChains(driver)
    actions.move_to_element(element).click().perform()


def _click_parent_element(driver, element):
    """Try clicking the parent element"""
    parent = element.find_element(By.XPATH, "./..")
    driver.execute_script("arguments[0].click();", parent)