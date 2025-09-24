"""
new_user_onboarding.py
Simplified new user account creation for Interview Connect
Creates user accounts in the database only - no external automations
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database configuration
DB_CONFIG = {
    'host': 'localhost',
    'database': 'interview_connect',
    'user': 'InConAdmin',
    'password': os.environ.get('DB_PASSWORD', '')
}

def get_db_connection():
    """Create and return a database connection"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        logger.error(f"Database connection error: {str(e)}")
        raise

def validate_user_data(user_data):
    """Validate required user data fields"""
    required_fields = {
        'firstName': user_data.get('firstName', '').strip(),
        'lastName': user_data.get('lastName', '').strip(),
        'email': user_data.get('email', '').strip(),
        'phone': user_data.get('phone', '').strip(),
        'password': user_data.get('password', '').strip(),
        'city': user_data.get('city', '').strip(),
        'state': user_data.get('state', '').strip(),
        'zipCode': user_data.get('zipCode', '').strip()
    }
    
    # Check for missing required fields
    missing_fields = [field for field, value in required_fields.items() if not value]
    if missing_fields:
        raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")
    
    # Basic email format validation
    email = required_fields['email']
    if '@' not in email or '.' not in email:
        raise ValueError("Invalid email format")
    
    return required_fields

def check_email_exists(conn, email):
    """Check if email already exists in the database"""
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
            return cursor.fetchone() is not None
    except Exception as e:
        logger.error(f"Error checking email existence: {str(e)}")
        raise

def calculate_tier_expiration():
    """Calculate tier expiration date (30 days from now for premium)"""
    return datetime.now() + timedelta(days=30)

def create_user_account(user_data):
    """
    Create a new user account in the database
    
    Args:
        user_data: Dictionary containing user information from the onboarding form
        
    Returns:
        Dictionary with success status and user details
    """
    conn = None
    
    try:
        # Validate input data
        validated_data = validate_user_data(user_data)
        
        # Get database connection
        conn = get_db_connection()
        
        # Check if email already exists
        if check_email_exists(conn, validated_data['email']):
            return {
                'success': False,
                'message': f"Email {validated_data['email']} already exists in the system",
                'error': 'duplicate_email'
            }
        
        # Prepare user data for insertion
        first_name = validated_data['firstName']
        last_name = validated_data['lastName']
        email = validated_data['email']
        phone = validated_data['phone']
        password = validated_data['password']  # No hashing per current requirements
        address = user_data.get('streetAddress', '').strip()
        city = validated_data['city']
        state = validated_data['state'].upper()
        zip_code = validated_data['zipCode']
        
        # Insert user into database
        with conn.cursor() as cursor:
            insert_query = """
                INSERT INTO users (
                    email, 
                    password_hash,
                    first_name,
                    last_name,
                    address,
                    city,
                    state,
                    zip_code,
                    country,
                    phone,
                    tier,
                    visa_status,
                    created_at,
                    last_login,
                    is_active
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                ) RETURNING id
            """
            
            cursor.execute(insert_query, (
                email,
                password,
                first_name,
                last_name,
                address,
                city,
                state,
                zip_code,
                'USA',  # Default country
                phone,
                'premium',  # New users start as premium
                'US Citizen',  # Default visa status
                datetime.now(),
                datetime.now(),
                True  # is_active
            ))
            
            user_id = cursor.fetchone()[0]
            
        # Commit the transaction
        conn.commit()
        
        logger.info(f"Successfully created user account - ID: {user_id}, Email: {email}")
        
        return {
            'success': True,
            'user_id': user_id,
            'email': email,
            'message': f'User account created successfully for {email}'
        }
        
    except ValueError as ve:
        # Validation errors
        logger.warning(f"Validation error: {str(ve)}")
        return {
            'success': False,
            'message': str(ve),
            'error': 'validation_error'
        }
        
    except Exception as e:
        # Rollback on any error
        if conn:
            conn.rollback()
        
        logger.error(f"Error creating user account: {str(e)}")
        return {
            'success': False,
            'message': 'Failed to create user account. Please try again.',
            'error': str(e)
        }
        
    finally:
        # Close connection
        if conn:
            conn.close()

def process_onboarding_request(user_data):
    """
    Main entry point for processing new user onboarding
    This function maintains compatibility with the existing main.py route
    
    Args:
        user_data: Dictionary containing user information from the onboarding form
        
    Returns:
        Dictionary with success status and user details
    """
    logger.info(f"Processing onboarding request for: {user_data.get('email')}")
    
    # Create the user account
    result = create_user_account(user_data)
    
    if result['success']:
        logger.info(f"Onboarding completed successfully for user ID: {result['user_id']}")
    else:
        logger.error(f"Onboarding failed: {result['message']}")
    
    return result