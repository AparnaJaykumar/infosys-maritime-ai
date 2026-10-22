import tempfile
import time
import unittest
from pathlib import Path

from auth_core import Store, issue_token, decode_token, password_errors, valid_email

QUESTION = 'What was the name of your first school?'
SECRET = 'a' * 48


class AuthTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Store(Path(self.tmp.name) / 'test.db')
        ok, msg = self.db.signup('alex', 'al@cd.ef', 'StrongPwd1!', QUESTION, 'Sample School')
        self.assertTrue(ok, msg)

    def tearDown(self):
        self.tmp.cleanup()

    def test_signup_validation_and_duplicates(self):
        self.assertTrue(valid_email('ab@cd.ef'))
        self.assertTrue(valid_email('an@outlook.com'))
        self.assertFalse(valid_email('a@b.c'))
        self.assertTrue(password_errors('weak'))
        self.assertFalse(self.db.signup('alex', 'xy@cd.ef', 'StrongPwd1!', QUESTION, 'A')[0])
        self.assertFalse(self.db.signup('second', 'al@cd.ef', 'StrongPwd1!', QUESTION, 'A')[0])

    def test_login_generic_errors_and_activity(self):
        self.assertIsNotNone(self.db.authenticate('alex', 'StrongPwd1!')[0])
        missing, err1 = self.db.authenticate('missing', 'wrong')
        incorrect, err2 = self.db.authenticate('alex', 'wrong')
        self.assertIsNone(missing)
        self.assertIsNone(incorrect)
        self.assertEqual(err1, err2)
        self.assertGreaterEqual(len(self.db.account_events('alex')), 2)

    def test_limit(self):
        for _ in range(5):
            self.db.failure('admin-login')
        self.assertTrue(self.db.limited('admin-login'))
        self.db.clear_limit('admin-login')
        self.assertFalse(self.db.limited('admin-login'))

    def test_question_and_reset_revokes_sessions(self):
        self.assertTrue(self.db.verify_answer('alex', 'sample school'))
        account = self.db.user('alex')
        version = account['session_version']
        self.assertTrue(self.db.reset_password('al@cd.ef', 'NewStrongPwd2!')[0])
        self.assertEqual(self.db.user('alex')['session_version'], version+1)
        self.assertIsNotNone(self.db.authenticate('alex', 'NewStrongPwd2!')[0])
        self.assertIsNone(self.db.authenticate('alex', 'StrongPwd1!')[0])

    def test_otp_reset_and_expiration(self):
        code, error = self.db.begin_otp('al@cd.ef', SECRET)
        self.assertFalse(error)
        self.assertRegex(code, r'^\d{6}$')
        self.assertFalse(self.db.verify_otp('al@cd.ef', '00000x', SECRET))
        self.assertTrue(self.db.verify_otp('al@cd.ef', code, SECRET))
        self.assertFalse(self.db.verify_otp('al@cd.ef', code, SECRET))
        other, note = self.db.begin_otp('al@cd.ef', SECRET)
        self.assertIsNone(other)
        self.assertIn('five minutes', note)
        self.db.cancel_otp('al@cd.ef')
        code, _ = self.db.begin_otp('al@cd.ef', SECRET)
        with self.db.db() as c:
            c.execute('UPDATE resets SET expires_at=? WHERE email=?', (int(time.time())-1,'al@cd.ef'))
        self.assertFalse(self.db.verify_otp('al@cd.ef', code, SECRET))

    def test_email_verification_before_login(self):
        ok, _ = self.db.signup('mariner', 'new@outlook.com', 'StrongPwd2!', QUESTION, 'Answer',
                               require_verification=True)
        self.assertTrue(ok)
        self.assertIsNone(self.db.authenticate('mariner','StrongPwd2!')[0])
        code, error = self.db.begin_email_verification('new@outlook.com', SECRET)
        self.assertIsNone(error)
        self.assertFalse(self.db.verify_email('new@outlook.com', '12345x', SECRET))
        self.assertTrue(self.db.verify_email('new@outlook.com', code, SECRET))
        self.assertFalse(self.db.verify_email('new@outlook.com', code, SECRET))
        self.assertIsNotNone(self.db.authenticate('mariner','StrongPwd2!')[0])
        self.assertEqual(self.db.user('mariner')['email_verified'], 1)

    def test_change_password(self):
        self.assertFalse(self.db.change_password('alex','bad','NewStrongPwd2!')[0])
        self.assertTrue(self.db.change_password('alex','StrongPwd1!','NewStrongPwd2!')[0])

    def test_tokens(self):
        token = issue_token('al@cd.ef', SECRET, version=3)
        self.assertEqual(decode_token(token,SECRET)['ver'],3)
        self.assertIsNone(decode_token(token, 'b'*48))
        expired = issue_token('al@cd.ef',SECRET,lifetime=-1)
        self.assertIsNone(decode_token(expired,SECRET))

    def test_delete(self):
        self.db.delete_user(self.db.user('alex')['id'])
        self.assertIsNone(self.db.user('alex'))


if __name__=='__main__':
    unittest.main()
