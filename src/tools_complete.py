"""Complete tools implementation combining all modules."""

import asyncio
from typing import Any, Dict, List, Optional
import base64
import structlog

from mcp.types import Tool
from google.ads.googleads.errors import GoogleAdsException

from .auth import GoogleAdsAuthManager
from .error_handler import ErrorHandler
from .tools_campaigns import CampaignTools
from .tools_reporting import ReportingTools
from .tools_ad_groups import AdGroupTools
from .tools_ads import AdTools
from .tools_keywords import KeywordTools
from .tools_budgets import BudgetTools
from .tools_assets import AssetTools
from .tools_extensions import ExtensionTools
from .utils import currency_to_micros, micros_to_currency

logger = structlog.get_logger(__name__)


class GoogleAdsTools:
    """Complete implementation of all Google Ads API v20 tools."""
    
    def __init__(self, auth_manager: GoogleAdsAuthManager, error_handler: ErrorHandler):
        self.auth_manager = auth_manager
        self.error_handler = error_handler
        
        # Initialize tool modules
        self.campaign_tools = CampaignTools(auth_manager, error_handler)
        self.reporting_tools = ReportingTools(auth_manager, error_handler)
        self.ad_group_tools = AdGroupTools(auth_manager, error_handler)
        self.ad_tools = AdTools(auth_manager, error_handler)
        self.keyword_tools = KeywordTools(auth_manager, error_handler)
        self.budget_tools = BudgetTools(auth_manager, error_handler)
        self.asset_tools = AssetTools(auth_manager, error_handler)
        self.extension_tools = ExtensionTools(auth_manager, error_handler)
        
        self._tools_registry = self._register_all_tools()
        
    def _register_all_tools(self) -> Dict[str, Dict[str, Any]]:
        """Register all available tools from all modules."""
        tools = {}
        
        # Account Management
        tools.update(self._register_account_tools())
        
        # Campaign Management (from CampaignTools)
        tools.update(self._register_campaign_tools())
        
        # Reporting & Analytics (from ReportingTools)
        tools.update(self._register_reporting_tools())
        
        # Additional tool categories
        # Ad Group Management
        tools.update(self._register_ad_group_tools())
        
        # Ad Management
        tools.update(self._register_ad_tools())
        
        # Asset Management
        tools.update(self._register_asset_tools())
        
        # Budget Management
        tools.update(self._register_budget_tools())
        
        # Keyword Management
        tools.update(self._register_keyword_tools())
        
        # Extension Management
        tools.update(self._register_extension_tools())
        
        # # Advanced Features
        # tools.update(self._register_advanced_tools())
        
        return tools
        
    def _register_account_tools(self) -> Dict[str, Dict[str, Any]]:
        """Register account management tools."""
        return {
            "list_accounts": {
                "description": "List all accessible Google Ads accounts",
                "handler": self.list_accounts,
                "parameters": {},
            },
            "get_account_info": {
                "description": "Get detailed information about a specific account",
                "handler": self.get_account_info,
                "parameters": {
                    "customer_id": {"type": "string", "required": True},
                },
            },
            "get_account_hierarchy": {
                "description": "Get the account hierarchy tree",
                "handler": self.get_account_hierarchy,
                "parameters": {
                    "customer_id": {"type": "string", "required": True},
                },
            },
        }
        
    def _register_campaign_tools(self) -> Dict[str, Dict[str, Any]]:
        """Register campaign management tools."""
        return {
            "create_campaign": {
                "description": "Create a new campaign with budget and settings",
                "handler": self.campaign_tools.create_campaign,
                "parameters": {
                    "customer_id": {"type": "string", "required": True},
                    "name": {"type": "string", "required": True},
                    "budget_amount": {"type": "number", "required": True},
                    "campaign_type": {"type": "string", "default": "SEARCH"},
                    "bidding_strategy": {"type": "string", "default": "MAXIMIZE_CLICKS"},
                    "start_date": {"type": "string"},
                    "end_date": {"type": "string"},
                    "target_locations": {"type": "array"},
                    "target_languages": {"type": "array"},
                },
            },
            "update_campaign": {
                "description": "Update campaign settings",
                "handler": self.campaign_tools.update_campaign,
                "parameters": {
                    "customer_id": {"type": "string", "required": True},
                    "campaign_id": {"type": "string", "required": True},
                    "name": {"type": "string"},
                    "status": {"type": "string"},
                    "start_date": {"type": "string"},
                    "end_date": {"type": "string"},
                },
            },
            "pause_campaign": {
                "description": "Pause a running campaign",
                "handler": self.campaign_tools.pause_campaign,
                "parameters": {
                    "customer_id": {"type": "string", "required": True},
                    "campaign_id": {"type": "string", "required": True},
                },
            },
            "resume_campaign": {
                "description": "Resume a paused campaign",
                "handler": self.campaign_tools.resume_campaign,
                "parameters": {
                    "customer_id": {"type": "string", "required": True},
                    "campaign_id": {"type": "string", "required": True},
                },
            },
            "list_campaigns": {
                "description": "List all campaigns with optional filters",
                "handler": self.campaign_tools.list_campaigns,
                "parameters": {
                    "customer_id": {"type": "string", "required": True},
                    "status": {"type": "string"},
                    "campaign_type": {"type": "string"},
                },
            },
            "get_campaign": {
                "description": "Get detailed campaign information",
                "handler": self.campaign_tools.get_campaign,
                "parameters": {
                    "customer_id": {"type": "string", "required": True},
                    "campaign_id": {"type": "string", "required": True},
                },
            },
            "delete_campaign": {
                "description": "Delete a campaign permanently",
                "handler": self.campaign_tools.delete_campaign,
                "parameters": {
                    "customer_id": {"type": "string", "required": True},
                    "campaign_id": {"type": "string", "required": True},
                },
            },
            "copy_campaign": {
                "description": "Copy an existing campaign with a new name and budget",
                "handler": self.campaign_tools.copy_campaign,
                "parameters": {
                    "customer_id": {"type": "string", "required": True},
                    "source_campaign_id": {"type": "string", "required": True},
                    "new_name": {"type": "string", "required": True},
                    "budget_amount": {"type": "number"},
                },
            },
        }
        
    def _register_ad_group_tools(self) -> Dict[str, Dict[str, Any]]:
        """Register ad group management tools."""
        return {
            "create_ad_group": {
                "description": "Create a new ad group in a campaign",
                "handler": self.ad_group_tools.create_ad_group,
                "parameters": {
                    "customer_id": {"type": "string", "required": True},
                    "campaign_id": {"type": "string", "required": True},
                    "name": {"type": "string", "required": True},
                    "cpc_bid_micros": {"type": "number"},
                },
            },
            "update_ad_group": {
                "description": "Update ad group settings",
                "handler": self.ad_group_tools.update_ad_group,
                "parameters": {
                    "customer_id": {"type": "string", "required": True},
                    "ad_group_id": {"type": "string", "required": True},
                    "name": {"type": "string"},
                    "status": {"type": "string"},
                    "cpc_bid_micros": {"type": "number"},
                },
            },
            "list_ad_groups": {
                "description": "List ad groups with filters",
                "handler": self.ad_group_tools.list_ad_groups,
                "parameters": {
                    "customer_id": {"type": "string", "required": True},
                    "campaign_id": {"type": "string"},
                    "status": {"type": "string"},
                },
            },
        }
        
    def _register_ad_tools(self) -> Dict[str, Dict[str, Any]]:
        """Register ad management tools."""
        return {
            "create_responsive_search_ad": {
                "description": "Create a responsive search ad",
                "handler": self.ad_tools.create_responsive_search_ad,
                "parameters": {
                    "customer_id": {"type": "string", "required": True},
                    "ad_group_id": {"type": "string", "required": True},
                    "headlines": {"type": "array", "required": True},
                    "descriptions": {"type": "array", "required": True},
                    "final_urls": {"type": "array", "required": True},
                    "path1": {"type": "string"},
                    "path2": {"type": "string"},
                },
            },
            "create_expanded_text_ad": {
                "description": "Create an expanded text ad",
                "handler": self.ad_tools.create_expanded_text_ad,
                "parameters": {
                    "customer_id": {"type": "string", "required": True},
                    "ad_group_id": {"type": "string", "required": True},
                    "headline1": {"type": "string", "required": True},
                    "headline2": {"type": "string", "required": True},
                    "headline3": {"type": "string"},
                    "description1": {"type": "string", "required": True},
                    "description2": {"type": "string"},
                    "final_urls": {"type": "array", "required": True},
                },
            },
            "list_ads": {
                "description": "List ads with filters",
                "handler": self.ad_tools.list_ads,
                "parameters": {
                    "customer_id": {"type": "string", "required": True},
                    "ad_group_id": {"type": "string"},
                    "campaign_id": {"type": "string"},
                    "status": {"type": "string"},
                },
            },
            "update_ad": {
                "description": "Update an existing ad including headlines, descriptions, URLs, display paths, and status",
                "handler": self.ad_tools.update_ad,
                "parameters": {
                    "customer_id": {"type": "string", "required": True},
                    "ad_group_id": {"type": "string", "required": True},
                    "ad_id": {"type": "string", "required": True},
                    "headlines": {"type": "array"},
                    "descriptions": {"type": "array"},
                    "final_urls": {"type": "array"},
                    "path1": {"type": "string"},
                    "path2": {"type": "string"},
                    "status": {"type": "string"},
                },
            },
            "pause_ad": {
                "description": "Pause a specific ad",
                "handler": self.ad_tools.pause_ad,
                "parameters": {
                    "customer_id": {"type": "string", "required": True},
                    "ad_group_id": {"type": "string", "required": True},
                    "ad_id": {"type": "string", "required": True},
                },
            },
            "enable_ad": {
                "description": "Enable a specific ad",
                "handler": self.ad_tools.enable_ad,
                "parameters": {
                    "customer_id": {"type": "string", "required": True},
                    "ad_group_id": {"type": "string", "required": True},
                    "ad_id": {"type": "string", "required": True},
                },
            },
            "delete_ad": {
                "description": "Delete a specific ad",
                "handler": self.ad_tools.delete_ad,
                "parameters": {
                    "customer_id": {"type": "string", "required": True},
                    "ad_group_id": {"type": "string", "required": True},
                    "ad_id": {"type": "string", "required": True},
                },
            },
            "get_ad_strength_and_review_status": {
                "description": "Get detailed ad strength ratings, review status, and quality recommendations",
                "handler": self.ad_tools.get_ad_strength_and_review_status,
                "parameters": {
                    "customer_id": {"type": "string", "required": True},
                    "ad_group_id": {"type": "string"},
                    "campaign_id": {"type": "string"},
                },
            },
        }
        
    def _register_asset_tools(self) -> Dict[str, Dict[str, Any]]:
        """Register asset management tools."""
        return {
            "upload_image_asset": {
                "description": "Upload an image asset",
                "handler": self.asset_tools.upload_image_asset,
                "parameters": {
                    "customer_id": {"type": "string", "required": True},
                    "image_data": {"type": "string", "required": True},
                    "name": {"type": "string", "required": True},
                },
            },
            "upload_text_asset": {
                "description": "Create a text asset",
                "handler": self.asset_tools.upload_text_asset,
                "parameters": {
                    "customer_id": {"type": "string", "required": True},
                    "text": {"type": "string", "required": True},
                    "name": {"type": "string", "required": True},
                },
            },
            "list_assets": {
                "description": "List all assets",
                "handler": self.asset_tools.list_assets,
                "parameters": {
                    "customer_id": {"type": "string", "required": True},
                    "asset_type": {"type": "string"},
                },
            },
        }
        
    def _register_budget_tools(self) -> Dict[str, Dict[str, Any]]:
        """Register budget management tools."""
        return {
            "create_budget": {
                "description": "Create a shared campaign budget",
                "handler": self.budget_tools.create_budget,
                "parameters": {
                    "customer_id": {"type": "string", "required": True},
                    "name": {"type": "string", "required": True},
                    "amount_micros": {"type": "number", "required": True},
                    "delivery_method": {"type": "string", "default": "STANDARD"},
                },
            },
            "update_budget": {
                "description": "Update budget amount or settings",
                "handler": self.budget_tools.update_budget,
                "parameters": {
                    "customer_id": {"type": "string", "required": True},
                    "budget_id": {"type": "string", "required": True},
                    "amount_micros": {"type": "number"},
                    "name": {"type": "string"},
                },
            },
            "list_budgets": {
                "description": "List all budgets",
                "handler": self.budget_tools.list_budgets,
                "parameters": {
                    "customer_id": {"type": "string", "required": True},
                },
            },
        }
        
    def _register_keyword_tools(self) -> Dict[str, Dict[str, Any]]:
        """Register keyword management tools."""
        return {
            "add_keywords": {
                "description": "Add keywords to an ad group",
                "handler": self.keyword_tools.add_keywords,
                "parameters": {
                    "customer_id": {"type": "string", "required": True},
                    "ad_group_id": {"type": "string", "required": True},
                    "keywords": {"type": "array", "required": True},
                },
            },
            "add_negative_keywords": {
                "description": "Add negative keywords (campaign or ad group level)",
                "handler": self.keyword_tools.add_negative_keywords,
                "parameters": {
                    "customer_id": {"type": "string", "required": True},
                    "keywords": {"type": "array", "required": True},
                    "campaign_id": {"type": "string"},
                    "ad_group_id": {"type": "string"},
                },
            },
            "list_keywords": {
                "description": "List keywords with performance data",
                "handler": self.keyword_tools.list_keywords,
                "parameters": {
                    "customer_id": {"type": "string", "required": True},
                    "ad_group_id": {"type": "string"},
                    "campaign_id": {"type": "string"},
                },
            },
            "update_keyword_bid": {
                "description": "Update the CPC bid for a specific keyword",
                "handler": self.keyword_tools.update_keyword_bid,
                "parameters": {
                    "customer_id": {"type": "string", "required": True},
                    "ad_group_id": {"type": "string", "required": True},
                    "keyword_id": {"type": "string", "required": True},
                    "cpc_bid_micros": {"type": "number", "required": True},
                },
            },
            "delete_keyword": {
                "description": "Delete a specific keyword",
                "handler": self.keyword_tools.delete_keyword,
                "parameters": {
                    "customer_id": {"type": "string", "required": True},
                    "ad_group_id": {"type": "string", "required": True},
                    "keyword_id": {"type": "string", "required": True},
                },
            },
            "pause_keyword": {
                "description": "Pause a specific keyword",
                "handler": self.keyword_tools.pause_keyword,
                "parameters": {
                    "customer_id": {"type": "string", "required": True},
                    "ad_group_id": {"type": "string", "required": True},
                    "keyword_id": {"type": "string", "required": True},
                },
            },
            "enable_keyword": {
                "description": "Enable a paused keyword",
                "handler": self.keyword_tools.enable_keyword,
                "parameters": {
                    "customer_id": {"type": "string", "required": True},
                    "ad_group_id": {"type": "string", "required": True},
                    "keyword_id": {"type": "string", "required": True},
                },
            },
            "get_keyword_performance": {
                "description": "Get keyword performance data with quality scores",
                "handler": self.keyword_tools.get_keyword_performance,
                "parameters": {
                    "customer_id": {"type": "string", "required": True},
                    "ad_group_id": {"type": "string"},
                    "date_range": {"type": "string", "default": "LAST_30_DAYS"},
                },
            },
        }
        
    def _register_extension_tools(self) -> Dict[str, Dict[str, Any]]:
        """Register extension management tools."""
        return {
            "create_sitelink_extensions": {
                "description": "Create sitelink extensions for a campaign",
                "handler": self.extension_tools.create_sitelink_extensions,
                "parameters": {
                    "customer_id": {"type": "string", "required": True},
                    "campaign_id": {"type": "string", "required": True},
                    "sitelinks": {"type": "array", "required": True},
                },
            },
            "create_callout_extensions": {
                "description": "Create callout extensions for a campaign",
                "handler": self.extension_tools.create_callout_extensions,
                "parameters": {
                    "customer_id": {"type": "string", "required": True},
                    "campaign_id": {"type": "string", "required": True},
                    "callouts": {"type": "array", "required": True},
                },
            },
            "create_call_extensions": {
                "description": "Create call extensions for a campaign",
                "handler": self.extension_tools.create_call_extensions,
                "parameters": {
                    "customer_id": {"type": "string", "required": True},
                    "campaign_id": {"type": "string", "required": True},
                    "phone_number": {"type": "string", "required": True},
                    "country_code": {"type": "string", "default": "US"},
                    "call_only": {"type": "boolean", "default": False},
                },
            },
            "list_extensions": {
                "description": "List extensions for a campaign or account",
                "handler": self.extension_tools.list_extensions,
                "parameters": {
                    "customer_id": {"type": "string", "required": True},
                    "campaign_id": {"type": "string"},
                    "extension_type": {"type": "string"},
                },
            },
            "delete_extension": {
                "description": "Delete a specific extension",
                "handler": self.extension_tools.delete_extension,
                "parameters": {
                    "customer_id": {"type": "string", "required": True},
                    "extension_id": {"type": "string", "required": True},
                },
            },
        }
        
    def _register_reporting_tools(self) -> Dict[str, Dict[str, Any]]:
        """Register reporting and analytics tools."""
        return {
            "get_campaign_performance": {
                "description": "Get campaign performance metrics",
                "handler": self.reporting_tools.get_campaign_performance,
                "parameters": {
                    "customer_id": {"type": "string", "required": True},
                    "campaign_id": {"type": "string"},
                    "date_range": {"type": "string", "default": "LAST_30_DAYS"},
                    "metrics": {"type": "array"},
                },
            },
            "get_ad_group_performance": {
                "description": "Get ad group performance metrics",
                "handler": self.reporting_tools.get_ad_group_performance,
                "parameters": {
                    "customer_id": {"type": "string", "required": True},
                    "ad_group_id": {"type": "string"},
                    "date_range": {"type": "string", "default": "LAST_30_DAYS"},
                },
            },
            "get_keyword_performance": {
                "description": "Get keyword performance metrics",
                "handler": self.reporting_tools.get_keyword_performance,
                "parameters": {
                    "customer_id": {"type": "string", "required": True},
                    "ad_group_id": {"type": "string"},
                    "date_range": {"type": "string", "default": "LAST_30_DAYS"},
                },
            },
            "run_gaql_query": {
                "description": "Run custom GAQL queries",
                "handler": self.reporting_tools.run_gaql_query,
                "parameters": {
                    "customer_id": {"type": "string", "required": True},
                    "query": {"type": "string", "required": True},
                },
            },
            "get_search_terms_report": {
                "description": "Get search terms report",
                "handler": self.reporting_tools.get_search_terms_report,
                "parameters": {
                    "customer_id": {"type": "string", "required": True},
                    "campaign_id": {"type": "string"},
                    "ad_group_id": {"type": "string"},
                    "date_range": {"type": "string", "default": "LAST_7_DAYS"},
                },
            },
        }
        
    def _register_advanced_tools(self) -> Dict[str, Dict[str, Any]]:
        """Register advanced feature tools."""
        return {
            "get_recommendations": {
                "description": "Get optimization recommendations",
                "handler": self.get_recommendations,
                "parameters": {
                    "customer_id": {"type": "string", "required": True},
                },
            },
            "apply_recommendation": {
                "description": "Apply a specific recommendation",
                "handler": self.apply_recommendation,
                "parameters": {
                    "customer_id": {"type": "string", "required": True},
                    "recommendation_id": {"type": "string", "required": True},
                },
            },
            "get_change_history": {
                "description": "Get account change history",
                "handler": self.get_change_history,
                "parameters": {
                    "customer_id": {"type": "string", "required": True},
                    "date_range": {"type": "string", "default": "LAST_7_DAYS"},
                },
            },
        }
        
    def get_all_tools(self) -> List[Tool]:
        """Get all tools in MCP format."""
        tools = []
        for name, config in self._tools_registry.items():
            # Extract required parameters
            required_params = []
            properties = {}
            
            for param_name, param_config in config["parameters"].items():
                # Create property schema without the 'required' field
                prop_schema = {k: v for k, v in param_config.items() if k != "required"}
                properties[param_name] = prop_schema
                
                # Add to required list if marked as required
                if param_config.get("required", False):
                    required_params.append(param_name)
            
            tool = Tool(
                name=name,
                description=config["description"],
                inputSchema={
                    "type": "object",
                    "properties": properties,
                    "required": required_params,
                },
            )
            tools.append(tool)
        return tools
        
    async def execute_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        """Execute a tool by name."""
        if name not in self._tools_registry:
            raise ValueError(f"Unknown tool: {name}")
            
        tool_config = self._tools_registry[name]
        handler = tool_config["handler"]
        
        # Validate required parameters
        for param, config in tool_config["parameters"].items():
            if config.get("required", False) and param not in arguments:
                raise ValueError(f"Missing required parameter: {param}")
                
        # Execute the handler
        return await handler(**arguments)
        
    # Account Management Methods
    
    async def list_accounts(self) -> Dict[str, Any]:
        """List all accessible Google Ads accounts."""
        try:
            customers = self.auth_manager.get_accessible_customers()
            return {
                "success": True,
                "accounts": customers,
                "count": len(customers),
            }
        except Exception as e:
            logger.error(f"Failed to list accounts: {e}")
            raise
            
    async def get_account_info(self, customer_id: str) -> Dict[str, Any]:
        """Get detailed account information."""
        try:
            client = self.auth_manager.get_client(customer_id)
            googleads_service = client.get_service("GoogleAdsService")
            
            query = """
                SELECT
                    customer.id,
                    customer.descriptive_name,
                    customer.currency_code,
                    customer.time_zone,
                    customer.auto_tagging_enabled,
                    customer.manager,
                    customer.test_account,
                    customer.optimization_score,
                    customer.optimization_score_weight
                FROM customer
                LIMIT 1
            """
            
            response = googleads_service.search(
                customer_id=customer_id,
                query=query,
            )
            
            for row in response:
                return {
                    "success": True,
                    "account": {
                        "id": str(row.customer.id),
                        "name": row.customer.descriptive_name,
                        "currency_code": row.customer.currency_code,
                        "time_zone": row.customer.time_zone,
                        "auto_tagging_enabled": row.customer.auto_tagging_enabled,
                        "is_manager": row.customer.manager,
                        "is_test_account": row.customer.test_account,
                        "optimization_score": row.customer.optimization_score,
                        "optimization_score_weight": row.customer.optimization_score_weight,
                    },
                }
                
            return {"success": False, "error": "Account not found"}
            
        except Exception as e:
            logger.error(f"Failed to get account info: {e}")
            raise
            
    async def get_account_hierarchy(self, customer_id: str) -> Dict[str, Any]:
        """Get the account hierarchy tree."""
        try:
            client = self.auth_manager.get_client(customer_id)
            googleads_service = client.get_service("GoogleAdsService")
            
            query = """
                SELECT
                    customer_client.id,
                    customer_client.descriptive_name,
                    customer_client.manager,
                    customer_client.level,
                    customer_client.time_zone,
                    customer_client.currency_code
                FROM customer_client
                WHERE customer_client.level <= 2
            """
            
            response = googleads_service.search(
                customer_id=customer_id,
                query=query,
            )
            
            hierarchy = []
            for row in response:
                hierarchy.append({
                    "id": str(row.customer_client.id),
                    "name": row.customer_client.descriptive_name,
                    "is_manager": row.customer_client.manager,
                    "level": row.customer_client.level,
                    "time_zone": row.customer_client.time_zone,
                    "currency_code": row.customer_client.currency_code,
                })
                
            return {
                "success": True,
                "hierarchy": hierarchy,
                "count": len(hierarchy),
            }
            
        except Exception as e:
            logger.error(f"Failed to get account hierarchy: {e}")
            raise
    # (Account, Ad Group, Ad, Asset, Budget, Keyword, and Advanced tools)
    # These would follow the same pattern as the campaign and reporting tools