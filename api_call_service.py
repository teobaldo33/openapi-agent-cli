import requests
import json
import copy
import time

# Import logger if available, use dummy function if not
try:
    from logger import log_request, log_response, logger
except ImportError:
    # Dummy logging functions if logger module is not available
    def log_request(*args, **kwargs): pass
    def log_response(*args, **kwargs): pass
    logger = None

# Store default headers that will be included in every request
_default_headers = {
    "Content-Type": "application/json",
    "Accept": "application/json"
}

def set_default_header(header_name, header_value):
    """
    Set a default header to be included in all API calls
    
    Args:
        header_name (str): Header name
        header_value (str): Header value
    """
    global _default_headers
    _default_headers[header_name] = header_value
    return _default_headers

def get_default_headers():
    """
    Get all default headers
    
    Returns:
        dict: Default headers dictionary
    """
    global _default_headers
    return copy.deepcopy(_default_headers)

def clear_default_headers():
    """Reset default headers to initial state"""
    global _default_headers
    _default_headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    return _default_headers

def api_call_service(url, method, requestBody=None, params=None, headers=None, timeout=30):
    """
    Service for calling external APIs.
    
    Args:
        url (str): URL to call
        method (str): HTTP method to use (GET, POST, PATCH, DELETE)
        requestBody (dict, optional): Request body in JSON
        params (dict, optional): URL parameters
        headers (dict, optional): HTTP headers (these will override default headers)
        timeout (int, optional): Timeout in seconds
        
    Returns:
        dict: API response or error message
    """
    if not url:
        return {"error": "URL is required"}
    if not method:
        return {"error": "Method is required"}
    
    # Start with default headers
    request_headers = get_default_headers()
    
    # Override with any provided headers
    if headers:
        for key, value in headers.items():
            request_headers[key] = value
    
    try:
        # Log request details for debugging
        debug_info = {
            "method": method,
            "url": url,
            # Mask authorization headers in logs for security
            "headers": mask_sensitive_headers(request_headers),
            "params": params,
            "requestBody": requestBody
        }
        
        # Log the request
        log_request(method, url, request_headers, params, requestBody)
        
        # Make the request and measure duration
        start_time = time.time()
        
        response = requests.request(
            method=method,
            url=url,
            json=requestBody,
            params=params,
            headers=request_headers,
            timeout=timeout
        )
        
        # Calculate request duration
        duration = time.time() - start_time
        
        # Log the response
        log_response(response, duration)
        
        # Try to parse the response as JSON
        try:
            result_data = response.json()
            
            # If the result is a list, wrap it in a dictionary
            if isinstance(result_data, list):
                result = {"data": result_data, "status_code": response.status_code}
            else:
                # If it's already a dictionary, just add the status code
                result = result_data
                result["status_code"] = response.status_code
        except json.JSONDecodeError:
            # If response is not valid JSON, return raw text
            result = {"text": response.text, "status_code": response.status_code}
        
        if response.status_code >= 400:
            # Enhanced error information
            error_msg = f"API call failed with status code {response.status_code}"
            
            # Add response reason if available
            if hasattr(response, 'reason') and response.reason:
                error_msg += f": {response.reason}"
                
            # Include detailed debug info for better diagnostics
            result["error"] = error_msg
            result["request"] = debug_info
            
            # Check for authentication errors
            if response.status_code == 401:
                result["error"] = f"Authentication failed (401): Check your API key"
            elif response.status_code == 403:
                result["error"] = f"Access forbidden (403): Check your API key permissions"
            
            # Try to extract more detailed error info from the response
            if isinstance(result_data, dict):
                if "message" in result_data:
                    result["error_message"] = result_data["message"]
                elif "error" in result_data:
                    if isinstance(result_data["error"], dict) and "message" in result_data["error"]:
                        result["error_message"] = result_data["error"]["message"]
                    else:
                        result["error_message"] = result_data["error"]
                
        return result
    except requests.RequestException as e:
        # Log the exception
        if logger:
            logger.error(f"Request exception: {str(e)}")
        
        # Enhanced exception handling with request details
        return {
            "error": f"Request failed: {str(e)}",
            "exception_type": type(e).__name__,
            "request": debug_info,
            "status_code": 500
        }

def mask_sensitive_headers(headers):
    """
    Mask sensitive header values for safe logging
    
    Args:
        headers (dict): Headers dictionary
        
    Returns:
        dict: Dictionary with masked sensitive values
    """
    if not headers:
        return {}
        
    masked_headers = copy.deepcopy(headers)
    sensitive_headers = ['authorization', 'x-api-key', 'api-key', 'token', 'apikey']
    
    for header, value in masked_headers.items():
        if header.lower() in sensitive_headers:
            # Keep first 4 chars and mask the rest
            if value and len(value) > 8:
                type_part = value.split(' ')[0] if ' ' in value else ""
                if type_part and len(type_part) < len(value):
                    # For headers like "Bearer xyz123"
                    masked_headers[header] = f"{type_part} {'*' * 8}"
                else:
                    # For direct API keys
                    masked_headers[header] = f"{value[:4]}{'*' * 8}"
            else:
                masked_headers[header] = "********"
                
    return masked_headers