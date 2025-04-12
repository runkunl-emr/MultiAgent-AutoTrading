"""
Discord监听主程序
"""
import os
import sys
import logging
import argparse
import signal
import time
import getpass

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# 使用相对导入
from utils.config import ConfigManager
from adapters.notification_adapter import NotificationService, create_platform_notification_adapter
from listeners.discord_listener import DiscordListener

def setup_logging(config):
    """设置日志"""
    log_level = config.get("logging.level", "INFO")
    log_file = config.get("logging.file")
    
    # 创建日志目录
    if log_file:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
    
    # 配置日志
    handlers = [logging.StreamHandler()]
    if log_file:
        handlers.append(logging.FileHandler(log_file))
    
    logging.basicConfig(
        level=getattr(logging, log_level),
        format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
        handlers=handlers
    )

def prompt_for_credentials(config):
    """
    交互式提示用户输入Discord token和频道ID
    
    Args:
        config: 配置管理器
    """
    # 检查是否已经有token
    token = config.get("discord.token")
    if not token:
        print("\n=== Discord Token设置 ===")
        print("请输入您的Discord用户token (输入时不会显示):")
        token = getpass.getpass("")
        if token:
            config.set("discord.token", token)
            print("Token已设置!")
        else:
            print("警告: 未提供Token，将无法连接到Discord")
    
    # 检查是否已经有频道ID
    channel_ids = config.get("discord.channel_ids", [])
    if not channel_ids:
        print("\n=== Discord频道ID设置 ===")
        print("请输入您要监听的Discord频道ID (多个ID用逗号分隔):")
        channels_input = input().strip()
        if channels_input:
            channel_ids = [ch.strip() for ch in channels_input.split(",")]
            config.set("discord.channel_ids", channel_ids)
            print(f"已设置{len(channel_ids)}个频道ID!")
        else:
            print("警告: 未提供频道ID，将无法监听任何频道")
    
    # 询问是否保存配置
    if token or channel_ids:
        print("\n是否将这些设置保存到配置文件中? (y/n):")
        save = input().strip().lower()
        if save == 'y' or save == 'yes':
            config.save_config()
            print("配置已保存!")

def main():
    """主函数"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="Discord交易信号监听")
    parser.add_argument("--config", "-c", type=str, default="config/discord_config.yaml",
                      help="配置文件路径")
    parser.add_argument("--token", "-t", type=str, help="Discord用户token")
    parser.add_argument("--channel", "-ch", type=str, action="append", help="监听的频道ID")
    parser.add_argument("--interactive", "-i", action="store_true", 
                      help="交互式模式，从终端提示输入token和频道ID")
    args = parser.parse_args()
    
    # 加载配置
    config = ConfigManager(args.config)
    
    # 命令行参数覆盖配置文件
    if args.token:
        config.set("discord.token", args.token)
    if args.channel:
        config.set("discord.channel_ids", args.channel)
    
    # 如果指定了交互式模式或者缺少必要的配置，则提示用户输入
    if args.interactive or not config.get("discord.token") or not config.get("discord.channel_ids", []):
        prompt_for_credentials(config)
    
    # 设置日志
    setup_logging(config)
    logger = logging.getLogger(__name__)
    
    # 验证必要的配置
    if not config.get("discord.token"):
        logger.error("错误: 未提供Discord token，无法启动")
        sys.exit(1)
    
    if not config.get("discord.channel_ids", []):
        logger.error("错误: 未提供频道ID，无法启动")
        sys.exit(1)
    
    # 输出启动信息
    logger.info("========== Discord交易信号监听 ==========")
    logger.info(f"配置文件: {args.config}")
    logger.info(f"监听频道数: {len(config.get('discord.channel_ids', []))}")
    
    # 设置通知服务
    notification_service = NotificationService()
    notification_service.add_adapter(create_platform_notification_adapter())
    
    # 创建并启动监听服务
    try:
        listener = DiscordListener(config, notification_service)
        listener.start()
        
        # 处理信号
        def signal_handler(sig, frame):
            logger.info("接收到退出信号，正在停止...")
            listener.stop()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # 保持主线程运行
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("用户中断，正在停止...")
        if 'listener' in locals():
            listener.stop()
    except Exception as e:
        logger.error(f"运行时错误: {str(e)}", exc_info=True)
        if 'listener' in locals():
            listener.stop()
        sys.exit(1)

if __name__ == "__main__":
    main() 