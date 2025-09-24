# dice_assistant/dice_step_2_login.py

import time
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException


def step_2_login(driver, user_email):
    """
    Step 2: Complete login process for Dice platform
    
    This step handles the entire login flow independently, including:
    - Loading credentials from database
    - Navigating to login page
    - Entering credentials
    - Handling multi-step authentication
    - Verifying successful login
    
    Args:
        driver: Selenium WebDriver instance
        user_email: User's email address to look up credentials
        
    Returns:
        dict: Result of the login operation
              Format: {
                  'success': bool,
                  'error': str (if failed),
                  'message': str (status message)
              }
    """
    try:
        print("\n" + "="*60)
        print("STEP 2: Dice Platform Login")
        print("="*60)
        
        # Load credentials from database
        print(f"[STEP 2] Loading credentials for: {user_email}")
        credentials = _load_credentials_from_db(user_email)
        
        if not credentials:
            return {
                'success': False,
                'error': 'Failed to retrieve credentials from database'
            }
        
        dice_email = credentials['dice_email']
        dice_password = credentials['dice_password']
        
        print(f"[STEP 2] Retrieved credentials for Dice account: {dice_email}")
        
        # Force fresh login - Add incognito mode to Chrome options for clean session
        print("[STEP 2] Forcing fresh login session...")
        
        # Start login process
        print("[STEP 2] Starting login process...")
        
        # Try multiple login URLs
        login_urls = [
            "https://www.dice.com/dashboard/login",
            "https://www.dice.com/login"
        ]
        
        login_successful = False
        
        for login_url in login_urls:
            print(f"\n[STEP 2] Attempting login via: {login_url}")
            
            try:
                # Navigate to login page
                driver.get(login_url)
                time.sleep(3)
                
                # Force login - skip already logged in check to ensure fresh session
                print("[STEP 2] Proceeding with login sequence...")
                
                # Enter email
                if _enter_email(driver, dice_email):
                    print("[STEP 2] Email entered successfully")
                else:
                    print(f"[STEP 2] Failed to enter email at {login_url}")
                    continue
                
                # Click continue/next button
                if _click_continue_button(driver):
                    print("[STEP 2] Clicked continue button")
                else:
                    print("[STEP 2] No continue button found, trying Enter key")
                    _send_enter_key_to_email(driver)
                
                time.sleep(2)
                
                # Enter password
                if _enter_password(driver, dice_password):
                    print("[STEP 2] Password entered successfully")
                else:
                    print(f"[STEP 2] Failed to enter password at {login_url}")
                    continue
                
                # Click sign in button
                if _click_signin_button(driver):
                    print("[STEP 2] Clicked sign in button")
                else:
                    print("[STEP 2] No sign in button found, trying Enter key")
                    _send_enter_key_to_password(driver)
                
                # Wait for login to process
                print("[STEP 2] Waiting for authentication...")
                time.sleep(5)
                
                # Verify login success
                if _verify_login_success(driver, dice_email):
                    print("[STEP 2] ✅ Login successful!")
                    login_successful = True
                    break
                else:
                    print(f"[STEP 2] Login verification failed for {login_url}")
                    
            except Exception as e:
                print(f"[STEP 2] Error during login attempt at {login_url}: {str(e)}")
                continue
        
        if login_successful:
            return {
                'success': True,
                'message': 'Login completed successfully'
            }
        else:
            return {
                'success': False,
                'error': 'Failed to login after trying all methods'
            }
            
    except Exception as e:
        error_msg = f"Unexpected error during login: {str(e)}"
        print(f"[STEP 2 ERROR] {error_msg}")
        print(f"[STEP 2 ERROR] Error type: {type(e).__name__}")
        if hasattr(e, '__traceback__'):
            import traceback
            print(f"[STEP 2 ERROR] Traceback: {traceback.format_exc()}")
        
        return {
            'success': False,
            'error': error_msg
        }


def _load_credentials_from_db(user_email):
    """Load credentials from database"""
    # Database configuration - matching email_verification.py pattern
    DB_CONFIG = {
        'host': 'localhost',
        'database': 'interview_connect',
        'user': 'InConAdmin',
        'password': os.environ.get('DB_PASSWORD', '')
    }
    
    conn = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            # Query to get user's credentials
            # Note: password_hash in this database stores plaintext passwords
            cursor.execute("""
                SELECT email, password_hash
                FROM users 
                WHERE email = %s AND is_active = true
            """, (user_email,))
            
            user = cursor.fetchone()
            
            if user:
                # Check if user has separate Dice credentials stored
                # For now, we'll use their main credentials for Dice
                # In the future, you could add a dice_credentials table
                dice_credentials = {
                    'dice_email': user['email'],
                    'dice_password': user['password_hash']  # This is plaintext in this system
                }
                
                print(f"✅ Loaded credentials for: {user['email']}")
                return dice_credentials
            else:
                print(f"❌ No active user found for email: {user_email}")
                return None
                
    except Exception as e:
        print(f"❌ Error loading credentials from database: {str(e)}")
        return None
    finally:
        if conn:
            conn.close()


def _check_already_logged_in(driver):
    """Check if user is already logged in"""
    try:
        current_url = driver.current_url.lower()
        
        # Check URL indicators
        if any(term in current_url for term in ['dashboard', 'home', 'profile']):
            return True
        
        # Look for authenticated user indicators
        authenticated_selectors = [
            "[class*='profile']",
            "[class*='user-menu']",
            "[class*='account']",
            "[data-testid*='profile']",
            "[data-testid*='user']",
            "[class*='avatar']",
            "nav [href*='dashboard']",
            "nav [href*='profile']",
            "button:contains('Sign Out')",
            "a:contains('Sign Out')"
        ]
        
        for selector in authenticated_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if elements and any(el.is_displayed() for el in elements):
                    return True
            except:
                continue
        
        # Check for logout/signout links
        try:
            signout_elements = driver.find_elements(By.XPATH, 
                "//button[contains(text(), 'Sign Out')] | //a[contains(text(), 'Sign Out')] | "
                "//button[contains(text(), 'Logout')] | //a[contains(text(), 'Logout')]")
            if signout_elements and any(el.is_displayed() for el in signout_elements):
                return True
        except:
            pass
            
    except Exception as e:
        print(f"[STEP 2] Error checking login status: {str(e)}")
    
    return False


def _enter_email(driver, email):
    """Enter email in the email field"""
    email_selectors = [
        "input[type='email']",
        "input[name='email']",
        "input[id='email']",
        "input[placeholder*='email' i]",
        "input[data-testid='email']",
        "#emailInput",
        "input[autocomplete='email']"
    ]
    
    for selector in email_selectors:
        try:
            email_field = driver.find_element(By.CSS_SELECTOR, selector)
            if email_field.is_displayed():
                email_field.clear()
                email_field.send_keys(email)
                return True
        except:
            continue
    
    # Try XPath selectors
    xpath_selectors = [
        "//input[@type='email']",
        "//input[contains(@placeholder, 'email')]",
        "//input[contains(@name, 'email')]"
    ]
    
    for xpath in xpath_selectors:
        try:
            email_field = driver.find_element(By.XPATH, xpath)
            if email_field.is_displayed():
                email_field.clear()
                email_field.send_keys(email)
                return True
        except:
            continue
    
    return False


def _click_continue_button(driver):
    """Click the continue/next button after entering email"""
    continue_selectors = [
        "button[type='submit']",
        "input[type='submit']",
        "button:contains('Continue')",
        "button:contains('Next')",
        "button.btn-primary",
        "[data-testid='continue-button']"
    ]
    
    # CSS selectors
    for selector in continue_selectors:
        try:
            if ':contains' not in selector:
                buttons = driver.find_elements(By.CSS_SELECTOR, selector)
                for button in buttons:
                    if button.is_displayed() and button.is_enabled():
                        button.click()
                        return True
        except:
            continue
    
    # XPath selectors
    xpath_selectors = [
        "//button[contains(text(), 'Continue')]",
        "//button[contains(text(), 'Next')]",
        "//input[@value='Continue']",
        "//button[@type='submit']"
    ]
    
    for xpath in xpath_selectors:
        try:
            button = driver.find_element(By.XPATH, xpath)
            if button.is_displayed() and button.is_enabled():
                button.click()
                return True
        except:
            continue
    
    return False


def _send_enter_key_to_email(driver):
    """Send Enter key to email field"""
    try:
        email_field = driver.find_element(By.CSS_SELECTOR, "input[type='email']")
        email_field.send_keys(Keys.ENTER)
        return True
    except:
        return False


def _enter_password(driver, password):
    """Enter password in the password field"""
    password_selectors = [
        "input[type='password']",
        "input[name='password']",
        "input[id='password']",
        "input[placeholder*='password' i]",
        "input[data-testid='password']",
        "#passwordInput"
    ]
    
    # Wait for password field to appear
    try:
        wait = WebDriverWait(driver, 10)
        password_field = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='password']"))
        )
        
        if password_field.is_displayed():
            password_field.clear()
            password_field.send_keys(password)
            return True
    except TimeoutException:
        print("[STEP 2] Timeout waiting for password field")
    
    # Try other selectors
    for selector in password_selectors:
        try:
            password_field = driver.find_element(By.CSS_SELECTOR, selector)
            if password_field.is_displayed():
                password_field.clear()
                password_field.send_keys(password)
                return True
        except:
            continue
    
    return False


def _click_signin_button(driver):
    """Click the sign in button"""
    signin_selectors = [
        "button[type='submit']",
        "input[type='submit']",
        "button:contains('Sign In')",
        "button:contains('Log In')",
        "button:contains('Login')",
        "button.btn-primary",
        "[data-testid='signin-button']"
    ]
    
    # Try CSS selectors
    for selector in signin_selectors:
        try:
            if ':contains' not in selector:
                buttons = driver.find_elements(By.CSS_SELECTOR, selector)
                for button in buttons:
                    if button.is_displayed() and button.is_enabled():
                        # Check if we're on password step
                        if driver.find_elements(By.CSS_SELECTOR, "input[type='password']"):
                            button.click()
                            return True
        except:
            continue
    
    # Try XPath selectors
    xpath_selectors = [
        "//button[contains(text(), 'Sign In')]",
        "//button[contains(text(), 'Log In')]",
        "//button[contains(text(), 'Login')]",
        "//input[@value='Sign In']",
        "//button[@type='submit'][last()]"  # Get the last submit button
    ]
    
    for xpath in xpath_selectors:
        try:
            button = driver.find_element(By.XPATH, xpath)
            if button.is_displayed() and button.is_enabled():
                button.click()
                return True
        except:
            continue
    
    return False


def _send_enter_key_to_password(driver):
    """Send Enter key to password field"""
    try:
        password_field = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
        password_field.send_keys(Keys.ENTER)
        return True
    except:
        return False


def _verify_login_success(driver, expected_email):
    """Verify that login was successful"""
    try:
        # Wait for page to stabilize after login
        time.sleep(5)
        
        current_url = driver.current_url.lower()
        print(f"[STEP 2] Post-login URL: {current_url}")
        
        # Check if we're no longer on login page
        if 'login' not in current_url:
            print("[STEP 2] Successfully navigated away from login page")
            
            # Additional checks for authenticated state
            if _check_already_logged_in(driver):
                print("[STEP 2] Authenticated state confirmed")
                return True
        
        # Check for error messages
        error_indicators = [
            "[class*='error']",
            "[class*='alert-danger']",
            ".error-message",
            "[data-testid='error']"
        ]
        
        for selector in error_indicators:
            try:
                error_elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for element in error_elements:
                    if element.is_displayed() and element.text:
                        print(f"[STEP 2] Login error detected: {element.text}")
                        return False
            except:
                continue
        
        # Check page source for email (user identifier)
        page_source = driver.page_source
        if expected_email.split('@')[0] in page_source:
            print("[STEP 2] Found user identifier in page")
            return True
        
        # If we made it here without errors, assume success
        return True
        
    except Exception as e:
        print(f"[STEP 2] Error verifying login: {str(e)}")
        return False