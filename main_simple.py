#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A-Share Quant System - Simplified Test Version (no akshare required)
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

import pandas as pd
import numpy as np

print("=" * 60)
print("A-Share Quant System - Module Test")
print("=" * 60)

# Test 1: Config
print("\n[1] Testing config module...")
try:
    from src.utils.config_loader import ConfigLoader
    config = ConfigLoader.create_default_config()
    print("[OK] Config module loaded")
    print(f"  - Initial cash: {config['backtest']['initial_cash']:,}")
    print(f"  - Commission: {config['backtest']['commission']*10000:.0f} bp")
except Exception as e:
    print(f"[ERROR] {e}")

# Test 2: Factor Module
print("\n[2] Testing factor module...")
try:
    from src.factors import FactorCalculator
    calc = FactorCalculator({})
    factors = calc.list_factors()
    print("[OK] Factor module loaded")
    print(f"  - Total factors: {len(factors)}")

    categories = calc.get_factor_categories()
    for cat, facs in categories.items():
        print(f"  - {cat}: {len(facs)} factors")
except Exception as e:
    print(f"[ERROR] {e}")

# Test 3: Multi-Factor Engine
print("\n[3] Testing multi-factor engine...")
try:
    from src.factors import MultiFactorEngine

    engine = MultiFactorEngine({
        "method": "score",
        "weights": {"value": 0.3, "quality": 0.3, "growth": 0.4},
        "neutralization": True
    })
    print("[OK] Multi-factor engine loaded")

    np.random.seed(42)
    test_data = pd.DataFrame({
        "value_pe_ttm": np.random.randn(100),
        "quality_roe": np.random.randn(100),
        "growth_revenue_yoy": np.random.randn(100),
    })

    scores = engine.calculate_factor_scores(
        test_data,
        ["value_pe_ttm", "quality_roe", "growth_revenue_yoy"],
        method="zscore"
    )
    print(f"[OK] Factor scores computed: {scores.shape}")

    combined = engine.combine_factors(scores)
    print(f"[OK] Factors combined: mean={combined.mean():.3f}, std={combined.std():.3f}")

except Exception as e:
    print(f"[ERROR] {e}")
    import traceback
    traceback.print_exc()

# Test 4: Utils Module
print("\n[4] Testing utils module...")
try:
    from src.utils.data_utils import DataUtils
    from src.utils.time_utils import TimeUtils

    test_series = pd.Series([1, 2, 3, 4, 5, 100, -50])
    winsorized = DataUtils.winsorize_data(test_series)
    print("[OK] Winsorization works")
    print(f"  - Original range: [{test_series.min():.1f}, {test_series.max():.1f}]")
    print(f"  - After: [{winsorized.min():.1f}, {winsorized.max():.1f}]")

    today = pd.Timestamp.now()
    prev_trade = TimeUtils.get_previous_trade_date(today)
    print("[OK] Trade date calculation works")
    print(f"  - Today: {today.strftime('%Y-%m-%d')}")
    print(f"  - Prev trade day: {prev_trade.strftime('%Y-%m-%d')}")

except Exception as e:
    print(f"[ERROR] {e}")

# Test 5: Backtest Module
print("\n[5] Testing backtest module...")
try:
    from src.backtest import VolumeMomentumStrategy
    print("[OK] Backtest strategy loaded")
    print("  - Strategy: VolumeMomentumStrategy")
except Exception as e:
    print(f"[ERROR] {e}")

# Test 6: Risk Module
print("\n[6] Testing risk module...")
try:
    from src.execution import RiskManager

    risk_mgr = RiskManager({
        "risk_control": {
            "position": {"max_single_position": 0.1},
            "stop_loss": {"price_stop": 0.08}
        }
    })
    print("[OK] Risk manager loaded")

    is_ok, reason = risk_mgr.check_position_risk(
        "000001.SZ", 1000, 10.0,
        {}, 1000000
    )
    print(f"[OK] Position risk check: {'PASS' if is_ok else 'REJECT'}")

except Exception as e:
    print(f"[ERROR] {e}")

print("\n" + "=" * 60)
print("Test completed!")
print("=" * 60)
