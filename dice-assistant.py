import time
import os
import sys
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

# Import updated step functions for new flow
try:
    # New login step
    from dice_assistant.dice_step_2_login import step_2_login
    
    # New flow steps (3-5)
    from dice_assistant.dice_step_3_catalog_jobs import step_3_catalog_jobs
    from dice_assistant.dice_step_4_apply_to_job_index import step_4_apply_to_job_index
    from dice_assistant.dice_step_5_loop_return import step_5_loop_return
    
    # Existing application steps (8-10) remain unchanged
    from dice_assistant.dice_step_8 import step_8_click_next
    from dice_assistant.dice_step_9 import step_9_submit_application
    from dice_assistant.dice_step_10 import step_10_handle_confirmation_and_return
    
    STEP_FUNCTIONS_AVAILABLE = True
    print("✅ All step modules imported successfully")
except ImportError as e:
    STEP_FUNCTIONS_AVAILABLE = False
    print(f"⚠️ Step functions not available: {str(e)}")


class DiceAssistant:
    """Dice Platform Assistant - Orchestration with Dynamic Job Titles and Locations"""
    
    def __init__(self, user_email=None):
        self.name = "Dice Assistant"
        self.platform = "dice"
        self.base_url = "https://www.dice.com"
        self.user_email = user_email  # Store user email for login
        self.current_job_title = None  # No default - must be provided by user
        self.current_location = None  # No default - optional from user
        
        print(f"✅ Dice Assistant initialized")
        if self.user_email:
            print(f"📧 User email: {self.user_email}")

    def _update_search_urls(self, job_title, location=None):
        """Update search URLs based on the job title and location"""
        import urllib.parse
        encoded_title = urllib.parse.quote(job_title)
        
        # Build Tier 1 URL with location if provided
        if location and location.strip():
            encoded_location = urllib.parse.quote(location)
            # Build URL with both job title and location
            self.tier1_url = f"https://www.dice.com/jobs?filters.easyApply=true&filters.postedDate=ONE&q={encoded_title}&location={encoded_location}"
            print(f"🔍 Tier 1 URL with location: {self.tier1_url}")
        else:
            # Build URL with just job title
            self.tier1_url = f"https://www.dice.com/jobs?filters.easyApply=true&filters.postedDate=ONE&q={encoded_title}"
            print(f"🔍 Tier 1 URL without location: {self.tier1_url}")
        
        # Tier 2 URL stays the same (filters only, manual entry later)
        self.tier2_url = "https://www.dice.com/jobs?filters.easyApply=true&filters.postedDate=ONE"
        
        print(f"🔍 Updated search URLs for job title: {job_title}")
        if location:
            print(f"📍 Location: {location}")

    def _create_robust_driver(self):
        """Create Chrome driver with proven configuration"""
        chrome_options = Options()
        
        # Essential options for stability
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # User agent
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        try:
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # Execute scripts to hide automation
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            print("✅ Chrome driver created successfully")
            return driver
        except Exception as e:
            raise Exception(f"Failed to create Chrome driver: {str(e)}")

    def _validate_job_page_success(self, driver):
        """Validate that we successfully reached a job listings page"""
        try:
            print("🔍 Validating job page...")
            
            current_url = driver.current_url
            time.sleep(3)
            
            # Check URL contains expected parameters
            if "filters.easyApply=true" in current_url and "filters.postedDate=ONE" in current_url:
                print("✅ Job page validation successful")
                return True
            
            # Check for job listings
            job_indicators = [
                ".job-card",
                "[data-cy*='job-card']",
                "[data-testid*='job-card']",
                "article[class*='job']"
            ]
            
            for indicator in job_indicators:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, indicator)
                    if elements:
                        print(f"✅ Found job listings")
                        return True
                except:
                    continue
            
            return False
            
        except Exception as e:
            print(f"❌ Job page validation error: {str(e)}")
            return False

    def _tier1_optimization(self, driver):
        """Tier 1: Direct navigate to optimized URL"""
        print(f"🎯 TIER 1: Direct navigation with job title: {self.current_job_title}")
        if self.current_location:
            print(f"📍 TIER 1: Including location: {self.current_location}")
        print(f"🔗 URL: {self.tier1_url}")
        
        try:
            driver.get(self.tier1_url)
            time.sleep(5)
            
            if self._validate_job_page_success(driver):
                print("✅ TIER 1 SUCCESS")
                return True
            else:
                print("❌ TIER 1 FAILED")
                return False
                
        except Exception as e:
            print(f"❌ TIER 1 ERROR: {str(e)}")
            return False

    def _tier2_fallback(self, driver):
        """Tier 2: Navigate to filtered URL then search"""
        print(f"🎯 TIER 2: Filtered URL + Search for: {self.current_job_title}")
        if self.current_location:
            print(f"📍 TIER 2: Will add location: {self.current_location}")
        
        try:
            driver.get(self.tier2_url)
            time.sleep(3)
            
            # For Tier 2, we need to manually search since we don't have the old step functions
            # This would normally use step_4_search_keyword
            return self._manual_search(driver, self.current_job_title)
                
        except Exception as e:
            print(f"❌ TIER 2 ERROR: {str(e)}")
            return False

    def _tier3_full_fallback(self, driver):
        """Tier 3: Full fallback - navigate to jobs page"""
        print(f"🎯 TIER 3: Navigate to jobs page directly")
        
        try:
            driver.get("https://www.dice.com/jobs")
            time.sleep(3)
            
            # Would need to implement search and filter application
            # For now, return False as we don't have the old step functions
            print("❌ TIER 3: Manual implementation needed")
            return False
                
        except Exception as e:
            print(f"❌ TIER 3 ERROR: {str(e)}")
            return False

    def _manual_search(self, driver, job_title):
        """Manual search fallback if step functions unavailable"""
        try:
            print(f"🔍 Manual search for: {job_title}")
            
            # Find search input
            search_selectors = [
                "input[type='search']",
                "input[name='q']",
                "input[placeholder*='job title' i]",
                "input[placeholder*='search' i]"
            ]
            
            search_field = None
            for selector in search_selectors:
                try:
                    search_field = driver.find_element(By.CSS_SELECTOR, selector)
                    if search_field.is_displayed():
                        break
                except:
                    continue
            
            if search_field:
                search_field.clear()
                search_field.send_keys(job_title)
                search_field.send_keys(Keys.ENTER)
                time.sleep(3)
                return True
            
            return False
            
        except Exception as e:
            print(f"❌ Manual search error: {str(e)}")
            return False

    def _apply_to_jobs(self, driver, tier_used=None):
        """Orchestrate job applications using new flow - apply to ALL jobs on page"""
        applications_completed = 0
        applied_jobs = []
                
        # Store the current filtered results URL before starting applications
        filtered_results_url = driver.current_url
        print(f"📌 Storing filtered results URL: {filtered_results_url}")
        
        try:
            # Step 3: Catalog all jobs on the page
            print("\n📋 Step 3: Cataloging all jobs on page...")
            job_catalog = step_3_catalog_jobs(driver)
            
            if not job_catalog or job_catalog.get('total_jobs', 0) == 0:
                print("❌ No jobs found on page")
                return {
                    'success': False,
                    'applications': 0,
                    'applied_jobs': []
                }
            
            total_jobs = job_catalog['total_jobs']
            print(f"✅ Found {total_jobs} jobs to apply to")
            
            # Loop through all jobs
            for job_index in range(total_jobs):
                print(f"\n📝 Processing job {job_index + 1}/{total_jobs}")
                
                try:
                    # Step 4: Apply to job at current index
                    print(f"📋 Step 4: Applying to job at index {job_index}...")
                    apply_result = step_4_apply_to_job_index(driver, job_index)
                    
                    if apply_result and apply_result.get('success'):
                        # Successfully clicked on job, now run steps 8-10
                        print("✅ Successfully selected job, proceeding with application...")
                        
                        # Step 8: Click "Apply now" button on job detail page
                        if step_8_click_next(driver):
                            print("✅ Step 8: Clicked Apply Now")
                            
                            # Step 9: Click "Next"
                            if step_9_submit_application(driver):
                                print("✅ Step 9: Clicked Next")
                                
                                # Step 10: Click "Submit" and handle confirmation
                                result = step_10_handle_confirmation_and_return(driver)
                                if result and result.get('submission_confirmed'):
                                    print(f"✅ Application submitted successfully!")
                                    applications_completed += 1
                                    applied_jobs.append({
                                        'title': f'Job #{job_index + 1}',
                                        'company': 'Applied via Dice',
                                        'job_search': self.current_job_title,
                                        'location': self.current_location,
                                        'index': job_index
                                    })
                                else:
                                    print(f"❌ Step 10: Failed to confirm submission")
                            else:
                                print(f"❌ Step 9: Failed to click Next")
                        else:
                            print(f"❌ Step 8: Failed to click Apply Now")
                    else:
                        error_msg = apply_result.get('error', 'Unknown error') if apply_result else 'No result returned'
                        print(f"❌ Step 4: Failed to select job - {error_msg}")
                    
                    # Step 5: Return to filtered results for next job (if not last job)
                    if job_index < total_jobs - 1:
                        print(f"\n📋 Step 5: Returning to filtered results page...")
                        loop_result = step_5_loop_return(driver, filtered_results_url)
                        
                        if loop_result and loop_result.get('ready_for_next'):
                            print("✅ Ready for next job application")
                            time.sleep(2)  # Brief pause before next application
                        else:
                            print("⚠️ Warning: May not have returned to results page properly")
                            # Try to navigate back manually
                            driver.get(filtered_results_url)
                            time.sleep(3)
                    
                except Exception as e:
                    print(f"❌ Error processing job {job_index}: {str(e)}")
                    # Try to return to results page for next job
                    if job_index < total_jobs - 1:
                        try:
                            driver.get(filtered_results_url)
                            time.sleep(3)
                        except:
                            pass
                    continue
            
            print(f"\n📊 Completed {applications_completed}/{total_jobs} applications")
            
        except Exception as e:
            print(f"❌ Fatal error in application loop: {str(e)}")
        
        return {
            'success': applications_completed > 0,
            'applications': applications_completed,
            'applied_jobs': applied_jobs
        }

    def run_automation(self, user_data=None, resume_data=None):
        """Main automation method with dynamic job title and location support"""
        driver = None
        
        # Extract job title from user_data - NO DEFAULT
        if user_data and isinstance(user_data, dict):
            job_title = user_data.get('jobTitle', '').strip()
            if not job_title:
                error_msg = "❌ ERROR: No job title provided! Job title is required to run automation."
                print(error_msg)
                return {'success': False, 'error': error_msg}
            self.current_job_title = job_title
            print(f"💼 Using job title from user data: {self.current_job_title}")
            
            # Extract location from user_data - NO DEFAULT
            location = user_data.get('location', '').strip()
            if location:
                self.current_location = location
                print(f"📍 Using location from user data: {self.current_location}")
            else:
                self.current_location = None
                print("📍 No location provided - will search without location filter")
        else:
            error_msg = "❌ ERROR: No user data provided! Cannot run automation without job title."
            print(error_msg)
            return {'success': False, 'error': error_msg}
        
        # Update URLs with the job title and location
        self._update_search_urls(self.current_job_title, self.current_location)
        
        try:
            print("🚀 Starting Dice Assistant")
            print(f"🔍 Searching for: {self.current_job_title}")
            if self.current_location:
                print(f"📍 In location: {self.current_location}")
            
            # Create driver
            driver = self._create_robust_driver()
            
            # Step 2: Login using the new independent step
            print("\n🔑 Step 2: Login process...")
            
            # Check if we have user email
            if not self.user_email:
                return {'success': False, 'error': 'No user email provided for login'}
            
            # Call the independent login step with just driver and email
            login_result = step_2_login(driver, self.user_email)
            
            if not login_result or not login_result.get('success'):
                error_msg = login_result.get('error', 'Login failed') if login_result else 'Login step returned no result'
                return {'success': False, 'error': error_msg}
            
            print("✅ Login successful")
            
            # Navigate to job page using tiered strategy
            tier_used = None
            
            if self._tier1_optimization(driver):
                tier_used = "Tier 1"
            elif self._tier2_fallback(driver):
                tier_used = "Tier 2"
            elif self._tier3_full_fallback(driver):
                tier_used = "Tier 3"
            else:
                return {'success': False, 'error': 'Failed to reach job page'}
            
            print(f"\n✅ Reached job page using {tier_used}")
            
            # Orchestrate applications - NEW FLOW: Apply to ALL jobs
            print(f"\n📋 Starting job applications for ALL available positions")
            print(f"🔍 Job Title: {self.current_job_title}")
            if self.current_location:
                print(f"📍 Location: {self.current_location}")
            
            results = self._apply_to_jobs(driver, tier_used)
            
            return {
                'success': True,
                'job_title_searched': self.current_job_title,
                'location_searched': self.current_location,
                'tier_used': tier_used,
                'total_applications': results['applications'],
                'applied_jobs': results['applied_jobs'],
                'message': f"Completed {results['applications']} applications for {self.current_job_title}" + 
                          (f" in {self.current_location}" if self.current_location else "")
            }
            
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            return {'success': False, 'error': str(e)}
        
        finally:
            if driver:
                try:
                    driver.quit()
                    print("🔒 Browser closed")
                except:
                    pass

    def start_automation(self, request, session):
        """Flask compatibility method - extracts job title and location from request"""
        try:
            # Get user email from session
            user_email = session.get('user_email')
            
            if not user_email:
                error_msg = "❌ ERROR: User email not found in session!"
                print(error_msg)
                return {'success': False, 'error': error_msg}
            
            # Re-initialize with user email
            self.__init__(user_email=user_email)
            
            # Get form data from request
            if request.is_json:
                form_data = request.get_json()
            else:
                form_data = request.form.to_dict()
            
            # Check if job title is provided
            job_title = form_data.get('jobTitle', '').strip()
            if not job_title:
                error_msg = "❌ ERROR: Job title is required but was not provided in the form!"
                print(error_msg)
                return {'success': False, 'error': error_msg}
            
            # Get location if provided
            location = form_data.get('location', '').strip()
            
            # Create user_data with job title and location
            user_data = {
                'jobTitle': job_title,
                'location': location,
                'firstName': form_data.get('firstName', ''),
                'lastName': form_data.get('lastName', ''),
                'email': form_data.get('email', ''),
                'city': form_data.get('city', ''),
                'state': form_data.get('state', '')
            }
            
            print(f"📥 Received request with job title: {user_data['jobTitle']}")
            if location:
                print(f"📍 Location: {user_data['location']}")
            
            return self.run_automation(user_data)
            
        except Exception as e:
            print(f"❌ Request processing error: {str(e)}")
            return {'success': False, 'error': f'Request processing error: {str(e)}'}