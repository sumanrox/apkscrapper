import unittest
from unittest.mock import patch, MagicMock
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from apkscraper.__main__ import APKPureScraper, UptodownScraper, APKMirrorScraper

class TestDeveloperScraping(unittest.TestCase):

    def setUp(self):
        self.apkpure = APKPureScraper()
        self.uptodown = UptodownScraper()
        self.apkmirror = APKMirrorScraper()

    @patch('requests.Session.get')
    def test_apkpure_developer_apps(self, mock_get):
        """Test APKPure's getDeveloperApps method."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'''
            <html>
                <ul class="dt-app-list">
                    <li>
                        <a href="/some-app-1" class="apk-item" title="App One">
                            <p class="p1">App One</p>
                        </a>
                    </li>
                    <li>
                        <a href="/some-app-2" class="apk-item" title="App Two">
                            <p class="p1">App Two</p>
                        </a>
                    </li>
                </ul>
            </html>
        '''
        mock_get.return_value = mock_response

        apps = self.apkpure.getDeveloperApps("Google LLC")
        
        # Test if it returns the correctly parsed list of apps
        self.assertEqual(len(apps), 2)
        self.assertEqual(apps[0]['name'], "App One")
        self.assertEqual(apps[0]['url'], "https://apkpure.net/some-app-1")
        self.assertTrue(mock_get.called)
        
        # Check if the URL passed to requests is URL encoded
        args, kwargs = mock_get.call_args
        self.assertIn("Google%20LLC", args[0])

    @patch('requests.Session.post')
    def test_uptodown_developer_apps(self, mock_post):
        """Test Uptodown's getDeveloperApps method."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": 1,
            "data": {
                "apps": [
                    {"name": "App One", "url": "https://app-one.en.uptodown.com/android"}
                ]
            }
        }
        mock_post.return_value = mock_response

        apps = self.uptodown.getDeveloperApps("Google LLC")
        
        self.assertEqual(len(apps), 1)
        self.assertEqual(apps[0]['name'], "App One")
        self.assertEqual(apps[0]['id'], "https://app-one.en.uptodown.com/android")

    @patch('requests.Session.get')
    def test_apkmirror_developer_apps(self, mock_get):
        """Test APKMirror's getDeveloperApps method."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'''
            <html>
                <div class="appRow">
                    <a class="fontBlack" href="/apk/google-inc/app-one/">App One</a>
                </div>
            </html>
        '''
        mock_get.return_value = mock_response

        apps = self.apkmirror.getDeveloperApps("Google LLC")
        
        self.assertEqual(len(apps), 1)
        self.assertEqual(apps[0]['name'], "App One")
        self.assertEqual(apps[0]['id'], "/apk/google-inc/app-one/")

if __name__ == '__main__':
    unittest.main()
