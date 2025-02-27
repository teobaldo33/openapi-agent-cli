#!/usr/bin/env python3
import argparse
import json
import os
import sys
import signal
from dotenv import load_dotenv
from anthropic import Anthropic
import time

# Import from the openapi_agent_tools library
from openapi_agent_tools.parse_openapi import generate_tools_from_openapi, load_openapi_from_url
from openapi_agent_tools.schema_validator import validate_and_fix_tools

from main import chat_with_claude, set_client, get_tool_execution_history, clear_tool_execution_history, set_api_key_header
from ascii_art import (
    clear_screen, print_logo, print_bot_message, print_user_prompt, 
    print_thinking_animation, print_status_update, print_tool_execution_summary
)
from logger import initialize_logging, logger, get_current_log_file

def load_tools(tools_file=None, openapi_url=None):
    """
    Load tools from a file or generate from an OpenAPI URL

    Args:
        tools_file (str): Path to a JSON file containing tools
        openapi_url (str): URL to an OpenAPI specification

    Returns:
        list: List of tools
        
    """
    tools = None
    
    # Load from file
    if tools_file and os.path.exists(tools_file):
        try:
            with open(tools_file, "r", encoding="utf-8") as f:
                tools = json.load(f)
                print_status_update(f"Loaded {len(tools)} tools from {tools_file}", "info")
        except Exception as e:
            print(f"Error loading tools from {tools_file}: {e}")
            sys.exit(1)
    
    # Generate from OpenAPI spec URL
    elif openapi_url:
        try:
            print(f"Retrieving OpenAPI spec from {openapi_url}...")
            
            # Use the specialized function to load OpenAPI spec from URL
            openapi_spec = load_openapi_from_url(openapi_url)
            
            # Extract base URL for the API endpoints
            base_url = openapi_url.rsplit("/", 1)[0]
            if 'servers' in openapi_spec and openapi_spec['servers'] and 'url' in openapi_spec['servers'][0]:
                base_url = openapi_spec['servers'][0]['url']
            
            print(f"Generating tools from OpenAPI spec...")
            tools = generate_tools_from_openapi(openapi_spec, base_url=base_url)
            print_status_update(f"Generated {len(tools)} tools from OpenAPI spec", "info")
        except Exception as e:
            print(f"Error retrieving tools from {openapi_url}: {e}")
            sys.exit(1)
    else:
        print("Error: Please specify a tools file or an OpenAPI URL")
        sys.exit(1)
    
    # Validate and fix tools to be compatible with Claude
    if tools:
        print_status_update(f"Validating and fixing {len(tools)} tools to be compatible with Claude...", "info")
        fixed_tools, failed_tools = validate_and_fix_tools(tools)
        
        if failed_tools:
            print_status_update(f"Warning: {len(failed_tools)} tools couldn't be fixed and will be removed", "warning")
            for failed in failed_tools:
                print_status_update(f"  - {failed.get('tool', {}).get('name', 'unknown')}: {failed.get('error')}", "warning")
        
        print_status_update(f"Successfully validated {len(fixed_tools)} tools", "success")
        return fixed_tools
    
    return []

def handle_exit(signum, frame):
    """Handle exit signal gracefully"""
    print("\n\nThank you for using OpenAPI Agent! Goodbye!")
    sys.exit(0)

def status_callback(message, status_type="info"):
    """Callback function to display status updates during processing"""
    print_status_update(message, status_type)

def conversation_mode(tools, model, max_tokens, verbose):
    """
    Run the agent in interactive conversation mode
    """
    # Register signal handler for Ctrl+C
    signal.signal(signal.SIGINT, handle_exit)
    
    # Clear tool execution history when starting a new conversation
    clear_tool_execution_history()
    
    # Display welcome message
    clear_screen()
    print_logo()
    print_bot_message("Welcome to OpenAPI Agent! I can interact with API endpoints for you. Type 'exit' to quit.")
    print_status_update("Type 'tools' to see a summary of tools used in this session", "info")
    print_status_update("Type 'errors' to see detailed error information for failed tool calls", "info")
    
    # Store conversation history for context
    messages = []
    
    while True:
        # Get user input
        user_query = print_user_prompt()
        
        # Exit condition
        if user_query.lower() in ['exit', 'quit', 'bye']:
            print_bot_message("Thank you for using OpenAPI Agent! Goodbye!")
            break
            
        # Command to display tool executions
        if user_query.lower() == 'tools':
            print_tool_execution_summary(get_tool_execution_history())
            continue
            
        # Command to display error details
        if user_query.lower() == 'errors':
            tool_history = get_tool_execution_history()
            failures = [exec for exec in tool_history if not exec.get("success", False)]
            if failures:
                print_tool_execution_summary(failures)
            else:
                print_status_update("No failed tool calls in this session", "info")
            continue
        
        # Additional command to show log file location
        if user_query.lower() == 'log':
            log_file = get_current_log_file()
            if log_file:
                print_status_update(f"Current log file: {log_file}", "info")
            else:
                print_status_update("Logging is not enabled", "warning")
            continue
        
        # Add user message to history
        if messages:
            messages.append({"role": "user", "content": user_query})
            
        # Show thinking animation
        if not verbose:
            print_thinking_animation(3)
        
        # Call Claude with the full conversation history
        if messages:
            # Use existing conversation
            response = chat_with_claude(
                user_query=user_query,
                tools=tools,
                model=model,
                max_tokens=max_tokens,
                verbose=verbose,
                messages=messages,
                status_callback=status_callback if not verbose else None
            )
        else:
            # Start new conversation
            response = chat_with_claude(
                user_query=user_query,
                tools=tools,
                model=model,
                max_tokens=max_tokens,
                verbose=verbose,
                status_callback=status_callback if not verbose else None
            )
            # Update messages with the response
            messages = [
                {"role": "user", "content": user_query},
                {"role": "assistant", "content": response.content}
            ]
        
        # Extract and display text response
        response_text = ""
        for content in response.content:
            if content.type == "text":
                response_text += content.text + "\n"
        
        # Display the bot's response
        print_bot_message(response_text.strip())
        
        # Show tool usage summary if any tools were used
        tool_history = get_tool_execution_history()
        if tool_history:
            print_status_update(f"{len(tool_history)} tools were used in this conversation. Type 'tools' to see details.", "info")

def main():
    # Configure argument parser
    parser = argparse.ArgumentParser(
        description='OpenAPI Agent - Interface with APIs using Claude AI',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    # Configuration arguments
    config_group = parser.add_argument_group('Configuration')
    config_group.add_argument('--api-key', dest='api_key', help='Anthropic API key')
    config_group.add_argument('--model', default='claude-3-7-sonnet-20250219', 
                        help='Claude model to use')
    config_group.add_argument('--max-tokens', type=int, default=1024,
                        help='Maximum tokens for response')
    
    # API Authentication
    auth_group = parser.add_argument_group('API Authentication')
    auth_group.add_argument('--target-api-key', help='API key for the target API')
    auth_group.add_argument('--auth-scheme', default='Bearer', 
                      help='Authentication scheme (Bearer, Basic, etc.)')
    auth_group.add_argument('--auth-header', default='Authorization',
                      help='Authentication header name')
    auth_group.add_argument('--extra-headers', help='Extra headers in JSON format')
    
    # Tools arguments
    tools_group = parser.add_argument_group('Tools')
    tools_source = tools_group.add_mutually_exclusive_group(required=True)
    tools_source.add_argument('--tools-file', help='JSON file containing tools')
    tools_source.add_argument('--openapi-url', help='OpenAPI specification URL')
    tools_group.add_argument('--save-tools', help='Save generated tools to file')
    
    # Input/Output arguments
    io_group = parser.add_argument_group('Input/Output')
    query_source = io_group.add_mutually_exclusive_group()
    query_source.add_argument('--query', help='Query to send to Claude')
    query_source.add_argument('--query-file', help='File containing the query')
    io_group.add_argument('--output-file', help='File to save the response')
    io_group.add_argument('--verbose', '-v', action='store_true', help='Verbose mode')
    io_group.add_argument('--interactive', '-i', action='store_true', help='Interactive conversation mode')
    
    # Logging options
    log_group = parser.add_argument_group('Logging')
    log_group.add_argument('--log-dir', default='logs', help='Directory to store log files')
    log_group.add_argument('--log-file', help='Specific log filename (default: auto-generated)')
    log_group.add_argument('--disable-logging', action='store_true', 
                     help='Disable detailed logging to file')
    
    args = parser.parse_args()
    
    # Setup logging unless disabled
    if not args.disable_logging:
        log_path = initialize_logging(log_dir=args.log_dir, log_file=args.log_file)
        print_status_update(f"Detailed logs will be written to {log_path}", "info")
        logger.info("OpenAPI Agent started")
        logger.info(f"Command line: {' '.join(sys.argv)}")
    
    # Load environment variables
    load_dotenv()
    if logger:
        logger.debug("Environment variables loaded from .env")
    
    # Get Anthropic API key
    anthropic_api_key = args.api_key or os.getenv("ANTHROPIC_API_KEY")
    if not anthropic_api_key:
        print("Error: Anthropic API key is required. Use --api-key or set ANTHROPIC_API_KEY")
        if logger:
            logger.error("Anthropic API key not provided")
        sys.exit(1)
    
    # Initialize Anthropic client
    client = Anthropic(api_key=anthropic_api_key)
    set_client(client)
    if logger:
        logger.debug("Anthropic client initialized")
    
    # Setup target API authentication if provided
    target_api_key = args.target_api_key or os.getenv("TARGET_API_KEY")
    if target_api_key:
        auth_header = args.auth_header
        auth_value = f"{args.auth_scheme} {target_api_key}" if args.auth_scheme else target_api_key
        
        print_status_update(f"Setting up authentication for target API", "info")
        set_api_key_header(auth_header, auth_value)
        
        if logger:
            logger.info(f"API authentication configured with header: {auth_header}")
        
        if args.verbose:
            print(f"Using authentication header: {auth_header}: {args.auth_scheme} [API KEY HIDDEN]")
    
    # Process extra headers if provided
    if args.extra_headers:
        try:
            if os.path.exists(args.extra_headers):
                # Load from file if it's a path
                with open(args.extra_headers, 'r') as f:
                    extra_headers = json.load(f)
            else:
                # Parse JSON string
                extra_headers = json.loads(args.extra_headers)
                
            # Set each extra header
            for header_name, header_value in extra_headers.items():
                set_api_key_header(header_name, header_value)
                
            if logger:
                logger.info(f"Added {len(extra_headers)} extra headers")
                
            if args.verbose:
                print(f"Added {len(extra_headers)} extra headers to all API requests")
                
        except json.JSONDecodeError:
            error_msg = "Could not parse extra headers. Please provide valid JSON."
            print(f"Error: {error_msg}")
            if logger:
                logger.error(error_msg)
            sys.exit(1)
        except Exception as e:
            error_msg = f"Error setting extra headers: {str(e)}"
            print(f"Error: {error_msg}")
            if logger:
                logger.error(error_msg)
            sys.exit(1)
    
    # Load tools
    start_time = time.time()
    tools = load_tools(args.tools_file, args.openapi_url)
    load_time = time.time() - start_time
    
    if logger:
        logger.info(f"Loaded {len(tools)} tools in {load_time:.2f}s")
    
    # Save tools if requested
    if args.save_tools:
        with open(args.save_tools, "w", encoding="utf-8") as f:
            json.dump(tools, f, indent=2, ensure_ascii=False)
        if logger:
            logger.info(f"Tools saved to {args.save_tools}")
        if args.verbose:
            print(f"Tools saved to {args.save_tools}")
    
    # Run in interactive mode if specified
    if args.interactive:
        if logger:
            logger.info("Starting interactive conversation mode")
        conversation_mode(tools, args.model, args.max_tokens, args.verbose)
        if logger:
            logger.info("Interactive conversation ended")
        return
    
    # Otherwise, run in single query mode
    if not args.query and not args.query_file:
        print("Error: Please provide a query with --query or --query-file, or use --interactive mode")
        if logger:
            logger.error("No query provided")
        sys.exit(1)
    
    # Get query
    if args.query:
        user_query = args.query
    else:
        with open(args.query_file, "r", encoding="utf-8") as f:
            user_query = f.read().strip()
    
    if args.verbose:
        print(f"User query: {user_query}")
        print(f"Using model: {args.model}")
        print(f"Number of available tools: {len(tools)}")
    
    # Clear tool execution history when starting a new query
    clear_tool_execution_history()
    
    # Call Claude with status updates
    response = chat_with_claude(
        user_query, 
        tools, 
        args.model, 
        args.max_tokens, 
        verbose=args.verbose,
        status_callback=status_callback if not args.verbose else None
    )
    
    # Display final response
    print("\nClaude's final response:")
    final_response = ""
    for content in response.content:
        if content.type == "text":
            print(content.text)
            final_response += content.text + "\n"
    
    # Display tool usage summary
    tool_history = get_tool_execution_history()
    if tool_history:
        print_tool_execution_summary(tool_history)
    
    # Save response if requested
    if args.output_file:
        with open(args.output_file, "w", encoding="utf-8") as f:
            f.write(final_response)
            
            # Also save tool execution history if tools were used
            if tool_history:
                f.write("\n\n--- TOOL EXECUTION HISTORY ---\n\n")
                f.write(json.dumps(tool_history, indent=2))
                
        if logger:
            logger.info(f"Response saved to {args.output_file}")
        if args.verbose:
            print(f"Response saved to {args.output_file}")
    
    # At the end of main
    if logger:
        logger.info("OpenAPI Agent finished execution")
        if args.output_file:
            logger.info(f"Response saved to {args.output_file}")
        
        # Show log file path
        log_file = get_current_log_file()
        if log_file:
            print_status_update(f"Detailed logs written to {log_file}", "info")

if __name__ == "__main__":
    main()
