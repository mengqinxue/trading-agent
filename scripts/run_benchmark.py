# -*- coding: utf-8 -*-
"""
回测系统Benchmark测试

运行多个策略和时间段的回测，对比结果验证系统准确性。
"""

import logging
import json
import time
from datetime import datetime
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)8s | %(message)s",
)

from src.backtest import BacktestRunner

# 输出目录
OUTPUT_DIR = Path("data/backtest/benchmark")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def run_benchmark(name: str, description: str, start: str, end: str, capital: float = 100000):
    """运行单个benchmark测试"""
    print("=" * 70)
    print(f"Benchmark: {name}")
    print("=" * 70)
    print(f"策略: {description}")
    print(f"时间: {start} ~ {end}")
    print(f"资金: {capital:,.0f} 元")
    print()

    runner = BacktestRunner()
    start_time = time.time()

    result = runner.run_from_description(
        description=description,
        start_date=start,
        end_date=end,
        initial_capital=capital,
    )

    elapsed = time.time() - start_time

    if result.get("success"):
        summary = result["summary"]
        output = {
            "name": name,
            "description": description,
            "start_date": start,
            "end_date": end,
            "initial_capital": capital,
            "elapsed_seconds": elapsed,
            "summary": summary,
            "timestamp": datetime.now().isoformat(),
        }

        # 保存结果
        output_file = OUTPUT_DIR / f"{name}.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

        print(f"\n结果:")
        print(f"  总收益率: {summary.get('total_return', 0):.2f}%")
        print(f"  年化收益: {summary.get('annual_return', 0):.2f}%")
        print(f"  最大回撤: {summary.get('max_drawdown', 0):.2f}%")
        print(f"  夏普比率: {summary.get('sharpe_ratio', 0):.2f}")
        print(f"  胜率: {summary.get('win_rate', 0):.2f}%")
        print(f"  盈亏比: {summary.get('profit_ratio', 0):.2f}")
        print(f"  总交易: {summary.get('total_trades', 0)}")
        print(f"  回测天数: {summary.get('total_days', 0)}")
        print(f"\n耗时: {elapsed:.1f} 秒")
        print(f"结果保存: {output_file}")

        return output
    else:
        print(f"\n失败: {result.get('error')}")
        return None


def main():
    """运行所有benchmark测试"""
    print("=" * 70)
    print("回测系统 Benchmark 测试")
    print("=" * 70)
    print()

    # Benchmark配置
    # 参考数据：
    # - 2018-2021: 涨停板策略年化20-35%
    # - 2022: 年化-5%~5%
    # - 2023: 年化-10%~0%
    # - 2024: 年化0~8%

    benchmarks = [
        # 1. 黄金期测试 (预期年化20-35%)
        {
            "name": "limit_up_2018_2021",
            "description": "涨停板策略，止盈8%，止损3%，非熊市参与",
            "start": "2018-01-01",
            "end": "2021-12-31",
        },
        # 2. 衰减期测试 (预期年化-5%~5%)
        {
            "name": "limit_up_2022",
            "description": "涨停板策略，止盈8%，止损3%",
            "start": "2022-01-01",
            "end": "2022-12-31",
        },
        # 3. 低表现期测试 (预期年化-10%~0%)
        {
            "name": "limit_up_2023",
            "description": "涨停板策略，止盈8%，止损3%",
            "start": "2023-01-01",
            "end": "2023-12-31",
        },
        # 4. 近期测试 (预期年化0~8%)
        {
            "name": "limit_up_2024",
            "description": "涨停板策略，止盈8%，止损3%",
            "start": "2024-01-01",
            "end": "2024-12-31",
        },
        # 5. 不同参数测试
        {
            "name": "limit_up_aggressive_2020_2021",
            "description": "涨停板策略，止盈15%，止损5%",
            "start": "2020-01-01",
            "end": "2021-12-31",
        },
        {
            "name": "limit_up_conservative_2020_2021",
            "description": "涨停板策略，止盈5%，止损2%",
            "start": "2020-01-01",
            "end": "2021-12-31",
        },
        # 6. 短期快速测试
        {
            "name": "quick_test_2024q4",
            "description": "涨停板策略，止盈8%，止损3%",
            "start": "2024-10-01",
            "end": "2024-12-31",
        },
    ]

    results = []

    for i, config in enumerate(benchmarks, 1):
        print(f"\n[{i}/{len(benchmarks)}] 运行 {config['name']}...")
        result = run_benchmark(
            name=config["name"],
            description=config["description"],
            start=config["start"],
            end=config["end"],
        )
        if result:
            results.append(result)

        # 短暂休息
        time.sleep(2)

    # 打印汇总
    print("\n" + "=" * 70)
    print("Benchmark 汇总")
    print("=" * 70)
    print()

    print("| 测试名称 | 时间段 | 年化收益 | 最大回撤 | 胜率 | 盈亏比 | 交易次数 |")
    print("|----------|--------|----------|----------|------|--------|----------|")

    for r in results:
        s = r["summary"]
        name = r["name"].replace("limit_up_", "").replace("_", " ")
        period = f"{r['start_date'][:4]}-{r['end_date'][:4]}"
        annual = s.get("annual_return", 0)
        drawdown = s.get("max_drawdown", 0)
        win_rate = s.get("win_rate", 0)
        profit_ratio = s.get("profit_ratio", 0)
        trades = s.get("total_trades", 0)
        print(f"| {name} | {period} | {annual:.1f}% | {drawdown:.1f}% | {win_rate:.1f}% | {profit_ratio:.2f} | {trades} |")

    # 保存汇总
    summary_file = OUTPUT_DIR / "benchmark_summary.json"
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "total_tests": len(results),
            "results": results,
        }, f, ensure_ascii=False, indent=2)

    print(f"\n汇总保存: {summary_file}")


if __name__ == "__main__":
    main()