import os
import time
import threading
import importlib
import sys

class GovernmentAssistant:
    """Government Industry Job Board Assistant - Runs automations sequentially"""
    
    def __init__(self):
        self.name = "Government Assistant"
        self.industry = "Government"
        self.stop_flag_ref = None
        self.selected_boards = []
        self.completed_boards = set()  # Track completed board IDs to prevent duplicates
        self.automation_modules = self._load_automation_modules()
        print(f"{self.name} initialized with {len(self.automation_modules)} automation modules")
    
    def _load_automation_modules(self):
        """Load all automation modules and map them by site name"""
        modules_map = {}
        
        # Correct path to website_automation directory
        current_dir = os.path.dirname(os.path.abspath(__file__))
        automation_dir = os.path.join(current_dir, 'website_automation')
        
        if not os.path.exists(automation_dir):
            print(f"Warning: website_automation directory not found at {automation_dir}")
            return modules_map
        
        # Add the parent directory to Python path for proper imports
        parent_dir = os.path.dirname(current_dir)
        if parent_dir not in sys.path:
            sys.path.insert(0, parent_dir)
        
        # Add current directory to path as well
        if current_dir not in sys.path:
            sys.path.insert(0, current_dir)
        
        # Scan for automation modules
        for filename in os.listdir(automation_dir):
            if filename.endswith('_automation.py') and filename != '__init__.py':
                module_name = filename[:-3]  # Remove .py
                
                try:
                    # Import the module
                    full_module_name = f"job_board_assistant.website_automation.{module_name}"
                    module = importlib.import_module(full_module_name)
                    
                    # Look for automation classes with HANDLES_SITE attribute
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        if (isinstance(attr, type) and 
                            hasattr(attr, 'HANDLES_SITE') and 
                            hasattr(attr, 'submit_application')):
                            site_name = attr.HANDLES_SITE
                            modules_map[site_name] = (full_module_name, attr_name)
                            print(f"Found automation: {attr_name} handles '{site_name}'")
                            
                except Exception as e:
                    print(f"Error loading {module_name}: {str(e)}")
                    import traceback
                    traceback.print_exc()
        
        return modules_map
    
    def set_stop_flag_reference(self, orchestrator):
        """Set reference to orchestrator's stop flag"""
        self.stop_flag_ref = orchestrator
    
    def set_selected_boards(self, boards):
        """Set the boards selected for this industry"""
        self.selected_boards = boards
        self.completed_boards.clear()  # Reset completed boards for new session
    
    def start_automation(self, session_data):
        """Start Government-specific automation"""
        print(f"Starting {self.name} automation")
        
        # Check stop flag before processing
        if self.stop_flag_ref and self.stop_flag_ref.stop_requested:
            return {'success': False, 'message': 'Stopped by user'}
        
        try:
            if not self.selected_boards:
                return {'success': False, 'message': 'No boards selected for processing'}
            
            print(f"Processing {len(self.selected_boards)} Government job boards")
            
            # Extract user profile from session_data
            user_profile = {
                'user_id': session_data.get('user_id'),
                'email': session_data.get('email'),
                'first_name': session_data.get('first_name'),
                'last_name': session_data.get('last_name'),
                'phone': session_data.get('phone'),
                'address': session_data.get('address'),
                'city': session_data.get('city'),
                'state': session_data.get('state'),
                'zip_code': session_data.get('zip_code'),
                'country': session_data.get('country', 'USA'),
                'resume_path': session_data.get('resume_path', '')
            }
            
            print(f"User Profile: {user_profile['first_name']} {user_profile['last_name']} ({user_profile['email']})")
            
            # Run automation in separate thread
            automation_thread = threading.Thread(
                target=self._run_Government_automation,
                args=(self.selected_boards, user_profile)
            )
            automation_thread.daemon = True
            automation_thread.start()
            
            return {
                'success': True, 
                'message': f'{self.name} started for {len(self.selected_boards)} boards',
                'boards_count': len(self.selected_boards)
            }
            
        except Exception as e:
            print(f"{self.name} error: {str(e)}")
            import traceback
            traceback.print_exc()
            return {'success': False, 'error': str(e)}
    
    def _run_Government_automation(self, boards, user_profile):
        """Run automation for all Government job boards sequentially"""
        results = {}
        successful_submissions = 0
        
        try:
            print(f"\n{'='*60}")
            print(f"Government AUTOMATION STARTING")
            print(f"User: {user_profile.get('first_name')} {user_profile.get('last_name')} ({user_profile.get('email')})")
            print(f"Boards to process: {len(boards)}")
            print(f"{'='*60}\n")
            
            for i, board in enumerate(boards):
                # Check stop flag before each board
                if self.stop_flag_ref and self.stop_flag_ref.stop_requested:
                    print(f"Government automation stopped by user at board {i+1}")
                    break
                
                board_id = board.get('id')
                board_name = board.get('site_name')
                
                # Skip if already completed in this session
                if board_id in self.completed_boards:
                    print(f"Skipping board {board_name} (ID: {board_id}) - already completed")
                    continue
                
                print(f"\n{'='*40}")
                print(f"Board {i+1}/{len(boards)}: {board_name}")
                print(f"ID: {board_id}")
                print(f"URL: {board.get('site_url', 'No URL')}")
                print(f"Agency: {board.get('agency_name', 'No Agency')}")
                print(f"Automation Script: {board.get('automation_script', 'Not specified')}")
                print(f"{'='*40}\n")
                
                try:
                    # Call the specific website automation
                    result = self._call_website_automation(board, user_profile)
                    results[board_name] = result
                    
                    if result.get('success'):
                        successful_submissions += 1
                        self.completed_boards.add(board_id)  # Mark as completed
                        print(f"✅ Successfully submitted to {board_name}")
                    else:
                        print(f"❌ Failed to submit to {board_name}: {result.get('message', 'Unknown error')}")
                    
                    # Wait between boards if not stopped
                    if not (self.stop_flag_ref and self.stop_flag_ref.stop_requested) and i < len(boards) - 1:
                        wait_time = 5
                        print(f"\nWaiting {wait_time} seconds before next board...")
                        for s in range(wait_time):
                            if self.stop_flag_ref and self.stop_flag_ref.stop_requested:
                                break
                            time.sleep(1)
                            if s % 10 == 0:
                                print(f"  {wait_time - s} seconds remaining...")
                
                except Exception as e:
                    print(f"❌ Error with board {board_name}: {str(e)}")
                    import traceback
                    traceback.print_exc()
                    results[board_name] = {'success': False, 'message': str(e)}
            
            print(f"\n{'='*60}")
            print(f"Government AUTOMATION COMPLETE")
            print(f"Successful submissions: {successful_submissions}/{len(boards)}")
            print(f"{'='*60}\n")
            
            # Log final results
            for board_name, result in results.items():
                status = "✅" if result.get('success') else "❌"
                print(f"{status} {board_name}: {result.get('message', 'Completed')}")
            
        except Exception as e:
            print(f"Government automation error: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def _call_website_automation(self, board, user_profile):
        """Call the specific website automation based on site name"""
        try:
            site_name = board.get('site_name', '')
            
            # Check if we have an automation for this site
            if site_name not in self.automation_modules:
                # Try to match by automation_script field if available
                automation_script = board.get('automation_script', '')
                if automation_script and automation_script in self.automation_modules:
                    site_name = automation_script
                else:
                    return {
                        'success': False, 
                        'message': f'No automation found for site: {site_name}. Available automations: {list(self.automation_modules.keys())}'
                    }
            
            module_name, class_name = self.automation_modules[site_name]
            
            try:
                # Import the module
                module = importlib.import_module(module_name)
                
                # Get the automation class
                automation_class = getattr(module, class_name)
                
                # Instantiate and run
                automation = automation_class()
                
                # Call submit_application with the correct parameters
                success, message = automation.submit_application(
                    job_board=board,
                    user_profile=user_profile,
                    stop_check_callback=lambda: self.stop_flag_ref and self.stop_flag_ref.stop_requested
                )
                
                return {'success': success, 'message': message}
                
            except Exception as e:
                print(f"Error running automation for {site_name}: {str(e)}")
                import traceback
                traceback.print_exc()
                return {'success': False, 'message': f'Error running automation: {str(e)}'}
            
        except Exception as e:
            return {'success': False, 'message': f'Automation error: {str(e)}'}

# Make it compatible with direct script execution
if __name__ == "__main__":
    assistant = GovernmentAssistant()
    print(f"✅ {assistant.name} loaded successfully")
    print(f"Available automations: {list(assistant.automation_modules.keys())}")