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
            asset_service = client.get_service("AssetService")
            campaign_asset_service = client.get_service("CampaignAssetService")
            
            # Step 1: Create sitelink assets
            asset_operations = []
            created_extensions = []
            
            for sitelink in sitelinks:
                # Create sitelink asset
                asset_operation = client.get_type("AssetOperation")
                asset = asset_operation.create
                asset.name = f"Sitelink: {sitelink['text']}"
                
                # Create SitelinkAsset with all required fields
                sitelink_asset = client.get_type("SitelinkAsset")
                sitelink_asset.link_text = sitelink["text"]
                # description1 and description2 are REQUIRED fields
                sitelink_asset.description1 = sitelink.get("description1", sitelink["text"])  # Use text as fallback
                sitelink_asset.description2 = sitelink.get("description2", "Learn more")  # Default fallback
                
                asset.sitelink_asset = sitelink_asset
                asset.type_ = client.enums.AssetTypeEnum.SITELINK
                # final_urls is required on the Asset level (not sitelink_asset)
                asset.final_urls.append(sitelink["url"])
                
                asset_operations.append(asset_operation)
            
            # Step 1: Create assets
            asset_response = asset_service.mutate_assets(
                customer_id=customer_id,
                operations=asset_operations
            )
            
            # Step 2: Associate assets with campaign
            campaign_asset_operations = []
            for i, asset_result in enumerate(asset_response.results):
                campaign_asset_operation = client.get_type("CampaignAssetOperation")
                campaign_asset = campaign_asset_operation.create
                
                campaign_asset.campaign = client.get_service("CampaignService").campaign_path(
                    customer_id, campaign_id
                )
                campaign_asset.asset = asset_result.resource_name
                campaign_asset.field_type = client.enums.AssetFieldTypeEnum.SITELINK
                # URLs are set on the Asset level, not CampaignAsset level
                
                campaign_asset_operations.append(campaign_asset_operation)
                
                created_extensions.append({
                    "text": sitelinks[i]["text"],
                    "url": sitelinks[i]["url"],
                    "asset_resource_name": asset_result.resource_name,
                    "asset_id": asset_result.resource_name.split("/")[-1]
                })
            
            # Execute campaign asset operations
            campaign_asset_response = campaign_asset_service.mutate_campaign_assets(
                customer_id=customer_id,
                operations=campaign_asset_operations
            )
            
            return {
                "success": True,
                "campaign_id": campaign_id,
                "sitelinks_created": len(created_extensions),
                "sitelinks": created_extensions,
                "message": f"Created {len(created_extensions)} sitelink assets and associated with campaign {campaign_id}"
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
            asset_service = client.get_service("AssetService")
            campaign_asset_service = client.get_service("CampaignAssetService")
            
            # Step 1: Create callout assets
            asset_operations = []
            created_extensions = []
            
            for callout_text in callouts:
                # Create callout asset
                asset_operation = client.get_type("AssetOperation")
                asset = asset_operation.create
                asset.name = f"Callout: {callout_text}"
                
                # Create CalloutAsset
                callout_asset = client.get_type("CalloutAsset")
                callout_asset.callout_text = callout_text
                
                asset.callout_asset = callout_asset
                asset.type_ = client.enums.AssetTypeEnum.CALLOUT
                
                asset_operations.append(asset_operation)
            
            # Step 1: Create assets
            asset_response = asset_service.mutate_assets(
                customer_id=customer_id,
                operations=asset_operations
            )
            
            # Step 2: Associate assets with campaign
            campaign_asset_operations = []
            for i, asset_result in enumerate(asset_response.results):
                campaign_asset_operation = client.get_type("CampaignAssetOperation")
                campaign_asset = campaign_asset_operation.create
                
                campaign_asset.campaign = client.get_service("CampaignService").campaign_path(
                    customer_id, campaign_id
                )
                campaign_asset.asset = asset_result.resource_name
                campaign_asset.field_type = client.enums.AssetFieldTypeEnum.CALLOUT
                
                campaign_asset_operations.append(campaign_asset_operation)
                
                created_extensions.append({
                    "callout_text": callouts[i],
                    "asset_resource_name": asset_result.resource_name,
                    "asset_id": asset_result.resource_name.split("/")[-1]
                })
            
            # Execute campaign asset operations
            campaign_asset_response = campaign_asset_service.mutate_campaign_assets(
                customer_id=customer_id,
                operations=campaign_asset_operations
            )
            
            return {
                "success": True,
                "campaign_id": campaign_id,
                "callouts_created": len(created_extensions),
                "callouts": created_extensions,
                "message": f"Created {len(created_extensions)} callout assets and associated with campaign {campaign_id}"
            }
            
        except GoogleAdsException as e:
            logger.error(f"Failed to create callout extensions: {e}")
            raise
    
    async def create_structured_snippet_extensions(
        self,
        customer_id: str,
        campaign_id: str,
        structured_snippets: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Create structured snippet extensions for a campaign.
        
        Args:
            customer_id: The customer ID
            campaign_id: The campaign ID
            structured_snippets: List of snippets with 'header' and 'values'
                Example: [{"header": "Services", "values": ["Web Design", "SEO", "PPC"]}]
        """
        try:
            client = self.auth_manager.get_client(customer_id)
            asset_service = client.get_service("AssetService")
            campaign_asset_service = client.get_service("CampaignAssetService")
            
            # Step 1: Create structured snippet assets
            asset_operations = []
            created_extensions = []
            
            for snippet in structured_snippets:
                # Create structured snippet asset
                asset_operation = client.get_type("AssetOperation")
                asset = asset_operation.create
                asset.name = f"Structured Snippet: {snippet['header']}"
                
                # Create StructuredSnippetAsset
                structured_snippet_asset = client.get_type("StructuredSnippetAsset")
                
                # Map header to proper enum value (Google has predefined headers)
                header_map = {
                    "AMENITIES": "AMENITIES",
                    "BRANDS": "BRANDS", 
                    "COURSES": "COURSES",
                    "DEGREE_PROGRAMS": "DEGREE_PROGRAMS",
                    "DESTINATIONS": "DESTINATIONS",
                    "FEATURED_HOTELS": "FEATURED_HOTELS",
                    "INSURANCE_COVERAGE": "INSURANCE_COVERAGE",
                    "MODELS": "MODELS",
                    "NEIGHBORHOODS": "NEIGHBORHOODS",
                    "SERVICE_CATALOG": "SERVICE_CATALOG",
                    "SERVICES": "SERVICE_CATALOG",  # Map SERVICES to SERVICE_CATALOG
                    "FEATURES": "SERVICE_CATALOG",  # Map FEATURES to SERVICE_CATALOG
                    "SHOW": "SHOW",
                    "STYLES": "STYLES",
                    "TYPES": "TYPES"
                }
                
                header_key = snippet["header"].upper()
                if header_key not in header_map:
                    # Default to SERVICE_CATALOG if unknown header
                    header_key = "SERVICE_CATALOG"
                    
                # Use simple string values for headers - Google expects specific strings
                if header_key in ["SERVICES", "FEATURES", "SERVICE_CATALOG"]:
                    structured_snippet_asset.header = "Services"
                elif header_key == "BRANDS":
                    structured_snippet_asset.header = "Brands"
                elif header_key == "AMENITIES":
                    structured_snippet_asset.header = "Amenities"
                elif header_key == "DESTINATIONS":
                    structured_snippet_asset.header = "Destinations"
                elif header_key == "MODELS":
                    structured_snippet_asset.header = "Models"
                elif header_key == "STYLES":
                    structured_snippet_asset.header = "Styles"
                elif header_key == "TYPES":
                    structured_snippet_asset.header = "Types"
                else:
                    structured_snippet_asset.header = "Services"  # Default
                
                # Ensure minimum 3 values for structured snippets (Google requirement)
                values = snippet["values"][:]  # Copy the list
                if len(values) < 3:
                    # Pad with generic values if too few provided
                    padding_needed = 3 - len(values)
                    for i in range(padding_needed):
                        values.append(f"Service {len(values) + 1}")
                
                # Ensure each value is at least 1 character and max 25 characters
                validated_values = []
                for value in values:
                    validated_value = str(value).strip()[:25]  # Limit to 25 chars
                    if validated_value:  # Only add non-empty values
                        validated_values.append(validated_value)
                
                # Ensure we still have at least 3 after validation
                while len(validated_values) < 3:
                    validated_values.append("Service")
                
                structured_snippet_asset.values.extend(validated_values)
                
                asset.structured_snippet_asset = structured_snippet_asset
                asset.type_ = client.enums.AssetTypeEnum.STRUCTURED_SNIPPET
                
                asset_operations.append(asset_operation)
            
            # Step 1: Create assets
            asset_response = asset_service.mutate_assets(
                customer_id=customer_id,
                operations=asset_operations
            )
            
            # Step 2: Associate assets with campaign
            campaign_asset_operations = []
            for i, asset_result in enumerate(asset_response.results):
                campaign_asset_operation = client.get_type("CampaignAssetOperation")
                campaign_asset = campaign_asset_operation.create
                
                campaign_asset.campaign = client.get_service("CampaignService").campaign_path(
                    customer_id, campaign_id
                )
                campaign_asset.asset = asset_result.resource_name
                campaign_asset.field_type = client.enums.AssetFieldTypeEnum.STRUCTURED_SNIPPET
                
                campaign_asset_operations.append(campaign_asset_operation)
                
                created_extensions.append({
                    "header": structured_snippets[i]["header"],
                    "values": structured_snippets[i]["values"],
                    "asset_resource_name": asset_result.resource_name,
                    "asset_id": asset_result.resource_name.split("/")[-1]
                })
            
            # Execute campaign asset operations
            campaign_asset_response = campaign_asset_service.mutate_campaign_assets(
                customer_id=customer_id,
                operations=campaign_asset_operations
            )
            
            return {
                "success": True,
                "campaign_id": campaign_id,
                "structured_snippets_created": len(created_extensions),
                "structured_snippets": created_extensions,
                "message": f"Created {len(created_extensions)} structured snippet assets and associated with campaign {campaign_id}"
            }
            
        except GoogleAdsException as e:
            logger.error(f"Failed to create structured snippet extensions: {e}")
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


