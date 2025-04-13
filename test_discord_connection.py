#!/usr/bin/env python3
import asyncio
import yaml
import logging
import sys
import discord
from discord.ext import tasks

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("discord-test")

class TestDiscordClient(discord.Client):
    def __init__(self, *args, **kwargs):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents, *args, **kwargs)
        self.channel_ids = kwargs.pop('channel_ids', [])
        self.connected = False

    async def setup_hook(self):
        # 启动连接检查循环
        self.check_connection.start()
    
    @tasks.loop(seconds=60.0)
    async def check_connection(self):
        if not self.connected:
            logger.warning("Discord连接丢失，尝试重新连接...")
    
    async def on_ready(self):
        self.connected = True
        logger.info(f"成功登录Discord，机器人用户名: {self.user}")
        
        # 验证频道存在并可访问
        channels_found = 0
        for channel_id in self.channel_ids:
            try:
                channel = await self.fetch_channel(int(channel_id))
                if channel:
                    logger.info(f"成功访问频道: {channel.name} (ID: {channel.id})")
                    channels_found += 1
            except discord.errors.NotFound:
                logger.error(f"未找到频道 ID {channel_id}")
            except discord.errors.Forbidden:
                logger.error(f"无权访问频道 ID {channel_id}")
            except Exception as e:
                logger.error(f"访问频道 {channel_id} 时出错: {str(e)}")
        
        if channels_found == 0:
            logger.warning("未找到任何有效频道！")
        else:
            logger.info(f"成功连接到 {channels_found}/{len(self.channel_ids)} 个频道")
        
        # 测试完成后退出
        logger.info("连接测试完成，5秒后退出...")
        await asyncio.sleep(5)
        await self.close()
    
    async def on_disconnect(self):
        self.connected = False
        logger.warning("与Discord的连接已断开")

async def main():
    try:
        # 加载配置
        with open('quant_trading_bot/config/config.yaml', 'r') as file:
            config = yaml.safe_load(file)
        
        discord_token = config.get('listener', {}).get('discord_token')
        channel_ids = config.get('listener', {}).get('channel_ids', [])
        
        if not discord_token or discord_token == "YOUR_DISCORD_TOKEN_HERE":
            logger.error("请在配置文件中设置有效的Discord令牌")
            return
        
        if not channel_ids or channel_ids[0] == "YOUR_CHANNEL_ID_HERE":
            logger.error("请在配置文件中设置有效的频道ID")
            return
        
        logger.info("尝试连接到Discord...")
        client = TestDiscordClient(channel_ids=channel_ids)
        await client.start(discord_token)
    
    except FileNotFoundError:
        logger.error("找不到配置文件，请确保配置文件存在于指定路径")
    except yaml.YAMLError:
        logger.error("配置文件格式错误，请检查YAML格式")
    except discord.errors.LoginFailure:
        logger.error("Discord登录失败，请检查令牌是否正确")
    except Exception as e:
        logger.error(f"发生未知错误: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main()) 