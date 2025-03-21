"""
Hoesway Update Manager

Handles automatic checking and downloading of updates for Hoesway.
Uses GitHub API to check for updates and prompts users to download updates.
"""

import os
import sys
import json
import time
import subprocess
import threading
import shutil
import tkinter as tk
from tkinter import ttk, messagebox
import requests
import zipfile
import tempfile
import datetime
import urllib.parse

class UpdateManager:
    """Manages application updates from GitHub releases"""
    
    def __init__(self, current_version, app_name="Hoesway", repo_owner="ConejoFastDL", repo_name="SomethingInteresting"):
        self.current_version = current_version
        self.app_name = app_name
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.api_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/releases/latest"
        self.check_interval = 24 * 60 * 60  # 24 hours in seconds
        
        # Setup necessary directories
        self.app_dir = os.path.abspath(os.path.dirname(sys.argv[0]))
        self.config_dir = os.path.join(os.path.expanduser("~"), f".{app_name.lower()}")
        
        if not os.path.exists(self.config_dir):
            os.makedirs(self.config_dir, exist_ok=True)
            
        self.last_check_file = os.path.join(self.config_dir, "last_update_check.txt")
        
    def check_for_updates(self, force=False):
        """
        Check if there are any updates available
        
        Args:
            force (bool): If True, bypass the time interval check
            
        Returns:
            dict or None: Update info if available, None otherwise
        """
        if not force and not self._should_check():
            return None
            
        # Update the last check time
        with open(self.last_check_file, "w") as f:
            f.write(str(datetime.datetime.now().timestamp()))
            
        try:
            return self._check_github_for_updates()
        except Exception as e:
            print(f"Error checking for updates: {e}")
            return None
            
    def _should_check(self):
        """Determine if we should check for updates based on the time interval"""
        if not os.path.exists(self.last_check_file):
            return True
            
        try:
            with open(self.last_check_file, "r") as f:
                last_check = float(f.read().strip())
                
            elapsed = datetime.datetime.now().timestamp() - last_check
            return elapsed >= self.check_interval
            
        except Exception:
            # If there's any issue reading the file, check for updates
            return True
            
    def _check_github_for_updates(self):
        """Check GitHub API for the latest release"""
        try:
            response = requests.get(self.api_url, timeout=10)
            response.raise_for_status()
            
            release_data = response.json()
            latest_version = release_data.get("tag_name", "").lstrip("v")
            
            # Compare versions
            if self._compare_versions(latest_version, self.current_version) > 0:
                return {
                    "version": latest_version,
                    "download_url": release_data.get("assets", [{}])[0].get("browser_download_url", ""),
                    "release_notes": release_data.get("body", ""),
                    "published_at": release_data.get("published_at", "")
                }
                
            return None
            
        except Exception as e:
            print(f"Error fetching update information: {e}")
            return None
            
    def _compare_versions(self, version1, version2):
        """
        Compare two version strings
        
        Returns:
            int: 1 if version1 > version2, -1 if version1 < version2, 0 if equal
        """
        v1_parts = [int(x) for x in version1.split(".")]
        v2_parts = [int(x) for x in version2.split(".")]
        
        # Pad shorter version with zeros
        while len(v1_parts) < len(v2_parts):
            v1_parts.append(0)
        while len(v2_parts) < len(v1_parts):
            v2_parts.append(0)
            
        for i in range(len(v1_parts)):
            if v1_parts[i] > v2_parts[i]:
                return 1
            elif v1_parts[i] < v2_parts[i]:
                return -1
                
        return 0
        
    def download_and_install_update(self, update_info, callback=None):
        """
        Download and install the update
        
        Args:
            update_info (dict): Update information
            callback (func): Optional callback for progress updates
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not update_info or not update_info.get("download_url"):
            return False
            
        try:
            # Download the update
            if callback:
                callback("Downloading update...")
                
            response = requests.get(update_info["download_url"], stream=True, timeout=60)
            response.raise_for_status()
            
            # Parse the filename from the URL
            url_path = urllib.parse.urlparse(update_info["download_url"]).path
            filename = os.path.basename(url_path)
            
            # Create a temporary directory for the download
            with tempfile.TemporaryDirectory() as temp_dir:
                downloaded_file = os.path.join(temp_dir, filename)
                
                # Save the downloaded file
                with open(downloaded_file, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            
                if callback:
                    callback("Installing update...")
                    
                # Handle different file types
                if filename.endswith('.zip'):
                    return self._install_from_zip(downloaded_file, callback)
                else:
                    return self._install_executable(downloaded_file, callback)
                    
        except Exception as e:
            if callback:
                callback(f"Error during update: {e}")
            print(f"Error during update: {e}")
            return False
            
    def _install_from_zip(self, zip_file, callback=None):
        """Extract and install from a zip file"""
        try:
            with tempfile.TemporaryDirectory() as extract_dir:
                with zipfile.ZipFile(zip_file, 'r') as zip_ref:
                    zip_ref.extractall(extract_dir)
                    
                # Find the executable in the extracted files
                for root, _, files in os.walk(extract_dir):
                    for file in files:
                        if file.endswith('.exe') and self.app_name.lower() in file.lower():
                            exe_path = os.path.join(root, file)
                            return self._install_executable(exe_path, callback)
                            
            if callback:
                callback("No executable found in the downloaded package.")
            return False
            
        except Exception as e:
            if callback:
                callback(f"Error extracting update: {e}")
            return False
            
    def _install_executable(self, exe_path, callback=None):
        """Install the update by replacing the current executable"""
        try:
            current_exe = sys.executable
            if hasattr(sys, 'frozen'):
                current_exe = sys.executable
            else:
                # For development environments, use the script path
                current_exe = os.path.join(self.app_dir, f"{self.app_name}.exe")
                
            if not os.path.exists(current_exe):
                current_exe = os.path.join(self.app_dir, "dist", f"{self.app_name}.exe")
                
            # Create backup directory if needed
            backup_dir = os.path.join(self.app_dir, "backup")
            os.makedirs(backup_dir, exist_ok=True)
            
            # Create a backup
            backup_file = os.path.join(backup_dir, f"{self.app_name}_backup_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.exe")
            shutil.copy2(current_exe, backup_file)
            
            if callback:
                callback("Creating installation script...")
                
            # Create a batch script to complete the installation
            batch_file = os.path.join(tempfile.gettempdir(), f"update_{self.app_name}.bat")
            
            with open(batch_file, 'w') as f:
                f.write('@echo off\n')
                f.write('echo Updating application...\n')
                f.write(f'ping 127.0.0.1 -n 3 > nul\n')  # Wait for 2 seconds
                f.write(f'copy /Y "{exe_path}" "{current_exe}"\n')
                f.write('echo Update complete!\n')
                f.write(f'start "" "{current_exe}"\n')
                f.write('del "%~f0"\n')  # Delete this batch file
                
            # Start the batch file
            subprocess.Popen(f'cmd /c "{batch_file}"', shell=True)
            
            if callback:
                callback("Update ready. Please close the application to complete installation.")
                
            return True
            
        except Exception as e:
            if callback:
                callback(f"Error installing update: {e}")
            return False
            
    def create_release_package(self, version, executable_path, release_notes=""):
        """
        Create a release package for GitHub
        
        Args:
            version (str): Version number for the release
            executable_path (str): Path to the executable
            release_notes (str): Release notes for the release
            
        Returns:
            str: Path to the created release package
        """
        release_dir = os.path.join(self.app_dir, "release")
        os.makedirs(release_dir, exist_ok=True)
        
        # Create release zip file
        zip_filename = f"{self.app_name}_v{version}.zip"
        zip_path = os.path.join(release_dir, zip_filename)
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Add the executable
            zipf.write(executable_path, os.path.basename(executable_path))
            
            # Add release notes
            if release_notes:
                notes_file = os.path.join(release_dir, "release_notes.txt")
                with open(notes_file, 'w') as f:
                    f.write(release_notes)
                zipf.write(notes_file, "release_notes.txt")
                
        print(f"Release package created at {zip_path}")
        return zip_path
        
    def prompt_for_update(self, parent, update_info):
        """
        Show a dialog prompting the user to update
        
        Args:
            parent: Parent window for the dialog
            update_info (dict): Information about the update
            
        Returns:
            bool: True if user wants to update, False otherwise
        """
        message = (
            f"A new version of {self.app_name} is available!\n\n"
            f"Current version: {self.current_version}\n"
            f"New version: {update_info['version']}\n\n"
            f"Would you like to update now?"
        )
        
        if 'release_notes' in update_info and update_info['release_notes']:
            message += f"\n\nRelease notes:\n{update_info['release_notes']}"
        
        result = messagebox.askyesno("Update Available", message)
        return result
        
    def download_and_install_update_with_ui(self, update_info, parent=None):
        """
        Install the update from the local file
        
        Args:
            update_info (dict): Information about the update
            parent: Optional parent window for progress dialog
            
        Returns:
            bool: True if update was successful, False otherwise
        """
        if parent:
            # Create a progress dialog
            progress_window = tk.Toplevel(parent)
            progress_window.title("Installing Update")
            progress_window.geometry("400x150")
            progress_window.transient(parent)
            progress_window.grab_set()
            progress_window.resizable(False, False)
            
            # Center in parent window
            if parent:
                x = parent.winfo_x() + (parent.winfo_width() - 400) // 2
                y = parent.winfo_y() + (parent.winfo_height() - 150) // 2
                progress_window.geometry(f"+{x}+{y}")
            
            # Add progress components
            ttk.Label(progress_window, text=f"Installing {self.app_name} v{update_info['version']}...", 
                    font=("Segoe UI", 12)).pack(pady=(20, 10))
            
            progress_var = tk.DoubleVar()
            progress_bar = ttk.Progressbar(progress_window, variable=progress_var, length=350, mode="indeterminate")
            progress_bar.pack(pady=10, padx=25)
            progress_bar.start(15)
            
            status_var = tk.StringVar(value="Preparing installation...")
            status_label = ttk.Label(progress_window, textvariable=status_var)
            status_label.pack(pady=10)
            
            # Start the installation in a separate thread
            def install_thread():
                try:
                    self.download_and_install_update(update_info, lambda status: status_var.set(status))
                    progress_window.destroy()
                    messagebox.showinfo("Update Successful", 
                                      f"{self.app_name} has been updated to version {update_info['version']}.\n"
                                      f"Please restart the application to use the new version.")
                except Exception as e:
                    progress_window.destroy()
                    messagebox.showerror("Update Failed", f"Error installing update: {e}")
                    
            threading.Thread(target=install_thread, daemon=True).start()
            return True
        else:
            # No parent window, just install directly
            try:
                self.download_and_install_update(update_info)
                return True
            except Exception as e:
                print(f"Error installing update: {e}")
                return False

# Example usage
if __name__ == "__main__":
    # Test the update manager
    update_manager = UpdateManager(current_version="0.6.0")
    update_info = update_manager.check_for_updates(force=True)
    
    if update_info:
        print(f"Update available: {update_info['version']}")
    else:
        print("No updates available.")
        
    # To create an update package (for testing):
    # update_manager.create_release_package("0.7.0", "path/to/executable.exe", release_notes="Bug fixes and improvements")
