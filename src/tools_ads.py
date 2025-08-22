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
    
    async def update_ad(
        self,
        customer_id: str,
        ad_group_id: str,
        ad_id: str,
        headlines: Optional[List[str]] = None,
        descriptions: Optional[List[str]] = None,
        final_urls: Optional[List[str]] = None,
        path1: Optional[str] = None,
        path2: Optional[str] = None,
        status: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update an existing ad."""
        try:
            client = self.auth_manager.get_client(customer_id)
            ad_group_ad_service = client.get_service("AdGroupAdService")
            
            # Create update operation
            ad_group_ad_operation = client.get_type("AdGroupAdOperation")
            ad_group_ad = ad_group_ad_operation.update
            
            # Set the ad resource name
            ad_group_ad.resource_name = client.get_service("AdGroupAdService").ad_group_ad_path(
                customer_id, ad_group_id, ad_id
            )
            
            # Update fields based on what's provided
            from google.protobuf.field_mask_pb2 import FieldMask
            update_mask = FieldMask()
            
            # Update status if provided
            if status:
                if status.upper() == "ENABLED":
                    ad_group_ad.status = client.enums.AdGroupAdStatusEnum.ENABLED
                elif status.upper() == "PAUSED":
                    ad_group_ad.status = client.enums.AdGroupAdStatusEnum.PAUSED
                update_mask.paths.append("status")
            
            # Update ad content if provided (for responsive search ads)
            if headlines or descriptions or final_urls or path1 is not None or path2 is not None:
                if headlines:
                    ad_group_ad.ad.responsive_search_ad.headlines.clear()
                    for i, headline in enumerate(headlines[:15]):  # Max 15 headlines
                        headline_asset = client.get_type("AdTextAsset")
                        headline_asset.text = headline
                        ad_group_ad.ad.responsive_search_ad.headlines.append(headline_asset)
                    update_mask.paths.append("ad.responsive_search_ad.headlines")
                
                if descriptions:
                    ad_group_ad.ad.responsive_search_ad.descriptions.clear()
                    for i, description in enumerate(descriptions[:4]):  # Max 4 descriptions
                        description_asset = client.get_type("AdTextAsset")
                        description_asset.text = description
                        ad_group_ad.ad.responsive_search_ad.descriptions.append(description_asset)
                    update_mask.paths.append("ad.responsive_search_ad.descriptions")
                
                if final_urls:
                    ad_group_ad.ad.final_urls.clear()
                    ad_group_ad.ad.final_urls.extend(final_urls)
                    update_mask.paths.append("ad.final_urls")
                
                # Update display paths
                if path1 is not None:
                    ad_group_ad.ad.responsive_search_ad.path1 = path1
                    update_mask.paths.append("ad.responsive_search_ad.path1")
                
                if path2 is not None:
                    ad_group_ad.ad.responsive_search_ad.path2 = path2
                    update_mask.paths.append("ad.responsive_search_ad.path2")
            
            # Set the update mask
            ad_group_ad_operation.update_mask = update_mask
            
            # Execute the update
            response = ad_group_ad_service.mutate_ad_group_ads(
                customer_id=customer_id,
                operations=[ad_group_ad_operation]
            )
            
            return {
                "success": True,
                "ad_id": ad_id,
                "updated_fields": list(update_mask.paths),
                "resource_name": response.results[0].resource_name,
            }
            
        except GoogleAdsException as e:
            logger.error(f"Failed to update ad: {e}")
            raise
    
    async def pause_ad(
        self,
        customer_id: str,
        ad_group_id: str,
        ad_id: str
    ) -> Dict[str, Any]:
        """Pause a specific ad."""
        return await self.update_ad(customer_id, ad_group_id, ad_id, status="PAUSED")
    
    async def enable_ad(
        self,
        customer_id: str,
        ad_group_id: str,
        ad_id: str
    ) -> Dict[str, Any]:
        """Enable a specific ad."""
        return await self.update_ad(customer_id, ad_group_id, ad_id, status="ENABLED")
    
    async def delete_ad(
        self,
        customer_id: str,
        ad_group_id: str,
        ad_id: str
    ) -> Dict[str, Any]:
        """Delete a specific ad."""
        try:
            client = self.auth_manager.get_client(customer_id)
            ad_group_ad_service = client.get_service("AdGroupAdService")
            
            # Create remove operation
            ad_group_ad_operation = client.get_type("AdGroupAdOperation")
            ad_group_ad_operation.remove = client.get_service("AdGroupAdService").ad_group_ad_path(
                customer_id, ad_group_id, ad_id
            )
            
            # Execute the removal
            response = ad_group_ad_service.mutate_ad_group_ads(
                customer_id=customer_id,
                operations=[ad_group_ad_operation]
            )
            
            return {
                "success": True,
                "ad_id": ad_id,
                "message": "Ad deleted successfully",
                "resource_name": response.results[0].resource_name,
            }
            
        except GoogleAdsException as e:
            logger.error(f"Failed to delete ad: {e}")
            raise
    
    async def get_ad_strength_and_review_status(
        self,
        customer_id: str,
        ad_group_id: Optional[str] = None,
        campaign_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get detailed ad strength, quality ratings, and review status for ads."""
        try:
            client = self.auth_manager.get_client(customer_id)
            googleads_service = client.get_service("GoogleAdsService")
            
            # Enhanced query to get ad strength, review status, and policy info
            query = """
                SELECT
                    ad_group_ad.ad.id,
                    ad_group_ad.ad.name,
                    ad_group_ad.status,
                    ad_group_ad.policy_summary.review_status,
                    ad_group_ad.policy_summary.approval_status,
                    ad_group_ad.ad.responsive_search_ad.headlines,
                    ad_group_ad.ad.responsive_search_ad.descriptions,
                    ad_group_ad.ad.responsive_search_ad.path1,
                    ad_group_ad.ad.responsive_search_ad.path2,
                    ad_group_ad.ad.final_urls,
                    ad_group_ad.ad.type,
                    ad_group_ad.strength,
                    ad_group.id,
                    ad_group.name,
                    campaign.id,
                    campaign.name,
                    metrics.clicks,
                    metrics.impressions,
                    metrics.ctr
                FROM ad_group_ad
                WHERE segments.date DURING LAST_30_DAYS
            """
            
            # Add filters
            conditions = []
            if ad_group_id:
                conditions.append(f"ad_group.id = {ad_group_id}")
            if campaign_id:
                conditions.append(f"campaign.id = {campaign_id}")
                
            if conditions:
                query += " AND " + " AND ".join(conditions)
            
            query += " ORDER BY ad_group_ad.ad.id"
            
            response = googleads_service.search(
                customer_id=customer_id, query=query
            )
            
            ads_details = []
            for row in response:
                ad_data = {
                    "ad_id": str(row.ad_group_ad.ad.id),
                    "ad_name": str(row.ad_group_ad.ad.name) if row.ad_group_ad.ad.name else f"Ad {row.ad_group_ad.ad.id}",
                    "ad_type": str(row.ad_group_ad.ad.type_.name),
                    "status": str(row.ad_group_ad.status.name),
                    "ad_group_name": str(row.ad_group.name),
                    "campaign_name": str(row.campaign.name),
                    
                    # Ad Strength & Quality
                    "ad_strength": str(row.ad_group_ad.strength.name) if hasattr(row.ad_group_ad, 'strength') and row.ad_group_ad.strength else "NOT_AVAILABLE",
                    
                    # Review & Policy Status
                    "review_status": str(row.ad_group_ad.policy_summary.review_status.name) if hasattr(row.ad_group_ad, 'policy_summary') else "UNKNOWN",
                    "approval_status": str(row.ad_group_ad.policy_summary.approval_status.name) if hasattr(row.ad_group_ad, 'policy_summary') else "UNKNOWN",
                    
                    # Performance
                    "performance": {
                        "clicks": int(row.metrics.clicks) if hasattr(row, 'metrics') else 0,
                        "impressions": int(row.metrics.impressions) if hasattr(row, 'metrics') else 0,
                        "ctr": f"{row.metrics.ctr:.2%}" if hasattr(row, 'metrics') and row.metrics.ctr else "0.00%",
                    }
                }
                
                # Add ad content details
                if row.ad_group_ad.ad.type_.name == "RESPONSIVE_SEARCH_AD":
                    headlines = [str(h.text) for h in row.ad_group_ad.ad.responsive_search_ad.headlines]
                    descriptions = [str(d.text) for d in row.ad_group_ad.ad.responsive_search_ad.descriptions]
                    
                    ad_data["ad_content"] = {
                        "headlines": headlines,
                        "descriptions": descriptions,
                        "display_path1": str(row.ad_group_ad.ad.responsive_search_ad.path1) if row.ad_group_ad.ad.responsive_search_ad.path1 else "",
                        "display_path2": str(row.ad_group_ad.ad.responsive_search_ad.path2) if row.ad_group_ad.ad.responsive_search_ad.path2 else "",
                        "final_urls": [str(url) for url in row.ad_group_ad.ad.final_urls],
                        "headline_count": len(headlines),
                        "description_count": len(descriptions),
                    }
                    
                    # Add strength analysis
                    ad_data["strength_analysis"] = {
                        "headline_diversity": len(set(headlines)),
                        "description_diversity": len(set(descriptions)),
                        "min_headlines_met": len(headlines) >= 3,
                        "optimal_headlines": len(headlines) >= 8,
                        "min_descriptions_met": len(descriptions) >= 2,
                        "optimal_descriptions": len(descriptions) >= 4,
                        "has_display_paths": bool(row.ad_group_ad.ad.responsive_search_ad.path1 or row.ad_group_ad.ad.responsive_search_ad.path2),
                    }
                
                ads_details.append(ad_data)
            
            # Summary statistics
            total_ads = len(ads_details)
            strength_summary = {}
            review_status_summary = {}
            
            for ad in ads_details:
                strength = ad["ad_strength"]
                review = ad["review_status"]
                
                strength_summary[strength] = strength_summary.get(strength, 0) + 1
                review_status_summary[review] = review_status_summary.get(review, 0) + 1
            
            return {
                "success": True,
                "total_ads": total_ads,
                "strength_summary": strength_summary,
                "review_status_summary": review_status_summary,
                "ads": ads_details,
                "recommendations": self._generate_ad_strength_recommendations(ads_details)
            }
            
        except GoogleAdsException as e:
            logger.error(f"Failed to get ad strength and review status: {e}")
            raise
    
    def _generate_ad_strength_recommendations(self, ads_details: List[Dict]) -> List[str]:
        """Generate recommendations to improve ad strength."""
        recommendations = []
        
        poor_ads = [ad for ad in ads_details if ad["ad_strength"] == "POOR"]
        
        if poor_ads:
            recommendations.append(f"🚨 {len(poor_ads)} ads have POOR strength ratings")
            
            for ad in poor_ads:
                if "strength_analysis" in ad:
                    analysis = ad["strength_analysis"]
                    ad_recs = []
                    
                    if not analysis["optimal_headlines"]:
                        ad_recs.append(f"Add more headlines ({analysis['headline_count']}/15 - aim for 8-15)")
                    
                    if not analysis["optimal_descriptions"]:
                        ad_recs.append(f"Add more descriptions ({analysis['description_count']}/4 - aim for 4)")
                    
                    if not analysis["has_display_paths"]:
                        ad_recs.append("Add display paths (path1/path2) for better visibility")
                    
                    if analysis["headline_diversity"] < analysis["headline_count"]:
                        ad_recs.append("Make headlines more unique/diverse")
                    
                    if ad_recs:
                        recommendations.append(f"  • Ad '{ad['ad_name']}': {', '.join(ad_recs)}")
        
        pending_ads = [ad for ad in ads_details if ad["review_status"] in ["UNDER_REVIEW", "PENDING"]]
        if pending_ads:
            recommendations.append(f"⏳ {len(pending_ads)} ads are pending review - performance data may be limited")
        
        return recommendations
