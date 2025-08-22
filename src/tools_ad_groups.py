"""Ad Group management tools for Google Ads API v21."""

from typing import Any, Dict, List, Optional
from datetime import datetime, date
import structlog

from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException

from .utils import currency_to_micros, micros_to_currency

logger = structlog.get_logger(__name__)


class AdGroupTools:
    """Ad Group management tools."""
    
    def __init__(self, auth_manager, error_handler):
        self.auth_manager = auth_manager
        self.error_handler = error_handler
        
    async def create_ad_group(
        self,
        customer_id: str,
        campaign_id: str,
        name: str,
        cpc_bid_micros: int = 2000000,  # Default $2 CPC
        ad_group_type: str = "SEARCH_STANDARD"
    ) -> Dict[str, Any]:
        """Create a new ad group in the specified campaign."""
        try:
            client = self.auth_manager.get_client(customer_id)
            ad_group_service = client.get_service("AdGroupService")
            
            # Create ad group operation
            ad_group_operation = client.get_type("AdGroupOperation")
            ad_group = ad_group_operation.create
            
            # Set ad group properties
            ad_group.name = name
            ad_group.campaign = client.get_service("CampaignService").campaign_path(
                customer_id, campaign_id
            )
            
            # Set ad group type (API v21 compatible)
            if ad_group_type.upper() == "SEARCH_STANDARD":
                ad_group.type_ = client.enums.AdGroupTypeEnum.SEARCH_STANDARD
            elif ad_group_type.upper() == "DISPLAY_STANDARD":
                ad_group.type_ = client.enums.AdGroupTypeEnum.DISPLAY_STANDARD
            else:
                ad_group.type_ = client.enums.AdGroupTypeEnum.SEARCH_STANDARD
            
            # Set status
            ad_group.status = client.enums.AdGroupStatusEnum.ENABLED
            
            # Set bidding - use CPC bid amount
            ad_group.cpc_bid_micros = cpc_bid_micros
            
            # Create the ad group
            response = ad_group_service.mutate_ad_groups(
                customer_id=customer_id,
                operations=[ad_group_operation],
            )
            
            # Extract ad group ID from the response
            ad_group_resource_name = response.results[0].resource_name
            ad_group_id = ad_group_resource_name.split("/")[-1]
            
            logger.info(
                f"Created ad group",
                customer_id=customer_id,
                campaign_id=campaign_id,
                ad_group_id=ad_group_id,
                name=name
            )
            
            return {
                "success": True,
                "ad_group_id": ad_group_id,
                "ad_group_resource_name": ad_group_resource_name,
                "name": name,
                "campaign_id": campaign_id,
                "cpc_bid": micros_to_currency(cpc_bid_micros),
                "status": "ENABLED",
                "type": ad_group_type.upper()
            }
            
        except GoogleAdsException as e:
            logger.error(f"Failed to create ad group: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_type": "GoogleAdsException"
            }
        except Exception as e:
            logger.error(f"Unexpected error creating ad group: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_type": "UnexpectedError"
            }
    
    async def list_ad_groups(
        self,
        customer_id: str,
        campaign_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """List ad groups, optionally filtered by campaign."""
        try:
            client = self.auth_manager.get_client(customer_id)
            googleads_service = client.get_service("GoogleAdsService")
            
            # Build query
            query = """
                SELECT
                    ad_group.id,
                    ad_group.name,
                    ad_group.status,
                    ad_group.type,
                    ad_group.cpc_bid_micros,
                    campaign.id,
                    campaign.name
                FROM ad_group
            """
            
            if campaign_id:
                query += f" WHERE campaign.id = {campaign_id}"
                
            response = googleads_service.search(
                customer_id=customer_id, query=query
            )
            
            ad_groups = []
            for row in response:
                ad_groups.append({
                    "id": str(row.ad_group.id),
                    "name": str(row.ad_group.name),
                    "status": str(row.ad_group.status.name),
                    "type": str(row.ad_group.type_.name),
                    "cpc_bid": micros_to_currency(row.ad_group.cpc_bid_micros),
                    "campaign_id": str(row.campaign.id),
                    "campaign_name": str(row.campaign.name)
                })
            
            return {
                "success": True,
                "ad_groups": ad_groups,
                "count": len(ad_groups),
                "filtered_by_campaign": campaign_id is not None
            }
            
        except GoogleAdsException as e:
            logger.error(f"Failed to list ad groups: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_type": "GoogleAdsException"
            }
        except Exception as e:
            logger.error(f"Unexpected error listing ad groups: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_type": "UnexpectedError"
            }
    
    async def update_ad_group(
        self,
        customer_id: str,
        ad_group_id: str,
        name: Optional[str] = None,
        cpc_bid_micros: Optional[int] = None,
        status: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update an existing ad group."""
        try:
            client = self.auth_manager.get_client(customer_id)
            ad_group_service = client.get_service("AdGroupService")
            
            # Create ad group operation
            ad_group_operation = client.get_type("AdGroupOperation")
            ad_group = ad_group_operation.update
            
            # Set the resource name
            ad_group.resource_name = ad_group_service.ad_group_path(
                customer_id, ad_group_id
            )
            
            # Set update mask fields (API v21 compatible)
            from google.protobuf.field_mask_pb2 import FieldMask
            update_mask = FieldMask()
            paths = []
            
            if name is not None:
                ad_group.name = name
                paths.append("name")
                
            if cpc_bid_micros is not None:
                ad_group.cpc_bid_micros = cpc_bid_micros
                paths.append("cpc_bid_micros")
                
            if status is not None:
                if status.upper() == "ENABLED":
                    ad_group.status = client.enums.AdGroupStatusEnum.ENABLED
                elif status.upper() == "PAUSED":
                    ad_group.status = client.enums.AdGroupStatusEnum.PAUSED
                paths.append("status")
                
            update_mask.paths.extend(paths)
            ad_group_operation.update_mask = update_mask
            
            # Update the ad group
            response = ad_group_service.mutate_ad_groups(
                customer_id=customer_id,
                operations=[ad_group_operation],
            )
            
            logger.info(
                f"Updated ad group",
                customer_id=customer_id,
                ad_group_id=ad_group_id,
                updated_fields=paths
            )
            
            return {
                "success": True,
                "ad_group_id": ad_group_id,
                "updated_fields": paths,
                "message": f"Successfully updated ad group {ad_group_id}"
            }
            
        except GoogleAdsException as e:
            logger.error(f"Failed to update ad group: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_type": "GoogleAdsException"
            }
        except Exception as e:
            logger.error(f"Unexpected error updating ad group: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_type": "UnexpectedError"
            }
    
    async def get_ad_group(
        self,
        customer_id: str,
        ad_group_id: str
    ) -> Dict[str, Any]:
        """Get detailed information about a specific ad group."""
        try:
            client = self.auth_manager.get_client(customer_id)
            googleads_service = client.get_service("GoogleAdsService")
            
            query = f"""
                SELECT
                    ad_group.id,
                    ad_group.name,
                    ad_group.status,
                    ad_group.type,
                    ad_group.cpc_bid_micros,
                    campaign.id,
                    campaign.name,
                    campaign.status
                FROM ad_group
                WHERE ad_group.id = {ad_group_id}
            """
            
            response = googleads_service.search(
                customer_id=customer_id, query=query
            )
            
            for row in response:
                return {
                    "success": True,
                    "ad_group": {
                        "id": str(row.ad_group.id),
                        "name": str(row.ad_group.name),
                        "status": str(row.ad_group.status.name),
                        "type": str(row.ad_group.type_.name),
                        "cpc_bid": micros_to_currency(row.ad_group.cpc_bid_micros),
                        "cpc_bid_micros": row.ad_group.cpc_bid_micros,
                        "campaign": {
                            "id": str(row.campaign.id),
                            "name": str(row.campaign.name),
                            "status": str(row.campaign.status.name)
                        }
                    }
                }
            
            # If no results found
            return {
                "success": False,
                "error": f"Ad group {ad_group_id} not found",
                "error_type": "NotFound"
            }
            
        except GoogleAdsException as e:
            logger.error(f"Failed to get ad group: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_type": "GoogleAdsException"
            }
        except Exception as e:
            logger.error(f"Unexpected error getting ad group: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_type": "UnexpectedError"
            }
