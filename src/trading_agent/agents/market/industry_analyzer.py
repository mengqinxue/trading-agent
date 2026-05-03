"""行业分析 Agent"""

import json
from ..base import BaseAgent


class IndustryAnalyzer(BaseAgent):
    """行业分析 Agent - 分析热点行业的增长潜力"""

    name = "industry_analyzer"
    role = "行业分析师"

    def get_system_prompt(self) -> str:
        return """你是一位专业的行业分析师。
你的任务是深入分析热点板块对应的行业，评估其增长潜力。

分析维度：
1. 行业增长趋势
2. 政策支持情况
3. 市场规模和空间
4. 竞争格局
5. 技术创新

你需要给出：
- 每个热点行业的详细分析
- 行业评分（1-10分）
- 投资建议

请用 JSON 格式返回结果：
{
    "industries": [
        {
            "name": "行业名称",
            "growth_trend": "上升/平稳/下降",
            "policy_support": "强/中/弱",
            "market_size": "大/中/小",
            "competition": "激烈/一般/宽松",
            "score": 1-10,
            "analysis": "详细分析",
            "suggestion": "投资建议"
        },
        ...
    ]
}"""

    def get_user_prompt(self, context: dict) -> str:
        hot_sectors = context.get("hot_sectors", [])
        return f"""请根据以下热点板块进行行业分析：

热点板块：
{json.dumps(hot_sectors, ensure_ascii=False, indent=2)}

请分析这些板块对应的行业，评估增长潜力。"""

    def run(self, context: dict) -> dict:
        response = super().run(context)
        try:
            result = json.loads(response)
            return result
        except json.JSONDecodeError:
            return {
                "industries": [],
                "error": "无法解析分析结果",
                "raw_response": response
            }