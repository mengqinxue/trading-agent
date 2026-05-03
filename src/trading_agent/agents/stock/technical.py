"""技术面分析 Agent"""

import json
from ..base import BaseAgent


class TechnicalAnalyzer(BaseAgent):
    """技术面分析 Agent - 分析K线和技术指标"""

    name = "technical_analyzer"
    role = "技术面分析师"

    def get_system_prompt(self) -> str:
        return """你是一位专业的技术面分析师。
你的任务是分析股票的技术面，评估股价走势和交易时机。

分析维度：
1. K线形态（近期走势、支撑位/压力位）
2. 均线系统（MA5、MA10、MA20、MA60）
3. MACD、KDJ等指标
4. 量价关系
5. 趋势判断

你需要给出：
- 技术面评分（1-10分）
- 各维度详细分析
- 买卖信号判断

请用 JSON 格式返回结果：
{
    "score": 1-10,
    "trend": "上升/下降/震荡",
    "kline_pattern": "K线形态分析",
    "support_level": "支撑位",
    "resistance_level": "压力位",
    "macd_signal": "MACD分析",
    "volume_analysis": "量价分析",
    "buy_signal": true/false,
    "sell_signal": true/false,
    "strengths": ["技术优势1", ...],
    "weaknesses": ["技术劣势1", ...],
    "suggestion": "操作建议"
}"""

    def get_user_prompt(self, context: dict) -> str:
        stock_code = context.get("stock_code", "")
        realtime_data = context.get("realtime_data", {})
        kline_data = context.get("kline_data", {})
        return f"""请分析股票 {stock_code} 的技术面：

实时行情：
{json.dumps(realtime_data, ensure_ascii=False, indent=2)}

K线数据（近60天）：
{json.dumps(kline_data.get('kline', [])[-10:], ensure_ascii=False, indent=2)}

请给出技术面分析和买卖信号。"""

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