from flask import jsonify
import os
import time
import threading
import json
from datetime import datetime
import importlib
import sys
import random
import string

# Try to import database-related modules
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False
    print("⚠️ psycopg2 not available - database features disabled")

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("⚠️ python-dotenv not available - using system environment variables")

class JobBoardAssistant:
    """Job Board Assistant - Industry-based orchestrator with subscription management"""
    
    def __init__(self):
        self.name = "Job Board Assistant"
        self.stop_requested = False
        
        # Subscription tier limits (weekly job board submissions)
        self.tier_limits = {
            'basic': {'weekly_submissions': 5, 'max_boards_per_session': 2},
            'plus': {'weekly_submissions': 15, 'max_boards_per_session': 5},
            'premium': {'weekly_submissions': 50, 'max_boards_per_session': 10}
        }
        
        # Load industry assistants
        self.industry_assistants = self._load_industry_assistants()
        
        print(f"✅ {self.name} Orchestrator initialized")
        print(f"Available industry assistants: {list(self.industry_assistants.keys())}")

    def _load_industry_assistants(self):
        """Load all available industry assistant modules"""
        assistants = {}
        
        # Add the current directory to Python path if not already there
        current_dir = os.path.dirname(os.path.abspath(__file__))
        if current_dir not in sys.path:
            sys.path.insert(0, current_dir)
        
        # Define the mapping of industries to their assistant modules
        industry_modules = {
            'Manufacturing': 'manufacturing_assistant',
            'Technology': 'technology_assistant',
            'Healthcare': 'healthcare_assistant',
            'Finance': 'finance_assistant',
            'Real_Estate': 'real_estate_assistant',
            'Retail': 'retail_assistant',
            'General': 'general_assistant',
            'Education': 'education_assistant',
            'Government': 'government_assistant',
            'Hospitality': 'hospitality_assistant',
            'Nonprofit': 'nonprofit_assistant'
        }
        
        for industry, module_name in industry_modules.items():
            try:
                # Try to import the module from job_board_assistant subdirectory
                module = importlib.import_module(f"job_board_assistant.{module_name}")
                
                # Get the assistant class (assumes class name follows pattern)
                class_name = f"{industry}Assistant"
                if hasattr(module, class_name):
                    assistants[industry] = (f"job_board_assistant.{module_name}", class_name)
                    print(f"✅ Loaded {industry} assistant")
                else:
                    print(f"⚠️ {industry} assistant class not found in {module_name}")
                    
            except ImportError as e:
                print(f"⚠️ Could not load {industry} assistant: {module_name} - {str(e)}")
            except Exception as e:
                print(f"❌ Error loading {industry} assistant: {str(e)}")
        
        return assistants

    def get_db_connection(self):
        """Get database connection"""
        if not DB_AVAILABLE:
            print("❌ Database not available")
            return None
            
        try:
            db_config = {
                'host': os.getenv('DB_HOST', 'localhost'),
                'database': os.getenv('DB_NAME', 'interview_connect'),
                'user': os.getenv('DB_USER', 'InConAdmin'),
                'password': os.getenv('DB_PASSWORD', ''),
                'port': os.getenv('DB_PORT', '5432')
            }
            return psycopg2.connect(**db_config)
        except Exception as e:
            print(f"❌ Database connection error: {str(e)}")
            return None

    def get_available_industries(self):
        """Get list of available industries"""
        default_industries = ['Manufacturing', 'Healthcare', 'Technology', 'Finance', 'Retail']
        
        if not DB_AVAILABLE:
            return default_industries
            
        try:
            conn = self.get_db_connection()
            if not conn:
                return default_industries
                
            cur = conn.cursor()
            cur.execute("SELECT DISTINCT industry FROM job_board_sites WHERE is_active = true ORDER BY industry")
            industries = [row[0] for row in cur.fetchall()]
            conn.close()
            
            return industries if industries else default_industries
            
        except Exception as e:
            print(f"❌ Error getting industries: {str(e)}")
            return default_industries

    def get_boards_for_industry(self, industry):
        """Get job boards for a specific industry from database"""
        if not DB_AVAILABLE:
            print("❌ Database not available")
            return []
            
        try:
            conn = self.get_db_connection()
            if not conn:
                return []
                
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            # Query job boards for specific industry using actual column names
            query = """
                SELECT id, site_name, site_url, agency_name, industry, 
                       agency_rating, automation_script, is_active, 
                       date_added, last_tested, success_rate
                FROM job_board_sites 
                WHERE industry = %s AND is_active = true
                ORDER BY site_name
            """
            
            cur.execute(query, (industry,))
            boards = cur.fetchall()
            conn.close()
            
            # Convert to list of dicts
            boards_list = [dict(board) for board in boards]
            
            print(f"Found {len(boards_list)} boards for {industry} industry")
            return boards_list
            
        except Exception as e:
            print(f"❌ Database error getting boards: {str(e)}")
            return []

    def check_tier_limits(self, user_tier, selected_boards_count):
        """Check if user can submit to selected number of boards based on tier"""
        # Normalize tier name to lowercase
        user_tier = user_tier.lower() if user_tier else 'basic'
        if user_tier not in self.tier_limits:
            user_tier = 'basic'
        
        limits = self.tier_limits[user_tier]
        
        # Check max boards per session
        if selected_boards_count > limits['max_boards_per_session']:
            return False, f"Your {user_tier} tier allows maximum {limits['max_boards_per_session']} boards per session"
        
        return True, "Within limits"
    
    def get_user_profile_from_db(self, user_email):
        """Get complete user profile from database"""
        if not DB_AVAILABLE:
            print("❌ Database not available")
            return None
            
        try:
            conn = self.get_db_connection()
            if not conn:
                return None
                
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            # Query ALL user data from users table
            cur.execute("""
                SELECT id, email, first_name, last_name, phone, 
                       address, city, state, zip_code, country,
                       tier, created_at, is_active
                FROM users 
                WHERE email = %s
            """, (user_email,))
            
            user_data = cur.fetchone()
            conn.close()
            
            if user_data:
                user_profile = dict(user_data)
                print(f"✅ Retrieved user profile for {user_email}")
                return user_profile
            else:
                print(f"❌ No user found with email: {user_email}")
                return None
                
        except Exception as e:
            print(f"❌ Database error getting user profile: {str(e)}")
            return None

    def record_board_submissions(self, user_email, industry, boards):
        """Record job board submissions to database"""
        if not DB_AVAILABLE:
            print("⚠️ Database not available - cannot record submissions")
            return False
            
        try:
            conn = self.get_db_connection()
            if not conn:
                return False
                
            cur = conn.cursor()
            
            # Get user_id
            cur.execute("SELECT id FROM users WHERE email = %s", (user_email,))
            user_result = cur.fetchone()
            
            if not user_result:
                print(f"❌ User not found: {user_email}")
                conn.close()
                return False
            
            user_id = user_result[0]
            
            # Record each board submission
            for board in boards:
                app_ref = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
                
                cur.execute("""
                    INSERT INTO application_stats 
                    (user_id, app_ref, platform, job_title, company, status, date_applied, submitted_at)
                    VALUES (%s, %s, %s, %s, %s, %s, CURRENT_DATE, NOW())
                """, (
                    user_id, 
                    app_ref, 
                    f"job-board-{board['site_name'].lower().replace(' ', '-')}", 
                    f"{industry} Position",
                    board.get('agency_name', 'Agency'),
                    'submitted'
                ))
            
            conn.commit()
            print(f"✅ Recorded {len(boards)} job board submissions for {user_email}")
            conn.close()
            return True
            
        except Exception as e:
            print(f"❌ Error recording submissions: {str(e)}")
            if conn:
                conn.rollback()
                conn.close()
            return False

    def start_automation(self, request, session):
        """Start Job Board Assistant orchestration"""
        user_email = session.get('user_email', '')
        user_tier = session.get('user_tier', 'basic')
        
        if not user_email:
            return jsonify({
                'status': 'error',
                'message': 'No user email in session'
            }), 400
        
        # Get complete user profile from database
        user_profile = self.get_user_profile_from_db(user_email)
        
        if not user_profile:
            return jsonify({
                'status': 'error',
                'message': 'User profile not found in database'
            }), 400
        
        user_id = user_profile.get('id')
        
        # Get selected industry from request
        selected_industry = request.form.get('industry', 'Manufacturing')
        
        # Get available industries
        available_industries = self.get_available_industries()
        
        # Validate industry selection
        if not selected_industry or selected_industry not in available_industries:
            return jsonify({
                'status': 'error',
                'message': 'Please select a valid industry',
                'available_industries': available_industries
            }), 400
        
        # Check if we have an assistant for this industry
        if selected_industry not in self.industry_assistants:
            return jsonify({
                'status': 'error',
                'message': f'No automation available for {selected_industry} industry yet.'
            }), 400
        
        # Get available boards for industry
        available_boards = self.get_boards_for_industry(selected_industry)
        
        if not available_boards:
            return jsonify({
                'status': 'error',
                'message': f'No active boards found for {selected_industry} industry in database.'
            }), 400
        
        # For now, select all available boards
        selected_boards = available_boards
        
        # Check tier limits
        can_proceed, limit_message = self.check_tier_limits(user_tier, len(selected_boards))
        if not can_proceed:
            return jsonify({
                'status': 'error',
                'message': limit_message,
                'selected_count': len(selected_boards),
                'tier_limits': self.tier_limits[user_tier.lower()]
            }), 400
        
        print(f"\n✅ Job Board Assistant Orchestrator started")
        print(f"User: {user_email} (ID: {user_id}, Tier: {user_tier})")
        print(f"Industry: {selected_industry}")
        print(f"Selected Boards: {', '.join([b['site_name'] for b in selected_boards])}")
        
        # Reset stop flag
        self.stop_requested = False
        
        # Create session data with complete user profile
        session_data = {
            'user_id': user_profile['id'],
            'email': user_profile['email'],
            'first_name': user_profile.get('first_name', ''),
            'last_name': user_profile.get('last_name', ''),
            'phone': user_profile.get('phone', ''),
            'address': user_profile.get('address', ''),
            'city': user_profile.get('city', ''),
            'state': user_profile.get('state', ''),
            'zip_code': user_profile.get('zip_code', ''),
            'country': user_profile.get('country', 'USA'),
            'user_tier': user_tier,
            'resume_path': ''
        }
        
        # Handle resume upload if present
        if 'resume' in request.files:
            resume_file = request.files['resume']
            if resume_file and resume_file.filename:
                # Save resume file
                os.makedirs('uploads', exist_ok=True)
                resume_filename = f"resume_{user_email.replace('@', '_')}_{int(time.time())}.{resume_file.filename.split('.')[-1]}"
                resume_path = os.path.join('uploads', resume_filename)
                resume_file.save(resume_path)
                session_data['resume_path'] = resume_path
                print(f"📄 Resume uploaded: {resume_filename}")
        
        # Start background automation
        automation_thread = threading.Thread(
            target=self._run_industry_orchestration,
            args=(user_email, selected_industry, selected_boards, session_data)
        )
        automation_thread.daemon = True
        automation_thread.start()
        
        return jsonify({
            'status': 'success',
            'message': f'Job Board Assistant started for {selected_industry} industry!',
            'data': {
                'industry': selected_industry,
                'boards_count': len(selected_boards),
                'boards': [{'id': b['id'], 'name': b['site_name']} for b in selected_boards],
                'automation_status': 'running',
                'selected_boards': [b['site_name'] for b in selected_boards]
            }
        })

    def stop_automation(self):
        """Stop the automation process"""
        self.stop_requested = True
        print("✅ Stop requested for Job Board Assistant Orchestrator")
        return jsonify({
            'status': 'success',
            'message': 'Stop signal sent to Job Board Assistant'
        })

    def _run_industry_orchestration(self, user_email, industry, selected_boards, session_data):
        """Orchestrate industry-specific assistant execution"""
        try:
            print(f"\n{'='*60}")
            print(f"ORCHESTRATION STARTING")
            print(f"Industry: {industry}")
            print(f"User: {user_email} (ID: {session_data.get('user_id')})")
            print(f"Selected boards: {[b['site_name'] for b in selected_boards]}")
            print(f"{'='*60}\n")
            
            # Get the industry assistant
            industry_assistant = self._get_industry_assistant(industry)
            
            if not industry_assistant:
                print(f"❌ No assistant available for {industry}")
                # Still record the attempt
                self.record_board_submissions(user_email, industry, selected_boards)
                return
            
            # Set up the assistant
            industry_assistant.set_stop_flag_reference(self)
            industry_assistant.set_selected_boards(selected_boards)
            
            # Start the industry-specific automation with complete user data
            result = industry_assistant.start_automation(session_data)
            
            if result.get('success'):
                print(f"\n✅ {industry} assistant completed successfully")
                
                # Record successful submissions to database
                self.record_board_submissions(user_email, industry, selected_boards)
                
            else:
                print(f"\n❌ {industry} assistant failed: {result.get('message')}")
                
                # Record failed submissions
                if DB_AVAILABLE:
                    try:
                        conn = self.get_db_connection()
                        if conn:
                            cur = conn.cursor()
                            cur.execute("SELECT id FROM users WHERE email = %s", (user_email,))
                            user_result = cur.fetchone()
                            
                            if user_result:
                                user_id = user_result[0]
                                # Record single failed entry
                                app_ref = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
                                cur.execute("""
                                    INSERT INTO application_stats 
                                    (user_id, app_ref, platform, job_title, company, status, date_applied, submitted_at)
                                    VALUES (%s, %s, %s, %s, %s, %s, CURRENT_DATE, NOW())
                                """, (user_id, app_ref, f"job-board-{industry.lower()}", 
                                     f"{industry} Position", "Multiple", 'failed'))
                                conn.commit()
                            conn.close()
                    except Exception as e:
                        print(f"⚠️ Could not record failed submission: {str(e)}")
            
            print(f"\n{'='*60}")
            print(f"ORCHESTRATION COMPLETE")
            print(f"{'='*60}\n")
            
        except Exception as e:
            print(f"\n{'='*60}")
            print(f"ORCHESTRATION ERROR: {str(e)}")
            print(f"{'='*60}\n")
            import traceback
            traceback.print_exc()
            
            # Try to record error in database
            if DB_AVAILABLE:
                try:
                    conn = self.get_db_connection()
                    if conn:
                        cur = conn.cursor()
                        cur.execute("SELECT id FROM users WHERE email = %s", (user_email,))
                        user_result = cur.fetchone()
                        
                        if user_result:
                            user_id = user_result[0]
                            app_ref = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
                            cur.execute("""
                                INSERT INTO application_stats 
                                (user_id, app_ref, platform, job_title, company, status, date_applied, submitted_at)
                                VALUES (%s, %s, %s, %s, %s, %s, CURRENT_DATE, NOW())
                            """, (user_id, app_ref, f"job-board-{industry.lower()}", 
                                 f"{industry} Position - Error", str(e)[:100], 'failed'))
                            conn.commit()
                        conn.close()
                except:
                    pass

    def _get_industry_assistant(self, industry):
        """Get the appropriate industry assistant instance"""
        if industry not in self.industry_assistants:
            print(f"⚠️ No assistant registered for {industry}")
            return None
        
        try:
            module_name, class_name = self.industry_assistants[industry]
            
            # Import the module from job_board_assistant subdirectory
            module = importlib.import_module(module_name)
            
            # Get the class
            assistant_class = getattr(module, class_name)
            
            # Create instance
            assistant_instance = assistant_class()
            
            print(f"✅ Created {industry} assistant instance")
            return assistant_instance
            
        except Exception as e:
            print(f"❌ Error creating {industry} assistant: {str(e)}")
            import traceback
            traceback.print_exc()
            return None

# Make it compatible with direct script execution
if __name__ == "__main__":
    assistant = JobBoardAssistant()
    print("✅ Job Board Assistant loaded successfully")
    print(f"Available industries: {assistant.get_available_industries()}")