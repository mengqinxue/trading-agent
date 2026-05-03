"""数据适配器 - 统一对外接口

将 DataFetcherManager 的功能封装为与现有 AkshareDataSource 兼容的接口，
便于在 agents 和 workflows 中替换使用。
"""

from typing import Optional, Dict, Any, List

from .providers.base import DataFetcherManager
from .providers.realtime_types import UnifiedRealtimeQuote, ChipDistribution


class DataAdapter:
    """数据适配器 - 统一对外接口

    功能：
    1. 封装 DataFetcherManager 的多数据源能力
    2. 提供与 AkshareDataSource 兼容的方法签名
    3. 支持新功能：筹码分布、基本面聚合

    使用方式：
        adapter = DataAdapter()
        market = adapter.get_market_overview()
        realtime = adapter.get_stock_realtime("000001")
        chip = adapter.get_chip_distribution("000001")
    """

    _manager: Optional[DataFetcherManager] = None

    @classmethod
    def get_manager(cls) -> DataFetcherManager:
        """获取或创建 DataFetcherManager 单例"""
        if cls._manager is None:
            cls._manager = DataFetcherManager()
        return cls._manager

    @classmethod
    def reset_manager(cls) -> None:
        """重置 manager（用于测试）"""
        cls._manager = None

    # === 市场数据 ===

    def get_market_overview(self) -> Dict[str, Any]:
        """获取市场概览（主要指数行情）

        Returns:
            包含主要指数数据的字典，格式兼容 AkshareDataSource
        """
        manager = self.get_manager()
        indices = manager.get_main_indices(region="cn")

        if not indices:
            return {}

        result = {}
        for idx in indices:
            code = idx.get("code", "")
            result[code] = {
                "name": idx.get("name", ""),
                "code": code,
                "price": idx.get("current", 0),
                "change": idx.get("change_pct", 0)
            }

        # 添加兼容字段名
        if "000001" in result:
            result["sh_composite"] = result["000001"]
        if "399001" in result:
            result["sz_component"] = result["399001"]
        if "399006" in result:
            result["chinext"] = result["399006"]

        return result

    def get_hot_sectors(self, top_n: int = 10) -> List[Dict[str, Any]]:
        """获取热点板块

        Args:
            top_n: 返回前 N 个板块

        Returns:
            板块列表，包含名称、涨幅等
        """
        manager = self.get_manager()
        top, _ = manager.get_sector_rankings(n=top_n)

        if not top:
            return []

        # 转换为兼容格式
        result = []
        for sector in top:
            result.append({
                "name": sector.get("name", ""),
                "change": sector.get("change", 0),
                "up_count": sector.get("up_count", 0),
                "down_count": sector.get("down_count", 0),
                "leading_stock": sector.get("leading_stock", "")
            })

        return result

    def get_market_stats(self) -> Dict[str, Any]:
        """获取市场涨跌统计

        Returns:
            包含 up_count, down_count, limit_up_count 等的字典
        """
        manager = self.get_manager()
        stats = manager.get_market_stats()
        return stats or {}

    # === 股票数据 ===

    def get_stock_info(self, code: str) -> Dict[str, Any]:
        """获取个股基本信息

        Args:
            code: 股票代码（如 000001）

        Returns:
            股票基本信息
        """
        manager = self.get_manager()

        # 获取股票名称
        name = manager.get_stock_name(code)

        # 获取所属板块
        boards = manager.get_belong_boards(code)

        # 获取实时行情中的估值数据
        quote = manager.get_realtime_quote(code)

        result = {
            "code": code,
            "name": name or "",
            "industry": boards[0].get("name", "") if boards else "",
            "boards": boards
        }

        # 添加估值数据
        if quote:
            result["pe_ratio"] = quote.pe_ratio
            result["pb_ratio"] = quote.pb_ratio
            result["market_cap"] = quote.total_mv

        return result

    def get_stock_realtime(self, code: str) -> Dict[str, Any]:
        """获取股票实时行情

        Args:
            code: 股票代码

        Returns:
            实时行情数据，格式兼容 AkshareDataSource
        """
        manager = self.get_manager()
        quote = manager.get_realtime_quote(code)

        if not quote or not quote.has_basic_data():
            return {"code": code, "error": "未找到股票数据"}

        # 转换为兼容格式
        return {
            "code": code,
            "name": quote.name,
            "price": quote.price,
            "change": quote.change_pct,
            "change_amount": quote.change_amount,
            "volume": quote.volume,
            "amount": quote.amount,
            "high": quote.high,
            "low": quote.low,
            "open": quote.open_price,
            "pre_close": quote.pre_close,
            # 新增字段
            "volume_ratio": quote.volume_ratio,
            "turnover_rate": quote.turnover_rate,
            "amplitude": quote.amplitude,
            "pe_ratio": quote.pe_ratio,
            "pb_ratio": quote.pb_ratio,
            "total_mv": quote.total_mv,
            "circ_mv": quote.circ_mv,
            "source": quote.source.value
        }

    def get_stock_kline(self, code: str, period: str = "daily", days: int = 60) -> Dict[str, Any]:
        """获取K线数据

        Args:
            code: 股票代码
            period: 周期（daily/weekly/monthly）
            days: 天数

        Returns:
            K线数据，格式兼容 AkshareDataSource
        """
        manager = self.get_manager()
        df, source = manager.get_daily_data(code, days=days)

        if df is None or df.empty:
            return {"code": code, "error": "未找到数据"}

        # 转换为兼容格式
        kline_list = []
        for _, row in df.iterrows():
            kline_list.append({
                "date": row["date"].strftime("%Y-%m-%d") if hasattr(row["date"], "strftime") else str(row["date"]),
                "open": float(row.get("open", 0)),
                "close": float(row.get("close", 0)),
                "high": float(row.get("high", 0)),
                "low": float(row.get("low", 0)),
                "volume": float(row.get("volume", 0)),
                "amount": float(row.get("amount", 0)),
                "pct_chg": float(row.get("pct_chg", 0)),
                # 新增技术指标
                "ma5": float(row.get("ma5", 0)),
                "ma10": float(row.get("ma10", 0)),
                "ma20": float(row.get("ma20", 0)),
                "volume_ratio": float(row.get("volume_ratio", 1))
            })

        return {
            "code": code,
            "period": period,
            "kline": kline_list,
            "source": source
        }

    def get_stock_financial(self, code: str) -> Dict[str, Any]:
        """获取财务数据

        Args:
            code: 股票代码

        Returns:
            主要财务指标
        """
        manager = self.get_manager()
        context = manager.get_fundamental_context(code, budget_seconds=10)

        result = {"code": code}

        # 提取关键财务指标
        if context:
            earnings = context.get("earnings", {})
            valuation = context.get("valuation", {})

            result["roe"] = earnings.get("roe", 0)
            result["net_profit_margin"] = earnings.get("net_profit_margin", 0)
            result["gross_profit_margin"] = earnings.get("gross_profit_margin", 0)
            result["pe_ratio"] = valuation.get("pe_ttm", 0)
            result["pb_ratio"] = valuation.get("pb", 0)

        return result

    # === 新功能 ===

    def get_chip_distribution(self, code: str) -> Dict[str, Any]:
        """获取筹码分布（新功能）

        Args:
            code: 股票代码

        Returns:
            筹码分布数据
        """
        manager = self.get_manager()
        chip = manager.get_chip_distribution(code)

        if not chip:
            return {"code": code, "error": "未找到筹码数据"}

        return chip.to_dict()

    def get_chip_status(self, code: str, current_price: Optional[float] = None) -> str:
        """获取筹码状态描述（新功能）

        Args:
            code: 股票代码
            current_price: 当前价格（可选，默认从实时行情获取）

        Returns:
            筹码状态描述文本
        """
        manager = self.get_manager()
        chip = manager.get_chip_distribution(code)

        if not chip:
            return "未找到筹码数据"

        # 获取当前价格
        if current_price is None:
            quote = manager.get_realtime_quote(code)
            if quote:
                current_price = quote.price

        if current_price is None or current_price <= 0:
            return "无法获取当前价格"

        return chip.get_chip_status(current_price)

    def get_fundamental_context(self, code: str, budget_seconds: float = 30) -> Dict[str, Any]:
        """获取基本面全景数据（新功能）

        Args:
            code: 股票代码
            budget_seconds: 获取预算时间（秒）

        Returns:
            基本面上下文，包含估值、成长、盈利、机构、资金流等
        """
        manager = self.get_manager()
        return manager.get_fundamental_context(code, budget_seconds=budget_seconds)

    def batch_get_stock_names(self, codes: List[str]) -> Dict[str, str]:
        """批量获取股票名称

        Args:
            codes: 股票代码列表

        Returns:
            {code: name} 字典
        """
        manager = self.get_manager()
        return manager.batch_get_stock_names(codes)


# 全局适配器实例（便于直接导入使用）
_adapter: Optional[DataAdapter] = None


def get_adapter() -> DataAdapter:
    """获取全局 DataAdapter 单例"""
    global _adapter
    if _adapter is None:
        _adapter = DataAdapter()
    return _adapter