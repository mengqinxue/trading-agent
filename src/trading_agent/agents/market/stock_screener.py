"""个股筛选 Agent"""

import json
from ..base import BaseAgent


class StockScreener(BaseAgent):
    """个股筛选 Agent - 从热点行业中筛选潜力个股"""

    name = "stock_screener"
    role = "个股筛选师"

    def get_system_prompt(self) -> str:
        return """你是一位专业的个股筛选师。
你的任务是从热点行业中筛选出最有潜力的个股。

筛选标准：
1. 行业龙头地位
2. 财务指标健康
3. 成交量活跃
4. 技术形态良好
5. 市值适中

你需要给出：
- 推荐个股 Top 10
- 每只股票的推荐理由
- 操作建议

请用 JSON 格式返回结果：
{
    "recommended_stocks": [
        {
            "code": "股票代码",
            "name": "股票名称",
            "industry": "所属行业",
            "reason": "推荐理由",
            "potential": "高/中/低",
            "suggestion": "建议买入价位和仓位"
        },
        ...
    ]
}"""

    def get_user_prompt(self, context: dict) -> str:
        industries = context.get("industries", [])
        stock_data = context.get("stock_data", [])
        return f"""请根据以下行业分析和股票数据筛选潜力个股：

行业分析：
{json.dumps(industries, ensure_ascii=False, indent=2)}

股票数据（部分）：
{json.dumps(stock_data[:20], ensure_ascii=False, indent=2)}

请筛选出最有潜力的个股并给出推荐理由。"""

    def run(self, context: dict) -> dict:
        response = super().run(context)
        try:
            result = json.loads(response)
            return result
        except json.JSONDecodeError:
            return {
                "recommended_stocks": [],
                "error": "无法解析分析结果",
                "raw_response": response
            }