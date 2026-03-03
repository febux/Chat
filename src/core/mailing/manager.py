"""
Email manager using FastAPI and FastAPI Mail.

This module provides a simple email manager using FastAPI and FastAPI Mail. It supports sending emails with attachments, templates, and custom headers.
"""

import asyncio
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import BackgroundTasks, HTTPException
from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType
from fastapi_mail.email_utils import DefaultChecker
from pydantic import EmailStr, RedisDsn, SecretStr

from src.core.logger.logger_factory import logger_bind

logger = logger_bind("EmailManager")


class EmailManager:
    """
    Email manager using FastAPI and FastAPI Mail.
    """

    def __init__(
        self,
        username: str,
        password: SecretStr,
        mail_from: EmailStr,
        server: str,
        port: int = 587,
        use_tls: bool = True,
        use_ssl: bool = False,
        from_name: str | None = None,
        template_folder: str | None = None,
        *,
        redis_url: Optional[RedisDsn] = None,
    ):
        """
        Initialize the email manager.

        :param username: The email username.
        :param password: The email password.
        :param mail_from: The email address to send emails from.
        :param server: The email server address.
        :param port: The email server port.
        :param use_tls: Whether to use TLS for the email connection.
        :param use_ssl: Whether to use SSL for the email connection.
        :param from_name: The name to display in the "From" header.
        :param template_folder: The folder path containing email template files.
        :param redis_url: The Redis connection URL (optional).
        """
        self.config = ConnectionConfig(
            MAIL_USERNAME=username,
            MAIL_PASSWORD=password,
            MAIL_FROM=mail_from,
            MAIL_PORT=port,
            MAIL_SERVER=server,
            MAIL_FROM_NAME=from_name,
            MAIL_STARTTLS=use_tls,
            MAIL_SSL_TLS=use_ssl,
            USE_CREDENTIALS=True,
            VALIDATE_CERTS=True,
            TEMPLATE_FOLDER=Path(template_folder) if template_folder else None,
        )
        self.fm = FastMail(self.config)
        self.redis_url = redis_url

    async def get_checker(self) -> DefaultChecker:
        """
        Initialize the email checker.
        The email checker is used to validate email addresses and block/disposable domains.

        :return: The initialized email checker.
        """
        checker = DefaultChecker()
        if self.redis_url:
            checker = DefaultChecker(
                db_provider="redis",
                redis_host=self.redis_url.host,
                redis_port=self.redis_url.port,
                redis_db=int(
                    self.redis_url.path.split("/")[-1] if self.redis_url.path else 0
                ),  # Redis DB number from URL
                redis_password=self.redis_url.password,
            )
            await checker.init_redis()
        await checker.fetch_temp_email_domains()
        return checker

    async def validate_recipients(
        self, recipients: List[EmailStr], checker: Optional[DefaultChecker] = None
    ) -> List[EmailStr]:
        """
        Validate recipients against the email checker.

        :param recipients: The list of email addresses to validate.
        :param checker: The email checker (optional).
        :return: The list of valid email addresses.
        """
        if not checker:
            checker = await self.get_checker()
        valid = []
        for email in recipients:
            email = str(email)
            # Проверка на блокировку email-адреса
            if await checker.is_blocked_address(email):  # type: ignore[cond-value]
                logger.warning(f"{email} is in email blacklist")
                continue
            # Проверка на блокировку домена
            domain = email.split("@")[-1]
            if await checker.is_blocked_domain(domain):  # type: ignore[cond-value]
                logger.warning(f"Domain {domain} is in domain blacklist")
                continue
            # Проверка на disposable-адрес
            if await checker.is_disposable(domain):  # type: ignore[cond-value]
                logger.warning(f"{email} uses disposable domain")
                continue
            valid.append(email)
        if not valid:
            raise HTTPException(status_code=400, detail="No valid recipients")
        return valid

    async def blacklist_add_email(self, email: str, checker: Optional[DefaultChecker] = None):
        """
        Add an email to the blacklist.

        :param email: The email address to blacklist.
        :param checker: The email checker (optional).
        :return: None
        """
        if not checker:
            checker = await self.get_checker()
        await checker.blacklist_add_email(email)  # type: ignore[return-value]

    async def blacklist_rm_email(self, email: str, checker: Optional[DefaultChecker] = None):
        """
        Remove an email from the blacklist.

        :param email: The email address to remove from the blacklist.
        :param checker: The email checker (optional).
        :return: None
        """
        if not checker:
            checker = await self.get_checker()
        await checker.blacklist_rm_email(email)  # type: ignore[return-value]

    async def blacklist_add_domain(self, domain: str, checker: Optional[DefaultChecker] = None):
        """
        Add a domain to the blacklist.

        :param domain: The domain to blacklist.
        :param checker: The email checker (optional).
        :return: None
        """
        if not checker:
            checker = await self.get_checker()
        await checker.blacklist_add_domain(domain)  # type: ignore[return-value]

    async def blacklist_rm_domain(self, domain: str, checker: Optional[DefaultChecker] = None):
        """
        Remove a domain from the blacklist.

        :param domain: The domain to remove from the blacklist.
        :param checker: The email checker (optional).
        :return: None
        """
        if not checker:
            checker = await self.get_checker()
        await checker.blacklist_rm_domain(domain)  # type: ignore[return-value]

    async def is_disposable(self, domain: str, checker: Optional[DefaultChecker] = None):
        """
        Check if a domain is disposable.

        :param domain: The domain to check.
        :param checker: The email checker (optional).
        :return: True if the domain is disposable, False otherwise.
        """
        if not checker:
            checker = await self.get_checker()
        return await checker.is_disposable(domain)  # type: ignore[return-value]

    async def check_mx(self, email: str, checker: Optional[DefaultChecker] = None) -> bool:
        """
        Check the MX record for a domain.
        :param email: The email address to check.
        :param checker: The email checker (optional).
        :return: True if the MX record is valid, False otherwise.
        """
        if not checker:
            checker = await self.get_checker()
        domain = email.split("@")[-1]
        return await checker.check_mx_record(domain, full_result=True)  # type: ignore[return-value]

    async def send_email(
        self,
        subject: str,
        recipients: List[EmailStr],
        body: str = "",
        subtype: MessageType = MessageType.plain,
        template_name: Optional[str] = None,
        template_body: Optional[Dict[str, Any]] = None,
        background_tasks: Optional[BackgroundTasks] = None,
        attachments=None,
        checker: Optional[DefaultChecker] = None,
    ):
        """
        Send an email.

        :param subject: The email subject.
        :param recipients: The list of email addresses to send the email to.
        :param body: The email body (optional).
        :param subtype: The email subtype (plain or html). Defaults to plain.
        :param template_name: The name of the template to use for rendering the email body (optional).
        :param template_body: The data to use for rendering the email body (optional).
        :param background_tasks: The background tasks instance (optional).
        :param attachments: The list of attachments to include in the email (optional).
        :param checker: The email checker (optional).
        :return: None
        """
        recipients = await self.validate_recipients(recipients, checker)
        message = MessageSchema(
            subject=subject,
            recipients=recipients,
            body=body,
            subtype=MessageType.html if template_name else subtype,
            template_body=template_body,
            attachments=attachments,
        )
        try:
            if template_name:
                if background_tasks:
                    background_tasks.add_task(self.fm.send_message, message, template_name=template_name)
                else:
                    await self.fm.send_message(message, template_name=template_name)
            else:
                if background_tasks:
                    background_tasks.add_task(self.fm.send_message, message)
                else:
                    await self.fm.send_message(message)
            logger.info(f"Email sent to {recipients} with subject '{subject}'")
        except Exception as exc:
            logger.exception(f"Failed to send email: {exc}")
            raise HTTPException(status_code=500, detail="Failed to send email")

    async def send_bulk(
        self,
        subject: str,
        recipients: List[str],
        template_name: str,
        data_list: List[Dict[str, Any]],
        background_tasks: Optional[BackgroundTasks] = None,
        delay: float = 0.0,
        checker: Optional[DefaultChecker] = None,
    ):
        """
        Send an email with a template for a bulk of recipients.

        :param subject: The email subject.
        :param recipients: The list of email addresses to send the email to.
        :param template_name: The name of the template to use for rendering the email body.
        :param data_list: The list of data to use for rendering the email body.
        :param background_tasks: The background tasks instance (optional).
        :param delay: The delay between sending each email (optional).
        :param checker: The email checker (optional).
        :return: None
        """
        if len(recipients) != len(data_list):
            raise ValueError("recipients and data_list lengths must match")

        for i, (recipient, data) in enumerate(zip(recipients, data_list)):
            try:
                valid_recipients = await self.validate_recipients([recipient], checker)
                if not valid_recipients:
                    logger.warning(f"Skipping blacklisted or disposable recipient: {recipient}")
                    continue
                await self.send_email(
                    subject=subject,
                    recipients=valid_recipients,
                    template_name=template_name,
                    template_body=data,
                    background_tasks=background_tasks,
                    checker=checker,
                )
                logger.info(f"Sent bulk email to {recipient}")
                if delay > 0 and i < len(recipients) - 1:
                    await asyncio.sleep(delay)
            except Exception as exc:
                logger.exception(f"Bulk send failed to {recipient}: {exc}")
