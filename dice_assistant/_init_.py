# ServiceScripts/__init__.py
# Empty file - just marks ServiceScripts as a package

# ===================================================================

# ServiceScripts/dice_assistant/__init__.py
"""
Dice Assistant Package

Provides automated job application functionality for Dice.com
"""

from .dice_step_3_catalog_jobs import step_3_catalog_jobs
from .dice_step_4_apply_to_job_index import step_4_apply_to_job_index
from .dice_step_5_loop_return import step_5_loop_return
from .dice_step_8 import step_8_click_next
from .dice_step_9 import step_9_submit_application
from .dice_step_10 import step_10_handle_confirmation_and_return
from .credentials import get_dice_credentials, get_platform_credentials

__all__ = [
    'step_3_catalog_jobs',
    'step_4_apply_to_job_index',
    'step_5_loop_return',
    'step_8_click_next',
    'step_9_submit_application',
    'step_10_handle_confirmation_and_return',
]

# Package metadata
__version__ = "2.0.0"  # Updated version for new flow
__author__ = "Interview Connect"
__description__ = "Automated Dice.com job application assistant - Apply to all jobs"