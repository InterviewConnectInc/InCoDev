# dice_assistant/dice_step_3_catalog_jobs.py

import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException


def step_3_catalog_jobs(driver):
    """
    Step 3: Catalog all job listings on the current page
    
    Args:
        driver: Selenium WebDriver instance
        
    Returns:
        dict: Contains total job count and basic page info
              Format: {
                  'total_jobs': int,
                  'page_url': str,
                  'filters_confirmed': bool
              }
    """
    try:
        print("\n" + "="*60)
        print("STEP 3: Cataloging all jobs on page")
        print("="*60)
        
        # Wait for page to stabilize
        time.sleep(3)
        current_url = driver.current_url
        print(f"[STEP 3] Current URL: {current_url}")
        
        # Verify we have the expected filters in URL
        filters_confirmed = False
        if "filters.easyApply=true" in current_url and "filters.postedDate=ONE" in current_url:
            print("[STEP 3] ✅ Confirmed: Easy Apply and Today filters are active")
            filters_confirmed = True
        else:
            print("[STEP 3] ⚠️ Warning: Expected filters may not be active")
        
        # Wait for job cards to be present
        print("[STEP 3] Waiting for job listings to load...")
        try:
            wait = WebDriverWait(driver, 10)
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='/job-detail/']")))
            print("[STEP 3] Job listings detected")
        except TimeoutException:
            print("[STEP 3] No job listings found (timeout)")
            return {
                'total_jobs': 0,
                'page_url': current_url,
                'filters_confirmed': filters_confirmed
            }
        
        # Find all unique job card elements
        print("[STEP 3] Counting job listings...")
        job_elements = _find_all_job_elements(driver)
        
        if not job_elements:
            print("[STEP 3] No jobs found on page")
            return {
                'total_jobs': 0,
                'page_url': current_url,
                'filters_confirmed': filters_confirmed
            }
        
        # Count total unique jobs
        total_jobs = len(job_elements)
        print(f"[STEP 3] Found {total_jobs} job(s) on page")
        
        # Log job titles for verification (first 5 only)
        print("\n[STEP 3] Job listings preview:")
        for i, element in enumerate(job_elements[:5]):
            try:
                job_title = element.text.strip() if element.text else "No title"
                print(f"  J{i}: {job_title[:60]}...")
            except:
                print(f"  J{i}: [Could not read title]")
        
        if total_jobs > 5:
            print(f"  ... and {total_jobs - 5} more job(s)")
        
        # Check for any "Applied" indicators
        applied_count = _count_already_applied_jobs(driver)
        if applied_count > 0:
            print(f"\n[STEP 3] Note: {applied_count} job(s) may already be applied to")
            print(f"[STEP 3] {total_jobs - applied_count} job(s) available for application")
        
        print(f"\n[STEP 3] SUCCESS: Catalog complete")
        
        return {
            'total_jobs': total_jobs,
            'page_url': current_url,
            'filters_confirmed': filters_confirmed
        }
        
    except Exception as e:
        print(f"[STEP 3 ERROR] Unexpected error: {str(e)}")
        print(f"[STEP 3 ERROR] Error type: {type(e).__name__}")
        if hasattr(e, '__traceback__'):
            import traceback
            print(f"[STEP 3 ERROR] Traceback: {traceback.format_exc()}")
        
        return {
            'total_jobs': 0,
            'page_url': driver.current_url,
            'filters_confirmed': False
        }


def _find_all_job_elements(driver):
    """Find all unique job card elements on the page"""
    
    # Job card selectors (same as used in original step 7)
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
                    # Only include visible elements with valid hrefs
                    if element.is_displayed():
                        href = element.get_attribute('href')
                        if href and '/job-detail/' in href and href not in seen_hrefs:
                            seen_hrefs.add(href)
                            all_job_elements.append(element)
                except:
                    continue
        except Exception as e:
            print(f"[STEP 3] Error with selector '{selector}': {str(e)}")
            continue
    
    print(f"[STEP 3] Found {len(all_job_elements)} unique job elements")
    
    # Sort by position on page (top to bottom)
    try:
        all_job_elements.sort(key=lambda elem: (elem.location['y'], elem.location['x']))
    except:
        print("[STEP 3] Could not sort jobs by position")
    
    return all_job_elements


def _count_already_applied_jobs(driver):
    """Count how many jobs show as already applied"""
    applied_count = 0
    
    try:
        # Look for common "Applied" indicators
        applied_indicators = [
            # Text-based indicators
            "//*[contains(text(), 'Applied')]",
            "//*[contains(text(), 'Already Applied')]",
            "//*[contains(text(), 'Application Submitted')]",
            # Button/element state indicators
            "button[disabled][class*='apply']",
            "button[class*='applied']",
            ".job-card[class*='applied']",
            "[data-applied='true']"
        ]
        
        # Check each job card area for applied indicators
        job_cards = driver.find_elements(By.CSS_SELECTOR, "[class*='job-card'], article[class*='job'], .job-listing")
        
        for card in job_cards:
            try:
                card_text = card.text.lower() if card.text else ""
                if any(term in card_text for term in ['applied', 'application submitted']):
                    applied_count += 1
                    continue
                
                # Check for disabled apply buttons within the card
                disabled_buttons = card.find_elements(By.CSS_SELECTOR, "button[disabled]")
                for button in disabled_buttons:
                    button_text = button.text.lower()
                    if 'apply' in button_text:
                        applied_count += 1
                        break
            except:
                continue
                
    except Exception as e:
        print(f"[STEP 3] Error counting applied jobs: {str(e)}")
    
    return applied_count


def _debug_page_state(driver):
    """Debug helper to analyze page state"""
    try:
        print("\n[DEBUG] Page State Analysis:")
        print(f"[DEBUG] Current URL: {driver.current_url}")
        print(f"[DEBUG] Page Title: {driver.title}")
        
        # Count different types of elements
        all_links = driver.find_elements(By.TAG_NAME, "a")
        job_links = [link for link in all_links if '/job-detail/' in (link.get_attribute('href') or '')]
        visible_job_links = [link for link in job_links if link.is_displayed()]
        
        print(f"[DEBUG] Total links: {len(all_links)}")
        print(f"[DEBUG] Job detail links: {len(job_links)}")
        print(f"[DEBUG] Visible job links: {len(visible_job_links)}")
        
        # Check for no results message
        page_text = driver.page_source.lower()
        if any(msg in page_text for msg in ['no results', 'no jobs found', '0 jobs']):
            print("[DEBUG] Page may contain 'no results' message")
        
        # Check for loading indicators
        loading_elements = driver.find_elements(By.CSS_SELECTOR, "[class*='loading'], [class*='spinner']")
        if loading_elements:
            print(f"[DEBUG] Found {len(loading_elements)} loading indicators")
            
    except Exception as e:
        print(f"[DEBUG ERROR] {str(e)}")