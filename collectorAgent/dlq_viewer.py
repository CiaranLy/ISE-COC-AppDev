"""
DLQ Viewer - View and manage the Dead Letter Queue.

Usage:
    python dlq_viewer.py              # View all messages
    python dlq_viewer.py --count      # Show count only
    python dlq_viewer.py --clear      # Clear all messages
    python dlq_viewer.py --retry      # Move all back to main queue (requires queue_manager running)
"""

import argparse
import json
import sys
from pathlib import Path

from dlq import DeadLetterQueue

# Load config
CONFIG_FILE = Path(__file__).parent / "config.json"
with open(CONFIG_FILE, "r") as f:
    config = json.load(f)

DLQ_FILE = config["dlq_file"]


def main():
    parser = argparse.ArgumentParser(description="View and manage the Dead Letter Queue")
    parser.add_argument("--count", action="store_true", help="Show count only")
    parser.add_argument("--clear", action="store_true", help="Clear all messages")
    parser.add_argument("--retry", action="store_true", help="Export messages for retry")
    args = parser.parse_args()
    
    dlq = DeadLetterQueue(DLQ_FILE)
    
    if args.count:
        print(f"DLQ contains {dlq.count()} message(s)")
        return 0
    
    if args.clear:
        count = dlq.count()
        dlq.clear()
        print(f"Cleared {count} message(s) from DLQ")
        return 0
    
    if args.retry:
        messages = dlq.retry_all()
        if messages:
            retry_file = Path(__file__).parent / "dlq_retry.json"
            with open(retry_file, "w") as f:
                json.dump(messages, f, indent=2, default=str)
            print(f"Exported {len(messages)} message(s) to {retry_file}")
            print("To retry, you can manually send these to the queue or restart collection")
        else:
            print("DLQ is empty, nothing to retry")
        return 0
    
    # Default: show all messages
    messages = dlq.get_all()
    
    if not messages:
        print("DLQ is empty")
        return 0
    
    print(f"Dead Letter Queue ({len(messages)} messages)")
    print("=" * 60)
    
    for i, entry in enumerate(messages):
        print(f"\n[{i}] Added: {entry['added_at']}")
        print(f"    Reason: {entry['reason']}")
        print(f"    Message: {json.dumps(entry['original_message'], indent=8, default=str)}")
    
    print("\n" + "=" * 60)
    print(f"Total: {len(messages)} message(s)")
    print("\nCommands:")
    print("  --clear  Clear all messages")
    print("  --retry  Export messages for retry")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
