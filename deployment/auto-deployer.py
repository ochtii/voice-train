#!/usr/bin/env python3
"""
Auto-Deployment System for Voice Recognition Pi
Continuously monitors GitHub repository for changes and deploys updates
"""

import os
import sys
import time
import subprocess
import hashlib
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Tuple
import requests
from colorama import init, Fore, Back, Style

# Initialize colorama for cross-platform colored output
init(autoreset=True)

class Colors:
    """Color constants for terminal output"""
    GREEN = Fore.GREEN
    RED = Fore.RED  
    YELLOW = Fore.YELLOW
    BLUE = Fore.BLUE
    CYAN = Fore.CYAN
    MAGENTA = Fore.MAGENTA
    WHITE = Fore.WHITE
    BRIGHT = Style.BRIGHT
    RESET = Style.RESET_ALL

class AutoDeployer:
    """Auto-deployment system for continuous integration"""
    
    def __init__(self):
        self.repo_url = os.getenv('GITHUB_REPO', 'https://github.com/ochtii/voice-train.git')
        self.branch = os.getenv('BRANCH', 'live')
        self.check_interval = int(os.getenv('CHECK_INTERVAL', '5'))
        self.project_root = Path('/home/ochtii/voice-recog-pi')
        self.deployment_root = self.project_root / 'deployment'
        self.logs_dir = self.project_root / 'logs'
        self.state_file = self.deployment_root / 'deployment_state.json'
        
        # Monitored file extensions
        self.monitored_extensions = {'.py', '.js', '.html', '.css', '.json', '.yml', '.yaml', '.md'}
        
        # Excluded patterns (cache, temp files, etc.)
        self.excluded_patterns = {
            '__pycache__', '.git', '.pytest_cache', 'node_modules', 
            '.DS_Store', '*.pyc', '*.pyo', '*.pyd', '.coverage',
            '.env', '.venv', 'venv', 'env', '*.log', '*.tmp'
        }
        
        self.setup_logging()
        self.ensure_directories()
        
    def setup_logging(self):
        """Configure detailed logging"""
        self.logs_dir.mkdir(exist_ok=True)
        
        # Main deployer logger
        self.logger = logging.getLogger('auto_deployer')
        self.logger.setLevel(logging.DEBUG)
        
        # File handler
        file_handler = logging.FileHandler(self.logs_dir / 'auto-deployer.log')
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_formatter = logging.Formatter(
            f'{Colors.CYAN}%(asctime)s{Colors.RESET} - {Colors.BRIGHT}%(levelname)s{Colors.RESET} - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        
    def ensure_directories(self):
        """Ensure all required directories exist"""
        dirs = [self.logs_dir, self.deployment_root]
        for directory in dirs:
            directory.mkdir(exist_ok=True)
            
    def load_state(self) -> Dict:
        """Load deployment state from file"""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.warning(f"Failed to load state: {e}")
        return {'last_commit': None, 'last_deployment': None, 'file_hashes': {}}
        
    def save_state(self, state: Dict):
        """Save deployment state to file"""
        try:
            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save state: {e}")
            
    def run_command(self, command: str, cwd: Path = None) -> Tuple[bool, str]:
        """Run shell command and return success status and output"""
        try:
            result = subprocess.run(
                command, 
                shell=True, 
                cwd=cwd or self.project_root,
                capture_output=True, 
                text=True, 
                timeout=300  # 5 minutes for slow Pi Zero
            )
            return result.returncode == 0, result.stdout + result.stderr
        except subprocess.TimeoutExpired:
            return False, "Command timed out"
        except Exception as e:
            return False, str(e)
            
    def get_remote_commit_hash(self) -> str:
        """Get latest commit hash from remote repository"""
        try:
            # GitHub API to get latest commit
            api_url = self.repo_url.replace('.git', '').replace('https://github.com/', 'https://api.github.com/repos/')
            api_url = f"{api_url}/commits/{self.branch}"
            
            response = requests.get(api_url, timeout=10)
            if response.status_code == 200:
                return response.json()['sha']
            else:
                self.logger.warning(f"GitHub API request failed: {response.status_code}")
                return None
        except Exception as e:
            self.logger.warning(f"Failed to get remote commit hash: {e}")
            return None
            
    def get_local_commit_hash(self) -> str:
        """Get current local commit hash"""
        success, output = self.run_command('git rev-parse HEAD')
        if success:
            return output.strip()
        return None
        
    def calculate_file_hash(self, file_path: Path) -> str:
        """Calculate MD5 hash of file content"""
        try:
            with open(file_path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception:
            return None
            
    def get_monitored_files(self) -> Dict[str, str]:
        """Get dictionary of monitored files and their hashes"""
        file_hashes = {}
        
        for root, dirs, files in os.walk(self.project_root):
            # Skip excluded directories
            dirs[:] = [d for d in dirs if not any(pattern in d for pattern in self.excluded_patterns)]
            
            root_path = Path(root)
            for file in files:
                file_path = root_path / file
                
                # Check if file should be monitored
                if (file_path.suffix in self.monitored_extensions and 
                    not any(pattern in str(file_path) for pattern in self.excluded_patterns)):
                    
                    relative_path = str(file_path.relative_to(self.project_root))
                    file_hash = self.calculate_file_hash(file_path)
                    if file_hash:
                        file_hashes[relative_path] = file_hash
                        
        return file_hashes
        
    def compare_files(self, old_hashes: Dict[str, str], new_hashes: Dict[str, str]) -> Tuple[Set[str], Set[str], Set[str]]:
        """Compare file hashes and return added, modified, deleted files"""
        old_files = set(old_hashes.keys())
        new_files = set(new_hashes.keys())
        
        added = new_files - old_files
        deleted = old_files - new_files
        modified = {f for f in (old_files & new_files) if old_hashes[f] != new_hashes[f]}
        
        return added, modified, deleted
        
    def print_file_changes(self, added: Set[str], modified: Set[str], deleted: Set[str]):
        """Print colored file changes summary"""
        if not (added or modified or deleted):
            self.logger.info(f"{Colors.GREEN}✓ No file changes detected{Colors.RESET}")
            return
            
        self.logger.info(f"{Colors.BRIGHT}📁 File Changes Summary:{Colors.RESET}")
        
        if added:
            self.logger.info(f"{Colors.GREEN}➕ Added Files ({len(added)}):{Colors.RESET}")
            for file in sorted(added):
                print(f"  {Colors.GREEN}+ {file}{Colors.RESET}")
                
        if modified:
            self.logger.info(f"{Colors.YELLOW}📝 Modified Files ({len(modified)}):{Colors.RESET}")
            for file in sorted(modified):
                print(f"  {Colors.YELLOW}~ {file}{Colors.RESET}")
                
        if deleted:
            self.logger.info(f"{Colors.RED}❌ Deleted Files ({len(deleted)}):{Colors.RESET}")
            for file in sorted(deleted):
                print(f"  {Colors.RED}- {file}{Colors.RESET}")
                
    def stop_services(self) -> bool:
        """Stop systemd services"""
        self.logger.info(f"{Colors.YELLOW}🛑 Stopping services...{Colors.RESET}")
        
        commands = [
            'sudo systemctl stop voice-recog.service'
        ]
        
        for cmd in commands:
            success, output = self.run_command(cmd)
            if success:
                self.logger.info(f"{Colors.GREEN}✓ {cmd}{Colors.RESET}")
            else:
                self.logger.warning(f"{Colors.YELLOW}⚠ {cmd} - {output}{Colors.RESET}")
                
        return True
        
    def start_services(self) -> bool:
        """Start systemd services"""
        self.logger.info(f"{Colors.BLUE}🚀 Starting services...{Colors.RESET}")
        
        success, output = self.run_command('sudo systemctl start voice-recog.service')
        if success:
            self.logger.info(f"{Colors.GREEN}✓ Services started successfully{Colors.RESET}")
            return True
        else:
            self.logger.error(f"{Colors.RED}❌ Failed to start services: {output}{Colors.RESET}")
            return False
            
    def deploy_updates(self) -> bool:
        """Deploy updates from repository"""
        self.logger.info(f"{Colors.BRIGHT}🔄 Starting deployment process...{Colors.RESET}")
        
        deployment_steps = [
            ('Fetching latest changes', 'git fetch origin'),
            ('Resetting to remote', f'git reset --hard origin/{self.branch}'),
            ('Cleaning untracked files', 'git clean -fd'),
            ('Updating submodules', 'git submodule update --init --recursive'),
            ('Installing Python dependencies', 'venv/bin/pip install -r backend/requirements.txt --quiet'),
        ]
        
        for step_name, command in deployment_steps:
            self.logger.info(f"{Colors.CYAN}📋 {step_name}...{Colors.RESET}")
            success, output = self.run_command(command)
            
            if success:
                self.logger.info(f"{Colors.GREEN}✓ {step_name} completed{Colors.RESET}")
                if output.strip():
                    self.logger.debug(f"Output: {output}")
            else:
                self.logger.error(f"{Colors.RED}❌ {step_name} failed: {output}{Colors.RESET}")
                return False
                
        return True
        
    def perform_deployment(self) -> bool:
        """Perform complete deployment process"""
        deployment_start = datetime.now()
        self.logger.info(f"{Colors.BRIGHT}🚀 DEPLOYMENT STARTED at {deployment_start.strftime('%Y-%m-%d %H:%M:%S')}{Colors.RESET}")
        
        try:
            # Stop services
            if not self.stop_services():
                return False
                
            # Deploy updates
            if not self.deploy_updates():
                return False
                
            # Start services
            if not self.start_services():
                return False
                
            deployment_end = datetime.now()
            duration = (deployment_end - deployment_start).total_seconds()
            
            self.logger.info(f"{Colors.GREEN}✅ DEPLOYMENT COMPLETED in {duration:.2f}s{Colors.RESET}")
            return True
            
        except Exception as e:
            self.logger.error(f"{Colors.RED}💥 DEPLOYMENT FAILED: {e}{Colors.RESET}")
            return False
            
    def check_for_updates(self) -> bool:
        """Check if updates are available"""
        state = self.load_state()
        
        # Get remote commit hash
        remote_commit = self.get_remote_commit_hash()
        if not remote_commit:
            self.logger.warning(f"{Colors.YELLOW}⚠ Could not fetch remote commit hash{Colors.RESET}")
            return False
            
        local_commit = self.get_local_commit_hash()
        
        # Check if commits differ
        if remote_commit != local_commit:
            self.logger.info(f"{Colors.BLUE}🔍 New commit detected:{Colors.RESET}")
            self.logger.info(f"  Remote: {remote_commit[:8]}")
            self.logger.info(f"  Local:  {local_commit[:8] if local_commit else 'unknown'}")
            return True
            
        # Check file changes (fallback)
        current_hashes = self.get_monitored_files()
        old_hashes = state.get('file_hashes', {})
        
        added, modified, deleted = self.compare_files(old_hashes, current_hashes)
        
        if added or modified or deleted:
            self.print_file_changes(added, modified, deleted)
            return True
            
        return False
        
    def run_deployment_cycle(self):
        """Run single deployment check cycle"""
        try:
            if self.check_for_updates():
                if self.perform_deployment():
                    # Update state after successful deployment
                    new_commit = self.get_local_commit_hash()
                    new_hashes = self.get_monitored_files()
                    
                    state = {
                        'last_commit': new_commit,
                        'last_deployment': datetime.now().isoformat(),
                        'file_hashes': new_hashes
                    }
                    self.save_state(state)
                    
        except Exception as e:
            self.logger.error(f"{Colors.RED}💥 Deployment cycle failed: {e}{Colors.RESET}")
            
    def run(self):
        """Main deployment loop"""
        self.logger.info(f"{Colors.BRIGHT}🎯 Auto-Deployer Started{Colors.RESET}")
        self.logger.info(f"Repository: {self.repo_url}")
        self.logger.info(f"Branch: {self.branch}")
        self.logger.info(f"Check interval: {self.check_interval}s")
        self.logger.info(f"Project root: {self.project_root}")
        
        while True:
            try:
                self.run_deployment_cycle()
                time.sleep(self.check_interval)
                
            except KeyboardInterrupt:
                self.logger.info(f"{Colors.YELLOW}🛑 Auto-Deployer stopped by user{Colors.RESET}")
                break
            except Exception as e:
                self.logger.error(f"{Colors.RED}💥 Unexpected error: {e}{Colors.RESET}")
                time.sleep(self.check_interval)

if __name__ == '__main__':
    deployer = AutoDeployer()
    deployer.run()