import os
import platform
import random
import sys
import time
import json  

OPENAPI_LOGO = [
    "  ____                            _____ _____                            _   ",
    " / __ \\                     /\\   |  __ \\_   _|     /\\                   | |  ",
    "| |  | |_ __   ___ _ __    /  \\  | |__) || |      /  \\   __ _  ___ _ __ | |_ ",
    "| |  | | '_ \\ / _ \\ '_ \\  / /\\ \\ |  ___/ || |     / /\\ \\ / _` |/ _ \\ '_ \\| __|",
    "| |__| | |_) |  __/ | | |/ ____ \\| |    _| |_   / ____ \\ (_| |  __/ | | | |_ ",
    " \\____/| .__/ \\___|_| |_/_/    \\_\\_|   |_____| /_/    \\_\\__, |\\___|_| |_|\\__|",
    "        | |                                               __/ |               ",
    "        |_|                                              |___/                "
]

BOT_FRAMES = [
    [
        " ╭─────╮ ",
        " │ ◕‿◕ │ ",
        " ╰─────╯ "
    ],
    [
        " ╭─────╮ ",
        " │ ⊙‿⊙ │ ",
        " ╰─────╯ "
    ],
    [
        " ╭─────╮ ",
        " │ ◠‿◠ │ ",
        " ╰─────╯ "
    ]
]

USER_ICON = [
    " ╭─────╮ ",
    " │ ︶︿︶│ ",
    " ╰─────╯ "
]

THINKING_FRAMES = [
    "⣾", "⣽", "⣻", "⢿", "⡿", "⣟", "⣯", "⣷"
]

def clear_screen():
    """Clear the terminal screen based on OS."""
    os_name = platform.system().lower()
    if os_name == 'windows':
        os.system('cls')
    else:
        os.system('clear')

def print_logo():
    """Print the OpenAPI Agent logo in color."""
    # ANSI color codes
    blue = "\033[94m"
    green = "\033[92m"
    reset = "\033[0m"
    
    for i, line in enumerate(OPENAPI_LOGO):
        if i % 2 == 0:
            print(f"{blue}{line}{reset}")
        else:
            print(f"{green}{line}{reset}")
    print("\n")

def print_bot_message(message, animation=False):
    """Print a message from the bot with an animated avatar."""
    frame = random.choice(BOT_FRAMES)
    
    print("\n")
    for line in frame:
        print(f"\033[94m{line}\033[0m")
    
    # Format and print the message
    print("\033[94m┌─" + "─" * 60 + "┐\033[0m")
    
    # First split by original line breaks
    original_lines = message.split('\n')
    formatted_lines = []
    
    for original_line in original_lines:
        # Split long lines by words to fit within 58 chars
        words = original_line.split()
        current_line = ""
        
        if not words:  # Empty line - preserve blank lines
            formatted_lines.append("")
            continue
            
        for word in words:
            if len(current_line) + len(word) + 1 <= 58:
                if current_line:
                    current_line += " " + word
                else:
                    current_line = word
            else:
                formatted_lines.append(current_line)
                current_line = word
        
        if current_line:
            formatted_lines.append(current_line)
    
    for line in formatted_lines:
        print(f"\033[94m│\033[0m {line}" + " " * (59 - len(line)) + "\033[94m│\033[0m")
    
    print("\033[94m└─" + "─" * 60 + "┘\033[0m")
    print("\n")

def print_user_prompt():
    """Print the user icon and prompt for input."""
    for line in USER_ICON:
        print(f"\033[92m{line}\033[0m")
    return input("\033[92m┌─ You: \033[0m")

def print_thinking_animation(seconds=2):
    """Show a thinking animation for the given number of seconds."""
    import time
    import sys
    
    print("\033[94m", end="")
    for _ in range(seconds * 5):
        for frame in THINKING_FRAMES:
            sys.stdout.write(f"\rThinking {frame}")
            sys.stdout.flush()
            time.sleep(0.1)
    print("\033[0m\r" + " " * 20 + "\r", end="")

def print_status_update(message, status_type="info"):
    """Print a status update with appropriate coloring based on type."""
    current_time = time.strftime("%H:%M:%S")
    
    # Color codes
    colors = {
        "info": "\033[94m",     # Blue
        "success": "\033[92m",  # Green
        "error": "\033[91m",    # Red
        "warning": "\033[93m",  # Yellow
        "tool_call": "\033[96m",  # Cyan
        "thinking": "\033[95m", # Magenta
        "response": "\033[97m", # White
    }
    
    color = colors.get(status_type, "\033[94m")
    reset = "\033[0m"
    
    # Status symbols
    symbols = {
        "info": "ℹ️",
        "success": "✅",
        "error": "❌",
        "warning": "⚠️",
        "tool_call": "🔧",
        "thinking": "🤔",
        "response": "💬",
    }
    
    symbol = symbols.get(status_type, "•")
    
    print(f"{color}[{current_time}] {symbol} {message}{reset}")

def print_progress_bar(iteration, total, prefix='Progress:', suffix='Complete', length=50, fill='█', print_end="\r"):
    """
    Call in a loop to create terminal progress bar
    """
    percent = ("{0:.1f}").format(100 * (iteration / float(total)))
    filled_length = int(length * iteration // total)
    bar = fill * filled_length + '-' * (length - filled_length)
    
    sys.stdout.write(f'\r{prefix} |{bar}| {percent}% {suffix}')
    sys.stdout.flush()
    
    # Print New Line on Complete
    if iteration == total: 
        print()

def print_tool_execution_summary(executions):
    """Print a summary of tool executions"""
    if not executions:
        print_status_update("No tools have been executed", "info")
        return
    
    print("\n\033[1m📊 Tool Execution Summary:\033[0m")
    print("\033[90m" + "-" * 110 + "\033[0m")
    print("\033[1m{:<30} {:<20} {:<10} {:<10} {:<30}\033[0m".format(
        "Tool Name", "Timestamp", "Duration", "Status", "Error Info"))
    print("\033[90m" + "-" * 110 + "\033[0m")
    
    for exec in executions:
        is_success = exec.get("success", False)
        status = "\033[92mSuccess\033[0m" if is_success else "\033[91mFailed\033[0m"
        
        # Get error info if available
        error_info = ""
        if not is_success and exec.get("error_details"):
            error_details = exec.get("error_details", {})
            msg = error_details.get("message", "")
            status_code = error_details.get("status_code", "")
            
            if msg:
                # Truncate long error messages
                if len(msg) > 27:
                    msg = msg[:24] + "..."
                
                if status_code:
                    error_info = f"{msg} (Status: {status_code})"
                else:
                    error_info = msg
        
        print("{:<30} {:<20} {:<10}s {:<10} {:<30}".format(
            exec.get("tool_name", "unknown")[:30],
            exec.get("timestamp", "unknown"),
            exec.get("duration", 0),
            status,
            error_info
        ))
    
    print("\033[90m" + "-" * 110 + "\033[0m")
    print(f"Total executions: {len(executions)}")
    
    # Show detailed failure information if any tools failed
    failures = [exec for exec in executions if not exec.get("success", False)]
    if failures:
        print("\n\033[1m❌ Failed Tool Details:\033[0m")
        
        for i, failure in enumerate(failures):
            print(f"\n\033[91mFailure #{i+1}: {failure.get('tool_name')}\033[0m")
            print("\033[90m" + "-" * 80 + "\033[0m")
            
            # Show input parameters
            print("\033[1mInput:\033[0m")
            print(json.dumps(failure.get("input", {}), indent=2))
            
            # Show error details
            print("\033[1mError:\033[0m")
            error_details = failure.get("error_details", {})
            
            if error_details:
                if "message" in error_details:
                    print(f"Message: {error_details['message']}")
                
                if "status_code" in error_details:
                    print(f"Status Code: {error_details['status_code']}")
                
                if "response" in error_details:
                    print("\nResponse:")
                    print(json.dumps(error_details["response"], indent=2))
                
                if "exception_type" in error_details:
                    print(f"\nException Type: {error_details['exception_type']}")
                
                if "traceback" in error_details and error_details["traceback"]:
                    print("\nTraceback:")
                    print(error_details["traceback"])
            else:
                print("No detailed error information available")
                
            print("\033[90m" + "-" * 80 + "\033[0m")
