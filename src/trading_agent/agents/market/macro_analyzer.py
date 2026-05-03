"""市场宏观分析 Agent"""

import json
from ..base import BaseAgent


class MarketMacroAnalyzer(BaseAgent):
    """市场宏观分析 Agent - 判断牛市/熊市/震荡市"""

    name = "market_macro_analyzer"
    role = "A股市场宏观分析师"

    def get_system_prompt(self) -> str:
        return """你是一位专业的A股市场宏观分析师。
你的任务是分析当前A股市场的整体形势，判断市场处于什么阶段。

分析维度：
1. 主要指数走势（上证指数、深证成指、创业板指）
2. 市场成交量变化
3. 涨跌比例
4. 市场情绪

你需要给出：
- 市场形势判断：牛市/熊市/震荡市
- 判断理由（3-5条）
- 操作建议

请用 JSON 格式返回结果：
{
    "market_sentiment": "牛市/熊市/震荡市",
    "confidence": 0.0-1.0,
    "reasons": ["理由1", "理由2", ...],
    "suggestion": "操作建议"
}"""

    def get_user_prompt(self, context: dict) -> str:
        market_data = context.get("market_data", {})
        return f"""请根据以下市场数据进行分析：

市场概览：
{json.dumps(market_data, ensure_ascii=False, indent=2)}

请判断当前市场形势并给出分析结果。"""

    def run(self, context: dict) -> dict:
        response = super().run(context)
        try:
            # 尝试解析 JSON
            result = json.loads(response)
            return result
        except json.JSONDecodeError:
            # 如果不是 JSON，返回默认结构
            return {
                "market_sentiment": "震荡市",
                "confidence": 0.5,
                "reasons": ["无法解析分析结果"],
                "suggestion": response
            }