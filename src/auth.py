"""Authentication module for Google Ads API supporting OAuth2 and Service Account."""

import os
import json
import logging
from typing import Optional, Dict, Any
from pathlib import Path
from datetime import datetime, timedelta

from google.oauth2.credentials import Credentials
from google.oauth2.service_account import Credentials as ServiceAccountCredentials
from google.auth.transport.requests import Request
from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException
from cachetools import TTLCache
import structlog

logger = structlog.get_logger(__name__)


class AuthenticationError(Exception):
    """Raised when authentication fails."""
    pass


class GoogleAdsAuthManager:
    """Manages Google Ads API authentication with multiple auth methods."""
    
    def __init__(self, config_path: Optional[Path] = None):
        """Initialize the auth manager.
        
        Args:
            config_path: Path to configuration file. If not provided, uses env vars.
        """
        self.config_path = config_path
        self._client_cache: TTLCache = TTLCache(maxsize=100, ttl=3600)
        self._load_config()
        
    def _load_config(self) -> None:
        """Load configuration from file or environment variables."""
        self.config: Dict[str, Any] = {}
        
        # Load from config file if provided
        if self.config_path and self.config_path.exists():
            with open(self.config_path) as f:
                file_config = json.load(f)
                self.config.update(file_config)
        
        # Environment variables override file config
        env_mapping = {
            "GOOGLE_ADS_CLIENT_ID": "client_id",
            "GOOGLE_ADS_CLIENT_SECRET": "client_secret",
            "GOOGLE_ADS_REFRESH_TOKEN": "refresh_token",
            "GOOGLE_ADS_DEVELOPER_TOKEN": "developer_token",
            "GOOGLE_ADS_LOGIN_CUSTOMER_ID": "login_customer_id",
            "GOOGLE_ADS_LINKED_CUSTOMER_ID": "linked_customer_id",
            "GOOGLE_ADS_SERVICE_ACCOUNT_PATH": "service_account_path",
            "GOOGLE_ADS_IMPERSONATED_EMAIL": "impersonated_email",
            "GOOGLE_ADS_USE_PROTO_PLUS": "use_proto_plus",
        }
        
        for env_key, config_key in env_mapping.items():
            if env_value := os.getenv(env_key):
                self.config[config_key] = env_value
                
        # Validate required fields
        if not self.config.get("developer_token"):
            raise AuthenticationError("Developer token is required")
            
    def _get_oauth_credentials(self) -> Credentials:
        """Get OAuth2 credentials, refreshing if necessary."""
        required_fields = ["client_id", "client_secret", "refresh_token"]
        missing = [f for f in required_fields if not self.config.get(f)]
        if missing:
            raise AuthenticationError(f"Missing OAuth credentials: {missing}")
            
        credentials = Credentials(
            token=None,
            refresh_token=self.config["refresh_token"],
            client_id=self.config["client_id"],
            client_secret=self.config["client_secret"],
            token_uri="https://oauth2.googleapis.com/token",
        )
        
        # Refresh the token if needed
        if not credentials.valid:
            try:
                credentials.refresh(Request())
                logger.info("OAuth2 token refreshed successfully")
            except Exception as e:
                logger.error(f"Failed to refresh OAuth2 token: {e}")
                raise AuthenticationError(f"Failed to refresh token: {e}")
                
        return credentials
        
    def _get_service_account_credentials(self) -> ServiceAccountCredentials:
        """Get service account credentials."""
        sa_path = self.config.get("service_account_path")
        if not sa_path:
            raise AuthenticationError("Service account path not provided")
            
        sa_path = Path(sa_path)
        if not sa_path.exists():
            raise AuthenticationError(f"Service account file not found: {sa_path}")
            
        try:
            credentials = ServiceAccountCredentials.from_service_account_file(
                str(sa_path),
                scopes=["https://www.googleapis.com/auth/adwords"],
            )
            
            # Handle impersonation if configured
            if impersonated_email := self.config.get("impersonated_email"):
                from google.auth import impersonated_credentials
                credentials = impersonated_credentials.Credentials(
                    source_credentials=credentials,
                    target_principal=impersonated_email,
                    target_scopes=["https://www.googleapis.com/auth/adwords"],
                )
                logger.info(f"Using impersonated credentials for: {impersonated_email}")
                
            return credentials
            
        except Exception as e:
            logger.error(f"Failed to load service account: {e}")
            raise AuthenticationError(f"Failed to load service account: {e}")
            
    def get_client(self, customer_id: Optional[str] = None) -> GoogleAdsClient:
        """Get an authenticated Google Ads client.
        
        Args:
            customer_id: Optional customer ID to use. Defaults to login_customer_id.
            
        Returns:
            Authenticated GoogleAdsClient instance.
        """
        # Check cache
        cache_key = customer_id or "default"
        if cached_client := self._client_cache.get(cache_key):
            return cached_client
            
        # Determine auth method
        use_service_account = bool(self.config.get("service_account_path"))
        
        try:
            if use_service_account:
                credentials = self._get_service_account_credentials()
                logger.info("Using service account authentication")
            else:
                credentials = self._get_oauth_credentials()
                logger.info("Using OAuth2 authentication")
                
            # Build configuration for GoogleAdsClient
            client_config = {
                "developer_token": self.config["developer_token"],
                "use_proto_plus": self.config.get("use_proto_plus", True),
            }
            
            # Add customer IDs
            if customer_id:
                client_config["login_customer_id"] = customer_id.replace("-", "")
            elif login_customer_id := self.config.get("login_customer_id"):
                client_config["login_customer_id"] = login_customer_id.replace("-", "")
                
            if linked_customer_id := self.config.get("linked_customer_id"):
                client_config["linked_customer_id"] = linked_customer_id.replace("-", "")
                
            # Create client
            client = GoogleAdsClient(
                credentials=credentials,
                developer_token=client_config["developer_token"],
                login_customer_id=client_config.get("login_customer_id"),
                linked_customer_id=client_config.get("linked_customer_id"),
                use_proto_plus=client_config["use_proto_plus"],
            )
            
            # Cache the client
            self._client_cache[cache_key] = client
            
            logger.info(
                "Google Ads client created successfully",
                customer_id=customer_id,
                auth_method="service_account" if use_service_account else "oauth2",
            )
            
            return client
            
        except Exception as e:
            logger.error(f"Failed to create Google Ads client: {e}")
            raise AuthenticationError(f"Failed to create client: {e}")
            
    def validate_credentials(self, customer_id: Optional[str] = None) -> bool:
        """Validate that credentials work by making a simple API call.
        
        Args:
            customer_id: Customer ID to validate against.
            
        Returns:
            True if credentials are valid, False otherwise.
        """
        try:
            client = self.get_client(customer_id)
            googleads_service = client.get_service("GoogleAdsService")
            
            # Simple query to test credentials
            query = "SELECT customer.id, customer.descriptive_name FROM customer LIMIT 1"
            
            if customer_id:
                response = googleads_service.search(
                    customer_id=customer_id.replace("-", ""),
                    query=query,
                )
            else:
                # Use the login customer ID
                response = googleads_service.search(
                    customer_id=self.config["login_customer_id"].replace("-", ""),
                    query=query,
                )
                
            # If we get here, credentials are valid
            for row in response:
                logger.info(
                    "Credentials validated successfully",
                    customer_id=row.customer.id,
                    customer_name=row.customer.descriptive_name,
                )
            return True
            
        except GoogleAdsException as e:
            logger.error(f"Credentials validation failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during validation: {e}")
            return False
            
    def get_accessible_customers(self) -> list[Dict[str, Any]]:
        """Get list of all accessible customer accounts.
        
        Returns:
            List of customer account information.
        """
        try:
            client = self.get_client()
            customer_service = client.get_service("CustomerService")
            
            accessible_customers = customer_service.list_accessible_customers()
            customers = []
            
            googleads_service = client.get_service("GoogleAdsService")
            
            for resource_name in accessible_customers.resource_names:
                customer_id = resource_name.split("/")[-1]
                
                # Get customer details
                query = f"""
                    SELECT 
                        customer.id,
                        customer.descriptive_name,
                        customer.currency_code,
                        customer.time_zone,
                        customer.manager
                    FROM customer
                    WHERE customer.id = {customer_id}
                """
                
                try:
                    response = googleads_service.search(
                        customer_id=customer_id,
                        query=query,
                    )
                    
                    for row in response:
                        customers.append({
                            "id": str(row.customer.id),
                            "name": row.customer.descriptive_name,
                            "currency_code": row.customer.currency_code,
                            "time_zone": row.customer.time_zone,
                            "is_manager": row.customer.manager,
                            "resource_name": resource_name,
                        })
                        
                except GoogleAdsException as e:
                    logger.warning(f"Failed to get details for customer {customer_id}: {e}")
                    
            return customers
            
        except Exception as e:
            logger.error(f"Failed to get accessible customers: {e}")
            raise AuthenticationError(f"Failed to get accessible customers: {e}")
            
    def refresh_token(self) -> bool:
        """Manually refresh OAuth token if needed.
        
        Returns:
            True if token was refreshed, False if using service account or refresh not needed.
        """
        if self.config.get("service_account_path"):
            logger.info("Using service account, no token refresh needed")
            return False
            
        try:
            credentials = self._get_oauth_credentials()
            if not credentials.valid:
                credentials.refresh(Request())
                logger.info("OAuth token manually refreshed")
                return True
            else:
                logger.info("OAuth token still valid")
                return False
                
        except Exception as e:
            logger.error(f"Failed to refresh token: {e}")
            raise AuthenticationError(f"Failed to refresh token: {e}")