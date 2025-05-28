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
            return True  # Allow in development/testing, but not recommended for prod

        if not signature_header:
            logger.warning("No signature provided in webhook")
            return False

        try:
            # Header format: "sha256=<signature>"
            algo, received_sig = signature_header.split("=", 1)
            if algo != "sha256":
                logger.error(f"Unsupported signature algorithm: {algo}")
                return False
            expected_sig = hmac.new(
                self.webhook_secret.encode(), payload, hashlib.sha256
            ).hexdigest()
            is_valid = hmac.compare_digest(received_sig, expected_sig)
            if not is_valid:
                logger.warning("Webhook signature does not match expected signature")
            return is_valid
        except Exception as e:
            logger.error(f"Error verifying webhook signature: {str(e)}")
            return False

    def handle_event(self, event_type: str, payload: Dict[str, Any], delivery_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Handle different types of GitHub webhook events.

        Args:
            event_type (str): The GitHub event type (from X-GitHub-Event header).
            payload (Dict[str, Any]): The parsed JSON webhook payload.
            delivery_id (str, optional): The delivery ID from X-GitHub-Delivery header for traceability.

        Returns:
            Dict[str, Any]: The processing result.
        """
        try:
            log_prefix = f"[delivery_id={delivery_id}] " if delivery_id else ""
            logger.info(f"{log_prefix}Processing GitHub webhook event: {event_type}")

            if event_type == "push":
                return self._handle_push_event(payload, delivery_id)
            elif event_type == "pull_request":
                return self._handle_pull_request_event(payload, delivery_id)
            elif event_type == "issues":
                return self._handle_issues_event(payload, delivery_id)
            elif event_type == "repository":
                return self._handle_repository_event(payload, delivery_id)
            elif event_type == "ping":
                return self._handle_ping_event(payload, delivery_id)
            else:
                logger.info(f"{log_prefix}Unhandled event type: {event_type}")
                return {
                    "status": "ignored",
                    "message": f"Event type {event_type} not handled"
                }
        except Exception as e:
            logger.error(f"Error handling webhook event {event_type}: {str(e)}")
            return {
                "status": "error",
                "message": str(e)
            }

    def _handle_push_event(self, payload: Dict[str, Any], delivery_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Handle push events from GitHub.

        Args:
            payload (Dict[str, Any]): The webhook payload.
            delivery_id (str, optional): The delivery ID for traceability.

        Returns:
            Dict[str, Any]: The processing result.
        """
        try:
            repository = payload.get("repository", {})
            repo_name = repository.get("full_name", "Unknown")
            commits = payload.get("commits", [])
            branch = payload.get("ref", "").replace("refs/heads/", "")
            pusher = payload.get("pusher", {}).get("name", "Unknown")
            log_prefix = f"[delivery_id={delivery_id}] " if delivery_id else ""

            logger.info(
                f"{log_prefix}Push event for {repo_name} on branch {branch} by {pusher} with {len(commits)} commits"
            )

            commit_messages = [commit.get("message", "") for commit in commits]
            result = {
                "status": "processed",
                "event_type": "push",
                "repository": repo_name,
                "branch": branch,
                "commits_count": len(commits),
                "pusher": pusher,
                "commit_messages": commit_messages,
                "message": f"Push event processed for {repo_name} on {branch} by {pusher}"
            }

            return result

        except Exception as e:
            logger.error(f"Error handling push event: {str(e)}")
            return {"status": "error", "message": str(e)}

    def _handle_pull_request_event(self, payload: Dict[str, Any], delivery_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Handle pull request events from GitHub.

        Args:
            payload (Dict[str, Any]): The webhook payload.
            delivery_id (str, optional): The delivery ID for traceability.

        Returns:
            Dict[str, Any]: The processing result.
        """
        try:
            pr = payload.get("pull_request", {})
            action = payload.get("action", "")
            repo_name = payload.get("repository", {}).get("full_name", "Unknown")
            pr_number = pr.get("number", "Unknown")
            pr_title = pr.get("title", "")
            pr_user = pr.get("user", {}).get("login", "Unknown")
            log_prefix = f"[delivery_id={delivery_id}] " if delivery_id else ""

            logger.info(
                f"{log_prefix}Pull request {action} on {repo_name} PR#{pr_number}: '{pr_title}' by {pr_user}"
            )
            result = {
                "status": "processed",
                "event_type": "pull_request",
                "repository": repo_name,
                "pr_number": pr_number,
                "pr_title": pr_title,
                "pr_user": pr_user,
                "action": action,
                "message": f"Pull request event processed: {action} PR#{pr_number} by {pr_user}"
            }
            return result
        except Exception as e:
            logger.error(f"Error handling pull request event: {str(e)}")
            return {"status": "error", "message": str(e)}

    def _handle_issues_event(self, payload: Dict[str, Any], delivery_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Handle issues events from GitHub.

        Args:
            payload (Dict[str, Any]): The webhook payload.
            delivery_id (str, optional): The delivery ID for traceability.

        Returns:
            Dict[str, Any]: The processing result.
        """
        try:
            issue = payload.get("issue", {})
            action = payload.get("action", "")
            repo_name = payload.get("repository", {}).get("full_name", "Unknown")
            issue_number = issue.get("number", "Unknown")
            issue_title = issue.get("title", "")
            issue_user = issue.get("user", {}).get("login", "Unknown")
            log_prefix = f"[delivery_id={delivery_id}] " if delivery_id else ""

            logger.info(
                f"{log_prefix}Issue {action} on {repo_name} Issue#{issue_number}: '{issue_title}' by {issue_user}"
            )
            result = {
                "status": "processed",
                "event_type": "issues",
                "repository": repo_name,
                "issue_number": issue_number,
                "issue_title": issue_title,
                "issue_user": issue_user,
                "action": action,
                "message": f"Issues event processed: {action} Issue#{issue_number} by {issue_user}"
            }
            return result
        except Exception as e:
            logger.error(f"Error handling issues event: {str(e)}")
            return {"status": "error", "message": str(e)}

    def _handle_repository_event(self, payload: Dict[str, Any], delivery_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Handle repository events from GitHub.

        Args:
            payload (Dict[str, Any]): The webhook payload.
            delivery_id (str, optional): The delivery ID for traceability.

        Returns:
            Dict[str, Any]: The processing result.
        """
        try:
            action = payload.get("action", "")
            repo_name = payload.get("repository", {}).get("full_name", "Unknown")
            log_prefix = f"[delivery_id={delivery_id}] " if delivery_id else ""

            logger.info(
                f"{log_prefix}Repository event {action} on {repo_name}"
            )
            result = {
                "status": "processed",
                "event_type": "repository",
                "repository": repo_name,
                "action": action,
                "message": f"Repository event processed: {action} on {repo_name}"
            }
            return result
        except Exception as e:
            logger.error(f"Error handling repository event: {str(e)}")
            return {"status": "error", "message": str(e)}

    def _handle_ping_event(self, payload: Dict[str, Any], delivery_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Handle ping events from GitHub.

        Args:
            payload (Dict[str, Any]): The webhook payload.
            delivery_id (str, optional): The delivery ID for traceability.

        Returns:
            Dict[str, Any]: The processing result.
        """
        try:
            repo_name = payload.get("repository", {}).get("full_name", "Unknown")
            zen = payload.get("zen", "")
            log_prefix = f"[delivery_id={delivery_id}] " if delivery_id else ""

            logger.info(
                f"{log_prefix}Ping event received from {repo_name}: '{zen}'"
            )
            result = {
                "status": "processed",
                "event_type": "ping",
                "repository": repo_name,
                "zen": zen,
                "message": f"Ping event processed: {zen}"
            }
            return result
        except Exception as e:
            logger.error(f"Error handling ping event: {str(e)}")
            return {"status": "error", "message": str(e)}
