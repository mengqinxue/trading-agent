#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""股票信息收集测试脚本 - 测试沃格光电（603773）

用法：
    uv run python scripts/collect_stock_info.py 603773
"""

import sys
from pathlib import Path
import logging

# 添加项目根目录到 path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.data.collectors import StockInfoCollector

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main(code: str = "603773"):
    """主函数"""
    logger.info("=" * 60)
    logger.info(f"股票信息收集测试: {code}")
    logger.info("=" * 60)

    # 创建收集器
    collector = StockInfoCollector()

    # 收集所有信息
    logger.info(f"开始收集 {code} 全量信息...")
    data = collector.collect_all(code, days=90)

    # 保存数据
    logger.info(f"保存数据...")
    save_path = collector.save(code, data)

    # 打印摘要
    print("\n" + collector.get_summary(code))
    print(f"\n数据保存路径: {save_path}")

    # 打印详细数据统计
    print("\n=== 数据统计 ===")
    print(f"基本信息: {len(data.get('basic', {}))} 字段")
    print(f"K线数据: {len(data.get('market', {}).get('kline', []))} 条")
    print(f"财务指标: {len(data.get('financial', {}).get('indicators', {}))} 字段")
    print(f"研报数据: {len(data.get('research', {}).get('reports', []))} 条")
    print(f"新闻数据: {data.get('news', {}).get('count', 0)} 条")
    print(f"公告数据: {data.get('announcements', {}).get('count', 0)} 条")
    print(f"板块归属: {len(data.get('sectors', []))} 个")

    logger.info("=" * 60)
    logger.info("收集完成")
    logger.info("=" * 60)


if __name__ == "__main__":
    # 从命令行参数获取股票代码
    code = sys.argv[1] if len(sys.argv) > 1 else "603773"
    main(code)