"""Geographic targeting and performance analysis tools for Google Ads API v21."""

from typing import Any, Dict, List, Optional
import structlog

from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException

from .utils import micros_to_currency

logger = structlog.get_logger(__name__)


class GeographyTools:
    """Geographic targeting and performance analysis tools."""
    
    def __init__(self, auth_manager, error_handler):
        self.auth_manager = auth_manager
        self.error_handler = error_handler
        
    async def get_location_performance(
        self,
        customer_id: str,
        campaign_id: Optional[str] = None,
        date_range: str = "LAST_30_DAYS",
        location_type: str = "COUNTRY_AND_REGION"
    ) -> Dict[str, Any]:
        """Get performance data by geographic location."""
        try:
            client = self.auth_manager.get_client(customer_id)
            googleads_service = client.get_service("GoogleAdsService")
            
            # Query geographic performance data
            query = f"""
                SELECT
                    geographic_view.country_criterion_id,
                    geographic_view.location_type,
                    geo_target_constant.name,
                    geo_target_constant.country_code,
                    geo_target_constant.target_type,
                    metrics.clicks,
                    metrics.impressions,
                    metrics.cost_micros,
                    metrics.conversions,
                    metrics.conversions_value,
                    metrics.ctr,
                    metrics.average_cpc,
                    campaign.name,
                    campaign.id
                FROM geographic_view
                WHERE segments.date DURING {date_range}
                AND geographic_view.location_type = '{location_type}'
            """
            
            if campaign_id:
                query += f" AND campaign.id = {campaign_id}"
            
            query += " ORDER BY metrics.cost_micros DESC"
            
            response = googleads_service.search(
                customer_id=customer_id, query=query
            )
            
            location_data = []
            total_cost = 0
            total_conversions = 0
            
            for row in response:
                cost = row.metrics.cost_micros / 1_000_000
                conversions = float(row.metrics.conversions)
                conversion_value = float(row.metrics.conversions_value)
                clicks = int(row.metrics.clicks)
                
                total_cost += cost
                total_conversions += conversions
                
                # Calculate efficiency metrics
                cost_per_conversion = cost / conversions if conversions > 0 else float('inf')
                roas = conversion_value / cost if cost > 0 else 0
                conversion_rate = (conversions / clicks * 100) if clicks > 0 else 0
                
                location_performance = {
                    "location_id": str(row.geographic_view.country_criterion_id),
                    "location_name": str(row.geo_target_constant.name),
                    "country_code": str(row.geo_target_constant.country_code),
                    "location_type": str(row.geographic_view.location_type.name),
                    "campaign_name": str(row.campaign.name),
                    "performance": {
                        "clicks": clicks,
                        "impressions": int(row.metrics.impressions),
                        "cost": round(cost, 2),
                        "conversions": conversions,
                        "conversion_value": round(conversion_value, 2),
                        "ctr": f"{row.metrics.ctr:.2%}" if row.metrics.ctr else "0.00%",
                        "avg_cpc": micros_to_currency(row.metrics.average_cpc) if row.metrics.average_cpc else 0,
                    },
                    "efficiency": {
                        "cost_per_conversion": round(cost_per_conversion, 2) if cost_per_conversion != float('inf') else "No conversions",
                        "roas": round(roas, 2),
                        "conversion_rate": f"{conversion_rate:.1f}%",
                    }
                }
                location_data.append(location_performance)
            
            # Calculate benchmarks for optimization recommendations
            avg_cost_per_conversion = total_cost / total_conversions if total_conversions > 0 else 0
            avg_roas = sum(loc["efficiency"]["roas"] for loc in location_data) / len(location_data) if location_data else 0
            
            # Generate geographic optimization recommendations
            optimization_recommendations = self._generate_geographic_recommendations(location_data, avg_cost_per_conversion, avg_roas)
            
            return {
                "success": True,
                "date_range": date_range,
                "location_type": location_type,
                "campaign_id": campaign_id,
                "total_locations": len(location_data),
                "overall_performance": {
                    "total_cost": round(total_cost, 2),
                    "total_conversions": total_conversions,
                    "avg_cost_per_conversion": round(avg_cost_per_conversion, 2),
                    "avg_roas": round(avg_roas, 2),
                },
                "location_performance": location_data,
                "optimization_recommendations": optimization_recommendations,
            }
            
        except GoogleAdsException as e:
            logger.error(f"Failed to get location performance: {e}")
            raise
    
    async def optimize_geographic_targeting(
        self,
        customer_id: str,
        campaign_id: str,
        date_range: str = "LAST_30_DAYS",
        min_cost_threshold: float = 20.0,
        poor_roas_threshold: float = 1.0
    ) -> Dict[str, Any]:
        """Auto-analyze geographic performance and suggest targeting optimizations."""
        try:
            # First get location performance data
            location_performance = await self.get_location_performance(
                customer_id, campaign_id, date_range
            )
            
            if not location_performance["success"]:
                return location_performance
            
            locations = location_performance["location_performance"]
            avg_cost_per_conversion = location_performance["overall_performance"]["avg_cost_per_conversion"]
            avg_roas = location_performance["overall_performance"]["avg_roas"]
            
            # Analyze and categorize locations
            high_performers = []
            underperformers = []
            exclusion_candidates = []
            bid_adjustment_candidates = []
            
            for location in locations:
                cost = location["performance"]["cost"]
                roas = location["efficiency"]["roas"]
                cost_per_conversion = location["efficiency"]["cost_per_conversion"]
                
                # High performers (better than average)
                if roas > avg_roas * 1.3 and cost > min_cost_threshold:
                    high_performers.append({
                        "location": location["location_name"],
                        "location_id": location["location_id"],
                        "roas": roas,
                        "cost": cost,
                        "recommendation": f"Increase bid by +20-50% - strong ROAS {roas:.2f}x",
                        "suggested_bid_modifier": 1.3  # +30% bid adjustment
                    })
                
                # Poor performers (exclude candidates)
                elif (roas < poor_roas_threshold and cost > min_cost_threshold) or \
                     (isinstance(cost_per_conversion, (int, float)) and cost_per_conversion > avg_cost_per_conversion * 2):
                    exclusion_candidates.append({
                        "location": location["location_name"],
                        "location_id": location["location_id"],
                        "roas": roas,
                        "cost": cost,
                        "cost_per_conversion": cost_per_conversion,
                        "recommendation": f"Consider excluding - poor ROAS {roas:.2f}x, high cost per conversion",
                        "potential_savings": cost  # Monthly savings if excluded
                    })
                
                # Medium performers (bid adjustment candidates)
                elif cost > min_cost_threshold and roas > 0:
                    if roas > avg_roas:
                        bid_adjustment_candidates.append({
                            "location": location["location_name"],
                            "location_id": location["location_id"],
                            "roas": roas,
                            "recommendation": f"Increase bid by +10-20% - above average ROAS",
                            "suggested_bid_modifier": 1.15  # +15% bid adjustment
                        })
                    elif roas < avg_roas * 0.7:
                        bid_adjustment_candidates.append({
                            "location": location["location_name"],
                            "location_id": location["location_id"],
                            "roas": roas,
                            "recommendation": f"Decrease bid by -20-30% - below average ROAS",
                            "suggested_bid_modifier": 0.75  # -25% bid adjustment
                        })
            
            # Calculate potential savings
            potential_monthly_savings = sum(loc["potential_savings"] for loc in exclusion_candidates if "potential_savings" in loc)
            
            return {
                "success": True,
                "campaign_id": campaign_id,
                "date_range": date_range,
                "analysis_summary": {
                    "total_locations_analyzed": len(locations),
                    "high_performers": len(high_performers),
                    "exclusion_candidates": len(exclusion_candidates),
                    "bid_adjustment_opportunities": len(bid_adjustment_candidates),
                    "potential_monthly_savings": round(potential_monthly_savings, 2),
                },
                "high_performing_locations": high_performers,
                "exclusion_recommendations": exclusion_candidates,
                "bid_adjustment_recommendations": bid_adjustment_candidates,
                "optimization_summary": [
                    f"🎯 {len(high_performers)} locations performing above average - consider bid increases",
                    f"🚫 {len(exclusion_candidates)} locations underperforming - consider exclusions (${potential_monthly_savings:.2f} potential savings)",
                    f"⚖️ {len(bid_adjustment_candidates)} locations need bid adjustments",
                ]
            }
            
        except GoogleAdsException as e:
            logger.error(f"Failed to optimize geographic targeting: {e}")
            raise
    
    def _generate_geographic_recommendations(self, location_data: List[Dict], avg_cost_per_conversion: float, avg_roas: float) -> List[str]:
        """Generate geographic optimization recommendations."""
        recommendations = []
        
        # Identify top and bottom performers
        if location_data:
            sorted_by_roas = sorted(location_data, key=lambda x: x["efficiency"]["roas"], reverse=True)
            
            best_location = sorted_by_roas[0]
            worst_location = sorted_by_roas[-1]
            
            if best_location["efficiency"]["roas"] > avg_roas * 1.5:
                recommendations.append(f"🎯 Top performer: {best_location['location_name']} - {best_location['efficiency']['roas']:.2f}x ROAS (consider bid increase)")
            
            if worst_location["efficiency"]["roas"] < avg_roas * 0.5 and worst_location["performance"]["cost"] > 20:
                recommendations.append(f"🚨 Underperformer: {worst_location['location_name']} - {worst_location['efficiency']['roas']:.2f}x ROAS (consider exclusion)")
            
            # Cost efficiency recommendations
            expensive_locations = [loc for loc in location_data if isinstance(loc["efficiency"]["cost_per_conversion"], (int, float)) and loc["efficiency"]["cost_per_conversion"] > avg_cost_per_conversion * 2]
            if expensive_locations:
                recommendations.append(f"💰 {len(expensive_locations)} locations have high cost per conversion (review targeting)")
        
        return recommendations
