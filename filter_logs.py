import sys
from datetime import datetime

# ANSI Color Codes
YELLOW = '\033[93m'
ORANGE = '\033[38;5;208m'
RED = '\033[91m'
RESET = '\033[0m'

def get_timestamp(line):
    try:
        # Format: ## 03-03-2026 - 14:33:38
        parts = line.strip().split()
        # parts[1] is 03-03-2026, parts[3] is 14:33:38
        date_str = f"{parts[1]} {parts[3]}"
        return datetime.strptime(date_str, "%d-%m-%Y %H:%M:%S")
    except (IndexError, ValueError):
        return None

def print_group(group):
    if not group:
        return

    start_time = get_timestamp(group[0])
    end_time = get_timestamp(group[-1])
    duration = (end_time - start_time).total_seconds()

   
    if duration < 150:
        color = RESET
    elif duration < 350:
        color = YELLOW
    elif duration < 680:
        color = ORANGE
    else:
        color = RED

    for g_line in group:
        # Use flush=True to ensure it appears in the terminal immediately
        print(f"{color}{g_line.strip()}{RESET}", flush=True)
    
    print("-" * 40, flush=True)

def main():
    current_group = []
    last_time = None

    # sys.stdin is an iterable that reads line by line
    for line in sys.stdin:
        clean_line = line.strip()
        if not clean_line.startswith("##"):
            continue

        current_time = get_timestamp(clean_line)
        if not current_time:
            continue

        if last_time is not None:
            diff = (current_time - last_time).total_seconds()
            # If the gap between THIS line and the PREVIOUS line is > 90s
            if diff > 90:
                print_group(current_group)
                current_group = []

        current_group.append(clean_line)
        last_time = current_time

    # This prints the final group once the stream ends (Ctrl+D or end of file)
    print_group(current_group)

if __name__ == "__main__":
    main()
