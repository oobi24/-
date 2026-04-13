"""
A股量化交易与多因子回测系统 - 主程序入口
"""

import sys
import argparse
from pathlib import Path

# 添加src到路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.utils.config_loader import ConfigLoader
from src.utils.log_utils import setup_logging, get_logger
from src.data_feed import DataFeed
from src.factors import FactorCalculator, MultiFactorEngine
# Optional imports
try:
    from src.backtest import BacktestEngine, VolumeMomentumStrategy
    _HAS_BACKTRADER = True
except ImportError:
    _HAS_BACKTRADER = False

try:
    from src.execution import ExecutionEngine
    _HAS_EXECUTION = True
except ImportError:
    _HAS_EXECUTION = False

logger = get_logger(__name__)


def run_backtest_mode(config: dict):
    """运行回测模式"""
    if not _HAS_BACKTRADER:
        logger.error("回测模式需要backtrader，请先安装: pip install backtrader")
        print("\n[ERROR] 回测模式需要backtrader模块")
        print("安装命令: pip install backtrader")
        return

    logger.info("启动回测模式")

    backtest_config = config.get("backtest", {})
    start_date = backtest_config.get("start_date", "2022-01-01")
    end_date = backtest_config.get("end_date", "2023-12-31")

    # 示例：使用交易量动量策略回测
    engine = BacktestEngine(config)

    # 加载示例数据
    data_feed = DataFeed(config)
    # 这里应该加载实际数据，简化处理

    engine.add_strategy(VolumeMomentumStrategy)

    logger.info(f"运行回测: {start_date} 到 {end_date}")
    results = engine.run_backtest(start_date, end_date)

    # 输出结果
    summary = results.get("summary", {})
    print("\n" + "="*60)
    print("回测结果")
    print("="*60)
    print(f"年化收益率: {summary.get('annual_return', 0)*100:.2f}%")
    print(f"夏普比率: {summary.get('sharpe_ratio', 0):.3f}")
    print(f"最大回撤: {summary.get('max_drawdown', 0)*100:.2f}%")
    print(f"胜率: {summary.get('win_rate', 0)*100:.2f}%")
    print("="*60)


def run_factor_mode(config: dict):
    """运行因子计算模式"""
    logger.info("启动因子计算模式")

    calculator = FactorCalculator(config)

    # 列出所有因子
    factors = calculator.list_factors()
    print("\n可用因子列表:")
    for factor in factors:
        print(f"  - {factor['name']}: {factor['description']}")


def run_live_mode(config: dict):
    """运行实盘模式"""
    if not _HAS_EXECUTION:
        logger.error("实盘模式依赖模块未安装")
        print("\n[ERROR] 实盘模式依赖模块未安装")
        return

    logger.info("启动实盘模式")

    engine = ExecutionEngine(config)

    if engine.start():
        logger.info("实盘引擎已启动")

        try:
            # 保持运行
            import time
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("接收到停止信号")
        finally:
            engine.stop()
    else:
        logger.error("实盘引擎启动失败")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="A股量化交易系统")
    parser.add_argument(
        "--config",
        type=str,
        default="config.yaml",
        help="配置文件路径"
    )
    parser.add_argument(
        "--mode",
        type=str,
        choices=["backtest", "factor", "live", "optimize"],
        default="backtest",
        help="运行模式"
    )

    args = parser.parse_args()

    # 加载配置
    try:
        config = ConfigLoader.load_yaml(args.config)
        logger.info(f"配置加载成功: {args.config}")
    except Exception as e:
        logger.error(f"配置加载失败: {e}")
        config = ConfigLoader.create_default_config()
        logger.info("使用默认配置")

    # 设置日志
    log_config = config.get("logging", {})
    setup_logging(
        level=log_config.get("level", "INFO"),
        log_file=log_config.get("file", "logs/quant_system.log")
    )

    # 根据模式运行
    if args.mode == "backtest":
        run_backtest_mode(config)
    elif args.mode == "factor":
        run_factor_mode(config)
    elif args.mode == "live":
        run_live_mode(config)
    else:
        logger.error(f"不支持的模式: {args.mode}")


if __name__ == "__main__":
    main()
