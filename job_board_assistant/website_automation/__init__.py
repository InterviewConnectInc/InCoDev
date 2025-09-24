# ServiceScripts/website_automations/__init__.py
"""
Website Automations Package
Contains all individual job board automation scripts
"""

# Import all automation classes for easy access
try:
    from .aps_automation import APSAutomation
except ImportError:
    print("Warning: APS automation not found")
    APSAutomation = None

# Add other automations as you create them
# try:
#     from .other_board_automation import OtherBoardAutomation
# except ImportError:
#     OtherBoardAutomation = None

__all__ = ['APSAutomation']