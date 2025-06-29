"""Comprehensive Google Ads API v20 tools implementation."""

import asyncio
import json
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, date, timedelta
from decimal import Decimal
import base64

from mcp.types import Tool
from google.ads.googleads.errors import GoogleAdsException
from google.ads.googleads.client import GoogleAdsClient
import structlog

from .auth import GoogleAdsAuthManager
from .error_handler import ErrorHandler, RetryableGoogleAdsClient
from .tools_campaigns import CampaignTools
from .tools_reporting import ReportingTools
from .utils import (
    format_currency, format_date_range, parse_date,
    micros_to_currency, currency_to_micros
)

logger = structlog.get_logger(__name__)


class GoogleAdsTools:
    """Implementation of all Google Ads API v20 tools."""
    
    def __init__(self, auth_manager: GoogleAdsAuthManager, error_handler: ErrorHandler):
        self.auth_manager = auth_manager
        self.error_handler = error_handler
        
        # Initialize sub-modules
        self.campaign_tools = CampaignTools(auth_manager, error_handler)
        self.reporting_tools = ReportingTools(auth_manager, error_handler)
        
        self._tools_registry = self._register_tools()
        
    def _register_tools(self) -> Dict[str, Dict[str, Any]]:
        """Register all available tools."""
        return {
            # Account Management
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
            
            # Campaign Management
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
                "handler": self.update_campaign,
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
                "handler": self.pause_campaign,
                "parameters": {
                    "customer_id": {"type": "string", "required": True},
                    "campaign_id": {"type": "string", "required": True},
                },
            },
            "resume_campaign": {
                "description": "Resume a paused campaign",
                "handler": self.resume_campaign,
                "parameters": {
                    "customer_id": {"type": "string", "required": True},
                    "campaign_id": {"type": "string", "required": True},
                },
            },
            "list_campaigns": {
                "description": "List all campaigns with optional filters",
                "handler": self.list_campaigns,
                "parameters": {
                    "customer_id": {"type": "string", "required": True},
                    "status": {"type": "string"},
                    "campaign_type": {"type": "string"},
                },
            },
            "get_campaign": {
                "description": "Get detailed campaign information",
                "handler": self.get_campaign,
                "parameters": {
                    "customer_id": {"type": "string", "required": True},
                    "campaign_id": {"type": "string", "required": True},
                },
            },
            
            # Ad Group Management
            "create_ad_group": {
                "description": "Create a new ad group in a campaign",
                "handler": self.create_ad_group,
                "parameters": {
                    "customer_id": {"type": "string", "required": True},
                    "campaign_id": {"type": "string", "required": True},
                    "name": {"type": "string", "required": True},
                    "cpc_bid_micros": {"type": "number"},
                },
            },
            "update_ad_group": {
                "description": "Update ad group settings",
                "handler": self.update_ad_group,
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
                "handler": self.list_ad_groups,
                "parameters": {
                    "customer_id": {"type": "string", "required": True},
                    "campaign_id": {"type": "string"},
                    "status": {"type": "string"},
                },
            },
            
            # Ad Management
            "create_responsive_search_ad": {
                "description": "Create a responsive search ad",
                "handler": self.create_responsive_search_ad,
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
                "handler": self.create_expanded_text_ad,
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
                "handler": self.list_ads,
                "parameters": {
                    "customer_id": {"type": "string", "required": True},
                    "ad_group_id": {"type": "string"},
                    "campaign_id": {"type": "string"},
                    "status": {"type": "string"},
                },
            },
            
            # Asset Management
            "upload_image_asset": {
                "description": "Upload an image asset",
                "handler": self.upload_image_asset,
                "parameters": {
                    "customer_id": {"type": "string", "required": True},
                    "image_data": {"type": "string", "required": True},
                    "name": {"type": "string", "required": True},
                },
            },
            "upload_text_asset": {
                "description": "Create a text asset",
                "handler": self.upload_text_asset,
                "parameters": {
                    "customer_id": {"type": "string", "required": True},
                    "text": {"type": "string", "required": True},
                    "name": {"type": "string", "required": True},
                },
            },
            "list_assets": {
                "description": "List all assets",
                "handler": self.list_assets,
                "parameters": {
                    "customer_id": {"type": "string", "required": True},
                    "asset_type": {"type": "string"},
                },
            },
            
            # Budget Management
            "create_budget": {
                "description": "Create a shared campaign budget",
                "handler": self.create_budget,
                "parameters": {
                    "customer_id": {"type": "string", "required": True},
                    "name": {"type": "string", "required": True},
                    "amount_micros": {"type": "number", "required": True},
                    "delivery_method": {"type": "string", "default": "STANDARD"},
                },
            },
            "update_budget": {
                "description": "Update budget amount or settings",
                "handler": self.update_budget,
                "parameters": {
                    "customer_id": {"type": "string", "required": True},
                    "budget_id": {"type": "string", "required": True},
                    "amount_micros": {"type": "number"},
                    "name": {"type": "string"},
                },
            },
            "list_budgets": {
                "description": "List all budgets",
                "handler": self.list_budgets,
                "parameters": {
                    "customer_id": {"type": "string", "required": True},
                },
            },
            
            # Keyword Management
            "add_keywords": {
                "description": "Add keywords to an ad group",
                "handler": self.add_keywords,
                "parameters": {
                    "customer_id": {"type": "string", "required": True},
                    "ad_group_id": {"type": "string", "required": True},
                    "keywords": {"type": "array", "required": True},
                },
            },
            "add_negative_keywords": {
                "description": "Add negative keywords (campaign or ad group level)",
                "handler": self.add_negative_keywords,
                "parameters": {
                    "customer_id": {"type": "string", "required": True},
                    "keywords": {"type": "array", "required": True},
                    "campaign_id": {"type": "string"},
                    "ad_group_id": {"type": "string"},
                },
            },
            "list_keywords": {
                "description": "List keywords with performance data",
                "handler": self.list_keywords,
                "parameters": {
                    "customer_id": {"type": "string", "required": True},
                    "ad_group_id": {"type": "string"},
                    "campaign_id": {"type": "string"},
                },
            },
            
            # Reporting & Analytics
            "get_campaign_performance": {
                "description": "Get campaign performance metrics",
                "handler": self.get_campaign_performance,
                "parameters": {
                    "customer_id": {"type": "string", "required": True},
                    "campaign_id": {"type": "string"},
                    "date_range": {"type": "string", "default": "LAST_30_DAYS"},
                    "metrics": {"type": "array"},
                },
            },
            "get_ad_group_performance": {
                "description": "Get ad group performance metrics",
                "handler": self.get_ad_group_performance,
                "parameters": {
                    "customer_id": {"type": "string", "required": True},
                    "ad_group_id": {"type": "string"},
                    "date_range": {"type": "string", "default": "LAST_30_DAYS"},
                },
            },
            "get_keyword_performance": {
                "description": "Get keyword performance metrics",
                "handler": self.get_keyword_performance,
                "parameters": {
                    "customer_id": {"type": "string", "required": True},
                    "ad_group_id": {"type": "string"},
                    "date_range": {"type": "string", "default": "LAST_30_DAYS"},
                },
            },
            "run_gaql_query": {
                "description": "Run custom GAQL queries",
                "handler": self.run_gaql_query,
                "parameters": {
                    "customer_id": {"type": "string", "required": True},
                    "query": {"type": "string", "required": True},
                },
            },
            "get_search_terms_report": {
                "description": "Get search terms report",
                "handler": self.get_search_terms_report,
                "parameters": {
                    "customer_id": {"type": "string", "required": True},
                    "campaign_id": {"type": "string"},
                    "ad_group_id": {"type": "string"},
                    "date_range": {"type": "string", "default": "LAST_7_DAYS"},
                },
            },
            
            # Advanced Features
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
            tool = Tool(
                name=name,
                description=config["description"],
                inputSchema={
                    "type": "object",
                    "properties": config["parameters"],
                    "required": [k for k, v in config["parameters"].items() if v.get("required", False)],
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
        
    # Account Management Tools
    
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