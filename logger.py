import logging
import os
import json
import sys
import time
import re
from datetime import datetime
from logging.handlers import RotatingFileHandler

# Configure the logger
logger = logging.getLogger("openapi_agent")
logger.setLevel(logging.DEBUG)

# Global variable to hold the file handler
file_handler = None

# Regular expression to match emoji characters
EMOJI_PATTERN = re.compile(
    "["
    "\U0001F600-\U0001F64F"  # emoticons
    "\U0001F300-\U0001F5FF"  # symbols & pictographs
    "\U0001F680-\U0001F6FF"  # transport & map symbols
    "\U0001F700-\U0001F77F"  # alchemical symbols
    "\U0001F780-\U0001F7FF"  # Geometric Shapes
    "\U0001F800-\U0001F8FF"  # Supplemental Arrows-C
    "\U0001F900-\U0001F9FF"  # Supplemental Symbols and Pictographs
    "\U0001FA00-\U0001FA6F"  # Chess Symbols
    "\U0001FA70-\U0001FAFF"  # Symbols and Pictographs Extended-A
    "\U00002702-\U000027B0"  # Dingbats
    "\U000024C2-\U0001F251"
    "]+"
)

def initialize_logging(log_level=logging.DEBUG, log_dir="logs", log_file=None):
    """
    Initialize the logging system with console and file output.
    
    Args:
        log_level: Logging level (default: DEBUG)
        log_dir: Directory to store log files (default: logs)
        log_file: Specific log file name (default: auto-generate based on timestamp)
    
    Returns:
        The path to the log file
    """
    global file_handler, logger
    
    # Clear any existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Create logs directory if it doesn't exist
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Generate log filename if not provided
    if log_file is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = f"openapi_agent_{timestamp}.log"
    
    log_path = os.path.join(log_dir, log_file)
    
    try:
        # Create file handler with rotation (max 10MB, keep 5 backup files)
        # Explicitly set encoding to utf-8 to handle emojis and special characters
        file_handler = RotatingFileHandler(
            log_path, 
            maxBytes=10*1024*1024,  # 10 MB
            backupCount=5,
            encoding='utf-8',  # Explicitly set UTF-8 encoding
            errors='replace'   # Replace characters that can't be encoded
        )
        file_handler.setLevel(log_level)
        
        # Create console handler
        console_handler = logging.StreamHandler(stream=sys.stdout)
        console_handler.setLevel(logging.WARNING)  # Only warnings and errors to console by default
        
        # Create formatters
        file_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(name)s - %(message)s'
        )
        console_formatter = logging.Formatter(
            '%(levelname)s: %(message)s'
        )
        
        # Add formatters to handlers
        file_handler.setFormatter(file_formatter)
        console_handler.setFormatter(console_formatter)
        
        # Add handlers to logger
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        logger.debug(f"Logging initialized to {log_path}")
    except Exception as e:
        print(f"Warning: Error setting up logging: {str(e)}. Logging to file will be disabled.")
        # Set up console-only logging as fallback
        console_handler = logging.StreamHandler(stream=sys.stdout)
        console_handler.setLevel(logging.WARNING)
        console_formatter = logging.Formatter('%(levelname)s: %(message)s')
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
        
    return log_path

def remove_emojis(text):
    """Remove emojis from text to avoid encoding issues.
    
    Args:
        text (str): Input text that may contain emojis
        
    Returns:
        str: Text with emojis removed
    """
    if not text or not isinstance(text, str):
        return text
    return EMOJI_PATTERN.sub('', text)

def sanitize_for_logging(obj):
    """Recursively sanitize an object to remove emojis and other problematic characters.
    
    Args:
        obj: Object to sanitize (dict, list, str, etc.)
        
    Returns:
        Same type of object with sanitized strings
    """
    if isinstance(obj, str):
        return remove_emojis(obj)
    elif isinstance(obj, dict):
        return {k: sanitize_for_logging(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [sanitize_for_logging(item) for item in obj]
    elif hasattr(obj, "__dict__"):
        # For custom objects, sanitize their dict representation
        try:
            return sanitize_for_logging(obj.__dict__)
        except:
            return str(obj)
    else:
        return obj

class ComplexJSONEncoder(json.JSONEncoder):
    """
    Custom JSON encoder that handles non-serializable objects.
    """
    def default(self, obj):
        # Handle objects like TextBlock and other Anthropic response types
        if hasattr(obj, 'type') and hasattr(obj, 'text'):
            return {"type": obj.type, "text": sanitize_for_logging(obj.text)}
        elif hasattr(obj, 'type') and hasattr(obj, 'name') and hasattr(obj, 'input'):
            return {"type": obj.type, "name": obj.name, "input": obj.input}
        elif hasattr(obj, 'content'):
            # Handle objects with content attribute (like Claude responses)
            content_list = []
            for item in obj.content:
                if hasattr(item, 'type'):
                    if item.type == "text":
                        content_list.append({
                            "type": "text", 
                            "text": sanitize_for_logging(item.text)
                        })
                    elif item.type == "tool_use":
                        content_list.append({
                            "type": "tool_use", 
                            "name": item.name, 
                            "input": item.input
                        })
                    else:
                        content_list.append({"type": item.type})
                else:
                    content_list.append(str(item))
            return {"content": content_list}
        # Handle other special types
        try:
            return str(obj)
        except:
            return f"<Object of type {type(obj).__name__}>"

def log_dict(data, message="", level=logging.DEBUG):
    """
    Log dictionary data as formatted JSON.
    
    Args:
        data: Dictionary to log
        message: Optional message to include
        level: Logging level to use
    """
    if not logger.isEnabledFor(level):
        return
        
    try:
        # Sanitize data first to remove problematic characters
        sanitized_data = sanitize_for_logging(data)
        
        # Format with indentation for readability using our custom encoder
        formatted_data = json.dumps(
            sanitized_data, 
            indent=2, 
            ensure_ascii=True,  # Use ASCII encoding for better compatibility
            cls=ComplexJSONEncoder
        )
        
        # Log with message if provided
        if message:
            logger.log(level, f"{message}\n{formatted_data}")
        else:
            logger.log(level, formatted_data)
    except Exception as e:
        # Fallback if JSON serialization fails
        logger.error(f"Error logging dictionary: {str(e)}")
        logger.debug(f"Raw data type: {type(data)}")
        # Fallback to simple representation
        if isinstance(data, dict):
            simple_data = {k: str(v) for k, v in data.items()}
            logger.debug(f"Simplified data: {simple_data}")
        else:
            logger.debug(f"Raw data: {str(data)}")

def log_request(method, url, headers, params=None, data=None):
    """
    Log an API request with sensitive information masked.
    """
    from api_call_service import mask_sensitive_headers
    
    log_dict({
        "type": "request",
        "timestamp": time.time(),
        "method": method,
        "url": url,
        "headers": mask_sensitive_headers(headers),
        "params": params,
        "data": data
    }, "API Request", logging.DEBUG)

def log_response(response, duration):
    """
    Log an API response.
    """
    try:
        # Try to extract JSON data
        response_data = response.json() if hasattr(response, 'json') else response
        
        # Sanitize response data to remove problematic characters
        sanitized_response = sanitize_for_logging(response_data)
        
        log_dict({
            "type": "response",
            "timestamp": time.time(),
            "status_code": response.status_code if hasattr(response, 'status_code') else None,
            "duration": duration,
            "data": sanitized_response
        }, "API Response", logging.DEBUG)
    except Exception as e:
        logger.error(f"Error logging response: {str(e)}")
        # Fallback method
        try:
            if hasattr(response, 'text'):
                simplified_text = remove_emojis(response.text[:1000])
                logger.debug(f"Response text (truncated): {simplified_text}...")
            elif hasattr(response, 'content'):
                simplified_content = str(response.content)[:1000]
                logger.debug(f"Response content (truncated): {simplified_content}...")
            else:
                logger.debug(f"Response type: {type(response)}")
        except:
            logger.error("Failed to log response in fallback mode")

def log_tool_execution(tool_name, tool_input, result, duration, success):
    """
    Log a tool execution.
    """
    log_dict({
        "type": "tool_execution",
        "timestamp": time.time(),
        "tool_name": tool_name,
        "input": tool_input,
        "result": result,
        "duration": duration,
        "success": success
    }, f"Tool Execution: {tool_name}", logging.DEBUG)

def log_claude_request(messages, model, max_tokens):
    """
    Log a request to Claude API.
    """
    # Make a copy of messages to avoid modifying the original
    log_messages = []
    for msg in messages:
        if isinstance(msg, dict):
            msg_copy = msg.copy()
            if "content" in msg_copy:
                # Handle content that might be a list of complex objects
                if isinstance(msg_copy["content"], list):
                    safe_content = []
                    for item in msg_copy["content"]:
                        if isinstance(item, dict):
                            safe_content.append(item)
                        else:
                            # Convert to simple dict if it's a complex object
                            safe_content.append({"type": type(item).__name__, "str": str(item)})
                    msg_copy["content"] = safe_content
            log_messages.append(msg_copy)
        else:
            log_messages.append(str(msg))
    
    log_dict({
        "type": "claude_request",
        "timestamp": time.time(),
        "model": model,
        "max_tokens": max_tokens,
        "messages": log_messages
    }, "Claude API Request", logging.DEBUG)

def log_claude_response(response, duration):
    """
    Log a response from Claude API, with emoji and special character handling.
    """
    try:
        # Pre-process the response to sanitize any text content
        sanitized_response = sanitize_for_logging(response)
        
        log_dict({
            "type": "claude_response",
            "timestamp": time.time(),
            "duration": duration,
            "response": sanitized_response
        }, "Claude API Response", logging.DEBUG)
    except Exception as e:
        logger.error(f"Error logging Claude response: {str(e)}")
        # Fallback logging with minimal content
        try:
            response_summary = "Content: ["
            if hasattr(response, 'content'):
                for item in response.content:
                    if hasattr(item, 'type'):
                        response_summary += f"{item.type}, "
            response_summary += "]"
            logger.debug(f"Claude response summary: {response_summary}")
        except:
            logger.error("Failed to create response summary")

def get_current_log_file():
    """
    Get the path to the current log file.
    
    Returns:
        str: Path to the log file, or None if not initialized
    """
    global file_handler
    if file_handler is not None:
        return file_handler.baseFilename
    return None
