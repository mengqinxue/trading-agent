"""Akshare 数据源 - A股数据获取"""

import akshare as ak
from typing import Optional


class AkshareDataSource:
    """A股数据源"""

    def get_market_overview(self) -> dict:
        """获取市场概览

        Returns:
            包含主要指数数据的字典
        """
        try:
            # 使用 stock_zh_index_spot_em 获取实时指数数据
            index_data = ak.stock_zh_index_spot_em()

            # 查找主要指数
            sh_row = index_data[index_data["代码"] == "000001"]
            sz_row = index_data[index_data["代码"] == "399001"]
            cyb_row = index_data[index_data["代码"] == "399006"]

            result = {}

            if not sh_row.empty:
                row = sh_row.iloc[0]
                result["sh_composite"] = {
                    "name": "上证指数",
                    "code": "000001",
                    "price": float(row["最新价"]),
                    "change": float(row["涨跌幅"])
                }

            if not sz_row.empty:
                row = sz_row.iloc[0]
                result["sz_component"] = {
                    "name": "深证成指",
                    "code": "399001",
                    "price": float(row["最新价"]),
                    "change": float(row["涨跌幅"])
                }

            if not cyb_row.empty:
                row = cyb_row.iloc[0]
                result["chinext"] = {
                    "name": "创业板指",
                    "code": "399006",
                    "price": float(row["最新价"]),
                    "change": float(row["涨跌幅"])
                }

            return result
        except Exception as e:
            print(f"获取市场概览失败: {e}")
            return {}

    def get_hot_sectors(self, top_n: int = 10) -> list[dict]:
        """获取热点板块

        Args:
            top_n: 返回前 N 个板块

        Returns:
            板块列表，包含名称、涨幅等
        """
        try:
            sector_data = ak.stock_board_concept_name_em()
            sector_data = sector_data.sort_values(by="涨跌幅", ascending=False)

            hot_sectors = []
            for i, row in sector_data.head(top_n).iterrows():
                hot_sectors.append({
                    "name": row["板块名称"],
                    "change": float(row["涨跌幅"]),
                    "up_count": int(row["上涨家数"]),
                    "down_count": int(row["下跌家数"]),
                    "leading_stock": row.get("领涨股票", "")
                })

            return hot_sectors
        except Exception as e:
            print(f"获取热点板块失败: {e}")
            return []

    def get_stock_info(self, code: str) -> dict:
        """获取个股基本信息

        Args:
            code: 股票代码（如 000001）

        Returns:
            股票基本信息
        """
        try:
            stock_info = ak.stock_individual_info_em(symbol=code)

            info_dict = {}
            for _, row in stock_info.iterrows():
                info_dict[row["item"]] = row["value"]

            return {
                "code": code,
                "name": info_dict.get("股票简称", ""),
                "industry": info_dict.get("行业", ""),
                "market_cap": info_dict.get("总市值", ""),
                "pe_ratio": info_dict.get("市盈率", ""),
                "pb_ratio": info_dict.get("市净率", "")
            }
        except Exception as e:
            print(f"获取股票信息失败 {code}: {e}")
            return {"code": code, "error": str(e)}

    def get_stock_realtime(self, code: str) -> dict:
        """获取股票实时行情

        Args:
            code: 股票代码

        Returns:
            实时行情数据
        """
        try:
            realtime_data = ak.stock_zh_a_spot_em()
            stock_data = realtime_data[realtime_data["代码"] == code]

            if stock_data.empty:
                return {"code": code, "error": "未找到股票数据"}

            row = stock_data.iloc[0]
            return {
                "code": code,
                "name": row["名称"],
                "price": float(row["最新价"]),
                "change": float(row["涨跌幅"]),
                "volume": float(row["成交量"]),
                "amount": float(row["成交额"]),
                "high": float(row["最高"]),
                "low": float(row["最低"]),
                "open": float(row["今开"]),
                "pre_close": float(row["昨收"])
            }
        except Exception as e:
            print(f"获取实时行情失败 {code}: {e}")
            return {"code": code, "error": str(e)}

    def get_stock_kline(self, code: str, period: str = "daily", days: int = 60) -> dict:
        """获取K线数据

        Args:
            code: 股票代码
            period: 周期（daily/weekly/monthly）
            days: 天数

        Returns:
            K线数据
        """
        try:
            kline_data = ak.stock_zh_a_hist(
                symbol=code,
                period=period,
                adjust="qfq"
            )

            recent_data = kline_data.tail(days)

            kline_list = []
            for _, row in recent_data.iterrows():
                kline_list.append({
                    "date": row["日期"],
                    "open": float(row["开盘"]),
                    "close": float(row["收盘"]),
                    "high": float(row["最高"]),
                    "low": float(row["最低"]),
                    "volume": float(row["成交量"]),
                    "amount": float(row["成交额"])
                })

            return {
                "code": code,
                "period": period,
                "kline": kline_list
            }
        except Exception as e:
            print(f"获取K线数据失败 {code}: {e}")
            return {"code": code, "error": str(e)}

    def get_stock_financial(self, code: str) -> dict:
        """获取财务数据

        Args:
            code: 股票代码

        Returns:
            主要财务指标
        """
        try:
            financial_data = ak.stock_financial_analysis_indicator(symbol=code)

            latest = financial_data.iloc[0]

            return {
                "code": code,
                "roe": float(latest.get("净资产收益率", 0)),
                "net_profit_margin": float(latest.get("销售净利率", 0)),
                "gross_profit_margin": float(latest.get("销售毛利率", 0)),
                "debt_ratio": float(latest.get("资产负债率", 0)),
                "current_ratio": float(latest.get("流动比率", 0))
            }
        except Exception as e:
            print(f"获取财务数据失败 {code}: {e}")
            return {"code": code, "error": str(e)}