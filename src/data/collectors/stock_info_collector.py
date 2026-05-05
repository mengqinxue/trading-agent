# -*- coding: utf-8 -*-
"""股票信息收集器 - 整合所有数据源，收集股票完整信息"""

import json
import logging
import os
import pandas as pd
from datetime import datetime, timedelta, date
from pathlib import Path
from typing import Dict, Any, List, Optional

from src.data.fetchers import (
    MarketFetcher,
    FinancialFetcher,
    NewsFetcher,
    AnnouncementFetcher,
)
from src.data.local_sources import MootdxSource
from src.data.akshare_data import AkshareDataSource
from src.data.fundamental_financial import get_financial_data, get_financial_history
from src.data.fundamental_research import get_research_reports, get_research_summary
from src.data.market_sector import get_stock_belong_sectors

logger = logging.getLogger(__name__)

# 数据存储路径
DATA_ROOT = Path("data/stock_info")


def json_serialize(obj):
    """JSON 序列化辅助函数"""
    if isinstance(obj, (datetime, date)):
        return obj.strftime("%Y-%m-%d %H:%M:%S") if isinstance(obj, datetime) else obj.strftime("%Y-%m-%d")
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


class StockInfoCollector:
    """股票信息收集器"""

    def __init__(self, data_root: Path = DATA_ROOT):
        self.data_root = Path(data_root)
        self.market_fetcher: Optional[MarketFetcher] = None
        self.financial_fetcher = FinancialFetcher()
        self.news_fetcher = NewsFetcher()
        self.announcement_fetcher = AnnouncementFetcher()
        self.akshare_source = AkshareDataSource()

        # 初始化市场数据获取器（需要数据库路径）
        db_path = Path("data/market/daily/stocks.db")
        if db_path.exists():
            self.market_fetcher = MarketFetcher(db_path)

    def collect_all(self, code: str, days: int = 90) -> Dict[str, Any]:
        """收集股票所有信息

        Args:
            code: 股票代码
            days: 查询天数（时效性）

        Returns:
            完整股票信息字典
        """
        logger.info(f"[收集器] 开始收集 {code} 信息...")

        data = {
            "code": code,
            "collect_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "data_range_days": days,
            "basic": self.collect_basic(code),
            "market": self.collect_market(code, days),
            "financial": self.collect_financial(code),
            "research": self.collect_research(code, days),
            "news": self.collect_news(code, days),
            "announcements": self.collect_announcements(code, days),
            "sectors": self.collect_sectors(code),
        }

        logger.info(f"[收集器] {code} 信息收集完成")
        return data

    def collect_basic(self, code: str) -> Dict[str, Any]:
        """收集基本信息"""
        logger.info(f"[基本信息] {code}")

        try:
            info = self.akshare_source.get_stock_info(code)

            # 补充实时行情中的名称
            realtime = self.akshare_source.get_stock_realtime(code)
            if realtime and not info.get("name"):
                info["name"] = realtime.get("name", "")

            return info

        except Exception as e:
            logger.error(f"[基本信息] {code} 失败: {e}")
            return {"code": code, "error": str(e)}

    def collect_market(self, code: str, days: int = 90) -> Dict[str, Any]:
        """收集行情数据"""
        logger.info(f"[行情数据] {code}")

        market_data = {"code": code}

        # 实时行情
        try:
            realtime = self.akshare_source.get_stock_realtime(code)
            market_data["realtime"] = realtime
        except Exception as e:
            logger.warning(f"[实时行情] 失败: {e}")
            market_data["realtime"] = {}

        # K线数据（近 days 天）
        try:
            kline = self.akshare_source.get_stock_kline(code, "daily", days)
            market_data["kline"] = kline.get("kline", [])
        except Exception as e:
            logger.warning(f"[K线数据] 失败: {e}")
            market_data["kline"] = []

        # 从数据库加载历史日线
        if self.market_fetcher:
            try:
                end_date = datetime.now().strftime("%Y-%m-%d")
                start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
                daily_data = self.market_fetcher.fetch_stock_daily(code, start_date, end_date)
                market_data["daily"] = daily_data
            except Exception as e:
                logger.warning(f"[日线数据] 失败: {e}")

        return market_data

    def collect_financial(self, code: str) -> Dict[str, Any]:
        """收集财务数据"""
        logger.info(f"[财务数据] {code}")

        financial_data = {"code": code}

        # Tushare 估值数据（PE/PB/PS等）
        try:
            valuation = self._get_tushare_valuation(code)
            if valuation:
                financial_data["valuation"] = valuation
                logger.info(f"[估值数据] {code} Tushare 获取成功")
        except Exception as e:
            logger.warning(f"[估值数据] 失败: {e}")

        # 财务指标
        try:
            indicators = get_financial_data(code)
            financial_data["indicators"] = indicators
        except Exception as e:
            logger.warning(f"[财务指标] 失败: {e}")

        # 历史财务数据（3年）
        try:
            history = get_financial_history(code, years=3)
            financial_data["history"] = history
        except Exception as e:
            logger.warning(f"[财务历史] 失败: {e}")

        # 详细财报
        try:
            reports = self.financial_fetcher.get_all_financials(code)
            financial_data["reports"] = reports
        except Exception as e:
            logger.warning(f"[详细财报] 失败: {e}")

        return financial_data

    def _get_tushare_valuation(self, code: str) -> Dict[str, Any]:
        """获取 Tushare 估值数据

        Args:
            code: 股票代码

        Returns:
            估值数据字典
        """
        try:
            import tushare as ts

            token = os.getenv('TUSHARE_TOKEN')
            if not token:
                logger.warning("[Tushare] 未配置 TUSHARE_TOKEN")
                return {}

            ts.set_token(token)
            pro = ts.pro_api()

            # 判断市场代码
            ts_code = f"{code}.SH" if code.startswith('6') else f"{code}.SZ"

            # 获取最新估值数据
            df = pro.daily_basic(ts_code=ts_code, fields='trade_date,pe,pe_ttm,pb,ps,ps_ttm,dv_ratio,dv_ttm,total_mv,circ_mv,turnover_rate,turnover_rate_f,volume_ratio')

            if df is None or df.empty:
                logger.warning(f"[Tushare估值] {code} 无数据")
                return {}

            # 取最新一条（第一行）
            row = df.iloc[0]

            # 安全转换函数
            def safe_val(key, default=0.0):
                val = row.get(key)
                if pd.isna(val) or val is None:
                    return default
                return float(val)

            valuation = {
                "code": code,
                "date": safe_val('trade_date', ''),
                "pe": safe_val('pe'),
                "pe_ttm": safe_val('pe_ttm'),
                "pb": safe_val('pb'),
                "ps": safe_val('ps'),
                "ps_ttm": safe_val('ps_ttm'),
                "dv_ratio": safe_val('dv_ratio'),  # 股息率
                "dv_ttm": safe_val('dv_ttm'),
                "total_mv": safe_val('total_mv') * 10000,  # 万元转元
                "circ_mv": safe_val('circ_mv') * 10000,
                "turnover_rate": safe_val('turnover_rate'),
                "volume_ratio": safe_val('volume_ratio'),
            }

            logger.info(f"[Tushare估值] {code} 获取成功")
            return valuation

        except Exception as e:
            logger.error(f"[Tushare估值] {code} 获取失败: {e}")
            return {}

    def collect_research(self, code: str, days: int = 90) -> Dict[str, Any]:
        """收集研报数据"""
        logger.info(f"[研报数据] {code}")

        research_data = {"code": code}

        # 研报列表
        try:
            reports = get_research_reports(code, days)
            research_data["reports"] = [
                {
                    "date": r.date,
                    "rating": r.rating,
                    "target_price": r.target_price,
                    "institution": r.institution,
                    "analyst": r.analyst,
                }
                for r in reports
            ]
        except Exception as e:
            logger.warning(f"[研报列表] 失败: {e}")
            research_data["reports"] = []

        # 研报摘要
        try:
            summary = get_research_summary(code, days)
            research_data["summary"] = summary
        except Exception as e:
            logger.warning(f"[研报摘要] 失败: {e}")

        return research_data

    def collect_news(self, code: str, days: int = 90) -> Dict[str, Any]:
        """收集新闻舆情"""
        logger.info(f"[新闻舆情] {code}")

        try:
            summary = self.news_fetcher.get_news_summary(code, days)
            return summary
        except Exception as e:
            logger.error(f"[新闻舆情] 失败: {e}")
            return {"code": code, "count": 0, "error": str(e)}

    def collect_announcements(self, code: str, days: int = 90) -> Dict[str, Any]:
        """收集公告数据"""
        logger.info(f"[公告数据] {code}")

        try:
            summary = self.announcement_fetcher.get_announcement_summary(code, days)
            return summary
        except Exception as e:
            logger.error(f"[公告数据] 失败: {e}")
            return {"code": code, "count": 0, "error": str(e)}

    def collect_sectors(self, code: str) -> List[Dict[str, Any]]:
        """收集板块归属"""
        logger.info(f"[板块归属] {code}")

        try:
            sectors = get_stock_belong_sectors(code)
            return sectors
        except Exception as e:
            logger.warning(f"[板块归属] 失败: {e}")
            return []

    def save(self, code: str, data: Dict[str, Any]) -> Path:
        """保存股票信息

        Args:
            code: 股票代码
            data: 股票数据

        Returns:
            保存路径
        """
        # 创建目录
        stock_dir = self.data_root / code
        stock_dir.mkdir(parents=True, exist_ok=True)

        # 保存完整数据
        data_file = stock_dir / "full_info.json"
        with open(data_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=json_serialize)

        # 分模块保存
        modules = ["basic", "market", "financial", "research", "news", "announcements"]
        for module in modules:
            if module in data:
                module_file = stock_dir / f"{module}.json"
                with open(module_file, "w", encoding="utf-8") as f:
                    json.dump(data[module], f, ensure_ascii=False, indent=2, default=json_serialize)

        # 保存元数据
        meta = {
            "code": code,
            "collect_time": data.get("collect_time"),
            "data_range_days": data.get("data_range_days"),
        }
        meta_file = stock_dir / "meta.json"
        with open(meta_file, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

        logger.info(f"[保存] {code} 数据已保存到 {stock_dir}")
        return stock_dir

    def load(self, code: str) -> Optional[Dict[str, Any]]:
        """加载已存储的股票信息

        Args:
            code: 股票代码

        Returns:
            股票数据（如果存在）
        """
        stock_dir = self.data_root / code
        data_file = stock_dir / "full_info.json"

        if not data_file.exists():
            logger.warning(f"[加载] {code} 数据不存在")
            return None

        with open(data_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        logger.info(f"[加载] {code} 数据加载成功")
        return data

    def update_daily(self, codes: List[str]) -> Dict[str, Path]:
        """每日更新（持仓股票）

        Args:
            codes: 股票代码列表

        Returns:
            保存路径字典
        """
        results = {}

        for code in codes:
            try:
                data = self.collect_all(code, days=90)
                path = self.save(code, data)
                results[code] = path
            except Exception as e:
                logger.error(f"[每日更新] {code} 失败: {e}")
                results[code] = None

        return results

    def get_summary(self, code: str) -> str:
        """获取股票信息摘要

        Args:
            code: 股票代码

        Returns:
            摘要文本
        """
        data = self.load(code)

        if not data:
            return f"股票 {code} 无数据"

        lines = []
        lines.append(f"=== {code} 信息摘要 ===")

        # 基本信息
        basic = data.get("basic", {})
        if basic:
            lines.append(f"名称: {basic.get('name', '未知')}")
            lines.append(f"行业: {basic.get('industry', '未知')}")
            lines.append(f"市值: {basic.get('market_cap', '未知')}")

        # 实时行情
        market = data.get("market", {})
        realtime = market.get("realtime", {})
        if realtime:
            lines.append(f"最新价: {realtime.get('price', 0):.2f}")
            lines.append(f"涨跌幅: {realtime.get('change', 0):.2f}%")

        # 财务指标
        financial = data.get("financial", {})
        indicators = financial.get("indicators", {})
        if indicators:
            lines.append(f"ROE: {indicators.get('roe', 0):.2f}%")
            lines.append(f"毛利率: {indicators.get('gross_profit_margin', 0):.2f}%")

        # 新闻统计
        news = data.get("news", {})
        lines.append(f"新闻数量: {news.get('count', 0)} 条")

        # 公告统计
        announcements = data.get("announcements", {})
        lines.append(f"公告数量: {announcements.get('count', 0)} 条")

        lines.append(f"更新时间: {data.get('collect_time', '未知')}")

        return "\n".join(lines)


# 需导入 timedelta（已在顶部导入）