# -*- coding: utf-8 -*-
"""
AI 查询服务

用 LLM 理解自然语言查询，从本地数据库检索数据。
"""

import json
import logging
import os
from pathlib import Path
from typing import Dict, Any, List, Optional

import pandas as pd
from openai import OpenAI

from src.core.config import config

logger = logging.getLogger(__name__)

# 本地数据路径
DATA_DIR = Path("data/CN_A")
STOCK_LIST_FILE = DATA_DIR / "stock_list.csv"
DAILY_DIR = DATA_DIR / "stock_daily"


class AIQueryService:
    """AI 查询服务 - 用 LLM 理解自然语言并查询本地数据"""

    def __init__(self):
        self.llm_config = config.llm
        self.client = OpenAI(
            api_key=self.llm_config.api_key,
            base_url=self.llm_config.base_url,
        )
        self.model = self.llm_config.model

        # 加载股票列表
        self._stock_list: Optional[pd.DataFrame] = None
        self._load_stock_list()

    def _load_stock_list(self) -> None:
        """加载股票列表"""
        if STOCK_LIST_FILE.exists():
            try:
                self._stock_list = pd.read_csv(STOCK_LIST_FILE)
                logger.info(f"[AI查询] 加载股票列表: {len(self._stock_list)} 只")
            except Exception as e:
                logger.warning(f"[AI查询] 加载股票列表失败: {e}")

    def _get_stock_daily(self, code: str, days: int = 30) -> Optional[pd.DataFrame]:
        """读取股票日线数据"""
        # 尝试多种文件名格式
        patterns = [
            f"{code}_*_Daily_To2026.csv",  # 000001_平安银行_Daily_To2026.csv
            f"{code}.csv",                 # 简单格式
        ]

        for pattern in patterns:
            files = list(DAILY_DIR.glob(pattern))
            if files:
                try:
                    df = pd.read_csv(files[0])
                    if 'date' in df.columns:
                        df = df.sort_values('date').tail(days)
                    return df
                except Exception as e:
                    logger.warning(f"[AI查询] 读取 {files[0]} 失败: {e}")

        return None

    def query(self, user_query: str) -> Dict[str, Any]:
        """
        处理自然语言查询

        Args:
            user_query: 用户自然语言问题

        Returns:
            查询结果
        """
        try:
            # 1. AI 理解用户意图
            intent = self._understand_intent(user_query)

            # 2. 执行查询
            result = self._execute_query(intent)

            # 3. AI 生成回答
            response = self._generate_response(user_query, result)

            return {
                "success": True,
                "query": user_query,
                "intent": intent,
                "data": result,
                "response": response,
            }

        except Exception as e:
            logger.error(f"[AI查询] 处理失败: {e}")
            return {
                "success": False,
                "query": user_query,
                "error": str(e),
            }

    def _understand_intent(self, user_query: str) -> Dict[str, Any]:
        """用 AI 理解用户查询意图"""

        # 构建上下文：可用数据字段
        available_fields = """
可用数据字段：
- 涨跌幅 (change_pct, pct_chg): 最近一天/一周/一个月的涨跌幅
- 换手率 (turnover): 最近一天的换手率
- 市值: 需要从最新日线计算
- 行业 (industry): 股票所属行业
- 名称 (name): 股票名称
- 代码 (code): 股票代码
- 日期 (date): 交易日期

数据范围：
- 全部 A 股股票（约 5700 只）
- 日线数据（含 OHLCV、涨跌幅、换手率等）
"""

        prompt = f"""你是一个股票数据查询助手。用户会用自然语言问你股票相关问题。
你需要理解用户意图，并返回结构化的查询参数。

{available_fields}

用户问题：{user_query}

请严格按以下 JSON 格式返回（不要添加其他字段）：
{{"query_type": "涨幅筛选", "conditions": [{{"field": "change_pct", "op": ">=", "value": 5, "time_range": "最近一天"}}], "sort_by": "change_pct", "sort_order": "desc", "limit": 20, "explanation": "用户想查询最近涨幅超过5%的股票}}

只返回 JSON，不要包裹在 markdown 中。"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,  # 低温度，更确定性
                max_tokens=500,
            )

            content = response.choices[0].message.content.strip()

            # 解析 JSON
            # 提取 JSON 部分（可能被 markdown 包裹）
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            intent = json.loads(content)
            logger.info(f"[AI查询] 理解意图: {intent.get('explanation', '')}")
            return intent

        except json.JSONDecodeError as e:
            logger.warning(f"[AI查询] JSON 解析失败: {e}, 原文: {content}")
            return {
                "query_type": "综合筛选",
                "conditions": [],
                "limit": 20,
                "explanation": "无法理解意图，返回默认结果",
            }
        except Exception as e:
            logger.error(f"[AI查询] AI 理解失败: {e}")
            raise

    def _execute_query(self, intent: Dict[str, Any]) -> Dict[str, Any]:
        """根据意图执行查询"""

        if self._stock_list is None or self._stock_list.empty:
            return {"stocks": [], "count": 0, "message": "股票列表未加载"}

        # 获取候选股票
        stocks_df = self._stock_list.copy()
        result_stocks: List[Dict[str, Any]] = []

        # 处理条件
        conditions = intent.get("conditions", [])
        limit = intent.get("limit", 20)

        # 先筛选行业条件（静态数据）
        for cond in conditions:
            if cond.get("field") == "industry":
                industry = cond.get("value", "")
                op = cond.get("op", "==")

                if op in ["==", "contains"]:
                    stocks_df = stocks_df[
                        stocks_df["industry"].fillna("").str.contains(industry, na=False)
                    ]

        # 获取每只股票的最新数据，应用动态条件
        for _, stock in stocks_df.iterrows():
            code = stock["code"]

            # 读取日线数据
            daily_df = self._get_stock_daily(code, days=30)
            if daily_df is None or daily_df.empty:
                continue

            # 最新一天数据
            latest = daily_df.iloc[-1]

            # 构建股票信息
            stock_info = {
                "code": code,
                "name": stock.get("name", ""),
                "industry": stock.get("industry", ""),
                "change_pct": latest.get("change_pct", 0) or latest.get("pct_chg", 0),
                "turnover": latest.get("turnover", 0),
                "close": latest.get("close", 0),
            }

            # 计算最近 N 天涨跌幅
            if len(daily_df) >= 5:
                stock_info["change_5d"] = (
                    (daily_df.iloc[-1]["close"] - daily_df.iloc[-5]["close"])
                    / daily_df.iloc[-5]["close"] * 100
                    if daily_df.iloc[-5]["close"] > 0
                    else 0
                )
            if len(daily_df) >= 20:
                stock_info["change_20d"] = (
                    (daily_df.iloc[-1]["close"] - daily_df.iloc[-20]["close"])
                    / daily_df.iloc[-20]["close"] * 100
                    if daily_df.iloc[-20]["close"] > 0
                    else 0
                )

            # 应用动态条件
            match = True
            for cond in conditions:
                field = cond.get("field")
                op = cond.get("op")
                value = cond.get("value")
                time_range = cond.get("time_range", "最近一天")

                # 时间范围映射
                actual_field = field
                if field == "change_pct":
                    if time_range == "最近一周" or "周" in time_range:
                        actual_field = "change_5d"
                    elif time_range == "最近一个月" or "月" in time_range:
                        actual_field = "change_20d"

                stock_value = stock_info.get(actual_field)
                if stock_value is None:
                    match = False
                    break

                # 比较操作
                if op == ">=" and stock_value < value:
                    match = False
                elif op == "<=" and stock_value > value:
                    match = False
                elif op == ">" and stock_value <= value:
                    match = False
                elif op == "<" and stock_value >= value:
                    match = False
                elif op == "==" and stock_value != value:
                    match = False

            if match:
                result_stocks.append(stock_info)

        # 排序
        sort_by = intent.get("sort_by", "change_pct")
        sort_order = intent.get("sort_order", "desc")

        if sort_by in ["change_pct", "change_5d", "change_20d", "turnover", "close"]:
            result_stocks.sort(
                key=lambda x: x.get(sort_by, 0) or 0,
                reverse=(sort_order == "desc"),
            )

        # 限制数量
        result_stocks = result_stocks[:limit]

        return {
            "stocks": result_stocks,
            "count": len(result_stocks),
            "total_matched": len(result_stocks),
        }

    def _generate_response(
        self, user_query: str, result: Dict[str, Any]
    ) -> str:
        """用 AI 生成自然语言回答"""

        stocks = result.get("stocks", [])
        count = result.get("count", 0)

        if not stocks:
            return "没有找到符合条件的股票。"

        # 构建数据摘要
        stock_summary = "\n".join(
            [
                f"- {s['code']} {s['name']}: 涨幅 {s.get('change_pct', 0):.2f}%, 行业 {s.get('industry', '未知')}"
                for s in stocks[:10]
            ]
        )

        prompt = f"""用户问题：{user_query}

查询结果：找到 {count} 只符合条件的股票
前 10 只：
{stock_summary}

请用简洁自然的语言回答用户，总结查询结果。不要超过 100 字。"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=150,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.warning(f"[AI查询] 生成回答失败: {e}")
            return f"找到 {count} 只符合条件的股票，请查看列表。"


# 全局实例
_service: Optional[AIQueryService] = None


def get_service() -> AIQueryService:
    """获取 AI 查询服务单例"""
    global _service
    if _service is None:
        _service = AIQueryService()
    return _service