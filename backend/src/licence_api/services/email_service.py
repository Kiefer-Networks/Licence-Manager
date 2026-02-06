"""Email service for SMTP configuration and sending emails."""

import asyncio
import logging
import re
import smtplib
import ssl
from concurrent.futures import ThreadPoolExecutor
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate, make_msgid
from functools import partial
from html import escape as html_escape
from typing import Any

from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession

from licence_api.repositories.settings_repository import SettingsRepository
from licence_api.security.encryption import get_encryption_service

logger = logging.getLogger(__name__)

# Thread pool for non-blocking SMTP operations
_smtp_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="smtp")

SMTP_CONFIG_KEY = "smtp_config"
SYSTEM_SETTINGS_KEY = "system_settings"
DEFAULT_SYSTEM_NAME = "License Management System"


class SmtpConfig(BaseModel):
    """SMTP configuration model."""

    host: str = Field(min_length=1, max_length=255)
    port: int = Field(ge=1, le=65535)
    username: str = Field(min_length=1, max_length=255)
    password_encrypted: bytes | None = None  # Only set when stored
    from_email: EmailStr
    from_name: str = Field(default="License Management System", max_length=255)
    use_tls: bool = True


class SmtpConfigRequest(BaseModel):
    """SMTP configuration request (with plaintext password)."""

    host: str = Field(min_length=1, max_length=255)
    port: int = Field(ge=1, le=65535, default=587)
    username: str = Field(min_length=1, max_length=255)
    password: str | None = Field(default=None, min_length=1, max_length=255)
    from_email: EmailStr
    from_name: str = Field(default="License Management System", max_length=255)
    use_tls: bool = True


class SmtpConfigResponse(BaseModel):
    """SMTP configuration response (without password)."""

    host: str
    port: int
    username: str
    from_email: str
    from_name: str
    use_tls: bool
    is_configured: bool = True


class EmailService:
    """Service for sending emails via SMTP."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize email service with database session."""
        self.session = session
        self.settings_repo = SettingsRepository(session)
        self.encryption = get_encryption_service()

    async def get_system_settings(self) -> tuple[str, str | None]:
        """Get the configured system name and URL.

        Returns:
            Tuple of (system_name, system_url)
        """
        settings = await self.settings_repo.get(SYSTEM_SETTINGS_KEY)
        if settings:
            return settings.get("name", DEFAULT_SYSTEM_NAME), settings.get("url")
        return DEFAULT_SYSTEM_NAME, None

    async def get_smtp_config(self) -> SmtpConfig | None:
        """Get and decrypt SMTP configuration.

        Returns:
            SmtpConfig if configured, None otherwise
        """
        config_data = await self.settings_repo.get(SMTP_CONFIG_KEY)
        if not config_data:
            return None

        try:
            # Decrypt password if present
            password_encrypted = config_data.get("password_encrypted")
            if password_encrypted:
                # Convert hex string back to bytes if needed
                if isinstance(password_encrypted, str):
                    password_encrypted = bytes.fromhex(password_encrypted)

            return SmtpConfig(
                host=config_data["host"],
                port=config_data["port"],
                username=config_data["username"],
                password_encrypted=password_encrypted,
                from_email=config_data["from_email"],
                from_name=config_data.get("from_name", "License Management System"),
                use_tls=config_data.get("use_tls", True),
            )
        except (KeyError, ValueError) as e:
            logger.error(f"Failed to parse SMTP config: {e}")
            return None

    async def get_smtp_config_response(self) -> SmtpConfigResponse | None:
        """Get SMTP configuration for API response (without password).

        Returns:
            SmtpConfigResponse if configured, None otherwise
        """
        config = await self.get_smtp_config()
        if not config:
            return None

        return SmtpConfigResponse(
            host=config.host,
            port=config.port,
            username=config.username,
            from_email=config.from_email,
            from_name=config.from_name,
            use_tls=config.use_tls,
            is_configured=True,
        )

    async def is_configured(self) -> bool:
        """Check if SMTP is configured.

        Returns:
            True if SMTP is configured
        """
        config = await self.settings_repo.get(SMTP_CONFIG_KEY)
        return config is not None

    async def save_smtp_config(self, request: SmtpConfigRequest) -> None:
        """Save SMTP configuration with encrypted password.

        Args:
            request: SMTP configuration request
        """
        # Get existing config to preserve password if not provided
        existing_config = await self.settings_repo.get(SMTP_CONFIG_KEY)
        password_encrypted: bytes | None = None

        if request.password:
            # Encrypt new password
            password_encrypted = self.encryption.encrypt_string(request.password)
        elif existing_config and existing_config.get("password_encrypted"):
            # Keep existing encrypted password
            existing_pwd = existing_config["password_encrypted"]
            if isinstance(existing_pwd, str):
                password_encrypted = bytes.fromhex(existing_pwd)
            else:
                password_encrypted = existing_pwd

        config_data: dict[str, Any] = {
            "host": request.host,
            "port": request.port,
            "username": request.username,
            "from_email": request.from_email,
            "from_name": request.from_name,
            "use_tls": request.use_tls,
        }

        if password_encrypted:
            # Store as hex string for JSON serialization
            config_data["password_encrypted"] = password_encrypted.hex()

        await self.settings_repo.set(SMTP_CONFIG_KEY, config_data)
        await self.session.commit()

    async def delete_smtp_config(self) -> bool:
        """Delete SMTP configuration.

        Returns:
            True if deleted, False if not found
        """
        result = await self.settings_repo.delete(SMTP_CONFIG_KEY)
        await self.session.commit()
        return result

    def _get_smtp_connection(
        self, config: SmtpConfig, password: str
    ) -> smtplib.SMTP | smtplib.SMTP_SSL:
        """Create SMTP connection.

        Args:
            config: SMTP configuration
            password: Decrypted password

        Returns:
            SMTP connection
        """
        context = ssl.create_default_context()

        if config.use_tls:
            # Use STARTTLS (port 587 typically)
            smtp = smtplib.SMTP(config.host, config.port, timeout=30)
            # EHLO before STARTTLS for proper server greeting
            smtp.ehlo()
            smtp.starttls(context=context)
            # EHLO again after STARTTLS as required by RFC 3207
            smtp.ehlo()
        else:
            # Direct SSL connection (port 465 typically)
            smtp = smtplib.SMTP_SSL(config.host, config.port, timeout=30, context=context)
            smtp.ehlo()

        smtp.login(config.username, password)
        return smtp

    def _create_message(
        self,
        config: SmtpConfig,
        to_email: str,
        subject: str,
        html_body: str,
        plain_body: str | None = None,
    ) -> MIMEMultipart:
        """Create email message with proper headers.

        Args:
            config: SMTP configuration
            to_email: Recipient email address
            subject: Email subject
            html_body: HTML email body
            plain_body: Plain text body (optional)

        Returns:
            Constructed email message
        """
        msg = MIMEMultipart("alternative")

        # Standard headers
        msg["Subject"] = subject
        msg["From"] = f"{config.from_name} <{config.from_email}>"
        msg["To"] = to_email

        # Additional headers for better deliverability
        msg["Message-ID"] = make_msgid(domain=config.from_email.split("@")[1])
        msg["Date"] = formatdate(localtime=True)
        msg["X-Mailer"] = "License Management System"

        # Add plain text part
        if plain_body:
            msg.attach(MIMEText(plain_body, "plain", "utf-8"))
        else:
            # Generate plain text from HTML (basic strip)
            plain = re.sub(r"<[^>]+>", "", html_body)
            plain = re.sub(r"\s+", " ", plain).strip()
            msg.attach(MIMEText(plain, "plain", "utf-8"))

        # Add HTML part
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        return msg

    def _send_email_sync(
        self,
        config: SmtpConfig,
        password: str,
        to_email: str,
        msg: MIMEMultipart,
    ) -> None:
        """Synchronous email sending (runs in thread pool).

        Args:
            config: SMTP configuration
            password: Decrypted password
            to_email: Recipient email address
            msg: Constructed email message
        """
        smtp = None
        try:
            smtp = self._get_smtp_connection(config, password)
            smtp.sendmail(config.from_email, to_email, msg.as_string())
        finally:
            if smtp:
                try:
                    smtp.quit()
                except Exception:
                    pass

    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        plain_body: str | None = None,
    ) -> bool:
        """Send an email via SMTP (non-blocking).

        Uses a thread pool executor to avoid blocking the async event loop.

        Args:
            to_email: Recipient email address
            subject: Email subject
            html_body: HTML email body
            plain_body: Plain text body (optional, auto-generated if not provided)

        Returns:
            True if sent successfully, False otherwise
        """
        config = await self.get_smtp_config()
        if not config or not config.password_encrypted:
            logger.warning("SMTP not configured, cannot send email")
            return False

        try:
            # Decrypt password
            password = self.encryption.decrypt_string(config.password_encrypted)

            # Create message with proper headers
            msg = self._create_message(config, to_email, subject, html_body, plain_body)

            # Run synchronous SMTP in thread pool to avoid blocking
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(
                _smtp_executor,
                partial(self._send_email_sync, config, password, to_email, msg),
            )

            logger.info(f"Email sent successfully to {to_email}")
            return True

        except smtplib.SMTPException as e:
            logger.error(f"SMTP error sending email to {to_email}: {e}")
            return False
        except Exception as e:
            logger.error(f"Error sending email to {to_email}: {e}")
            return False

    async def send_test_email(self, to_email: str) -> tuple[bool, str]:
        """Send a test email to verify SMTP configuration (non-blocking).

        Args:
            to_email: Recipient email address

        Returns:
            Tuple of (success, message)
        """
        config = await self.get_smtp_config()
        if not config:
            return False, "SMTP not configured"

        if not config.password_encrypted:
            return False, "SMTP password not configured"

        try:
            password = self.encryption.decrypt_string(config.password_encrypted)
            system_name, system_url = await self.get_system_settings()

            url_html = ""
            url_text = ""
            if system_url:
                url_html = f'<p>System URL: <a href="{system_url}">{system_url}</a></p>'
                url_text = f"\nSystem URL: {system_url}"

            html_body = f"""
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <h2>Test Email</h2>
                <p>This is a test email from {system_name}.</p>
                <p>If you received this email, your SMTP configuration is working correctly.</p>
                {url_html}
            </body>
            </html>
            """
            plain_body = (
                "Test Email\n\n"
                f"This is a test email from {system_name}.\n"
                "If you received this email, your SMTP configuration is working correctly."
                f"{url_text}"
            )

            # Create message with proper headers
            msg = self._create_message(
                config,
                to_email,
                f"{system_name} - Test Email",
                html_body,
                plain_body,
            )

            # Run synchronous SMTP in thread pool to avoid blocking
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(
                _smtp_executor,
                partial(self._send_email_sync, config, password, to_email, msg),
            )

            return True, "Test email sent successfully"

        except smtplib.SMTPAuthenticationError:
            return False, "Authentication failed. Check username and password."
        except smtplib.SMTPConnectError:
            return False, f"Could not connect to SMTP server at {config.host}:{config.port}"
        except smtplib.SMTPRecipientsRefused:
            return False, f"Recipient address rejected: {to_email}"
        except TimeoutError:
            return False, "Connection timed out. Check host and port."
        except Exception as e:
            logger.error(f"SMTP test failed: {e}")
            return False, f"Connection failed: {str(e)}"

    def _get_email_translations(self, language: str, system_name: str) -> dict[str, str]:
        """Get email translations for the specified language.

        Args:
            language: ISO 639-1 language code (e.g., 'en', 'de')
            system_name: The configured system name

        Returns:
            Dictionary with translation strings
        """
        # Normalize language code (e.g., 'de-DE' -> 'de')
        lang = language.split("-")[0].lower() if language else "en"

        translations = {
            "en": {
                # New user email
                "new_user_subject": f"{system_name} - Your Account Has Been Created",
                "new_user_heading": f"Welcome to {system_name}",
                "new_user_greeting": "Hello",
                "new_user_intro": "Your account has been created. Please use the following credentials to log in:",
                "email_label": "Email",
                "temp_password_label": "Temporary Password",
                "new_password_label": "New Temporary Password",
                "new_user_warning": "You will be required to change this password when you first log in.",
                "security_notice": "For security reasons, please do not share this email with anyone.",
                "footer": f"This is an automated message from {system_name}.",
                "important": "Important",
                "login_link": "Log in here",
                # Password reset email
                "reset_subject": f"{system_name} - Password Reset",
                "reset_heading": "Password Reset",
                "reset_intro": "Your password has been reset by an administrator. Please use the following credentials to log in:",
                "reset_warning": "You will be required to change this password when you next log in.",
                "reset_not_requested": "If you did not request this password reset, please contact your administrator immediately.",
            },
            "de": {
                # New user email
                "new_user_subject": f"{system_name} - Ihr Konto wurde erstellt",
                "new_user_heading": f"Willkommen bei {system_name}",
                "new_user_greeting": "Hallo",
                "new_user_intro": "Ihr Konto wurde erstellt. Bitte verwenden Sie die folgenden Anmeldedaten:",
                "email_label": "E-Mail",
                "temp_password_label": "Temporäres Passwort",
                "new_password_label": "Neues temporäres Passwort",
                "new_user_warning": "Sie müssen dieses Passwort bei der ersten Anmeldung ändern.",
                "security_notice": "Aus Sicherheitsgründen teilen Sie diese E-Mail bitte nicht mit anderen.",
                "footer": f"Dies ist eine automatische Nachricht von {system_name}.",
                "important": "Wichtig",
                "login_link": "Hier anmelden",
                # Password reset email
                "reset_subject": f"{system_name} - Passwort zurückgesetzt",
                "reset_heading": "Passwort zurückgesetzt",
                "reset_intro": "Ihr Passwort wurde von einem Administrator zurückgesetzt. Bitte verwenden Sie die folgenden Anmeldedaten:",
                "reset_warning": "Sie müssen dieses Passwort bei der nächsten Anmeldung ändern.",
                "reset_not_requested": "Falls Sie dieses Zurücksetzen nicht angefordert haben, kontaktieren Sie bitte umgehend Ihren Administrator.",
            },
        }

        return translations.get(lang, translations["en"])

    async def send_password_email(
        self,
        to_email: str,
        user_name: str | None,
        password: str,
        is_new_user: bool = True,
        language: str = "en",
    ) -> bool:
        """Send password to user via email in the specified language.

        Args:
            to_email: User's email address
            user_name: User's name (optional)
            password: The temporary password
            is_new_user: True for new user, False for password reset
            language: ISO 639-1 language code (e.g., 'en', 'de')

        Returns:
            True if sent successfully, False otherwise
        """
        # Get system settings and translations for the user's language
        system_name, system_url = await self.get_system_settings()
        t = self._get_email_translations(language, system_name)

        # Escape user-provided data for HTML to prevent XSS
        name_display = html_escape(user_name or to_email)
        safe_email = html_escape(to_email)
        safe_password = html_escape(password)

        # Build login link if URL is configured
        login_link_html = ""
        login_link_text = ""
        if system_url:
            login_link_html = f'<p style="margin-top: 16px;"><a href="{system_url}" style="display: inline-block; background-color: #2563eb; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: 500;">{t["login_link"]}</a></p>'
            login_link_text = f"\n{t['login_link']}: {system_url}"

        if is_new_user:
            subject = t["new_user_subject"]
            html_body = f"""
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto;">
                <h2 style="color: #2563eb;">{t["new_user_heading"]}</h2>
                <p>{t["new_user_greeting"]} {name_display},</p>
                <p>{t["new_user_intro"]}</p>
                <div style="background-color: #f3f4f6; padding: 16px; border-radius: 8px; margin: 20px 0;">
                    <p style="margin: 0;"><strong>{t["email_label"]}:</strong> {safe_email}</p>
                    <p style="margin: 8px 0 0 0;"><strong>{t["temp_password_label"]}:</strong></p>
                    <p style="font-family: monospace; font-size: 18px; background-color: #fff; padding: 12px; border-radius: 4px; margin: 8px 0;">{safe_password}</p>
                </div>
                {login_link_html}
                <p style="color: #dc2626;"><strong>{t["important"]}:</strong> {t["new_user_warning"]}</p>
                <p>{t["security_notice"]}</p>
                <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 24px 0;">
                <p style="color: #6b7280; font-size: 12px;">{t["footer"]}</p>
            </body>
            </html>
            """
            plain_body = f"""{t["new_user_heading"]}

{t["new_user_greeting"]} {user_name or to_email},

{t["new_user_intro"]}

{t["email_label"]}: {to_email}
{t["temp_password_label"]}: {password}
{login_link_text}

{t["important"].upper()}: {t["new_user_warning"]}

{t["security_notice"]}

---
{t["footer"]}"""
        else:
            subject = t["reset_subject"]
            html_body = f"""
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto;">
                <h2 style="color: #2563eb;">{t["reset_heading"]}</h2>
                <p>{t["new_user_greeting"]} {name_display},</p>
                <p>{t["reset_intro"]}</p>
                <div style="background-color: #f3f4f6; padding: 16px; border-radius: 8px; margin: 20px 0;">
                    <p style="margin: 0;"><strong>{t["email_label"]}:</strong> {safe_email}</p>
                    <p style="margin: 8px 0 0 0;"><strong>{t["new_password_label"]}:</strong></p>
                    <p style="font-family: monospace; font-size: 18px; background-color: #fff; padding: 12px; border-radius: 4px; margin: 8px 0;">{safe_password}</p>
                </div>
                {login_link_html}
                <p style="color: #dc2626;"><strong>{t["important"]}:</strong> {t["reset_warning"]}</p>
                <p>{t["reset_not_requested"]}</p>
                <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 24px 0;">
                <p style="color: #6b7280; font-size: 12px;">{t["footer"]}</p>
            </body>
            </html>
            """
            plain_body = f"""{t["reset_heading"]}

{t["new_user_greeting"]} {user_name or to_email},

{t["reset_intro"]}

{t["email_label"]}: {to_email}
{t["new_password_label"]}: {password}
{login_link_text}

{t["important"].upper()}: {t["reset_warning"]}

{t["reset_not_requested"]}

---
{t["footer"]}"""

        return await self.send_email(to_email, subject, html_body, plain_body)
