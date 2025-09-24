from flask import jsonify
import os
import time
import threading
import random
import string
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementNotInteractableException
import re
import psycopg2
from psycopg2.extras import RealDictCursor

# Try to import optional libraries
try:
    import PyPDF2
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    print("⚠️ PyPDF2 not available - resume parsing disabled")

try:
    from docx import Document
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False
    print("⚠️ python-docx not available - resume parsing disabled")

# Try to import dice assistant
try:
    # Add path resolution for dice assistant
    import sys
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)
    
    from dice_assistant.credentials import get_dice_credentials
    CREDENTIALS_AVAILABLE = True
except ImportError:
    CREDENTIALS_AVAILABLE = False
    print("⚠️ Credentials system not available")


# ============================================================================
# APPLICATION TRACKING CLASS
# ============================================================================

class ApplicationTracker:
    """Track application submissions in the database"""
    
    @staticmethod
    def get_db_connection():
        """Get database connection"""
        return psycopg2.connect(
            host="localhost",
            database="interview_connect",
            user="InConAdmin",
            password="your_password_here"  # Replace with actual password
        )
    
    @staticmethod
    def generate_simple_ref() -> str:
        """Generate a simple reference code like APP-2024-A1B2C3"""
        year = datetime.now().year
        # Generate 6 character alphanumeric code
        chars = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        return f"APP-{year}-{chars}"
    
    @staticmethod
    def log_application(user_email: str, platform: str, job_title: str, 
                       company: str, status: str = 'submitted') -> dict:
        """
        Log an application submission to the database
        
        Args:
            user_email: User's email address
            platform: Platform name (LinkedIn, Indeed, etc.)
            job_title: Job title applied for
            company: Company name
            status: Application status (submitted, failed, pending)
        
        Returns:
            Dict with success status and reference number
        """
        try:
            conn = ApplicationTracker.get_db_connection()
            cur = conn.cursor()
            
            # Get user_id from email (integer type)
            cur.execute("SELECT id FROM users WHERE email = %s", (user_email,))
            user_result = cur.fetchone()
            
            if not user_result:
                print(f"⚠️ Warning: User not found for email {user_email}")
                return {'success': False, 'error': 'User not found'}
            
            user_id = user_result[0]  # This is an integer
            
            # Generate simple reference code
            app_ref = ApplicationTracker.generate_simple_ref()
            
            # Insert application record (id auto-increments)
            cur.execute("""
                INSERT INTO application_stats 
                (user_id, app_ref, platform, job_title, company, status)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id, app_ref
            """, (
                user_id,
                app_ref,
                platform,
                job_title[:255] if job_title else 'Not Specified',  # Truncate if too long
                company[:255] if company else 'Not Specified',    # Truncate if too long
                status
            ))
            
            result = cur.fetchone()
            new_id = result[0]
            new_ref = result[1]
            
            conn.commit()
            cur.close()
            conn.close()
            
            print(f"✅ Logged application #{new_id}: {job_title} at {company} via {platform}")
            print(f"📋 Reference: {new_ref}")
            
            return {
                'success': True, 
                'id': new_id,
                'reference': new_ref
            }
            
        except Exception as e:
            print(f"❌ Error logging application: {str(e)}")
            if conn:
                conn.rollback()
                conn.close()
            return {'success': False, 'error': str(e)}


# ============================================================================
# APPLICATION ASSISTANT CLASS
# ============================================================================

class ApplicationAssistant:
    """Application Assistant - Multi-platform job application automation"""
    
    def __init__(self):
        self.name = "Application Assistant"
        self.supported_platforms = ['indeed', 'dice', 'glassdoor', 'ziprecruiter']
        self.tracker = ApplicationTracker()  # Initialize tracker
        print(f"✅ {self.name} initialized with tracking enabled")
    
    def parse_resume(self, request, session):
        """Parse uploaded resume and extract information"""
        user_email = session.get('user_email')
        print(f"📄 Resume parsing requested by: {user_email}")
        
        if 'resume' not in request.files:
            print("❌ No resume file in request")
            return jsonify({'status': 'error', 'message': 'No resume file uploaded'}), 400
        
        resume_file = request.files['resume']
        
        if resume_file.filename == '':
            print("❌ Empty filename")
            return jsonify({'status': 'error', 'message': 'No file selected'}), 400
        
        try:
            # Save uploaded file
            os.makedirs('uploads', exist_ok=True)
            resume_filename = f"resume_{user_email.split('@')[0]}_{int(time.time())}.{resume_file.filename.split('.')[-1]}"
            resume_path = os.path.join('uploads', resume_filename)
            resume_file.save(resume_path)
            print(f"📁 Resume saved to: {resume_path}")
            
            # Extract text from resume
            resume_text = ""
            if resume_filename.lower().endswith('.pdf'):
                if PDF_AVAILABLE:
                    resume_text = self._extract_text_from_pdf(resume_path)
                else:
                    return jsonify({'status': 'error', 'message': 'PDF parsing not available - install PyPDF2'}), 500
            elif resume_filename.lower().endswith(('.doc', '.docx')):
                if DOCX_AVAILABLE:
                    resume_text = self._extract_text_from_docx(resume_path)
                else:
                    return jsonify({'status': 'error', 'message': 'DOCX parsing not available - install python-docx'}), 500
            else:
                return jsonify({'status': 'error', 'message': 'Unsupported file format. Use PDF, DOC, or DOCX'}), 400
            
            if not resume_text.strip():
                return jsonify({'status': 'error', 'message': 'Could not extract text from resume'}), 400
            
            # Parse resume content
            parsed_data = self._parse_resume_content_advanced(resume_text)
            
            # Store parsed data in session
            session['parsed_resume_data'] = parsed_data
            session['resume_filename'] = resume_filename
            session['resume_path'] = resume_path
            
            print(f"✅ Resume parsed successfully: {parsed_data.get('firstName', 'Unknown')} {parsed_data.get('lastName', 'Unknown')}")
            
            return jsonify({
                'status': 'success',
                'message': 'Resume parsed successfully',
                'data': parsed_data
            })
            
        except Exception as e:
            print(f"❌ Resume parsing error: {str(e)}")
            return jsonify({'status': 'error', 'message': f'Error parsing resume: {str(e)}'}), 500
    
    def start_automation(self, request, session):
        """Start Application Assistant automation"""
        user_email = session.get('user_email')
        print(f"🎯 ORCHESTRATOR: Automation requested by: {user_email}")
        
        try:
            # Get form data - handle both JSON and form data
            if request.is_json:
                form_data = request.get_json()
                print("📥 ORCHESTRATOR: Received JSON data")
            else:
                form_data = request.form.to_dict()
                print("📥 ORCHESTRATOR: Received form data")
            
            print(f"📋 ORCHESTRATOR: Form data keys: {list(form_data.keys())}")
            
            # Extract selected platforms with multiple strategies
            selected_platforms = []
            
            # Strategy 1: Direct platforms key
            if 'platforms' in form_data:
                platforms_data = form_data['platforms']
                if isinstance(platforms_data, list):
                    selected_platforms = platforms_data
                elif isinstance(platforms_data, str):
                    # Could be comma-separated or JSON string
                    try:
                        import json
                        selected_platforms = json.loads(platforms_data)
                    except:
                        selected_platforms = [p.strip() for p in platforms_data.split(',') if p.strip()]
                print(f"🎯 ORCHESTRATOR: Platforms from 'platforms' key: {selected_platforms}")
            
            # Strategy 2: Check individual platform checkboxes
            if not selected_platforms:
                for platform in self.supported_platforms:
                    if form_data.get(f'platform-{platform}') or form_data.get(platform):
                        selected_platforms.append(platform)
                print(f"🎯 ORCHESTRATOR: Platforms from checkboxes: {selected_platforms}")
            
            # Strategy 3: Look for any platform-related keys
            if not selected_platforms:
                for key, value in form_data.items():
                    if 'platform' in key.lower() and value:
                        for platform in self.supported_platforms:
                            if platform in key.lower():
                                selected_platforms.append(platform)
                print(f"🎯 ORCHESTRATOR: Platforms from key analysis: {selected_platforms}")
            
            # Default fallback
            if not selected_platforms:
                print("⚠️ ORCHESTRATOR: No platforms detected, checking for any automation request")
                selected_platforms = ['indeed']  # Safe default
            
            print(f"🎯 ORCHESTRATOR: User selected platforms: {selected_platforms}")
            
            # Validate platforms
            valid_platforms = [p for p in selected_platforms if p in self.supported_platforms]
            if not valid_platforms:
                return jsonify({'status': 'error', 'message': 'No valid platforms selected'}), 400
            
            print(f"✅ ORCHESTRATOR: Valid platforms confirmed: {valid_platforms}")
            
            # Get user data from form
            user_data = {
                'firstName': form_data.get('firstName', ''),
                'lastName': form_data.get('lastName', ''),
                'email': form_data.get('email', ''),
                'phone': form_data.get('phone', ''),
                'dob': form_data.get('dob', ''),
                'street': form_data.get('street', ''),
                'city': form_data.get('city', ''),
                'state': form_data.get('state', ''),
                'zipCode': form_data.get('zipCode', ''),
                'skills': form_data.get('skills', ''),
                'certifications': form_data.get('certifications', ''),
                'race': form_data.get('race', ''),
                'gender': form_data.get('gender', ''),
                'veteranStatus': form_data.get('veteranStatus', ''),
                'disabilityStatus': form_data.get('disabilityStatus', ''),
                'jobTitle': form_data.get('jobTitle',''),
                'location': form_data.get('location', ''),  # Add location from form
                'name': f"{form_data.get('firstName', '')} {form_data.get('lastName', '')}"
            }
            
            # Get resume data if available
            resume_data = session.get('parsed_resume_data')
            resume_path = session.get('resume_path')
            if resume_path:
                user_data['resume_path'] = resume_path
            
            print(f"🚀 ORCHESTRATOR: Starting delegation to {len(valid_platforms)} specialized assistants")
            
            # Start automation in background thread
            automation_thread = threading.Thread(
                target=self._run_automation,
                args=(user_data, resume_data, valid_platforms, user_email)
            )
            automation_thread.daemon = True
            automation_thread.start()
            
            return jsonify({
                'status': 'success',
                'message': f'Application Assistant started for {len(valid_platforms)} platforms!',
                'data': {
                    'name': user_data['name'],
                    'platforms': valid_platforms,
                    'location': user_data.get('location', 'Not specified'),  # Include location in response
                    'jobTitle': user_data.get('jobTitle', 'Not specified'),  # Include job title in response
                    'resume_uploaded': resume_path is not None
                }
            })
            
        except Exception as e:
            print(f"❌ ORCHESTRATOR: Application Assistant error: {str(e)}")
            return jsonify({'status': 'error', 'message': str(e)}), 500
    
    def _extract_text_from_pdf(self, pdf_path):
        """Extract text from PDF resume"""
        try:
            print(f"📄 Extracting text from PDF: {pdf_path}")
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""
                for page_num, page in enumerate(pdf_reader.pages):
                    page_text = page.extract_text()
                    text += page_text + "\n"
                    print(f"📄 Extracted {len(page_text)} characters from page {page_num + 1}")
            print(f"📄 Total extracted text: {len(text)} characters")
            return text
        except Exception as e:
            print(f"❌ Error reading PDF: {str(e)}")
            return ""
    
    def _extract_text_from_docx(self, docx_path):
        """Extract text from DOCX resume"""
        try:
            print(f"📄 Extracting text from DOCX: {docx_path}")
            doc = Document(docx_path)
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            print(f"📄 Extracted {len(text)} characters from DOCX")
            return text
        except Exception as e:
            print(f"❌ Error reading DOCX: {str(e)}")
            return ""
    
    def _parse_resume_content_advanced(self, resume_text):
        """Advanced resume parsing to extract comprehensive information"""
        parsed_data = {
            'firstName': '',
            'lastName': '',
            'email': '',
            'phone': '',
            'city': '',
            'state': '',
            'zipCode': '',
            'skills': '',
            'certifications': '',
            'summary': '',
            'experience_years': 0,
            'job_titles': [],
            'education': []
        }
        
        if not resume_text:
            return parsed_data
        
        try:
            lines = resume_text.split('\n')
            text_lower = resume_text.lower()
            print(f"📊 Parsing resume with {len(lines)} lines")
            
            # Extract email
            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            email_matches = re.findall(email_pattern, resume_text)
            if email_matches:
                parsed_data['email'] = email_matches[0]
                print(f"📧 Found email: {parsed_data['email']}")
            
            # Extract phone number
            phone_pattern = r'(\(?\d{3}\)?[-.\\s]?\d{3}[-.\\s]?\d{4})'
            phone_matches = re.findall(phone_pattern, resume_text)
            if phone_matches:
                parsed_data['phone'] = phone_matches[0]
                print(f"📞 Found phone: {parsed_data['phone']}")
            
            # Extract name (first few lines usually contain name)
            for line in lines[:5]:
                line = line.strip()
                if line and len(line.split()) >= 2 and not '@' in line and not any(char.isdigit() for char in line):
                    words = line.split()
                    if len(words) >= 2:
                        parsed_data['firstName'] = words[0]
                        parsed_data['lastName'] = words[1]
                        print(f"👤 Found name: {parsed_data['firstName']} {parsed_data['lastName']}")
                        break
            
            # Extract city, state, zip
            address_pattern = r'([A-Za-z\s]+),\s*([A-Z]{2})\s*(\d{5})'
            address_matches = re.findall(address_pattern, resume_text)
            if address_matches:
                city, state, zip_code = address_matches[0]
                parsed_data['city'] = city.strip()
                parsed_data['state'] = state.strip()
                parsed_data['zipCode'] = zip_code.strip()
                print(f"📍 Found location: {parsed_data['city']}, {parsed_data['state']} {parsed_data['zipCode']}")
            
            # Extract skills
            skills_section = ""
            skill_keywords = ['skills', 'technical skills', 'core competencies', 'expertise']
            for keyword in skill_keywords:
                if keyword in text_lower:
                    start_idx = text_lower.find(keyword)
                    skills_section = resume_text[start_idx:start_idx+500]
                    break
            
            if skills_section:
                skill_patterns = [
                    r'(?i)(python|java|javascript|sql|html|css|react|node\.js|angular|vue)',
                    r'(?i)(communication|leadership|problem solving|teamwork|management)',
                    r'(?i)(project management|agile|scrum|devops|git|docker|aws|azure)'
                ]
                found_skills = []
                for pattern in skill_patterns:
                    matches = re.findall(pattern, skills_section)
                    found_skills.extend(matches)
                if found_skills:
                    parsed_data['skills'] = ', '.join(list(set(found_skills))[:10])
                    print(f"🛠️ Found skills: {parsed_data['skills']}")
            
            # Extract certifications
            cert_keywords = ['certification', 'certified', 'license', 'credential']
            certifications = []
            for line in lines:
                line_lower = line.lower()
                if any(keyword in line_lower for keyword in cert_keywords):
                    certifications.append(line.strip())
            if certifications:
                parsed_data['certifications'] = '; '.join(certifications[:3])
                print(f"🏆 Found certifications: {parsed_data['certifications']}")
            
            print(f"✅ Resume parsing completed successfully")
            
        except Exception as e:
            print(f"❌ Advanced resume parsing error: {str(e)}")
        
        return parsed_data
    
    def _track_application(self, user_email, platform, job_title, company, status='submitted'):
        """
        Track an application submission
        
        Args:
            user_email: User's email
            platform: Platform name
            job_title: Job title applied for
            company: Company name
            status: Application status
        
        Returns:
            Tracking result dictionary
        """
        result = ApplicationTracker.log_application(
            user_email=user_email,
            platform=platform,
            job_title=job_title or 'Not Specified',
            company=company or 'Not Specified',
            status=status
        )
        
        if result['success']:
            print(f"📊 Dashboard will update with reference: {result['reference']}")
        else:
            print(f"⚠️ Failed to track application: {result.get('error', 'Unknown error')}")
        
        return result
    
    def _run_automation(self, user_data, resume_data, selected_platforms, user_email):
        """Run automation for multiple platforms"""
        results = {}
        total_applications = 0
        tracked_applications = []
        
        try:
            print(f"📤 ORCHESTRATOR: Delegating to {len(selected_platforms)} platform assistants")
            print(f"📍 ORCHESTRATOR: Job Title: {user_data.get('jobTitle', 'Not specified')}")
            print(f"📍 ORCHESTRATOR: Location: {user_data.get('location', 'Not specified')}")
            
            for platform in selected_platforms:
                print(f"📤 ORCHESTRATOR: Delegating {platform} to specialized assistant...")
                
                try:
                    if platform == 'indeed':
                        result = self._indeed_automation(user_data, resume_data, user_email)
                    elif platform == 'dice':
                        result = self._dice_automation(user_data, resume_data, user_email)
                    elif platform == 'glassdoor':
                        result = self._glassdoor_automation(user_data, resume_data, user_email)
                    elif platform == 'ziprecruiter':
                        result = self._ziprecruiter_automation(user_data, resume_data, user_email)
                    else:
                        result = {'success': False, 'error': f'Platform {platform} not implemented yet'}
                    
                    results[platform] = result
                    print(f"📥 ORCHESTRATOR: Received result from {platform} assistant")
                    
                    if result.get('success'):
                        applications = result.get('total_applications', 0)
                        total_applications += applications
                        print(f"✅ ORCHESTRATOR: {platform.title()} completed: {applications} applications")
                        
                        # Track successful applications
                        # If the platform returns specific job details, use them
                        # Otherwise, use generic tracking
                        if result.get('jobs_applied'):
                            # Platform returned specific job details
                            for job in result['jobs_applied']:
                                track_result = self._track_application(
                                    user_email=user_email,
                                    platform=platform,
                                    job_title=job.get('title', user_data.get('jobTitle', 'Not Specified')),
                                    company=job.get('company', 'Various'),
                                    status='submitted'
                                )
                                tracked_applications.append(track_result)
                        else:
                            # Generic tracking for the platform
                            for i in range(applications):
                                track_result = self._track_application(
                                    user_email=user_email,
                                    platform=platform,
                                    job_title=user_data.get('jobTitle', 'Not Specified'),
                                    company=f'Company {i+1}',
                                    status='submitted'
                                )
                                tracked_applications.append(track_result)
                    else:
                        print(f"❌ ORCHESTRATOR: {platform.title()} failed: {result.get('error', 'Unknown error')}")
                        
                        # Track failed attempt
                        self._track_application(
                            user_email=user_email,
                            platform=platform,
                            job_title=user_data.get('jobTitle', 'Not Specified'),
                            company='N/A',
                            status='failed'
                        )
                    
                    if len(selected_platforms) > 1:
                        print(f"⏳ ORCHESTRATOR: Waiting 15 seconds before next platform...")
                        time.sleep(15)
                        
                except Exception as e:
                    print(f"❌ ORCHESTRATOR: Error with {platform}: {str(e)}")
                    results[platform] = {'success': False, 'error': str(e)}
                    
                    # Track error
                    self._track_application(
                        user_email=user_email,
                        platform=platform,
                        job_title=user_data.get('jobTitle', 'Not Specified'),
                        company='N/A',
                        status='failed'
                    )
            
            print(f"📊 ORCHESTRATOR: Aggregated results - {total_applications} applications across {len(selected_platforms)} platforms")
            print(f"📊 ORCHESTRATOR: Tracked {len(tracked_applications)} applications in database")
            
        except Exception as e:
            print(f"❌ ORCHESTRATOR: Automation error: {str(e)}")
    
    def _indeed_automation(self, user_data, resume_data, user_email):
        """Indeed automation - NOT YET IMPLEMENTED"""
        print(f"🔍 INDEED: Starting automation for {user_data['name']}")
        print(f"📍 INDEED: Job Title: {user_data.get('jobTitle', 'Not specified')}")
        print(f"📍 INDEED: Location: {user_data.get('location', 'Not specified')}")
        
        # For demo purposes, simulate some applications
        # Remove this when you implement real Indeed automation
        demo_applications = [
            {'title': 'Software Engineer', 'company': 'Tech Corp'},
            {'title': 'Senior Developer', 'company': 'Innovation Labs'},
        ]
        
        # Track demo applications
        for job in demo_applications:
            self._track_application(
                user_email=user_email,
                platform='indeed',
                job_title=job['title'],
                company=job['company'],
                status='submitted'
            )
        
        return {
            'success': True,  # Change to False when not demo
            'total_applications': len(demo_applications),
            'jobs_applied': demo_applications,
            'message': 'Demo mode - Indeed automation not yet implemented'
        }
    
    def _dice_automation(self, user_data, resume_data, user_email):
        """Dice automation using dice assistant"""
        print(f"🎲 DICE: Starting automation for {user_data['name']}")
        print(f"📍 DICE: Job Title: {user_data.get('jobTitle', 'Not specified')}")
        print(f"📍 DICE: Location: {user_data.get('location', 'Not specified')}")
        
        # Import and use dice assistant
        dice_assistant_path = os.path.join(os.path.dirname(__file__), 'dice-assistant.py')
        
        if not os.path.exists(dice_assistant_path):
            error_msg = f"❌ DICE: dice-assistant.py not found at {dice_assistant_path}"
            print(error_msg)
            return {'success': False, 'error': error_msg}
        
        # Dynamic import of dice assistant
        import importlib.util
        spec = importlib.util.spec_from_file_location("dice_assistant", dice_assistant_path)
        dice_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(dice_module)
        
        # Pass user_email to DiceAssistant to get credentials from database
        print(f"📧 DICE: Creating DiceAssistant with user email: {user_email}")
        dice_assistant = dice_module.DiceAssistant(user_email)
        
        # Pass user_data with location to dice assistant
        print("🚀 DICE: Starting actual Dice automation...")
        result = dice_assistant.run_automation(user_data, resume_data)
        
        # The dice assistant should return jobs_applied list
        # If it doesn't, we'll track generically
        if result.get('success'):
            jobs_applied = result.get('jobs_applied', [])
            if jobs_applied:
                for job in jobs_applied:
                    self._track_application(
                        user_email=user_email,
                        platform='dice',
                        job_title=job.get('title', user_data.get('jobTitle', 'Not Specified')),
                        company=job.get('company', 'Unknown'),
                        status='submitted'
                    )
            else:
                # Generic tracking if no specific jobs returned
                for i in range(result.get('total_applications', 0)):
                    self._track_application(
                        user_email=user_email,
                        platform='dice',
                        job_title=user_data.get('jobTitle', 'Not Specified'),
                        company=f'Dice Company {i+1}',
                        status='submitted'
                    )
        
        print(f"✅ DICE: Delegation completed")
        return result
    
    def _glassdoor_automation(self, user_data, resume_data, user_email):
        """Glassdoor automation - placeholder"""
        print(f"🏢 GLASSDOOR: Automation not yet implemented")
        return {'success': False, 'error': 'Glassdoor automation coming soon'}
    
    def _ziprecruiter_automation(self, user_data, resume_data, user_email):
        """ZipRecruiter automation - placeholder"""
        print(f"📮 ZIPRECRUITER: Automation not yet implemented")
        return {'success': False, 'error': 'ZipRecruiter automation coming soon'}
    
    def _create_robust_driver(self, headless=True):
        """Create a robust Chrome driver with advanced configuration
        
        Args:
            headless: Boolean to run in headless mode (default: True)
        """
        chrome_options = Options()
        
        # HEADLESS MODE - Run invisibly in background
        if headless:
            chrome_options.add_argument("--headless=new")  # Use new headless mode (Chrome 109+)
            chrome_options.add_argument("--window-size=1920,1080")  # Set window size for headless
            print("🤖 Running in HEADLESS mode (invisible)")
        else:
            chrome_options.add_argument("--start-maximized")
            print("👁️ Running in VISIBLE mode")
        
        # Essential options for stability
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # Additional stealth options
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--allow-running-insecure-content")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-plugins")
        chrome_options.add_argument("--disable-images")  # Faster loading
        chrome_options.add_argument("--disable-javascript-harmony-shipping")
        chrome_options.add_argument("--disable-default-apps")
        
        # Headless-specific optimizations
        if headless:
            chrome_options.add_argument("--disable-gpu")  # Disable GPU in headless
            chrome_options.add_argument("--disable-software-rasterizer")
            chrome_options.add_argument("--disable-dev-tools")
            chrome_options.add_argument("--no-zygote")
            chrome_options.add_argument("--single-process")  # Better for headless
            chrome_options.add_argument("--disable-setuid-sandbox")
            chrome_options.add_argument("--disable-accelerated-2d-canvas")
            chrome_options.add_argument("--disable-webgl")
            chrome_options.add_argument("--disable-threaded-animation")
            chrome_options.add_argument("--disable-threaded-scrolling")
            chrome_options.add_argument("--disable-background-timer-throttling")
            chrome_options.add_argument("--disable-renderer-backgrounding")
            chrome_options.add_argument("--disable-features=VizDisplayCompositor")
            chrome_options.add_argument("--disable-ipc-flooding-protection")
        
        
        # User agent to appear more human (works in headless too)
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        # Performance improvements for headless
        if headless:
            prefs = {
                'profile.default_content_setting_values': {
                    'images': 2,  # Block images
                    'plugins': 2,  # Block plugins
                    'popups': 2,  # Block popups
                    'geolocation': 2,  # Block location
                    'notifications': 2,  # Block notifications
                    'media_stream': 2,  # Block media stream
                    'media_stream_mic': 2,  # Block microphone
                    'media_stream_camera': 2,  # Block camera
                    'protocol_handlers': 2,  # Block protocol handlers
                    'ppapi_broker': 2,  # Block PPAPI broker
                    'automatic_downloads': 2,  # Block automatic downloads
                    'midi_sysex': 2,  # Block MIDI sysex
                    'push_messaging': 2,  # Block push messages
                    'ssl_cert_decisions': 2,  # Block SSL cert decisions
                    'metro_switch_to_desktop': 2,  # Block metro switch
                    'protected_media_identifier': 2,  # Block protected media identifier
                    'app_banner': 2,  # Block app banner
                    'site_engagement': 2,  # Block site engagement
                    'durable_storage': 2  # Block durable storage
                }
            }
            chrome_options.add_experimental_option('prefs', prefs)
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                print(f"🔧 Creating Chrome driver (attempt {attempt + 1})...")
                
                # Create service with logging suppressed in headless mode
                service = Service(ChromeDriverManager().install())
                if headless:
                    service.log_path = 'NUL' if os.name == 'nt' else '/dev/null'
                
                driver = webdriver.Chrome(
                    service=service,
                    options=chrome_options
                )
                
                # Execute scripts to hide automation (works in headless too)
                driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
                driver.execute_script("Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]})")
                driver.execute_script("Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']})")
                
                # Additional stealth for headless
                if headless:
                    driver.execute_cdp_cmd('Page.setWebLifecycleState', {'state': 'active'})
                    driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                        "userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                    })
                
                print(f"✅ Chrome driver created successfully in {'HEADLESS' if headless else 'VISIBLE'} mode")
                return driver
                
            except Exception as e:
                print(f"❌ Driver creation attempt {attempt + 1} failed: {str(e)}")
                if attempt == max_retries - 1:
                    raise Exception(f"Failed to create driver after {max_retries} attempts")
                time.sleep(2)