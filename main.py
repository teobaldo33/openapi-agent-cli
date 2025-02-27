import anthropic
import os
from dotenv import load_dotenv
from api_call_service import api_call_service, set_default_header, get_default_headers
import json
import time
import traceback

# Import logger if available
try:
    from logger import logger, log_tool_execution, log_claude_request, log_claude_response
except ImportError:
    # Create dummy logging functions if logger is not available
    def log_tool_execution(*args, **kwargs): pass
    def log_claude_request(*args, **kwargs): pass
    def log_claude_response(*args, **kwargs): pass
    logger = None

# Load environment variables from .env
load_dotenv()

# Global client variable that can be set from outside
client = None

# Function execution history
tool_execution_history = []

def set_client(anthropic_client):
    """Set the Anthropic client from outside"""
    global client
    client = anthropic_client

def get_client():
    """Get or initialize the Anthropic client"""
    global client
    if client is None:
        client = anthropic.Anthropic(
            api_key=os.getenv("ANTHROPIC_API_KEY")
        )
    return client

# Function to set API key header for external API calls
def set_api_key_header(header_name, header_value):
    """Set a default header for all API calls"""
    set_default_header(header_name, header_value)

# Function to get all default headers
def get_api_headers():
    """Get all default headers for API calls"""
    return get_default_headers()

def process_tool_use(tool_use, tools, verbose=False, callback=None):
    """Processes a specific tool call and returns the result"""
    start_time = time.time()
    
    # Record the tool use in the history
    tool_execution = {
        "tool_name": tool_use.name,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "input": tool_use.input,
        "result": None,
        "duration": 0,
        "success": False,
        "error_details": None
    }
    
    if logger:
        logger.debug(f"Processing tool use: {tool_use.name}")
    
    if verbose:
        print(f"\nClaude is requesting to use the tool: {tool_use.name}")
        print(f"Parameters: {json.dumps(tool_use.input, indent=2)}")
    
    # Notify via callback if provided
    if callback:
        callback(f"Using tool: {tool_use.name}", "tool_call")
    
    # if tool_use.name starts with api_call then call the api_call_service.py
    if tool_use.name.startswith("api_call"):
        if verbose:
            print(f"\nCalling tool: {tool_use.name}")
            print(f"Parameters: {json.dumps(tool_use.input, indent=2)}")
        url = tool_use.input.get("url")
        method = tool_use.input.get("method")
        requestBody = tool_use.input.get("requestBody")
        params = tool_use.input.get("params")
        
        # Get headers from input if provided, otherwise use default headers
        headers = tool_use.input.get("headers")
        
        # Call the API
        try:
            tool_result = api_call_service(url, method, requestBody, params, headers)
            
            # Check if the API call itself reported an error
            if "error" in tool_result:
                error_msg = tool_result["error"]
                status_code = tool_result.get("status_code", "unknown")
                
                # Store detailed error information
                tool_execution["error_details"] = {
                    "message": error_msg,
                    "status_code": status_code,
                    "response": tool_result
                }
                
                tool_execution["success"] = False
                
                if logger:
                    logger.error(f"Tool {tool_use.name} failed: {error_msg} (Status: {status_code})")
            else:
                tool_execution["success"] = True
                if logger:
                    logger.debug(f"Tool {tool_use.name} succeeded")
                
            tool_execution["result"] = tool_result
            
        except Exception as e:
            # Capture detailed exception info including stack trace
            exc_info = traceback.format_exc()
            error_msg = str(e)
            
            if logger:
                logger.error(f"Exception in tool {tool_use.name}: {error_msg}")
                logger.debug(f"Traceback: {exc_info}")
            
            tool_execution["result"] = {"error": error_msg}
            tool_execution["error_details"] = {
                "message": error_msg,
                "exception_type": type(e).__name__,
                "traceback": exc_info
            }
            
            if verbose:
                print(f"\nError using tool {tool_use.name}: {error_msg}")
                print(f"Exception details: {exc_info}")
            
            if callback:
                callback(f"Error using tool {tool_use.name}: {error_msg}", "error")
                
            return {
                "tool_use_id": tool_use.id,
                "content": json.dumps({"error": error_msg, "details": exc_info}, indent=2, ensure_ascii=False)
            }
        
        end_time = time.time()
        tool_execution["duration"] = round(end_time - start_time, 2)
        
        # Log the tool execution
        log_tool_execution(
            tool_execution["tool_name"],
            tool_execution["input"],
            tool_execution["result"],
            tool_execution["duration"],
            tool_execution["success"]
        )
        
        if verbose:
            print("\nTool result:")
            print(json.dumps(tool_result, indent=2))
            print(f"Tool execution took {tool_execution['duration']}s")
            if "error" in tool_result:
                print(f"Tool execution failed with error: {tool_result['error']}")
                if "status_code" in tool_result:
                    print(f"Status code: {tool_result['status_code']}")
        
        # Add to history
        global tool_execution_history
        tool_execution_history.append(tool_execution)
        
        # Notify via callback if provided
        if callback:
            status = "success" if tool_execution["success"] else "error"
            msg = f"Tool {tool_use.name} completed in {tool_execution['duration']}s"
            if not tool_execution["success"]:
                error_msg = tool_execution.get("error_details", {}).get("message", "Unknown error")
                status_code = tool_execution.get("error_details", {}).get("status_code", "")
                msg += f" with error: {error_msg}"
                if status_code:
                    msg += f" (Status: {status_code})"
            callback(msg, status)
        
        return {
            "tool_use_id": tool_use.id,
            "content": json.dumps(tool_result, indent=2, ensure_ascii=False)
        }
    
    return None

def get_tool_execution_history():
    """Return the tool execution history"""
    global tool_execution_history
    return tool_execution_history

def clear_tool_execution_history():
    """Clear the tool execution history"""
    global tool_execution_history
    tool_execution_history = []

def validate_tools(tools, verbose=False):
    """
    Validate and fix tools to comply with Anthropic API requirements
    - Tool names must be 64 characters or less
    
    Args:
        tools (list): List of tools to validate
        verbose (bool): Whether to print verbose output
        
    Returns:
        list: Validated tools
    """
    validated_tools = []
    
    for i, tool in enumerate(tools):
        valid_tool = {
            "name": tool["name"],
            "description": tool.get("description", ""),
            "input_schema": tool.get("input_schema", {})
        }
        
        # Check name length (max 64 chars)
        if len(valid_tool["name"]) > 64:
            original_name = valid_tool["name"]
            # Truncate name but try to keep meaningful prefix and suffix
            # Keep the method (get/post) and the last part of the endpoint
            parts = original_name.split('_')
            if len(parts) >= 3:  # api_call_get_something_something
                prefix = '_'.join(parts[:3])  # Keep api_call_get
                suffix = parts[-1]  # Keep last part
                
                # Calculate how much space we have left for middle parts
                remaining_chars = 64 - len(prefix) - len(suffix) - 2  # 2 for underscores
                
                if remaining_chars > 0:
                    # Add truncated middle parts
                    middle = '_'.join(parts[3:-1])
                    if len(middle) > remaining_chars:
                        middle = middle[:remaining_chars]
                    
                    valid_tool["name"] = f"{prefix}_{middle}_{suffix}"
                else:
                    # Not enough space, use simple truncation
                    valid_tool["name"] = original_name[:60] + "..."
            else:
                # Simple case, just truncate
                valid_tool["name"] = original_name[:60] + "..."
            
            if verbose:
                print(f"Tool name too long ({len(original_name)} chars), truncated:")
                print(f"  Original: {original_name}")
                print(f"  Truncated: {valid_tool['name']}")
        
        validated_tools.append(valid_tool)
    
    if verbose:
        print(f"Validated {len(validated_tools)} tools")
    
    return validated_tools

def chat_with_claude(user_query, tools, model="claude-3-5-haiku-latest", max_tokens=1024, verbose=False, messages=None, status_callback=None):
    """Manages a complete conversation with Claude, including multiple tool calls"""
    # Initialize the conversation
    if messages is None:
        messages = [{"role": "user", "content": user_query}]
    else:
        # Use existing conversation history
        messages.append({"role": "user", "content": user_query})
    
    if logger:
        logger.info(f"Starting conversation with Claude. Model: {model}, Max tokens: {max_tokens}")
        logger.debug(f"User query: {user_query}")
    
    current_client = get_client()
    max_iterations = 10  # Safety limit to avoid infinite loops
    iteration = 0
    
    # Validate tools before sending to API
    validated_tools = validate_tools(tools, verbose)
    
    while iteration < max_iterations:
        iteration += 1
        
        if logger:
            logger.debug(f"Starting conversation iteration {iteration}/{max_iterations}")
        
        # Update status via callback if provided
        if status_callback:
            status_callback(f"Waiting for Claude's response (iteration {iteration}/{max_iterations})...", "thinking")
        
        # Log Claude request
        log_claude_request(messages, model, max_tokens)
        
        # Send the conversation to Claude
        start_time = time.time()
        try:
            response = current_client.messages.create(
                model=model,
                max_tokens=max_tokens,
                tools=validated_tools,
                messages=messages
            )
            request_time = round(time.time() - start_time, 2)
            
            # Log Claude response
            log_claude_response(response, request_time)
            
            if logger:
                logger.debug(f"Claude response received in {request_time}s")
        except Exception as e:
            request_time = round(time.time() - start_time, 2)
            error_msg = str(e)
            if logger:
                logger.error(f"Error calling Claude API: {error_msg}")
                logger.debug(f"Request took {request_time}s before failing")
                logger.debug(f"Traceback: {traceback.format_exc()}")
            
            # Re-raise the exception
            raise
        
        # Update status via callback if provided
        if status_callback:
            status_callback(f"Response received in {request_time}s", "response")
        
        # Display Claude's text response
        if verbose:
            print("\nClaude's response (iteration", iteration, "):")
            print(f"Request took {request_time}s")
            has_text = False
            for content in response.content:
                if content.type == "text":
                    print(content.text)
                    has_text = True
        
        # Check if there's a tool call
        tool_use = None
        for content_block in response.content:
            if content_block.type == 'tool_use':
                tool_use = content_block
                break
        
        if not tool_use:
            # No tool call, this is the final response
            if verbose:
                print("\nConversation completed after", iteration, "iterations.")
            if logger:
                logger.info(f"Conversation completed after {iteration} iterations")
            return response
        
        if verbose:
            print("\ntool_use:", tool_use)
        
        # Process the tool call
        tool_result = process_tool_use(tool_use, tools, verbose, status_callback)
        
        if tool_result:
            # Add the assistant's response to history
            messages.append({
                "role": "assistant",
                "content": response.content
            })
            
            # Add the tool result to history
            messages.append({
                "role": "user", 
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": tool_result["tool_use_id"],
                        "content": tool_result["content"]
                    }
                ]
            })
    
    # If we reach the iteration limit
    if verbose:
        print("\nMaximum iteration limit reached.")
    if logger:
        logger.warning(f"Maximum iteration limit ({max_iterations}) reached")
    return response

def main():
    # Load tools from OpenAPI specification
    with open("/docs/tools.json", "r") as f:
        tools = json.load(f)

    user_query = "Get the statuses and correction types from the referentials, then give me the type-correction with id 14"
    print(f"\nUser query: {user_query}")
    
    # Use the conversation function
    final_response = chat_with_claude(user_query, tools, verbose=True)
    
    # Display the final response
    print("\nClaude's final response:")
    for content in final_response.content:
        if content.type == "text":
            print(content.text)

if __name__ == "__main__":
    main()
