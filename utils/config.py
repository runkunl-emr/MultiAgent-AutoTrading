"""
配置管理 - 加载和处理配置
"""
import os
import logging
from typing import Dict, Any, List, Optional

# 尝试多种方式导入yaml模块
try:
    import yaml
except ImportError:
    try:
        import pyyaml as yaml
    except ImportError:
        raise ImportError("无法导入yaml模块。请确保安装了PyYAML包：pip install pyyaml")

logger = logging.getLogger(__name__)

DEFAULT_CONFIG = {
    "discord": {
        "token": "",
        "channel_ids": [],
        "signal_keywords": ["buy", "sell", "long", "short", "signal", "trading", "trade", "entry"]
    },
    "notification": {
        "enabled": True,
        "sound": "default"
    },
    "logging": {
        "level": "INFO",
        "file": "logs/discord_monitor.log"
    }
}

class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化配置管理器
        
        Args:
            config_path: 配置文件路径
        """
        self.config = DEFAULT_CONFIG.copy()
        self.config_path = config_path
        
        if config_path:
            self.load_config(config_path)
    
    def load_config(self, config_path: str) -> bool:
        """
        从文件加载配置
        
        Args:
            config_path: 配置文件路径
            
        Returns:
            是否加载成功
        """
        try:
            if not os.path.exists(config_path):
                logger.warning(f"配置文件不存在: {config_path}，使用默认配置")
                return False
                
            with open(config_path, 'r') as f:
                file_config = yaml.safe_load(f)
                
            # 更新配置
            self._update_config_recursive(self.config, file_config)
            logger.info(f"配置已从 {config_path} 加载")
            return True
            
        except Exception as e:
            logger.error(f"加载配置出错: {str(e)}")
            return False
    
    def save_config(self, config_path: Optional[str] = None) -> bool:
        """
        保存配置到文件
        
        Args:
            config_path: 配置文件路径，如果为None则使用初始化时的路径
            
        Returns:
            是否保存成功
        """
        path = config_path or self.config_path
        if not path:
            logger.error("未指定配置文件路径")
            return False
            
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(path), exist_ok=True)
            
            with open(path, 'w') as f:
                yaml.dump(self.config, f, default_flow_style=False)
                
            logger.info(f"配置已保存到 {path}")
            return True
            
        except Exception as e:
            logger.error(f"保存配置出错: {str(e)}")
            return False
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值
        
        Args:
            key: 配置键，使用点号分隔的路径，如'discord.token'
            default: 默认值
            
        Returns:
            配置值或默认值
        """
        parts = key.split('.')
        value = self.config
        
        for part in parts:
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                return default
                
        return value
    
    def set(self, key: str, value: Any) -> None:
        """
        设置配置值
        
        Args:
            key: 配置键，使用点号分隔的路径，如'discord.token'
            value: 配置值
        """
        parts = key.split('.')
        config = self.config
        
        for i, part in enumerate(parts[:-1]):
            if part not in config:
                config[part] = {}
            config = config[part]
            
        config[parts[-1]] = value
    
    def _update_config_recursive(self, target: Dict[str, Any], source: Dict[str, Any]) -> None:
        """
        递归更新配置
        
        Args:
            target: 目标配置
            source: 源配置
        """
        for key, value in source.items():
            if isinstance(value, dict) and key in target and isinstance(target[key], dict):
                self._update_config_recursive(target[key], value)
            else:
                target[key] = value 