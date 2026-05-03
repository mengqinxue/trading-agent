"""TrendRadar MCP 客户端 - 获取热点新闻和板块"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional


class TrendRadarMCPClient:
    """TrendRadar MCP 客户端

    获取热点新闻和板块信息，用于市场分析和个股筛选。
    """

    def __init__(self, data_path: Optional[str] = None):
        """初始化

        Args:
            data_path: TrendRadar 数据目录路径
        """
        self.data_path = Path(data_path or os.environ.get("TRENDARAR_DATA_PATH", ""))

        # 如果没有配置，尝试常见路径
        if not self.data_path.exists():
            common_paths = [
                Path.home() / "Documents" / "workspace" / "TrendRadar" / "data",
                Path.home() / "workspace" / "TrendRadar" / "data",
                Path("data") / "trendradar",
            ]
            for p in common_paths:
                if p.exists():
                    self.data_path = p
                    break

    def get_hot_news(self, date: Optional[str] = None, keywords: Optional[list] = None) -> list:
        """获取热点新闻

        Args:
            date: 日期字符串 (YYYY-MM-DD)，默认今天
            keywords: 过滤关键词列表

        Returns:
            新闻列表
        """
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")

        # 尝试读取 TrendRadar 数据
        news_file = self.data_path / "daily" / f"{date}.json"

        if news_file.exists():
            try:
                news = json.loads(news_file.read_text(encoding="utf-8"))

                # 过滤关键词
                if keywords:
                    news = [
                        n for n in news
                        if any(k in n.get("title", "") or k in n.get("content", "") for k in keywords)
                    ]

                return news
            except Exception:
                pass

        # 如果没有数据文件，返回模拟数据
        return self._get_mock_news(date)

    def get_hot_sectors(self, news: Optional[list] = None, date: Optional[str] = None) -> list:
        """从新闻中提取热点板块

        Args:
            news: 新闻列表，如果不提供则自动获取
            date: 日期

        Returns:
            热点板块列表 [{name, heat_score, leaders, news_count}]
        """
        if not news:
            news = self.get_hot_news(date)

        if not news:
            return self._get_mock_sectors()

        # 分析新闻标题和内容，提取板块关键词
        sector_keywords = {
            "半导体": ["半导体", "芯片", "晶圆", "封测"],
            "新能源": ["新能源", "光伏", "风电", "储能", "锂电池"],
            "医药": ["医药", "生物", "疫苗", "创新药"],
            "AI": ["AI", "人工智能", "大模型", "算力"],
            "金融": ["银行", "保险", "券商", "金融"],
            "消费": ["消费", "零售", "白酒", "食品"],
        }

        sectors = []
        for sector, keywords in sector_keywords.items():
            count = sum(
                1 for n in news
                if any(k in n.get("title", "") or k in n.get("content", "") for k in keywords)
            )

            if count > 0:
                sectors.append({
                    "name": sector,
                    "heat_score": count * 10,  # 简化评分
                    "news_count": count,
                    "leaders": [],  # 需要额外分析
                    "keywords": keywords
                })

        # 按热度排序
        sectors.sort(key=lambda x: x["heat_score"], reverse=True)

        return sectors[:5]  # 返回 Top 5

    def identify_leaders(self, sector: dict, stock_db: Optional[dict] = None) -> list:
        """识别板块龙头

        Args:
            sector: 板块信息
            stock_db: 股票数据库

        Returns:
            龙头股票列表 [{code, name, reason}]
        """
        # 简化实现：返回板块常见龙头
        sector_leaders = {
            "半导体": ["600036", "002371", "603501"],
            "新能源": ["300750", "002594", "601012"],
            "医药": ["300760", "000661", "600276"],
            "AI": ["000977", "002230", "300474"],
            "金融": ["601318", "600036", "601398"],
            "消费": ["000858", "600519", "000568"],
        }

        leaders = []
        sector_name = sector.get("name", "")

        for code in sector_leaders.get(sector_name, [])[:3]:
            leaders.append({
                "code": code,
                "name": self._get_stock_name(code),
                "reason": f"{sector_name}板块龙头"
            })

        return leaders

    def _get_mock_news(self, date: str) -> list:
        """获取模拟新闻数据"""
        return [
            {
                "title": "半导体板块大涨，芯片股集体走强",
                "content": "今日半导体板块表现强劲...",
                "source": "财经新闻",
                "date": date
            },
            {
                "title": "新能源政策利好，光伏产业迎机遇",
                "content": "国家出台新能源支持政策...",
                "source": "行业资讯",
                "date": date
            },
            {
                "title": "AI大模型突破，算力需求激增",
                "content": "AI技术快速发展...",
                "source": "科技新闻",
                "date": date
            }
        ]

    def _get_mock_sectors(self) -> list:
        """获取模拟板块数据"""
        return [
            {"name": "半导体", "heat_score": 80, "news_count": 8, "leaders": []},
            {"name": "新能源", "heat_score": 70, "news_count": 7, "leaders": []},
            {"name": "AI", "heat_score": 60, "news_count": 6, "leaders": []},
            {"name": "医药", "heat_score": 50, "news_count": 5, "leaders": []},
            {"name": "消费", "heat_score": 40, "news_count": 4, "leaders": []},
        ]

    def _get_stock_name(self, code: str) -> str:
        """获取股票名称"""
        # 简化实现
        stock_names = {
            "600036": "招商银行",
            "300750": "宁德时代",
            "000858": "五粮液",
            "600519": "贵州茅台",
            "002371": "北方华创",
            "603501": "韦尔股份",
            "002594": "比亚迪",
            "601012": "隆基绿能",
            "300760": "迈瑞医疗",
            "000977": "浪潮信息",
            "002230": "科大讯飞",
        }
        return stock_names.get(code, code)