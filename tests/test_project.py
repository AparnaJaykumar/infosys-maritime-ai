import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

class ProjectTests(unittest.TestCase):
    def test_configuration_files_present(self):
        for fname in ['app.py','auth_core.py','requirements.txt','README.md','.env.example','Dockerfile']:
            self.assertTrue((ROOT/fname).exists(),fname)

    def test_missing_secrets_not_hardcoded(self):
        app=(ROOT/'app.py').read_text()
        self.assertIn('os.getenv("EMAIL_PASSWORD", "")',app)
        self.assertIn('os.getenv("ADMIN_PASSWORD", "")',app)
        self.assertIn('os.getenv("JWT_SECRET", "")',app)


if __name__=='__main__':
    unittest.main()
