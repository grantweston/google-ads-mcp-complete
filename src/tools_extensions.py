"""Extensions management tools for Google Ads API v21."""

from typing import Any, Dict, List, Optional
import structlog

from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException

logger = structlog.get_logger(__name__)


class ExtensionTools:
    """Extension management tools."""
    
    def __init__(self, auth_manager, error_handler):
        self.auth_manager = auth_manager
        self.error_handler = error_handler
        
    async def create_sitelink_extensions(
        self,
        customer_id: str,
        campaign_id: str,
        sitelinks: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """Create sitelink extensions for a campaign.
        
        Args:
            customer_id: The customer ID
            campaign_id: The campaign ID
            sitelinks: List of sitelinks with 'text', 'url' and optional 'description1', 'description2'
        """
        try:
            client = self.auth_manager.get_client(customer_id)
            extension_feed_item_service = client.get_service("ExtensionFeedItemService")
            
            operations = []
            created_extensions = []
            
            for sitelink in sitelinks:
                # Create sitelink extension
                extension_feed_item_operation = client.get_type("ExtensionFeedItemOperation")
                extension_feed_item = extension_feed_item_operation.create
                
                # Set extension type
                extension_feed_item.extension_type = client.enums.ExtensionTypeEnum.SITELINK
                
                # Set sitelink feed item
                sitelink_feed_item = extension_feed_item.sitelink_feed_item
                sitelink_feed_item.link_text = sitelink["text"]
                sitelink_feed_item.line1 = sitelink.get("description1", "")
                sitelink_feed_item.line2 = sitelink.get("description2", "")
                
                # Set final URLs
                extension_feed_item.final_urls.append(sitelink["url"])
                
                # Set targeted campaign
                extension_feed_item.targeted_campaign = client.get_service("CampaignService").campaign_path(
                    customer_id, campaign_id
                )
                
                operations.append(extension_feed_item_operation)
            
            # Execute operations
            response = extension_feed_item_service.mutate_extension_feed_items(
                customer_id=customer_id,
                operations=operations
            )
            
            for i, result in enumerate(response.results):
                created_extensions.append({
                    "sitelink_text": sitelinks[i]["text"],
                    "url": sitelinks[i]["url"],
                    "resource_name": result.resource_name,
                })
            
            return {
                "success": True,
                "campaign_id": campaign_id,
                "sitelinks_created": len(created_extensions),
                "sitelinks": created_extensions,
            }
            
        except GoogleAdsException as e:
            logger.error(f"Failed to create sitelink extensions: {e}")
            raise
    
    async def create_callout_extensions(
        self,
        customer_id: str,
        campaign_id: str,
        callouts: List[str]
    ) -> Dict[str, Any]:
        """Create callout extensions for a campaign.
        
        Args:
            customer_id: The customer ID
            campaign_id: The campaign ID  
            callouts: List of callout text strings
        """
        try:
            client = self.auth_manager.get_client(customer_id)
            extension_feed_item_service = client.get_service("ExtensionFeedItemService")
            
            operations = []
            created_extensions = []
            
            for callout_text in callouts:
                # Create callout extension
                extension_feed_item_operation = client.get_type("ExtensionFeedItemOperation")
                extension_feed_item = extension_feed_item_operation.create
                
                # Set extension type
                extension_feed_item.extension_type = client.enums.ExtensionTypeEnum.CALLOUT
                
                # Set callout feed item
                callout_feed_item = extension_feed_item.callout_feed_item
                callout_feed_item.callout_text = callout_text
                
                # Set targeted campaign
                extension_feed_item.targeted_campaign = client.get_service("CampaignService").campaign_path(
                    customer_id, campaign_id
                )
                
                operations.append(extension_feed_item_operation)
            
            # Execute operations
            response = extension_feed_item_service.mutate_extension_feed_items(
                customer_id=customer_id,
                operations=operations
            )
            
            for i, result in enumerate(response.results):
                created_extensions.append({
                    "callout_text": callouts[i],
                    "resource_name": result.resource_name,
                })
            
            return {
                "success": True,
                "campaign_id": campaign_id,
                "callouts_created": len(created_extensions),
                "callouts": created_extensions,
            }
            
        except GoogleAdsException as e:
            logger.error(f"Failed to create callout extensions: {e}")
            raise
    
    async def create_call_extensions(
        self,
        customer_id: str,
        campaign_id: str,
        phone_number: str,
        country_code: str = "US",
        call_only: bool = False
    ) -> Dict[str, Any]:
        """Create call extensions for a campaign.
        
        Args:
            customer_id: The customer ID
            campaign_id: The campaign ID
            phone_number: The phone number to display
            country_code: The country code (default: US)
            call_only: Whether this is call-only (default: False)
        """
        try:
            client = self.auth_manager.get_client(customer_id)
            extension_feed_item_service = client.get_service("ExtensionFeedItemService")
            
            # Create call extension
            extension_feed_item_operation = client.get_type("ExtensionFeedItemOperation")
            extension_feed_item = extension_feed_item_operation.create
            
            # Set extension type
            extension_feed_item.extension_type = client.enums.ExtensionTypeEnum.CALL
            
            # Set call feed item
            call_feed_item = extension_feed_item.call_feed_item
            call_feed_item.phone_number = phone_number
            call_feed_item.country_code = country_code
            call_feed_item.call_tracking_enabled = True
            call_feed_item.call_conversion_action = ""  # Can be set if conversion tracking is needed
            call_feed_item.call_conversion_tracking_disabled = False
            
            # Set targeted campaign
            extension_feed_item.targeted_campaign = client.get_service("CampaignService").campaign_path(
                customer_id, campaign_id
            )
            
            # Execute operation
            response = extension_feed_item_service.mutate_extension_feed_items(
                customer_id=customer_id,
                operations=[extension_feed_item_operation]
            )
            
            return {
                "success": True,
                "campaign_id": campaign_id,
                "phone_number": phone_number,
                "country_code": country_code,
                "resource_name": response.results[0].resource_name,
            }
            
        except GoogleAdsException as e:
            logger.error(f"Failed to create call extension: {e}")
            raise
    
    async def list_extensions(
        self,
        customer_id: str,
        campaign_id: Optional[str] = None,
        extension_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """List extensions for a campaign or account.
        
        Args:
            customer_id: The customer ID
            campaign_id: Optional campaign ID to filter by
            extension_type: Optional extension type (SITELINK, CALLOUT, CALL, etc.)
        """
        try:
            client = self.auth_manager.get_client(customer_id)
            googleads_service = client.get_service("GoogleAdsService")
            
            query = """
                SELECT
                    extension_feed_item.resource_name,
                    extension_feed_item.id,
                    extension_feed_item.extension_type,
                    extension_feed_item.status,
                    extension_feed_item.sitelink_feed_item.link_text,
                    extension_feed_item.sitelink_feed_item.line1,
                    extension_feed_item.sitelink_feed_item.line2,
                    extension_feed_item.callout_feed_item.callout_text,
                    extension_feed_item.call_feed_item.phone_number,
                    extension_feed_item.call_feed_item.country_code,
                    extension_feed_item.final_urls,
                    campaign.name,
                    campaign.id
                FROM extension_feed_item
            """
            
            conditions = []
            if campaign_id:
                conditions.append(f"campaign.id = {campaign_id}")
            if extension_type:
                conditions.append(f"extension_feed_item.extension_type = '{extension_type.upper()}'")
            
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            
            query += " ORDER BY extension_feed_item.extension_type, extension_feed_item.id"
            
            response = googleads_service.search(
                customer_id=customer_id,
                query=query
            )
            
            extensions = []
            for row in response:
                extension_data = {
                    "id": str(row.extension_feed_item.id),
                    "type": str(row.extension_feed_item.extension_type.name),
                    "status": str(row.extension_feed_item.status.name),
                    "campaign_name": str(row.campaign.name),
                    "campaign_id": str(row.campaign.id),
                    "resource_name": row.extension_feed_item.resource_name,
                }
                
                # Add type-specific data
                if row.extension_feed_item.extension_type.name == "SITELINK":
                    extension_data["sitelink"] = {
                        "link_text": str(row.extension_feed_item.sitelink_feed_item.link_text),
                        "description1": str(row.extension_feed_item.sitelink_feed_item.line1),
                        "description2": str(row.extension_feed_item.sitelink_feed_item.line2),
                        "url": row.extension_feed_item.final_urls[0] if row.extension_feed_item.final_urls else "",
                    }
                elif row.extension_feed_item.extension_type.name == "CALLOUT":
                    extension_data["callout"] = {
                        "text": str(row.extension_feed_item.callout_feed_item.callout_text),
                    }
                elif row.extension_feed_item.extension_type.name == "CALL":
                    extension_data["call"] = {
                        "phone_number": str(row.extension_feed_item.call_feed_item.phone_number),
                        "country_code": str(row.extension_feed_item.call_feed_item.country_code),
                    }
                
                extensions.append(extension_data)
            
            return {
                "success": True,
                "campaign_id": campaign_id,
                "extension_type": extension_type,
                "extensions": extensions,
                "count": len(extensions),
            }
            
        except GoogleAdsException as e:
            logger.error(f"Failed to list extensions: {e}")
            raise
    
    async def delete_extension(
        self,
        customer_id: str,
        extension_id: str
    ) -> Dict[str, Any]:
        """Delete a specific extension.
        
        Args:
            customer_id: The customer ID
            extension_id: The extension feed item resource name or ID
        """
        try:
            client = self.auth_manager.get_client(customer_id)
            extension_feed_item_service = client.get_service("ExtensionFeedItemService")
            
            # Create remove operation
            extension_feed_item_operation = client.get_type("ExtensionFeedItemOperation")
            
            # Handle both resource name and ID formats
            if extension_id.startswith("customers/"):
                extension_feed_item_operation.remove = extension_id
            else:
                extension_feed_item_operation.remove = client.get_service("ExtensionFeedItemService").extension_feed_item_path(
                    customer_id, extension_id
                )
            
            # Execute removal
            response = extension_feed_item_service.mutate_extension_feed_items(
                customer_id=customer_id,
                operations=[extension_feed_item_operation]
            )
            
            return {
                "success": True,
                "extension_id": extension_id,
                "message": "Extension deleted successfully",
                "resource_name": response.results[0].resource_name,
            }
            
        except GoogleAdsException as e:
            logger.error(f"Failed to delete extension: {e}")
            raise
