import os
import sys
import time
import threading
from typing import List, Dict, Any, Optional, Tuple
import PySimpleGUI as sg

from ..config import config
from ..downloaders import YtdlpDownloader, Aria2Downloader
from ..services import ProxyManager, CaptchaSolver, BatchManager
from ..utils import is_youtube_url, check_aria2_installed, ensure_dir, format_size


class GuiInterface:
    """
    Graphical user interface for the YouTube Downloader.
    """
    
    def __init__(self):
        """
        Initialize the GUI interface.
        """
        # Set theme
        sg.theme('DarkBlue3')
        
        # Create services
        self.proxy_manager = ProxyManager()
        self.captcha_solver = CaptchaSolver()
        
        # Create batch manager
        self.batch_manager = BatchManager(
            proxy_manager=self.proxy_manager
        )
        
        # Initialize download tracking
        self.stop_flag = threading.Event()
        self.update_thread = None
    
    def create_main_window(self) -> sg.Window:
        """
        Create the main window for the GUI.
        
        Returns:
            PySimpleGUI window
        """
        # Define the window layout
        layout = [
            [sg.Text('YouTube Video Downloader', font=('Helvetica', 16), justification='center', expand_x=True)],
            
            # URL input
            [sg.Text('Video URL(s):', font=('Helvetica', 10, 'bold'))],
            [sg.Multiline(size=(70, 5), key='-URLS-')],
            [sg.Text('Or load from file:'), sg.Input(key='-URL-FILE-'), sg.FileBrowse()],
            
            # Download options
            [sg.Frame('Download Options', [
                [sg.Text('Download Directory:'), 
                 sg.Input(default_text=config.get('download_dir'), key='-OUTPUT-DIR-'), 
                 sg.FolderBrowse()],
                [sg.Checkbox('Use Aria2 (faster downloads)', key='-USE-ARIA2-', default=config.get('aria2.enabled', True))],
                [sg.Text('Video Format:'), 
                 sg.Combo(['best', 'bestvideo+bestaudio', '1080p', '720p', '480p', '360p'], 
                          default_value=config.get('ytdlp.format', 'bestvideo+bestaudio/best'),
                          key='-FORMAT-')],
                [sg.Checkbox('Download Subtitles', key='-SUBTITLES-')],
            ])],
            
            # Proxy options
            [sg.Frame('Proxy Settings', [
                [sg.Text('Proxy URL:'), sg.Input(key='-PROXY-', default_text=config.get('default_proxy', ''))],
                [sg.Text('Or load from file:'), sg.Input(key='-PROXY-FILE-'), sg.FileBrowse()],
            ])],
            
            # Batch options
            [sg.Frame('Batch Settings', [
                [sg.Text('Max Concurrent Downloads:'), 
                 sg.Spin([i for i in range(1, 11)], initial_value=config.get('batch.max_concurrent', 3),
                        key='-CONCURRENT-')],
            ])],
            
            # Action buttons
            [sg.Button('Download', size=(15, 1)), sg.Button('Settings', size=(15, 1)), sg.Button('Exit', size=(15, 1))],
            
            # Download progress
            [sg.Text('Downloads:', font=('Helvetica', 10, 'bold'))],
            [sg.Table(values=[], headings=['URL', 'Status', 'Progress', 'Size', 'Speed', 'ETA'],
                     auto_size_columns=False,
                     col_widths=[30, 10, 10, 10, 10, 10],
                     justification='left',
                     key='-DOWNLOADS-',
                     enable_events=True,
                     expand_x=True,
                     expand_y=True,
                     size=(70, 10))],
            
            # Status bar
            [sg.Text('Ready', key='-STATUS-', size=(70, 1))],
        ]
        
        # Create the window
        return sg.Window('YouTube Downloader', layout, finalize=True, resizable=True)
    
    def create_settings_window(self) -> sg.Window:
        """
        Create the settings window for the GUI.
        
        Returns:
            PySimpleGUI window
        """
        # Define the window layout
        layout = [
            [sg.Text('Settings', font=('Helvetica', 16), justification='center', expand_x=True)],
            
            # Aria2 settings
            [sg.Frame('Aria2 Settings', [
                [sg.Text('Aria2 Path:'), 
                 sg.Input(default_text=config.get('aria2.path', 'aria2c'), key='-ARIA2-PATH-'),
                 sg.FileBrowse()],
                [sg.Text('Max Connections:'), 
                 sg.Spin([i for i in range(1, 17)], initial_value=config.get('aria2.max_connections', 4),
                        key='-ARIA2-CONNECTIONS-')],
                [sg.Text('Split:'), 
                 sg.Spin([i for i in range(1, 17)], initial_value=config.get('aria2.split', 4),
                        key='-ARIA2-SPLIT-')],
            ])],
            
            # CAPTCHA settings
            [sg.Frame('CAPTCHA Settings', [
                [sg.Text('2Captcha API Key:'), 
                 sg.Input(default_text=config.get('captcha_api_key', ''), key='-CAPTCHA-KEY-')],
            ])],
            
            # Advanced settings
            [sg.Frame('Advanced Settings', [
                [sg.Text('Configuration File:'), 
                 sg.Input(key='-CONFIG-FILE-'), 
                 sg.FileBrowse()],
                [sg.Button('Load Config'), sg.Button('Save Config')],
            ])],
            
            # Action buttons
            [sg.Button('Save', size=(15, 1)), sg.Button('Cancel', size=(15, 1))],
        ]
        
        # Create the window
        return sg.Window('Settings', layout, finalize=True, modal=True)
    
    def run(self) -> int:
        """
        Run the GUI interface.
        
        Returns:
            Exit code
        """
        # Check for required Aria2
        aria2_installed, aria2_version = check_aria2_installed()
        
        # Create the main window
        window = self.create_main_window()
        
        # Display a warning if Aria2 is not installed
        if not aria2_installed:
            sg.popup_warning(
                "Aria2 is not installed or not found in PATH.\n"
                "Multi-threaded downloads will not be available.",
                title="Warning"
            )
            window['-USE-ARIA2-'].update(value=False)
            window['-USE-ARIA2-'].update(disabled=True)
        
        # Start the update thread
        self.update_thread = threading.Thread(
            target=self._update_downloads_table,
            args=(window,),
            daemon=True
        )
        self.update_thread.start()
        
        try:
            # Event loop
            while True:
                event, values = window.read(timeout=100)
                
                # Handle window closing
                if event in (sg.WIN_CLOSED, 'Exit'):
                    break
                
                # Handle download button
                if event == 'Download':
                    # Get URLs
                    urls = []
                    
                    if values['-URLS-']:
                        # Parse URLs from text input
                        for line in values['-URLS-'].splitlines():
                            line = line.strip()
                            if line:
                                urls.append(line)
                    
                    if values['-URL-FILE-'] and os.path.exists(values['-URL-FILE-']):
                        # Load URLs from file
                        try:
                            with open(values['-URL-FILE-'], 'r') as f:
                                for line in f:
                                    line = line.strip()
                                    if line and not line.startswith('#'):
                                        urls.append(line)
                        except Exception as e:
                            sg.popup_error(f"Error reading URL file: {e}", title="Error")
                    
                    # Validate URLs
                    valid_urls = []
                    for url in urls:
                        if is_youtube_url(url):
                            valid_urls.append(url)
                        else:
                            sg.popup_warning(f"Skipping invalid YouTube URL: {url}", title="Warning")
                    
                    if not valid_urls:
                        sg.popup_error("No valid YouTube URLs to download", title="Error")
                        continue
                    
                    # Update configuration
                    if values['-OUTPUT-DIR-']:
                        output_dir = values['-OUTPUT-DIR-']
                        ensure_dir(output_dir)
                        config.set('download_dir', output_dir)
                    
                    if values['-CONCURRENT-']:
                        config.set('batch.max_concurrent', int(values['-CONCURRENT-']))
                    
                    # Update batch manager
                    self.batch_manager = BatchManager(
                        download_dir=config.get('download_dir'),
                        max_concurrent=config.get('batch.max_concurrent'),
                        proxy_manager=self.proxy_manager
                    )
                    
                    # Add URLs to batch manager
                    download_ids = self.batch_manager.add_urls(
                        urls=valid_urls,
                        use_aria2=values['-USE-ARIA2-'] and aria2_installed,
                        format_str=values['-FORMAT-'],
                        proxy=values['-PROXY-'],
                        subtitles=values['-SUBTITLES-']
                    )
                    
                    # Update status
                    window['-STATUS-'].update(f"Added {len(valid_urls)} URLs to download queue")
                
                # Handle settings button
                if event == 'Settings':
                    # Create settings window
                    settings_window = self.create_settings_window()
                    
                    # Settings window event loop
                    while True:
                        settings_event, settings_values = settings_window.read()
                        
                        # Handle window closing
                        if settings_event in (sg.WIN_CLOSED, 'Cancel'):
                            break
                        
                        # Handle save button
                        if settings_event == 'Save':
                            # Update configuration
                            config.set('aria2.path', settings_values['-ARIA2-PATH-'])
                            config.set('aria2.max_connections', int(settings_values['-ARIA2-CONNECTIONS-']))
                            config.set('aria2.split', int(settings_values['-ARIA2-SPLIT-']))
                            config.set('captcha_api_key', settings_values['-CAPTCHA-KEY-'])
                            
                            # Update CAPTCHA solver
                            self.captcha_solver = CaptchaSolver(settings_values['-CAPTCHA-KEY-'])
                            
                            sg.popup_ok("Settings saved", title="Success")
                            break
                        
                        # Handle load config button
                        if settings_event == 'Load Config' and settings_values['-CONFIG-FILE-']:
                            try:
                                from ..config import Config
                                global config
                                config = Config(settings_values['-CONFIG-FILE-'])
                                
                                # Update settings window
                                settings_window['-ARIA2-PATH-'].update(config.get('aria2.path', 'aria2c'))
                                settings_window['-ARIA2-CONNECTIONS-'].update(config.get('aria2.max_connections', 4))
                                settings_window['-ARIA2-SPLIT-'].update(config.get('aria2.split', 4))
                                settings_window['-CAPTCHA-KEY-'].update(config.get('captcha_api_key', ''))
                                
                                sg.popup_ok("Configuration loaded", title="Success")
                            except Exception as e:
                                sg.popup_error(f"Error loading configuration: {e}", title="Error")
                        
                        # Handle save config button
                        if settings_event == 'Save Config' and settings_values['-CONFIG-FILE-']:
                            try:
                                config.save(settings_values['-CONFIG-FILE-'])
                                sg.popup_ok("Configuration saved", title="Success")
                            except Exception as e:
                                sg.popup_error(f"Error saving configuration: {e}", title="Error")
                    
                    # Close settings window
                    settings_window.close()
                
                # Handle download table events
                if event == '-DOWNLOADS-' and len(values['-DOWNLOADS-']) > 0:
                    selected_index = values['-DOWNLOADS-'][0]
                    
                    # Get all downloads
                    downloads = self.batch_manager.get_all_downloads()
                    download_ids = list(downloads.keys())
                    
                    if selected_index < len(download_ids):
                        download_id = download_ids[selected_index]
                        download = downloads[download_id]
                        
                        # Show the download details
                        sg.popup(
                            f"URL: {download['url']}\n"
                            f"Status: {download['status']}\n"
                            f"Progress: {download['progress']:.1f}%\n"
                            f"Size: {format_size(download['total_bytes'])}\n"
                            f"Downloaded: {format_size(download['downloaded_bytes'])}\n"
                            f"Added: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(download['added_at']))}\n"
                            f"Output: {download['output_file'] or 'Not completed'}\n"
                            f"Error: {download['error'] or 'None'}\n",
                            title="Download Details"
                        )
        
        except Exception as e:
            sg.popup_error(f"Error: {e}", title="Error")
            return 1
        
        finally:
            # Stop the update thread
            self.stop_flag.set()
            if self.update_thread and self.update_thread.is_alive():
                self.update_thread.join(timeout=1)
            
            # Stop the batch manager
            self.batch_manager.stop()
            
            # Close the window
            window.close()
        
        return 0
    
    def _update_downloads_table(self, window: sg.Window) -> None:
        """
        Update the downloads table in the main window.
        
        Args:
            window: Main window
        """
        while not self.stop_flag.is_set():
            try:
                # Get all downloads
                downloads = self.batch_manager.get_all_downloads()
                
                # Update the table
                table_data = []
                for download_id, download in downloads.items():
                    url = download['url']
                    status = download['status'].capitalize()
                    progress = f"{download['progress']:.1f}%" if download['progress'] > 0 else "0.0%"
                    size = format_size(download['total_bytes']) if download['total_bytes'] > 0 else "Unknown"
                    speed = format_size(download.get('speed', 0)) + "/s" if download.get('speed', 0) > 0 else "N/A"
                    eta = f"{download.get('eta', 0)}s" if download.get('eta', 0) > 0 else "N/A"
                    
                    table_data.append([url, status, progress, size, speed, eta])
                
                # Update the table
                window['-DOWNLOADS-'].update(values=table_data)
                
                # Update status
                active_downloads = sum(1 for d in downloads.values() if d['status'] in ('queued', 'downloading'))
                completed_downloads = sum(1 for d in downloads.values() if d['status'] == 'completed')
                failed_downloads = sum(1 for d in downloads.values() if d['status'] == 'failed')
                
                if active_downloads > 0:
                    window['-STATUS-'].update(f"Downloading {active_downloads} file(s)")
                elif len(downloads) > 0:
                    window['-STATUS-'].update(f"Completed: {completed_downloads}, Failed: {failed_downloads}")
                else:
                    window['-STATUS-'].update("Ready")
            
            except Exception as e:
                print(f"Error updating downloads table: {e}")
            
            # Sleep to avoid high CPU usage
            time.sleep(0.5)


def main() -> int:
    """
    Main entry point for the graphical user interface.
    
    Returns:
        Exit code
    """
    gui = GuiInterface()
    return gui.run()


if __name__ == "__main__":
    sys.exit(main())