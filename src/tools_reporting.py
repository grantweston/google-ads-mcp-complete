"""Reporting and analytics tools for Google Ads API v20."""

from typing import Any, Dict, List, Optional
from datetime import datetime, date, timedelta
import structlog

from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException

from .utils import micros_to_currency, format_date_range

logger = structlog.get_logger(__name__)


class ReportingTools:
    """Reporting and analytics tools."""
    
    def __init__(self, auth_manager, error_handler):
        self.auth_manager = auth_manager
        self.error_handler = error_handler
        
    async def get_campaign_performance(
        self,
        customer_id: str,
        campaign_id: Optional[str] = None,
        date_range: str = "LAST_30_DAYS",
        metrics: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Get campaign performance metrics."""
        try:
            client = self.auth_manager.get_client(customer_id)
            googleads_service = client.get_service("GoogleAdsService")
            
            # Default metrics if not specified
            if not metrics:
                metrics = [
                    "clicks", "impressions", "cost_micros", "conversions",
                    "ctr", "average_cpc", "conversion_rate", "cost_per_conversion"
                ]
                
            # Build metrics selection
            metrics_fields = ", ".join([f"metrics.{m}" for m in metrics])
            
            query = f"""
                SELECT
                    campaign.id,
                    campaign.name,
                    campaign.status,
                    {metrics_fields}
                FROM campaign
                WHERE segments.date DURING {date_range}
            """
            
            if campaign_id:
                query += f" AND campaign.id = {campaign_id}"
                
            query += " ORDER BY metrics.cost_micros DESC"
            
            response = googleads_service.search(
                customer_id=customer_id,
                query=query,
            )
            
            campaigns = []
            total_metrics = {m: 0 for m in metrics}
            
            for row in response:
                campaign_data = {
                    "id": str(row.campaign.id),
                    "name": row.campaign.name,
                    "status": row.campaign.status.name,
                    "metrics": {}
                }
                
                # Process each metric
                for metric in metrics:
                    value = getattr(row.metrics, metric)
                    
                    # Format currency metrics
                    if metric.endswith("_micros"):
                        campaign_data["metrics"][metric.replace("_micros", "")] = micros_to_currency(value)
                        total_metrics[metric] += value
                    elif metric in ["ctr", "conversion_rate"]:
                        campaign_data["metrics"][metric] = f"{value:.2%}"
                        total_metrics[metric] += value
                    else:
                        campaign_data["metrics"][metric] = value
                        total_metrics[metric] += value
                        
                campaigns.append(campaign_data)
                
            # Format totals
            formatted_totals = {}
            for metric, value in total_metrics.items():
                if metric.endswith("_micros"):
                    formatted_totals[metric.replace("_micros", "")] = micros_to_currency(value)
                elif metric in ["ctr", "conversion_rate"]:
                    # Calculate weighted average for rates
                    if len(campaigns) > 0:
                        formatted_totals[metric] = f"{value/len(campaigns):.2%}"
                    else:
                        formatted_totals[metric] = "0.00%"
                else:
                    formatted_totals[metric] = value
                    
            return {
                "success": True,
                "date_range": date_range,
                "campaigns": campaigns,
                "total_metrics": formatted_totals,
                "count": len(campaigns),
            }
            
        except GoogleAdsException as e:
            logger.error(f"Failed to get campaign performance: {e}")
            return self.error_handler.format_error_response(e)
        except Exception as e:
            logger.error(f"Unexpected error getting campaign performance: {e}")
            raise
            
    async def get_ad_group_performance(
        self,
        customer_id: str,
        ad_group_id: Optional[str] = None,
        date_range: str = "LAST_30_DAYS",
    ) -> Dict[str, Any]:
        """Get ad group performance metrics."""
        try:
            client = self.auth_manager.get_client(customer_id)
            googleads_service = client.get_service("GoogleAdsService")
            
            query = f"""
                SELECT
                    ad_group.id,
                    ad_group.name,
                    ad_group.status,
                    campaign.id,
                    campaign.name,
                    metrics.clicks,
                    metrics.impressions,
                    metrics.cost_micros,
                    metrics.conversions,
                    metrics.ctr,
                    metrics.average_cpc,
                    metrics.conversions,
                    metrics.cost_per_conversion
                FROM ad_group
                WHERE segments.date DURING {date_range}
            """
            
            if ad_group_id:
                query += f" AND ad_group.id = {ad_group_id}"
                
            query += " ORDER BY metrics.cost_micros DESC"
            
            response = googleads_service.search(
                customer_id=customer_id,
                query=query,
            )
            
            ad_groups = []
            for row in response:
                ad_groups.append({
                    "id": str(row.ad_group.id),
                    "name": row.ad_group.name,
                    "status": row.ad_group.status.name,
                    "campaign": {
                        "id": str(row.campaign.id),
                        "name": row.campaign.name,
                    },
                    "metrics": {
                        "clicks": row.metrics.clicks,
                        "impressions": row.metrics.impressions,
                        "cost": micros_to_currency(row.metrics.cost_micros),
                        "conversions": row.metrics.conversions,
                        "ctr": f"{row.metrics.ctr:.2%}",
                        "average_cpc": micros_to_currency(row.metrics.average_cpc),
                        "conversion_rate": f"{(row.metrics.conversions / row.metrics.clicks * 100):.2f}%" if row.metrics.clicks > 0 else "0.00%",
                        "cost_per_conversion": micros_to_currency(row.metrics.cost_per_conversion),
                    },
                })
                
            return {
                "success": True,
                "date_range": date_range,
                "ad_groups": ad_groups,
                "count": len(ad_groups),
            }
            
        except GoogleAdsException as e:
            logger.error(f"Failed to get ad group performance: {e}")
            return self.error_handler.format_error_response(e)
        except Exception as e:
            logger.error(f"Unexpected error getting ad group performance: {e}")
            raise
            
    async def get_keyword_performance(
        self,
        customer_id: str,
        ad_group_id: Optional[str] = None,
        date_range: str = "LAST_30_DAYS",
    ) -> Dict[str, Any]:
        """Get keyword performance metrics."""
        try:
            client = self.auth_manager.get_client(customer_id)
            googleads_service = client.get_service("GoogleAdsService")
            
            query = f"""
                SELECT
                    ad_group_criterion.keyword.text,
                    ad_group_criterion.keyword.match_type,
                    ad_group_criterion.status,
                    ad_group.id,
                    ad_group.name,
                    campaign.id,
                    campaign.name,
                    metrics.clicks,
                    metrics.impressions,
                    metrics.cost_micros,
                    metrics.conversions,
                    metrics.ctr,
                    metrics.average_cpc,
                    metrics.conversions,
                    metrics.average_position
                FROM keyword_view
                WHERE segments.date DURING {date_range}
                    AND ad_group_criterion.type = 'KEYWORD'
            """
            
            if ad_group_id:
                query += f" AND ad_group.id = {ad_group_id}"
                
            query += " ORDER BY metrics.impressions DESC"
            
            response = googleads_service.search(
                customer_id=customer_id,
                query=query,
            )
            
            keywords = []
            for row in response:
                keywords.append({
                    "text": row.ad_group_criterion.keyword.text,
                    "match_type": row.ad_group_criterion.keyword.match_type.name,
                    "status": row.ad_group_criterion.status.name,
                    "ad_group": {
                        "id": str(row.ad_group.id),
                        "name": row.ad_group.name,
                    },
                    "campaign": {
                        "id": str(row.campaign.id),
                        "name": row.campaign.name,
                    },
                    "metrics": {
                        "clicks": row.metrics.clicks,
                        "impressions": row.metrics.impressions,
                        "cost": micros_to_currency(row.metrics.cost_micros),
                        "conversions": row.metrics.conversions,
                        "ctr": f"{row.metrics.ctr:.2%}",
                        "average_cpc": micros_to_currency(row.metrics.average_cpc),
                        "conversion_rate": f"{(row.metrics.conversions / row.metrics.clicks * 100):.2f}%" if row.metrics.clicks > 0 else "0.00%",
                        "average_position": f"{row.metrics.average_position:.1f}" if row.metrics.average_position else "N/A",
                    },
                })
                
            return {
                "success": True,
                "date_range": date_range,
                "keywords": keywords,
                "count": len(keywords),
            }
            
        except GoogleAdsException as e:
            logger.error(f"Failed to get keyword performance: {e}")
            return self.error_handler.format_error_response(e)
        except Exception as e:
            logger.error(f"Unexpected error getting keyword performance: {e}")
            raise
            
    async def run_gaql_query(self, customer_id: str, query: str) -> Dict[str, Any]:
        """Run custom GAQL queries."""
        try:
            client = self.auth_manager.get_client(customer_id)
            googleads_service = client.get_service("GoogleAdsService")
            
            # Clean up the query
            query = query.strip()
            if query.endswith(";"):
                query = query[:-1]
                
            # Use search_stream for large result sets
            stream = googleads_service.search_stream(
                customer_id=customer_id,
                query=query,
            )
            
            rows = []
            fields = set()
            
            for batch in stream:
                for row in batch.results:
                    row_data = {}
                    
                    # Extract fields dynamically
                    for field_name in dir(row):
                        if not field_name.startswith("_"):
                            field_value = getattr(row, field_name)
                            if hasattr(field_value, "__class__"):
                                # Handle nested objects
                                nested_data = self._extract_nested_fields(field_value)
                                if nested_data:
                                    row_data[field_name] = nested_data
                                    fields.add(field_name)
                                    
                    rows.append(row_data)
                    
            return {
                "success": True,
                "query": query,
                "rows": rows,
                "row_count": len(rows),
                "fields": list(fields),
            }
            
        except GoogleAdsException as e:
            logger.error(f"Failed to run GAQL query: {e}")
            return self.error_handler.format_error_response(e)
        except Exception as e:
            logger.error(f"Unexpected error running GAQL query: {e}")
            raise
            
    def _extract_nested_fields(self, obj) -> Dict[str, Any]:
        """Extract fields from nested objects."""
        data = {}
        
        for field_name in dir(obj):
            if not field_name.startswith("_"):
                try:
                    field_value = getattr(obj, field_name)
                    
                    # Skip methods
                    if callable(field_value):
                        continue
                        
                    # Handle enums
                    if hasattr(field_value, "name"):
                        data[field_name] = field_value.name
                    # Handle numbers
                    elif isinstance(field_value, (int, float)):
                        # Convert micros to currency
                        if field_name.endswith("_micros"):
                            data[field_name.replace("_micros", "")] = micros_to_currency(field_value)
                        else:
                            data[field_name] = field_value
                    # Handle strings and booleans
                    elif isinstance(field_value, (str, bool)):
                        data[field_name] = field_value
                    # Handle nested objects recursively
                    elif hasattr(field_value, "__class__"):
                        nested = self._extract_nested_fields(field_value)
                        if nested:
                            data[field_name] = nested
                            
                except Exception:
                    continue
                    
        return data
        
    async def get_search_terms_report(
        self,
        customer_id: str,
        campaign_id: Optional[str] = None,
        ad_group_id: Optional[str] = None,
        date_range: str = "LAST_7_DAYS",
    ) -> Dict[str, Any]:
        """Get search terms report."""
        try:
            client = self.auth_manager.get_client(customer_id)
            googleads_service = client.get_service("GoogleAdsService")
            
            query = f"""
                SELECT
                    search_term_view.search_term,
                    search_term_view.status,
                    campaign.id,
                    campaign.name,
                    ad_group.id,
                    ad_group.name,
                    metrics.clicks,
                    metrics.impressions,
                    metrics.cost_micros,
                    metrics.conversions,
                    metrics.ctr,
                    metrics.average_cpc
                FROM search_term_view
                WHERE segments.date DURING {date_range}
            """
            
            conditions = []
            if campaign_id:
                conditions.append(f"campaign.id = {campaign_id}")
            if ad_group_id:
                conditions.append(f"ad_group.id = {ad_group_id}")
                
            if conditions:
                query += " AND " + " AND ".join(conditions)
                
            query += " ORDER BY metrics.impressions DESC LIMIT 100"
            
            response = googleads_service.search(
                customer_id=customer_id,
                query=query,
            )
            
            search_terms = []
            for row in response:
                search_terms.append({
                    "search_term": row.search_term_view.search_term,
                    "status": row.search_term_view.status.name,
                    "campaign": {
                        "id": str(row.campaign.id),
                        "name": row.campaign.name,
                    },
                    "ad_group": {
                        "id": str(row.ad_group.id),
                        "name": row.ad_group.name,
                    },
                    "metrics": {
                        "clicks": row.metrics.clicks,
                        "impressions": row.metrics.impressions,
                        "cost": micros_to_currency(row.metrics.cost_micros),
                        "conversions": row.metrics.conversions,
                        "ctr": f"{row.metrics.ctr:.2%}",
                        "average_cpc": micros_to_currency(row.metrics.average_cpc),
                    },
                })
                
            return {
                "success": True,
                "date_range": date_range,
                "search_terms": search_terms,
                "count": len(search_terms),
            }
            
        except GoogleAdsException as e:
            logger.error(f"Failed to get search terms report: {e}")
            return self.error_handler.format_error_response(e)
        except Exception as e:
            logger.error(f"Unexpected error getting search terms report: {e}")
            raise