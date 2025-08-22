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
    
    async def compare_ad_performance(
        self,
        customer_id: str,
        ad_ids: List[str],
        ad_group_id: str,
        date_range: str = "LAST_30_DAYS"
    ) -> Dict[str, Any]:
        """Compare performance of multiple ads side-by-side."""
        try:
            client = self.auth_manager.get_client(customer_id)
            googleads_service = client.get_service("GoogleAdsService")
            
            # Build query to get detailed performance metrics
            ad_ids_str = ",".join(ad_ids)
            query = f"""
                SELECT
                    ad_group_ad.ad.id,
                    ad_group_ad.ad.name,
                    ad_group_ad.ad.responsive_search_ad.headlines,
                    ad_group_ad.ad.responsive_search_ad.descriptions,
                    ad_group_ad.strength,
                    ad_group_ad.status,
                    metrics.clicks,
                    metrics.impressions,
                    metrics.cost_micros,
                    metrics.conversions,
                    metrics.conversions_value,
                    metrics.ctr,
                    metrics.average_cpc,
                    metrics.cost_per_conversion,
                    ad_group.name,
                    campaign.name
                FROM ad_group_ad
                WHERE ad_group.id = {ad_group_id}
                AND ad_group_ad.ad.id IN ({ad_ids_str})
                AND segments.date DURING {date_range}
            """
            
            response = googleads_service.search(
                customer_id=customer_id, query=query
            )
            
            ads_comparison = []
            for row in response:
                # Calculate efficiency metrics
                clicks = int(row.metrics.clicks) if hasattr(row, 'metrics') else 0
                cost = row.metrics.cost_micros / 1_000_000 if hasattr(row, 'metrics') else 0
                conversions = float(row.metrics.conversions) if hasattr(row, 'metrics') else 0
                conversion_value = float(row.metrics.conversions_value) if hasattr(row, 'metrics') else 0
                
                # Calculate derived metrics
                cost_per_conversion = cost / conversions if conversions > 0 else 0
                roas = conversion_value / cost if cost > 0 else 0
                conversion_rate = (conversions / clicks * 100) if clicks > 0 else 0
                
                ad_data = {
                    "ad_id": str(row.ad_group_ad.ad.id),
                    "ad_name": str(row.ad_group_ad.ad.name) if row.ad_group_ad.ad.name else f"Ad {row.ad_group_ad.ad.id}",
                    "ad_strength": str(row.ad_group_ad.strength.name) if hasattr(row.ad_group_ad, 'strength') and row.ad_group_ad.strength else "NOT_AVAILABLE",
                    "status": str(row.ad_group_ad.status.name),
                    
                    # Core Performance Metrics
                    "performance": {
                        "clicks": clicks,
                        "impressions": int(row.metrics.impressions) if hasattr(row, 'metrics') else 0,
                        "cost": round(cost, 2),
                        "conversions": conversions,
                        "conversion_value": round(conversion_value, 2),
                        "ctr": f"{row.metrics.ctr:.2%}" if hasattr(row, 'metrics') and row.metrics.ctr else "0.00%",
                        "avg_cpc": row.metrics.average_cpc / 1_000_000 if hasattr(row, 'metrics') else 0,
                    },
                    
                    # Efficiency Metrics
                    "efficiency": {
                        "cost_per_conversion": round(cost_per_conversion, 2),
                        "roas": round(roas, 2),
                        "conversion_rate": f"{conversion_rate:.1f}%",
                        "efficiency_score": round((conversions * roas) / max(cost, 0.01), 2),  # Custom efficiency metric
                    },
                    
                    # Ad Content
                    "content_summary": {
                        "headline_count": len(row.ad_group_ad.ad.responsive_search_ad.headlines) if row.ad_group_ad.ad.responsive_search_ad.headlines else 0,
                        "description_count": len(row.ad_group_ad.ad.responsive_search_ad.descriptions) if row.ad_group_ad.ad.responsive_search_ad.descriptions else 0,
                        "first_headline": str(row.ad_group_ad.ad.responsive_search_ad.headlines[0].text) if row.ad_group_ad.ad.responsive_search_ad.headlines else "N/A",
                    }
                }
                ads_comparison.append(ad_data)
            
            # Sort by efficiency score for ranking
            ads_comparison.sort(key=lambda x: x["efficiency"]["efficiency_score"], reverse=True)
            
            # Generate comparison insights
            insights = self._generate_comparison_insights(ads_comparison)
            
            return {
                "success": True,
                "date_range": date_range,
                "ads_compared": len(ads_comparison),
                "comparison": ads_comparison,
                "insights": insights,
                "best_performer": ads_comparison[0] if ads_comparison else None,
                "worst_performer": ads_comparison[-1] if len(ads_comparison) > 1 else None,
            }
            
        except GoogleAdsException as e:
            logger.error(f"Failed to compare ad performance: {e}")
            raise
    
    async def get_ad_group_performance_ranking(
        self,
        customer_id: str,
        ad_group_id: str,
        date_range: str = "LAST_30_DAYS",
        sort_by: str = "efficiency_score"
    ) -> Dict[str, Any]:
        """Rank all ads in an ad group by performance metrics."""
        try:
            client = self.auth_manager.get_client(customer_id)
            googleads_service = client.get_service("GoogleAdsService")
            
            query = f"""
                SELECT
                    ad_group_ad.ad.id,
                    ad_group_ad.ad.name,
                    ad_group_ad.strength,
                    ad_group_ad.status,
                    metrics.clicks,
                    metrics.impressions,
                    metrics.cost_micros,
                    metrics.conversions,
                    metrics.conversions_value,
                    metrics.ctr,
                    metrics.average_cpc,
                    metrics.cost_per_conversion
                FROM ad_group_ad
                WHERE ad_group.id = {ad_group_id}
                AND segments.date DURING {date_range}
                AND ad_group_ad.status != 'REMOVED'
            """
            
            response = googleads_service.search(
                customer_id=customer_id, query=query
            )
            
            ads_ranking = []
            for row in response:
                clicks = int(row.metrics.clicks) if hasattr(row, 'metrics') else 0
                cost = row.metrics.cost_micros / 1_000_000 if hasattr(row, 'metrics') else 0
                conversions = float(row.metrics.conversions) if hasattr(row, 'metrics') else 0
                conversion_value = float(row.metrics.conversions_value) if hasattr(row, 'metrics') else 0
                
                # Calculate comprehensive efficiency metrics
                cost_per_conversion = cost / conversions if conversions > 0 else float('inf')
                roas = conversion_value / cost if cost > 0 else 0
                conversion_rate = (conversions / clicks * 100) if clicks > 0 else 0
                ctr = float(row.metrics.ctr) if hasattr(row, 'metrics') and row.metrics.ctr else 0
                
                # Custom efficiency score (higher is better)
                # Factors: CTR, conversion rate, ROAS, with cost efficiency
                efficiency_score = 0
                if clicks > 0 and cost > 0:
                    efficiency_score = (ctr * 10) + (conversion_rate * 5) + (roas * 2) + (100 / max(cost_per_conversion, 1))
                
                ad_data = {
                    "rank": 0,  # Will be set after sorting
                    "ad_id": str(row.ad_group_ad.ad.id),
                    "ad_name": str(row.ad_group_ad.ad.name) if row.ad_group_ad.ad.name else f"Ad {row.ad_group_ad.ad.id}",
                    "ad_strength": str(row.ad_group_ad.strength.name) if hasattr(row.ad_group_ad, 'strength') and row.ad_group_ad.strength else "NOT_AVAILABLE",
                    "status": str(row.ad_group_ad.status.name),
                    
                    # Performance metrics
                    "performance": {
                        "clicks": clicks,
                        "impressions": int(row.metrics.impressions) if hasattr(row, 'metrics') else 0,
                        "cost": round(cost, 2),
                        "conversions": conversions,
                        "conversion_value": round(conversion_value, 2),
                        "ctr": f"{ctr:.2%}",
                        "avg_cpc": row.metrics.average_cpc / 1_000_000 if hasattr(row, 'metrics') else 0,
                    },
                    
                    # Efficiency metrics
                    "efficiency": {
                        "cost_per_conversion": round(cost_per_conversion, 2) if cost_per_conversion != float('inf') else "N/A",
                        "roas": round(roas, 2),
                        "conversion_rate": f"{conversion_rate:.1f}%",
                        "efficiency_score": round(efficiency_score, 2),
                    }
                }
                ads_ranking.append(ad_data)
            
            # Sort by specified metric
            if sort_by == "ctr":
                ads_ranking.sort(key=lambda x: float(x["performance"]["ctr"].rstrip('%')), reverse=True)
            elif sort_by == "conversions":
                ads_ranking.sort(key=lambda x: x["performance"]["conversions"], reverse=True)
            elif sort_by == "roas":
                ads_ranking.sort(key=lambda x: x["efficiency"]["roas"], reverse=True)
            elif sort_by == "cost_per_conversion":
                ads_ranking.sort(key=lambda x: x["efficiency"]["cost_per_conversion"] if x["efficiency"]["cost_per_conversion"] != "N/A" else float('inf'))
            else:  # Default: efficiency_score
                ads_ranking.sort(key=lambda x: x["efficiency"]["efficiency_score"], reverse=True)
            
            # Add rank numbers
            for i, ad in enumerate(ads_ranking):
                ad["rank"] = i + 1
            
            # Generate ranking insights
            ranking_insights = []
            if len(ads_ranking) > 1:
                best = ads_ranking[0]
                worst = ads_ranking[-1]
                
                ranking_insights.append(f"🏆 Best Performer: '{best['ad_name']}' - {best['efficiency']['efficiency_score']} efficiency score")
                ranking_insights.append(f"🚨 Worst Performer: '{worst['ad_name']}' - {worst['efficiency']['efficiency_score']} efficiency score")
                
                # Performance gap analysis
                if best["efficiency"]["efficiency_score"] > 0 and worst["efficiency"]["efficiency_score"] >= 0:
                    performance_gap = best["efficiency"]["efficiency_score"] / max(worst["efficiency"]["efficiency_score"], 1)
                    ranking_insights.append(f"📊 Performance Gap: {performance_gap:.1f}x difference between best and worst")
                
                # Identify clear winners and losers
                winners = [ad for ad in ads_ranking if ad["efficiency"]["efficiency_score"] > 50]
                losers = [ad for ad in ads_ranking if ad["efficiency"]["efficiency_score"] < 10 and ad["performance"]["clicks"] > 10]
                
                if winners:
                    ranking_insights.append(f"✅ High Performers ({len(winners)}): Consider increasing budgets")
                if losers:
                    ranking_insights.append(f"❌ Low Performers ({len(losers)}): Consider pausing or optimizing")
            
            return {
                "success": True,
                "ad_group_id": ad_group_id,
                "date_range": date_range,
                "sorted_by": sort_by,
                "total_ads": len(ads_ranking),
                "ranking": ads_ranking,
                "insights": ranking_insights,
            }
            
        except GoogleAdsException as e:
            logger.error(f"Failed to get ad group performance ranking: {e}")
            raise
    
    async def identify_optimization_opportunities(
        self,
        customer_id: str,
        ad_group_id: Optional[str] = None,
        campaign_id: Optional[str] = None,
        date_range: str = "LAST_30_DAYS",
        min_clicks: int = 10
    ) -> Dict[str, Any]:
        """Identify specific optimization opportunities based on ad performance analysis."""
        try:
            client = self.auth_manager.get_client(customer_id)
            googleads_service = client.get_service("GoogleAdsService")
            
            query = f"""
                SELECT
                    ad_group_ad.ad.id,
                    ad_group_ad.ad.name,
                    ad_group_ad.strength,
                    ad_group_ad.status,
                    metrics.clicks,
                    metrics.impressions,
                    metrics.cost_micros,
                    metrics.conversions,
                    metrics.conversions_value,
                    metrics.ctr,
                    metrics.average_cpc,
                    metrics.cost_per_conversion,
                    ad_group.name,
                    ad_group.id,
                    campaign.name,
                    campaign.id
                FROM ad_group_ad
                WHERE segments.date DURING {date_range}
                AND ad_group_ad.status != 'REMOVED'
                AND metrics.clicks >= {min_clicks}
            """
            
            conditions = []
            if ad_group_id:
                conditions.append(f"ad_group.id = {ad_group_id}")
            if campaign_id:
                conditions.append(f"campaign.id = {campaign_id}")
            
            if conditions:
                query += " AND " + " AND ".join(conditions)
            
            response = googleads_service.search(
                customer_id=customer_id, query=query
            )
            
            ads_data = []
            total_cost = 0
            total_conversions = 0
            
            for row in response:
                clicks = int(row.metrics.clicks) if hasattr(row, 'metrics') else 0
                cost = row.metrics.cost_micros / 1_000_000 if hasattr(row, 'metrics') else 0
                conversions = float(row.metrics.conversions) if hasattr(row, 'metrics') else 0
                conversion_value = float(row.metrics.conversions_value) if hasattr(row, 'metrics') else 0
                ctr = float(row.metrics.ctr) if hasattr(row, 'metrics') and row.metrics.ctr else 0
                
                total_cost += cost
                total_conversions += conversions
                
                cost_per_conversion = cost / conversions if conversions > 0 else float('inf')
                roas = conversion_value / cost if cost > 0 else 0
                conversion_rate = (conversions / clicks * 100) if clicks > 0 else 0
                
                ads_data.append({
                    "ad_id": str(row.ad_group_ad.ad.id),
                    "ad_name": str(row.ad_group_ad.ad.name) if row.ad_group_ad.ad.name else f"Ad {row.ad_group_ad.ad.id}",
                    "ad_group_name": str(row.ad_group.name),
                    "campaign_name": str(row.campaign.name),
                    "strength": str(row.ad_group_ad.strength.name) if hasattr(row.ad_group_ad, 'strength') and row.ad_group_ad.strength else "NOT_AVAILABLE",
                    "clicks": clicks,
                    "cost": cost,
                    "conversions": conversions,
                    "conversion_value": conversion_value,
                    "ctr": ctr,
                    "cost_per_conversion": cost_per_conversion,
                    "roas": roas,
                    "conversion_rate": conversion_rate,
                })
            
            # Calculate averages for comparison
            avg_cost_per_conversion = total_cost / total_conversions if total_conversions > 0 else 0
            avg_ctr = sum(ad["ctr"] for ad in ads_data) / len(ads_data) if ads_data else 0
            avg_roas = sum(ad["roas"] for ad in ads_data) / len(ads_data) if ads_data else 0
            
            # Identify optimization opportunities
            opportunities = {
                "pause_recommendations": [],
                "optimize_recommendations": [],
                "scale_recommendations": [],
                "strength_improvements": []
            }
            
            for ad in ads_data:
                # Pause recommendations (poor performers)
                if ad["cost_per_conversion"] > avg_cost_per_conversion * 2 and ad["conversions"] > 0:
                    opportunities["pause_recommendations"].append({
                        "ad_id": ad["ad_id"],
                        "ad_name": ad["ad_name"],
                        "reason": f"High cost per conversion: ${ad['cost_per_conversion']:.2f} vs avg ${avg_cost_per_conversion:.2f}",
                        "action": "Consider pausing - spending too much per conversion"
                    })
                
                # Scale recommendations (high performers)  
                if ad["roas"] > avg_roas * 1.5 and ad["conversions"] >= 3:
                    opportunities["scale_recommendations"].append({
                        "ad_id": ad["ad_id"],
                        "ad_name": ad["ad_name"],
                        "reason": f"High ROAS: {ad['roas']:.2f}x vs avg {avg_roas:.2f}x",
                        "action": "Consider increasing budget allocation - strong performer"
                    })
                
                # Optimize recommendations (medium performers)
                if avg_cost_per_conversion * 0.8 < ad["cost_per_conversion"] < avg_cost_per_conversion * 1.5:
                    opportunities["optimize_recommendations"].append({
                        "ad_id": ad["ad_id"], 
                        "ad_name": ad["ad_name"],
                        "reason": f"Medium performer with optimization potential",
                        "action": "Consider A/B testing different headlines or descriptions"
                    })
                
                # Strength improvements
                if ad["strength"] == "POOR":
                    opportunities["strength_improvements"].append({
                        "ad_id": ad["ad_id"],
                        "ad_name": ad["ad_name"],
                        "reason": "Poor ad strength rating",
                        "action": "Add more headlines, descriptions, or display paths"
                    })
            
            return {
                "success": True,
                "date_range": date_range,
                "total_ads_analyzed": len(ads_data),
                "account_averages": {
                    "avg_cost_per_conversion": round(avg_cost_per_conversion, 2),
                    "avg_ctr": f"{avg_ctr:.2%}",
                    "avg_roas": round(avg_roas, 2),
                },
                "opportunities": opportunities,
                "summary": {
                    "pause_candidates": len(opportunities["pause_recommendations"]),
                    "scale_candidates": len(opportunities["scale_recommendations"]),
                    "optimize_candidates": len(opportunities["optimize_recommendations"]),
                    "strength_improvements_needed": len(opportunities["strength_improvements"]),
                }
            }
            
        except GoogleAdsException as e:
            logger.error(f"Failed to identify optimization opportunities: {e}")
            raise
    
    async def calculate_roas_by_ad(
        self,
        customer_id: str,
        ad_group_id: Optional[str] = None,
        campaign_id: Optional[str] = None,
        date_range: str = "LAST_30_DAYS",
        min_cost: float = 5.0
    ) -> Dict[str, Any]:
        """Calculate Return on Ad Spend (ROAS) for each ad with detailed breakdown."""
        try:
            client = self.auth_manager.get_client(customer_id)
            googleads_service = client.get_service("GoogleAdsService")
            
            query = f"""
                SELECT
                    ad_group_ad.ad.id,
                    ad_group_ad.ad.name,
                    metrics.cost_micros,
                    metrics.conversions_value,
                    metrics.conversions,
                    metrics.clicks,
                    metrics.impressions,
                    ad_group.name,
                    ad_group.id,
                    campaign.name,
                    campaign.id
                FROM ad_group_ad
                WHERE segments.date DURING {date_range}
                AND ad_group_ad.status != 'REMOVED'
                AND metrics.cost_micros >= {int(min_cost * 1_000_000)}
            """
            
            conditions = []
            if ad_group_id:
                conditions.append(f"ad_group.id = {ad_group_id}")
            if campaign_id:
                conditions.append(f"campaign.id = {campaign_id}")
            
            if conditions:
                query += " AND " + " AND ".join(conditions)
            
            query += " ORDER BY metrics.conversions_value DESC"
            
            response = googleads_service.search(
                customer_id=customer_id, query=query
            )
            
            roas_analysis = []
            total_cost = 0
            total_value = 0
            
            for row in response:
                cost = row.metrics.cost_micros / 1_000_000
                conversion_value = float(row.metrics.conversions_value)
                conversions = float(row.metrics.conversions)
                
                total_cost += cost
                total_value += conversion_value
                
                roas = conversion_value / cost if cost > 0 else 0
                
                # ROAS category
                roas_category = "Excellent" if roas >= 4 else "Good" if roas >= 2 else "Poor" if roas > 0 else "No Revenue"
                
                roas_data = {
                    "ad_id": str(row.ad_group_ad.ad.id),
                    "ad_name": str(row.ad_group_ad.ad.name) if row.ad_group_ad.ad.name else f"Ad {row.ad_group_ad.ad.id}",
                    "ad_group_name": str(row.ad_group.name),
                    "campaign_name": str(row.campaign.name),
                    "cost": round(cost, 2),
                    "conversion_value": round(conversion_value, 2),
                    "conversions": conversions,
                    "roas": round(roas, 2),
                    "roas_category": roas_category,
                    "revenue_per_click": round(conversion_value / max(row.metrics.clicks, 1), 2),
                }
                roas_analysis.append(roas_data)
            
            # Calculate overall ROAS
            overall_roas = total_value / total_cost if total_cost > 0 else 0
            
            # Categorize ads by ROAS performance
            excellent_ads = [ad for ad in roas_analysis if ad["roas"] >= 4]
            good_ads = [ad for ad in roas_analysis if 2 <= ad["roas"] < 4]
            poor_ads = [ad for ad in roas_analysis if 0 < ad["roas"] < 2]
            no_revenue_ads = [ad for ad in roas_analysis if ad["roas"] == 0]
            
            return {
                "success": True,
                "date_range": date_range,
                "overall_roas": round(overall_roas, 2),
                "total_cost": round(total_cost, 2),
                "total_revenue": round(total_value, 2),
                "ads_analyzed": len(roas_analysis),
                
                "roas_breakdown": {
                    "excellent_ads": len(excellent_ads),  # ROAS >= 4x
                    "good_ads": len(good_ads),           # ROAS 2-4x
                    "poor_ads": len(poor_ads),           # ROAS 0-2x
                    "no_revenue_ads": len(no_revenue_ads), # ROAS = 0
                },
                
                "detailed_analysis": roas_analysis,
                
                "recommendations": [
                    f"🎯 Focus budget on {len(excellent_ads)} excellent performers (ROAS ≥ 4x)" if excellent_ads else "No excellent performers found",
                    f"⚠️ Review {len(poor_ads)} poor performers (ROAS < 2x)" if poor_ads else "No poor performers identified",
                    f"🚨 Consider pausing {len(no_revenue_ads)} ads with no revenue" if no_revenue_ads else "All ads generating revenue",
                ]
            }
            
        except GoogleAdsException as e:
            logger.error(f"Failed to calculate ROAS by ad: {e}")
            raise
    
    def _generate_comparison_insights(self, ads_comparison: List[Dict]) -> List[str]:
        """Generate insights from ad comparison data."""
        insights = []
        
        if len(ads_comparison) < 2:
            return ["Need at least 2 ads to generate comparison insights"]
        
        best = ads_comparison[0]
        worst = ads_comparison[-1]
        
        # Performance gap insights
        if best["efficiency"]["efficiency_score"] > worst["efficiency"]["efficiency_score"]:
            gap = best["efficiency"]["efficiency_score"] / max(worst["efficiency"]["efficiency_score"], 1)
            insights.append(f"📊 {gap:.1f}x performance difference between best and worst ads")
        
        # CTR comparison
        best_ctr = float(best["performance"]["ctr"].rstrip('%'))
        worst_ctr = float(worst["performance"]["ctr"].rstrip('%'))
        if best_ctr > worst_ctr * 1.5:
            insights.append(f"🎯 CTR Leader: '{best['ad_name']}' ({best['performance']['ctr']}) vs '{worst['ad_name']}' ({worst['performance']['ctr']})")
        
        # Cost efficiency
        if best["efficiency"]["cost_per_conversion"] != "N/A" and worst["efficiency"]["cost_per_conversion"] != "N/A":
            if worst["efficiency"]["cost_per_conversion"] > best["efficiency"]["cost_per_conversion"] * 2:
                insights.append(f"💰 Cost Efficiency Gap: '{worst['ad_name']}' costs {worst['efficiency']['cost_per_conversion']/best['efficiency']['cost_per_conversion']:.1f}x more per conversion")
        
        # Strength correlation
        strength_performance = {}
        for ad in ads_comparison:
            strength = ad["ad_strength"]
            if strength not in strength_performance:
                strength_performance[strength] = []
            strength_performance[strength].append(ad["efficiency"]["efficiency_score"])
        
        # Check if higher strength correlates with better performance
        if "EXCELLENT" in strength_performance and "POOR" in strength_performance:
            excellent_avg = sum(strength_performance["EXCELLENT"]) / len(strength_performance["EXCELLENT"])
            poor_avg = sum(strength_performance["POOR"]) / len(strength_performance["POOR"])
            if excellent_avg > poor_avg * 1.3:
                insights.append(f"📈 Strength Correlation: Excellent-rated ads perform {excellent_avg/poor_avg:.1f}x better on average")
        
        return insights
    
    async def analyze_ad_strength_trends(
        self,
        customer_id: str,
        ad_group_id: str,
        current_date_range: str = "LAST_7_DAYS",
        comparison_date_range: str = "LAST_30_DAYS"
    ) -> Dict[str, Any]:
        """Analyze how ad strength correlates with performance over time."""
        try:
            client = self.auth_manager.get_client(customer_id)
            googleads_service = client.get_service("GoogleAdsService")
            
            # Get current period data
            current_query = f"""
                SELECT
                    ad_group_ad.ad.id,
                    ad_group_ad.ad.name,
                    ad_group_ad.strength,
                    metrics.clicks,
                    metrics.impressions,
                    metrics.cost_micros,
                    metrics.conversions,
                    metrics.ctr
                FROM ad_group_ad
                WHERE ad_group.id = {ad_group_id}
                AND segments.date DURING {current_date_range}
                AND ad_group_ad.status != 'REMOVED'
            """
            
            # Get comparison period data
            comparison_query = f"""
                SELECT
                    ad_group_ad.ad.id,
                    ad_group_ad.ad.name,
                    ad_group_ad.strength,
                    metrics.clicks,
                    metrics.impressions,
                    metrics.cost_micros,
                    metrics.conversions,
                    metrics.ctr
                FROM ad_group_ad
                WHERE ad_group.id = {ad_group_id}
                AND segments.date DURING {comparison_date_range}
                AND ad_group_ad.status != 'REMOVED'
            """
            
            current_response = googleads_service.search(customer_id=customer_id, query=current_query)
            comparison_response = googleads_service.search(customer_id=customer_id, query=comparison_query)
            
            # Process current data
            current_data = {}
            for row in current_response:
                ad_id = str(row.ad_group_ad.ad.id)
                current_data[ad_id] = {
                    "ad_name": str(row.ad_group_ad.ad.name) if row.ad_group_ad.ad.name else f"Ad {ad_id}",
                    "strength": str(row.ad_group_ad.strength.name) if hasattr(row.ad_group_ad, 'strength') and row.ad_group_ad.strength else "NOT_AVAILABLE",
                    "clicks": int(row.metrics.clicks) if hasattr(row, 'metrics') else 0,
                    "ctr": float(row.metrics.ctr) if hasattr(row, 'metrics') and row.metrics.ctr else 0,
                    "conversions": float(row.metrics.conversions) if hasattr(row, 'metrics') else 0,
                    "cost": row.metrics.cost_micros / 1_000_000 if hasattr(row, 'metrics') else 0,
                }
            
            # Process comparison data
            comparison_data = {}
            for row in comparison_response:
                ad_id = str(row.ad_group_ad.ad.id)
                comparison_data[ad_id] = {
                    "clicks": int(row.metrics.clicks) if hasattr(row, 'metrics') else 0,
                    "ctr": float(row.metrics.ctr) if hasattr(row, 'metrics') and row.metrics.ctr else 0,
                    "conversions": float(row.metrics.conversions) if hasattr(row, 'metrics') else 0,
                    "cost": row.metrics.cost_micros / 1_000_000 if hasattr(row, 'metrics') else 0,
                }
            
            # Calculate trends
            trends_analysis = []
            for ad_id, current in current_data.items():
                if ad_id in comparison_data:
                    comparison = comparison_data[ad_id]
                    
                    # Calculate percentage changes
                    ctr_change = ((current["ctr"] - comparison["ctr"]) / max(comparison["ctr"], 0.001)) * 100
                    conversion_change = ((current["conversions"] - comparison["conversions"]) / max(comparison["conversions"], 1)) * 100
                    
                    trends_analysis.append({
                        "ad_id": ad_id,
                        "ad_name": current["ad_name"],
                        "current_strength": current["strength"],
                        "current_performance": {
                            "ctr": f"{current['ctr']:.2%}",
                            "conversions": current["conversions"],
                            "cost": round(current["cost"], 2),
                        },
                        "trends": {
                            "ctr_change": f"{ctr_change:+.1f}%",
                            "conversion_change": f"{conversion_change:+.1f}%",
                            "trending_direction": "improving" if ctr_change > 10 and conversion_change > 20 else "declining" if ctr_change < -10 or conversion_change < -20 else "stable",
                        }
                    })
            
            # Strength performance correlation
            strength_performance = {}
            for ad in trends_analysis:
                strength = ad["current_strength"]
                if strength not in strength_performance:
                    strength_performance[strength] = {
                        "count": 0,
                        "avg_ctr": 0,
                        "avg_conversions": 0,
                        "total_ctr": 0,
                        "total_conversions": 0
                    }
                
                strength_performance[strength]["count"] += 1
                ctr_val = float(ad["current_performance"]["ctr"].rstrip('%'))
                strength_performance[strength]["total_ctr"] += ctr_val
                strength_performance[strength]["total_conversions"] += ad["current_performance"]["conversions"]
            
            # Calculate averages
            for strength, data in strength_performance.items():
                if data["count"] > 0:
                    data["avg_ctr"] = data["total_ctr"] / data["count"]
                    data["avg_conversions"] = data["total_conversions"] / data["count"]
            
            return {
                "success": True,
                "ad_group_id": ad_group_id,
                "current_period": current_date_range,
                "comparison_period": comparison_date_range,
                "trends_analysis": trends_analysis,
                "strength_performance_correlation": strength_performance,
                "insights": [
                    f"📊 Analyzed {len(trends_analysis)} ads across two time periods",
                    f"📈 {len([ad for ad in trends_analysis if ad['trends']['trending_direction'] == 'improving'])} ads trending upward",
                    f"📉 {len([ad for ad in trends_analysis if ad['trends']['trending_direction'] == 'declining'])} ads trending downward",
                ]
            }
            
        except GoogleAdsException as e:
            logger.error(f"Failed to analyze ad strength trends: {e}")
            raise
