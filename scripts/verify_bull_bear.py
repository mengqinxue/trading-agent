# -*- coding: utf-8 -*-
"""
牛熊周期验证脚本

输出上证指数1990年以来所有牛熊周期，验证策略模块效果。

用法：
    uv run python scripts/verify_bull_bear.py
"""

import sys
from pathlib import Path

# 设置路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from strategies import MarketTrendStrategy, BullBearCycleDetector
from src.data_sources import load_index_daily


def main():
    """验证牛熊周期检测"""
    print("=" * 70)
    print("牛熊周期验证脚本")
    print("=" * 70)

    # 加载上证指数历史数据
    print("\n[1] 加载上证指数历史数据...")
    df = load_index_daily("000001")

    if df is None or df.empty:
        print("❌ 无法加载上证指数数据")
        return

    print(f"✅ 数据范围: {df.iloc[0]['date']} ~ {df.iloc[-1]['date']}")
    print(f"✅ 数据条数: {len(df)} 条")

    # 当前市场状态判断
    print("\n[2] 当前市场状态判断...")
    trend_strategy = MarketTrendStrategy()
    result = trend_strategy.analyze(df)

    print(f"\n当前状态: {result['status']}")
    print(f"趋势强度: {result['trend_strength']}")
    print(f"置信度: {result['confidence']:.2f}")
    print(f"分析日期: {result['date']}")
    print(f"当前价格: {result['price']:.2f}")
    print(f"MA20: {result['ma20']:.2f}, MA60: {result['ma60']:.2f}")

    print("\n判断信号:")
    for signal in result["signals"]:
        print(f"  - {signal}")

    print("\n技术指标:")
    print(f"  RSI(14): {result['rsi']:.2f}")
    print(f"  MACD: DIF={result['macd']['dif']:.4f}, DEA={result['macd']['dea']:.4f}")

    print("\n涨跌幅:")
    for period, change in result["price_change"].items():
        print(f"  {period}: {change:+.2f}%")

    # 历史牛熊周期检测
    print("\n[3] 历史牛熊周期检测...")
    cycle_detector = BullBearCycleDetector()
    cycles = cycle_detector.detect_cycles(df)

    # 打印周期列表
    cycle_detector.print_cycles(cycles, "上证指数")

    # 保存周期到文件
    output_file = Path("data/CN_A/index_daily/bull_bear_cycles.json")
    import json
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(json.dumps(cycles, ensure_ascii=False, indent=2))
    print(f"\n周期数据已保存到: {output_file}")

    # 统计摘要
    summary = cycle_detector.get_cycle_summary(cycles)
    print("\n统计摘要:")
    print(f"  总周期数: {summary['total_cycles']}")
    print(f"  牛市周期: {summary['bull_count']} 个, 平均涨幅 {summary['avg_bull_change']:+.2f}%")
    print(f"  熊市周期: {summary['bear_count']} 个, 平均跌幅 {summary['avg_bear_change']:+.2f}%")
    print(f"  震荡周期: {summary['oscillation_count']} 个")
    print(f"  牛市平均持续: {summary['avg_bull_days']} 天")
    print(f"  熊市平均持续: {summary['avg_bear_days']} 天")

    print("\n" + "=" * 70)
    print("验证完成")
    print("=" * 70)


if __name__ == "__main__":
    main()