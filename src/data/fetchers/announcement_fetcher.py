# -*- coding: utf-8 -*-
"""公告数据获取模块 - 获取股票公告信息"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any

import akshare as ak

logger = logging.getLogger(__name__)


class AnnouncementFetcher:
    """公告数据获取器"""

    def get_announcements(
        self,
        code: str,
        days: int = 90
    ) -> List[Dict[str, Any]]:
        """获取股票公告

        Args:
            code: 股票代码
            days: 查询天数

        Returns:
            公告列表
        """
        try:
            # 使用公告接口（尝试多个可能的 API）
            df = None

            # 尝试不同的 Akshare API
            try:
                df = ak.stock_notice_report(symbol=code)
            except AttributeError:
                pass

            if df is None:
                try:
                    df = ak.stock_news_report(symbol=code)
                except AttributeError:
                    pass

            if df is None or df.empty:
                logger.warning(f"[公告] {code} 未获取到公告数据")
                return []

            # 过滤最近 days 天
            cutoff_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

            announcements = []
            for _, row in df.iterrows():
                announce_date = str(row.get("公告日期", row.get("日期", "")))

                # 时间过滤
                if announce_date and len(announce_date) >= 10:
                    if announce_date[:10] < cutoff_date:
                        continue

                announcement = {
                    "code": code,
                    "title": str(row.get("公告标题", row.get("标题", ""))),
                    "type": str(row.get("公告类型", row.get("类型", ""))),
                    "date": announce_date,
                    "url": str(row.get("公告链接", row.get("链接", ""))),
                }
                announcements.append(announcement)

            logger.info(f"[公告] {code} 获取成功: {len(announcements)} 条（最近{days}天）")
            return announcements

        except Exception as e:
            logger.error(f"[公告] {code} 获取失败: {e}")
            return []

    def get_performance_forecast(self, code: str) -> List[Dict[str, Any]]:
        """获取业绩预告

        Args:
            code: 股票代码

        Returns:
            业绩预告列表
        """
        try:
            # 尝试多个 API
            df = None
            try:
                df = ak.stock_forecast_em(symbol=code)
            except AttributeError:
                pass

            if df is None:
                try:
                    df = ak.stock_yjyg_em(symbol=code)
                except AttributeError:
                    pass

            if df is None or df.empty:
                return []

            forecasts = []
            for _, row in df.iterrows():
                forecast = {
                    "code": code,
                    "report_period": str(row.get("报告期", row.get("报告期", ""))),
                    "forecast_type": str(row.get("预告类型", row.get("类型", ""))),
                    "forecast_change": str(row.get("预告净利润变动幅度", row.get("变动幅度", ""))),
                    "forecast_amount": str(row.get("预告净利润", row.get("净利润", ""))),
                    "announcement_date": str(row.get("公告日期", row.get("日期", ""))),
                }
                forecasts.append(forecast)

            return forecasts

        except Exception as e:
            logger.warning(f"[业绩预告] {code} 获取失败: {e}")
            return []

    def get_dividend_info(self, code: str) -> List[Dict[str, Any]]:
        """获取分红配送信息

        Args:
            code: 股票代码

        Returns:
            分红信息列表
        """
        try:
            df = ak.stock_dividend_cninfo(symbol=code)

            if df is None or df.empty:
                return []

            dividends = []
            for _, row in df.iterrows():
                dividend = {
                    "code": code,
                    "report_period": str(row.get("报告期", "")),
                    "dividend_type": str(row.get("分红类型", "")),
                    "dividend_amount": float(row.get("分红金额", 0) or 0),
                    "announcement_date": str(row.get("公告日期", "")),
                }
                dividends.append(dividend)

            return dividends

        except Exception as e:
            logger.warning(f"[分红] {code} 获取失败: {e}")
            return []

    def get_shareholder_changes(self, code: str) -> List[Dict[str, Any]]:
        """获取股东增减持

        Args:
            code: 股票代码

        Returns:
            东增减持列表
        """
        try:
            df = ak.stock_share_change_cninfo(symbol=code)

            if df is None or df.empty:
                return []

            changes = []
            for _, row in df.iterrows():
                change = {
                    "code": code,
                    "shareholder_name": str(row.get("股东名称", "")),
                    "change_type": str(row.get("变动类型", "")),
                    "change_amount": float(row.get("变动数量", 0) or 0),
                    "change_ratio": float(row.get("变动比例", 0) or 0),
                    "change_date": str(row.get("变动日期", "")),
                }
                changes.append(change)

            return changes

        except Exception as e:
            logger.warning(f"[股东增减持] {code} 获取失败: {e}")
            return []

    def get_announcement_summary(self, code: str, days: int = 90) -> Dict[str, Any]:
        """获取公告摘要

        Args:
            code: 股票代码
            days: 查询天数

        Returns:
            公告统计摘要
        """
        announcements = self.get_announcements(code, days)
        forecasts = self.get_performance_forecast(code)

        if not announcements:
            return {"code": code, "count": 0, "summary": "无公告数据"}

        # 统计公告类型分布
        type_counts = {}
        for ann in announcements:
            ann_type = ann.get("type", "其他")
            type_counts[ann_type] = type_counts.get(ann_type, 0) + 1

        return {
            "code": code,
            "count": len(announcements),
            "type_distribution": type_counts,
            "performance_forecasts": forecasts[:3] if forecasts else [],
            "latest": announcements[:5] if announcements else [],
            "summary": f"最近{days}天共{len(announcements)}条公告",
        }