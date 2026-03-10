import unittest
from unittest.mock import Mock, patch

import Main


class PasswordResetRouteTests(unittest.TestCase):
    def setUp(self):
        Main.app.config.update(TESTING=True, SECRET_KEY="test-secret")
        self.client = Main.app.test_client()

    def test_password_reset_email_is_configured_with_emailjs(self):
        with patch.dict(
            Main.os.environ,
            {
                "EMAILJS_SERVICE_ID": "service_reset",
                "EMAILJS_PASSWORD_RESET_TEMPLATE_ID": "template_reset",
                "EMAILJS_PUBLIC_KEY": "public-key",
                "EMAILJS_PRIVATE_KEY": "private-key",
            },
            clear=True,
        ):
            self.assertTrue(Main.password_reset_email_is_configured())

    def test_send_password_reset_email_prefers_emailjs_when_configured(self):
        with patch.dict(
            Main.os.environ,
            {
                "EMAILJS_SERVICE_ID": "service_reset",
                "EMAILJS_PASSWORD_RESET_TEMPLATE_ID": "template_reset",
                "EMAILJS_PUBLIC_KEY": "public-key",
                "EMAILJS_PRIVATE_KEY": "private-key",
            },
            clear=True,
        ), patch.object(Main, "send_password_reset_email_via_emailjs", return_value=True) as send_emailjs:
            email_sent = Main.send_password_reset_email(
                "jane@example.com",
                "Doe, Jane",
                "https://smartq.example/reset-password/token-123",
            )

        self.assertTrue(email_sent)
        send_emailjs.assert_called_once_with(
            "jane@example.com",
            "Doe, Jane",
            "https://smartq.example/reset-password/token-123",
        )

    def test_format_emailjs_password_reset_error_mentions_backend_security_for_1010(self):
        error_message = Main.format_emailjs_password_reset_error(403, "error code: 1010")

        self.assertIn("HTTP 403", error_message)
        self.assertIn("error code: 1010", error_message)
        self.assertIn("non-browser/server-side API requests", error_message)

    def test_forgot_password_known_email_sends_reset_email(self):
        fake_conn = Mock()

        with patch.object(Main, "password_reset_email_is_configured", return_value=True), \
             patch.object(Main, "get_db_connection", return_value=fake_conn), \
             patch.object(Main, "ensure_password_reset_tokens_table"), \
             patch.object(Main, "find_user_by_email", return_value={
                 "id": 7,
                 "fullname": "Doe, Jane",
                 "email": "jane@example.com",
             }), \
             patch.object(Main, "create_password_reset_token", return_value=("token-123", None)) as create_token, \
             patch.object(Main, "get_public_base_url", return_value="https://smartq.example"), \
             patch.object(Main, "send_password_reset_email", return_value=True) as send_email:
            response = self.client.post(
                "/forgot-password",
                data={"email": "jane@example.com"},
                follow_redirects=False,
            )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers["Location"].endswith("/login"))
        create_token.assert_called_once_with(fake_conn, 7)
        send_email.assert_called_once_with(
            "jane@example.com",
            "Doe, Jane",
            "https://smartq.example/reset-password/token-123",
        )
        fake_conn.close.assert_called_once()

    def test_forgot_password_unknown_email_still_shows_generic_success(self):
        fake_conn = Mock()

        with patch.object(Main, "password_reset_email_is_configured", return_value=True), \
             patch.object(Main, "get_db_connection", return_value=fake_conn), \
             patch.object(Main, "ensure_password_reset_tokens_table"), \
             patch.object(Main, "find_user_by_email", return_value=None):
            response = self.client.post(
                "/forgot-password",
                data={"email": "missing@example.com"},
                follow_redirects=True,
            )

        self.assertEqual(response.status_code, 200)
        self.assertIn(
            b"If an account exists for that email, a password reset link has been sent.",
            response.data,
        )
        fake_conn.close.assert_called_once()

    def test_reset_password_invalid_token_redirects_to_forgot_password(self):
        fake_conn = Mock()

        with patch.object(Main, "get_db_connection", return_value=fake_conn), \
             patch.object(Main, "ensure_password_reset_tokens_table"), \
             patch.object(Main, "get_password_reset_record", return_value=None):
            response = self.client.get("/reset-password/bad-token", follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn(
            b"This password reset link is invalid or has expired.",
            response.data,
        )
        fake_conn.close.assert_called_once()

    def test_reset_password_success_updates_password_and_invalidates_tokens(self):
        fake_conn = Mock()

        with patch.object(Main, "get_db_connection", return_value=fake_conn), \
             patch.object(Main, "ensure_password_reset_tokens_table"), \
             patch.object(Main, "get_password_reset_record", return_value={"user_id": 9}), \
             patch.object(Main, "set_user_password") as set_password, \
             patch.object(Main, "invalidate_password_reset_tokens") as invalidate_tokens:
            response = self.client.post(
                "/reset-password/good-token",
                data={"password": "new-pass-123", "confirm_password": "new-pass-123"},
                follow_redirects=False,
            )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers["Location"].endswith("/login"))
        self.assertEqual(set_password.call_args.args[0], fake_conn)
        self.assertEqual(set_password.call_args.args[1], 9)
        self.assertTrue(Main.check_password_hash(set_password.call_args.args[2], "new-pass-123"))
        invalidate_tokens.assert_called_once_with(fake_conn, 9)
        fake_conn.commit.assert_called_once()
        fake_conn.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()
