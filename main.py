from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
import os
import sys
import time
import psycopg2
from psycopg2.extras import RealDictCursor
import random
import string
import json

# Add ServiceScripts to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'ServiceScripts'))

# Import the assistant modules
import importlib.util

# Configure Flask to find templates in correct location
current_dir = os.path.dirname(os.path.abspath(__file__))
templates_current = os.path.join(current_dir, 'templates')
templates_parent = os.path.join(os.path.dirname(current_dir), 'templates')

if os.path.exists(templates_current):
    template_folder = templates_current
elif os.path.exists(templates_parent):
    template_folder = templates_parent
else:
    template_folder = templates_current
    os.makedirs(template_folder, exist_ok=True)

print(f"Using template folder: {template_folder}")

app = Flask(__name__,
    template_folder=template_folder,
    static_folder=os.path.join(current_dir, 'static') if os.path.exists(os.path.join(current_dir, 'static')) else None
)

app.secret_key = 'your-ultra-secure-secret-key-change-this-in-production'

# Database configuration
DB_CONFIG = {
    'host': 'localhost',
    'database': 'interview_connect',
    'user': 'InConAdmin',
    'password': os.environ.get('DB_PASSWORD', '')  # Set via environment variable
}

# Load application-assistant.py
try:
    app_assistant_spec = importlib.util.spec_from_file_location(
        "application_assistant",
        os.path.join(os.path.dirname(__file__), 'application-assistant.py')
    )
    application_assistant_module = importlib.util.module_from_spec(app_assistant_spec)
    app_assistant_spec.loader.exec_module(application_assistant_module)
    app_assistant = application_assistant_module.ApplicationAssistant()
    print("✅ Application Assistant loaded successfully")
except Exception as e:
    print(f"❌ Error loading Application Assistant: {str(e)}")
    app_assistant = None

# Load job-board-assistant.py
try:
    job_assistant_spec = importlib.util.spec_from_file_location(
        "job_board_assistant",
        os.path.join(os.path.dirname(__file__), 'job-board-assistant.py')
    )
    job_board_assistant_module = importlib.util.module_from_spec(job_assistant_spec)
    job_assistant_spec.loader.exec_module(job_board_assistant_module)
    job_assistant = job_board_assistant_module.JobBoardAssistant()
    print("✅ Job Board Assistant loaded successfully")
except Exception as e:
    print(f"❌ Error loading Job Board Assistant: {str(e)}")
    job_assistant = None

# ============================================================================
# CONFIGURATION CONSTANTS
# ============================================================================

SESSION_TIMEOUT_MINUTES = 30

RESUME_LIMITS = {
    'basic': 1,
    'plus': 3,
    'premium': 5
}

# ============================================================================
# DATABASE FUNCTIONS
# ============================================================================

def get_db_connection():
    """Create and return a database connection"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        print(f"Database connection error: {str(e)}")
        return None

def verify_user_credentials(email, password):
    """Verify user credentials against database"""
    conn = get_db_connection()
    if not conn:
        return None
    
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                SELECT id, email, tier, is_active 
                FROM users 
                WHERE email = %s AND password_hash = %s AND is_active = true
            """, (email, password))
            
            user = cursor.fetchone()
            return user
            
    except Exception as e:
        print(f"Error verifying credentials: {str(e)}")
        return None
    finally:
        conn.close()

def get_user_profile(user_id):
    """Get user profile information"""
    conn = get_db_connection()
    if not conn:
        return None
    
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            # Check if user_profiles table exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'user_profiles'
                );
            """)
            
            if cursor.fetchone()['exists']:
                # Get full profile with join
                cursor.execute("""
                    SELECT u.*, up.*
                    FROM users u
                    LEFT JOIN user_profiles up ON u.id = up.user_id
                    WHERE u.id = %s
                """, (user_id,))
            else:
                # Get basic info from users table
                cursor.execute("""
                    SELECT email
                    FROM users
                    WHERE id = %s
                """, (user_id,))
            
            return cursor.fetchone()
            
    except Exception as e:
        print(f"Error getting user profile: {str(e)}")
        return None
    finally:
        conn.close()

def check_session_expired():
    """Check if user session has expired"""
    if 'user_id' not in session:
        return True
    
    if 'last_activity' not in session:
        return True
    
    last_activity = datetime.fromisoformat(session['last_activity'])
    if datetime.now() - last_activity > timedelta(minutes=SESSION_TIMEOUT_MINUTES):
        return True
    
    return False

def update_session_activity():
    """Update last activity timestamp"""
    session['last_activity'] = datetime.now().isoformat()

def get_resume_limit(tier):
    """Get resume upload limit for tier"""
    return RESUME_LIMITS.get(tier, 1)

# ============================================================================
# APPLICATION TRACKING FUNCTIONS (Simple Solution)
# ============================================================================

def record_application(user_email, platform, job_title, company='', status='submitted'):
    """Record an application to the database"""
    conn = get_db_connection()
    if not conn:
        print(f"❌ Failed to record application - no DB connection")
        return False
    
    try:
        with conn.cursor() as cursor:
            # Get user_id from email
            cursor.execute("SELECT id FROM users WHERE email = %s", (user_email,))
            user_result = cursor.fetchone()
            
            if not user_result:
                print(f"❌ User not found: {user_email}")
                return False
            
            user_id = user_result[0]
            
            # Generate a reference number
            app_ref = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
            
            # Insert application record
            cursor.execute("""
                INSERT INTO application_stats 
                (user_id, app_ref, platform, job_title, company, status, date_applied, submitted_at)
                VALUES (%s, %s, %s, %s, %s, %s, CURRENT_DATE, NOW())
            """, (user_id, app_ref, platform, job_title, company, status))
            
            conn.commit()
            print(f"✅ Recorded application: {platform} - {job_title}")
            return True
            
    except Exception as e:
        print(f"❌ Error recording application: {str(e)}")
        conn.rollback()
        return False
    finally:
        conn.close()

# ============================================================================
# APPLICATION TRACKING CLASS (for Dashboard)
# ============================================================================

class ApplicationTracker:
    """Track application submissions in the database"""
    
    @staticmethod
    def get_user_stats(user_email: str) -> dict:
        """Get application statistics for a user"""
        try:
            conn = get_db_connection()
            if not conn:
                return {'error': 'Database connection failed'}
                
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            # Get user_id
            cur.execute("SELECT id FROM users WHERE email = %s", (user_email,))
            user_result = cur.fetchone()
            
            if not user_result:
                return {'error': 'User not found'}
            
            user_id = user_result['id']
            
            # Get today's count
            cur.execute("""
                SELECT COUNT(*) as count 
                FROM application_stats 
                WHERE user_id = %s 
                AND date_applied = CURRENT_DATE
                AND status = 'submitted'
            """, (user_id,))
            today_count = cur.fetchone()['count']
            
            # Get yesterday's count for comparison
            cur.execute("""
                SELECT COUNT(*) as count 
                FROM application_stats 
                WHERE user_id = %s 
                AND date_applied = CURRENT_DATE - INTERVAL '1 day'
                AND status = 'submitted'
            """, (user_id,))
            yesterday_count = cur.fetchone()['count']
            
            # Get this week's count
            cur.execute("""
                SELECT COUNT(*) as count 
                FROM application_stats 
                WHERE user_id = %s 
                AND date_applied >= date_trunc('week', CURRENT_DATE)
                AND status = 'submitted'
            """, (user_id,))
            week_count = cur.fetchone()['count']
            
            # Get last week's count for comparison
            cur.execute("""
                SELECT COUNT(*) as count 
                FROM application_stats 
                WHERE user_id = %s 
                AND date_applied >= date_trunc('week', CURRENT_DATE - INTERVAL '1 week')
                AND date_applied < date_trunc('week', CURRENT_DATE)
                AND status = 'submitted'
            """, (user_id,))
            last_week_count = cur.fetchone()['count']
            
            # Get this month's count
            cur.execute("""
                SELECT COUNT(*) as count 
                FROM application_stats 
                WHERE user_id = %s 
                AND date_applied >= date_trunc('month', CURRENT_DATE)
                AND status = 'submitted'
            """, (user_id,))
            month_count = cur.fetchone()['count']
            
            # Get last month's count for comparison
            cur.execute("""
                SELECT COUNT(*) as count 
                FROM application_stats 
                WHERE user_id = %s 
                AND date_applied >= date_trunc('month', CURRENT_DATE - INTERVAL '1 month')
                AND date_applied < date_trunc('month', CURRENT_DATE)
                AND status = 'submitted'
            """, (user_id,))
            last_month_count = cur.fetchone()['count']
            
            # Get success rate
            cur.execute("""
                SELECT 
                    COUNT(*) FILTER (WHERE status = 'submitted') as submitted,
                    COUNT(*) FILTER (WHERE status = 'failed') as failed,
                    COUNT(*) as total
                FROM application_stats 
                WHERE user_id = %s
            """, (user_id,))
            success_data = cur.fetchone()
            success_rate = 0
            if success_data['total'] > 0:
                success_rate = int((success_data['submitted'] / success_data['total']) * 100)
            
            # Get last 7 days data for chart
            cur.execute("""
                SELECT 
                    date_applied,
                    COUNT(*) as count
                FROM application_stats
                WHERE user_id = %s
                AND date_applied >= CURRENT_DATE - INTERVAL '6 days'
                AND status = 'submitted'
                GROUP BY date_applied
                ORDER BY date_applied
            """, (user_id,))
            chart_data = cur.fetchall()
            
            # Format chart data
            dates = []
            values = []
            for i in range(7):
                date = datetime.now().date() - timedelta(days=6-i)
                dates.append(date.strftime('%a'))
                
                # Find count for this date
                count = 0
                for row in chart_data:
                    if row['date_applied'] == date:
                        count = row['count']
                        break
                values.append(count)
            
            # Calculate percentage changes
            today_change = 0
            if yesterday_count > 0:
                today_change = int(((today_count - yesterday_count) / yesterday_count) * 100)
            elif today_count > 0:
                today_change = 100
                
            week_change = 0
            if last_week_count > 0:
                week_change = int(((week_count - last_week_count) / last_week_count) * 100)
            elif week_count > 0:
                week_change = 100
                
            month_change = 0
            if last_month_count > 0:
                month_change = int(((month_count - last_month_count) / last_month_count) * 100)
            elif month_count > 0:
                month_change = 100
            
            cur.close()
            conn.close()
            
            return {
                'today': today_count,
                'week': week_count,
                'month': month_count,
                'successRate': success_rate,
                'todayChange': today_change,
                'weekChange': week_change,
                'monthChange': month_change,
                'chartData': {
                    'labels': dates,
                    'values': values
                }
            }
            
        except Exception as e:
            print(f"❌ Error getting stats: {str(e)}")
            if conn:
                conn.close()
            return {'error': str(e)}

@app.before_request
def before_request():
    """Check session on every request"""
    # Allow access to these endpoints without session check
    exempt_endpoints = ['index', 'login', 'static', 'onboarding','complete_onboarding', 'validate_email_availability', 'check_onboarding_status']
    
    if request.endpoint in exempt_endpoints:
        return
    
    if check_session_expired():
        session.clear()
        if request.is_json:
            return jsonify({'status': 'error', 'message': 'Session expired. Please log in again.'}), 401
        return redirect(url_for('index'))
    
    update_session_activity()

# ============================================================================
# AUTHENTICATION ROUTES
# ============================================================================

@app.route('/')
def index():
    if 'user_id' in session and not check_session_expired():
        update_session_activity()
        # Redirect to dashboard if already logged in
        return redirect(url_for('dashboard'))
    
    session.clear()
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    
    # Verify against database
    user = verify_user_credentials(email, password)
    
    if user:
        session['user_id'] = user['id']
        session['user_email'] = user['email']
        session['user_tier'] = user['tier']
        session['resume_limit'] = get_resume_limit(user['tier'])
        session['login_time'] = datetime.now().isoformat()
        session['last_activity'] = datetime.now().isoformat()
        session['session_id'] = f"session_{int(time.time())}"
        
        print(f"✅ User logged in: {email} (Tier: {session['user_tier']}, Resume Limit: {session['resume_limit']})")
        
        return jsonify({
            'status': 'success',
            'message': 'Login successful! Redirecting to dashboard...',
            'redirect': '/dashboard',  # Redirect to dashboard
            'user': email,
            'tier': session['user_tier'],
            'resume_limit': session['resume_limit']
        })
    else:
        print(f"❌ Failed login attempt: {email}")
        
        return jsonify({
            'status': 'error',
            'message': 'Invalid email or password.'
        }), 401

@app.route('/logout')
def logout():
    user_email = session.get('user_email', 'Unknown')
    session.clear()
    print(f"🚪 User logged out: {user_email}")
    return redirect(url_for('index'))

@app.route('/session_status')
def session_status():
    """API endpoint to check session status"""
    if check_session_expired():
        return jsonify({
            'status': 'expired',
            'message': 'Session has expired'
        }), 401
    
    last_activity = datetime.fromisoformat(session['last_activity'])
    time_remaining = SESSION_TIMEOUT_MINUTES * 60 - (datetime.now() - last_activity).total_seconds()
    
    return jsonify({
        'status': 'active',
        'user': session.get('user_email'),
        'tier': session.get('user_tier'),
        'resume_limit': session.get('resume_limit'),
        'time_remaining': max(0, int(time_remaining)),
        'last_activity': session.get('last_activity')
    })

# ============================================================================
# DASHBOARD ROUTES
# ============================================================================

@app.route('/dashboard')
def dashboard():
    """Main dashboard view"""
    user_email = session.get('user_email')
    user_tier = session.get('user_tier', 'basic')
    resume_limit = session.get('resume_limit', 1)
    
    if not user_email:
        return redirect(url_for('index'))
    
    print(f"📊 Dashboard accessed by: {user_email} (Tier: {user_tier})")
    
    return render_template('dashboard.html', 
                         user_email=user_email,
                         user_tier=user_tier,
                         resume_limit=resume_limit)

@app.route('/api/application-stats')
def get_application_stats():
    """API endpoint for dashboard statistics"""
    user_email = session.get('user_email')
    
    if not user_email:
        return jsonify({'error': 'Not authenticated'}), 401
    
    # Get stats using the tracker
    stats = ApplicationTracker.get_user_stats(user_email)
    
    return jsonify(stats)

@app.route('/api/recent-applications')
def get_recent_applications():
    """API endpoint for recent applications"""
    user_email = session.get('user_email')
    
    if not user_email:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
            
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("""
            SELECT 
                a.app_ref,
                a.platform,
                a.job_title,
                a.company,
                a.status,
                a.submitted_at
            FROM application_stats a
            JOIN users u ON a.user_id = u.id
            WHERE u.email = %s
            ORDER BY a.submitted_at DESC
            LIMIT 10
        """, (user_email,))
        
        applications = cur.fetchall()
        
        # Format timestamps for JSON serialization
        for app in applications:
            if app['submitted_at']:
                app['submitted_at'] = app['submitted_at'].isoformat()
        
        cur.close()
        conn.close()
        
        return jsonify(applications)
        
    except Exception as e:
        print(f"❌ Error getting recent applications: {str(e)}")
        return jsonify({'error': str(e)}), 500

# ============================================================================
# ONBOARDING ROUTE
# ============================================================================

@app.route('/onboarding')
def onboarding():
    """Display the oboarding/signup page for new users"""
    return render_template('onboarding.html')

@app.route('/complete_onboarding', methods=['POST'])
def complete_onboarding():
    """Process the onboarding form submission and create user accounts"""
    try:
        # Get form data
        form_data = request.get_json()
        
        print(f"📥 Received onboarding data for: {form_data.get('email')}")
        print(f"📋 Creating accounts for: {form_data.get('firstName')} {form_data.get('lastName')}")
        
        # Import the onboarding orchestrator
        try:
            # Try to import from new_user_automations package
            from new_user_automations.new_user_onboarding import process_onboarding_request
            print("✅ Onboarding orchestrator imported successfully")
        except ImportError as e:
            print(f"⚠️ Could not import from package, trying direct import: {e}")
            # Try direct import if package structure isn't set up
            try:
                import sys
                sys.path.append(os.path.join(os.path.dirname(__file__), 'ServiceScripts'))
                from new_user_automations.new_user_onboarding import process_onboarding_request
                print("✅ Onboarding orchestrator imported via direct path")
            except ImportError as e2:
                print(f"❌ Failed to import onboarding module: {e2}")
                return jsonify({
                    'status': 'error',
                    'message': 'Onboarding system not available. Please contact support.',
                    'error': str(e2)
                }), 500
        
        # Process the onboarding through the orchestrator
        print("🚀 Starting onboarding process...")
        result = process_onboarding_request(form_data)
        
        if result['success']:
            print(f"✅ Onboarding successful for user ID: {result['user_id']}")
            print(f"📧 InCon email created: {result['incon_email']}")
            
            # Set up session for the new user
            session['user_id'] = result['user_id']
            session['user_email'] = result['email']
            session['user_tier'] = 'premium'  # New users start with premium
            session['resume_limit'] = 10
            session['login_time'] = datetime.now().isoformat()
            session['last_activity'] = datetime.now().isoformat()
            session['is_new_user'] = True  # Flag to show welcome message
            
            # Record the successful onboarding in application_stats (optional)
            try:
                record_application(
                    user_email=result['email'],
                    platform='onboarding',
                    job_title='Account Creation',
                    company='Interview Connect',
                    status='completed'
                )
            except:
                pass  # Non-critical, just for tracking
            
            return jsonify({
                'status': 'success',
                'message': result.get('message', 'Onboarding completed successfully!'),
                'user_id': result['user_id'],
                'incon_email': result['incon_email'],
                'redirect': '/dashboard',  # Redirect to dashboard after onboarding
                'details': result.get('details', {})
            })
        else:
            print(f"❌ Onboarding failed: {result.get('error', 'Unknown error')}")
            
            # Check if it's a partial success
            if result.get('partial_success'):
                return jsonify({
                    'status': 'partial',
                    'message': result.get('message', 'Onboarding partially completed'),
                    'error': result.get('error'),
                    'status_details': result.get('status', {})
                }), 206  # 206 Partial Content
            else:
                return jsonify({
                    'status': 'error',
                    'message': result.get('message', 'Onboarding failed'),
                    'error': result.get('error')
                }), 400
            
    except Exception as e:
        print(f"❌ Onboarding error: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return jsonify({
            'status': 'error',
            'message': 'An error occurred during onboarding',
            'error': str(e)
        }), 500

@app.route('/check_onboarding_status/<int:user_id>')
def check_onboarding_status(user_id):
    """Check the status of an ongoing onboarding process"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'status': 'error', 'message': 'Database connection failed'}), 500
        
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Get user and check their status
        cursor.execute("""
            SELECT 
                u.id,
                u.email,
                u.incon_email,
                u.tier,
                u.created_at,
                u.is_active,
                (SELECT COUNT(*) FROM resumes WHERE user_id = u.id) as resume_count
            FROM users u
            WHERE u.id = %s
        """, (user_id,))
        
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if user:
            # Check what's been completed
            onboarding_complete = bool(user['incon_email'])
            
            return jsonify({
                'status': 'success',
                'user': {
                    'id': user['id'],
                    'email': user['email'],
                    'incon_email': user['incon_email'],
                    'tier': user['tier'],
                    'created_at': user['created_at'].isoformat() if user['created_at'] else None,
                    'is_active': user['is_active'],
                    'resume_count': user['resume_count']
                },
                'onboarding_complete': onboarding_complete,
                'steps_completed': {
                    'database_user': True,
                    'incon_email': bool(user['incon_email']),
                    'resume_uploaded': user['resume_count'] > 0
                }
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'User not found'
            }), 404
            
    except Exception as e:
        print(f"❌ Error checking onboarding status: {str(e)}")
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

@app.route('/onboarding/validate_email', methods=['POST'])
def validate_email_availability():
    """Check if an email is already registered"""
    try:
        data = request.get_json()
        email = data.get('email', '').lower().strip()
        
        if not email:
            return jsonify({'available': False, 'message': 'Email is required'}), 400
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'available': False, 'message': 'Database connection failed'}), 500
        
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
        exists = cursor.fetchone() is not None
        cursor.close()
        conn.close()
        
        if exists:
            return jsonify({
                'available': False,
                'message': 'This email is already registered. Please login instead.'
            })
        else:
            return jsonify({
                'available': True,
                'message': 'Email is available'
            })
            
    except Exception as e:
        print(f"❌ Error validating email: {str(e)}")
        return jsonify({
            'available': False,
            'message': 'Error checking email availability'
        }), 500
# ============================================================================
# APPLICATION ASSISTANT ROUTES
# ============================================================================

@app.route('/application-assistant')
def application_assistant():
    """Application Assistant - Full featured job application system"""
    user_email = session.get('user_email')
    user_tier = session.get('user_tier', 'basic')
    resume_limit = session.get('resume_limit', 1)
    
    print(f"🎯 Application Assistant accessed by: {user_email} (Tier: {user_tier})")
    
    return render_template('application-assistant.html',
        user_email=user_email,
        user_tier=user_tier,
        resume_limit=resume_limit)

@app.route('/parse_resume', methods=['POST'])
def parse_resume():
    """Parse uploaded resume and extract information"""
    if not app_assistant:
        return jsonify({'status': 'error', 'message': 'Application Assistant not available'}), 500
    return app_assistant.parse_resume(request, session)

@app.route('/start_application_assistant', methods=['POST'])
def start_application_assistant():
    """Start Application Assistant automation"""
    if not app_assistant:
        return jsonify({'status': 'error', 'message': 'Application Assistant not available'}), 500
    
    # Get data from request
    data = request.get_json()
    user_email = session.get('user_email')
    
    # Record applications for each selected platform
    if user_email and data:
        platforms = data.get('platforms', [])
        job_title = data.get('jobTitle', 'Not specified')
        location = data.get('location', '')
        
        # Record an application for each platform
        for platform in platforms:
            record_application(
                user_email=user_email,
                platform=platform,
                job_title=job_title,
                company=f"Various ({location})" if location else "Various",
                status='in_progress'
            )
        
        print(f"📊 Recorded {len(platforms)} applications for {user_email}")
    
    # Continue with existing automation
    return app_assistant.start_automation(request, session)

# ============================================================================
# JOB BOARD ASSISTANT ROUTES
# ============================================================================

@app.route('/job-board-assistant')
def job_board_assistant():
    """Job Board Assistant - Simplified job board submission system"""
    user_email = session.get('user_email')
    print(f"📋 Job Board Assistant accessed by: {user_email}")
    
    return render_template('job-board-assistant.html', user_email=user_email)

@app.route('/start_job_board_assistant', methods=['POST'])
def start_job_board_assistant():
    """Start Job Board Assistant automation"""
    if not job_assistant:
        return jsonify({'status': 'error', 'message': 'Job Board Assistant not available'}), 500
    
    # Get user email and industry
    user_email = session.get('user_email')
    industry = request.form.get('industry', 'Not specified')
    
    # Record job board submission
    if user_email:
        record_application(
            user_email=user_email,
            platform=f'job-board-{industry.lower()}',
            job_title=f'{industry} Industry Positions',
            company='Multiple Agencies',
            status='in_progress'
        )
        print(f"📊 Recorded job board submission for {user_email} in {industry}")
    
    # Get user profile data for the assistant
    user_id = session.get('user_id')
    if user_id:
        user_profile = get_user_profile(user_id)
        if user_profile:
            session['user_profile'] = user_profile
    
    return job_assistant.start_automation(request, session)

@app.route('/stop_job_board_assistant', methods=['POST'])
def stop_job_board_assistant():
    """Stop Job Board Assistant"""
    if not job_assistant:
        return jsonify({'status': 'error', 'message': 'Job Board Assistant not available'}), 500
    
    return job_assistant.stop_automation()

# ============================================================================
# MAIN APPLICATION
# ============================================================================

if __name__ == '__main__':
    # Test database connection
    print("\n🔍 Testing database connection...")
    test_conn = get_db_connection()
    if test_conn:
        print("✅ Database connection successful")
        
        # Check if application_stats table exists
        try:
            with test_conn.cursor() as cursor:
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = 'application_stats'
                    );
                """)
                if cursor.fetchone()[0]:
                    print("✅ Application stats table found")
                else:
                    print("⚠️ Application stats table not found - dashboard stats will not work")
        except Exception as e:
            print(f"⚠️ Could not check for application_stats table: {str(e)}")
        
        test_conn.close()
    else:
        print("❌ Database connection failed - check your DB_PASSWORD environment variable")
    
    # Debug: Print current directory structure
    print("\n🔍 Checking directory structure...")
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    print(f"📁 Current directory: {current_dir}")
    print(f"📁 Template directory: {template_folder}")
    print(f"📁 Template directory exists: {os.path.exists(template_folder)}")
    
    if os.path.exists(template_folder):
        templates = [f for f in os.listdir(template_folder) if f.endswith('.html')]
        print(f"📄 Templates found: {templates}")
        
        # Check for dashboard.html specifically
        if 'dashboard.html' in templates:
            print("✅ Dashboard template found")
        else:
            print("⚠️ Dashboard template not found - please add dashboard.html to templates folder")
    else:
        print("❌ Template directory not found!")
    
    print("\n" + "🚀" * 20)
    print("🚀 INTERVIEW CONNECT SERVER STARTING...")
    print("🚀" * 20)
    print("🌐 Server running on: http://localhost:5001")
    print("📊 Dashboard available at: http://localhost:5001/dashboard")
    print("📊 Using PostgreSQL database for authentication and tracking")
    print("🚀" * 20 + "\n")
    
    # Ensure the server runs on port 5001
    try:
        app.run(debug=True, host='0.0.0.0', port=5001, threaded=True)
    except Exception as e:
        print(f"❌ Failed to start server on port 5001: {str(e)}")
        print("🔄 Trying alternative ports...")
        
        # Try alternative ports if 5001 is busy
        for port in [5002, 5003, 5004, 5005]:
            try:
                print(f"🔄 Trying port {port}...")
                app.run(debug=True, host='0.0.0.0', port=port, threaded=True)
                break
            except Exception as e:
                print(f"❌ Port {port} failed: {str(e)}")
                continue
