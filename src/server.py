"""Google Ads API v20 MCP Server with comprehensive functionality."""

import asyncio
import json
import os
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, date, timedelta
from pathlib import Path

from mcp.server.models import InitializationOptions
from mcp.server import Server, NotificationOptions
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource
from pydantic import BaseModel, Field
import structlog

from .auth import GoogleAdsAuthManager, AuthenticationError
from .error_handler import ErrorHandler, RetryableGoogleAdsClient
from .tools import GoogleAdsTools
from .utils import format_currency, format_date_range, parse_date

logger = structlog.get_logger(__name__)


class GoogleAdsMCPServer:
    """MCP Server for Google Ads API v20."""
    
    def __init__(self, config_path: Optional[Path] = None):
        """Initialize the Google Ads MCP Server.
        
        Args:
            config_path: Optional path to configuration file.
        """
        self.server = Server("google-ads-mcp")
        self.auth_manager = GoogleAdsAuthManager(config_path)
        self.error_handler = ErrorHandler()
        self.tools = GoogleAdsTools(self.auth_manager, self.error_handler)
        
        # Register handlers
        self._register_handlers()
        
    def _register_handlers(self) -> None:
        """Register all MCP handlers."""
        
        @self.server.list_tools()
        async def handle_list_tools() -> List[Tool]:
            """Return all available Google Ads tools."""
            return self.tools.get_all_tools()
            
        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: Optional[Dict[str, Any]] = None) -> List[Union[TextContent, ImageContent, EmbeddedResource]]:
            """Execute a Google Ads tool."""
            try:
                result = await self.tools.execute_tool(name, arguments or {})
                
                # Format result as TextContent
                if isinstance(result, dict):
                    content = json.dumps(result, indent=2)
                else:
                    content = str(result)
                    
                return [TextContent(type="text", text=content)]
                
            except Exception as e:
                logger.error(f"Tool execution failed: {e}", tool=name, arguments=arguments)
                error_response = {
                    "success": False,
                    "error": str(e),
                    "tool": name,
                }
                
                # Add error details if it's a Google Ads exception
                if hasattr(e, "__class__") and e.__class__.__name__ == "GoogleAdsException":
                    error_response.update(self.error_handler.format_error_response(e))
                    
                return [TextContent(type="text", text=json.dumps(error_response, indent=2))]
                
        @self.server.list_resources()
        async def handle_list_resources() -> List[str]:
            """List available resources."""
            resources = [
                "googleads://accounts",
                "googleads://documentation",
                "googleads://error-codes",
                "googleads://gaql-reference",
            ]
            
            # Add account-specific resources if authenticated
            try:
                customers = self.auth_manager.get_accessible_customers()
                for customer in customers:
                    resources.append(f"googleads://customers/{customer['id']}")
            except:
                pass
                
            return resources
            
        @self.server.read_resource()
        async def handle_read_resource(uri: str) -> str:
            """Read a resource."""
            if uri == "googleads://documentation":
                return self._get_documentation()
            elif uri == "googleads://error-codes":
                return self._get_error_codes_reference()
            elif uri == "googleads://gaql-reference":
                return self._get_gaql_reference()
            elif uri.startswith("googleads://customers/"):
                customer_id = uri.split("/")[-1]
                return await self._get_customer_info(customer_id)
            elif uri == "googleads://accounts":
                return await self._get_all_accounts()
            else:
                return f"Unknown resource: {uri}"
                
    def _get_documentation(self) -> str:
        """Get comprehensive documentation for the MCP server."""
        return """# Google Ads MCP Server Documentation

## Overview
This MCP server provides comprehensive access to Google Ads API v20 functionality.

## Authentication
The server supports two authentication methods:
1. OAuth2 with refresh token
2. Service Account with optional impersonation

## Available Tools

### Account Management
- **list_accounts**: List all accessible Google Ads accounts
- **get_account_info**: Get detailed information about a specific account
- **get_account_hierarchy**: Get the account hierarchy tree

### Campaign Management
- **create_campaign**: Create a new campaign with budget and settings
- **update_campaign**: Update campaign settings (name, status, dates, etc.)
- **pause_campaign**: Pause a running campaign
- **resume_campaign**: Resume a paused campaign
- **list_campaigns**: List all campaigns with optional filters
- **get_campaign**: Get detailed campaign information

### Ad Group Management
- **create_ad_group**: Create a new ad group in a campaign
- **update_ad_group**: Update ad group settings
- **list_ad_groups**: List ad groups with filters
- **get_ad_group**: Get detailed ad group information

### Ad Management
- **create_responsive_search_ad**: Create a responsive search ad
- **create_expanded_text_ad**: Create an expanded text ad
- **update_ad**: Update ad content and settings
- **list_ads**: List ads with filters
- **get_ad**: Get detailed ad information

### Asset Management
- **upload_image_asset**: Upload an image asset
- **upload_text_asset**: Create a text asset
- **list_assets**: List all assets
- **create_asset_group**: Create an asset group for Performance Max

### Budget Management
- **create_budget**: Create a shared campaign budget
- **update_budget**: Update budget amount or settings
- **list_budgets**: List all budgets
- **get_budget**: Get budget details

### Keyword Management
- **add_keywords**: Add keywords to an ad group
- **update_keywords**: Update keyword bids or match types
- **add_negative_keywords**: Add negative keywords (campaign or ad group level)
- **list_keywords**: List keywords with performance data

### Reporting & Analytics
- **get_campaign_performance**: Get campaign performance metrics
- **get_ad_group_performance**: Get ad group performance metrics
- **get_keyword_performance**: Get keyword performance metrics
- **get_ad_performance**: Get ad performance metrics
- **run_gaql_query**: Run custom GAQL queries
- **get_search_terms_report**: Get search terms report

### Advanced Features
- **get_recommendations**: Get optimization recommendations
- **apply_recommendation**: Apply a specific recommendation
- **create_experiment**: Create a campaign experiment
- **get_change_history**: Get account change history

## Error Handling
The server automatically handles:
- Retryable errors with exponential backoff
- Partial failures in batch operations
- Token refresh for OAuth authentication
- Detailed error messages with documentation links

## GAQL Query Examples
```sql
-- Campaign performance last 30 days
SELECT campaign.name, metrics.clicks, metrics.impressions, metrics.cost_micros
FROM campaign
WHERE segments.date DURING LAST_30_DAYS

-- Keywords with low CTR
SELECT keyword.text, metrics.ctr, metrics.clicks, metrics.impressions
FROM keyword_view
WHERE metrics.ctr < 0.01 AND metrics.impressions > 100
```

## Best Practices
1. Use specific tools for common operations instead of raw GAQL
2. Always specify customer_id for operations
3. Use date_range parameter for performance queries
4. Check partial_failure in batch operation responses
5. Monitor rate limits and implement appropriate delays
"""

    def _get_error_codes_reference(self) -> str:
        """Get reference for common error codes."""
        return """# Google Ads API Error Codes Reference

## Authentication Errors
- **AUTHENTICATION_ERROR**: Invalid credentials or token expired
- **AUTHORIZATION_ERROR**: User doesn't have permission for the operation
- **CUSTOMER_NOT_FOUND**: The specified customer ID doesn't exist

## Validation Errors
- **REQUIRED_FIELD_MISSING**: A required field was not provided
- **INVALID_FIELD_VALUE**: Field value doesn't meet requirements
- **DUPLICATE_NAME**: Resource with the same name already exists

## Campaign Errors
- **CAMPAIGN_ERROR**: General campaign-related errors
- **INVALID_ADVERTISING_CHANNEL_TYPE**: Invalid campaign type
- **BUDGET_CANNOT_BE_SHARED**: Budget sharing not allowed for campaign type

## Budget Errors
- **CAMPAIGN_BUDGET_ERROR**: Budget-related errors
- **BUDGET_IN_USE**: Cannot delete budget that's assigned to campaigns
- **INVALID_BUDGET_AMOUNT**: Budget amount is invalid (too low/high)

## Retryable Errors
- **INTERNAL_ERROR**: Temporary server error, retry with backoff
- **TRANSIENT_ERROR**: Temporary issue, safe to retry
- **RESOURCE_EXHAUSTED**: Rate limit hit, wait before retry
- **DEADLINE_EXCEEDED**: Request timeout, can retry

## Handling Errors
1. Check if error is retryable (automatic in this MCP)
2. For validation errors, fix the request and retry
3. For permission errors, check account access
4. Use error documentation URLs for detailed explanations
"""

    def _get_gaql_reference(self) -> str:
        """Get GAQL query language reference."""
        return """# Google Ads Query Language (GAQL) Reference

## Basic Syntax
```sql
SELECT
  [fields]
FROM
  [resource]
WHERE
  [conditions]
ORDER BY
  [field] [ASC|DESC]
LIMIT [number]
```

## Common Resources
- **campaign**: Campaign data
- **ad_group**: Ad group data
- **ad_group_ad**: Ad data
- **keyword_view**: Keyword performance
- **search_term_view**: Search terms data
- **customer**: Account data

## Common Fields

### Attributes
- campaign.name, campaign.status, campaign.id
- ad_group.name, ad_group.status, ad_group.id
- keyword.text, keyword.match_type
- ad_group_ad.ad.id, ad_group_ad.status

### Metrics
- metrics.clicks, metrics.impressions
- metrics.cost_micros (cost in micros, divide by 1,000,000)
- metrics.ctr (click-through rate)
- metrics.average_cpc (average cost per click)
- metrics.conversions, metrics.conversion_rate

### Segments
- segments.date (for daily data)
- segments.device (MOBILE, DESKTOP, TABLET)
- segments.ad_network_type

## Date Ranges
- DURING LAST_30_DAYS
- DURING LAST_7_DAYS
- DURING THIS_MONTH
- BETWEEN '2024-01-01' AND '2024-12-31'

## Example Queries

### Campaign Performance
```sql
SELECT
  campaign.name,
  campaign.status,
  metrics.clicks,
  metrics.impressions,
  metrics.cost_micros,
  metrics.ctr
FROM campaign
WHERE campaign.status = 'ENABLED'
  AND segments.date DURING LAST_30_DAYS
ORDER BY metrics.clicks DESC
```

### Keyword Performance
```sql
SELECT
  keyword.text,
  keyword.match_type,
  metrics.clicks,
  metrics.conversions,
  metrics.cost_per_conversion
FROM keyword_view
WHERE metrics.impressions > 100
ORDER BY metrics.conversions DESC
LIMIT 50
```

### Search Terms Report
```sql
SELECT
  search_term_view.search_term,
  metrics.clicks,
  metrics.impressions,
  metrics.ctr,
  metrics.average_cpc
FROM search_term_view
WHERE segments.date DURING LAST_7_DAYS
ORDER BY metrics.clicks DESC
```

## Tips
1. Always specify date ranges for metrics
2. Use LIMIT to control response size
3. Metrics are aggregated based on SELECT fields
4. Resource names use customers/[ID]/[type]/[ID] format
5. Use '' for string literals, not double quotes
"""

    async def _get_customer_info(self, customer_id: str) -> str:
        """Get detailed customer information."""
        try:
            result = await self.tools.execute_tool("get_account_info", {"customer_id": customer_id})
            return json.dumps(result, indent=2)
        except Exception as e:
            return f"Error getting customer info: {str(e)}"
            
    async def _get_all_accounts(self) -> str:
        """Get all accessible accounts."""
        try:
            result = await self.tools.execute_tool("list_accounts", {})
            return json.dumps(result, indent=2)
        except Exception as e:
            return f"Error listing accounts: {str(e)}"
            
    async def run(self) -> None:
        """Run the MCP server."""
        async with stdio_server() as (read_stream, write_stream):
            init_options = InitializationOptions(
                server_name="google-ads-mcp",
                server_version="1.0.0",
                capabilities=self.server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            )
            
            await self.server.run(
                read_stream,
                write_stream,
                init_options,
            )


async def main():
    """Main entry point."""
    # Look for config in standard locations
    config_paths = [
        Path.home() / ".config" / "google-ads-mcp" / "config.json",
        Path.home() / ".google-ads-mcp.json",
        Path("google-ads-config.json"),
    ]
    
    config_path = None
    for path in config_paths:
        if path.exists():
            config_path = path
            logger.info(f"Using config file: {config_path}")
            break
            
    try:
        server = GoogleAdsMCPServer(config_path)
        await server.run()
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())