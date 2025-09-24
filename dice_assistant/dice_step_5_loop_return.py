# dice_assistant/dice_step_5_loop_return.py

import time
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, NoSuchElementException


def step_5_loop_return(driver, filtered_results_url):
    """
    Step 5: Return to the filtered job results page to process the next job
    
    Args:
        driver: Selenium WebDriver instance
        filtered_results_url: The URL of the filtered search results to return to
        
    Returns:
        dict: Result of the operation
              Format: {
                  'ready_for_next': bool,
                  'current_url': str,
                  'error': str (if failed)
              }
    """
    try:
        print("\n" + "="*60)
        print("STEP 5: Returning to filtered results page")
        print("="*60)
        
        current_url = driver.current_url
        print(f"[STEP 5] Current URL: {current_url}")
        print(f"[STEP 5] Target URL: {filtered_results_url}")
        
        # Check if we're in a different tab
        current_windows = driver.window_handles
        print(f"[STEP 5] Current number of windows: {len(current_windows)}")
        
        # If multiple windows are open, handle tab closing
        if len(current_windows) > 1:
            print("[STEP 5] Multiple windows detected, handling tabs...")
            
            # Check if we have stored the original window
            if hasattr(driver, 'original_window'):
                print(f"[STEP 5] Original window handle found: {driver.original_window}")
                
                # Close current tab if it's not the original
                current_window = driver.current_window_handle
                if current_window != driver.original_window:
                    print("[STEP 5] Closing current tab...")
                    driver.close()
                    time.sleep(0.5)
                
                # Switch back to original window
                print("[STEP 5] Switching to original window...")
                driver.switch_to.window(driver.original_window)
                time.sleep(1)
            else:
                # No original window stored, try to find the right one
                print("[STEP 5] No original window stored, attempting to find results window...")
                
                # Try each window to find the one with the results
                for window in current_windows:
                    driver.switch_to.window(window)
                    if filtered_results_url in driver.current_url:
                        print(f"[STEP 5] Found results window: {window}")
                        # Close other windows
                        for other_window in current_windows:
                            if other_window != window:
                                driver.switch_to.window(other_window)
                                driver.close()
                        driver.switch_to.window(window)
                        break
        
        # Navigate to filtered results URL
        print("[STEP 5] Navigating to filtered results...")
        
        # Check if we're already on the results page
        if driver.current_url == filtered_results_url:
            print("[STEP 5] Already on filtered results page")
        else:
            # Navigate to the filtered results
            driver.get(filtered_results_url)
            print("[STEP 5] Navigated to filtered results URL")
        
        # Wait for page to load
        print("[STEP 5] Waiting for page to stabilize...")
        time.sleep(4)
        
        # Verify we're on the job search results page
        if _verify_on_results_page(driver):
            print("[STEP 5] SUCCESS: Back on job results page")
            
            # Clear any popups or modals that might interfere
            _handle_popups(driver)
            
            # Final check that we're ready for the next job
            if _verify_ready_for_next_job(driver):
                print("[STEP 5] Ready to process next job")
                
                return {
                    'ready_for_next': True,
                    'current_url': driver.current_url
                }
            else:
                print("[STEP 5] WARNING: Page loaded but may not be ready for next job")
                return {
                    'ready_for_next': True,  # Continue anyway
                    'current_url': driver.current_url
                }
        else:
            error_msg = "Failed to verify return to results page"
            print(f"[STEP 5] ERROR: {error_msg}")
            
            # Try one more direct navigation
            print("[STEP 5] Attempting direct navigation retry...")
            driver.get(filtered_results_url)
            time.sleep(3)
            
            return {
                'ready_for_next': True,  # Continue anyway to avoid getting stuck
                'current_url': driver.current_url,
                'error': error_msg
            }
            
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        print(f"[STEP 5 ERROR] {error_msg}")
        print(f"[STEP 5 ERROR] Error type: {type(e).__name__}")
        if hasattr(e, '__traceback__'):
            import traceback
            print(f"[STEP 5 ERROR] Traceback: {traceback.format_exc()}")
        
        # Try to recover by direct navigation
        try:
            print("[STEP 5] Attempting recovery via direct navigation...")
            driver.get(filtered_results_url)
            time.sleep(3)
            return {
                'ready_for_next': True,
                'current_url': driver.current_url,
                'error': error_msg
            }
        except:
            return {
                'ready_for_next': False,
                'current_url': driver.current_url if hasattr(driver, 'current_url') else 'unknown',
                'error': error_msg
            }


def _verify_on_results_page(driver):
    """Verify we're on a job search results page"""
    try:
        current_url = driver.current_url
        
        # Check URL contains job search indicators
        if any(term in current_url for term in ['/jobs', 'search', 'q=']) and '/job-detail/' not in current_url:
            print("[STEP 5] URL indicates job search page")
            
            # Look for job listing elements
            job_indicators = [
                "a[href*='/job-detail/']",
                ".job-card",
                ".job-listing",
                "[data-cy*='job-card']",
                "[data-testid*='job-card']",
                "article[class*='job']"
            ]
            
            for indicator in job_indicators:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, indicator)
                    if elements:
                        print(f"[STEP 5] Found job listings using selector: {indicator}")
                        return True
                except:
                    continue
            
            # Even if no jobs found, if URL is right, we're on the page
            if 'filters.easyApply=true' in current_url:
                print("[STEP 5] Filters confirmed in URL, assuming results page")
                return True
                
        return False
        
    except Exception as e:
        print(f"[STEP 5] Error verifying results page: {str(e)}")
        return False


def _verify_ready_for_next_job(driver):
    """Verify the page is ready to click on the next job"""
    try:
        # Check that page is not loading
        ready_state = driver.execute_script("return document.readyState")
        if ready_state != "complete":
            print(f"[STEP 5] Page not fully loaded, state: {ready_state}")
            return False
        
        # Check for loading spinners
        loading_indicators = [
            "[class*='loading']",
            "[class*='spinner']",
            ".loader",
            "[data-testid='loading']"
        ]
        
        for indicator in loading_indicators:
            try:
                loaders = driver.find_elements(By.CSS_SELECTOR, indicator)
                visible_loaders = [l for l in loaders if l.is_displayed()]
                if visible_loaders:
                    print(f"[STEP 5] Found {len(visible_loaders)} visible loading indicators")
                    return False
            except:
                continue
        
        # Check that job elements are present and clickable
        job_links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/job-detail/']")
        if job_links:
            print(f"[STEP 5] Found {len(job_links)} job links on page")
            return True
        else:
            print("[STEP 5] No job links found yet")
            return False
            
    except Exception as e:
        print(f"[STEP 5] Error checking page readiness: {str(e)}")
        return True  # Default to ready to avoid getting stuck


def _handle_popups(driver):
    """Handle any popups or modals that might interfere with clicking jobs"""
    try:
        # Common popup close button selectors
        popup_close_selectors = [
            "button[aria-label='Close']",
            "button[class*='close']",
            ".modal button[class*='close']",
            "[data-dismiss='modal']",
            "button:contains('×')",
            "button:contains('X')",
            "[class*='popup'] button[class*='close']"
        ]
        
        for selector in popup_close_selectors:
            try:
                # Handle CSS selectors
                if ':contains' not in selector:
                    close_buttons = driver.find_elements(By.CSS_SELECTOR, selector)
                else:
                    # Handle text-based selectors
                    button_text = selector.split("'")[1]
                    close_buttons = driver.find_elements(By.XPATH, f"//button[contains(text(), '{button_text}')]")
                
                for button in close_buttons:
                    if button.is_displayed() and button.is_enabled():
                        print(f"[STEP 5] Found popup close button, clicking...")
                        try:
                            driver.execute_script("arguments[0].click();", button)
                            time.sleep(1)
                            print("[STEP 5] Popup closed")
                        except:
                            pass
            except:
                continue
                
    except Exception as e:
        print(f"[STEP 5] Error handling popups: {str(e)}")


def _debug_page_state(driver):
    """Debug helper to analyze current page state"""
    try:
        print("\n[DEBUG] Page State Analysis:")
        print(f"[DEBUG] Current URL: {driver.current_url}")
        print(f"[DEBUG] Page Title: {driver.title}")
        print(f"[DEBUG] Window Handles: {len(driver.window_handles)}")
        
        # Check for job elements
        job_links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/job-detail/']")
        visible_jobs = [j for j in job_links if j.is_displayed()]
        print(f"[DEBUG] Total job links: {len(job_links)}")
        print(f"[DEBUG] Visible job links: {len(visible_jobs)}")
        
        # Check page text for indicators
        page_text = driver.page_source[:500].lower()
        if 'no results' in page_text or '0 jobs' in page_text:
            print("[DEBUG] Page may show no results")
        
    except Exception as e:
        print(f"[DEBUG ERROR] {str(e)}")