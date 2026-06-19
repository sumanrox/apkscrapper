import unittest
from unittest.mock import patch, MagicMock
import sys
sys.dont_write_bytecode = True
import os
import argparse

# Add parent directory to path so we can import the scraper
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from apkscraper.__main__ import APKPureScraper, processVersion

class TestAPKPureScraper(unittest.TestCase):
    
    def setUp(self):
        """Initialize the scraper before each test."""
        self.scraper = APKPureScraper()

    @patch('requests.Session.get')
    def test_search_success(self, mock_get):
        """Test that the search correctly parses a valid JSON API response."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"url": "...", "packageName": "com.google.android.youtube", "title": "YouTube"}
        ]
        mock_get.return_value = mock_response

        results = self.scraper.search("youtube")
        
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['id'], "com.google.android.youtube")
        self.assertEqual(results[0]['name'], "YouTube")

    @patch('requests.Session.get')
    def test_search_failure(self, mock_get):
        """Test that network errors or non-200s are handled gracefully."""
        import requests
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = requests.RequestException("Server Error")
        mock_get.return_value = mock_response

        results = self.scraper.search("youtube")
        
        # Should gracefully fallback to an empty list instead of crashing
        self.assertEqual(results, [])

    @patch('requests.Session.get')
    def test_getVersions_success(self, mock_get):
        """Test the HTML parsing logic for version extraction."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        # Simulating the HTML structure of the APKPure versions page
        mock_response.content = b'''
            <ul>
                <li>
                    <a href="/youtube-2025/com.google.android.youtube/download/21.21.91">Download</a>
                    <span class="update-on">2026-06-19</span>
                </li>
            </ul>
        '''
        mock_get.return_value = mock_response

        versions = self.scraper.getVersions("com.google.android.youtube")
        
        self.assertEqual(len(versions), 1)
        self.assertEqual(versions[0]['version'], "21.21.91")
        self.assertTrue("download/21.21.91" in versions[0]['url'])

    @patch('requests.Session.get')
    def test_getDownloadLink_success(self, mock_get):
        """Test the regex parser for the final CDN download link."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'<html><a href="https://d.apkpure.net/b/XAPK/com.test?versionCode=123">Click Here</a></html>'
        mock_get.return_value = mock_response

        link = self.scraper.getDownloadLink("https://apkpure.net/fake_download")
        
        self.assertEqual(link, "https://d.apkpure.net/b/XAPK/com.test?versionCode=123")

    @patch('requests.Session.get')
    def test_getDownloadLink_missing(self, mock_get):
        """Test handling when the CDN link is missing from the page."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'<html><body>No valid link here</body></html>'
        mock_get.return_value = mock_response

        link = self.scraper.getDownloadLink("https://apkpure.net/fake_download")
        
        self.assertIsNone(link)

if __name__ == '__main__':
    unittest.main()
