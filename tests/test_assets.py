import hashlib
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]

class VisualAssetTests(unittest.TestCase):
    def test_original_wallpapers_unchanged(self):
        signatures = {
            'portwise_light_bg.png':'73485e3a2d4bf490f08997a6d346f6a0bf96fca9d6fd91b843c360556bce1d9b',
            'portwise_dark_bg.png':'7c8d5533aaf447da46936547cde3e09caaf5dc45666749d925a0d5e5f4f28313',
        }
        for name, expected in signatures.items():
            data=(HERE/'static'/name).read_bytes()
            self.assertTrue(data.startswith(b'\x89PNG\r\n\x1a\n'))
            self.assertEqual(hashlib.sha256(data).hexdigest(), expected)

    def test_theme_and_motion_present(self):
        text=(HERE/'app.py').read_text()
        for snippet in ('portwiseOceanPan','portwiseShimmer','prefers-reduced-motion',
                        '"theme": "Light"','"verify-email"','otp_timer','verify_email_page'):
            self.assertIn(snippet,text)


if __name__=='__main__':
    unittest.main()
