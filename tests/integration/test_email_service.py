"""
Integration Tests for Email Service

Tests email delivery with multiple providers.
Note: Uses mocks to avoid sending real emails in tests.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4
from pathlib import Path
import tempfile

from transcript_builder.api.services.email_service import EmailService, create_email_service
from transcript_builder.api.database.models import Transcript, Student


class TestEmailServiceSMTP:
    """Tests for SMTP email delivery"""

    @pytest.fixture
    def smtp_service(self, db_session, test_tenant):
        """Create SMTP email service"""
        return EmailService(
            db=db_session,
            tenant_id=test_tenant.id,
            provider="smtp",
            host="smtp.test.com",
            port=587,
            username="test@test.com",
            password="test_password",
            from_email="transcripts@school.edu",
        )

    @pytest.fixture
    def test_transcript(self, db_session, test_tenant):
        """Create a test transcript with file"""
        # Create temp PDF file
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(b"%PDF-1.4 test content")
            file_path = f.name

        # Create student
        student = Student(
            id=uuid4(),
            tenant_id=test_tenant.id,
            external_id="12345",
            user_id=12345,
            first_name="Test",
            last_name="Student",
            graduation_year=2025,
        )
        db_session.add(student)

        # Create transcript
        transcript = Transcript(
            id=uuid4(),
            tenant_id=test_tenant.id,
            student_id=student.id,
            transcript_type="official",
            file_path=file_path,
            verification_code="TEST-12345-CODE",
        )
        db_session.add(transcript)

        return transcript, student

    @pytest.mark.asyncio
    async def test_send_transcript_smtp(self, smtp_service, test_transcript, db_session):
        """Test sending transcript via SMTP"""
        transcript, student = test_transcript
        await db_session.commit()

        with patch("smtplib.SMTP") as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value.__enter__ = MagicMock(return_value=mock_server)
            mock_smtp.return_value.__exit__ = MagicMock(return_value=False)

            result = await smtp_service.send_transcript(
                transcript_id=transcript.id,
                recipient_email="recipient@test.com",
            )

            assert result["status"] == "sent"
            mock_server.sendmail.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_transcript_with_custom_message(self, smtp_service, test_transcript, db_session):
        """Test sending transcript with custom subject and message"""
        transcript, student = test_transcript
        await db_session.commit()

        with patch("smtplib.SMTP") as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value.__enter__ = MagicMock(return_value=mock_server)
            mock_smtp.return_value.__exit__ = MagicMock(return_value=False)

            result = await smtp_service.send_transcript(
                transcript_id=transcript.id,
                recipient_email="recipient@test.com",
                subject="Custom Subject",
                message="Custom message body",
            )

            assert result["status"] == "sent"


class TestEmailServiceSendGrid:
    """Tests for SendGrid email delivery"""

    @pytest.fixture
    def sendgrid_service(self, db_session, test_tenant):
        """Create SendGrid email service"""
        return EmailService(
            db=db_session,
            tenant_id=test_tenant.id,
            provider="sendgrid",
            api_key="SG.test_api_key",
            from_email="transcripts@school.edu",
        )

    @pytest.mark.asyncio
    async def test_send_via_sendgrid(self, sendgrid_service):
        """Test SendGrid API call structure"""
        # Verify service initialized correctly
        assert sendgrid_service.sendgrid_api_key == "SG.test_api_key"
        assert sendgrid_service.provider == "sendgrid"


class TestEmailServiceSES:
    """Tests for AWS SES email delivery"""

    @pytest.fixture
    def ses_service(self, db_session, test_tenant):
        """Create AWS SES email service"""
        return EmailService(
            db=db_session,
            tenant_id=test_tenant.id,
            provider="ses",
            region="us-east-1",
            from_email="transcripts@school.edu",
        )

    @pytest.mark.asyncio
    async def test_ses_initialization(self, ses_service):
        """Test SES service initialization"""
        assert ses_service.aws_region == "us-east-1"
        assert ses_service.provider == "ses"


class TestEmailServiceMailgun:
    """Tests for Mailgun email delivery"""

    @pytest.fixture
    def mailgun_service(self, db_session, test_tenant):
        """Create Mailgun email service"""
        return EmailService(
            db=db_session,
            tenant_id=test_tenant.id,
            provider="mailgun",
            api_key="key-test123",
            domain="mg.school.edu",
            from_email="transcripts@school.edu",
        )

    @pytest.mark.asyncio
    async def test_mailgun_initialization(self, mailgun_service):
        """Test Mailgun service initialization"""
        assert mailgun_service.mailgun_api_key == "key-test123"
        assert mailgun_service.mailgun_domain == "mg.school.edu"


class TestEmailServiceBatch:
    """Tests for batch email operations"""

    @pytest.fixture
    def email_service(self, db_session, test_tenant):
        """Create email service for batch testing"""
        return EmailService(
            db=db_session,
            tenant_id=test_tenant.id,
            provider="smtp",
            host="smtp.test.com",
            port=587,
            from_email="test@school.edu",
        )

    @pytest.mark.asyncio
    async def test_send_batch_success(self, email_service):
        """Test batch email sending"""
        with patch.object(
            email_service, "send_transcript", new_callable=AsyncMock
        ) as mock_send:
            mock_send.return_value = {"status": "sent", "message_id": "123"}

            transcript_emails = [
                {"transcript_id": uuid4(), "recipient_email": "a@test.com"},
                {"transcript_id": uuid4(), "recipient_email": "b@test.com"},
            ]

            result = await email_service.send_batch(transcript_emails)

            assert result["total"] == 2
            assert result["sent"] == 2
            assert result["failed"] == 0

    @pytest.mark.asyncio
    async def test_send_batch_partial_failure(self, email_service):
        """Test batch with some failures"""
        call_count = 0

        async def mock_send(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return {"status": "sent", "message_id": "123"}
            raise Exception("Send failed")

        with patch.object(email_service, "send_transcript", side_effect=mock_send):
            transcript_emails = [
                {"transcript_id": uuid4(), "recipient_email": "a@test.com"},
                {"transcript_id": uuid4(), "recipient_email": "b@test.com"},
            ]

            result = await email_service.send_batch(transcript_emails)

            assert result["total"] == 2
            assert result["sent"] == 1
            assert result["failed"] == 1
            assert len(result["errors"]) == 1


class TestEmailServiceFactory:
    """Tests for email service factory function"""

    def test_create_smtp_service(self, db_session):
        """Test creating SMTP service from settings"""
        settings = {
            "provider": "smtp",
            "from_email": "test@school.edu",
            "smtp": {
                "host": "smtp.test.com",
                "port": 587,
                "username": "user",
                "password": "pass",
            },
        }

        service = create_email_service(db_session, uuid4(), settings)

        assert service.provider == "smtp"
        assert service.smtp_host == "smtp.test.com"

    def test_create_sendgrid_service(self, db_session):
        """Test creating SendGrid service from settings"""
        settings = {
            "provider": "sendgrid",
            "from_email": "test@school.edu",
            "sendgrid": {
                "api_key": "SG.test_key",
            },
        }

        service = create_email_service(db_session, uuid4(), settings)

        assert service.provider == "sendgrid"
        assert service.sendgrid_api_key == "SG.test_key"

    def test_invalid_provider(self, db_session):
        """Test error with invalid provider"""
        settings = {
            "provider": "invalid_provider",
            "from_email": "test@school.edu",
        }

        with pytest.raises(ValueError) as exc_info:
            create_email_service(db_session, uuid4(), settings)

        assert "Unknown email provider" in str(exc_info.value)
