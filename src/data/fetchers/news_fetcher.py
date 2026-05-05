# -*- coding: utf-8 -*-
"""新闻舆情获取模块 - 获取个股相关新闻"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any

import akshare as ak

logger = logging.getLogger(__name__)


class NewsFetcher:
    """新闻舆情获取器"""

    def get_stock_news(
        self,
        code: str,
        days: int = 90
    ) -> List[Dict[str, Any]]:
        """获取个股新闻

        Args:
            code: 股票代码
            days: 查询天数（默认90天）

        Returns:
            新闻列表
        """
        try:
            # 使用东方财富个股新闻接口
            df = ak.stock_news_em(symbol=code)

            if df is None or df.empty:
                logger.warning(f"[新闻] {code} 未获取到新闻数据")
                return []

            # 过滤最近 days 天
            cutoff_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

            news_list = []
            for _, row in df.iterrows():
                publish_time = str(row.get("发布时间", ""))

                # 时间过滤
                if publish_time:
                    # 处理不同时间格式
                    try:
                        if len(publish_time) > 10:
                            date_str = publish_time[:10]
                        else:
                            date_str = publish_time

                        if date_str < cutoff_date:
                            continue
                    except:
                        pass

                news_item = {
                    "code": code,
                    "title": str(row.get("新闻标题", "")),
                    "content": str(row.get("新闻内容", "")),
                    "publish_time": publish_time,
                    "source": str(row.get("来源", "")),
                    "url": str(row.get("新闻链接", "")),
                }
                news_list.append(news_item)

            logger.info(f"[新闻] {code} 获取成功: {len(news_list)} 条（最近{days}天）")
            return news_list

        except Exception as e:
            logger.error(f"[新闻] {code} 获取失败: {e}")
            return []

    def get_market_news(self, top_n: int = 20) -> List[Dict[str, Any]]:
        """获取市场热点新闻

        Args:
            top_n: 返回数量

        Returns:
            市场新闻列表
        """
        try:
            # 使用财经新闻接口
            df = ak.stock_news_em(symbol="财经新闻")

            if df is None or df.empty:
                return []

            news_list = []
            for _, row in df.head(top_n).iterrows():
                news_item = {
                    "title": str(row.get("新闻标题", "")),
                    "content": str(row.get("新闻内容", "")),
                    "publish_time": str(row.get("发布时间", "")),
                    "source": str(row.get("来源", "")),
                }
                news_list.append(news_item)

            return news_list

        except Exception as e:
            logger.error(f"[市场新闻] 获取失败: {e}")
            return []

    def get_news_summary(self, code: str, days: int = 90) -> Dict[str, Any]:
        """获取新闻摘要

        Args:
            code: 股票代码
            days: 查询天数

        Returns:
            新闻统计摘要
        """
        news_list = self.get_stock_news(code, days)

        if not news_list:
            return {"code": code, "count": 0, "summary": "无新闻数据"}

        # 统计新闻来源分布
        source_counts = {}
        for news in news_list:
            source = news.get("source", "未知")
            source_counts[source] = source_counts.get(source, 0) + 1

        # 按时间排序（最新的在前）
        sorted_news = sorted(
            news_list,
            key=lambda x: x.get("publish_time", ""),
            reverse=True
        )

        return {
            "code": code,
            "count": len(news_list),
            "latest": sorted_news[:5] if sorted_news else [],
            "source_distribution": source_counts,
            "summary": f"最近{days}天共{len(news_list)}条新闻",
        }