"""Asset management tools for Google Ads API v21."""

from typing import Any, Dict, List, Optional
import base64
import structlog

from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException

logger = structlog.get_logger(__name__)


class AssetTools:
    """Asset management tools."""
    
    def __init__(self, auth_manager, error_handler):
        self.auth_manager = auth_manager
        self.error_handler = error_handler
        
    async def upload_image_asset(
        self,
        customer_id: str,
        image_data: str,
        name: str
    ) -> Dict[str, Any]:
        """Upload an image asset.
        
        Args:
            customer_id: The customer ID
            image_data: Base64 encoded image data or file path
            name: Name for the asset
        """
        try:
            client = self.auth_manager.get_client(customer_id)
            asset_service = client.get_service("AssetService")
            
            # Create asset operation
            asset_operation = client.get_type("AssetOperation")
            asset = asset_operation.create
            
            # Set asset name
            asset.name = name
            
            # Handle image data (assume base64 encoded for now)
            try:
                # If it's a base64 string, decode it
                if image_data.startswith('data:image'):
                    # Remove data URL prefix
                    image_data = image_data.split(',')[1]
                
                image_bytes = base64.b64decode(image_data)
            except Exception:
                # If decoding fails, assume it's a file path and read it
                try:
                    with open(image_data, 'rb') as f:
                        image_bytes = f.read()
                except Exception as e:
                    return {
                        "success": False,
                        "error": f"Failed to read image data: {str(e)}",
                        "error_type": "ValidationError"
                    }
            
            # Set image asset data
            asset.image_asset.data = image_bytes
            
            # Set asset type
            asset.type_ = client.enums.AssetTypeEnum.IMAGE
            
            # Create the asset
            response = asset_service.mutate_assets(
                customer_id=customer_id,
                operations=[asset_operation],
            )
            
            # Extract asset ID from response
            asset_resource_name = response.results[0].resource_name
            asset_id = asset_resource_name.split("/")[-1]
            
            logger.info(
                f"Uploaded image asset",
                customer_id=customer_id,
                asset_id=asset_id,
                name=name,
                size_bytes=len(image_bytes)
            )
            
            return {
                "success": True,
                "asset_id": asset_id,
                "asset_resource_name": asset_resource_name,
                "name": name,
                "type": "IMAGE",
                "size_bytes": len(image_bytes)
            }
            
        except GoogleAdsException as e:
            logger.error(f"Failed to upload image asset: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_type": "GoogleAdsException"
            }
        except Exception as e:
            logger.error(f"Unexpected error uploading image asset: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_type": "UnexpectedError"
            }
    
    async def upload_text_asset(
        self,
        customer_id: str,
        text: str,
        name: str
    ) -> Dict[str, Any]:
        """Create a text asset."""
        try:
            client = self.auth_manager.get_client(customer_id)
            asset_service = client.get_service("AssetService")
            
            # Create asset operation
            asset_operation = client.get_type("AssetOperation")
            asset = asset_operation.create
            
            # Set asset properties
            asset.name = name
            asset.text_asset.text = text
            asset.type_ = client.enums.AssetTypeEnum.TEXT
            
            # Create the asset
            response = asset_service.mutate_assets(
                customer_id=customer_id,
                operations=[asset_operation],
            )
            
            # Extract asset ID from response
            asset_resource_name = response.results[0].resource_name
            asset_id = asset_resource_name.split("/")[-1]
            
            logger.info(
                f"Created text asset",
                customer_id=customer_id,
                asset_id=asset_id,
                name=name,
                text_length=len(text)
            )
            
            return {
                "success": True,
                "asset_id": asset_id,
                "asset_resource_name": asset_resource_name,
                "name": name,
                "type": "TEXT",
                "text": text,
                "text_length": len(text)
            }
            
        except GoogleAdsException as e:
            logger.error(f"Failed to create text asset: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_type": "GoogleAdsException"
            }
        except Exception as e:
            logger.error(f"Unexpected error creating text asset: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_type": "UnexpectedError"
            }
    
    async def list_assets(
        self,
        customer_id: str,
        asset_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """List all assets with optional type filter."""
        try:
            client = self.auth_manager.get_client(customer_id)
            googleads_service = client.get_service("GoogleAdsService")
            
            # Build query
            query = """
                SELECT
                    asset.id,
                    asset.name,
                    asset.type,
                    asset.text_asset.text,
                    asset.image_asset.file_size
                FROM asset
            """
            
            # Add type filter if specified
            if asset_type:
                asset_type_upper = asset_type.upper()
                query += f" WHERE asset.type = {asset_type_upper}"
                
            response = googleads_service.search(
                customer_id=customer_id, query=query
            )
            
            assets = []
            for row in response:
                asset_data = {
                    "id": str(row.asset.id),
                    "name": str(row.asset.name) if row.asset.name else "",
                    "type": str(row.asset.type_.name)
                }
                
                # Add type-specific data
                if row.asset.type_.name == "TEXT" and hasattr(row.asset, 'text_asset'):
                    asset_data["text"] = str(row.asset.text_asset.text)
                    asset_data["text_length"] = len(row.asset.text_asset.text)
                elif row.asset.type_.name == "IMAGE" and hasattr(row.asset, 'image_asset'):
                    if hasattr(row.asset.image_asset, 'file_size'):
                        asset_data["file_size_bytes"] = row.asset.image_asset.file_size
                
                assets.append(asset_data)
            
            return {
                "success": True,
                "assets": assets,
                "count": len(assets),
                "filtered_by_type": asset_type is not None
            }
            
        except GoogleAdsException as e:
            logger.error(f"Failed to list assets: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_type": "GoogleAdsException"
            }
        except Exception as e:
            logger.error(f"Unexpected error listing assets: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_type": "UnexpectedError"
            }
