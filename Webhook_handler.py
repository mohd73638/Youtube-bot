import os
import hmac
import hashlib
import logging
from typing import Dict, Any, Optional
from github_analyzer import GitHubAnalyzer

logger = logging.getLogger(__name__)

class WebhookHandler:
    def __init__(self):
        self.webhook_secret = os.environ.get( GITHUB_WEBHOOK_SECRET )
        self.github_analyzer = GitHubAnalyzer()
        
    def is_configured(self) -> bool:
        """Check if webhook is properly configured"""
        return bool(self.webhook_secret)
    
    def verify_signature(self, payload: bytes, signature: str) -> bool:
        """Verify GitHub webhook signature"""
        if not self.webhook_secret:
            logger.warning("No webhook secret configured, skipping signature verification")
            return True  # Allow in development/testing
        
        if not signature:
            logger.warning("No signature provided in webhook")
            return False
        
        try:
            # GitHub sends signature as "sha256=<hash>"
            expected_signature = f"sha256={hmac.new(self.webhook_secret.encode(), payload, hashlib.sha256).hexdigest()}"
            return hmac.compare_digest(signature, expected_signature)
        except Exception as e:
            logger.error(f"Error verifying webhook signature: {str(e)}")
            return False
    
    def handle_event(self, event_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle different types of GitHub webhook events"""
        try:
            logger.info(f"Processing GitHub webhook event: {event_type}")
            
            if event_type ==  push :
                return self._handle_push_event(payload)
            elif event_type ==  pull_request :
                return self._handle_pull_request_event(payload)
            elif event_type ==  issues :
                return self._handle_issues_event(payload)
            elif event_type ==  repository :
                return self._handle_repository_event(payload)
            elif event_type ==  ping :
                return self._handle_ping_event(payload)
            else:
                logger.info(f"Unhandled event type: {event_type}")
                return { status :  ignored ,  message : f Event type {event_type} not handled }
                
        except Exception as e:
            logger.error(f"Error handling webhook event {event_type}: {str(e)}")
            return { status :  error ,  message : str(e)}
    
    def _handle_push_event(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle push events"""
        try:
            repository = payload.get( repository , {})
            repo_name = repository.get( full_name ,  Unknown )
            commits = payload.get( commits , [])
            branch = payload.get( ref ,   ).replace( refs/heads/ ,   )
            
            logger.info(f"Push event for {repo_name} on branch {branch} with {len(commits)} commits")
            
            result = {
                 status :  processed ,
                 event_type :  push ,
                 repository : repo_name,
                 branch : branch,
                 commits_count : len(commits),
                 message : f Push event processed for {repo_name} 
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error handling push event:
