# Quantitative Trading Bot

量化交易机器人，用于自动监听和执行交易信号。

## 项目概述

该项目实现了一个完整的量化交易机器人，能够监听Discord通道中的交易信号，解析信号内容，进行风险评估，并通过券商API执行交易。特别适合需要快速响应交易机会的交易者。

### 特点

- Discord消息监听和处理
- 支持多种格式的信号解析（包括英文和中文）
- 可配置的风险管理系统
- 模拟交易和实盘交易模式
- 断路器和自动重试机制，增强系统稳定性
- 详细的日志和交易统计
- 简单高效的可配置接口

## 项目结构

```
quant_trading_bot/
├── adapters/            # 外部服务适配器
│   ├── broker_adapter.py  # 券商适配器接口
│   ├── ibkr_adapter.py    # 盈透证券适配器
│   └── mock_adapter.py    # 模拟交易适配器
├── config/              # 配置文件
│   ├── config.py          # 配置加载
│   └── config_template.yaml  # 配置模板
├── core/                # 核心功能模块
│   ├── executor.py        # 执行交易
│   ├── listener.py        # 监听Discord消息
│   ├── models.py          # 数据模型
│   ├── orchestrator.py    # 协调各模块
│   ├── parser.py          # 解析交易信号
│   └── risk_guard.py      # 风险控制
├── utils/               # 工具模块
│   ├── circuit_breaker.py # 断路器
│   ├── logging.py         # 日志工具
│   └── retry.py           # 重试机制
├── logs/                # 日志文件目录
├── main.py              # 主程序入口
├── test_bot.py          # 测试脚本
└── requirements.txt     # 依赖项
```

## 安装

1. 克隆仓库

```bash
git clone https://github.com/yourusername/quant_trading_bot.git
cd quant_trading_bot
```

2. 创建虚拟环境（推荐）

```bash
python -m venv venv
source venv/bin/activate  # 在Windows上使用: venv\Scripts\activate
```

3. 安装依赖

```bash
pip install -r requirements.txt
```

## 配置

1. 从模板创建配置文件

```bash
cp quant_trading_bot/config/config_template.yaml quant_trading_bot/config/config.yaml
```

2. 编辑配置文件，设置Discord令牌、频道ID、风险参数和券商信息

配置文件包含以下主要部分：

- `listener`: Discord监听器配置
- `parser`: 解析器配置
- `risk_management`: 风险管理参数
- `broker`: 券商配置
- `execution`: 执行设置
- `logging`: 日志配置

## 运行

### 基本运行

```bash
python -m quant_trading_bot.main --config quant_trading_bot/config/config.yaml
```

### 参数说明

- `--config`, `-c`: 配置文件路径（默认：config/config.yaml）
- `--log-level`, `-l`: 日志级别（默认：INFO）
- `--dry-run`, `-d`: 测试模式，不执行实际交易

### 示例

```bash
# 以DEBUG日志级别运行
python -m quant_trading_bot.main --log-level DEBUG

# 以测试模式运行（无实际交易）
python -m quant_trading_bot.main --dry-run
```

## 测试

可以使用测试脚本来验证系统各部分的功能：

```bash
python -m quant_trading_bot.test_bot --test all
```

测试选项：
- `all`: 运行所有测试
- `parsing`: 测试消息解析
- `manual`: 测试手动交易执行
- `rejected`: 测试风控拒绝交易

## 开发

### 添加新的券商适配器

1. 在`adapters`目录下创建新的适配器文件
2. 继承`BrokerAdapter`类并实现所有必需的方法
3. 在`BrokerAdapterFactory`中添加新适配器的创建逻辑

### 添加新的信号格式

1. 在`core/parser.py`中添加新的解析器类
2. 继承`AlertParser`类并实现`can_parse`和`parse_alert`方法
3. 在`ParserFactory`中注册新的解析器

## 风险声明

此软件仅供教育和研究目的。使用该工具进行实际交易风险自负。开发者不对任何交易决策或结果负责。

## 许可

[MIT License](LICENSE) 