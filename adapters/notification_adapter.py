"""
通知适配器 - 用于发送不同类型的通知
"""
import abc
import logging
import os
import platform
from typing import Optional

logger = logging.getLogger(__name__)

class NotificationAdapter(abc.ABC):
    """通知适配器基类"""
    
    @abc.abstractmethod
    def send_notification(self, title: str, message: str) -> bool:
        """
        发送通知
        
        Args:
            title: 通知标题
            message: 通知内容
            
        Returns:
            是否发送成功
        """
        pass

class MacNotificationAdapter(NotificationAdapter):
    """Mac系统通知适配器"""
    
    def __init__(self, sound_name: str = "default"):
        """
        初始化Mac通知适配器
        
        Args:
            sound_name: 通知声音名称
        """
        self.sound_name = sound_name
        
        if platform.system() != "Darwin":
            logger.warning("当前不是Mac系统，Mac通知可能无法正常工作")
    
    def send_notification(self, title: str, message: str) -> bool:
        """
        发送Mac系统通知
        
        Args:
            title: 通知标题
            message: 通知内容
            
        Returns:
            是否发送成功
        """
        try:
            # 转义引号
            title_escaped = title.replace('"', '\\"')
            message_escaped = message.replace('"', '\\"')
            
            # 构建AppleScript
            script = f'''
            osascript -e 'display notification "{message_escaped}" with title "{title_escaped}" sound name "{self.sound_name}"'
            '''
            
            # 执行脚本
            result = os.system(script)
            success = result == 0
            
            if success:
                logger.debug(f"Mac通知发送成功: {title}")
            else:
                logger.error(f"Mac通知发送失败，错误码: {result}")
                
            return success
            
        except Exception as e:
            logger.error(f"发送Mac通知出错: {str(e)}")
            return False

class ConsoleNotificationAdapter(NotificationAdapter):
    """控制台通知适配器"""
    
    def send_notification(self, title: str, message: str) -> bool:
        """
        将通知打印到控制台
        
        Args:
            title: 通知标题
            message: 通知内容
            
        Returns:
            是否发送成功
        """
        try:
            print(f"\n=== {title} ===")
            print(message)
            print("=" * (len(title) + 8))
            return True
        except Exception as e:
            logger.error(f"打印通知出错: {str(e)}")
            return False

class NotificationService:
    """通知服务 - 管理多个通知适配器"""
    
    def __init__(self):
        self.adapters = []
    
    def add_adapter(self, adapter: NotificationAdapter):
        """添加通知适配器"""
        self.adapters.append(adapter)
    
    def send_notification(self, title: str, message: str) -> bool:
        """通过所有适配器发送通知"""
        if not self.adapters:
            logger.warning("没有配置通知适配器")
            return False
            
        success = True
        for adapter in self.adapters:
            if not adapter.send_notification(title, message):
                success = False
                
        return success

# 工厂函数 - 创建适合当前平台的通知适配器
def create_platform_notification_adapter() -> NotificationAdapter:
    """创建适合当前平台的通知适配器"""
    system = platform.system()
    
    if system == "Darwin":  # macOS
        return MacNotificationAdapter(sound_name="Submarine")
    else:
        # 默认使用控制台通知
        return ConsoleNotificationAdapter() 