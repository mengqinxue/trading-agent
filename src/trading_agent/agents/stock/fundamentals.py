"""基本面分析 Agent"""

import json
from ..base import BaseAgent


class FundamentalsAnalyzer(BaseAgent):
    """基本面分析 Agent - 分析公司财务和经营状况"""

    name = "fundamentals_analyzer"
    role = "基本面分析师"

    def get_system_prompt(self) -> str:
        return """你是一位专业的基本面分析师。
你的任务是分析股票的基本面，评估公司的财务健康状况和投资价值。

分析维度：
1. 财务指标（ROE、净利润率、毛利率、负债率等）
2. 行业地位
3. 公司治理
4. 成长性
5. 估值水平（PE、PB）

你需要给出：
- 基本面评分（1-10分）
- 各维度详细分析
- 投资建议

请用 JSON 格式返回结果：
{
    "score": 1-10,
    "financial_health": {
        "roe": "数值和评价",
        "net_profit_margin": "数值和评价",
        "debt_ratio": "数值和评价"
    },
    "industry_position": "行业地位分析",
    "growth_potential": "成长性分析",
    "valuation": "估值分析",
    "strengths": ["优势1", "优势2", ...],
    "weaknesses": ["劣势1", "劣势2", ...],
    "suggestion": "投资建议"
}"""

    def get_user_prompt(self, context: dict) -> str:
        stock_code = context.get("stock_code", "")
        stock_info = context.get("stock_info", {})
        financial_data = context.get("financial_data", {})
        return f"""请分析股票 {stock_code} 的基本面：

股票信息：
{json.dumps(stock_info, ensure_ascii=False, indent=2)}

财务数据：
{json.dumps(financial_data, ensure_ascii=False, indent=2)}

请给出基本面分析和评分。"""

    def run(self, context: dict) -> dict:
        response = super().run(context)
        try:
            result = json.loads(response)
            return result
        except json.JSONDecodeError:
            return {
                "score": 5,
                "error": "无法解析分析结果",
                "raw_response": response
            }