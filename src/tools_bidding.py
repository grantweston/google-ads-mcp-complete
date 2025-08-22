"""Bidding strategy and bid adjustment management tools for Google Ads API v21."""

from typing import Any, Dict, List, Optional
import structlog

from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException

from .utils import micros_to_currency

logger = structlog.get_logger(__name__)


class BiddingTools:
    """Bidding strategy and bid adjustment management tools."""
    
    def __init__(self, auth_manager, error_handler):
        self.auth_manager = auth_manager
        self.error_handler = error_handler
        
    async def set_bid_adjustments(
        self,
        customer_id: str,
        campaign_id: str,
        adjustments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Set bid adjustments for campaign (device, location, demographic).
        
        Args:
            customer_id: The customer ID
            campaign_id: The campaign ID
            adjustments: Dict with 'device', 'location', 'demographic' adjustments
                Example: {
                    "device": {"mobile": 1.2, "desktop": 0.9, "tablet": 1.1},
                    "location": {"2840": 1.3},  # Location ID with +30% bid
                    "demographic": {"age_18_24": 0.8, "age_25_34": 1.4}
                }
        """
        try:
            client = self.auth_manager.get_client(customer_id)
            campaign_criterion_service = client.get_service("CampaignCriterionService")
            
            operations = []
            applied_adjustments = []
            
            # Device bid adjustments
            if "device" in adjustments:
                device_adjustments = adjustments["device"]
                
                for device_type, modifier in device_adjustments.items():
                    # Create campaign criterion operation
                    campaign_criterion_operation = client.get_type("CampaignCriterionOperation")
                    criterion = campaign_criterion_operation.create
                    
                    # Set campaign
                    criterion.campaign = client.get_service("CampaignService").campaign_path(
                        customer_id, campaign_id
                    )
                    
                    # Set device criterion
                    if device_type.lower() == "mobile":
                        criterion.mobile_device.device_type = client.enums.MobileDeviceTypeEnum.MOBILE
                    elif device_type.lower() == "desktop":  
                        criterion.platform.platform_name = "Desktop"
                    elif device_type.lower() == "tablet":
                        criterion.mobile_device.device_type = client.enums.MobileDeviceTypeEnum.TABLET
                    
                    # Set bid modifier
                    criterion.bid_modifier = modifier
                    criterion.status = client.enums.CampaignCriterionStatusEnum.ENABLED
                    
                    operations.append(campaign_criterion_operation)
                    applied_adjustments.append({
                        "type": "device",
                        "target": device_type,
                        "bid_modifier": modifier,
                        "percentage": f"{(modifier - 1) * 100:+.0f}%"
                    })
            
            # Location bid adjustments
            if "location" in adjustments:
                location_adjustments = adjustments["location"]
                
                for location_id, modifier in location_adjustments.items():
                    campaign_criterion_operation = client.get_type("CampaignCriterionOperation")
                    criterion = campaign_criterion_operation.create
                    
                    # Set campaign
                    criterion.campaign = client.get_service("CampaignService").campaign_path(
                        customer_id, campaign_id
                    )
                    
                    # Set location criterion
                    criterion.location.geo_target_constant = client.get_service("GeoTargetConstantService").geo_target_constant_path(location_id)
                    
                    # Set bid modifier
                    criterion.bid_modifier = modifier
                    criterion.status = client.enums.CampaignCriterionStatusEnum.ENABLED
                    
                    operations.append(campaign_criterion_operation)
                    applied_adjustments.append({
                        "type": "location",
                        "target": location_id,
                        "bid_modifier": modifier,
                        "percentage": f"{(modifier - 1) * 100:+.0f}%"
                    })
            
            # Execute all operations
            if operations:
                response = campaign_criterion_service.mutate_campaign_criteria(
                    customer_id=customer_id,
                    operations=operations
                )
                
                return {
                    "success": True,
                    "campaign_id": campaign_id,
                    "adjustments_applied": len(applied_adjustments),
                    "adjustments_detail": applied_adjustments,
                    "resource_names": [result.resource_name for result in response.results],
                    "message": f"Applied {len(applied_adjustments)} bid adjustments to campaign {campaign_id}"
                }
            else:
                return {
                    "success": False,
                    "error": "No valid adjustments provided",
                    "expected_format": {
                        "device": {"mobile": 1.2, "desktop": 0.9},
                        "location": {"location_id": 1.3}
                    }
                }
            
        except GoogleAdsException as e:
            logger.error(f"Failed to set bid adjustments: {e}")
            raise
    
    async def get_bid_adjustment_performance(
        self,
        customer_id: str,
        campaign_id: str,
        date_range: str = "LAST_30_DAYS"
    ) -> Dict[str, Any]:
        """Get performance data for current bid adjustments."""
        try:
            client = self.auth_manager.get_client(customer_id)
            googleads_service = client.get_service("GoogleAdsService")
            
            # Query bid adjustment performance
            query = f"""
                SELECT
                    campaign_criterion.criterion_id,
                    campaign_criterion.type,
                    campaign_criterion.bid_modifier,
                    campaign_criterion.status,
                    campaign_criterion.mobile_device.device_type,
                    campaign_criterion.location.geo_target_constant,
                    geo_target_constant.name,
                    metrics.clicks,
                    metrics.impressions,
                    metrics.cost_micros,
                    metrics.conversions,
                    metrics.conversions_value,
                    metrics.ctr,
                    campaign.name
                FROM campaign_criterion
                WHERE campaign.id = {campaign_id}
                AND segments.date DURING {date_range}
                AND campaign_criterion.status = 'ENABLED'
                AND campaign_criterion.bid_modifier != 1.0
            """
            
            response = googleads_service.search(
                customer_id=customer_id, query=query
            )
            
            adjustments_performance = []
            total_adjusted_cost = 0
            total_adjusted_conversions = 0
            
            for row in response:
                cost = row.metrics.cost_micros / 1_000_000
                conversions = float(row.metrics.conversions)
                conversion_value = float(row.metrics.conversions_value)
                
                total_adjusted_cost += cost
                total_adjusted_conversions += conversions
                
                # Determine adjustment type and target
                adjustment_type = str(row.campaign_criterion.type.name)
                target_name = "Unknown"
                
                if adjustment_type == "MOBILE_DEVICE":
                    device_type = str(row.campaign_criterion.mobile_device.device_type.name)
                    target_name = device_type.title()
                elif adjustment_type == "LOCATION":
                    target_name = str(row.geo_target_constant.name) if hasattr(row, 'geo_target_constant') else "Location"
                
                # Calculate performance impact
                roas = conversion_value / cost if cost > 0 else 0
                cost_per_conversion = cost / conversions if conversions > 0 else float('inf')
                
                adjustment_data = {
                    "criterion_id": str(row.campaign_criterion.criterion_id),
                    "adjustment_type": adjustment_type.lower(),
                    "target_name": target_name,
                    "bid_modifier": row.campaign_criterion.bid_modifier,
                    "bid_percentage": f"{(row.campaign_criterion.bid_modifier - 1) * 100:+.0f}%",
                    "performance": {
                        "clicks": int(row.metrics.clicks),
                        "impressions": int(row.metrics.impressions),
                        "cost": round(cost, 2),
                        "conversions": conversions,
                        "conversion_value": round(conversion_value, 2),
                        "ctr": f"{row.metrics.ctr:.2%}" if row.metrics.ctr else "0.00%",
                    },
                    "efficiency": {
                        "roas": round(roas, 2),
                        "cost_per_conversion": round(cost_per_conversion, 2) if cost_per_conversion != float('inf') else "No conversions",
                    }
                }
                adjustments_performance.append(adjustment_data)
            
            # Analyze adjustment effectiveness
            effectiveness_analysis = self._analyze_adjustment_effectiveness(adjustments_performance)
            
            return {
                "success": True,
                "campaign_id": campaign_id,
                "date_range": date_range,
                "total_adjustments": len(adjustments_performance),
                "overall_adjusted_performance": {
                    "total_cost": round(total_adjusted_cost, 2),
                    "total_conversions": total_adjusted_conversions,
                    "avg_cost_per_conversion": round(total_adjusted_cost / total_adjusted_conversions, 2) if total_adjusted_conversions > 0 else "N/A",
                },
                "adjustments_performance": adjustments_performance,
                "effectiveness_analysis": effectiveness_analysis,
            }
            
        except GoogleAdsException as e:
            logger.error(f"Failed to get bid adjustment performance: {e}")
            raise
    
    async def create_portfolio_bidding_strategy(
        self,
        customer_id: str,
        name: str,
        strategy_type: str,
        target_cpa_micros: Optional[int] = None,
        target_roas: Optional[float] = None
    ) -> Dict[str, Any]:
        """Create a portfolio bidding strategy for sharing across campaigns."""
        try:
            client = self.auth_manager.get_client(customer_id)
            bidding_strategy_service = client.get_service("BiddingStrategyService")
            
            # Create bidding strategy operation
            bidding_strategy_operation = client.get_type("BiddingStrategyOperation")
            bidding_strategy = bidding_strategy_operation.create
            
            bidding_strategy.name = name
            bidding_strategy.status = client.enums.BiddingStrategyStatusEnum.ENABLED
            
            # Set strategy type and configuration
            if strategy_type.upper() == "TARGET_CPA":
                bidding_strategy.target_cpa.target_cpa_micros = target_cpa_micros or 10_000_000  # Default $10
                bidding_strategy.type_ = client.enums.BiddingStrategyTypeEnum.TARGET_CPA
                
            elif strategy_type.upper() == "TARGET_ROAS":
                bidding_strategy.target_roas.target_roas = target_roas or 3.0  # Default 3x ROAS
                bidding_strategy.type_ = client.enums.BiddingStrategyTypeEnum.TARGET_ROAS
                
            elif strategy_type.upper() == "MAXIMIZE_CONVERSIONS":
                bidding_strategy.maximize_conversions = client.get_type("MaximizeConversions")
                bidding_strategy.type_ = client.enums.BiddingStrategyTypeEnum.MAXIMIZE_CONVERSIONS
                
            elif strategy_type.upper() == "MAXIMIZE_CLICKS":
                bidding_strategy.maximize_clicks = client.get_type("MaximizeClicks")
                bidding_strategy.type_ = client.enums.BiddingStrategyTypeEnum.MAXIMIZE_CLICKS
            
            # Execute operation
            response = bidding_strategy_service.mutate_bidding_strategies(
                customer_id=customer_id,
                operations=[bidding_strategy_operation]
            )
            
            strategy_id = response.results[0].resource_name.split('/')[-1]
            
            return {
                "success": True,
                "strategy_id": strategy_id,
                "strategy_name": name,
                "strategy_type": strategy_type,
                "target_cpa": micros_to_currency(target_cpa_micros) if target_cpa_micros else None,
                "target_roas": target_roas,
                "resource_name": response.results[0].resource_name,
                "message": f"Portfolio bidding strategy '{name}' created successfully"
            }
            
        except GoogleAdsException as e:
            logger.error(f"Failed to create portfolio bidding strategy: {e}")
            raise
    
    async def list_bidding_strategies(
        self,
        customer_id: str
    ) -> Dict[str, Any]:
        """List all bidding strategies in the account."""
        try:
            client = self.auth_manager.get_client(customer_id)
            googleads_service = client.get_service("GoogleAdsService")
            
            query = """
                SELECT
                    bidding_strategy.id,
                    bidding_strategy.name,
                    bidding_strategy.type,
                    bidding_strategy.status,
                    bidding_strategy.target_cpa.target_cpa_micros,
                    bidding_strategy.target_roas.target_roas,
                    bidding_strategy.campaign_count,
                    bidding_strategy.non_removed_campaign_count
                FROM bidding_strategy
                WHERE bidding_strategy.status != 'REMOVED'
                ORDER BY bidding_strategy.name
            """
            
            response = googleads_service.search(
                customer_id=customer_id, query=query
            )
            
            strategies = []
            for row in response:
                strategy_data = {
                    "strategy_id": str(row.bidding_strategy.id),
                    "name": str(row.bidding_strategy.name),
                    "type": str(row.bidding_strategy.type.name),
                    "status": str(row.bidding_strategy.status.name),
                    "campaign_count": row.bidding_strategy.campaign_count,
                    "active_campaigns": row.bidding_strategy.non_removed_campaign_count,
                    "resource_name": f"customers/{customer_id}/biddingStrategies/{row.bidding_strategy.id}",
                }
                
                # Add type-specific configuration
                if row.bidding_strategy.type.name == "TARGET_CPA":
                    strategy_data["target_cpa"] = micros_to_currency(row.bidding_strategy.target_cpa.target_cpa_micros)
                elif row.bidding_strategy.type.name == "TARGET_ROAS":
                    strategy_data["target_roas"] = row.bidding_strategy.target_roas.target_roas
                
                strategies.append(strategy_data)
            
            return {
                "success": True,
                "total_strategies": len(strategies),
                "strategies": strategies,
                "summary": {
                    "target_cpa_strategies": len([s for s in strategies if s["type"] == "TARGET_CPA"]),
                    "target_roas_strategies": len([s for s in strategies if s["type"] == "TARGET_ROAS"]),
                    "maximize_conversions": len([s for s in strategies if s["type"] == "MAXIMIZE_CONVERSIONS"]),
                    "maximize_clicks": len([s for s in strategies if s["type"] == "MAXIMIZE_CLICKS"]),
                }
            }
            
        except GoogleAdsException as e:
            logger.error(f"Failed to list bidding strategies: {e}")
            raise
    
    async def get_device_performance(
        self,
        customer_id: str,
        campaign_id: Optional[str] = None,
        date_range: str = "LAST_30_DAYS"
    ) -> Dict[str, Any]:
        """Get performance breakdown by device type (mobile, desktop, tablet)."""
        try:
            client = self.auth_manager.get_client(customer_id)
            googleads_service = client.get_service("GoogleAdsService")
            
            query = f"""
                SELECT
                    segments.device,
                    metrics.clicks,
                    metrics.impressions,
                    metrics.cost_micros,
                    metrics.conversions,
                    metrics.conversions_value,
                    metrics.ctr,
                    metrics.average_cpc,
                    campaign.name,
                    campaign.id
                FROM campaign
                WHERE segments.date DURING {date_range}
            """
            
            if campaign_id:
                query += f" AND campaign.id = {campaign_id}"
            
            query += " ORDER BY metrics.cost_micros DESC"
            
            response = googleads_service.search(
                customer_id=customer_id, query=query
            )
            
            device_performance = {}
            total_cost = 0
            total_conversions = 0
            
            for row in response:
                device = str(row.segments.device.name)
                cost = row.metrics.cost_micros / 1_000_000
                conversions = float(row.metrics.conversions)
                conversion_value = float(row.metrics.conversions_value)
                clicks = int(row.metrics.clicks)
                
                total_cost += cost
                total_conversions += conversions
                
                if device not in device_performance:
                    device_performance[device] = {
                        "device": device,
                        "clicks": 0,
                        "impressions": 0,
                        "cost": 0,
                        "conversions": 0,
                        "conversion_value": 0,
                    }
                
                device_performance[device]["clicks"] += clicks
                device_performance[device]["impressions"] += int(row.metrics.impressions)
                device_performance[device]["cost"] += cost
                device_performance[device]["conversions"] += conversions
                device_performance[device]["conversion_value"] += conversion_value
            
            # Calculate metrics for each device
            device_analysis = []
            for device, data in device_performance.items():
                cost = data["cost"]
                conversions = data["conversions"]
                clicks = data["clicks"]
                conversion_value = data["conversion_value"]
                
                ctr = (clicks / data["impressions"] * 100) if data["impressions"] > 0 else 0
                cost_per_conversion = cost / conversions if conversions > 0 else float('inf')
                roas = conversion_value / cost if cost > 0 else 0
                conversion_rate = (conversions / clicks * 100) if clicks > 0 else 0
                
                device_analysis.append({
                    "device": device,
                    "performance": {
                        "clicks": clicks,
                        "impressions": data["impressions"],
                        "cost": round(cost, 2),
                        "conversions": conversions,
                        "conversion_value": round(conversion_value, 2),
                        "ctr": f"{ctr:.2%}",
                        "cost_per_conversion": round(cost_per_conversion, 2) if cost_per_conversion != float('inf') else "No conversions",
                        "roas": round(roas, 2),
                        "conversion_rate": f"{conversion_rate:.1f}%",
                    },
                    "share_of_spend": f"{(cost / total_cost * 100):.1f}%" if total_cost > 0 else "0.0%",
                    "share_of_conversions": f"{(conversions / total_conversions * 100):.1f}%" if total_conversions > 0 else "0.0%",
                })
            
            # Generate device optimization recommendations
            device_recommendations = self._generate_device_recommendations(device_analysis)
            
            return {
                "success": True,
                "campaign_id": campaign_id,
                "date_range": date_range,
                "total_cost": round(total_cost, 2),
                "total_conversions": total_conversions,
                "device_performance": device_analysis,
                "optimization_recommendations": device_recommendations,
            }
            
        except GoogleAdsException as e:
            logger.error(f"Failed to get device performance: {e}")
            raise
    
    def _analyze_adjustment_effectiveness(self, adjustments_performance: List[Dict]) -> Dict[str, Any]:
        """Analyze the effectiveness of current bid adjustments."""
        analysis = {
            "total_adjustments": len(adjustments_performance),
            "positive_adjustments": 0,
            "negative_adjustments": 0,
            "best_performing_adjustment": None,
            "worst_performing_adjustment": None,
            "recommendations": []
        }
        
        if not adjustments_performance:
            return analysis
        
        # Count positive/negative adjustments
        for adj in adjustments_performance:
            if adj["bid_modifier"] > 1.0:
                analysis["positive_adjustments"] += 1
            else:
                analysis["negative_adjustments"] += 1
        
        # Find best and worst performers by ROAS
        sorted_by_roas = sorted(adjustments_performance, key=lambda x: x["efficiency"]["roas"], reverse=True)
        analysis["best_performing_adjustment"] = sorted_by_roas[0]
        analysis["worst_performing_adjustment"] = sorted_by_roas[-1]
        
        # Generate recommendations
        best = sorted_by_roas[0]
        worst = sorted_by_roas[-1]
        
        if best["efficiency"]["roas"] > 2.0:
            analysis["recommendations"].append(f"✅ {best['target_name']} performing well with {best['bid_percentage']} adjustment")
        
        if worst["efficiency"]["roas"] < 1.0 and worst["performance"]["cost"] > 10:
            analysis["recommendations"].append(f"⚠️ {worst['target_name']} underperforming with {worst['bid_percentage']} adjustment - consider reducing")
        
        return analysis
    
    def _generate_device_recommendations(self, device_analysis: List[Dict]) -> List[str]:
        """Generate device-specific bid adjustment recommendations."""
        recommendations = []
        
        if len(device_analysis) < 2:
            return ["Need multiple device types to generate recommendations"]
        
        # Sort by ROAS to identify best/worst performers
        sorted_devices = sorted(device_analysis, key=lambda x: x["performance"]["roas"], reverse=True)
        
        best_device = sorted_devices[0]
        worst_device = sorted_devices[-1]
        
        # Best performer recommendation
        if best_device["performance"]["roas"] > 2.0:
            recommendations.append(f"🎯 {best_device['device']} is your best performer ({best_device['performance']['roas']:.2f}x ROAS) - consider +20-50% bid increase")
        
        # Worst performer recommendation  
        if worst_device["performance"]["roas"] < 1.0 and worst_device["performance"]["cost"] > 20:
            recommendations.append(f"🚨 {worst_device['device']} underperforming ({worst_device['performance']['roas']:.2f}x ROAS) - consider -30-50% bid decrease")
        
        # Mobile-specific recommendations
        mobile_device = next((d for d in device_analysis if d["device"].lower() == "mobile"), None)
        if mobile_device:
            mobile_conversion_rate = float(mobile_device["performance"]["conversion_rate"].rstrip('%'))
            if mobile_conversion_rate < 2.0:
                recommendations.append(f"📱 Mobile conversion rate low ({mobile_device['performance']['conversion_rate']}) - check mobile landing page experience")
        
        return recommendations
