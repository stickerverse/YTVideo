import unittest
import os
import tempfile
from unittest.mock import patch, MagicMock

from youtube_downloader.utils import (
    is_url, 
    is_youtube_url, 
    ensure_dir, 
    read_urls_from_file, 
    sanitize_filename,
    check_aria2_installed,
    format_size
)


class TestUtils(unittest.TestCase):
    """
    Tests for utility functions.
    """
    
    def test_is_url(self):
        """
        Test URL validation.
        """
        # Valid URLs
        self.assertTrue(is_url('https://www.example.com'))
        self.assertTrue(is_url('http://example.com'))
        self.assertTrue(is_url('https://www.youtube.com/watch?v=dQw4w9WgXcQ'))
        
        # Invalid URLs
        self.assertFalse(is_url('not a url'))
        self.assertFalse(is_url('www.example.com'))  # Missing scheme
        self.assertFalse(is_url('https://'))  # Missing netloc
    
    def test_is_youtube_url(self):
        """
        Test YouTube URL validation.
        """
        # Valid YouTube URLs
        self.assertTrue(is_youtube_url('https://www.youtube.com/watch?v=dQw4w9WgXcQ'))
        self.assertTrue(is_youtube_url('https://youtu.be/dQw4w9WgXcQ'))
        self.assertTrue(is_youtube_url('https://youtube.com/playlist?list=PLlaN88a7y2_plecYoJxvRFTLHVbIVAOoS'))
        self.assertTrue(is_youtube_url('http://www.youtube.com/watch?v=dQw4w9WgXcQ'))
        
        # Invalid YouTube URLs
        self.assertFalse(is_youtube_url('https://www.example.com'))
        self.assertFalse(is_youtube_url('not a url'))
        self.assertFalse(is_youtube_url('https://vimeo.com/123456789'))
    
    def test_ensure_dir(self):
        """
        Test directory creation.
        """
        # Create a temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            # Test with existing directory
            result = ensure_dir(temp_dir)
            self.assertEqual(result, temp_dir)
            self.assertTrue(os.path.exists(temp_dir))
            
            # Test with new directory
            new_dir = os.path.join(temp_dir, 'new_dir')
            result = ensure_dir(new_dir)
            self.assertEqual(result, new_dir)
            self.assertTrue(os.path.exists(new_dir))
            
            # Test with nested directory
            nested_dir = os.path.join(temp_dir, 'nested/dir')
            result = ensure_dir(nested_dir)
            self.assertEqual(result, nested_dir)
            self.assertTrue(os.path.exists(nested_dir))
    
    def test_read_urls_from_file(self):
        """
        Test reading URLs from a file.
        """
        # Create a temporary file with URLs
        with tempfile.NamedTemporaryFile(mode='w+', delete=False) as temp_file:
            temp_file.write("https://www.youtube.com/watch?v=dQw4w9WgXcQ\n")
            temp_file.write("# Comment line\n")
            temp_file.write("\n")  # Empty line
            temp_file.write("https://www.youtube.com/watch?v=9bZkp7q19f0\n")
            temp_file_path = temp_file.name
        
        try:
            # Read URLs from the file
            urls = read_urls_from_file(temp_file_path)
            
            # Check the results
            self.assertEqual(len(urls), 2)
            self.assertEqual(urls[0], "https://www.youtube.com/watch?v=dQw4w9WgXcQ")
            self.assertEqual(urls[1], "https://www.youtube.com/watch?v=9bZkp7q19f0")
            
            # Test with non-existent file
            with self.assertRaises(FileNotFoundError):
                read_urls_from_file("non_existent_file.txt")
        finally:
            # Clean up
            os.unlink(temp_file_path)
    
    def test_sanitize_filename(self):
        """
        Test filename sanitization.
        """
        # Test with invalid characters
        self.assertEqual(sanitize_filename('file:name'), 'file_name')
        self.assertEqual(sanitize_filename('file/name'), 'file_name')
        self.assertEqual(sanitize_filename('file\\name'), 'file_name')
        self.assertEqual(sanitize_filename('file?name'), 'file_name')
        self.assertEqual(sanitize_filename('file*name'), 'file_name')
        self.assertEqual(sanitize_filename('file"name'), 'file_name')
        self.assertEqual(sanitize_filename('file<name'), 'file_name')
        self.assertEqual(sanitize_filename('file>name'), 'file_name')
        self.assertEqual(sanitize_filename('file|name'), 'file_name')
        
        # Test with long filename
        long_name = 'a' * 300
        sanitized = sanitize_filename(long_name)
        self.assertLessEqual(len(sanitized), 255)
    
    @patch('subprocess.run')
    def test_check_aria2_installed(self, mock_run):
        """
        Test Aria2 installation check.
        """
        # Mock subprocess.run for success
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = "aria2 version 1.36.0"
        mock_run.return_value = mock_process
        
        # Check if Aria2 is installed
        is_installed, version = check_aria2_installed()
        
        # Check the results
        self.assertTrue(is_installed)
        self.assertEqual(version, "1.36.0")
        
        # Mock subprocess.run for failure
        mock_process.returncode = 1
        is_installed, version = check_aria2_installed()
        
        # Check the results
        self.assertFalse(is_installed)
        self.assertIsNone(version)
        
        # Mock subprocess.run to raise an exception
        mock_run.side_effect = Exception("Command failed")
        is_installed, version = check_aria2_installed()
        
        # Check the results
        self.assertFalse(is_installed)
        self.assertIsNone(version)
    
    def test_format_size(self):
        """
        Test size formatting.
        """
        self.assertEqual(format_size(0), "0 B")
        self.assertEqual(format_size(1023), "1023 B")
        self.assertEqual(format_size(1024), "1.00 KB")
        self.assertEqual(format_size(1024 * 1024), "1.00 MB")
        self.assertEqual(format_size(1024 * 1024 * 1024), "1.00 GB")
        self.assertEqual(format_size(1024 * 1024 * 1024 * 2), "2.00 GB")


if __name__ == '__main__':
    unittest.main()