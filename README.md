# A股量化交易与多因子回测系统 (A-Share Quant System)

## 项目概述
本项目旨在构建一个专为A股市场设计、基于Python生态的端到端量化投研与交易平台。系统不仅支持单因子的趋势跟踪策略，更全面集成了涵盖"估值、质量、成长、动量、量价"的五大经典多因子评价体系。实现从"基本面选股排雷"到"高频量价择时交易"的全生命周期闭环。

### 核心设计理念
- **多因子与量价结合**：基本面决定股票"能不能买"，量价与动量决定"什么时候买"。
- **轻量化与模块化**：数据获取、因子计算、回测引擎、交易执行完全解耦。
- **贴合A股生态**：内置符合A股"涨跌停限制"、"T+1交易制"规则的底层逻辑。

## 系统架构

### 1. 数据中心模块 (Data Feed Layer)
负责处理A股的所有数据输入，统一输出为标准化的数据结构。
- **历史行情与财务数据**：对接 `AkShare` / `Tushare Pro` 获取前复权日线、财报披露数据。
- **高频Level-2与实时行情**：对接券商极速交易接口（如 `QMT` / `Ptrade`）获取Tick级资金流向与实时切片。

### 2. 核心因子库与多因子引擎 (Core Factor & Multi-Factor Engine)
系统内置符合A股市场特征的五大经典核心因子库：

#### ① 估值因子库 (Value Factors)
- PE-TTM / EP (市盈率/盈利率)
- PB-LF (市净率)
- Dividend Yield (股息率)

#### ② 质量与基本面因子库 (Quality Factors)
- ROE (净资产收益率)
- 毛利率及环比变化
- 经营活动现金流净额 / 营业收入

#### ③ 成长因子库 (Growth Factors)
- 净利润/营业收入 YOY
- PEG (市盈率相对盈利增长比率)

#### ④ 动量与反转因子库 (Momentum & Reversal)
- 1个月收益率反转 (1M Reversal)
- 6个月/12个月动量 (6/12M Momentum)
- 创52周新高 (52-Week High)

#### ⑤ 量价与情绪因子库 (Volume & Price)
- **[核心首发] 交易量动量 (Volume Momentum & H-1 Breakout)**
- 换手率 (Turnover Rate)
- 波动率 (Volatility)
- 特质收益率 (Idiosyncratic Return)
- 主力资金净流入占比

### 3. 历史回测系统 (Backtesting Engine)
- **引擎选型**：基于开源框架 `Backtrader` 进行二次封装，支持多只股票并发回测。
- **规则适配**：严格执行T+1、涨跌停板无法成交过滤、剔除停牌日。
- **成本模型**：双向万分之二点五佣金，卖出单向千分之一（或万分之五）印花税，加入滑点（Slippage）模型。
- **评估指标**：资金曲线图、年化收益率 (CAGR)、最大回撤 (Max Drawdown)、夏普比率 (Sharpe Ratio)、卡玛比率 (Calmar Ratio)。

### 4. 交易执行与风控 (Execution & Risk Control)
- **仓位与头寸管理**：基于 ATR（真实波动幅度）动态计算仓位。
- **硬性止损机制**：价格止损（下跌 8% 无条件斩仓）和时间止损。
- **实盘接口对接**：使用 `QMT/Ptrade` API 自动转换为实盘订单。

## 技术栈
- **开发语言**: Python 3.9+
- **科学计算**: Pandas, NumPy, SciPy
- **金融数据**: AkShare, Tushare Pro
- **回测框架**: Backtrader, Alphalens
- **可视化**: Matplotlib, Pyecharts

## 项目结构
```
.
├── README.md
├── requirements.txt
├── config.yaml
├── src/
│   ├── data_feed/      # 数据获取模块
│   ├── factors/        # 因子计算模块
│   ├── backtest/       # 回测引擎模块
│   ├── execution/      # 交易执行与风控模块
│   └── utils/          # 工具函数模块
├── tests/              # 单元测试
├── docs/               # 文档
├── data/               # 数据存储
│   ├── raw/           # 原始数据
│   └── processed/     # 处理后数据
└── logs/              # 日志文件
```

## 研发路线图

### Phase 1: 因子计算基建与单策略跑通 (1-2周)
- 构建本地数据池，编写并封装"五大类因子"的计算模块（Factor Extractors）。
- 将【交易量动量+突破(H-1)】作为首个择时策略，接入 `Backtrader` 跑通基准回测。

### Phase 2: 构建多因子打分模型 (3-4周)
- **选股层**：用（质量+估值）剔除垃圾股，构建动态股票池。
- **择时层**：股票池内标的一旦触发（交易量动量爆发 + H-1突破），立即发出买入信号。
- 接入 `Alphalens` 对所有单一因子进行有效性（IC值、分层收益）测试。

### Phase 3: 模拟推送与实盘对接 (5周及以后)
- 编写盘后定时任务，每日计算全市场因子得分与量价信号，微信Webhook推送"明日备选票"。
- 跑通 QMT 模拟盘环境的自动下单。

## 快速开始

### 安装依赖
```bash
pip install -r requirements.txt
```

### 配置
1. 复制 `config.example.yaml` 为 `config.yaml`
2. 修改配置文件中的API密钥和数据源设置

### 运行示例
```bash
python main.py --config config.yaml --mode backtest
```

## 许可证
MIT License
