# -*- coding: utf-8 -*-
"""
夜间数据补全脚本

批量补全股票数据：
1. 行业分类（申万行业、概念板块）
2. 基本面数据（PE、PB、市值、ROE）
3. 股票标签（风格标签、概念标签）

策略：每 3-5 分钟处理一批，避免被限流
"""

import json
import logging
import os
import random
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

import pandas as pd
import numpy as np

# 设置路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.config import config
from src.data_sources import get_fetcher

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)8s | %(message)s',
    handlers=[
        logging.FileHandler('logs/night_update.log'),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

# 数据路径
DATA_DIR = Path("data/CN_A")
STOCK_LIST_FILE = DATA_DIR / "stock_list.csv"
DAILY_DIR = DATA_DIR / "stock_daily"
FUNDAMENTAL_DIR = DATA_DIR / "fundamental"
TAGS_DIR = DATA_DIR / "tags"

# 创建目录
FUNDAMENTAL_DIR.mkdir(exist_ok=True)
TAGS_DIR.mkdir(exist_ok=True)


class NightDataUpdater:
    """夜间数据补全器"""

    def __init__(self):
        self.fetcher = get_fetcher()
        self.stock_list: Optional[pd.DataFrame] = None
        self.total_stocks = 0
        self.processed = 0
        self.failed = 0
        self.start_time = datetime.now()

        # 加载股票列表
        self._load_stock_list()

        # 加载进度
        self.progress_file = DATA_DIR / "update_progress.json"
        self.progress = self._load_progress()

    def _load_stock_list(self) -> None:
        """加载股票列表"""
        if STOCK_LIST_FILE.exists():
            self.stock_list = pd.read_csv(STOCK_LIST_FILE)
            self.total_stocks = len(self.stock_list)
            logger.info(f"[数据补全] 加载股票列表: {self.total_stocks} 只")
        else:
            logger.error("[数据补全] 股票列表不存在")
            self.stock_list = pd.DataFrame()

    def _load_progress(self) -> Dict[str, Any]:
        """加载更新进度"""
        if self.progress_file.exists():
            try:
                return json.loads(self.progress_file.read_text())
            except Exception:
                pass
        return {
            "last_update": "",
            "processed_codes": [],
            "phase": "industry",  # industry / fundamental / tags
        }

    def _save_progress(self) -> None:
        """保存更新进度"""
        self.progress["last_update"] = datetime.now().isoformat()
        self.progress_file.write_text(json.dumps(self.progress, ensure_ascii=False))

    def run(self) -> None:
        """执行夜间数据补全"""
        logger.info("=" * 60)
        logger.info("[数据补全] 开始执行")
        logger.info(f"[数据补全] 总股票数: {self.total_stocks}")
        logger.info(f"[数据补全] 当前阶段: {self.progress.get('phase', 'industry')}")
        logger.info("=" * 60)

        phases = ["industry", "fundamental", "tags"]
        current_phase = self.progress.get("phase", "industry")

        for phase in phases:
            if phases.index(phase) < phases.index(current_phase):
                continue  # 跳过已完成的阶段

            logger.info(f"\n[数据补全] 进入阶段: {phase}")
            self.progress["phase"] = phase

            if phase == "industry":
                self._update_industry_data()
            elif phase == "fundamental":
                self._update_fundamental_data()
            elif phase == "tags":
                self._update_tags_data()

            self._save_progress()

        # 更新完成统计
        elapsed = datetime.now() - self.start_time
        logger.info("\n" + "=" * 60)
        logger.info("[数据补全] 全部完成")
        logger.info(f"[数据补全] 处理股票: {self.processed} 只")
        logger.info(f"[数据补全] 失败股票: {self.failed} 只")
        logger.info(f"[数据补全] 耗时: {elapsed}")
        logger.info("=" * 60)

    def _update_industry_data(self) -> None:
        """更新行业分类数据"""
        logger.info("[行业数据] 开始补全行业分类")

        # 获取行业分类（使用 akshare）
        try:
            import akshare as ak

            # 获取申万行业分类
            logger.info("[行业数据] 获取申万行业分类...")
            random_sleep()

            # 行业分类接口
            industry_map = {}

            # 方法1：通过股票信息接口获取行业
            logger.info("[行业数据] 使用实时行情数据提取行业...")
            df = ak.stock_zh_a_spot_em()

            if df is not None and not df.empty:
                # 从实时行情中提取行业信息（有些接口不提供）
                logger.info(f"[行业数据] 实时行情数据: {len(df)} 条")

                # 更新股票列表的行业字段（如果有的话）
                for _, row in df.iterrows():
                    code = str(row.get('代码', ''))
                    # 暂时没有行业字段，后续通过其他接口补充
                    industry_map[code] = ""

                # 保存到股票列表
                self._update_stock_list_industry(industry_map)

            # 方法2：获取板块成分股，反向推断行业
            logger.info("[行业数据] 通过板块成分股推断行业...")
            self._infer_industry_from_sectors()

        except Exception as e:
            logger.error(f"[行业数据] 获取失败: {e}")

    def _update_stock_list_industry(self, industry_map: Dict[str, str]) -> None:
        """更新股票列表的行业字段"""
        if self.stock_list is None:
            return

        # 更新行业字段
        self.stock_list['industry'] = self.stock_list['code'].map(
            lambda x: industry_map.get(str(x), '')
        )

        # 保存
        self.stock_list.to_csv(STOCK_LIST_FILE, index=False)
        logger.info(f"[行业数据] 更新股票列表行业字段")

    def _infer_industry_from_sectors(self) -> None:
        """通过板块成分股推断行业"""
        try:
            import akshare as ak

            # 获取概念板块
            logger.info("[行业数据] 获取概念板块...")
            random_sleep()

            concept_df = ak.stock_board_concept_name_em()
            if concept_df is not None and not concept_df.empty:
                logger.info(f"[行业数据] 概念板块数量: {len(concept_df)}")

                # 保存板块列表
                sectors_file = DATA_DIR / "sectors.csv"
                concept_df.to_csv(sectors_file, index=False)

            # 获取行业板块
            logger.info("[行业数据] 获取行业板块...")
            random_sleep()

            industry_df = ak.stock_board_industry_name_em()
            if industry_df is not None and not industry_df.empty:
                logger.info(f"[行业数据] 行业板块数量: {len(industry_df)}")

                # 保存行业板块
                industry_sectors_file = DATA_DIR / "industry_sectors.csv"
                industry_df.to_csv(industry_sectors_file, index=False)

                # 为每个行业板块获取成分股
                self._process_industry_sectors(industry_df)

        except Exception as e:
            logger.error(f"[行业数据] 板块数据获取失败: {e}")

    def _process_industry_sectors(self, industry_df: pd.DataFrame) -> None:
        """处理行业板块，获取成分股并更新股票行业字段"""
        industry_map: Dict[str, List[str]] = {}  # 股票代码 -> 所属行业列表

        total_sectors = len(industry_df)
        batch_size = 20  # 每批处理 20 个板块
        batch_count = 0

        for i, (_, row) in enumerate(industry_df.iterrows()):
            sector_name = row.get('板块名称', '')
            if not sector_name:
                continue

            try:
                random_sleep()
                import akshare as ak

                # 获取板块成分股
                stocks_df = ak.stock_board_industry_cons_em(sector_name)
                if stocks_df is not None and not stocks_df.empty:
                    for _, stock in stocks_df.iterrows():
                        code = str(stock.get('代码', ''))
                        if code:
                            if code not in industry_map:
                                industry_map[code] = []
                            industry_map[code].append(sector_name)

                    logger.info(f"[行业数据] {sector_name}: {len(stocks_df)} 只成分股")

                batch_count += 1
                if batch_count >= batch_size:
                    # 每批后休眠 3 分钟
                    logger.info(f"[行业数据] 已处理 {i+1}/{total_sectors} 个板块，休眠 3 分钟...")
                    time.sleep(180)
                    batch_count = 0

            except Exception as e:
                logger.warning(f"[行业数据] {sector_name} 成分股获取失败: {e}")
                continue

        # 更新股票列表
        if self.stock_list is not None:
            self.stock_list['industry'] = self.stock_list['code'].map(
                lambda x: ', '.join(industry_map.get(str(x), [])) if industry_map.get(str(x)) else ''
            )
            self.stock_list.to_csv(STOCK_LIST_FILE, index=False)
            logger.info(f"[行业数据] 更新完成，{len(industry_map)} 只股票有行业信息")

        # 保存行业映射
        industry_map_file = DATA_DIR / "stock_industry_map.json"
        industry_map_file.write_text(json.dumps(industry_map, ensure_ascii=False))

    def _update_fundamental_data(self) -> None:
        """更新基本面数据（PE、PB、市值等）"""
        logger.info("[基本面数据] 开始补全")

        # 从实时行情获取 PE、PB、市值
        try:
            import akshare as ak

            logger.info("[基本面数据] 获取实时行情数据...")
            random_sleep()

            df = ak.stock_zh_a_spot_em()
            if df is None or df.empty:
                logger.error("[基本面数据] 实时行情获取失败")
                return

            logger.info(f"[基本面数据] 实时行情: {len(df)} 条")

            # 提取基本面数据
            fundamental_data = []
            for _, row in df.iterrows():
                code = str(row.get('代码', ''))
                name = str(row.get('名称', ''))

                # 基本面字段
                pe = safe_float(row.get('市盈率-动态'))
                pb = safe_float(row.get('市净率'))
                total_mv = safe_float(row.get('总市值'))
                circ_mv = safe_float(row.get('流通市值'))

                fundamental_data.append({
                    'code': code,
                    'name': name,
                    'pe': pe,
                    'pb': pb,
                    'total_mv': total_mv,
                    'circ_mv': circ_mv,
                    'update_time': datetime.now().strftime('%Y-%m-%d'),
                })

            # 保存
            fund_df = pd.DataFrame(fundamental_data)
            fund_file = FUNDAMENTAL_DIR / "valuation.csv"
            fund_df.to_csv(fund_file, index=False)
            logger.info(f"[基本面数据] 保存估值数据: {len(fund_df)} 只")

            # 更新股票列表
            if self.stock_list is not None:
                # 合并市值数据
                mv_map = {str(r['code']): r['circ_mv'] for r in fundamental_data}
                self.stock_list['circ_mv'] = self.stock_list['code'].map(
                    lambda x: mv_map.get(str(x), 0)
                )
                self.stock_list.to_csv(STOCK_LIST_FILE, index=False)

        except Exception as e:
            logger.error(f"[基本面数据] 获取失败: {e}")

    def _update_tags_data(self) -> None:
        """更新股票标签"""
        logger.info("[标签数据] 开始补全")

        # 加载基本面数据
        valuation_file = FUNDAMENTAL_DIR / "valuation.csv"
        if not valuation_file.exists():
            logger.warning("[标签数据] 估值数据不存在，跳过")
            return

        valuation_df = pd.read_csv(valuation_file)

        # 加载行业数据
        industry_map_file = DATA_DIR / "stock_industry_map.json"
        industry_map = {}
        if industry_map_file.exists():
            industry_map = json.loads(industry_map_file.read_text())

        # 加载概念板块成分股
        concept_map = self._load_concept_stocks()

        # 生成标签
        tags_data = []
        for _, stock in self.stock_list.iterrows():
            code = str(stock.get('code', ''))
            name = str(stock.get('name', ''))

            tags = self._generate_tags(
                code, name,
                valuation_df,
                industry_map.get(code, []),
                concept_map.get(code, []),
            )

            tags_data.append({
                'code': code,
                'name': name,
                'tags': json.dumps(tags, ensure_ascii=False),
                'style_tags': json.dumps(tags.get('style', []), ensure_ascii=False),
                'industry_tags': json.dumps(tags.get('industry', []), ensure_ascii=False),
                'concept_tags': json.dumps(tags.get('concept', []), ensure_ascii=False),
                'metric_tags': json.dumps(tags.get('metrics', []), ensure_ascii=False),
            })

        # 保存
        tags_df = pd.DataFrame(tags_data)
        tags_file = TAGS_DIR / "stock_tags.csv"
        tags_df.to_csv(tags_file, index=False)
        logger.info(f"[标签数据] 保存标签: {len(tags_df)} 只")

    def _load_concept_stocks(self) -> Dict[str, List[str]]:
        """加载概念板块成分股"""
        concept_map: Dict[str, List[str]] = {}

        try:
            import akshare as ak

            # 获取概念板块列表
            logger.info("[标签数据] 获取概念板块...")
            random_sleep()

            concept_df = ak.stock_board_concept_name_em()
            if concept_df is None or concept_df.empty:
                return concept_map

            logger.info(f"[标签数据] 概念板块: {len(concept_df)} 个")

            # 批量获取成分股
            batch_size = 30
            batch_count = 0

            for i, (_, row) in enumerate(concept_df.iterrows()):
                concept_name = row.get('板块名称', '')
                if not concept_name:
                    continue

                try:
                    random_sleep()
                    stocks_df = ak.stock_board_concept_cons_em(concept_name)
                    if stocks_df is not None and not stocks_df.empty:
                        for _, stock in stocks_df.iterrows():
                            code = str(stock.get('代码', ''))
                            if code:
                                if code not in concept_map:
                                    concept_map[code] = []
                                concept_map[code].append(concept_name)

                    batch_count += 1
                    if batch_count >= batch_size:
                        logger.info(f"[标签数据] 已处理 {i+1}/{len(concept_df)} 个概念，休眠 3 分钟...")
                        time.sleep(180)
                        batch_count = 0

                except Exception as e:
                    logger.warning(f"[标签数据] {concept_name} 成分股获取失败: {e}")
                    continue

            # 保存
            concept_map_file = DATA_DIR / "stock_concept_map.json"
            concept_map_file.write_text(json.dumps(concept_map, ensure_ascii=False))
            logger.info(f"[标签数据] {len(concept_map)} 只股票有概念标签")

        except Exception as e:
            logger.error(f"[标签数据] 概念板块获取失败: {e}")

        return concept_map

    def _generate_tags(
        self,
        code: str,
        name: str,
        valuation_df: pd.DataFrame,
        industries: List[str],
        concepts: List[str],
    ) -> Dict[str, List[str]]:
        """为股票生成多种标签"""

        tags: Dict[str, List[str]] = {
            'style': [],      # 风格标签：大盘、小盘、成长、价值
            'industry': [],   # 行业标签
            'concept': [],    # 概念标签
            'metrics': [],    # 指标标签：高ROE、低PE、破净
            'status': [],     # 状态标签：ST、次新股
        }

        # 状态标签
        if 'ST' in name or 'st' in name:
            tags['status'].append('ST')

        # 从估值数据获取指标
        val_row = valuation_df[valuation_df['code'] == code]
        if not val_row.empty:
            row = val_row.iloc[0]

            pe = safe_float(row.get('pe', 0))
            pb = safe_float(row.get('pb', 0))
            circ_mv = safe_float(row.get('circ_mv', 0))

            # 市值风格
            if circ_mv >= 500e9:  # 500亿以上
                tags['style'].append('大盘')
            elif circ_mv >= 100e9:  # 100-500亿
                tags['style'].append('中盘')
            else:
                tags['style'].append('小盘')

            # PE/PB 指标
            if pe > 0 and pe < 15:
                tags['metrics'].append('低PE')
            if pe > 50:
                tags['metrics'].append('高PE')
            if pb > 0 and pb < 1:
                tags['metrics'].append('破净')

        # 行业标签（取前3个）
        tags['industry'] = industries[:3]

        # 概念标签（取前5个）
        tags['concept'] = concepts[:5]

        return tags


def safe_float(val: Any) -> float:
    """安全转换为浮点数"""
    if val is None or val == '' or val == '-':
        return 0.0
    try:
        return float(val)
    except Exception:
        return 0.0


def random_sleep(min_sec: float = 3.0, max_sec: float = 8.0) -> None:
    """随机休眠，防封禁"""
    sleep_time = random.uniform(min_sec, max_sec)
    logger.debug(f"[防封禁] 休眠 {sleep_time:.1f} 秒")
    time.sleep(sleep_time)


def main() -> None:
    """主函数"""
    updater = NightDataUpdater()
    updater.run()


if __name__ == "__main__":
    main()