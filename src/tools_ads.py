"""Ad management tools for Google Ads API v21."""

from typing import Any, Dict, List, Optional
import structlog

from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException

logger = structlog.get_logger(__name__)


class AdTools:
    """Ad management tools."""
    
    def __init__(self, auth_manager, error_handler):
        self.auth_manager = auth_manager
        self.error_handler = error_handler
        
    async def create_responsive_search_ad(
        self,
        customer_id: str,
        ad_group_id: str,
        headlines: List[str],
        descriptions: List[str],
        final_urls: List[str],
        path1: Optional[str] = None,
        path2: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a responsive search ad."""
        try:
            client = self.auth_manager.get_client(customer_id)
            ad_group_ad_service = client.get_service("AdGroupAdService")
            
            # Create ad group ad operation
            ad_group_ad_operation = client.get_type("AdGroupAdOperation")
            ad_group_ad = ad_group_ad_operation.create
            
            # Set ad group
            ad_group_ad.ad_group = client.get_service("AdGroupService").ad_group_path(
                customer_id, ad_group_id
            )
            
            # Set ad status
            ad_group_ad.status = client.enums.AdGroupAdStatusEnum.ENABLED
            
            # Create the responsive search ad
            ad_group_ad.ad.type_ = client.enums.AdTypeEnum.RESPONSIVE_SEARCH_AD
            responsive_search_ad_info = ad_group_ad.ad.responsive_search_ad
            
            # Add headlines (max 15, min 3)
            headlines = headlines[:15]  # Limit to API max
            for headline_text in headlines:
                headline_asset = client.get_type("AdTextAsset")
                headline_asset.text = headline_text
                responsive_search_ad_info.headlines.append(headline_asset)
            
            # Add descriptions (max 4, min 2) 
            descriptions = descriptions[:4]  # Limit to API max
            for description_text in descriptions:
                description_asset = client.get_type("AdTextAsset")
                description_asset.text = description_text
                responsive_search_ad_info.descriptions.append(description_asset)
            
            # Set final URLs
            ad_group_ad.ad.final_urls.extend(final_urls)
            
            # Set display paths if provided
            if path1:
                responsive_search_ad_info.path1 = path1
            if path2:
                responsive_search_ad_info.path2 = path2
            
            # Create the ad
            response = ad_group_ad_service.mutate_ad_group_ads(
                customer_id=customer_id,
                operations=[ad_group_ad_operation],
            )
            
            # Extract ad ID from response
            ad_resource_name = response.results[0].resource_name
            ad_id = ad_resource_name.split("/")[-1]
            
            logger.info(
                f"Created responsive search ad",
                customer_id=customer_id,
                ad_group_id=ad_group_id,
                ad_id=ad_id,
                headlines_count=len(headlines),
                descriptions_count=len(descriptions)
            )
            
            return {
                "success": True,
                "ad_id": ad_id,
                "ad_resource_name": ad_resource_name,
                "ad_group_id": ad_group_id,
                "ad_type": "RESPONSIVE_SEARCH_AD",
                "headlines_count": len(headlines),
                "descriptions_count": len(descriptions),
                "final_urls": final_urls,
                "status": "ENABLED"
            }
            
        except GoogleAdsException as e:
            logger.error(f"Failed to create responsive search ad: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_type": "GoogleAdsException"
            }
        except Exception as e:
            logger.error(f"Unexpected error creating responsive search ad: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_type": "UnexpectedError"
            }
    
    async def create_expanded_text_ad(
        self,
        customer_id: str,
        ad_group_id: str,
        headline1: str,
        headline2: str,
        description1: str,
        final_urls: List[str],
        headline3: Optional[str] = None,
        description2: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create an expanded text ad (legacy format)."""
        try:
            client = self.auth_manager.get_client(customer_id)
            ad_group_ad_service = client.get_service("AdGroupAdService")
            
            # Create ad group ad operation
            ad_group_ad_operation = client.get_type("AdGroupAdOperation")
            ad_group_ad = ad_group_ad_operation.create
            
            # Set ad group
            ad_group_ad.ad_group = client.get_service("AdGroupService").ad_group_path(
                customer_id, ad_group_id
            )
            
            # Set ad status
            ad_group_ad.status = client.enums.AdGroupAdStatusEnum.ENABLED
            
            # Create the expanded text ad
            ad_group_ad.ad.type_ = client.enums.AdTypeEnum.EXPANDED_TEXT_AD
            expanded_text_ad_info = ad_group_ad.ad.expanded_text_ad
            
            # Set headlines
            expanded_text_ad_info.headline_part1 = headline1
            expanded_text_ad_info.headline_part2 = headline2
            if headline3:
                expanded_text_ad_info.headline_part3 = headline3
            
            # Set descriptions
            expanded_text_ad_info.description = description1
            if description2:
                expanded_text_ad_info.description2 = description2
            
            # Set final URLs
            ad_group_ad.ad.final_urls.extend(final_urls)
            
            # Create the ad
            response = ad_group_ad_service.mutate_ad_group_ads(
                customer_id=customer_id,
                operations=[ad_group_ad_operation],
            )
            
            # Extract ad ID from response
            ad_resource_name = response.results[0].resource_name
            ad_id = ad_resource_name.split("/")[-1]
            
            logger.info(
                f"Created expanded text ad",
                customer_id=customer_id,
                ad_group_id=ad_group_id,
                ad_id=ad_id
            )
            
            return {
                "success": True,
                "ad_id": ad_id,
                "ad_resource_name": ad_resource_name,
                "ad_group_id": ad_group_id,
                "ad_type": "EXPANDED_TEXT_AD",
                "headlines": [headline1, headline2, headline3] if headline3 else [headline1, headline2],
                "descriptions": [description1, description2] if description2 else [description1],
                "final_urls": final_urls,
                "status": "ENABLED"
            }
            
        except GoogleAdsException as e:
            logger.error(f"Failed to create expanded text ad: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_type": "GoogleAdsException"
            }
        except Exception as e:
            logger.error(f"Unexpected error creating expanded text ad: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_type": "UnexpectedError"
            }
    
    async def list_ads(
        self,
        customer_id: str,
        ad_group_id: Optional[str] = None,
        campaign_id: Optional[str] = None,
        status: Optional[str] = None
    ) -> Dict[str, Any]:
        """List ads with optional filters."""
        try:
            client = self.auth_manager.get_client(customer_id)
            googleads_service = client.get_service("GoogleAdsService")
            
            # Build query
            query = """
                SELECT
                    ad_group_ad.ad.id,
                    ad_group_ad.ad.type,
                    ad_group_ad.status,
                    ad_group_ad.ad.final_urls,
                    ad_group_ad.ad.responsive_search_ad.headlines,
                    ad_group_ad.ad.responsive_search_ad.descriptions,
                    ad_group_ad.ad.expanded_text_ad.headline_part1,
                    ad_group_ad.ad.expanded_text_ad.headline_part2,
                    ad_group_ad.ad.expanded_text_ad.description,
                    ad_group.id,
                    ad_group.name,
                    campaign.id,
                    campaign.name
                FROM ad_group_ad
            """
            
            # Add filters
            conditions = []
            if ad_group_id:
                conditions.append(f"ad_group.id = {ad_group_id}")
            if campaign_id:
                conditions.append(f"campaign.id = {campaign_id}")
            if status:
                status_enum = f"ad_group_ad.status = {status.upper()}"
                conditions.append(status_enum)
                
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
                
            response = googleads_service.search(
                customer_id=customer_id, query=query
            )
            
            ads = []
            for row in response:
                ad_data = {
                    "id": str(row.ad_group_ad.ad.id),
                    "type": str(row.ad_group_ad.ad.type_.name),
                    "status": str(row.ad_group_ad.status.name),
                    "final_urls": list(row.ad_group_ad.ad.final_urls),
                    "ad_group_id": str(row.ad_group.id),
                    "ad_group_name": str(row.ad_group.name),
                    "campaign_id": str(row.campaign.id),
                    "campaign_name": str(row.campaign.name)
                }
                
                # Add type-specific details
                if row.ad_group_ad.ad.type_.name == "RESPONSIVE_SEARCH_AD":
                    rsa = row.ad_group_ad.ad.responsive_search_ad
                    ad_data["headlines"] = [h.text for h in rsa.headlines]
                    ad_data["descriptions"] = [d.text for d in rsa.descriptions]
                elif row.ad_group_ad.ad.type_.name == "EXPANDED_TEXT_AD":
                    eta = row.ad_group_ad.ad.expanded_text_ad
                    ad_data["headline1"] = eta.headline_part1
                    ad_data["headline2"] = eta.headline_part2
                    ad_data["headline3"] = eta.headline_part3 if eta.headline_part3 else None
                    ad_data["description1"] = eta.description
                    ad_data["description2"] = eta.description2 if eta.description2 else None
                
                ads.append(ad_data)
            
            return {
                "success": True,
                "ads": ads,
                "count": len(ads),
                "filters": {
                    "ad_group_id": ad_group_id,
                    "campaign_id": campaign_id,
                    "status": status
                }
            }
            
        except GoogleAdsException as e:
            logger.error(f"Failed to list ads: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_type": "GoogleAdsException"
            }
        except Exception as e:
            logger.error(f"Unexpected error listing ads: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_type": "UnexpectedError"
            }
