"""
Discord消息处理器 - 解析和处理Discord消息
"""
import logging
from typing import Dict, Any, Set, List, Callable

logger = logging.getLogger(__name__)

class MessageProcessor:
    def __init__(self, channel_ids: List[str], signal_keywords: List[str], 
                 signal_callback: Callable[[Dict[str, Any]], None]):
        """
        初始化消息处理器
        
        Args:
            channel_ids: 要监听的频道ID列表
            signal_keywords: 交易信号关键词列表
            signal_callback: 检测到交易信号时的回调函数
        """
        self.channel_ids = channel_ids
        self.signal_keywords = [kw.lower() for kw in signal_keywords]
        self.signal_callback = signal_callback
        self.processed_message_ids: Set[str] = set()
        
    def process_message(self, message_data: Dict[str, Any]):
        """
        处理Discord消息
        
        Args:
            message_data: Discord消息数据
        """
        try:
            # 提取消息信息
            message_id = message_data["id"]
            channel_id = message_data["channel_id"]
            content = message_data["content"]
            author = message_data["author"]["username"]
            
            # 检查是否为目标频道且消息未处理
            if channel_id in self.channel_ids and message_id not in self.processed_message_ids:
                # 添加到已处理消息集
                self.processed_message_ids.add(message_id)
                
                # 限制已处理消息数量
                if len(self.processed_message_ids) > 1000:
                    old_ids = list(self.processed_message_ids)[:500]
                    for old_id in old_ids:
                        self.processed_message_ids.remove(old_id)
                
                # 记录收到的消息
                content_preview = content[:100] + ("..." if len(content) > 100 else "")
                logger.info(f"收到消息: [{author}] {content_preview}")
                
                # 检查是否包含交易信号关键词
                if self._is_trading_signal(content):
                    logger.info(f"检测到交易信号! ID: {message_id}")
                    self.signal_callback(message_data)
        
        except Exception as e:
            logger.error(f"处理消息出错: {str(e)}")
    
    def _is_trading_signal(self, content: str) -> bool:
        """
        判断消息是否包含交易信号关键词
        
        Args:
            content: 消息内容
            
        Returns:
            是否为交易信号
        """
        content_lower = content.lower()
        return any(keyword in content_lower for keyword in self.signal_keywords) 