#!/usr/bin/env python3
"""
Simple script to start Discord monitoring program
"""
import os
import sys
import logging
import argparse
import getpass
import yaml
import signal
import time
import threading
import json
import datetime
from typing import Dict, Any, Set, List, Callable, Optional
import platform
import websocket
import requests

# ANSI color codes for terminal output
class Colors:
    """Terminal color codes"""
    RESET = "\033[0m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"

class ConfigManager:
    """Configuration manager"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config = {
            "discord": {
                "token": "",
                "channel_ids": [],
                "signal_keywords": ["buy", "sell", "long", "short", "signal", "trading", "trade", "entry", "bullish", "bearish"]
            },
            "notification": {
                "enabled": True,
                "sound": "Submarine"
            },
            "logging": {
                "level": "INFO",
                "file": "logs/discord_monitor.log",
                "signal_file": "logs/trading_signals.log"
            }
        }
        self.config_path = config_path
        
        if config_path and os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    file_config = yaml.safe_load(f)
                    if file_config:
                        self._update_config_recursive(self.config, file_config)
                        print(f"Configuration loaded from {config_path}")
            except Exception as e:
                print(f"Error loading configuration: {str(e)}")
    
    def save_config(self, config_path: Optional[str] = None) -> bool:
        path = config_path or self.config_path
        if not path:
            print("No configuration file path specified")
            return False
            
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            
            with open(path, 'w') as f:
                yaml.dump(self.config, f, default_flow_style=False)
                
            print(f"Configuration saved to {path}")
            return True
            
        except Exception as e:
            print(f"Error saving configuration: {str(e)}")
            return False
    
    def get(self, key: str, default: Any = None) -> Any:
        parts = key.split('.')
        value = self.config
        
        for part in parts:
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                return default
                
        return value
    
    def set(self, key: str, value: Any) -> None:
        parts = key.split('.')
        config = self.config
        
        for i, part in enumerate(parts[:-1]):
            if part not in config:
                config[part] = {}
            config = config[part]
            
        config[parts[-1]] = value
    
    def _update_config_recursive(self, target: Dict[str, Any], source: Dict[str, Any]) -> None:
        for key, value in source.items():
            if isinstance(value, dict) and key in target and isinstance(target[key], dict):
                self._update_config_recursive(target[key], value)
            else:
                target[key] = value

class NotificationAdapter:
    """Base notification adapter"""
    
    def send_notification(self, title: str, message: str) -> bool:
        """Send notification"""
        pass

class MacNotificationAdapter(NotificationAdapter):
    """Mac system notification adapter"""
    
    def __init__(self, sound_name: str = "default"):
        self.sound_name = sound_name
        
        if platform.system() != "Darwin":
            print("Current system is not Mac, Mac notifications may not work properly")
    
    def send_notification(self, title: str, message: str) -> bool:
        try:
            # Escape quotes
            title_escaped = title.replace('"', '\\"')
            message_escaped = message.replace('"', '\\"')
            
            # Build AppleScript
            script = f'''
            osascript -e 'display notification "{message_escaped}" with title "{title_escaped}" sound name "{self.sound_name}"'
            '''
            
            # Execute script
            result = os.system(script)
            success = result == 0
            
            if success:
                print(f"Mac notification sent successfully: {title}")
            else:
                print(f"Mac notification failed, error code: {result}")
                
            return success
            
        except Exception as e:
            print(f"Error sending Mac notification: {str(e)}")
            return False

class ConsoleNotificationAdapter(NotificationAdapter):
    """Console notification adapter"""
    
    def send_notification(self, title: str, message: str) -> bool:
        try:
            print(f"\n{Colors.YELLOW}=== {title} ==={Colors.RESET}")
            print(message)
            print(f"{Colors.YELLOW}{'=' * (len(title) + 8)}{Colors.RESET}")
            return True
        except Exception as e:
            print(f"Error printing notification: {str(e)}")
            return False

class NotificationService:
    """Notification service"""
    
    def __init__(self):
        self.adapters = []
    
    def add_adapter(self, adapter: NotificationAdapter):
        self.adapters.append(adapter)
    
    def send_notification(self, title: str, message: str) -> bool:
        if not self.adapters:
            print("No notification adapters configured")
            return False
            
        success = True
        for adapter in self.adapters:
            if not adapter.send_notification(title, message):
                success = False
                
        return success

class MessageProcessor:
    """Message processor"""
    
    def __init__(self, channel_ids: List[str], signal_keywords: List[str], 
                 signal_callback: Callable[[Dict[str, Any]], None], token: str, use_rest_api: bool = False):
        self.channel_ids = channel_ids
        self.signal_keywords = [kw.lower() for kw in signal_keywords]
        self.signal_callback = signal_callback
        self.processed_message_ids: Set[str] = set()
        self.token = token  # Store token for REST API calls
        self.use_rest_api = use_rest_api  # Control whether to use REST API
        self.current_user = None  # Store current username to compare message sender
        # Print only monitored channel IDs without extra text
        for channel_id in channel_ids:
            if channel_id not in self.channel_ids:
                self.channel_ids.append(channel_id)
        
    def set_current_user(self, username: str):
        """Set current username"""
        self.current_user = username
        print(f"Logged in as: {username}")
        
    def process_message(self, message_data: Dict[str, Any]):
        try:
            # Extract message information
            message_id = message_data.get("id", "unknown")
            channel_id = message_data.get("channel_id", "unknown")
            
            # Check if this channel is in our monitoring list first
            # If not, silently ignore the message without processing
            # 修复类型不匹配问题 - 确保比较时都是字符串类型
            channel_id_str = str(channel_id)
            is_monitored = False
            
            for monitored_id in self.channel_ids:
                if str(monitored_id) == channel_id_str:
                    is_monitored = True
                    break
                    
            if not is_monitored:
                return
            
            # Start timing for latency measurement
            start_time = time.time()
            
            # Get essential message data
            content = message_data.get("content", "")
            author = message_data.get("author", {}).get("username", "unknown")
            
            # Get channel and guild names if available from gateway
            channel_name = message_data.get("_channel_name", "Unknown Channel")
            guild_name = message_data.get("_guild_name", "Unknown Server")
            
            # Check if message has already been processed to avoid duplicates
            if message_id in self.processed_message_ids:
                return
            
            # Add to processed message set
            self.processed_message_ids.add(message_id)
            
            # Limit processed message count
            if len(self.processed_message_ids) > 1000:
                old_ids = list(self.processed_message_ids)[:500]
                for old_id in old_ids:
                    self.processed_message_ids.remove(old_id)
            
            # Check if message sender is the current user
            is_self_message = self.current_user and author == self.current_user
            
            # Get timestamp - convert Discord format to readable time if possible
            timestamp = message_data.get("timestamp", "")
            try:
                if timestamp:
                    # Convert ISO format to datetime
                    dt = datetime.datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    # Format as human-readable
                    timestamp = dt.strftime("%Y-%m-%d %H:%M:%S")
            except:
                # If conversion fails, use original
                pass
            
            # Display clear separator for new messages - FOCUS ON THE CONTENT
            print(f"\n{Colors.MAGENTA}{'='*15} NEW MESSAGE IN MONITORED CHANNEL {'='*15}{Colors.RESET}")
            print(f"{Colors.CYAN}[{timestamp}] {author} in {channel_name}{Colors.RESET}")
            
            # Message content - THIS IS WHAT USER MAINLY CARES ABOUT
            if content:
                print(f"\n{Colors.GREEN}{content}{Colors.RESET}")
            else:
                # Try to recover content from embeds and attachments
                recovered_content = self._try_recover_content(message_data)
                if recovered_content:
                    print(f"\n{Colors.GREEN}{recovered_content}{Colors.RESET}")
                else:
                    print(f"{Colors.YELLOW}[Message without text content]{Colors.RESET}")
                    
                # Check for media attachments
                attachments = message_data.get("attachments", [])
                if attachments:
                    print(f"{Colors.YELLOW}[Contains {len(attachments)} attachments]{Colors.RESET}")
            
            # Only highlight if trading signal found
            combined_content = content
            
            # Include embeds in signal detection
            embeds = message_data.get("embeds", [])
            for embed in embeds:
                if "title" in embed:
                    combined_content += " " + embed["title"]
                if "description" in embed:
                    combined_content += " " + embed["description"]
            
            # Check if contains trading signal keywords - HIGHLIGHT IMPORTANT SIGNALS
            if combined_content and self._is_trading_signal(combined_content):
                print(f"\n{Colors.YELLOW}!!! TRADING SIGNAL DETECTED !!!{Colors.RESET}")
                matched_kw = [kw for kw in self.signal_keywords if kw in combined_content.lower()]
                print(f"{Colors.YELLOW}Matched keywords: {', '.join(matched_kw)}{Colors.RESET}")
                self.signal_callback(message_data)
                
            # End with a short separator
            print(f"{Colors.MAGENTA}{'='*60}{Colors.RESET}")
            
        except Exception as e:
            print(f"Error processing message: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def _fetch_message_details(self, channel_id: str, message_id: str):
        """Use REST API to get message details, simulating curl call"""
        try:
            # Masked token display (for security)
            masked_token = "USER_TOKEN_HIDDEN" if self.token else "NO_TOKEN_PROVIDED"
            
            print(f"\nSimulated API call:")
            print(f"curl -X GET \"https://discord.com/api/v10/channels/{channel_id}/messages/{message_id}\" -H \"Authorization: {masked_token}\"")
            
            # Actual API request
            api_url = f"https://discord.com/api/v10/channels/{channel_id}/messages/{message_id}"
            headers = {"Authorization": self.token}
            
            # Make request
            print("Requesting message details, this may fail due to Discord API restrictions...")
            response = requests.get(api_url, headers=headers)
            
            if response.status_code == 200:
                message_data = response.json()
                print(f"\nComplete message from REST API: \n{json.dumps(message_data, indent=2, ensure_ascii=False)}")
                return True
            else:
                print(f"API request failed: Status code {response.status_code}")
                print(f"Response content: {response.text}")
                
                # More specific explanation for common error codes
                if response.status_code == 401:
                    print("Error reason: Unauthorized - User token is invalid or expired")
                elif response.status_code == 403:
                    print("Error reason: Forbidden - User token doesn't have sufficient permissions to access this API")
                    print("Discord has recently limited user token access to message API, this is expected behavior")
                    print("WebSocket listening functionality still works and can receive new messages")
                elif response.status_code == 429:
                    print("Error reason: Too Many Requests - API rate limit reached")
                
                return False
        
        except Exception as e:
            print(f"API request error: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def _is_trading_signal(self, content: str) -> bool:
        content_lower = content.lower()
        matched_keywords = [kw for kw in self.signal_keywords if kw in content_lower]
        if matched_keywords:
            print(f"Matched keywords: {matched_keywords}")
            return True
        return False
    
    def _try_recover_content(self, message_data: Dict[str, Any]) -> Optional[str]:
        """Try to recover content from message data"""
        try:
            # Try to extract content from possible fields
            if "embeds" in message_data and message_data["embeds"]:
                embeds = message_data["embeds"]
                embed_contents = []
                
                for embed in embeds:
                    if "title" in embed:
                        embed_contents.append(f"[Title] {embed['title']}")
                    if "description" in embed:
                        embed_contents.append(f"[Description] {embed['description']}")
                    if "fields" in embed:
                        for field in embed["fields"]:
                            if "name" in field and "value" in field:
                                embed_contents.append(f"[{field['name']}] {field['value']}")
                
                if embed_contents:
                    return "\n".join(embed_contents)
            
            # Check if there are attachments
            if "attachments" in message_data and message_data["attachments"]:
                attachments = message_data["attachments"]
                attachment_urls = [att.get("url", "") for att in attachments if "url" in att]
                
                if attachment_urls:
                    return f"[Attachments] {', '.join(attachment_urls)}"
            
            # Directly access raw_content field in message_data (if exists)
            if "raw_content" in message_data:
                return message_data["raw_content"]
                
            return None
        except Exception as e:
            print(f"Error recovering content: {str(e)}")
            return None

class DiscordGateway:
    """Discord Gateway client"""
    
    def __init__(self, token: str, message_callback: Callable[[Dict[str, Any]], None], channel_ids: List[str] = None):
        self.token = token
        self.message_callback = message_callback
        self.ws = None
        self.heartbeat_interval = 0
        self.heartbeat_thread = None
        self.last_sequence = None
        self.session_id = None
        self.running = False
        self.reconnect_count = 0
        self.reconnect_max = 20
        # Channel and guild cache
        self.channel_names = {}  # Map of channel_id -> name
        self.guild_names = {}    # Map of guild_id -> name
        
        # 直接存储监控的频道ID - 不再依赖message_callback
        self.monitored_channel_ids = []
        # 首先，使用传入的参数
        if channel_ids:
            self.monitored_channel_ids = [str(cid) for cid in channel_ids]
        # 如果没有直接传入，尝试从message_callback获取
        elif hasattr(message_callback, 'channel_ids'):
            self.monitored_channel_ids = [str(cid) for cid in message_callback.channel_ids]
            
        print(f"{Colors.GREEN}DiscordGateway initialized with {len(self.monitored_channel_ids)} monitored channels: {self.monitored_channel_ids}{Colors.RESET}")
        
    def start(self):
        self.running = True
        self.connect()
        
    def stop(self):
        self.running = False
        if self.ws:
            self.ws.close()
            
    def connect(self):
        try:
            gateway_url = self._get_gateway_url()
            if not gateway_url:
                raise Exception("Unable to get Gateway URL")
                
            # Create WebSocket connection
            self.ws = websocket.WebSocketApp(
                f"{gateway_url}/?v=9&encoding=json",
                on_open=self._on_open,
                on_message=self._on_message,
                on_error=self._on_error,
                on_close=self._on_close
            )
            
            # Run WebSocket (in a new thread)
            ws_thread = threading.Thread(target=self.ws.run_forever, kwargs={
                'ping_interval': 30,
                'ping_timeout': 10
            })
            ws_thread.daemon = True
            ws_thread.start()
            
        except Exception as e:
            print(f"Connection failed: {str(e)}")
            self._schedule_reconnect()
            
    def _get_gateway_url(self) -> Optional[str]:
        try:
            response = requests.get(
                "https://discord.com/api/v9/gateway",
                headers={"Authorization": self.token}
            )
            if response.status_code == 200:
                return response.json()["url"]
            else:
                print(f"Failed to get Gateway URL: {response.status_code}")
                return None
        except Exception as e:
            print(f"Exception getting Gateway URL: {str(e)}")
            return None
            
    def _on_open(self, ws):
        print("Discord Gateway connection opened")
    
    def _on_message(self, ws, message):
        try:
            # Parse the message data
            data = json.loads(message)
            op_code = data["op"]
            
            # 添加所有事件的调试日志
            event_type = data.get("t", "NO_EVENT_TYPE")
            print(f"\n{Colors.YELLOW}DEBUG: Received event: {event_type} (op: {op_code}){Colors.RESET}")
            
            # Only show critical websocket events and completely hide routine ones
            is_critical_event = False
            
            # Critical events: connection errors, invalid session, etc.
            if op_code in [9, 7, 4] or ('t' in data and data['t'] == 'ERROR'):
                is_critical_event = True
                
            # Show minimal info for critical websocket events, hide others completely
            if is_critical_event:
                print(f"\n{Colors.RED}Critical Discord Event - Code: {op_code}{Colors.RESET}")
                op_types = {
                    0: "DISPATCH", 1: "HEARTBEAT", 2: "IDENTIFY", 3: "PRESENCE UPDATE",
                    6: "RESUME", 7: "RECONNECT", 9: "INVALID SESSION", 10: "HELLO",
                    11: "HEARTBEAT ACK"
                }
                print(f"Type: {op_types.get(op_code, 'UNKNOWN')}")
            
            # Completely suppress logs for heartbeat ACKs and routine events
            if op_code == 11:  # Heartbeat ACK
                pass 
            elif op_code == 10:  # Hello - just show minimal connection info
                original_interval = data["d"]["heartbeat_interval"] / 1000
                self.heartbeat_interval = 60.0  # Fixed at 60 seconds
                print(f"Connected to Discord Gateway (heartbeat: 60s)")
                self._start_heartbeat()
                
                # Try to resume session or send identification
                if self.session_id and self.last_sequence:
                    self._send_resume()
                else:
                    self._send_identify()
                    
            elif op_code == 9:  # Invalid session (critical error)
                resumable = data.get('d', False)
                print(f"{Colors.RED}INVALID SESSION ERROR (resumable: {resumable}){Colors.RESET}")
                
                # Force a new identification after a brief delay
                time.sleep(1)
                self.session_id = None
                self._send_identify()
                
            elif op_code == 7:  # Reconnect
                print(f"{Colors.YELLOW}Discord requested reconnection.{Colors.RESET}")
                if self.ws:
                    self.ws.close()
                
            elif op_code == 0:  # Dispatch
                event_type = data["t"]
                
                # 记录所有收到的事件类型，包括MESSAGE_CREATE
                print(f"{Colors.YELLOW}DEBUG: Dispatch event: {event_type}{Colors.RESET}")
                
                # Only show specific events we care about
                if event_type == "READY":
                    self.session_id = data["d"]["session_id"]
                    self.reconnect_count = 0
                    user_name = data['d']['user']['username']
                    print(f"{Colors.GREEN}Successfully connected as user: {user_name}{Colors.RESET}")
                    
                    # Process guild and channel information but don't show logs for it
                    self._process_guilds_and_channels(data['d'])
                    
                    # Set current user if needed
                    if hasattr(self.message_callback, 'set_current_user'):
                        self.message_callback.set_current_user(user_name)
                
                # Handle errors but don't log normal events
                elif event_type == "ERROR":
                    print(f"{Colors.RED}ERROR EVENT RECEIVED:{Colors.RESET}")
                    print(f"{Colors.RED}{json.dumps(data['d'], indent=2)}{Colors.RESET}")
                
                # Update channel info silently, only log monitored channels
                elif event_type == "GUILD_CREATE":
                    guild_id = data['d'].get('id')
                    guild_name = data['d'].get('name')
                    if guild_id and guild_name:
                        self.guild_names[guild_id] = guild_name
                        
                    # Process channels silently, only show monitored ones
                    channels = data['d'].get('channels', [])
                    monitored_in_guild = []
                    for channel in channels:
                        channel_id = channel.get('id')
                        channel_name = channel.get('name')
                        if channel_id and channel_name:
                            self.channel_names[channel_id] = channel_name
                            # Only collect monitored channels
                            if str(channel_id) in self.monitored_channel_ids:
                                monitored_in_guild.append(f"{Colors.CYAN}→ Monitoring: {channel_name} ({channel_id}) in {guild_name}{Colors.RESET}")
                    
                    # Only print if we found monitored channels in this guild
                    if monitored_in_guild:
                        print(f"\n{Colors.GREEN}Found monitored channels in {guild_name}:{Colors.RESET}")
                        for channel_info in monitored_in_guild:
                            print(channel_info)
                    
                # Process actual messages (what we really care about)
                elif event_type == "MESSAGE_CREATE":
                    channel_id = data['d'].get('channel_id', "unknown")
                    author = data['d'].get('author', {}).get('username', 'unknown')
                    content = data['d'].get('content', '[No content]')
                    
                    # 打印出所有MESSAGE_CREATE事件的基本信息，不管是否是监控的频道
                    print(f"\n{Colors.MAGENTA}DEBUG: MESSAGE_CREATE - Channel: {channel_id}, Author: {author}{Colors.RESET}")
                    print(f"{Colors.MAGENTA}Message content preview: {content[:30]}...{Colors.RESET}")
                    
                    # 只检查本地存储的监控频道ID列表 - 确认目前有多少个监控的频道
                    if len(self.monitored_channel_ids) > 0:
                        print(f"{Colors.YELLOW}DEBUG: Monitoring {len(self.monitored_channel_ids)} channels: {self.monitored_channel_ids}{Colors.RESET}")
                    else:
                        print(f"{Colors.RED}WARNING: No channels are being monitored!{Colors.RESET}")
                    
                    # Only process if message is from monitored channel
                    # 简化检查逻辑 - 只依赖本地存储的频道ID
                    channel_id_str = str(channel_id)
                    is_monitored = channel_id_str in self.monitored_channel_ids
                    
                    if is_monitored:
                        print(f"{Colors.GREEN}Message is from monitored channel - Processing{Colors.RESET}")
                        # Get channel name if available
                        channel_name = self.channel_names.get(channel_id, "Unknown Channel")
                        guild_id = data['d'].get('guild_id', "unknown")
                        guild_name = self.guild_names.get(guild_id, "Unknown Server")
                        
                        # Add info to message data
                        if 'd' in data:
                            data['d']['_channel_name'] = channel_name
                            data['d']['_guild_name'] = guild_name
                        
                        # Process message without extra logs
                        self.message_callback(data["d"])
                    else:
                        print(f"{Colors.YELLOW}Message is NOT from monitored channel - Ignoring{Colors.RESET}")
                        print(f"{Colors.YELLOW}Expected one of: {self.monitored_channel_ids}{Colors.RESET}")
                        print(f"{Colors.YELLOW}Received: {channel_id}{Colors.RESET}")
            
            # Look for error fields in any response
            if 'error' in data:
                print(f"{Colors.RED}ERROR RESPONSE: {json.dumps(data['error'], indent=2)}{Colors.RESET}")
            if 'message' in data and op_code != 0:  # Don't include message field for normal messages
                print(f"{Colors.RED}ERROR MESSAGE: {data['message']}{Colors.RESET}")
                    
        except Exception as e:
            print(f"Error processing message: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def _on_error(self, ws, error):
        print(f"WebSocket error: {str(error)}")
    
    def _on_close(self, ws, close_status_code, close_msg):
        # Only print detailed error information for non-normal closures
        if close_status_code != 1000:  # 1000 is normal closure
            print(f"{Colors.RED}WebSocket connection closed: {close_status_code} - {close_msg}{Colors.RESET}")
            
            # Display more detailed information about known error codes
            if close_status_code == 4004:
                print(f"{Colors.RED}ERROR DETAILS: Authentication failed. The token you provided is invalid.{Colors.RESET}")
                print(f"{Colors.RED}Token starts with: {self.token[:10]}...{Colors.RESET}")
                # More specific information only for authentication errors
                if self.token.startswith("MTk") or self.token.startswith("MTE") or self.token.startswith("MTI"):
                    print(f"{Colors.YELLOW}You're using what appears to be a user token.{Colors.RESET}")
                    print(f"{Colors.YELLOW}Discord has been increasingly restricting user token usage.{Colors.RESET}")
                elif self.token.startswith("OD"):
                    print(f"{Colors.YELLOW}You're using what appears to be an older format token.{Colors.RESET}")
            # Only print the most critical error messages, omitting general advice
        else:
            print("WebSocket connection closed normally")
            
        if self.running:
            self._schedule_reconnect()
    
    def _schedule_reconnect(self):
        if not self.running:
            return
            
        self.reconnect_count += 1
        if self.reconnect_count > self.reconnect_max:
            print("Maximum reconnection attempts reached, stopping reconnection")
            return
            
        delay = min(30, 2 ** self.reconnect_count)
        print(f"Attempting to reconnect in {delay} seconds ({self.reconnect_count}/{self.reconnect_max})")
        
        threading.Timer(delay, self.connect).start()
    
    def _start_heartbeat(self):
        if self.heartbeat_thread and self.heartbeat_thread.is_alive():
            return
            
        # Simplified heartbeat start message
        print(f"Starting heartbeat (interval: 60 seconds)")
        self.heartbeat_thread = threading.Thread(target=self._heartbeat_loop)
        self.heartbeat_thread.daemon = True
        self.heartbeat_thread.start()
    
    def _heartbeat_loop(self):
        while self.running and self.ws and self.ws.sock and self.ws.sock.connected:
            try:
                payload = {
                    "op": 1,  # Heartbeat
                    "d": self.last_sequence
                }
                self.ws.send(json.dumps(payload))
                # Only log heartbeat issues, not successful ones
                time.sleep(self.heartbeat_interval)
            except Exception as e:
                print(f"Heartbeat send failed: {str(e)}")
                break
    
    def _send_identify(self):
        # 增加MESSAGE_CONTENT (1 << 15)权限，确保有权读取消息内容
        # 1 << 0 (GUILDS), 1 << 9 (GUILD_MESSAGES), 1 << 15 (MESSAGE_CONTENT)
        intents = 33283  # 使用更高的intents值
        
        # 打印当前使用的intents值
        print(f"{Colors.YELLOW}Using Discord intents: {intents} (includes MESSAGE_CONTENT){Colors.RESET}")
        
        # Very minimal identification info
        print(f"Authenticating with Discord...")
        
        payload = {
            "op": 2,  # Identify
            "d": {
                "token": self.token,
                "intents": intents,  # 确保包含intents字段
                "properties": {
                    "$os": "iOS",
                    "$browser": "Discord iOS",
                    "$device": "iPhone14,3",
                    "browser_user_agent": "Discord-iOS/191.0 (iPhone; iOS 16.5; Scale/3.00)",
                    "browser_version": "191.0",
                    "os_version": "16.5",
                    "referrer": "",
                    "referring_domain": "",
                    "referrer_current": "",
                    "referring_domain_current": "",
                    "release_channel": "stable",
                    "client_build_number": 191,
                    "client_event_source": None
                },
                "capabilities": 4093,
                "presence": {
                    "status": "online",
                    "since": 0,
                    "activities": [],
                    "afk": False
                },
                "compress": False,
                "client_state": {
                    "guild_versions": {},
                    "highest_last_message_id": "0",
                    "read_state_version": 0,
                    "user_guild_settings_version": -1,
                    "user_settings_version": -1,
                    "private_channels_version": "0",
                    "api_code_version": 0
                }
            }
        }
        
        self.ws.send(json.dumps(payload))
    
    def _send_resume(self):
        payload = {
            "op": 6,  # Resume
            "d": {
                "token": self.token,
                "session_id": self.session_id,
                "seq": self.last_sequence
            }
        }
        
        print(f"Attempting to resume session (seq: {self.last_sequence})...")
        self.ws.send(json.dumps(payload))
    
    def _process_guilds_and_channels(self, ready_data):
        """Process guild and channel information from READY event"""
        try:
            # Process guilds and channels silently (no logs for each channel)
            guilds = ready_data.get('guilds', [])
            
            for guild in guilds:
                guild_id = guild.get('id')
                guild_name = guild.get('name')
                
                if guild_id and guild_name:
                    self.guild_names[guild_id] = guild_name
                    
                channels = guild.get('channels', [])
                for channel in channels:
                    channel_id = channel.get('id')
                    channel_name = channel.get('name')
                    if channel_id and channel_name:
                        self.channel_names[channel_id] = channel_name
            
            # Only show monitored channels
            if hasattr(self.message_callback, 'channel_ids'):
                monitored_channels = self.message_callback.channel_ids
                
                print(f"\n{Colors.GREEN}{'='*20} MONITORED CHANNELS {'='*20}{Colors.RESET}")
                
                # Check if we have any channel names
                found_any = False
                for channel_id in monitored_channels:
                    channel_name = self.channel_names.get(channel_id, "Unknown Channel")
                    guild_id = None
                    
                    # Find channel's guild
                    for g in guilds:
                        if any(c.get('id') == channel_id for c in g.get('channels', [])):
                            guild_id = g.get('id')
                            break
                    
                    guild_name = self.guild_names.get(guild_id, "Unknown Server") if guild_id else "Unknown Server"
                    print(f"{Colors.CYAN}→ {channel_name} ({channel_id}) in {guild_name}{Colors.RESET}")
                    found_any = True
                
                if not found_any:
                    print(f"{Colors.YELLOW}No channel names found yet. Names will appear as messages arrive.{Colors.RESET}")
                    for channel_id in monitored_channels:
                        print(f"{Colors.CYAN}→ Channel ID: {channel_id}{Colors.RESET}")
                
                print(f"{Colors.GREEN}{'='*57}{Colors.RESET}")
                print(f"{Colors.YELLOW}Waiting for messages in monitored channels...{Colors.RESET}")
            
        except Exception as e:
            print(f"Error processing channels: {str(e)}")
    
    def get_channel_name(self, channel_id: str) -> str:
        """Get channel name from cache or fetch from API if needed"""
        if channel_id in self.channel_names:
            return self.channel_names[channel_id]
        
        # If not in cache, try to fetch from API
        try:
            api_url = f"https://discord.com/api/v9/channels/{channel_id}"
            # Determine if we need to add "Bot " prefix
            auth_header = self.token
            if self.token.startswith("OD") or self.token.startswith("MT"):
                if not self.token.startswith("Bot "):
                    auth_header = self.token  # User token doesn't need prefix
            
            headers = {"Authorization": auth_header}
            
            response = requests.get(api_url, headers=headers)
            if response.status_code == 200:
                channel_data = response.json()
                channel_name = channel_data.get('name', 'Unknown')
                self.channel_names[channel_id] = channel_name
                return channel_name
                
        except Exception as e:
            print(f"Error fetching channel info: {str(e)}")
            
        return "Unknown Channel"

class DiscordListener:
    """Discord listener"""
    
    def __init__(self, token: str, channel_ids: List[str],
                 signal_keywords: List[str],
                 notification_service: NotificationService):
        """
        Initialize Discord listener
        
        Args:
            token: Discord user token
            channel_ids: List of channel IDs to listen to
            signal_keywords: List of trading signal keywords
            notification_service: Notification service
        """
        self.token = token
        self.channel_ids = channel_ids
        self.signal_keywords = signal_keywords
        self.notification_service = notification_service
        
        # Message processor
        self.message_processor = MessageProcessor(
            channel_ids=channel_ids,
            signal_keywords=signal_keywords,
            signal_callback=self._handle_trading_signal,
            token=token,
            use_rest_api=False  # Disable REST API calls
        )
        
        # Create Gateway client - 直接传入监控的频道ID
        self.gateway = DiscordGateway(token, self.message_processor.process_message, channel_ids)
        
        # Signal log file
        self.signal_log_path = "logs/trading_signals.log"
        os.makedirs(os.path.dirname(self.signal_log_path), exist_ok=True)
        
        self.running = False
    
    def get_channel_name(self, channel_id: str) -> str:
        """Get channel name from the gateway's cache or return the ID if not available yet"""
        if hasattr(self.gateway, 'get_channel_name'):
            return self.gateway.get_channel_name(channel_id)
        return f"Channel {channel_id}"
    
    def start(self):
        if self.running:
            print("Listening service is already running")
            return
            
        # Send startup notification
        self.notification_service.send_notification(
            "Discord Monitor Started",
            f"Monitoring {len(self.channel_ids)} channels for trading signals"
        )
        
        # Start Gateway
        self.running = True
        self.gateway.start()
        
        # Get channel names when possible
        channel_info = []
        for channel_id in self.channel_ids:
            channel_name = self.get_channel_name(channel_id)
            channel_info.append(f"{channel_name} ({channel_id})")
        
        print(f"{Colors.GREEN}Discord listening service started, monitoring channels:{Colors.RESET}")
        for info in channel_info:
            print(f"{Colors.CYAN}→ {info}{Colors.RESET}")
    
    def stop(self):
        if not self.running:
            return
            
        self.running = False
        self.gateway.stop()
            
        print("Discord listening service stopped")
    
    def _handle_trading_signal(self, message_data: Dict[str, Any]):
        try:
            # Extract information
            content = message_data.get("content", "")
            author = message_data.get("author", {}).get("username", "Unknown User")
            timestamp = message_data.get("timestamp", "Unknown Time")
            
            # Try to recover content from embeds
            if not content and "embeds" in message_data and message_data["embeds"]:
                embeds = message_data["embeds"]
                embed_contents = []
                
                for embed in embeds:
                    if "title" in embed:
                        embed_contents.append(f"[Title] {embed['title']}")
                    if "description" in embed:
                        embed_contents.append(f"[Description] {embed['description']}")
                
                if embed_contents:
                    content = "\n".join(embed_contents)
            
            # If still no content, provide a default message
            if not content:
                content = "[Message content unavailable, please check original Discord message]"
            
            # Send notification
            self.notification_service.send_notification(
                f"Trading Signal - {author}",
                content[:200] + ("..." if len(content) > 200 else "")
            )
            
            # Log to signal log file
            with open(self.signal_log_path, "a", encoding="utf-8") as f:
                f.write(f"=========== {timestamp} ===========\n")
                f.write(f"Source: {author}\n")
                f.write(f"Content:\n{content}\n\n")
                
            print(f"Recorded trading signal from: {author}")
            
        except Exception as e:
            print(f"Error handling trading signal: {str(e)}")

def prompt_for_credentials(config):
    """Interactively prompt user for Discord token and channel IDs"""
    # Check if token already exists
    token = config.get("discord.token")
    if not token:
        print("\n=== Discord Token Setup ===")
        print("Please enter your Discord user token (input will not be displayed):")
        token = getpass.getpass("")
        if token:
            config.set("discord.token", token)
            print("Token set!")
        else:
            print("Warning: No token provided, will not be able to connect to Discord")
    
    # Check if channel IDs already exist
    channel_ids = config.get("discord.channel_ids", [])
    if not channel_ids:
        print("\n=== Discord Channel ID Setup ===")
        print("Please enter Discord channel IDs to monitor (separate multiple IDs with commas):")
        channels_input = input().strip()
        if channels_input:
            channel_ids = [ch.strip() for ch in channels_input.split(",")]
            config.set("discord.channel_ids", channel_ids)
            print(f"Set {len(channel_ids)} channel IDs!")
        else:
            print("Warning: No channel IDs provided, will not be able to monitor any channels")
    
    # Ask whether to save configuration
    if token or channel_ids:
        print("\nSave these settings to configuration file? (y/n):")
        save = input().strip().lower()
        if save == 'y' or save == 'yes':
            config.save_config()
            print("Configuration saved!")

def setup_logging():
    """Set up log directory"""
    os.makedirs("logs", exist_ok=True)

def main():
    """Main function"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Discord Trading Signal Monitor")
    parser.add_argument("--config", "-c", type=str, default="config/discord_config.yaml",
                      help="Configuration file path")
    parser.add_argument("--token", "-t", type=str, help="Discord user token")
    parser.add_argument("--channel", "-ch", type=str, action="append", help="Channel ID to monitor")
    parser.add_argument("--interactive", "-i", action="store_true", 
                      help="Interactive mode, prompt for token and channel IDs from terminal")
    args = parser.parse_args()
    
    # Set up logging
    setup_logging()
    
    # Load configuration
    config = ConfigManager(args.config)
    
    # Command line arguments override configuration file
    if args.token:
        config.set("discord.token", args.token)
    if args.channel:
        config.set("discord.channel_ids", args.channel)
    
    # Only prompt for input when interactive mode is explicitly specified
    if args.interactive:
        prompt_for_credentials(config)
    # If necessary configuration in config file is empty, show error instead of prompting
    elif not config.get("discord.token") or not config.get("discord.channel_ids", []):
        if not config.get("discord.token"):
            print("Error: No Discord token provided, please set in configuration file or use --token parameter")
        if not config.get("discord.channel_ids", []):
            print("Error: No channel IDs provided, please set in configuration file or use --channel parameter")
        print("Tip: Use -i or --interactive parameter to enable interactive input mode")
        sys.exit(1)
    
    # Output startup information
    print(f"{Colors.CYAN}========== Discord Trading Signal Monitor =========={Colors.RESET}")
    print(f"Configuration file: {args.config}")
    
    # Highlight monitored channel IDs (make it very clear)
    channel_ids = config.get('discord.channel_ids', [])
    if not channel_ids:
        print(f"{Colors.RED}ERROR: No channels specified for monitoring!{Colors.RESET}")
        print(f"{Colors.RED}Please add channel IDs to your configuration:{Colors.RESET}")
        print(f"{Colors.YELLOW}discord:{Colors.RESET}")
        print(f"{Colors.YELLOW}  channel_ids:{Colors.RESET}")
        print(f"{Colors.YELLOW}    - \"YOUR_CHANNEL_ID_HERE\"{Colors.RESET}")
        sys.exit(1)
    
    print(f"{Colors.GREEN}Monitoring {len(channel_ids)} channels:{Colors.RESET}")
    for channel_id in channel_ids:
        print(f"{Colors.CYAN}- {channel_id}{Colors.RESET}")
    
    # Set up notification service
    notification_service = NotificationService()
    if platform.system() == "Darwin":  # macOS
        notification_service.add_adapter(MacNotificationAdapter(sound_name="Submarine"))
    notification_service.add_adapter(ConsoleNotificationAdapter())
    
    # Create and start listening service
    try:
        listener = DiscordListener(config.get("discord.token"), config.get("discord.channel_ids", []),
                                  config.get("discord.signal_keywords", []), notification_service)
        listener.start()
        
        # Handle signals
        def signal_handler(sig, frame):
            print("Received exit signal, stopping...")
            listener.stop()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Keep main thread running
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("User interrupt, stopping...")
        if 'listener' in locals():
            listener.stop()
    except Exception as e:
        print(f"Runtime error: {str(e)}")
        if 'listener' in locals():
            listener.stop()
        sys.exit(1)

if __name__ == "__main__":
    main() 