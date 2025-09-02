"""Keyword management tools for Google Ads API v21."""

from typing import Any, Dict, List, Optional
import structlog

from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException

from .utils import micros_to_currency

logger = structlog.get_logger(__name__)


class KeywordTools:
    """Keyword management tools."""
    
    def __init__(self, auth_manager, error_handler):
        self.auth_manager = auth_manager
        self.error_handler = error_handler
        
    async def add_keywords(
        self,
        customer_id: str,
        ad_group_id: str,
        keywords: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Add keywords to an ad group.
        
        Keywords format:
        [
            {"text": "offshore team monitoring", "match_type": "BROAD", "cpc_bid_micros": 2000000},
            {"text": "remote work verification", "match_type": "PHRASE"},
            ...
        ]
        """
        try:
            client = self.auth_manager.get_client(customer_id)
            ad_group_criterion_service = client.get_service("AdGroupCriterionService")
            
            operations = []
            for keyword_data in keywords:
                # Create ad group criterion operation
                operation = client.get_type("AdGroupCriterionOperation")
                criterion = operation.create
                
                # Set ad group
                criterion.ad_group = client.get_service("AdGroupService").ad_group_path(
                    customer_id, ad_group_id
                )
                
                # Set status
                criterion.status = client.enums.AdGroupCriterionStatusEnum.ENABLED
                
                # Create keyword info
                criterion.keyword.text = keyword_data["text"]
                
                # Set match type (default to BROAD if not specified)
                match_type = keyword_data.get("match_type", "BROAD").upper()
                if match_type == "BROAD":
                    criterion.keyword.match_type = client.enums.KeywordMatchTypeEnum.BROAD
                elif match_type == "PHRASE":
                    criterion.keyword.match_type = client.enums.KeywordMatchTypeEnum.PHRASE
                elif match_type == "EXACT":
                    criterion.keyword.match_type = client.enums.KeywordMatchTypeEnum.EXACT
                else:
                    criterion.keyword.match_type = client.enums.KeywordMatchTypeEnum.BROAD
                
                # Set CPC bid if provided
                if "cpc_bid_micros" in keyword_data:
                    criterion.cpc_bid_micros = keyword_data["cpc_bid_micros"]
                
                operations.append(operation)
            
            # Execute all operations
            response = ad_group_criterion_service.mutate_ad_group_criteria(
                customer_id=customer_id,
                operations=operations,
            )
            
            # Extract results
            added_keywords = []
            for i, result in enumerate(response.results):
                keyword_id = result.resource_name.split("/")[-1]
                added_keywords.append({
                    "keyword_id": keyword_id,
                    "text": keywords[i]["text"],
                    "match_type": keywords[i].get("match_type", "BROAD"),
                    "cpc_bid": micros_to_currency(keywords[i].get("cpc_bid_micros", 0)),
                    "resource_name": result.resource_name
                })
            
            logger.info(
                f"Added keywords to ad group",
                customer_id=customer_id,
                ad_group_id=ad_group_id,
                keywords_count=len(added_keywords)
            )
            
            return {
                "success": True,
                "keywords": added_keywords,
                "count": len(added_keywords),
                "ad_group_id": ad_group_id
            }
            
        except GoogleAdsException as e:
            logger.error(f"Failed to add keywords: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_type": "GoogleAdsException"
            }
        except Exception as e:
            logger.error(f"Unexpected error adding keywords: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_type": "UnexpectedError"
            }
    
    async def add_negative_keywords(
        self,
        customer_id: str,
        keywords: List[str],
        campaign_id: Optional[str] = None,
        ad_group_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Add negative keywords at campaign or ad group level.
        
        IMPORTANT SYNTAX:
        - keywords: Array of strings like ['free', 'cheap', 'demo']
        - Use EITHER campaign_id OR ad_group_id, not both
        - Tool creates proper KeywordInfo protobuf objects automatically
        
        Example usage:
        - Campaign level: add_negative_keywords(customer_id='123', keywords=['free', 'cheap'], campaign_id='456')
        - Ad group level: add_negative_keywords(customer_id='123', keywords=['trial'], ad_group_id='789')
        """
        try:
            client = self.auth_manager.get_client(customer_id)
            
            if campaign_id:
                # Campaign-level negative keywords
                campaign_criterion_service = client.get_service("CampaignCriterionService")
                operations = []
                
                for keyword_text in keywords:
                    operation = client.get_type("CampaignCriterionOperation")
                    criterion = operation.create
                    
                    criterion.campaign = client.get_service("CampaignService").campaign_path(
                        customer_id, campaign_id
                    )
                    criterion.negative = True
                    
                    # Create KeywordInfo object properly
                    keyword_info = client.get_type("KeywordInfo")
                    keyword_info.text = keyword_text
                    keyword_info.match_type = client.enums.KeywordMatchTypeEnum.BROAD
                    criterion.keyword = keyword_info
                    
                    operations.append(operation)
                
                response = campaign_criterion_service.mutate_campaign_criteria(
                    customer_id=customer_id,
                    operations=operations,
                )
                
                level = "campaign"
                level_id = campaign_id
                
            elif ad_group_id:
                # Ad group-level negative keywords
                ad_group_criterion_service = client.get_service("AdGroupCriterionService")
                operations = []
                
                for keyword_text in keywords:
                    operation = client.get_type("AdGroupCriterionOperation")
                    criterion = operation.create
                    
                    criterion.ad_group = client.get_service("AdGroupService").ad_group_path(
                        customer_id, ad_group_id
                    )
                    criterion.negative = True
                    
                    # Create KeywordInfo object properly
                    keyword_info = client.get_type("KeywordInfo")
                    keyword_info.text = keyword_text
                    keyword_info.match_type = client.enums.KeywordMatchTypeEnum.BROAD
                    criterion.keyword = keyword_info
                    
                    operations.append(operation)
                
                response = ad_group_criterion_service.mutate_ad_group_criteria(
                    customer_id=customer_id,
                    operations=operations,
                )
                
                level = "ad_group"
                level_id = ad_group_id
                
            else:
                return {
                    "success": False,
                    "error": "Must specify either campaign_id or ad_group_id",
                    "error_type": "ValidationError"
                }
            
            # Extract results
            added_negatives = []
            for i, result in enumerate(response.results):
                negative_id = result.resource_name.split("/")[-1]
                added_negatives.append({
                    "negative_keyword_id": negative_id,
                    "text": keywords[i],
                    "level": level,
                    "resource_name": result.resource_name
                })
            
            logger.info(
                f"Added negative keywords at {level} level",
                customer_id=customer_id,
                level_id=level_id,
                keywords_count=len(added_negatives)
            )
            
            return {
                "success": True,
                "negative_keywords": added_negatives,
                "count": len(added_negatives),
                "level": level,
                f"{level}_id": level_id
            }
            
        except GoogleAdsException as e:
            logger.error(f"Failed to add negative keywords: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_type": "GoogleAdsException"
            }
        except Exception as e:
            logger.error(f"Unexpected error adding negative keywords: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_type": "UnexpectedError"
            }
    
    async def list_keywords(
        self,
        customer_id: str,
        ad_group_id: Optional[str] = None,
        campaign_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """List keywords with performance data."""
        try:
            client = self.auth_manager.get_client(customer_id)
            googleads_service = client.get_service("GoogleAdsService")
            
            # Build query
            query = """
                SELECT
                    ad_group_criterion.criterion_id,
                    ad_group_criterion.keyword.text,
                    ad_group_criterion.keyword.match_type,
                    ad_group_criterion.status,
                    ad_group_criterion.cpc_bid_micros,
                    ad_group_criterion.negative,
                    ad_group.id,
                    ad_group.name,
                    campaign.id,
                    campaign.name,
                    metrics.clicks,
                    metrics.impressions,
                    metrics.cost_micros,
                    metrics.conversions
                FROM ad_group_criterion
                WHERE ad_group_criterion.type = KEYWORD
            """
            
            # Add filters
            conditions = []
            if ad_group_id:
                conditions.append(f"ad_group.id = {ad_group_id}")
            if campaign_id:
                conditions.append(f"campaign.id = {campaign_id}")
                
            if conditions:
                query += " AND " + " AND ".join(conditions)
                
            query += " AND segments.date DURING LAST_30_DAYS"
                
            response = googleads_service.search(
                customer_id=customer_id, query=query
            )
            
            keywords = []
            for row in response:
                keyword_data = {
                    "keyword_id": str(row.ad_group_criterion.criterion_id),
                    "text": str(row.ad_group_criterion.keyword.text),
                    "match_type": str(row.ad_group_criterion.keyword.match_type.name),
                    "status": str(row.ad_group_criterion.status.name),
                    "negative": row.ad_group_criterion.negative,
                    "cpc_bid": micros_to_currency(row.ad_group_criterion.cpc_bid_micros),
                    "ad_group_id": str(row.ad_group.id),
                    "ad_group_name": str(row.ad_group.name),
                    "campaign_id": str(row.campaign.id),
                    "campaign_name": str(row.campaign.name)
                }
                
                # Add performance metrics if available
                if hasattr(row, 'metrics'):
                    keyword_data["metrics"] = {
                        "clicks": int(row.metrics.clicks),
                        "impressions": int(row.metrics.impressions),
                        "cost": micros_to_currency(row.metrics.cost_micros),
                        "conversions": float(row.metrics.conversions)
                    }
                
                keywords.append(keyword_data)
            
            return {
                "success": True,
                "keywords": keywords,
                "count": len(keywords),
                "filters": {
                    "ad_group_id": ad_group_id,
                    "campaign_id": campaign_id
                }
            }
            
        except GoogleAdsException as e:
            logger.error(f"Failed to list keywords: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_type": "GoogleAdsException"
            }
        except Exception as e:
            logger.error(f"Unexpected error listing keywords: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_type": "UnexpectedError"
            }
    
    async def update_keyword_bid(
        self,
        customer_id: str,
        ad_group_id: str,
        keyword_id: str,
        cpc_bid_micros: int
    ) -> Dict[str, Any]:
        """Update the CPC bid for a specific keyword."""
        try:
            client = self.auth_manager.get_client(customer_id)
            ad_group_criterion_service = client.get_service("AdGroupCriterionService")
            
            # Create update operation
            ad_group_criterion_operation = client.get_type("AdGroupCriterionOperation")
            criterion = ad_group_criterion_operation.update
            
            # Set the criterion resource name
            criterion.resource_name = client.get_service("AdGroupCriterionService").ad_group_criterion_path(
                customer_id, ad_group_id, keyword_id
            )
            
            # Update the CPC bid
            criterion.cpc_bid_micros = cpc_bid_micros
            
            # Set update mask
            from google.protobuf.field_mask_pb2 import FieldMask
            ad_group_criterion_operation.update_mask = FieldMask(paths=["cpc_bid_micros"])
            
            # Execute the update
            response = ad_group_criterion_service.mutate_ad_group_criteria(
                customer_id=customer_id,
                operations=[ad_group_criterion_operation]
            )
            
            return {
                "success": True,
                "keyword_id": keyword_id,
                "new_cpc_bid": micros_to_currency(cpc_bid_micros),
                "new_cpc_bid_micros": cpc_bid_micros,
                "resource_name": response.results[0].resource_name,
            }
            
        except GoogleAdsException as e:
            logger.error(f"Failed to update keyword bid: {e}")
            raise
    
    async def delete_keyword(
        self,
        customer_id: str,
        ad_group_id: str,
        keyword_id: str
    ) -> Dict[str, Any]:
        """Delete a specific keyword."""
        try:
            client = self.auth_manager.get_client(customer_id)
            ad_group_criterion_service = client.get_service("AdGroupCriterionService")
            
            # Create remove operation
            ad_group_criterion_operation = client.get_type("AdGroupCriterionOperation")
            ad_group_criterion_operation.remove = client.get_service("AdGroupCriterionService").ad_group_criterion_path(
                customer_id, ad_group_id, keyword_id
            )
            
            # Execute the removal
            response = ad_group_criterion_service.mutate_ad_group_criteria(
                customer_id=customer_id,
                operations=[ad_group_criterion_operation]
            )
            
            return {
                "success": True,
                "keyword_id": keyword_id,
                "message": "Keyword deleted successfully",
                "resource_name": response.results[0].resource_name,
            }
            
        except GoogleAdsException as e:
            logger.error(f"Failed to delete keyword: {e}")
            raise
    
    async def pause_keyword(
        self,
        customer_id: str,
        ad_group_id: str,
        keyword_id: str
    ) -> Dict[str, Any]:
        """Pause a specific keyword."""
        try:
            client = self.auth_manager.get_client(customer_id)
            ad_group_criterion_service = client.get_service("AdGroupCriterionService")
            
            # Create update operation
            ad_group_criterion_operation = client.get_type("AdGroupCriterionOperation")
            criterion = ad_group_criterion_operation.update
            
            # Set the criterion resource name
            criterion.resource_name = client.get_service("AdGroupCriterionService").ad_group_criterion_path(
                customer_id, ad_group_id, keyword_id
            )
            
            # Set status to paused
            criterion.status = client.enums.AdGroupCriterionStatusEnum.PAUSED
            
            # Set update mask
            from google.protobuf.field_mask_pb2 import FieldMask
            ad_group_criterion_operation.update_mask = FieldMask(paths=["status"])
            
            # Execute the update
            response = ad_group_criterion_service.mutate_ad_group_criteria(
                customer_id=customer_id,
                operations=[ad_group_criterion_operation]
            )
            
            return {
                "success": True,
                "keyword_id": keyword_id,
                "status": "PAUSED",
                "message": "Keyword paused successfully",
                "resource_name": response.results[0].resource_name,
            }
            
        except GoogleAdsException as e:
            logger.error(f"Failed to pause keyword: {e}")
            raise
    
    async def enable_keyword(
        self,
        customer_id: str,
        ad_group_id: str,
        keyword_id: str
    ) -> Dict[str, Any]:
        """Enable a paused keyword."""
        try:
            client = self.auth_manager.get_client(customer_id)
            ad_group_criterion_service = client.get_service("AdGroupCriterionService")
            
            # Create update operation
            ad_group_criterion_operation = client.get_type("AdGroupCriterionOperation")
            criterion = ad_group_criterion_operation.update
            
            # Set the criterion resource name
            criterion.resource_name = client.get_service("AdGroupCriterionService").ad_group_criterion_path(
                customer_id, ad_group_id, keyword_id
            )
            
            # Set status to enabled
            criterion.status = client.enums.AdGroupCriterionStatusEnum.ENABLED
            
            # Set update mask
            from google.protobuf.field_mask_pb2 import FieldMask
            ad_group_criterion_operation.update_mask = FieldMask(paths=["status"])
            
            # Execute the update
            response = ad_group_criterion_service.mutate_ad_group_criteria(
                customer_id=customer_id,
                operations=[ad_group_criterion_operation]
            )
            
            return {
                "success": True,
                "keyword_id": keyword_id,
                "status": "ENABLED",
                "message": "Keyword enabled successfully",
                "resource_name": response.results[0].resource_name,
            }
            
        except GoogleAdsException as e:
            logger.error(f"Failed to enable keyword: {e}")
            raise
    
    async def get_keyword_performance(
        self,
        customer_id: str,
        ad_group_id: Optional[str] = None,
        date_range: str = "LAST_30_DAYS"
    ) -> Dict[str, Any]:
        """Get keyword performance data with quality scores."""
        try:
            client = self.auth_manager.get_client(customer_id)
            googleads_service = client.get_service("GoogleAdsService")
            
            query = """
                SELECT
                    ad_group_criterion.criterion_id,
                    ad_group_criterion.keyword.text,
                    ad_group_criterion.keyword.match_type,
                    ad_group_criterion.status,
                    ad_group_criterion.cpc_bid_micros,
                    ad_group_criterion.quality_info.quality_score,
                    metrics.clicks,
                    metrics.impressions,
                    metrics.cost_micros,
                    metrics.conversions,
                    metrics.ctr,
                    metrics.average_cpc,
                    ad_group.name,
                    ad_group.id
                FROM keyword_view
            """
            
            conditions = [f"segments.date DURING {date_range}"]
            if ad_group_id:
                conditions.append(f"ad_group.id = {ad_group_id}")
            
            query += " WHERE " + " AND ".join(conditions)
            query += " ORDER BY metrics.clicks DESC"
            
            response = googleads_service.search(
                customer_id=customer_id,
                query=query
            )
            
            keywords = []
            for row in response:
                keyword_data = {
                    "keyword_id": str(row.ad_group_criterion.criterion_id),
                    "text": str(row.ad_group_criterion.keyword.text),
                    "match_type": str(row.ad_group_criterion.keyword.match_type.name),
                    "status": str(row.ad_group_criterion.status.name),
                    "cpc_bid": micros_to_currency(row.ad_group_criterion.cpc_bid_micros),
                    "ad_group_name": str(row.ad_group.name),
                    "ad_group_id": str(row.ad_group.id),
                    "quality_score": row.ad_group_criterion.quality_info.quality_score or "N/A",
                    "performance": {
                        "clicks": int(row.metrics.clicks) if hasattr(row, 'metrics') else 0,
                        "impressions": int(row.metrics.impressions) if hasattr(row, 'metrics') else 0,
                        "cost": micros_to_currency(row.metrics.cost_micros) if hasattr(row, 'metrics') else 0,
                        "conversions": float(row.metrics.conversions) if hasattr(row, 'metrics') else 0,
                        "ctr": f"{row.metrics.ctr:.2%}" if hasattr(row, 'metrics') and row.metrics.ctr else "0.00%",
                        "avg_cpc": micros_to_currency(row.metrics.average_cpc) if hasattr(row, 'metrics') else 0,
                    }
                }
                keywords.append(keyword_data)
            
            return {
                "success": True,
                "date_range": date_range,
                "ad_group_id": ad_group_id,
                "keywords": keywords,
                "count": len(keywords),
            }
            
        except GoogleAdsException as e:
            logger.error(f"Failed to get keyword performance: {e}")
            raise
    
    async def auto_suggest_negative_keywords(
        self,
        customer_id: str,
        campaign_id: Optional[str] = None,
        ad_group_id: Optional[str] = None,
        date_range: str = "LAST_30_DAYS",
        min_cost: float = 5.0,
        max_suggestions: int = 50
    ) -> Dict[str, Any]:
        """Auto-suggest negative keywords based on wasteful search terms."""
        try:
            client = self.auth_manager.get_client(customer_id)
            googleads_service = client.get_service("GoogleAdsService")
            
            # Query search terms with high cost but no conversions
            query = f"""
                SELECT
                    search_term_view.search_term,
                    search_term_view.status,
                    metrics.clicks,
                    metrics.impressions,
                    metrics.cost_micros,
                    metrics.conversions,
                    metrics.ctr,
                    ad_group.name,
                    ad_group.id,
                    campaign.name,
                    campaign.id
                FROM search_term_view
                WHERE segments.date DURING {date_range}
                AND metrics.cost_micros >= {int(min_cost * 1_000_000)}
                AND metrics.conversions = 0
                AND search_term_view.status = 'ADDED'
            """
            
            conditions = []
            if campaign_id:
                conditions.append(f"campaign.id = {campaign_id}")
            if ad_group_id:
                conditions.append(f"ad_group.id = {ad_group_id}")
            
            if conditions:
                query += " AND " + " AND ".join(conditions)
            
            query += " ORDER BY metrics.cost_micros DESC"
            
            response = googleads_service.search(
                customer_id=customer_id, query=query
            )
            
            # Analyze wasteful search terms
            wasteful_terms = []
            total_waste = 0
            
            for row in response:
                cost = row.metrics.cost_micros / 1_000_000
                search_term = str(row.search_term_view.search_term).lower()
                
                total_waste += cost
                
                wasteful_terms.append({
                    "search_term": search_term,
                    "cost": round(cost, 2),
                    "clicks": int(row.metrics.clicks),
                    "impressions": int(row.metrics.impressions),
                    "ctr": f"{row.metrics.ctr:.2%}" if row.metrics.ctr else "0.00%",
                    "campaign_name": str(row.campaign.name),
                    "ad_group_name": str(row.ad_group.name),
                })
            
            # Generate negative keyword suggestions using pattern analysis
            negative_suggestions = self._analyze_wasteful_patterns(wasteful_terms, max_suggestions)
            
            return {
                "success": True,
                "date_range": date_range,
                "total_wasteful_terms": len(wasteful_terms),
                "total_waste_cost": round(total_waste, 2),
                "suggested_negatives": negative_suggestions,
                "potential_monthly_savings": round(total_waste * (30 / self._get_days_in_range(date_range)), 2),
                "wasteful_terms_detail": wasteful_terms[:20],  # Top 20 most expensive
            }
            
        except GoogleAdsException as e:
            logger.error(f"Failed to auto-suggest negative keywords: {e}")
            raise
    
    async def get_search_terms_insights(
        self,
        customer_id: str,
        campaign_id: Optional[str] = None,
        ad_group_id: Optional[str] = None,
        date_range: str = "LAST_30_DAYS",
        min_impressions: int = 5
    ) -> Dict[str, Any]:
        """Get comprehensive search terms analysis with keyword opportunities."""
        try:
            client = self.auth_manager.get_client(customer_id)
            googleads_service = client.get_service("GoogleAdsService")
            
            # Query all search terms with performance data
            query = f"""
                SELECT
                    search_term_view.search_term,
                    search_term_view.status,
                    metrics.clicks,
                    metrics.impressions,
                    metrics.cost_micros,
                    metrics.conversions,
                    metrics.conversions_value,
                    metrics.ctr,
                    metrics.average_cpc,
                    ad_group.name,
                    ad_group.id,
                    campaign.name,
                    campaign.id
                FROM search_term_view
                WHERE segments.date DURING {date_range}
                AND metrics.impressions >= {min_impressions}
            """
            
            conditions = []
            if campaign_id:
                conditions.append(f"campaign.id = {campaign_id}")
            if ad_group_id:
                conditions.append(f"ad_group.id = {ad_group_id}")
            
            if conditions:
                query += " AND " + " AND ".join(conditions)
            
            query += " ORDER BY metrics.impressions DESC"
            
            response = googleads_service.search(
                customer_id=customer_id, query=query
            )
            
            # Categorize search terms
            high_performers = []
            keyword_opportunities = []
            wasteful_terms = []
            total_data = {"cost": 0, "conversions": 0, "clicks": 0}
            
            for row in response:
                cost = row.metrics.cost_micros / 1_000_000
                conversions = float(row.metrics.conversions)
                conversion_value = float(row.metrics.conversions_value)
                clicks = int(row.metrics.clicks)
                search_term = str(row.search_term_view.search_term)
                
                total_data["cost"] += cost
                total_data["conversions"] += conversions
                total_data["clicks"] += clicks
                
                search_data = {
                    "search_term": search_term,
                    "status": str(row.search_term_view.status.name),
                    "cost": round(cost, 2),
                    "clicks": clicks,
                    "impressions": int(row.metrics.impressions),
                    "conversions": conversions,
                    "conversion_value": round(conversion_value, 2),
                    "ctr": f"{row.metrics.ctr:.2%}" if row.metrics.ctr else "0.00%",
                    "avg_cpc": row.metrics.average_cpc / 1_000_000 if row.metrics.average_cpc else 0,
                    "roas": round(conversion_value / cost, 2) if cost > 0 else 0,
                    "triggered_keyword": "N/A",  # Not available from search_term_view
                    "match_type": "N/A",  # Not available from search_term_view
                    "campaign_name": str(row.campaign.name),
                    "ad_group_name": str(row.ad_group.name),
                }
                
                # Categorize based on performance
                if conversions > 0 and cost > 0:
                    roas = conversion_value / cost
                    if roas >= 2 or (conversions >= 2 and cost < 50):
                        high_performers.append(search_data)
                    elif conversions == 0 and cost >= 5:
                        wasteful_terms.append(search_data)
                
                # Identify keyword expansion opportunities
                if row.search_term_view.status.name == "NONE" and conversions > 0:
                    keyword_opportunities.append(search_data)
            
            # Generate insights
            insights = [
                f"📊 Total search terms analyzed: {len(high_performers) + len(keyword_opportunities) + len(wasteful_terms)}",
                f"🎯 High performers: {len(high_performers)} search terms driving conversions",
                f"💡 Keyword opportunities: {len(keyword_opportunities)} converting terms not yet added as keywords",
                f"🚨 Wasteful terms: {len(wasteful_terms)} terms spending money without conversions",
            ]
            
            if total_data["cost"] > 0:
                overall_conversion_rate = (total_data["conversions"] / total_data["clicks"] * 100) if total_data["clicks"] > 0 else 0
                insights.append(f"📈 Overall search term conversion rate: {overall_conversion_rate:.1f}%")
            
            return {
                "success": True,
                "date_range": date_range,
                "summary": {
                    "total_search_terms": len(high_performers) + len(keyword_opportunities) + len(wasteful_terms),
                    "high_performers": len(high_performers),
                    "keyword_opportunities": len(keyword_opportunities),
                    "wasteful_terms": len(wasteful_terms),
                    "total_cost": round(total_data["cost"], 2),
                    "total_conversions": total_data["conversions"],
                },
                "high_performing_terms": high_performers,
                "keyword_expansion_opportunities": keyword_opportunities,
                "wasteful_terms": wasteful_terms[:20],  # Top 20 most expensive
                "insights": insights,
                "recommended_actions": self._generate_search_terms_actions(high_performers, keyword_opportunities, wasteful_terms),
            }
            
        except GoogleAdsException as e:
            logger.error(f"Failed to get search terms insights: {e}")
            raise
    
    def _analyze_wasteful_patterns(self, wasteful_terms: List[Dict], max_suggestions: int) -> List[Dict]:
        """Analyze wasteful search terms to suggest negative keywords."""
        suggestions = []
        
        # Group by common patterns
        word_frequency = {}
        phrase_patterns = {}
        
        for term_data in wasteful_terms:
            search_term = term_data["search_term"]
            cost = term_data["cost"]
            
            # Analyze individual words
            words = search_term.split()
            for word in words:
                if len(word) > 3:  # Skip short words
                    if word not in word_frequency:
                        word_frequency[word] = {"count": 0, "total_cost": 0}
                    word_frequency[word]["count"] += 1
                    word_frequency[word]["total_cost"] += cost
            
            # Analyze two-word phrases
            for i in range(len(words) - 1):
                phrase = f"{words[i]} {words[i+1]}"
                if phrase not in phrase_patterns:
                    phrase_patterns[phrase] = {"count": 0, "total_cost": 0}
                phrase_patterns[phrase]["count"] += 1
                phrase_patterns[phrase]["total_cost"] += cost
        
        # Generate suggestions from high-cost frequent patterns
        
        # Word-based suggestions
        for word, data in word_frequency.items():
            if data["count"] >= 3 and data["total_cost"] >= 10:  # Appeared 3+ times, cost $10+
                suggestions.append({
                    "negative_keyword": word,
                    "match_type": "BROAD",
                    "reason": f"Appeared in {data['count']} wasteful searches, cost ${data['total_cost']:.2f}",
                    "potential_savings": round(data["total_cost"], 2),
                    "confidence": "high" if data["count"] >= 5 else "medium"
                })
        
        # Phrase-based suggestions  
        for phrase, data in phrase_patterns.items():
            if data["count"] >= 2 and data["total_cost"] >= 15:  # Appeared 2+ times, cost $15+
                suggestions.append({
                    "negative_keyword": phrase,
                    "match_type": "PHRASE",
                    "reason": f"Phrase appeared in {data['count']} wasteful searches, cost ${data['total_cost']:.2f}",
                    "potential_savings": round(data["total_cost"], 2),
                    "confidence": "high" if data["count"] >= 3 else "medium"
                })
        
        # Sort by potential savings and limit
        suggestions.sort(key=lambda x: x["potential_savings"], reverse=True)
        return suggestions[:max_suggestions]
    
    def _generate_search_terms_actions(self, high_performers: List, opportunities: List, wasteful: List) -> List[str]:
        """Generate actionable recommendations from search terms analysis."""
        actions = []
        
        if opportunities:
            actions.append(f"➕ Add {len(opportunities)} high-converting search terms as exact match keywords")
            top_opportunity = max(opportunities, key=lambda x: x["conversions"]) if opportunities else None
            if top_opportunity:
                actions.append(f"   Priority: '{top_opportunity['search_term']}' - {top_opportunity['conversions']} conversions, ${top_opportunity['cost']} cost")
        
        if wasteful:
            total_waste = sum(term["cost"] for term in wasteful)
            actions.append(f"🚫 Add negative keywords to prevent ${total_waste:.2f} monthly waste")
            if wasteful:
                actions.append(f"   Most expensive waste: '{wasteful[0]['search_term']}' - ${wasteful[0]['cost']} with 0 conversions")
        
        if high_performers:
            actions.append(f"🎯 Monitor {len(high_performers)} high-performing terms for bid optimization")
            best_performer = max(high_performers, key=lambda x: x["roas"]) if high_performers else None
            if best_performer:
                actions.append(f"   Best ROAS: '{best_performer['search_term']}' - {best_performer['roas']:.2f}x return")
        
        return actions
    
    def _get_days_in_range(self, date_range: str) -> int:
        """Get number of days in a date range for calculations."""
        range_mapping = {
            "LAST_7_DAYS": 7,
            "LAST_14_DAYS": 14, 
            "LAST_30_DAYS": 30,
            "LAST_90_DAYS": 90,
            "TODAY": 1,
            "YESTERDAY": 1,
        }
        return range_mapping.get(date_range, 30)
