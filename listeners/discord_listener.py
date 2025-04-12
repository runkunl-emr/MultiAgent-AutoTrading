"""
Discord监听服务 - 协调Discord消息监听和处理
"""
import logging
import os
import threading
import time
from typing import List, Dict, Any, Optional, Callable

from ..core.discord_gateway import DiscordGateway
from ..core.message_processor import MessageProcessor
from ..adapters.notification_adapter import NotificationService
from ..utils.config import ConfigManager

logger = logging.getLogger(__name__)

class DiscordListener:
    """Discord监听服务"""
    
    def __init__(self, config: ConfigManager, notification_service: NotificationService):
        """
        初始化Discord监听服务
        
        Args:
            config: 配置管理器
            notification_service: 通知服务
        """
        self.config = config
        self.notification_service = notification_service
        self.gateway = None
        self.processor = None
        self.running = False
        
        # 信号日志文件
        self.signal_log_path = config.get("logging.signal_file", "logs/trading_signals.log")
        os.makedirs(os.path.dirname(self.signal_log_path), exist_ok=True)
    
    def start(self):
        """启动监听服务"""
        if self.running:
            logger.warning("监听服务已在运行")
            return
            
        # 获取配置
        token = self.config.get("discord.token")
        channel_ids = self.config.get("discord.channel_ids", [])
        keywords = self.config.get("discord.signal_keywords", [])
        
        # 验证配置
        if not token:
            raise ValueError("未配置Discord token")
            
        if not channel_ids:
            raise ValueError("未配置监听频道ID")
        
        # 初始化消息处理器
        self.processor = MessageProcessor(
            channel_ids=channel_ids,
            signal_keywords=keywords,
            signal_callback=self._handle_trading_signal
        )
        
        # 初始化Discord Gateway
        self.gateway = DiscordGateway(
            token=token,
            message_callback=self.processor.process_message
        )
        
        # 发送启动通知
        self.notification_service.send_notification(
            "Discord监听已启动",
            f"正在监听 {len(channel_ids)} 个频道的交易信号"
        )
        
        # 启动Gateway
        self.running = True
        self.gateway.start()
        
        logger.info(f"Discord监听服务已启动, 监听频道: {channel_ids}")
    
    def stop(self):
        """停止监听服务"""
        if not self.running:
            return
            
        self.running = False
        
        if self.gateway:
            self.gateway.stop()
            
        logger.info("Discord监听服务已停止")
    
    def _handle_trading_signal(self, message_data: Dict[str, Any]):
        """
        处理交易信号
        
        Args:
            message_data: Discord消息数据
        """
        try:
            # 提取信息
            content = message_data["content"]
            author = message_data["author"]["username"]
            timestamp = message_data["timestamp"]
            
            # 发送通知
            self.notification_service.send_notification(
                f"交易信号 - {author}",
                content[:200] + ("..." if len(content) > 200 else "")
            )
            
            # 记录到信号日志文件
            with open(self.signal_log_path, "a", encoding="utf-8") as f:
                f.write(f"=========== {timestamp} ===========\n")
                f.write(f"来源: {author}\n")
                f.write(f"内容:\n{content}\n\n")
                
            logger.info(f"已记录交易信号，来源: {author}")
            
        except Exception as e:
            logger.error(f"处理交易信号出错: {str(e)}") 