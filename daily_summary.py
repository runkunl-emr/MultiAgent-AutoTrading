#!/usr/bin/env python3
"""
Daily summary automation script
Runs daily to generate AI-powered summaries of stock market messages
"""
import os
import sys
import yaml
import subprocess
from datetime import datetime, timedelta
import argparse

def load_config(config_path: str) -> dict:
    """Load configuration"""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"Error loading config: {e}")
        return {}

def run_daily_summary(config_path: str, channel_id: str, username: str, output_dir: str = "summaries"):
    """Run daily summary for a user"""
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate filename with date
    today = datetime.now().strftime("%Y-%m-%d")
    output_file = os.path.join(output_dir, f"{username}_daily_{today}.txt")
    
    # Run the summarization script
    cmd = [
        sys.executable,
        "summarize_user_messages.py",
        "--config", config_path,
        "--channel", channel_id,
        "--user", username,
        "--max", "500",  # Last 500 messages should cover a day
        "--output", output_file,
        "--ai"  # Enable AI summarization
    ]
    
    print(f"Running daily summary for {username}...")
    print(f"Command: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(result.stdout)
        print(f"\n✓ Daily summary saved to: {output_file}")
        return output_file
    except subprocess.CalledProcessError as e:
        print(f"Error running summary: {e}")
        print(f"Error output: {e.stderr}")
        return None

def main():
    parser = argparse.ArgumentParser(description="Generate daily AI summaries")
    parser.add_argument("--config", "-c", type=str, default="config/discord_config.yaml",
                      help="Configuration file path")
    parser.add_argument("--channel", "-ch", type=str,
                      help="Channel ID (if not specified, uses all configured channels)")
    parser.add_argument("--user", "-u", type=str,
                      help="Username (if not specified, uses all users from user_filters)")
    parser.add_argument("--output-dir", "-o", type=str, default="summaries",
                      help="Output directory for summaries")
    
    args = parser.parse_args()
    
    # Load config
    config = load_config(args.config)
    
    # Get users to summarize
    users_to_summarize = []
    
    if args.user:
        # Single user specified
        if args.channel:
            users_to_summarize.append((args.channel, args.user))
        else:
            print("Error: --channel required when using --user")
            sys.exit(1)
    else:
        # Get users from user_filters config
        user_filters = config.get("discord", {}).get("user_filters", {})
        if not user_filters:
            print("No users configured. Use --user and --channel or configure user_filters in config.")
            sys.exit(1)
        
        for channel_id, users in user_filters.items():
            for user in users:
                users_to_summarize.append((channel_id, user))
    
    if not users_to_summarize:
        print("No users to summarize.")
        sys.exit(0)
    
    # Generate summaries
    print(f"Generating daily summaries for {len(users_to_summarize)} user(s)...")
    print("=" * 80)
    
    successful = []
    failed = []
    
    for channel_id, username in users_to_summarize:
        result = run_daily_summary(args.config, channel_id, username, args.output_dir)
        if result:
            successful.append((channel_id, username, result))
        else:
            failed.append((channel_id, username))
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Successful: {len(successful)}")
    for channel_id, username, filepath in successful:
        print(f"  ✓ {username} ({channel_id}): {filepath}")
    
    if failed:
        print(f"\nFailed: {len(failed)}")
        for channel_id, username in failed:
            print(f"  ✗ {username} ({channel_id})")

if __name__ == "__main__":
    main()

