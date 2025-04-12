import discord
import logging
import asyncio
import re
from typing import Callable, List, Optional, Dict, Any
from discord.ext import tasks

logger = logging.getLogger(__name__)


class DiscordListener(discord.Client):
    def __init__(self, token: str, channel_ids: List[str], 
                 message_callback: Callable[[str, str], None],
                 reconnect_attempts: int = 3,
                 message_throttle: int = 100,
                 *args, **kwargs):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents, *args, **kwargs)
        
        self.token = token
        self.channel_ids = [str(channel_id) for channel_id in channel_ids]
        self.message_callback = message_callback
        self.reconnect_attempts = reconnect_attempts
        self.message_throttle = message_throttle
        self.message_count = 0
        self.running = False
        self.last_reconnect_time = 0
        self.connected = False
        self.message_pattern = None  # Optional regex pattern for filtering messages
    
    async def setup_hook(self):
        self.check_connection.start()
    
    @tasks.loop(seconds=60.0)
    async def check_connection(self):
        if self.running and not self.connected:
            logger.warning("Discord connection lost, attempting reconnect...")
            await self.close()
            await self.start(self.token)
    
    async def on_ready(self):
        self.connected = True
        logger.info(f"Discord listener connected as {self.user}")
        
        # Verify channels exist and are accessible
        for channel_id in self.channel_ids:
            channel = self.get_channel(int(channel_id))
            if channel is None:
                try:
                    channel = await self.fetch_channel(int(channel_id))
                except discord.errors.NotFound:
                    logger.error(f"Channel ID {channel_id} not found")
                except discord.errors.Forbidden:
                    logger.error(f"No access to channel ID {channel_id}")
            
            if channel:
                logger.info(f"Monitoring channel: {channel.name} (ID: {channel.id})")
            else:
                logger.warning(f"Could not access channel ID {channel_id}")
    
    async def on_disconnect(self):
        logger.warning("Discord connection lost")
        self.connected = False
    
    async def on_message(self, message):
        # Ignore our own messages
        if message.author == self.user:
            return
        
        # Check if the message is from a monitored channel
        if str(message.channel.id) not in self.channel_ids:
            return
        
        # Apply throttling if needed
        self.message_count += 1
        if self.message_count > self.message_throttle:
            logger.warning(f"Message throttle limit reached ({self.message_throttle}), ignoring message")
            return
        
        # Apply pattern filtering if specified
        if self.message_pattern and not re.search(self.message_pattern, message.content):
            return
        
        # Pass message to callback
        try:
            self.message_callback(message.content, str(message.channel.id))
            logger.debug(f"Processed message from channel {message.channel.id}")
        except Exception as e:
            logger.error(f"Error processing message: {e}")
    
    def set_message_filter(self, pattern: Optional[str] = None):
        if pattern:
            try:
                self.message_pattern = re.compile(pattern)
                logger.info(f"Message filter set: {pattern}")
            except re.error as e:
                logger.error(f"Invalid regex pattern: {e}")
                self.message_pattern = None
        else:
            self.message_pattern = None
    
    async def start_listening(self):
        self.running = True
        logger.info("Starting Discord listener...")
        try:
            await self.start(self.token)
        except discord.errors.LoginFailure:
            logger.error("Invalid Discord token")
            raise
        except Exception as e:
            logger.error(f"Error starting Discord listener: {e}")
            raise
    
    def stop_listening(self):
        logger.info("Stopping Discord listener...")
        self.running = False
        asyncio.create_task(self.close())


class DiscordListenerWrapper:
    def __init__(self, config: Dict[str, Any], message_callback: Callable[[str, str], None]):
        self.config = config
        self.message_callback = message_callback
        self.client = None
        self.loop = asyncio.new_event_loop()
        self.listener_task = None
    
    def start_listening(self):
        if self.client:
            logger.warning("Discord listener already running")
            return
        
        token = self.config['discord_token']
        channel_ids = self.config['channel_ids']
        reconnect_attempts = self.config.get('reconnect_attempts', 3)
        message_throttle = self.config.get('message_throttle', 100)
        
        if not token:
            raise ValueError("Discord token not provided")
        
        if not channel_ids:
            raise ValueError("No channel IDs provided")
        
        self.client = DiscordListener(
            token=token,
            channel_ids=channel_ids,
            message_callback=self.message_callback,
            reconnect_attempts=reconnect_attempts,
            message_throttle=message_throttle
        )
        
        asyncio.set_event_loop(self.loop)
        self.listener_task = self.loop.create_task(self.client.start_listening())
        
        # Run in a separate thread
        import threading
        thread = threading.Thread(target=self.loop.run_forever, daemon=True)
        thread.start()
        
        logger.info("Discord listener started in background thread")
    
    def stop_listening(self):
        if not self.client or not self.listener_task:
            logger.warning("Discord listener not running")
            return
        
        self.client.stop_listening()
        
        try:
            # Cancel the listener task
            self.listener_task.cancel()
            
            # Stop the event loop
            self.loop.call_soon_threadsafe(self.loop.stop)
            
            logger.info("Discord listener stopped")
        except Exception as e:
            logger.error(f"Error stopping Discord listener: {e}")
        
        self.client = None
        self.listener_task = None 