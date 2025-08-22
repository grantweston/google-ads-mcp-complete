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
        """Add negative keywords at campaign or ad group level."""
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
                    criterion.keyword.text = keyword_text
                    criterion.keyword.match_type = client.enums.KeywordMatchTypeEnum.BROAD
                    
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
                    criterion.keyword.text = keyword_text
                    criterion.keyword.match_type = client.enums.KeywordMatchTypeEnum.BROAD
                    
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
