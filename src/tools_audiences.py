"""Audience and targeting management tools for Google Ads API v21."""

from typing import Any, Dict, List, Optional
import structlog

from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException

logger = structlog.get_logger(__name__)


class AudienceTools:
    """Audience management and targeting tools."""
    
    def __init__(self, auth_manager, error_handler):
        self.auth_manager = auth_manager
        self.error_handler = error_handler
        
    async def create_custom_audience(
        self,
        customer_id: str,
        name: str,
        audience_type: str,
        rules: Dict[str, Any],
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a custom audience for targeting.
        
        Args:
            customer_id: The customer ID
            name: Name for the audience
            audience_type: WEBSITE_VISITORS, CUSTOMER_MATCH, SIMILAR_TO_USERS, etc.
            rules: Audience rules configuration
            description: Optional description
        """
        try:
            client = self.auth_manager.get_client(customer_id)
            user_list_service = client.get_service("UserListService")
            
            # Create user list operation
            user_list_operation = client.get_type("UserListOperation")
            user_list = user_list_operation.create
            
            user_list.name = name
            user_list.description = description or f"Custom audience: {name}"
            user_list.membership_status = client.enums.UserListMembershipStatusEnum.OPEN
            user_list.membership_life_span = 540  # Default 540 days (18 months)
            
            # Set audience type and rules
            if audience_type.upper() == "WEBSITE_VISITORS":
                # Create remarketing list based on website activity
                rule_based_user_list = user_list.rule_based_user_list
                rule_based_user_list.prepopulation_status = client.enums.UserListPrepopulationStatusEnum.REQUESTED
                
                # Create rule group (website visitors)
                rule_item_group = client.get_type("UserListRuleItemGroup")
                rule_item = client.get_type("UserListRuleItem")
                
                # Set up website visit rules
                if "url_contains" in rules:
                    rule_item.name = "url__"
                    rule_item.string_rule_item.operator = client.enums.UserListStringRuleItemOperatorEnum.CONTAINS
                    rule_item.string_rule_item.value = rules["url_contains"]
                elif "url_equals" in rules:
                    rule_item.name = "url__"
                    rule_item.string_rule_item.operator = client.enums.UserListStringRuleItemOperatorEnum.EQUALS
                    rule_item.string_rule_item.value = rules["url_equals"]
                else:
                    # Default: all visitors
                    rule_item.name = "url__"
                    rule_item.string_rule_item.operator = client.enums.UserListStringRuleItemOperatorEnum.CONTAINS
                    rule_item.string_rule_item.value = rules.get("domain", "")
                
                rule_item_group.rule_items.append(rule_item)
                
                # Create rule group
                rule_group = client.get_type("UserListRuleGroup")
                rule_group.rule_item_groups.append(rule_item_group)
                rule_based_user_list.flexible_rule_user_list.inclusive_rule_operator = client.enums.UserListFlexibleRuleOperatorEnum.AND
                rule_based_user_list.flexible_rule_user_list.inclusive_operands.append(rule_group)
                
            elif audience_type.upper() == "CUSTOMER_MATCH":
                # Create customer match list (email addresses, phone numbers)
                crm_based_user_list = user_list.crm_based_user_list
                crm_based_user_list.upload_key_type = client.enums.CustomerMatchUploadKeyTypeEnum.CONTACT_INFO
                
            # Execute operation
            response = user_list_service.mutate_user_lists(
                customer_id=customer_id,
                operations=[user_list_operation]
            )
            
            audience_id = response.results[0].resource_name.split('/')[-1]
            
            return {
                "success": True,
                "audience_id": audience_id,
                "audience_name": name,
                "audience_type": audience_type,
                "resource_name": response.results[0].resource_name,
                "membership_life_span": 540,
                "status": "OPEN",
                "message": f"Custom audience '{name}' created successfully"
            }
            
        except GoogleAdsException as e:
            logger.error(f"Failed to create custom audience: {e}")
            raise
    
    async def add_audience_targeting(
        self,
        customer_id: str,
        ad_group_id: str,
        audience_id: str,
        targeting_mode: str = "TARGETING",
        bid_modifier: Optional[float] = None
    ) -> Dict[str, Any]:
        """Add audience targeting to an ad group.
        
        Args:
            customer_id: The customer ID
            ad_group_id: The ad group ID
            audience_id: The audience/user list ID
            targeting_mode: TARGETING (restrict to audience) or OBSERVATION (collect data)
            bid_modifier: Optional bid adjustment (e.g., 1.2 for +20%)
        """
        try:
            client = self.auth_manager.get_client(customer_id)
            ad_group_criterion_service = client.get_service("AdGroupCriterionService")
            
            # Create ad group criterion operation
            ad_group_criterion_operation = client.get_type("AdGroupCriterionOperation")
            criterion = ad_group_criterion_operation.create
            
            # Set ad group
            criterion.ad_group = client.get_service("AdGroupService").ad_group_path(
                customer_id, ad_group_id
            )
            
            # Set audience criterion
            criterion.user_list.user_list = client.get_service("UserListService").user_list_path(
                customer_id, audience_id
            )
            
            # Set targeting mode
            if targeting_mode.upper() == "OBSERVATION":
                criterion.type_ = client.enums.CriterionTypeEnum.USER_LIST
                # For observation mode, we just collect data without restricting targeting
            else:
                criterion.type_ = client.enums.CriterionTypeEnum.USER_LIST
            
            # Set bid modifier if provided
            if bid_modifier:
                criterion.bid_modifier = bid_modifier
            
            # Set status
            criterion.status = client.enums.AdGroupCriterionStatusEnum.ENABLED
            
            # Execute operation
            response = ad_group_criterion_service.mutate_ad_group_criteria(
                customer_id=customer_id,
                operations=[ad_group_criterion_operation]
            )
            
            return {
                "success": True,
                "ad_group_id": ad_group_id,
                "audience_id": audience_id,
                "targeting_mode": targeting_mode,
                "bid_modifier": bid_modifier,
                "resource_name": response.results[0].resource_name,
                "message": f"Audience targeting added to ad group {ad_group_id}"
            }
            
        except GoogleAdsException as e:
            logger.error(f"Failed to add audience targeting: {e}")
            raise
    
    async def list_audiences(
        self,
        customer_id: str,
        audience_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """List all available audiences/user lists."""
        try:
            client = self.auth_manager.get_client(customer_id)
            googleads_service = client.get_service("GoogleAdsService")
            
            query = """
                SELECT
                    user_list.id,
                    user_list.name,
                    user_list.description,
                    user_list.membership_status,
                    user_list.membership_life_span,
                    user_list.size_for_display,
                    user_list.size_for_search,
                    user_list.type,
                    user_list.crm_based_user_list.upload_key_type,
                    user_list.rule_based_user_list.prepopulation_status
                FROM user_list
                WHERE user_list.type != 'UNKNOWN'
            """
            
            if audience_type:
                query += f" AND user_list.type = '{audience_type.upper()}'"
            
            query += " ORDER BY user_list.name"
            
            response = googleads_service.search(
                customer_id=customer_id, query=query
            )
            
            audiences = []
            for row in response:
                audience_data = {
                    "audience_id": str(row.user_list.id),
                    "name": str(row.user_list.name),
                    "description": str(row.user_list.description),
                    "type": str(row.user_list.type.name),
                    "membership_status": str(row.user_list.membership_status.name),
                    "membership_life_span": row.user_list.membership_life_span,
                    "size_for_display": row.user_list.size_for_display if row.user_list.size_for_display else 0,
                    "size_for_search": row.user_list.size_for_search if row.user_list.size_for_search else 0,
                    "resource_name": f"customers/{customer_id}/userLists/{row.user_list.id}",
                }
                
                # Add type-specific details
                if row.user_list.type.name == "CRM_BASED":
                    audience_data["upload_key_type"] = str(row.user_list.crm_based_user_list.upload_key_type.name) if hasattr(row.user_list, 'crm_based_user_list') else "N/A"
                elif row.user_list.type.name == "RULE_BASED":
                    audience_data["prepopulation_status"] = str(row.user_list.rule_based_user_list.prepopulation_status.name) if hasattr(row.user_list, 'rule_based_user_list') else "N/A"
                
                audiences.append(audience_data)
            
            return {
                "success": True,
                "total_audiences": len(audiences),
                "audiences": audiences,
                "summary": {
                    "rule_based": len([a for a in audiences if a["type"] == "RULE_BASED"]),
                    "crm_based": len([a for a in audiences if a["type"] == "CRM_BASED"]),
                    "similar_users": len([a for a in audiences if a["type"] == "SIMILAR"]),
                }
            }
            
        except GoogleAdsException as e:
            logger.error(f"Failed to list audiences: {e}")
            raise
    
    async def get_audience_performance(
        self,
        customer_id: str,
        audience_id: Optional[str] = None,
        campaign_id: Optional[str] = None,
        date_range: str = "LAST_30_DAYS"
    ) -> Dict[str, Any]:
        """Get performance data for audience targeting."""
        try:
            client = self.auth_manager.get_client(customer_id)
            googleads_service = client.get_service("GoogleAdsService")
            
            query = f"""
                SELECT
                    user_list.id,
                    user_list.name,
                    ad_group_criterion.bid_modifier,
                    ad_group_criterion.status,
                    metrics.clicks,
                    metrics.impressions,
                    metrics.cost_micros,
                    metrics.conversions,
                    metrics.conversions_value,
                    metrics.ctr,
                    ad_group.name,
                    ad_group.id,
                    campaign.name,
                    campaign.id
                FROM user_list_view
                WHERE segments.date DURING {date_range}
                AND ad_group_criterion.status != 'REMOVED'
            """
            
            conditions = []
            if audience_id:
                conditions.append(f"user_list.id = {audience_id}")
            if campaign_id:
                conditions.append(f"campaign.id = {campaign_id}")
            
            if conditions:
                query += " AND " + " AND ".join(conditions)
            
            query += " ORDER BY metrics.conversions DESC"
            
            response = googleads_service.search(
                customer_id=customer_id, query=query
            )
            
            audience_performance = []
            total_audience_cost = 0
            total_audience_conversions = 0
            
            for row in response:
                cost = row.metrics.cost_micros / 1_000_000
                conversions = float(row.metrics.conversions)
                conversion_value = float(row.metrics.conversions_value)
                
                total_audience_cost += cost
                total_audience_conversions += conversions
                
                performance_data = {
                    "audience_id": str(row.user_list.id),
                    "audience_name": str(row.user_list.name),
                    "ad_group_name": str(row.ad_group.name),
                    "campaign_name": str(row.campaign.name),
                    "bid_modifier": row.ad_group_criterion.bid_modifier if row.ad_group_criterion.bid_modifier else 1.0,
                    "status": str(row.ad_group_criterion.status.name),
                    "performance": {
                        "clicks": int(row.metrics.clicks),
                        "impressions": int(row.metrics.impressions),
                        "cost": round(cost, 2),
                        "conversions": conversions,
                        "conversion_value": round(conversion_value, 2),
                        "ctr": f"{row.metrics.ctr:.2%}" if row.metrics.ctr else "0.00%",
                        "cost_per_conversion": round(cost / conversions, 2) if conversions > 0 else "N/A",
                        "roas": round(conversion_value / cost, 2) if cost > 0 else 0,
                    }
                }
                audience_performance.append(performance_data)
            
            # Calculate overall audience performance
            overall_cost_per_conversion = total_audience_cost / total_audience_conversions if total_audience_conversions > 0 else 0
            
            return {
                "success": True,
                "date_range": date_range,
                "audience_id": audience_id,
                "campaign_id": campaign_id,
                "total_audiences": len(audience_performance),
                "overall_performance": {
                    "total_cost": round(total_audience_cost, 2),
                    "total_conversions": total_audience_conversions,
                    "avg_cost_per_conversion": round(overall_cost_per_conversion, 2),
                },
                "audience_performance": audience_performance,
            }
            
        except GoogleAdsException as e:
            logger.error(f"Failed to get audience performance: {e}")
            raise

