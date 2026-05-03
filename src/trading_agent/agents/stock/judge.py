"""决策 Agent - 综合辩论结果做出最终判断，含归因分析和反事实推断"""

import json
from typing import Optional
from pathlib import Path

from ..base import BaseAgent


class Judge(BaseAgent):
    """决策 Agent - 综合辩论结果做出最终判断

    包含:
    - 归因分析 (Causal Chain): 解释买入/卖出的因果链
    - 反事实推断 (Counterfactual): 分析假设下跌场景的影响
    """

    name = "judge"
    role = "投资决策师"

    def get_system_prompt(self) -> str:
        return """你是投资决策师，你的任务是综合正反方辩论结果，做出最终投资决策。

你必须：
1. 客观评估正方和反方的论点
2. 权衡买入和卖出理由
3. 考虑基本面和技术面评分
4. 考虑当前持仓情况
5. 做出明确的决策

**归因分析**:
生成因果链，解释决策的原因：
A(原始信号) → B(中间传导) → C(决策依据) → D(最终决策)

例如:
A(热点板块炒作) → B(龙头股关注度提升) → C(技术面突破信号) → D(基本面支撑) → E(买入建议)

**反事实推断**:
分析假设下跌场景的影响:
- 下跌5%: 短期波动，观望
- 下跌10%: 触发止损线，减仓
- 下跌20%: 严重亏损，清仓

决策选项：
- buy：买入
- sell：卖出
- hold：持有/观望

请用 JSON 格式返回：
{
    "decision": "buy/sell/hold",
    "confidence": 0.0-1.0,
    "reason": "决策理由",
    "key_factors": ["关键因素1", "关键因素2"],
    "bull_score": 1-10,
    "bear_score": 1-10,
    "causal_chain": [
        {"step": "A", "description": "...", "evidence": "..."},
        {"step": "B", "description": "...", "evidence": "..."},
        ...
    ],
    "counterfactual": {
        "scenarios": [
            {"scenario": "下跌5%", "impact": "...", "suggestion": "..."},
            {"scenario": "下跌10%", "impact": "...", "suggestion": "..."},
            {"scenario": "下跌20%", "impact": "...", "suggestion": "..."}
        ],
        "worst_case": "...",
        "exit_strategy": {"stop_loss": ..., "take_profit": ...}
    },
    "should_enter": true/false,
    "risk_level": "high/medium/low"
}"""

    def get_user_prompt(self, context: dict) -> str:
        stock_code = context.get("stock_code", "")
        stock_name = context.get("stock_name", stock_code)
        fundamentals = context.get("fundamentals", {})
        technical = context.get("technical", {})
        analysis_summary = context.get("analysis_summary", {})
        bull_arguments = context.get("bull_arguments", [])
        bear_arguments = context.get("bear_arguments", [])
        debate_rounds = context.get("debate_rounds", 0)
        current_position = context.get("current_position", 0)

        return f"""股票：{stock_name} ({stock_code})
当前持仓：{current_position} 元

基本面评分：{fundamentals.get('score', 'N/A')}
基本面优势：{json.dumps(fundamentals.get('strengths', []), ensure_ascii=False)}
基本面劣势：{json.dumps(fundamentals.get('weaknesses', []), ensure_ascii=False)}

技术面评分：{technical.get('score', 'N/A')}
技术面趋势：{technical.get('trend', 'N/A')}
技术面信号：{json.dumps(technical.get('signals', []), ensure_ascii=False)}

综合评分：{analysis_summary.get('combined_score', 'N/A')}
买入论据：{json.dumps(analysis_summary.get('buy_arguments', []), ensure_ascii=False)}
卖出论据：{json.dumps(analysis_summary.get('sell_arguments', []), ensure_ascii=False)}

正方（买方）论点：
{json.dumps(bull_arguments, ensure_ascii=False, indent=2)}

反方（卖方）论点：
{json.dumps(bear_arguments, ensure_ascii=False, indent=2)}

辩论轮数：{debate_rounds}

请综合以上信息，做出最终投资决策，并提供归因分析和反事实推断。"""

    def run(self, context: dict) -> dict:
        """执行决策分析"""
        response = super().run(context)

        try:
            result = json.loads(response)

            # 确保包含归因链和反事实
            if "causal_chain" not in result:
                result["causal_chain"] = self._build_causal_chain(context)

            if "counterfactual" not in result:
                result["counterfactual"] = self._build_counterfactual(context)

            return result

        except json.JSONDecodeError:
            return {
                "decision": "hold",
                "confidence": 0.5,
                "reason": "无法解析决策结果",
                "bull_score": 5,
                "bear_score": 5,
                "causal_chain": self._build_causal_chain(context),
                "counterfactual": self._build_counterfactual(context),
                "should_enter": False,
                "risk_level": "medium",
                "raw_response": response
            }

    def _build_causal_chain(self, context: dict) -> list:
        """构建归因链"""
        chain = []
        fundamentals = context.get("fundamentals", {})
        technical = context.get("technical", {})
        analysis_summary = context.get("analysis_summary", {})

        # A: 基本面信号
        if fundamentals.get("score", 0) > 60:
            chain.append({
                "step": "A",
                "description": f"基本面评分 {fundamentals.get('score', 'N/A')}",
                "evidence": fundamentals.get("strengths", []),
                "source": "akshare财务"
            })

        # B: 技术面信号
        tech_signals = technical.get("signals", [])
        if tech_signals:
            chain.append({
                "step": "B",
                "description": f"技术面信号：{tech_signals[:3]}",
                "evidence": technical.get("trend", "N/A"),
                "source": "akshare K线"
            })

        # C: 辩论结果
        bull_args = context.get("bull_arguments", [])
        bear_args = context.get("bear_arguments", [])
        if bull_args or bear_args:
            chain.append({
                "step": "C",
                "description": f"辩论结果：买方 {len(bull_args)} 论据，卖方 {len(bear_args)} 论据",
                "evidence": f"辩论 {context.get('debate_rounds', 0)} 轮",
                "source": "辩论引擎"
            })

        # D: 综合评分
        combined_score = analysis_summary.get("combined_score", 50)
        chain.append({
            "step": "D",
            "description": f"综合评分 {combined_score:.1f}",
            "evidence": f"基本面权重 60%，技术面权重 40%",
            "source": "汇总节点"
        })

        # E: 最终决策
        decision = "hold"
        if combined_score >= 70:
            decision = "buy"
        elif combined_score < 50:
            decision = "sell"

        chain.append({
            "step": "E",
            "description": f"决策：{decision}",
            "evidence": f"置信度 {analysis_summary.get('confidence', 0.5):.0%}",
            "source": "决策引擎"
        })

        return chain

    def _build_counterfactual(self, context: dict) -> dict:
        """构建反事实推断"""
        # 获取当前价格（如果有）
        technical = context.get("technical", {})
        current_price = technical.get("current_price", 0)

        # 如果没有价格，使用默认值
        if not current_price:
            current_price = 100  # 假设价格

        position = context.get("current_position", 0)

        scenarios = [
            {
                "scenario": "下跌5%",
                "price": current_price * 0.95,
                "impact": f"持仓市值减少 {position * 0.05:.0f} 元" if position else "短期波动",
                "expectation": "可能回调，观望等待企稳",
                "suggestion": "继续持有，关注支撑位"
            },
            {
                "scenario": "下跌10%",
                "price": current_price * 0.90,
                "impact": "触发止损线",
                "expectation": "技术面可能破位",
                "suggestion": "减仓50%，保留观察仓位"
            },
            {
                "scenario": "下跌20%",
                "price": current_price * 0.80,
                "impact": "严重亏损，基本面可能有问题",
                "expectation": "需要重新评估",
                "suggestion": "清仓止损，等待新信号"
            }
        ]

        return {
            "scenarios": scenarios,
            "worst_case": scenarios[-1]["scenario"],
            "probability_estimate": "中等概率",
            "exit_strategy": {
                "stop_loss": current_price * 0.90,
                "take_profit": current_price * 1.20,
                "risk_level": "medium"
            }
        }


def judge_node(state: dict, log_folder: Optional[Path] = None) -> dict:
    """决策节点函数"""
    from trading_agent.core.llm import get_llm
    from trading_agent.core.logger import logger
    from trading_agent.scheduler.workspace_manager import write_log

    if log_folder:
        write_log(log_folder, "=== Node: 综合决策 [开始] ===")

    logger.info("做出最终决策...")

    llm = get_llm()
    judge = Judge(llm)
    result = judge.run(state)

    decision = result.get("decision", "hold")
    confidence = result.get("confidence", 0)
    causal_chain = result.get("causal_chain", [])
    counterfactual = result.get("counterfactual", {})

    logger.info(f"决策: {decision}")

    if log_folder:
        write_log(log_folder, f"决策结果: {decision}")
        write_log(log_folder, f"置信度: {confidence}")
        write_log(log_folder, f"理由: {result.get('reason', '')[:100]}...")
        write_log(log_folder, f"正方评分: {result.get('bull_score', 'N/A')}")
        write_log(log_folder, f"反方评分: {result.get('bear_score', 'N/A')}")

        # 归因链
        write_log(log_folder, "归因链:")
        for step in causal_chain:
            write_log(log_folder, f"  {step['step']}: {step['description']}")

        # 反事实
        write_log(log_folder, "反事实推断:")
        for scenario in counterfactual.get("scenarios", []):
            write_log(log_folder, f"  {scenario['scenario']}: {scenario['suggestion']}")

        write_log(log_folder, "=== Node: 综合决策 [结束] ===")

    return {
        "final_decision": result,
        "causal_chain": causal_chain,
        "counterfactual": counterfactual,
        "logs": state.get("logs", []) + ["决策完成"]
    }