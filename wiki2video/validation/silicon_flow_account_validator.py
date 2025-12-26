
"""
SiliconFlow account validator for checking API token and account balance.

This validator helps validate how many balance left in this account, and whether the token is legit.
Add a constant of min_balance, and we need balance > 100.

API Response format:
{
  "code": 20000,
  "message": "OK",
  "status": true,
  "data": {
    "id": "userid",
    "name": "username",
    "image": "user_avatar_image_url",
    "email": "user_email_address",
    "isAdmin": false,
    "balance": "0.88",
    "status": "normal",
    "introduction": "",
    "role": "",
    "chargeBalance": "88.00",
    "totalBalance": "88.88"
  }
}
"""

import requests
from typing import Dict, Any, Optional
from pathlib import Path

try:
    from .base_validator import BaseValidator
except ImportError:
    from base_validator import BaseValidator

from wiki2video.config.config_manager import config


class SiliconFlowAccountValidator(BaseValidator):
    """Validator for SiliconFlow API account status and balance."""
    
    # Constants
    MIN_BALANCE = 100.0  # Minimum required balance
    API_URL = "https://api.siliconflow.cn/v1/user/info"
    TIMEOUT = 10  # Request timeout in seconds
    
    def __init__(self):
        super().__init__("silicon_flow_account_validator")
    
    def validate(self, project_path: Path) -> Dict[str, Any]:
        """
        Validate SiliconFlow account status and balance.
        
        Args:
            project_path: Path to the project directory (not used for this validator)
            
        Returns:
            Dict containing validation results
        """
        errors = []
        warnings = []
        details = {}
        
        # Get API token from environment
        api_token = self._get_api_token()
        if not api_token:
            return {
                "valid": False,
                "errors": ["SiliconFlow API token not found. Set SILICONFLOW_API_TOKEN environment variable."],
                "warnings": [],
                "details": {}
            }
        
        # Make API request to check account status
        try:
            account_info = self._fetch_account_info(api_token)
            if account_info is None:
                return {
                    "valid": False,
                    "errors": ["Failed to fetch account information from SiliconFlow API"],
                    "warnings": [],
                    "details": {}
                }
            
            # Validate account status
            status_result = self._validate_account_status(account_info)
            errors.extend(status_result["errors"])
            warnings.extend(status_result["warnings"])
            details.update(status_result["details"])
            
            # Validate balance
            balance_result = self._validate_balance(account_info)
            errors.extend(balance_result["errors"])
            warnings.extend(balance_result["warnings"])
            details.update(balance_result["details"])
            
        except Exception as e:
            return {
                "valid": False,
                "errors": [f"Error validating SiliconFlow account: {str(e)}"],
                "warnings": [],
                "details": {"error_type": type(e).__name__}
            }
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "details": details
        }
    
    def _get_api_token(self) -> Optional[str]:
        """Get SiliconFlow API token from environment variables."""
        platform = config.get("platforms", "text_to_video")
        token = config.get(platform, "api_key") if platform else None
        return token
    
    def _fetch_account_info(self, api_token: str) -> Optional[Dict[str, Any]]:
        """Fetch account information from SiliconFlow API."""
        headers = {"Authorization": f"Bearer {api_token}"}
        
        try:
            response = requests.get(
                self.API_URL,
                headers=headers,
                timeout=self.TIMEOUT
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("code") == 20000 and data.get("status"):
                    return data.get("data")
                else:
                    print(f"API returned error: {data.get('message', 'Unknown error')}")
                    return None
            else:
                print(f"HTTP error: {response.status_code} - {response.text}")
                return None
                
        except requests.exceptions.Timeout:
            print("Request timeout")
            return None
        except requests.exceptions.RequestException as e:
            print(f"Request error: {e}")
            return None
        except Exception as e:
            print(f"Unexpected error: {e}")
            return None
    
    def _validate_account_status(self, account_info: Dict[str, Any]) -> Dict[str, Any]:
        """Validate account status and basic information."""
        errors = []
        warnings = []
        details = {}
        
        # Check if account is active
        status = account_info.get("status", "unknown")
        if status != "normal":
            errors.append(f"Account status is not normal: {status}")
        else:
            details["account_status"] = "normal"
        
        # Check if user is admin (optional)
        is_admin = account_info.get("isAdmin", False)
        details["is_admin"] = is_admin
        
        # Get basic account info
        user_id = account_info.get("id", "unknown")
        user_name = account_info.get("name", "unknown")
        user_email = account_info.get("email", "unknown")
        
        details["user_id"] = user_id
        details["user_name"] = user_name
        details["user_email"] = user_email
        
        # Check if email is valid
        if user_email == "unknown" or not user_email:
            warnings.append("User email not available")
        
        return {
            "errors": errors,
            "warnings": warnings,
            "details": details
        }
    
    def _validate_balance(self, account_info: Dict[str, Any]) -> Dict[str, Any]:
        """Validate account balance."""
        errors = []
        warnings = []
        details = {}
        
        # Get balance information
        balance_str = account_info.get("balance", "0")
        charge_balance_str = account_info.get("chargeBalance", "0")
        total_balance_str = account_info.get("totalBalance", "0")
        
        try:
            balance = float(balance_str)
            charge_balance = float(charge_balance_str)
            total_balance = float(total_balance_str)
            
            details["balance"] = balance
            details["charge_balance"] = charge_balance
            details["total_balance"] = total_balance
            
            # Check if balance meets minimum requirement
            if balance < self.MIN_BALANCE:
                errors.append(f"Account balance ({balance}) is below minimum required ({self.MIN_BALANCE})")
            else:
                details["balance_sufficient"] = True
            
            # Check if total balance is reasonable
            if total_balance < self.MIN_BALANCE:
                warnings.append(f"Total balance ({total_balance}) is below recommended minimum ({self.MIN_BALANCE})")
            
            # Check balance ratio
            if total_balance > 0:
                balance_ratio = balance / total_balance
                details["balance_ratio"] = balance_ratio
                if balance_ratio < 0.1:  # Less than 10% of total balance
                    warnings.append(f"Available balance is only {balance_ratio:.1%} of total balance")
            
        except (ValueError, TypeError) as e:
            errors.append(f"Invalid balance format: {e}")
            details["balance_parse_error"] = str(e)
        
        return {
            "errors": errors,
            "warnings": warnings,
            "details": details
        }
    
    @classmethod
    def get_min_balance(cls) -> float:
        """Get the minimum required balance."""
        return cls.MIN_BALANCE
    
    @classmethod
    def set_min_balance(cls, min_balance: float) -> None:
        """Set the minimum required balance."""
        cls.MIN_BALANCE = min_balance
