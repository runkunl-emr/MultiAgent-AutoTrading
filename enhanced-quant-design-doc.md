# 量化交易机器人设计文档 (增强版)

## 1. 系统概述与问题定义

### 1.1 问题陈述

1. 人是情绪化的 - 我们希望利用机器交易系统尽可能消除人为因素。
2. 我们生活在与美国时区不同的地区，时差导致我们很难在市场开放时保持清醒和专注。
3. 我们希望在高风险金融产品交易中获得高回报（如加密货币/期货/杠杆指数如TQQQ/TSLL），但不清楚风险与收益的比例。
4. 作为软件工程师，我们有编程和AI方面的专业知识想要利用，但缺乏金融领域的专业/基础知识。

### 1.2 系统目标

开发一个完全自动化的量化交易系统，能够：
- 自动监听并解析来自Discord的金融警报
- 将警报转换为标准交易指令，并通过券商API执行
- 提供风险管理功能，包括止损和止盈策略
- 支持策略回测与投资组合管理
- 具备紧急市场监控与响应能力

## 2. 系统架构 (增强设计)

### 2.1 高级架构概述

系统采用**事件驱动微服务架构**，由以下主要组件构成：

1. **监听模块 (Listener Service)**：监控Discord频道并发布警报事件
2. **解析模块 (Parser Service)**：将原始警报转换为标准数据结构
3. **风控模块 (RiskGuard Service)**：评估交易风险并作出决策
4. **执行模块 (Execution Service)**：通过券商API执行交易指令
5. **主控模块 (Orchestrator)**：协调各服务的工作流程
6. **监控与日志模块 (Monitoring & Logging)**：系统健康和性能监控
7. **紧急市场监控模块 (Emergency Monitor)**：监控市场异常状况

系统将使用**消息队列**作为服务间通信的主要方式，增强解耦性和容错能力。

### 2.2 事件流与数据流图

```
┌─────────────┐    警报事件     ┌─────────────┐   解析事件    ┌─────────────┐
│ 监听服务    │───────────────>│ 解析服务    │──────────────>│ 风控服务    │
└─────────────┘                └─────────────┘               └─────────────┘
                                                                    │
                                                                    │ 交易决策事件
                                                                    ▼
┌─────────────┐    执行结果     ┌─────────────┐   执行请求    ┌─────────────┐
│ 监控与日志  │<───────────────│ 执行服务    │<──────────────│ 主控服务    │
└─────────────┘                └─────────────┘               └─────────────┘
      ▲                                                             ▲
      │                                                             │
      │                       ┌─────────────┐                       │
      └───────────────────────┤紧急市场监控 ├───────────────────────┘
                              └─────────────┘
                               市场异常事件
```

### 2.3 系统关键性能指标

- 自动交易警报覆盖率 ≥ 95%
- 从接收警报到实际下单的端到端延迟 ≤ 500ms
- 单笔交易亏损控制在总账户资产的 ≤ 2%
- 系统识别并停止超风险阈值交易的准确率 ≥ 99%

## 3. 详细模块设计

### 3.1 监听模块 (Listener Service)

#### 核心职责：
- 连接Discord API并监听特定频道的警报消息
- 检测新消息并将其发布到消息队列
- 维持连接健康性，处理断线重连

#### 接口设计：
```python
class DiscordListener:
    def start_listening(self, channel_id: str) -> None:
        """启动Discord监听服务"""
        
    def stop_listening(self) -> None:
        """停止监听服务"""
    
    async def on_message(self, message) -> None:
        """处理接收到的Discord消息"""
        # 验证消息格式
        # 发布到消息队列
```

#### 增强设计:
1. **输入验证**：实现强健的输入验证，防范格式错误或恶意消息
2. **限流机制**：防止过多消息导致系统过载
3. **健康检查**：定期验证Discord连接状态
4. **多源支持**：预留接口支持将来添加Telegram等其他消息源

### 3.2 解析模块 (Parser Service)

#### 核心职责:
- 订阅消息队列中的原始警报消息
- 解析消息内容，提取关键交易信息
- 将解析结果标准化为AlertInfo结构
- 发布解析结果到消息队列

#### 接口设计:
```python
class AlertParser:
    def parse_alert(self, message: str) -> Optional[AlertInfo]:
        """解析警报消息，返回结构化的警报信息"""
        # 使用正则表达式或结构化解析
        # 验证提取的数据
        # 返回AlertInfo实例
    
    def detect_language(self, message: str) -> str:
        """检测消息语言以选择正确的解析器"""
```

#### 增强设计:
1. **模板策略**：使用模板策略模式支持多种消息格式
2. **完整性检查**：确保所有必要字段都被正确提取
3. **标准化处理**：统一处理不同时区、货币单位等
4. **异常日志**：详细记录无法解析的消息以便分析

### 3.3 风控模块 (RiskGuard Service)

#### 核心职责:
- 订阅解析后的警报消息
- 对交易信号进行风险评估
- 确定适当的交易参数（数量、价格）
- 实施风险控制策略
- 发布交易决策到消息队列

#### 接口设计:
```python
class RiskGuardService:
    def evaluate_alert(self, alert: AlertInfo) -> Optional[OrderInfo]:
        """评估警报风险，返回订单信息或拒绝交易"""
        # 执行账户风险检查
        # 检查持仓限制
        # 确定交易数量
        # 设置止损/止盈参数
    
    def set_risk_parameters(self, params: RiskParameters) -> None:
        """设置风险控制参数"""
```

#### 增强设计:
1. **多层风控**：实现分级风控策略（账户级、持仓级、订单级）
2. **断路器模式**：检测异常市场状况并触发保护措施
3. **投资组合风险评估**：考虑整体组合风险而非单笔交易
4. **动态仓位管理**：基于波动率和相关性动态调整仓位

### 3.4 执行模块 (Execution Service)

#### 核心职责:
- 订阅交易决策消息
- 将交易指令转换为券商API调用
- 执行交易并获取结果
- 发布执行结果到消息队列

#### 接口设计:
```python
class BrokerAdapter(ABC):
    @abstractmethod
    def connect(self) -> bool:
        """连接券商API"""
        pass
    
    @abstractmethod
    def place_order(self, order: OrderInfo) -> OrderResult:
        """执行交易订单"""
        pass
    
    @abstractmethod
    def disconnect(self) -> None:
        """断开与券商API的连接"""
        pass
    
    @abstractmethod
    def get_account_info(self) -> AccountInfo:
        """获取账户信息"""
        pass
```

#### 增强设计:
1. **重试机制**：对瞬态错误实现智能重试
2. **并发控制**：处理并发订单的正确性
3. **交易确认**：等待并验证交易执行结果
4. **API凭证安全**：使用安全密钥管理存储凭证
5. **适配器工厂**：使用工厂模式创建适当的券商适配器

### 3.5 主控模块 (Orchestrator)

#### 核心职责:
- 初始化和协调各服务
- 处理系统配置
- 维护系统状态
- 管理服务之间的事件流
- 处理错误和异常情况

#### 接口设计:
```python
class TradingOrchestrator:
    def initialize(self, config: Config) -> None:
        """初始化系统和各服务"""
    
    def start(self) -> None:
        """启动交易系统"""
    
    def stop(self) -> None:
        """安全停止系统"""
    
    def handle_exception(self, service: str, exception: Exception) -> None:
        """处理服务异常"""
```

#### 增强设计:
1. **优雅启停**：确保系统可以安全地启动和停止
2. **状态管理**：维护全局系统状态
3. **健康检查**：监控各服务健康状态
4. **配置热加载**：支持无需重启的配置更新

### 3.6 监控与日志模块 (Monitoring & Logging)

#### 核心职责:
- 收集系统性能指标
- 实现结构化日志
- 提供健康状态检查
- 实现告警机制

#### 接口设计:
```python
class MonitoringService:
    def record_metric(self, name: str, value: float, tags: Dict[str, str]) -> None:
        """记录系统指标"""
    
    def health_check(self) -> Dict[str, bool]:
        """检查各服务健康状态"""
    
    def set_alert(self, metric: str, threshold: float, callback: Callable) -> None:
        """设置指标告警"""

class LoggingService:
    def log(self, level: str, message: str, context: Dict) -> None:
        """记录结构化日志"""
    
    def transaction_log(self, transaction_id: str, status: str, details: Dict) -> None:
        """记录交易事务日志"""
```

#### 增强设计:
1. **结构化日志**：采用JSON格式记录所有日志，包含上下文信息
2. **分布式追踪**：使用唯一事务ID贯穿整个处理流程
3. **实时指标**：收集关键性能指标并发布到监控系统
4. **自动告警**：基于预设阈值触发告警
5. **历史分析**：支持历史性能和交易数据分析

### 3.7 紧急市场监控模块 (Emergency Monitor)

#### 核心职责:
- 实时监控全球金融市场指标
- 分析市场异常波动
- 触发紧急响应措施
- 向用户发送高级别通知

#### 接口设计:
```python
class EmergencyMonitor:
    def set_thresholds(self, thresholds: Dict[str, float]) -> None:
        """设置市场异常阈值"""
    
    def monitor_market(self) -> None:
        """启动市场监控"""
    
    def trigger_emergency_response(self, reason: str) -> None:
        """触发紧急响应"""
    
    def send_notification(self, level: str, message: str) -> None:
        """发送紧急通知"""
```

#### 增强设计:
1. **多指标监控**：同时监控多个市场指标和相关性
2. **异常检测算法**：使用统计和机器学习方法检测异常
3. **分级响应**：根据严重程度实施不同级别的响应
4. **自动化操作**：能够自动执行预设的应急策略

## 4. 数据模型与消息结构

### 4.1 核心数据结构

```python
@dataclass
class AlertInfo:
    """从警报解析的交易信号"""
    symbol: str                      # 交易标的代码
    price: float                     # 警报价格
    direction: str                   # 方向: "bull"或"bear"
    strategy_id: str                 # 策略编号或名称
    market_data: Dict[str, float]    # 其他市场数据
    timestamp: datetime              # 警报时间戳
    source: str                      # 信号来源
    confidence: float = 1.0          # 信号置信度
    correlation_id: str = None       # 事务关联ID

@dataclass
class OrderInfo:
    """交易订单信息"""
    symbol: str                      # 交易标的代码
    action: str                      # 动作: "BUY", "SELL", "SELL_SHORT"
    quantity: int                    # 下单数量
    order_type: str                  # 订单类型: "MKT", "LMT"等
    price: float = None              # 限价单价格
    stop_loss: float = None          # 止损价格
    take_profit: float = None        # 目标价格
    strategy_id: str = None          # 来源策略编号
    correlation_id: str = None       # 事务关联ID
    risk_score: float = None         # 风险评分
    max_slippage: float = None       # 最大允许滑点
    
@dataclass
class OrderResult:
    """订单执行结果"""
    success: bool                    # 执行是否成功
    order_id: str = None             # 券商订单ID
    filled_price: float = None       # 成交价格
    filled_quantity: int = None      # 成交数量
    status: str = None               # 订单状态
    error_message: str = None        # 错误信息
    execution_time: float = None     # 执行时间(ms)
    correlation_id: str = None       # 事务关联ID
```

### 4.2 消息队列主题设计

系统将使用以下消息队列主题:

1. `raw_alerts` - 原始Discord警报消息
2. `parsed_alerts` - 解析后的结构化警报
3. `trade_decisions` - 风控后的交易决策
4. `order_executions` - 订单执行结果
5. `system_metrics` - 系统性能指标
6. `market_events` - 市场异常事件
7. `system_logs` - 系统日志

## 5. 系统配置与环境

### 5.1 配置管理

系统配置采用分层设计:

```python
@dataclass
class ListenerConfig:
    discord_token: str
    channel_ids: List[str]
    reconnect_attempts: int = 3
    message_throttle: int = 100  # 每分钟最大处理消息数
    
@dataclass
class RiskConfig:
    max_position_size: float  # 占账户比例
    max_loss_per_trade: float  # 占账户比例
    daily_loss_limit: float  # 占账户比例
    max_open_positions: int
    correlation_threshold: float = 0.7
    
@dataclass
class BrokerConfig:
    broker_type: str  # "IBKR", "MooMoo"等
    trading_mode: str  # "paper", "live"
    credentials: Dict[str, str]
    api_endpoints: Dict[str, str]
    connection_timeout: int = 30

@dataclass
class SystemConfig:
    listener: ListenerConfig
    risk: RiskConfig
    broker: BrokerConfig
    log_level: str = "INFO"
    metrics_interval: int = 60  # 秒
    emergency_thresholds: Dict[str, float] = None
    notification_emails: List[str] = None
```

### 5.2 多环境支持

系统支持以下环境:

1. **开发环境** - 用于特性开发和本地测试
2. **测试环境** - 使用历史数据和模拟交易进行集成测试
3. **模拟环境** - 连接真实市场数据但使用模拟交易
4. **生产环境** - 实盘交易环境

## 6. 安全设计

### 6.1 API凭证管理

1. 使用环境变量或安全密钥管理服务存储API凭证
2. 实施凭证定期轮换机制
3. 限制凭证访问范围至最小所需权限

### 6.2 交易验证

1. 实现交易前多重检查机制:
   - 验证订单参数合法性
   - 检查异常交易量
   - 验证价格偏离度
2. 要求高风险交易的额外确认

### 6.3 操作安全

1. 实现访问控制和操作审计
2. 所有配置变更需记录和验证
3. 紧急操作需多重授权

## 7. 容错与恢复设计

### 7.1 断路器模式

对所有外部依赖实现断路器:

```python
class CircuitBreaker:
    def __init__(self, service_name, failure_threshold=5, reset_timeout=60):
        self.service_name = service_name
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF-OPEN
        
    def execute(self, func, *args, **kwargs):
        """执行操作，如果断路器开启则阻止执行"""
        # 实现断路器逻辑
```

### 7.2 重试策略

对瞬态错误实现智能重试:

```python
def retry_with_backoff(func, retries=3, backoff_factor=2):
    """实现指数退避重试"""
    # 实现重试逻辑
```

### 7.3 状态恢复

1. 定期保存系统状态快照
2. 实现从崩溃中恢复的机制
3. 记录所有未完成事务以便重启后恢复

## 8. 测试策略

### 8.1 单元测试

为所有关键组件编写单元测试，使用模拟对象隔离依赖:

```python
# 风控模块单元测试示例
def test_risk_guard_rejects_oversized_positions():
    alert = AlertInfo(symbol="AAPL", price=150.0, direction="bull", ...)
    risk_guard = RiskGuardService(max_position_size=0.01)  # 最大仓位1%
    
    # 模拟账户只有1000元，股价150，超过1%仓位
    with mock.patch('account_service.get_balance', return_value=1000.0):
        order = risk_guard.evaluate_alert(alert)
        assert order is None or order.quantity <= 6  # 最多6股
```

### 8.2 集成测试

使用模拟券商API进行端到端测试:

```python
def test_full_trading_flow():
    # 设置模拟环境
    # 发送模拟警报
    # 验证系统正确解析、风控和"执行"交易
```

### 8.3 回测验证

使用历史数据验证策略和系统行为:

```python
def backtest_with_historical_alerts(alerts_file, market_data):
    # 读取历史警报
    # 模拟系统处理过程
    # 计算模拟收益和风险指标
```

## 9. 开发与部署计划

### 9.1 开发阶段

**阶段一: 核心功能 (P0)**
1. 实现基础监听和解析模块
2. 开发简单风控和模拟交易
3. 建立基础日志系统
4. 完成IBKR适配器

**阶段二: 风险与安全加强 (P0.5)**
1. 改进风控策略
2. 增强安全措施
3. 添加基本监控
4. 实现紧急停止机制

### 9.2 部署架构

系统将部署为Docker容器集群:

```
┌─────────────────────────────────────────┐
│              负载均衡器                 │
└───────────────┬─────────────────────────┘
                │
    ┌───────────┴───────────┐
    │                       │
┌───▼───┐               ┌───▼───┐
│ API网关│               │监控仪表板│
└───┬───┘               └───────┘
    │
    │    ┌──────────┐    ┌──────────┐    ┌──────────┐
    ├────► 监听服务 ├────► 解析服务 ├────► 风控服务 │
    │    └──────────┘    └──────────┘    └──────────┘
    │                                         │
    │    ┌──────────┐    ┌──────────┐         │
    └────► 执行服务 ◄────┤ 主控服务 ◄─────────┘
         └──────────┘    └──────────┘
              │               ▲
              │               │
         ┌────▼───────────────┴───┐
         │      消息队列          │
         └──────────┬─────────────┘
                    │
         ┌──────────▼─────────────┐
         │       数据存储         │
         └────────────────────────┘
```

## 10. 监控与可观测性

### 10.1 关键指标

系统将监控以下关键指标:

1. **业务指标**
   - 每分钟警报数
   - 警报处理成功率
   - 交易执行延迟
   - 每日交易量
   - 账户余额变化

2. **系统指标**
   - 服务响应时间
   - 消息队列长度
   - CPU和内存使用率
   - API错误率
   - 第三方服务延迟

### 10.2 日志结构

所有系统日志采用JSON格式，包含以下字段:

```json
{
  "timestamp": "2023-04-06T12:34:56.789Z",
  "level": "INFO",
  "service": "parser",
  "correlation_id": "abc-123-xyz",
  "message": "成功解析警报",
  "data": {
    "symbol": "AAPL",
    "direction": "bull",
    "processing_time_ms": 42
  }
}
```

## 11. 紧急市场监控与响应模块设计

### 11.1 监控指标

1. 市场指数波动率
2. 主要股指短期变化率
3. 关键词财经新闻监控
4. 交易量异常变化

### 11.2 响应策略

1. **低级别警告 (Warning)**
   - 增加风控敏感度
   - 减少新开仓位

2. **中级别警告 (Alert)**
   - 停止新开仓
   - 开始减仓高风险持仓

3. **高级别紧急 (Emergency)**
   - 触发全面保护措施
   - 清仓所有持仓
   - 发送紧急通知

## 12. 初始实施重点 (P0阶段执行计划)

为了确保3.30~4.6期间完成可运行程序，建议优先实施:

1. **核心流程**
   - Discord监听模块的基本功能
   - 警报解析的核心能力
   - 简化的风控规则
   - 模拟交易适配器

2. **最小可行系统**
   - 简单配置文件支持
   - 基本日志记录
   - 本地运行环境
   - 命令行启停

3. **必要测试**
   - 关键路径单元测试
   - 简单集成测试
   - 手动测试脚本

---

本设计文档整合了原始需求和工程最佳实践，为量化交易机器人提供了清晰的实施蓝图。系统采用模块化、事件驱动的架构，确保各组件松耦合且高内聚，同时强化了安全性、可观测性和容错能力。无论是初始的P0阶段实现还是后续扩展，本文档都提供了充分的指导和架构基础。 