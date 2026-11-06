"""Media integration checks against the real app; temporary session, read-only data."""
from html.parser import HTMLParser
from pathlib import Path
import tempfile
import unittest
from app import create_app

class Images(HTMLParser):
    def __init__(self):
        super().__init__(); self.images = []
    def handle_starttag(self, tag, attrs):
        if tag == 'img': self.images.append(dict(attrs))

class MediaIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.client = create_app({'TESTING': True, 'SECRET_KEY': 'media-test-only',
            'AUDIT_PATH': Path(self.temp.name)/'audit.jsonl'}).test_client()
    def tearDown(self):
        self.temp.cleanup()
    def sign_in(self):
        with self.client.session_transaction() as session:
            session['user_id'] = 1
    def test_help_requires_login(self):
        self.assertEqual(self.client.get('/how-it-works').status_code, 302)
    def test_media_is_served_and_has_alternative_text(self):
        self.sign_in()
        for route in ['/', '/?media=baseline', '/how-it-works']:
            response = self.client.get(route)
            self.assertEqual(response.status_code, 200)
            parser = Images(); parser.feed(response.text)
            self.assertGreaterEqual(len(parser.images), 2)
            for image in parser.images:
                self.assertIn('alt', image)
                self.assertTrue(image['src'].startswith('/static/'))
                with self.client.get(image['src']) as asset:
                    self.assertEqual(asset.status_code, 200)

if __name__ == '__main__': unittest.main(verbosity=2)
