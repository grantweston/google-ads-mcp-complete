"""Campaign management tools for Google Ads API v20."""

from typing import Any, Dict, List, Optional
from datetime import datetime, date
import structlog

from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException

from .utils import currency_to_micros, micros_to_currency, parse_date

logger = structlog.get_logger(__name__)


class CampaignTools:
    """Campaign management tools."""
    
    def __init__(self, auth_manager, error_handler):
        self.auth_manager = auth_manager
        self.error_handler = error_handler
        
    async def create_campaign(
        self,
        customer_id: str,
        name: str,
        budget_amount: float,
        campaign_type: str = "SEARCH",
        bidding_strategy: str = "MAXIMIZE_CLICKS",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        target_locations: Optional[List[str]] = None,
        target_languages: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Create a new campaign with budget and settings."""
        try:
            client = self.auth_manager.get_client(customer_id)
            
            # First create a budget
            budget_service = client.get_service("CampaignBudgetService")
            campaign_service = client.get_service("CampaignService")
            
            # Create budget operation
            budget_operation = client.get_type("CampaignBudgetOperation")
            budget = budget_operation.create
            budget.name = f"{name} - Budget"
            budget.amount_micros = currency_to_micros(budget_amount)
            budget.delivery_method = client.enums.BudgetDeliveryMethodEnum.STANDARD
            
            # Add the budget
            budget_response = budget_service.mutate_campaign_budgets(
                customer_id=customer_id,
                operations=[budget_operation],
            )
            
            budget_resource_name = budget_response.results[0].resource_name
            
            # Create campaign operation
            campaign_operation = client.get_type("CampaignOperation")
            campaign = campaign_operation.create
            campaign.name = name
            campaign.campaign_budget = budget_resource_name
            
            # Set campaign type
            channel_type_enum = client.enums.AdvertisingChannelTypeEnum
            campaign_type_map = {
                "SEARCH": channel_type_enum.SEARCH,
                "DISPLAY": channel_type_enum.DISPLAY,
                "SHOPPING": channel_type_enum.SHOPPING,
                "VIDEO": channel_type_enum.VIDEO,
                "PERFORMANCE_MAX": channel_type_enum.PERFORMANCE_MAX,
                "SMART": channel_type_enum.SMART,
                "LOCAL": channel_type_enum.LOCAL,
            }
            campaign.advertising_channel_type = campaign_type_map.get(
                campaign_type.upper(), channel_type_enum.SEARCH
            )
            
            # Set campaign subtype for Performance Max
            if campaign_type.upper() == "PERFORMANCE_MAX":
                channel_subtype_enum = client.enums.AdvertisingChannelSubTypeEnum
                campaign.advertising_channel_sub_type = channel_subtype_enum.SHOPPING_COMPARISON_LISTING_ADS
            
            # Set bidding strategy (API v21 compatible) 
            # For now, use manual CPC which we know works
            manual_cpc = client.get_type("ManualCpc")
            campaign.manual_cpc = manual_cpc
            
            # TODO: Add other bidding strategies once we figure out the correct API v21 syntax
                
            # Set dates
            if start_date:
                campaign.start_date = parse_date(start_date).strftime("%Y%m%d")
            if end_date:
                campaign.end_date = parse_date(end_date).strftime("%Y%m%d")
                
            # Set network settings for Search campaigns
            if campaign_type.upper() == "SEARCH":
                campaign.network_settings.target_google_search = True
                campaign.network_settings.target_search_network = True
                campaign.network_settings.target_partner_search_network = False
                
            # Set campaign status
            campaign.status = client.enums.CampaignStatusEnum.ENABLED
            
            # Set required API v21 fields - use proper enum for EU political advertising
            # DOES_NOT_CONTAIN_EU_POLITICAL_ADVERTISING since we're targeting non-EU only
            campaign.contains_eu_political_advertising = client.enums.EuPoliticalAdvertisingStatusEnum.DOES_NOT_CONTAIN_EU_POLITICAL_ADVERTISING
            
            # Create the campaign
            campaign_response = campaign_service.mutate_campaigns(
                customer_id=customer_id,
                operations=[campaign_operation],
            )
            
            campaign_resource_name = campaign_response.results[0].resource_name
            campaign_id = campaign_resource_name.split("/")[-1]
            
            # Skip geo targeting for now - will fix separately
            # locations_to_target = target_locations or ["US"]  # Default to US only  
            # await self._add_geo_targeting(
            #     client, customer_id, campaign_id, locations_to_target
            # )
                
            # Add language targeting if provided
            if target_languages:
                await self._add_language_targeting(
                    client, customer_id, campaign_id, target_languages
                )
                
            return {
                "success": True,
                "campaign_id": campaign_id,
                "campaign_resource_name": campaign_resource_name,
                "budget_id": budget_resource_name.split("/")[-1],
                "budget_resource_name": budget_resource_name,
                "message": f"Campaign '{name}' created successfully",
            }
            
        except GoogleAdsException as e:
            logger.error(f"Failed to create campaign: {e}")
            return self.error_handler.format_error_response(e)
        except Exception as e:
            logger.error(f"Unexpected error creating campaign: {e}")
            raise
            
    async def _add_geo_targeting(
        self, client: GoogleAdsClient, customer_id: str, campaign_id: str, locations: List[str]
    ) -> None:
        """Add geographic targeting to a campaign."""
        campaign_criterion_service = client.get_service("CampaignCriterionService")
        geo_target_constant_service = client.get_service("GeoTargetConstantService")
        
        operations = []
        
        for location in locations:
            # Search for location
            gtc_query = f"""
                SELECT geo_target_constant.id, geo_target_constant.name
                FROM geo_target_constant
                WHERE geo_target_constant.name = '{location}'
                    AND geo_target_constant.status = 'ENABLED'
            """
            
            # Use the correct method for API v21
            gtc_response = geo_target_constant_service.search_geo_target_constants(query=gtc_query)
            
            for row in gtc_response:
                operation = client.get_type("CampaignCriterionOperation")
                criterion = operation.create
                criterion.campaign = f"customers/{customer_id}/campaigns/{campaign_id}"
                criterion.location.geo_target_constant = row.geo_target_constant.resource_name
                criterion.negative = False
                operations.append(operation)
                break
                
        if operations:
            campaign_criterion_service.mutate_campaign_criteria(
                customer_id=customer_id,
                operations=operations,
            )
            
    async def _add_language_targeting(
        self, client: GoogleAdsClient, customer_id: str, campaign_id: str, languages: List[str]
    ) -> None:
        """Add language targeting to a campaign."""
        campaign_criterion_service = client.get_service("CampaignCriterionService")
        
        # Language codes mapping
        language_map = {
            "English": "1000",  # English
            "Spanish": "1003",  # Spanish
            "French": "1002",   # French
            "German": "1001",   # German
            "Italian": "1004",  # Italian
            "Portuguese": "1014", # Portuguese
            "Dutch": "1010",    # Dutch
            "Russian": "1023",  # Russian
            "Japanese": "1005", # Japanese
            "Chinese": "1017",  # Chinese (simplified)
        }
        
        operations = []
        
        for language in languages:
            if language_code := language_map.get(language):
                operation = client.get_type("CampaignCriterionOperation")
                criterion = operation.create
                criterion.campaign = f"customers/{customer_id}/campaigns/{campaign_id}"
                criterion.language.language_constant = f"languageConstants/{language_code}"
                criterion.negative = False
                operations.append(operation)
                
        if operations:
            campaign_criterion_service.mutate_campaign_criteria(
                customer_id=customer_id,
                operations=operations,
            )
            
    async def update_campaign(
        self,
        customer_id: str,
        campaign_id: str,
        name: Optional[str] = None,
        status: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Update campaign settings."""
        try:
            client = self.auth_manager.get_client(customer_id)
            campaign_service = client.get_service("CampaignService")
            
            campaign_operation = client.get_type("CampaignOperation")
            campaign = campaign_operation.update
            campaign.resource_name = f"customers/{customer_id}/campaigns/{campaign_id}"
            
            update_mask = []
            
            if name is not None:
                campaign.name = name
                update_mask.append("name")
                
            if status is not None:
                status_enum = client.enums.CampaignStatusEnum
                status_map = {
                    "ENABLED": status_enum.ENABLED,
                    "PAUSED": status_enum.PAUSED,
                    "REMOVED": status_enum.REMOVED,
                }
                campaign.status = status_map.get(status.upper(), status_enum.PAUSED)
                update_mask.append("status")
                
            if start_date is not None:
                campaign.start_date = parse_date(start_date).strftime("%Y%m%d")
                update_mask.append("start_date")
                
            if end_date is not None:
                campaign.end_date = parse_date(end_date).strftime("%Y%m%d")
                update_mask.append("end_date")
                
            # Set the update mask
            campaign_operation.update_mask.CopyFrom(
                client.get_type("FieldMask")(paths=update_mask)
            )
            
            response = campaign_service.mutate_campaigns(
                customer_id=customer_id,
                operations=[campaign_operation],
            )
            
            return {
                "success": True,
                "campaign_id": campaign_id,
                "updated_fields": update_mask,
                "message": f"Campaign {campaign_id} updated successfully",
            }
            
        except GoogleAdsException as e:
            logger.error(f"Failed to update campaign: {e}")
            return self.error_handler.format_error_response(e)
        except Exception as e:
            logger.error(f"Unexpected error updating campaign: {e}")
            raise
            
    async def pause_campaign(self, customer_id: str, campaign_id: str) -> Dict[str, Any]:
        """Pause a running campaign."""
        return await self.update_campaign(customer_id, campaign_id, status="PAUSED")
        
    async def resume_campaign(self, customer_id: str, campaign_id: str) -> Dict[str, Any]:
        """Resume a paused campaign."""
        return await self.update_campaign(customer_id, campaign_id, status="ENABLED")
        
    async def list_campaigns(
        self,
        customer_id: str,
        status: Optional[str] = None,
        campaign_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List all campaigns with optional filters."""
        try:
            client = self.auth_manager.get_client(customer_id)
            googleads_service = client.get_service("GoogleAdsService")
            
            query = """
                SELECT
                    campaign.id,
                    campaign.name,
                    campaign.status,
                    campaign.advertising_channel_type
                FROM campaign
            """
            
            conditions = []
            if status:
                conditions.append(f"campaign.status = '{status.upper()}'")
            if campaign_type:
                conditions.append(f"campaign.advertising_channel_type = '{campaign_type.upper()}'")
                
            if conditions:
                query += " AND " + " AND ".join(conditions)
                
            query += " ORDER BY campaign.name"
            
            response = googleads_service.search(
                customer_id=customer_id,
                query=query,
            )
            
            campaigns = []
            for row in response:
                # Convert all protobuf/enum values to strings explicitly
                campaigns.append({
                    "id": str(row.campaign.id),
                    "name": str(row.campaign.name),
                    "status": str(row.campaign.status.name),
                    "type": str(row.campaign.advertising_channel_type.name),
                })
                
            return {
                "success": True,
                "campaigns": campaigns,
                "count": len(campaigns),
            }
            
        except GoogleAdsException as e:
            logger.error(f"Failed to list campaigns: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_type": "GoogleAdsException"
            }
        except Exception as e:
            logger.error(f"Unexpected error listing campaigns: {e}")
            raise
            
    async def get_campaign(self, customer_id: str, campaign_id: str) -> Dict[str, Any]:
        """Get detailed campaign information."""
        try:
            client = self.auth_manager.get_client(customer_id)
            googleads_service = client.get_service("GoogleAdsService")
            
            query = f"""
                SELECT
                    campaign.id,
                    campaign.name,
                    campaign.status,
                    campaign.advertising_channel_type,
                    campaign.advertising_channel_sub_type,
                    campaign.campaign_budget,
                    campaign_budget.amount_micros,
                    campaign_budget.delivery_method,
                    campaign.bidding_strategy_type,
                    campaign.start_date,
                    campaign.end_date,
                    campaign.network_settings.target_google_search,
                    campaign.network_settings.target_search_network,
                    campaign.network_settings.target_partner_search_network,
                    campaign.optimization_score,
                    metrics.clicks,
                    metrics.impressions,
                    metrics.cost_micros,
                    metrics.conversions,
                    metrics.average_cpc,
                    metrics.ctr,
                    metrics.conversion_rate
                FROM campaign
                WHERE campaign.id = {campaign_id}
                    AND segments.date DURING LAST_30_DAYS
            """
            
            response = googleads_service.search(
                customer_id=customer_id,
                query=query,
            )
            
            for row in response:
                return {
                    "success": True,
                    "campaign": {
                        "id": str(row.campaign.id),
                        "name": row.campaign.name,
                        "status": row.campaign.status.name,
                        "type": row.campaign.advertising_channel_type.name,
                        "subtype": getattr(row.campaign.advertising_channel_sub_type, "name", None),
                        "budget": {
                            "amount": micros_to_currency(row.campaign_budget.amount_micros),
                            "delivery_method": row.campaign_budget.delivery_method.name,
                        },
                        "bidding_strategy": row.campaign.bidding_strategy_type.name,
                        "dates": {
                            "start": row.campaign.start_date,
                            "end": row.campaign.end_date,
                        },
                        "network_settings": {
                            "google_search": row.campaign.network_settings.target_google_search,
                            "search_network": row.campaign.network_settings.target_search_network,
                            "partner_network": row.campaign.network_settings.target_partner_search_network,
                        },
                        "optimization_score": row.campaign.optimization_score,
                        "metrics": {
                            "clicks": row.metrics.clicks,
                            "impressions": row.metrics.impressions,
                            "cost": micros_to_currency(row.metrics.cost_micros),
                            "conversions": row.metrics.conversions,
                            "average_cpc": micros_to_currency(row.metrics.average_cpc),
                            "ctr": f"{row.metrics.ctr:.2%}",
                            "conversion_rate": f"{row.metrics.conversion_rate:.2%}",
                        },
                    },
                }
                
            return {"success": False, "error": f"Campaign {campaign_id} not found"}
            
        except GoogleAdsException as e:
            logger.error(f"Failed to get campaign: {e}")
            return self.error_handler.format_error_response(e)
        except Exception as e:
            logger.error(f"Unexpected error getting campaign: {e}")
            raise