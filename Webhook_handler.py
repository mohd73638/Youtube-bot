import os
import hmac
import hashlib
import logging
from typing import Dict, Any, Optional

from github_analyzer import GitHubAnalyzer

logger = logging.getLogger(__name__)

class WebhookHandler:
    def __init__(self):
        self.webhook_secret = os.environ.get("GITHUB_WEBHOOK_SECRET")
        self.github_analyzer = GitHubAnalyzer()

    def is_configured(self) -> bool:
        """Check if webhook is properly configured by ensuring the secret is set."""
        return bool(self.webhook_secret)

    def verify_signature(self, payload: bytes, signature_header: Optional[str]) -> bool:
        """
        Verify GitHub webhook signature from the X-Hub-Signature-256 header.

        Args:
            payload (bytes): The raw request body.
            signature_header (str): The value of the X-Hub-Signature-256 header.

        Returns:
            bool: True if the signature is valid, False otherwise.
        """
        if not self.webhook_secret:
            logger.warning("No webhook secret configured, skipping signature verification")
            return True  # Caution: allow in development only!

        if not signature_header or not signature_header.startswith("sha256="):
            logger.warning("Invalid or missing X-Hub-Signature-256 header")
            return False

        # Extract the actual signature
        signature = signature_header.split("=", 1)[1].strip()

        # Compute HMAC using the shared secret and payload
        mac = hmac.new(
            key=self.webhook_secret.encode("utf-8"),
            msg=payload,
            digestmod=hashlib.sha256
        )
        expected_signature = mac.hexdigest()

        # Use hmac.compare_digest for constant-time comparison
        is_valid = hmac.compare_digest(signature, expected_signature)
        if not is_valid:
            logger.warning("Webhook signature mismatch")

        return is_valid
