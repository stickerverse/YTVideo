import unittest
import os
import tempfile
from unittest.mock import patch, MagicMock

from youtube_downloader.downloaders import YtdlpDownloader, Aria2Downloader
from youtube_downloader.utils import is_youtube_url


class TestYtdlpDownloader(unittest.TestCase):
    """
    Tests for the yt-dlp downloader.
    """
    
    def setUp(self):
        """
        Set up test environment.
        """
        # Create a temporary directory for downloads
        self.temp_dir = tempfile.mkdtemp()
        self.downloader = YtdlpDownloader(download_dir=self.temp_dir)
    
    def tearDown(self):
        """
        Clean up test environment.
        """
        # Remove the temporary directory
        for root, dirs, files in os.walk(self.temp_dir, topdown=False):
            for name in files:
                os.remove(os.path.join(root, name))
            for name in dirs:
                os.rmdir(os.path.join(root, name))
        os.rmdir(self.temp_dir)
    
    @patch('yt_dlp.YoutubeDL')
    def test_download(self, mock_ytdl):
        """
        Test downloading a video with yt-dlp.
        """
        # Mock YoutubeDL instance
        mock_ytdl_instance = MagicMock()
        mock_ytdl.return_value.__enter__.return_value = mock_ytdl_instance
        
        # Mock extract_info method
        mock_ytdl_instance.extract_info.return_value = {
            'title': 'test_video',
            'ext': 'mp4',
        }
        
        # Download a video
        url = 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'
        output_file = self.downloader.download(url)
        
        # Check that YoutubeDL was called with the correct arguments
        mock_ytdl.assert_called_once()
        mock_ytdl_instance.extract_info.assert_called_once_with(url, download=True)
        
        # Check that the output file path is correct
        self.assertEqual(os.path.basename(output_file), 'test_video.mp4')
        self.assertTrue(output_file.startswith(self.temp_dir))
    
    def test_get_info(self):
        """
        Test getting information about a video.
        """
        # This is more of an integration test, so we'll skip it for now
        pass
    
    def test_is_youtube_url(self):
        """
        Test the YouTube URL validation function.
        """
        # Valid YouTube URLs
        self.assertTrue(is_youtube_url('https://www.youtube.com/watch?v=dQw4w9WgXcQ'))
        self.assertTrue(is_youtube_url('https://youtu.be/dQw4w9WgXcQ'))
        self.assertTrue(is_youtube_url('https://youtube.com/playlist?list=PLlaN88a7y2_plecYoJxvRFTLHVbIVAOoS'))
        
        # Invalid YouTube URLs
        self.assertFalse(is_youtube_url('https://www.example.com'))
        self.assertFalse(is_youtube_url('not a url'))
        self.assertFalse(is_youtube_url('https://vimeo.com/123456789'))


class TestAria2Downloader(unittest.TestCase):
    """
    Tests for the Aria2 downloader.
    """
    
    @unittest.skipIf(os.system('aria2c --version > /dev/null 2>&1') != 0,
                     "Aria2 is not installed")
    def setUp(self):
        """
        Set up test environment.
        """
        # Create a temporary directory for downloads
        self.temp_dir = tempfile.mkdtemp()
        self.downloader = Aria2Downloader(download_dir=self.temp_dir)
    
    def tearDown(self):
        """
        Clean up test environment.
        """
        # Remove the temporary directory if it exists
        if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
            for root, dirs, files in os.walk(self.temp_dir, topdown=False):
                for name in files:
                    os.remove(os.path.join(root, name))
                for name in dirs:
                    os.rmdir(os.path.join(root, name))
            os.rmdir(self.temp_dir)
    
    @unittest.skipIf(os.system('aria2c --version > /dev/null 2>&1') != 0,
                     "Aria2 is not installed")
    @patch('subprocess.Popen')
    def test_download(self, mock_popen):
        """
        Test downloading a file with Aria2.
        """
        # Mock subprocess.Popen
        mock_process = MagicMock()
        mock_process.stdout = None
        mock_process.poll.return_value = None
        mock_process.wait.return_value = 0
        mock_popen.return_value = mock_process
        
        # Download a file
        url = 'https://example.com/file.zip'
        output_file = os.path.join(self.temp_dir, 'file.zip')
        
        # Create an empty file to simulate a successful download
        with open(output_file, 'w') as f:
            f.write('')
        
        result = self.downloader.download(url)
        
        # Check that subprocess.Popen was called with the correct arguments
        mock_popen.assert_called_once()
        args = mock_popen.call_args[0][0]
        self.assertEqual(args[0], self.downloader.aria2_path)
        self.assertIn('--max-connection-per-server', args)
        self.assertIn('--split', args)
        self.assertIn(url, args)
        
        # Check that the output file path is correct
        self.assertEqual(result, output_file)


if __name__ == '__main__':
    unittest.main()