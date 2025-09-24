# ServiceScripts/dice_assistant/credentials.py

"""
Credentials Management for Interview Connect SaaS

Maps Interview Connect users to their platform credentials.
This allows multiple clients to use the service with their own accounts.
"""

import os
from typing import Dict, Optional

# Platform credentials mapped to Interview Connect user accounts
USER_PLATFORM_CREDENTIALS = {
    # Demo/Test Accounts
    'demo@jobbot.com': {
        'dice': {
            'email': 'demo.user@dice.com',
            'password': 'DemoPassword123!'
        },
        'indeed': {
            'email': 'demo.user@indeed.com', 
            'password': 'DemoPassword123!'
        },
        'glassdoor': {
            'email': 'demo.user@glassdoor.com',
            'password': 'DemoPassword123!'
        }
    },
    
    # Basic Tier Account
    'admin@autoapply.com': {
        'dice': {
            'email': 'admin.user@dice.com',
            'password': 'AdminPassword456!'
        },
        'indeed': {
            'email': 'admin.user@indeed.com',
            'password': 'AdminPassword456!'
        }
    },
    
    # Premium Tier Account  
    'i.test@interview-connect.com': {
        'dice': {
            'email': 'i.test@interview-connect.com',
            'password': 'MaximumHope98@'
        },
        'indeed': {
            'email': 'premium.user@indeed.com',
            'password': 'PremiumPassword789!'
        },
        'glassdoor': {
            'email': 'premium.user@glassdoor.com', 
            'password': 'PremiumPassword789!'
        },
        'ziprecruiter': {
            'email': 'premium.user@ziprecruiter.com',
            'password': 'PremiumPassword789!'
        }
    },
    
    # Add more clients as needed
    # 'client1@company.com': {
    #     'dice': {
    #         'email': 'client1@dice.com',
    #         'password': 'ClientPassword!'
    #     }
    # }
}

# Environment variable overrides (for production)
ENV_CREDENTIAL_MAPPING = {
    'demo@jobbot.com': {
        'dice': {
            'email': os.environ.get('DEMO_DICE_EMAIL'),
            'password': os.environ.get('DEMO_DICE_PASSWORD')
        }
    },
    'i.test@interview-connect.com': {
        'dice': {
            'email': os.environ.get('PREMIUM_DICE_EMAIL'),
            'password': os.environ.get('PREMIUM_DICE_PASSWORD')
        }
    }
}


class CredentialsManager:
    """Manages platform credentials for Interview Connect users"""
    
    def __init__(self):
        self.user_credentials = USER_PLATFORM_CREDENTIALS.copy()
        self._apply_environment_overrides()
    
    def _apply_environment_overrides(self):
        """Apply environment variable overrides for production"""
        for user_email, platforms in ENV_CREDENTIAL_MAPPING.items():
            if user_email in self.user_credentials:
                for platform, creds in platforms.items():
                    if creds['email'] and creds['password']:  # Only if env vars exist
                        self.user_credentials[user_email][platform] = creds
                        print(f"Applied environment override for {user_email} on {platform}")
    
    def get_platform_credentials(self, user_email: str, platform: str) -> Optional[Dict[str, str]]:
        """
        Get platform credentials for a specific user
        
        Args:
            user_email: Interview Connect user email
            platform: Platform name ('dice', 'indeed', 'glassdoor', etc.)
            
        Returns:
            Dict with 'email' and 'password' keys, or None if not found
        """
        if user_email not in self.user_credentials:
            print(f"WARNING: No credentials found for user: {user_email}")
            return None
        
        user_platforms = self.user_credentials[user_email]
        if platform not in user_platforms:
            print(f"WARNING: No {platform} credentials found for user: {user_email}")
            return None
        
        creds = user_platforms[platform]
        print(f"Retrieved {platform} credentials for {user_email}")
        return {
            'email': creds['email'],
            'password': creds['password']
        }
    
    def get_dice_credentials(self, user_email: str) -> Optional[Dict[str, str]]:
        """Convenience method for Dice credentials"""
        return self.get_platform_credentials(user_email, 'dice')
    
    def get_indeed_credentials(self, user_email: str) -> Optional[Dict[str, str]]:
        """Convenience method for Indeed credentials"""
        return self.get_platform_credentials(user_email, 'indeed')
    
    def get_glassdoor_credentials(self, user_email: str) -> Optional[Dict[str, str]]:
        """Convenience method for Glassdoor credentials"""
        return self.get_platform_credentials(user_email, 'glassdoor')
    
    def add_user_credentials(self, user_email: str, platform_credentials: Dict[str, Dict[str, str]]):
        """
        Add credentials for a new user
        
        Args:
            user_email: Interview Connect user email
            platform_credentials: Dict of platform -> {'email': str, 'password': str}
        """
        self.user_credentials[user_email] = platform_credentials
        print(f"Added credentials for new user: {user_email}")
    
    def get_supported_platforms(self, user_email: str) -> list:
        """Get list of platforms this user has credentials for"""
        if user_email not in self.user_credentials:
            return []
        return list(self.user_credentials[user_email].keys())
    
    def validate_user_access(self, user_email: str, platform: str) -> bool:
        """Check if user has access to a specific platform"""
        return self.get_platform_credentials(user_email, platform) is not None


# Global instance
credentials_manager = CredentialsManager()

# Convenience functions for backward compatibility
def get_dice_credentials(user_email: str) -> Optional[Dict[str, str]]:
    """Get Dice credentials for a user"""
    return credentials_manager.get_dice_credentials(user_email)

def get_platform_credentials(user_email: str, platform: str) -> Optional[Dict[str, str]]:
    """Get platform credentials for a user"""
    return credentials_manager.get_platform_credentials(user_email, platform)