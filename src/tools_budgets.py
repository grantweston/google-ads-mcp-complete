"""Budget management tools for Google Ads API v21."""

from typing import Any, Dict, List, Optional
import structlog

from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException

from .utils import currency_to_micros, micros_to_currency

logger = structlog.get_logger(__name__)


class BudgetTools:
    """Budget management tools."""
    
    def __init__(self, auth_manager, error_handler):
        self.auth_manager = auth_manager
        self.error_handler = error_handler
        
    async def create_budget(
        self,
        customer_id: str,
        name: str,
        amount_micros: int,
        delivery_method: str = "STANDARD"
    ) -> Dict[str, Any]:
        """Create a shared campaign budget."""
        try:
            client = self.auth_manager.get_client(customer_id)
            budget_service = client.get_service("CampaignBudgetService")
            
            # Create budget operation
            budget_operation = client.get_type("CampaignBudgetOperation")
            budget = budget_operation.create
            
            # Set budget properties
            budget.name = name
            budget.amount_micros = amount_micros
            
            # Set delivery method
            if delivery_method.upper() == "ACCELERATED":
                budget.delivery_method = client.enums.BudgetDeliveryMethodEnum.ACCELERATED
            else:
                budget.delivery_method = client.enums.BudgetDeliveryMethodEnum.STANDARD
            
            # Create the budget
            response = budget_service.mutate_campaign_budgets(
                customer_id=customer_id,
                operations=[budget_operation],
            )
            
            # Extract budget ID from response
            budget_resource_name = response.results[0].resource_name
            budget_id = budget_resource_name.split("/")[-1]
            
            logger.info(
                f"Created campaign budget",
                customer_id=customer_id,
                budget_id=budget_id,
                name=name,
                amount=micros_to_currency(amount_micros)
            )
            
            return {
                "success": True,
                "budget_id": budget_id,
                "budget_resource_name": budget_resource_name,
                "name": name,
                "amount": micros_to_currency(amount_micros),
                "delivery_method": delivery_method.upper()
            }
            
        except GoogleAdsException as e:
            logger.error(f"Failed to create budget: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_type": "GoogleAdsException"
            }
        except Exception as e:
            logger.error(f"Unexpected error creating budget: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_type": "UnexpectedError"
            }
    
    async def update_budget(
        self,
        customer_id: str,
        budget_id: str,
        amount_micros: Optional[int] = None,
        name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update budget amount or settings."""
        try:
            client = self.auth_manager.get_client(customer_id)
            budget_service = client.get_service("CampaignBudgetService")
            
            # Create budget operation
            budget_operation = client.get_type("CampaignBudgetOperation")
            budget = budget_operation.update
            
            # Set resource name
            budget.resource_name = budget_service.campaign_budget_path(
                customer_id, budget_id
            )
            
            # Set update mask fields (API v21 compatible)
            from google.protobuf.field_mask_pb2 import FieldMask
            update_mask = FieldMask()
            paths = []
            
            if amount_micros is not None:
                budget.amount_micros = amount_micros
                paths.append("amount_micros")
                
            if name is not None:
                budget.name = name
                paths.append("name")
                
            update_mask.paths.extend(paths)
            budget_operation.update_mask = update_mask
            
            # Update the budget
            response = budget_service.mutate_campaign_budgets(
                customer_id=customer_id,
                operations=[budget_operation],
            )
            
            logger.info(
                f"Updated campaign budget",
                customer_id=customer_id,
                budget_id=budget_id,
                updated_fields=paths
            )
            
            return {
                "success": True,
                "budget_id": budget_id,
                "updated_fields": paths,
                "message": f"Successfully updated budget {budget_id}"
            }
            
        except GoogleAdsException as e:
            logger.error(f"Failed to update budget: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_type": "GoogleAdsException"
            }
        except Exception as e:
            logger.error(f"Unexpected error updating budget: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_type": "UnexpectedError"
            }
    
    async def list_budgets(
        self,
        customer_id: str
    ) -> Dict[str, Any]:
        """List all budgets."""
        try:
            client = self.auth_manager.get_client(customer_id)
            googleads_service = client.get_service("GoogleAdsService")
            
            query = """
                SELECT
                    campaign_budget.id,
                    campaign_budget.name,
                    campaign_budget.amount_micros,
                    campaign_budget.delivery_method,
                    campaign_budget.status
                FROM campaign_budget
            """
            
            response = googleads_service.search(
                customer_id=customer_id, query=query
            )
            
            budgets = []
            for row in response:
                budgets.append({
                    "id": str(row.campaign_budget.id),
                    "name": str(row.campaign_budget.name),
                    "amount": micros_to_currency(row.campaign_budget.amount_micros),
                    "amount_micros": row.campaign_budget.amount_micros,
                    "delivery_method": str(row.campaign_budget.delivery_method.name),
                    "status": str(row.campaign_budget.status.name)
                })
            
            return {
                "success": True,
                "budgets": budgets,
                "count": len(budgets)
            }
            
        except GoogleAdsException as e:
            logger.error(f"Failed to list budgets: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_type": "GoogleAdsException"
            }
        except Exception as e:
            logger.error(f"Unexpected error listing budgets: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_type": "UnexpectedError"
            }
