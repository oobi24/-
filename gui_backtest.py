#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
量化策略回测可视化界面 (纯tkinter版本)
支持CSV数据导入
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
import sys
from pathlib import Path
import pandas as pd
import numpy as np
import threading

sys.path.insert(0, str(Path(__file__).parent / "src"))

from simple_backtest import SimpleBacktestEngine, volume_momentum_strategy, ma_cross_strategy
from src.utils.config_loader import ConfigLoader
from data_loader import StockDataLoader

# 尝试导入Tushare
try:
    from tushare_feed import TushareDataFeed
    _HAS_TUSHARE = True
except ImportError:
    _HAS_TUSHARE = False

# 导入本地股票列表
from stock_code_list import search_stock_local


class QuantGUI:
    """量化回测GUI"""

    def __init__(self, root):
        self.root = root
        self.root.title("A股量化策略回测系统 v1.0")
        self.root.geometry("1200x800")
        self.root.minsize(900, 600)

        # 数据缓存
        self.data = None
        self.results = None
        self.current_file = None

        self._check_environment()
        self._create_widgets()
        self._load_default_config()

    def _check_environment(self):
        """检查Python环境"""
        import sys
        # 检查是否是Anaconda Python
        is_anaconda = 'anaconda' in sys.executable.lower() or 'conda' in sys.executable.lower()
        if not is_anaconda:
            # 显示警告
            self.root.after(100, self._show_env_warning)

    def _show_env_warning(self):
        """显示环境警告"""
        import sys
        msg = f"""当前Python环境可能不是Anaconda:

{sys.executable}

这可能导致Tushare等模块无法找到。

请使用以下方式启动:
1. 双击运行 run_gui.bat
2. 或在终端运行: C:\ProgramData\Anaconda3\python.exe gui_backtest.py
"""
        messagebox.showwarning("环境警告", msg)

    def _create_widgets(self):
        """创建界面组件"""
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 配置行列权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(2, weight=1)

        # ===== 左侧面板：参数配置 =====
        left_frame = ttk.LabelFrame(main_frame, text="策略配置", padding="10")
        left_frame.grid(row=0, column=0, rowspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))
        left_frame.columnconfigure(0, weight=1)

        # 数据加载框架
        data_frame = ttk.LabelFrame(left_frame, text="数据源", padding="10")
        data_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))

        self.data_source_var = tk.StringVar(value="sample")
        ttk.Radiobutton(data_frame, text="示例数据", variable=self.data_source_var,
                       value="sample").grid(row=0, column=0, sticky=tk.W)
        ttk.Radiobutton(data_frame, text="CSV文件", variable=self.data_source_var,
                       value="csv").grid(row=1, column=0, sticky=tk.W)
        ttk.Radiobutton(data_frame, text="Tushare在线数据", variable=self.data_source_var,
                       value="tushare").grid(row=2, column=0, sticky=tk.W)
        ttk.Radiobutton(data_frame, text="生成随机数据", variable=self.data_source_var,
                       value="random").grid(row=3, column=0, sticky=tk.W)

        # CSV文件路径
        self.csv_path_var = tk.StringVar()
        ttk.Entry(data_frame, textvariable=self.csv_path_var, state="readonly").grid(row=4, column=0, sticky=(tk.W, tk.E), pady=(5, 0))
        ttk.Button(data_frame, text="浏览...", command=self._browse_csv).grid(row=4, column=1, padx=(5, 0), pady=(5, 0))

        # Tushare配置区域
        ttk.Separator(data_frame, orient=tk.HORIZONTAL).grid(row=5, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 5))

        # 股票代码
        ttk.Label(data_frame, text="股票代码:").grid(row=6, column=0, sticky=tk.W, pady=(5, 0))
        self.stock_symbol_var = tk.StringVar(value="000001.SZ")
        ttk.Entry(data_frame, textvariable=self.stock_symbol_var, width=15).grid(row=6, column=1, sticky=(tk.W, tk.E), padx=(5, 0), pady=(5, 0))

        # 开始日期
        ttk.Label(data_frame, text="开始日期:").grid(row=7, column=0, sticky=tk.W, pady=(5, 0))
        self.start_date_var = tk.StringVar(value="2023-01-01")
        ttk.Entry(data_frame, textvariable=self.start_date_var, width=15).grid(row=7, column=1, sticky=(tk.W, tk.E), padx=(5, 0), pady=(5, 0))

        # 结束日期
        ttk.Label(data_frame, text="结束日期:").grid(row=8, column=0, sticky=tk.W, pady=(5, 0))
        self.end_date_var = tk.StringVar(value="2023-12-31")
        ttk.Entry(data_frame, textvariable=self.end_date_var, width=15).grid(row=8, column=1, sticky=(tk.W, tk.E), padx=(5, 0), pady=(5, 0))

        # 搜索股票按钮
        ttk.Button(data_frame, text="搜索股票...", command=self._search_stock).grid(row=9, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))

        # 加载数据按钮
        ttk.Button(left_frame, text="加载数据", command=self._load_data, width=20).grid(row=1, column=0, pady=(0, 10))

        # 数据信息显示
        self.data_info_var = tk.StringVar(value="未加载数据")
        ttk.Label(left_frame, textvariable=self.data_info_var, foreground="gray").grid(row=2, column=0, pady=(0, 10))

        # 策略选择
        ttk.Label(left_frame, text="策略类型:").grid(row=3, column=0, sticky=tk.W, pady=(0, 5))
        self.strategy_var = tk.StringVar(value="volume_momentum")
        strategy_combo = ttk.Combobox(left_frame, textvariable=self.strategy_var,
                                      values=["volume_momentum", "ma_cross", "rsi", "macd"],
                                      state="readonly", width=20)
        strategy_combo.grid(row=4, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        strategy_combo.bind("<<ComboboxSelected>>", self._on_strategy_change)

        # 参数框架
        self.param_frame = ttk.LabelFrame(left_frame, text="策略参数", padding="10")
        self.param_frame.grid(row=5, column=0, sticky=(tk.W, tk.E), pady=(0, 10))

        # 动态参数
        self.param_vars = {}
        self._create_strategy_params()

        # 回测配置
        backtest_frame = ttk.LabelFrame(left_frame, text="回测配置", padding="10")
        backtest_frame.grid(row=6, column=0, sticky=(tk.W, tk.E), pady=(0, 10))

        # 初始资金
        ttk.Label(backtest_frame, text="初始资金:").grid(row=0, column=0, sticky=tk.W)
        self.initial_cash_var = tk.StringVar(value="1000000")
        ttk.Entry(backtest_frame, textvariable=self.initial_cash_var, width=15).grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(5, 0))

        # 佣金
        ttk.Label(backtest_frame, text="佣金率(‱):").grid(row=1, column=0, sticky=tk.W, pady=(5, 0))
        self.commission_var = tk.StringVar(value="2.5")
        ttk.Entry(backtest_frame, textvariable=self.commission_var, width=15).grid(row=1, column=1, sticky=(tk.W, tk.E), padx=(5, 0), pady=(5, 0))

        # 印花税
        ttk.Label(backtest_frame, text="印花税(‱):").grid(row=2, column=0, sticky=tk.W, pady=(5, 0))
        self.tax_var = tk.StringVar(value="10")
        ttk.Entry(backtest_frame, textvariable=self.tax_var, width=15).grid(row=2, column=1, sticky=(tk.W, tk.E), padx=(5, 0), pady=(5, 0))

        # 操作按钮
        btn_frame = ttk.Frame(left_frame)
        btn_frame.grid(row=7, column=0, sticky=(tk.W, tk.E), pady=(10, 0))

        ttk.Button(btn_frame, text="运行回测", command=self._run_backtest, width=25).grid(row=0, column=0)

        # 进度条
        self.progress = ttk.Progressbar(left_frame, mode='indeterminate', length=200)
        self.progress.grid(row=8, column=0, sticky=(tk.W, tk.E), pady=(10, 0))

        # ===== 右侧面板：结果显示 =====
        right_frame = ttk.Notebook(main_frame)
        right_frame.grid(row=0, column=1, rowspan=3, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 绩效指标页
        metrics_frame = ttk.Frame(right_frame, padding="10")
        right_frame.add(metrics_frame, text="绩效指标")
        metrics_frame.columnconfigure(1, weight=1)

        # 绩效指标显示
        self.metrics_labels = {}
        metrics = [
            ("初始资金", "initial_cash", "{:.0f}"),
            ("最终价值", "final_value", "{:.0f}"),
            ("总收益率", "total_return", "{:.2%}"),
            ("年化收益", "annual_return", "{:.2%}"),
            ("最大回撤", "max_drawdown", "{:.2%}"),
            ("夏普比率", "sharpe_ratio", "{:.3f}"),
            ("交易次数", "total_trades", "{:d}"),
            ("胜率", "win_rate", "{:.2%}"),
            ("盈利次数", "winning_trades", "{:d}"),
        ]

        for i, (name, key, fmt) in enumerate(metrics):
            ttk.Label(metrics_frame, text=f"{name}:", font=("Microsoft YaHei", 10, "bold")).grid(
                row=i, column=0, sticky=tk.W, pady=(8, 0))
            label = ttk.Label(metrics_frame, text="-", font=("Microsoft YaHei", 10))
            label.grid(row=i, column=1, sticky=tk.W, padx=(15, 0), pady=(8, 0))
            self.metrics_labels[key] = (label, fmt)

        # 收益曲线页（使用Canvas绘制）
        chart_frame = ttk.Frame(right_frame, padding="10")
        right_frame.add(chart_frame, text="收益曲线")
        chart_frame.columnconfigure(0, weight=1)
        chart_frame.rowconfigure(0, weight=1)

        # 创建Canvas用于绘图
        self.chart_canvas = tk.Canvas(chart_frame, bg="white", width=600, height=350)
        self.chart_canvas.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 交易记录页
        trade_frame = ttk.Frame(right_frame, padding="10")
        right_frame.add(trade_frame, text="交易记录")
        trade_frame.columnconfigure(0, weight=1)
        trade_frame.rowconfigure(0, weight=1)

        self.trade_text = scrolledtext.ScrolledText(trade_frame, wrap=tk.WORD, width=70, height=25)
        self.trade_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 日志页
        log_frame = ttk.Frame(right_frame, padding="10")
        right_frame.add(log_frame, text="运行日志")
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)

        self.log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, width=70, height=25)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 状态栏
        self.status_var = tk.StringVar(value="就绪")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))

    def _browse_csv(self):
        """浏览CSV文件"""
        filename = filedialog.askopenfilename(
            title="选择股票数据CSV文件",
            filetypes=[("CSV文件", "*.csv"), ("所有文件", "*.*")]
        )
        if filename:
            self.csv_path_var.set(filename)
            self.data_source_var.set("csv")

    def _search_stock(self):
        """搜索股票"""
        if not _HAS_TUSHARE:
            msg = """Tushare模块未找到。

可能的原因:
1. 你是通过双击运行此文件，使用了系统默认的Python环境
2. Tushare安装在用户目录但Python路径未包含

解决方法:
请使用 run_gui.bat 启动程序，它会正确设置Python环境。

或者手动运行:
  C:\ProgramData\Anaconda3\python.exe gui_backtest.py"""
            messagebox.showerror("Tushare未找到", msg)
            return

        # 创建搜索对话框
        search_window = tk.Toplevel(self.root)
        search_window.title("搜索股票")
        search_window.geometry("400x300")
        search_window.transient(self.root)
        search_window.grab_set()

        # 搜索框
        ttk.Label(search_window, text="输入股票代码或名称:").pack(pady=(10, 5))
        search_var = tk.StringVar()
        ttk.Entry(search_window, textvariable=search_var, width=30).pack(pady=(0, 10))

        # 结果列表
        result_frame = ttk.Frame(search_window)
        result_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        result_listbox = tk.Listbox(result_frame, width=50, height=10)
        result_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(result_frame, orient=tk.VERTICAL, command=result_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        result_listbox.config(yscrollcommand=scrollbar.set)

        def do_search():
            keyword = search_var.get()
            if not keyword:
                return

            result_listbox.delete(0, tk.END)

            # 首先尝试Tushare在线搜索
            if _HAS_TUSHARE:
                try:
                    token = self.config.get('data_sources', {}).get('tushare', {}).get('token')
                    if token:
                        feed = TushareDataFeed(token)
                        results = feed.search_stock(keyword)

                        if not results.empty:
                            for _, row in results.head(20).iterrows():
                                industry = row.get('industry', '未知')
                                display = f"{row['ts_code']} - {row['name']} ({industry})"
                                result_listbox.insert(tk.END, display)
                            return
                except Exception as e:
                    self._log(f"Tushare搜索失败，使用本地列表: {e}")

            # 使用本地股票列表搜索
            results = search_stock_local(keyword)

            if not results:
                result_listbox.insert(tk.END, "未找到匹配的股票")
            else:
                for stock in results[:20]:
                    display = f"{stock['ts_code']} - {stock['name']} ({stock['industry']})"
                    result_listbox.insert(tk.END, display)

        def select_stock():
            selection = result_listbox.curselection()
            if selection:
                selected = result_listbox.get(selection[0])
                ts_code = selected.split(" - ")[0]
                self.stock_symbol_var.set(ts_code)
                self.data_source_var.set("tushare")
                search_window.destroy()

        # 按钮
        btn_frame = ttk.Frame(search_window)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="搜索", command=do_search).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="选择", command=select_stock).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="关闭", command=search_window.destroy).pack(side=tk.LEFT, padx=5)

    def _create_strategy_params(self):
        """创建策略参数输入"""
        # 清除旧参数
        for widget in self.param_frame.winfo_children():
            widget.destroy()
        self.param_vars.clear()

        strategy = self.strategy_var.get()

        if strategy == "volume_momentum":
            params = [
                ("量比阈值", "volume_ratio", "1.5"),
                ("最大持仓天数", "max_hold_days", "10"),
                ("止损比例(%)", "stop_loss", "8"),
            ]
        elif strategy == "ma_cross":
            params = [
                ("短期均线", "short_ma", "5"),
                ("长期均线", "long_ma", "20"),
            ]
        elif strategy == "rsi":
            params = [
                ("RSI周期", "rsi_period", "14"),
                ("超买阈值", "overbought", "70"),
                ("超卖阈值", "oversold", "30"),
            ]
        elif strategy == "macd":
            params = [
                ("快线周期", "fast", "12"),
                ("慢线周期", "slow", "26"),
                ("信号周期", "signal", "9"),
            ]
        else:
            params = []

        for i, (label, key, default) in enumerate(params):
            ttk.Label(self.param_frame, text=f"{label}:").grid(row=i, column=0, sticky=tk.W, pady=(5, 0))
            var = tk.StringVar(value=default)
            ttk.Entry(self.param_frame, textvariable=var, width=12).grid(
                row=i, column=1, sticky=(tk.W, tk.E), padx=(5, 0), pady=(5, 0))
            self.param_vars[key] = var

    def _on_strategy_change(self, event=None):
        """策略改变时更新参数"""
        self._create_strategy_params()

    def _load_default_config(self):
        """加载默认配置"""
        try:
            self.config = ConfigLoader.create_default_config()
            self._log("系统初始化完成")
            self._log("默认配置加载成功")
        except Exception as e:
            self._log(f"配置加载失败: {e}")

    def _log(self, message):
        """添加日志"""
        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)

    def _load_data(self):
        """加载数据"""
        self.status_var.set("正在加载数据...")
        self.progress.start()
        self.root.update()

        try:
            source = self.data_source_var.get()

            if source == "sample":
                # 加载示例数据
                sample_path = Path(__file__).parent / "data" / "sample" / "000001.SZ.csv"
                if sample_path.exists():
                    self.data = StockDataLoader.load_from_csv(str(sample_path))
                    self.current_file = str(sample_path)
                    self._log(f"加载示例数据: {sample_path}")
                else:
                    # 生成并保存示例数据
                    self.data = StockDataLoader.generate_sample_data("2023-01-01", "2023-12-31", "000001.SZ")
                    sample_path.parent.mkdir(parents=True, exist_ok=True)
                    StockDataLoader.save_to_csv(self.data, str(sample_path))
                    self.current_file = str(sample_path)
                    self._log("生成并保存示例数据")

            elif source == "csv":
                # 从CSV加载
                csv_path = self.csv_path_var.get()
                if not csv_path:
                    messagebox.showwarning("警告", "请选择CSV文件")
                    return
                self.data = StockDataLoader.load_from_csv(csv_path)
                self.current_file = csv_path
                self._log(f"加载CSV数据: {csv_path}")

            elif source == "random":
                # 生成随机数据
                self.data = StockDataLoader.generate_sample_data("2023-01-01", "2023-12-31", "RANDOM.SZ", seed=None)
                self.current_file = None
                self._log("生成随机数据")

            elif source == "tushare":
                # 从Tushare获取数据
                if not _HAS_TUSHARE:
                    msg = """Tushare模块未找到。

请使用 run_gui.bat 启动程序，它会正确设置Python环境。"""
                    messagebox.showerror("Tushare未找到", msg)
                    return

                symbol = self.stock_symbol_var.get()
                start_date = self.start_date_var.get()
                end_date = self.end_date_var.get()

                # 从配置获取token
                token = self.config.get('data_sources', {}).get('tushare', {}).get('token')
                if not token:
                    messagebox.showerror("错误", "请在config.yaml中配置Tushare token")
                    return

                self._log(f"从Tushare获取数据: {symbol}")
                try:
                    feed = TushareDataFeed(token)
                    self.data = feed.get_daily_data(symbol, start_date, end_date)
                    self.current_file = None
                    self._log(f"Tushare数据获取成功: {len(self.data)}条记录")
                except RuntimeError as e:
                    error_msg = str(e)
                    if "权限" in error_msg or "积分" in error_msg or "api init error" in error_msg.lower():
                        msg = """Tushare接口权限不足。

你的token没有访问日线数据的权限。

解决方案:
1. 去 https://tushare.pro/document/1?doc_id=108 查看积分规则
2. 或者使用CSV文件导入数据（推荐）

示例CSV格式:
date,open,high,low,close,volume
2023-01-03,12.35,12.58,12.28,12.45,45231500
..."""
                        messagebox.showerror("Tushare权限不足", msg)
                        self._log(f"Tushare权限错误: {e}")
                    else:
                        raise

            # 更新信息显示
            if self.data is not None:
                info = f"股票: {self.data['symbol'].iloc[0]} | 记录: {len(self.data)}条 | 日期: {self.data.index[0].date()} ~ {self.data.index[-1].date()}"
                self.data_info_var.set(info)
                self._log(f"数据加载成功: {len(self.data)}条记录")
                self._log(f"日期范围: {self.data.index[0].date()} 到 {self.data.index[-1].date()}")
                self._log(f"价格范围: {self.data['close'].min():.2f} ~ {self.data['close'].max():.2f}")
                self.status_var.set(f"数据就绪: {len(self.data)}条")

                # 绘制价格预览
                self._draw_price_preview()

        except Exception as e:
            messagebox.showerror("错误", f"数据加载失败: {e}")
            self._log(f"错误: {e}")
        finally:
            self.progress.stop()

    def _draw_price_preview(self):
        """绘制价格预览"""
        if self.data is None or self.data.empty:
            return

        canvas = self.chart_canvas
        canvas.delete("all")

        width = canvas.winfo_width()
        height = canvas.winfo_height()

        # 价格数据
        prices = self.data["close"].values
        n = len(prices)

        # 归一化到画布
        min_p, max_p = prices.min(), prices.max()
        padding = 50

        # 绘制标题
        symbol = self.data['symbol'].iloc[0]
        canvas.create_text(width//2, 20, text=f"{symbol} - Close Price Preview", font=("Arial", 12, "bold"))

        # 绘制坐标轴
        canvas.create_line(padding, height-padding, width-padding, height-padding, width=2)  # X轴
        canvas.create_line(padding, padding, padding, height-padding, width=2)  # Y轴

        # 绘制价格曲线
        x_scale = (width - 2*padding) / (n-1) if n > 1 else 1
        y_scale = (height - 2*padding) / (max_p - min_p) if max_p > min_p else 1

        points = []
        for i, p in enumerate(prices):
            x = padding + i * x_scale
            y = height - padding - (p - min_p) * y_scale
            points.extend([x, y])

        if len(points) >= 4:
            canvas.create_line(points, fill="blue", width=1.5, smooth=True)

        # Y轴标签
        canvas.create_text(padding-20, padding, text=f"{max_p:.2f}", font=("Arial", 8))
        canvas.create_text(padding-20, height-padding, text=f"{min_p:.2f}", font=("Arial", 8))

        # 统计信息
        canvas.create_text(width//2, height-15, text=f"Records: {n} | Range: {min_p:.2f}~{max_p:.2f}", font=("Arial", 9))

    def _run_backtest(self):
        """运行回测"""
        if self.data is None:
            messagebox.showwarning("警告", "请先加载数据")
            return

        # 在新线程中运行回测，避免界面卡顿
        thread = threading.Thread(target=self._backtest_worker)
        thread.daemon = True
        thread.start()

    def _backtest_worker(self):
        """回测工作线程"""
        self.status_var.set("正在运行回测...")
        self.progress.start()

        try:
            # 更新配置
            self.config["backtest"]["initial_cash"] = float(self.initial_cash_var.get())
            self.config["backtest"]["commission"] = float(self.commission_var.get()) / 10000
            self.config["backtest"]["stamp_tax"] = float(self.tax_var.get()) / 1000

            # 创建引擎
            engine = SimpleBacktestEngine(self.config)

            # 获取策略参数
            strategy_params = {k: float(v.get()) for k, v in self.param_vars.items()}

            # 选择策略
            strategy_name = self.strategy_var.get()
            if strategy_name == "volume_momentum":
                strategy_func = volume_momentum_strategy
            elif strategy_name == "ma_cross":
                strategy_func = ma_cross_strategy
            else:
                strategy_func = volume_momentum_strategy

            self._log(f"开始回测: {strategy_name}")
            self._log(f"策略参数: {strategy_params}")
            self._log(f"股票代码: {self.data['symbol'].iloc[0]}")

            # 运行回测
            self.results = engine.run_backtest(
                self.data,
                strategy_func,
                strategy_params
            )

            # 更新界面
            self.root.after(0, self._update_results)

        except Exception as e:
            self.root.after(0, lambda: self._show_error(f"回测失败: {e}"))
        finally:
            self.root.after(0, self._stop_progress)

    def _update_results(self):
        """更新结果显示"""
        if not self.results:
            return

        # 更新绩效指标
        for key, (label, fmt) in self.metrics_labels.items():
            value = self.results.get(key, 0)
            label.config(text=fmt.format(value))

        # 更新图表
        self._update_chart()

        # 更新交易记录
        self._update_trade_records()

        self._log("回测完成!")
        self.status_var.set("回测完成")

    def _update_chart(self):
        """更新收益曲线图"""
        daily_values = self.results.get("daily_values")
        if daily_values is None or daily_values.empty:
            return

        canvas = self.chart_canvas
        canvas.delete("all")

        width = canvas.winfo_width()
        height = canvas.winfo_height()

        values = daily_values["value"].values
        n = len(values)
        initial = self.results.get("initial_cash", 1000000)

        # 归一化
        min_v, max_v = values.min(), values.max()
        padding = 50

        # 标题
        symbol = self.data['symbol'].iloc[0] if self.data is not None else "Stock"
        canvas.create_text(width//2, 20, text=f"{symbol} - Backtest Performance", font=("Arial", 12, "bold"))

        # 坐标轴
        canvas.create_line(padding, height-padding, width-padding, height-padding, width=2)
        canvas.create_line(padding, padding, padding, height-padding, width=2)

        # 绘制初始资金基准线
        if max_v > min_v:
            y_baseline = height - padding - (initial - min_v) / (max_v - min_v) * (height - 2*padding)
            canvas.create_line(padding, y_baseline, width-padding, y_baseline, fill="gray", dash=(4, 4))
            canvas.create_text(padding-30, y_baseline, text="Initial", font=("Arial", 8), fill="gray")

        # 绘制资金曲线
        x_scale = (width - 2*padding) / (n-1) if n > 1 else 1
        y_scale = (height - 2*padding) / (max_v - min_v) if max_v > min_v else 1

        points = []
        for i, v in enumerate(values):
            x = padding + i * x_scale
            y = height - padding - (v - min_v) * y_scale
            points.extend([x, y])

        if len(points) >= 4:
            # 根据盈亏设置颜色
            color = "green" if values[-1] >= initial else "red"
            canvas.create_line(points, fill=color, width=2, smooth=True)

        # 标注最终值
        final_y = height - padding - (values[-1] - min_v) * y_scale
        canvas.create_text(width-padding+40, final_y, text=f"{values[-1]:.0f}", font=("Arial", 9, "bold"))

        # Y轴范围
        canvas.create_text(padding-25, padding, text=f"{max_v:.0f}", font=("Arial", 8))
        canvas.create_text(padding-25, height-padding, text=f"{min_v:.0f}", font=("Arial", 8))

        # 统计信息
        total_ret = (values[-1] - initial) / initial
        canvas.create_text(width//2, height-15, text=f"Total Return: {total_ret*100:.2f}%", font=("Arial", 10, "bold"))

    def _update_trade_records(self):
        """更新交易记录"""
        self.trade_text.delete(1.0, tk.END)

        trades = self.results.get("trades", [])
        if not trades:
            self.trade_text.insert(tk.END, "无交易记录\n")
            return

        symbol = self.data['symbol'].iloc[0] if self.data is not None else ""
        self.trade_text.insert(tk.END, f"交易记录 - {symbol} (共{len(trades)}笔)\n")
        self.trade_text.insert(tk.END, "=" * 70 + "\n\n")

        for trade in trades:
            date = trade["date"].strftime("%Y-%m-%d")
            action = "买入" if trade["action"] == "buy" else "卖出"
            price = trade["price"]
            size = trade["size"]

            if trade["action"] == "sell":
                pnl = trade.get("pnl", 0)
                self.trade_text.insert(tk.END,
                    f"{date}  {action:2s}  {size:6,d}股  @  {price:7.2f}  盈亏: {pnl:+12,.2f}\n")
            else:
                cost = trade.get("cost", 0)
                self.trade_text.insert(tk.END,
                    f"{date}  {action:2s}  {size:6,d}股  @  {price:7.2f}  成本: {cost:12,.2f}\n")

    def _stop_progress(self):
        """停止进度条"""
        self.progress.stop()

    def _show_error(self, message):
        """显示错误"""
        messagebox.showerror("错误", message)
        self._log(f"错误: {message}")


def main():
    """主函数"""
    root = tk.Tk()

    # 设置DPI感知
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except:
        pass

    # 设置主题
    style = ttk.Style()
    try:
        style.theme_use('vista')
    except:
        pass

    app = QuantGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
