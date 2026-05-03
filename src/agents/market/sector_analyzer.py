"""板块分析 Agent"""

import json
from ..base import BaseAgent


class SectorAnalyzer(BaseAgent):
    """板块分析 Agent - 识别热点板块"""

    name = "sector_analyzer"
    role = "A股板块分析师"

    def get_system_prompt(self) -> str:
        return """你是一位专业的A股板块分析师。
你的任务是分析当前市场的热点板块，找出最具投资价值的板块。

分析维度：
1. 板块涨幅排名
2. 板块资金流向
3. 板块内个股表现
4. 板块热度持续性

你需要给出：
- 热点板块 Top 5
- 每个板块的分析理由
- 板块投资建议

请用 JSON 格式返回结果：
{
    "hot_sectors": [
        {
            "name": "板块名称",
            "reason": "分析理由",
            "potential": "高/中/低",
            "suggestion": "建议"
        },
        ...
    ]
}"""

    def get_user_prompt(self, context: dict) -> str:
        sector_data = context.get("sector_data", [])
        market_sentiment = context.get("market_sentiment", "")
        return f"""请根据以下数据进行分析：

市场形势：{market_sentiment}

热点板块数据：
{json.dumps(sector_data[:10], ensure_ascii=False, indent=2)}

请分析热点板块并给出投资建议。"""

    def run(self, context: dict) -> dict:
        response = super().run(context)
        try:
            result = json.loads(response)
            return result
        except json.JSONDecodeError:
            return {
                "hot_sectors": [],
                "error": "无法解析分析结果",
                "raw_response": response
            }