#!/usr/bin/env python3
import sys
import os
import yaml
import logging

# 将当前目录添加到Python路径
sys.path.insert(0, os.path.abspath('.'))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("simple-test")

# 示例交易信号
SAMPLE_ALERTS = [
    # 标准格式
    """🚨 SIGNAL ALERT 🚨
Symbol: AAPL
Direction: BULLISH
Entry Price: 185.50
Target: 190.00
Stop Loss: 180.00
Strategy: Breakout
Time Frame: 1h
Confidence: High
""",
    # 另一种格式
    """🔔 Trading Opportunity 🔔
BUY $MSFT at $350.75
Take profit: $360.00
Stop loss: $345.00
Technical setup: Cup and Handle
""",
    # 中文格式
    """📊 交易信号 📊
币种: BTC/USDT
方向: 看涨
入场价: 65000
目标价: 70000
止损: 62000
策略: 突破
"""
]

def test_parser():
    try:
        # 导入解析器
        from quant_trading_bot.core.parser import ParserFactory
        
        # 加载配置
        with open('quant_trading_bot/config/config.yaml', 'r') as file:
            config = yaml.safe_load(file)
        
        parser_config = config.get('parser', {})
        parser_factory = ParserFactory(parser_config)
        
        # 测试解析样本消息
        logger.info("===== 测试交易信号解析 =====")
        
        for i, message in enumerate(SAMPLE_ALERTS):
            logger.info(f"\n----- 测试消息 {i+1} -----")
            logger.info(f"消息内容:\n{message}")
            
            # 尝试解析
            try:
                result = parser_factory.parse_alert(message)
                if result:
                    logger.info(f"解析成功!")
                    logger.info(f"交易对: {result.symbol}")
                    logger.info(f"方向: {result.direction}")
                    logger.info(f"价格: {result.price}")
                    logger.info(f"策略ID: {result.strategy_id}")
                else:
                    logger.warning("无法解析消息")
            except Exception as e:
                logger.error(f"解析出错: {str(e)}")
        
        logger.info("\n测试完成!")
    
    except ModuleNotFoundError as e:
        logger.error(f"模块导入错误: {str(e)}")
        logger.error("请确保项目结构正确并且您在正确的目录中运行此脚本")
    except FileNotFoundError:
        logger.error("找不到配置文件")
    except Exception as e:
        logger.error(f"测试过程中发生错误: {str(e)}")

if __name__ == "__main__":
    test_parser() 