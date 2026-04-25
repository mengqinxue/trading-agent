"""
Tech Analyst node - 技术面分析

Responsibilities:
- K-line pattern recognition
- Technical indicators (MACD, RSI, MA)
- Volume analysis
- Money flow analysis
- Generate buy/sell/hold recommendation
"""

from datetime import datetime
from typing import Dict, List, Any

from trading_agent.graph.state import (
    WorkflowState,
    StepStatus,
    TechAnalysisResult,
    Recommendation,
    Stock,
)
from trading_agent.data_sources import DataAggregator
from trading_agent.data_sources.akshare_data import KlineData
from trading_agent.utils.logger import get_logger

logger = get_logger("TECH_ANALYST")


def tech_analyst_node(state: WorkflowState) -> Dict:
    """
    Tech Analyst node entry function

    This node runs in parallel with fund_analyst.
    Performs technical analysis on candidate stocks.

    Args:
        state: Current workflow state

    Returns:
        Dict with updated state fields
    """
    run_id = state.get("run_id", "unknown")
    logger.info(f"[{run_id}] Tech Analyst node started")
    logger.info(f"[{run_id}] Status: {state.get('tech_analyst_status')}")

    # Update status to RUNNING
    updates: Dict[str, Any] = {
        "tech_analyst_status": StepStatus.RUNNING.value,
        "current_step_start": datetime.now().isoformat(),
    }

    try:
        # Load candidate stocks from screener
        candidates = state.get("candidate_stocks", [])
        logger.info(f"[{run_id}] Loaded {len(candidates)} candidate stocks")

        if not candidates:
            logger.warning(f"[{run_id}] No candidate stocks to analyze")
            updates["tech_results"] = []
            updates["tech_analyst_status"] = StepStatus.COMPLETED.value
            return updates

        # Initialize data aggregator
        aggregator = DataAggregator(kline_days=60)

        # Analyze each candidate stock
        tech_results: List[TechAnalysisResult] = []

        for candidate in candidates:
            # Convert dict to Stock if needed
            if isinstance(candidate, dict):
                stock = Stock(**candidate)
            else:
                stock = candidate

            logger.info(f"[{run_id}] Analyzing {stock.code} - {stock.name}")

            try:
                # Step 1: Get K-line data
                logger.info(f"[{run_id}] Step 1: Fetching K-line data for {stock.code}")
                stock_bundle = aggregator.aggregate_stock_data(stock.code)
                kline_data = stock_bundle.kline_data

                if not kline_data or not kline_data.success:
                    logger.warning(
                        f"[{run_id}] K-line data fetch failed for {stock.code}: {kline_data.error if kline_data else 'No data'}"
                    )
                    # Create fallback result
                    tech_result = _create_fallback_result(stock, run_id)
                    tech_results.append(tech_result)
                    continue

                klines = kline_data.data
                logger.info(f"[{run_id}] Got {len(klines)} K-line data points")

                # Step 2: Calculate technical indicators
                logger.info(f"[{run_id}] Step 2: Calculating technical indicators")
                indicators = _calculate_indicators(klines, run_id)

                # Step 3: Analyze K-line patterns
                logger.info(f"[{run_id}] Step 3: Analyzing K-line patterns")
                patterns = _analyze_patterns(klines, run_id)

                # Step 4: Analyze volume and money flow
                logger.info(f"[{run_id}] Step 4: Analyzing volume and money flow")
                volume_analysis = _analyze_volume(klines, run_id)

                # Step 5: Generate trend direction
                logger.info(f"[{run_id}] Step 5: Determining trend direction")
                trend = _determine_trend(indicators, patterns, volume_analysis, run_id)

                # Step 6: Generate signals
                logger.info(f"[{run_id}] Step 6: Generating signals")
                signals = _generate_signals(indicators, patterns, volume_analysis, trend, run_id)

                # Step 7: Generate recommendation
                logger.info(f"[{run_id}] Step 7: Generating recommendation")
                recommendation, confidence, arguments = _generate_recommendation(
                    indicators, patterns, volume_analysis, trend, signals, run_id
                )

                # Build TechAnalysisResult
                tech_result = TechAnalysisResult(
                    stock_code=stock.code,
                    stock_name=stock.name,
                    trend_direction=trend,
                    signals=signals,
                    recommendation=recommendation,
                    confidence=confidence,
                    arguments=arguments,
                )
                tech_results.append(tech_result)

                logger.info(
                    f"[{run_id}] Analysis complete for {stock.code}: "
                    f"trend={trend}, recommendation={recommendation.value}, confidence={confidence:.2f}"
                )

            except Exception as e:
                logger.error(f"[{run_id}] Failed to analyze {stock.code}: {e}")
                # Create fallback result on error
                tech_result = _create_fallback_result(stock, run_id, str(e))
                tech_results.append(tech_result)

        # Update state with results
        updates["tech_results"] = tech_results
        updates["tech_analyst_status"] = StepStatus.COMPLETED.value

        logger.info(f"[{run_id}] Tech Analyst node completed successfully")
        logger.info(f"[{run_id}] Results: {len(tech_results)} stocks analyzed")

    except Exception as e:
        logger.error(f"[{run_id}] Tech Analyst node failed: {e}")
        updates["tech_analyst_status"] = StepStatus.FAILED.value
        updates["error_step"] = "tech_analyst"
        updates["error_message"] = str(e)
        updates["tech_results"] = []

    return updates


# ============== Technical Indicator Calculations ==============


def _calculate_indicators(klines: List[KlineData], run_id: str) -> Dict[str, Any]:
    """
    Calculate technical indicators from K-line data

    Simplified implementation for MVP - calculates mock indicators.

    Args:
        klines: List of K-line data points
        run_id: Run ID for logging

    Returns:
        Dict containing MACD, RSI, KDJ, MA indicators
    """
    if len(klines) < 10:
        logger.warning(f"[{run_id}] Insufficient K-line data for indicator calculation")
        return _get_default_indicators()

    # Get recent prices
    closes = [k.close for k in klines]

    # Calculate Moving Averages (MA5, MA10, MA20)
    ma5 = _calculate_ma(closes, 5)
    ma10 = _calculate_ma(closes, 10)
    ma20 = _calculate_ma(closes, 20)

    logger.info(
        f"[{run_id}] MA indicators: MA5={ma5:.2f}, MA10={ma10:.2f}, MA20={ma20:.2f}"
    )

    # Calculate RSI (simplified)
    rsi = _calculate_rsi(closes, 14)
    logger.info(f"[{run_id}] RSI indicator: {rsi:.2f}")

    # Calculate MACD (simplified)
    macd, signal, histogram = _calculate_macd(closes)
    logger.info(
        f"[{run_id}] MACD indicators: MACD={macd:.2f}, Signal={signal:.2f}, Histogram={histogram:.2f}"
    )

    # Calculate KDJ (simplified)
    k, d, j = _calculate_kdj(klines)
    logger.info(f"[{run_id}] KDJ indicators: K={k:.2f}, D={d:.2f}, J={j:.2f}")

    return {
        "ma5": ma5,
        "ma10": ma10,
        "ma20": ma20,
        "rsi": rsi,
        "macd": macd,
        "macd_signal": signal,
        "macd_histogram": histogram,
        "kdj_k": k,
        "kdj_d": d,
        "kdj_j": j,
        "latest_close": closes[-1],
        "price_change_5d": _calculate_price_change(closes, 5),
        "price_change_10d": _calculate_price_change(closes, 10),
    }


def _calculate_ma(prices: List[float], period: int) -> float:
    """Calculate Simple Moving Average"""
    if len(prices) < period:
        return prices[-1] if prices else 0.0
    return sum(prices[-period:]) / period


def _calculate_rsi(prices: List[float], period: int = 14) -> float:
    """
    Calculate Relative Strength Index (simplified)

    RSI = 100 - 100 / (1 + RS)
    RS = Average Gain / Average Loss
    """
    if len(prices) < period + 1:
        return 50.0  # Neutral RSI

    gains = []
    losses = []

    for i in range(1, len(prices)):
        change = prices[i] - prices[i - 1]
        if change > 0:
            gains.append(change)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(change))

    # Calculate average gains and losses over period
    avg_gain = sum(gains[-period:]) / period if gains else 0
    avg_loss = sum(losses[-period:]) / period if losses else 0

    if avg_loss == 0:
        return 100.0

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    return round(rsi, 2)


def _calculate_macd(prices: List[float]) -> tuple[float, float, float]:
    """
    Calculate MACD (Moving Average Convergence Divergence) - simplified

    MACD = EMA12 - EMA26
    Signal = EMA9 of MACD
    Histogram = MACD - Signal

    Using simplified EMA calculation for MVP.
    """
    if len(prices) < 26:
        return (0.0, 0.0, 0.0)

    # Simplified EMA calculation using MA
    ema12 = _calculate_ma(prices, 12)
    ema26 = _calculate_ma(prices, 26)

    macd = ema12 - ema26

    # Need more data for signal line, use simplified
    # Calculate MACD values for signal
    macd_values = []
    for i in range(9, len(prices)):
        ema12_i = _calculate_ma(prices[:i + 1], 12)
        ema26_i = _calculate_ma(prices[:i + 1], 26)
        macd_values.append(ema12_i - ema26_i)

    signal = _calculate_ma(macd_values[-9:], 9) if len(macd_values) >= 9 else 0.0
    histogram = macd - signal

    return (round(macd, 4), round(signal, 4), round(histogram, 4))


def _calculate_kdj(klines: List[KlineData]) -> tuple[float, float, float]:
    """
    Calculate KDJ indicator (Stochastic) - simplified

    K = (Close - Lowest Low) / (Highest High - Lowest Low) * 100
    D = 3-period MA of K
    J = 3K - 2D
    """
    if len(klines) < 9:
        return (50.0, 50.0, 50.0)

    period = 9
    recent_klines = klines[-period:]

    highest_high = max(k.high for k in recent_klines)
    lowest_low = min(k.low for k in recent_klines)
    latest_close = klines[-1].close

    if highest_high == lowest_low:
        k_value = 50.0
    else:
        k_value = (latest_close - lowest_low) / (highest_high - lowest_low) * 100

    # Simplified D calculation
    d_value = k_value  # For MVP, use K as D

    j_value = 3 * k_value - 2 * d_value

    return (round(k_value, 2), round(d_value, 2), round(j_value, 2))


def _calculate_price_change(prices: List[float], days: int) -> float:
    """Calculate price change percentage over N days"""
    if len(prices) < days + 1:
        return 0.0
    return round((prices[-1] - prices[-days - 1]) / prices[-days - 1] * 100, 2)


def _get_default_indicators() -> Dict[str, Any]:
    """Return default neutral indicators when calculation fails"""
    return {
        "ma5": 0.0,
        "ma10": 0.0,
        "ma20": 0.0,
        "rsi": 50.0,
        "macd": 0.0,
        "macd_signal": 0.0,
        "macd_histogram": 0.0,
        "kdj_k": 50.0,
        "kdj_d": 50.0,
        "kdj_j": 50.0,
        "latest_close": 0.0,
        "price_change_5d": 0.0,
        "price_change_10d": 0.0,
    }


# ============== Pattern Analysis ==============


def _analyze_patterns(klines: List[KlineData], run_id: str) -> Dict[str, Any]:
    """
    Analyze K-line patterns for trading signals

    Simplified implementation for MVP.

    Args:
        klines: List of K-line data points
        run_id: Run ID for logging

    Returns:
        Dict containing pattern analysis results
    """
    if len(klines) < 3:
        return {"patterns_detected": [], "pattern_strength": 0.0}

    patterns_detected: List[str] = []
    pattern_strength = 0.0

    # Get recent K-lines
    latest = klines[-1]
    prev = klines[-2]
    prev2 = klines[-3] if len(klines) >= 3 else klines[-2]

    # Check for bullish patterns
    if latest.close > latest.open and prev.close < prev.open:
        patterns_detected.append("阳包阴")  # Bullish engulfing
        pattern_strength += 0.3

    if latest.close > prev.close and prev.close > prev2.close:
        patterns_detected.append("三连阳")  # Three consecutive bullish
        pattern_strength += 0.2

    # Check for bearish patterns
    if latest.close < latest.open and prev.close > prev.open:
        patterns_detected.append("阴包阳")  # Bearish engulfing
        pattern_strength -= 0.3

    if latest.close < prev.close and prev.close < prev2.close:
        patterns_detected.append("三连阴")  # Three consecutive bearish
        pattern_strength -= 0.2

    # Check for doji (neutral)
    body_size = abs(latest.close - latest.open)
    candle_range = latest.high - latest.low
    if candle_range > 0 and body_size / candle_range < 0.1:
        patterns_detected.append("十字星")  # Doji
        pattern_strength += 0.0

    logger.info(
        f"[{run_id}] Patterns detected: {patterns_detected}, strength: {pattern_strength:.2f}"
    )

    return {
        "patterns_detected": patterns_detected,
        "pattern_strength": round(pattern_strength, 2),
    }


# ============== Volume Analysis ==============


def _analyze_volume(klines: List[KlineData], run_id: str) -> Dict[str, Any]:
    """
    Analyze volume and money flow

    Simplified implementation for MVP.

    Args:
        klines: List of K-line data points
        run_id: Run ID for logging

    Returns:
        Dict containing volume analysis results
    """
    if len(klines) < 5:
        return {"volume_trend": "neutral", "money_flow": "neutral"}

    recent_volumes = [k.volume for k in klines[-5:]]
    avg_volume = sum(recent_volumes) / len(recent_volumes)
    latest_volume = klines[-1].volume

    # Volume trend analysis
    if latest_volume > avg_volume * 1.5:
        volume_trend = "increasing"
    elif latest_volume < avg_volume * 0.5:
        volume_trend = "decreasing"
    else:
        volume_trend = "neutral"

    # Money flow (simplified: price change * volume)
    latest_close = klines[-1].close
    prev_close = klines[-2].close
    price_change = latest_close - prev_close

    if price_change > 0 and latest_volume > avg_volume:
        money_flow = "inflow"  # Price up with high volume = inflow
    elif price_change < 0 and latest_volume > avg_volume:
        money_flow = "outflow"  # Price down with high volume = outflow
    else:
        money_flow = "neutral"

    logger.info(
        f"[{run_id}] Volume trend: {volume_trend}, Money flow: {money_flow}"
    )

    return {
        "volume_trend": volume_trend,
        "money_flow": money_flow,
        "avg_volume": round(avg_volume, 0),
        "latest_volume": round(latest_volume, 0),
        "volume_ratio": round(latest_volume / avg_volume, 2) if avg_volume > 0 else 1.0,
    }


# ============== Trend Determination ==============


def _determine_trend(
    indicators: Dict[str, Any],
    patterns: Dict[str, Any],
    volume_analysis: Dict[str, Any],
    run_id: str,
) -> str:
    """
    Determine overall trend direction based on indicators

    Args:
        indicators: Technical indicators dict
        patterns: Pattern analysis dict
        volume_analysis: Volume analysis dict
        run_id: Run ID for logging

    Returns:
        Trend direction: 'up', 'down', or 'neutral'
    """
    # Count bullish and bearish signals
    bullish_score = 0.0
    bearish_score = 0.0

    # MA trend
    ma5 = indicators.get("ma5", 0)
    ma10 = indicators.get("ma10", 0)
    ma20 = indicators.get("ma20", 0)

    if ma5 > ma10 > ma20:
        bullish_score += 0.3
    elif ma5 < ma10 < ma20:
        bearish_score += 0.3

    # RSI trend
    rsi = indicators.get("rsi", 50)
    if rsi > 70:
        bearish_score += 0.2  # Overbought
    elif rsi < 30:
        bullish_score += 0.2  # Oversold (potential bounce)

    # MACD trend
    macd = indicators.get("macd", 0)
    macd_signal = indicators.get("macd_signal", 0)
    if macd > macd_signal:
        bullish_score += 0.2
    else:
        bearish_score += 0.2

    # KDJ trend
    kdj_k = indicators.get("kdj_k", 50)
    kdj_j = indicators.get("kdj_j", 50)
    if kdj_k > 80 and kdj_j > 100:
        bearish_score += 0.2  # Overbought
    elif kdj_k < 20 and kdj_j < 0:
        bullish_score += 0.2  # Oversold

    # Pattern strength
    pattern_strength = patterns.get("pattern_strength", 0)
    if pattern_strength > 0:
        bullish_score += pattern_strength
    elif pattern_strength < 0:
        bearish_score += abs(pattern_strength)

    # Volume confirmation
    money_flow = volume_analysis.get("money_flow", "neutral")
    if money_flow == "inflow":
        bullish_score += 0.1
    elif money_flow == "outflow":
        bearish_score += 0.1

    # Determine trend
    if bullish_score > bearish_score + 0.2:
        trend = "up"
    elif bearish_score > bullish_score + 0.2:
        trend = "down"
    else:
        trend = "neutral"

    logger.info(
        f"[{run_id}] Trend determination: bullish={bullish_score:.2f}, bearish={bearish_score:.2f}, trend={trend}"
    )

    return trend


# ============== Signal Generation ==============


def _generate_signals(
    indicators: Dict[str, Any],
    patterns: Dict[str, Any],
    volume_analysis: Dict[str, Any],
    trend: str,
    run_id: str,
) -> List[str]:
    """
    Generate trading signals based on analysis

    Args:
        indicators: Technical indicators
        patterns: Pattern analysis
        volume_analysis: Volume analysis
        trend: Trend direction
        run_id: Run ID for logging

    Returns:
        List of signal strings
    """
    signals: List[str] = []

    # MA signals
    ma5 = indicators.get("ma5", 0)
    ma10 = indicators.get("ma10", 0)
    ma20 = indicators.get("ma20", 0)
    latest_close = indicators.get("latest_close", 0)

    if latest_close > ma5 > ma10:
        signals.append("价格位于均线上方")
    elif latest_close < ma5 < ma10:
        signals.append("价格位于均线下方")

    # RSI signals
    rsi = indicators.get("rsi", 50)
    if rsi > 70:
        signals.append(f"RSI超买区域({rsi:.1f})")
    elif rsi < 30:
        signals.append(f"RSI超卖区域({rsi:.1f})")
    else:
        signals.append(f"RSI正常区域({rsi:.1f})")

    # MACD signals
    macd = indicators.get("macd", 0)
    macd_signal = indicators.get("macd_signal", 0)
    histogram = indicators.get("macd_histogram", 0)
    if histogram > 0:
        signals.append("MACD金叉信号")
    elif histogram < 0:
        signals.append("MACD死叉信号")

    # KDJ signals
    kdj_k = indicators.get("kdj_k", 50)
    if kdj_k > 80:
        signals.append(f"KDJ超买(K={kdj_k:.1f})")
    elif kdj_k < 20:
        signals.append(f"KDJ超卖(K={kdj_k:.1f})")

    # Pattern signals
    patterns_detected = patterns.get("patterns_detected", [])
    if patterns_detected:
        signals.extend(patterns_detected)

    # Volume signals
    money_flow = volume_analysis.get("money_flow", "neutral")
    volume_ratio = volume_analysis.get("volume_ratio", 1.0)
    if money_flow == "inflow":
        signals.append(f"资金流入(量比={volume_ratio:.2f})")
    elif money_flow == "outflow":
        signals.append(f"资金流出(量比={volume_ratio:.2f})")

    logger.info(f"[{run_id}] Generated signals: {signals}")

    return signals


# ============== Recommendation Generation ==============


def _generate_recommendation(
    indicators: Dict[str, Any],
    patterns: Dict[str, Any],
    volume_analysis: Dict[str, Any],
    trend: str,
    signals: List[str],
    run_id: str,
) -> tuple[Recommendation, float, List[str]]:
    """
    Generate final recommendation with confidence and arguments

    Args:
        indicators: Technical indicators
        patterns: Pattern analysis
        volume_analysis: Volume analysis
        trend: Trend direction
        signals: List of signals
        run_id: Run ID for logging

    Returns:
        Tuple of (Recommendation, confidence, arguments)
    """
    bullish_arguments: List[str] = []
    bearish_arguments: List[str] = []

    # Build bullish arguments
    if trend == "up":
        bullish_arguments.append("技术面趋势向上")

    if indicators.get("rsi", 50) < 30:
        bullish_arguments.append("RSI处于超卖区，可能反弹")

    if indicators.get("macd_histogram", 0) > 0:
        bullish_arguments.append("MACD金叉确认")

    if volume_analysis.get("money_flow") == "inflow":
        bullish_arguments.append("资金持续流入")

    # Build bearish arguments
    if trend == "down":
        bearish_arguments.append("技术面趋势向下")

    if indicators.get("rsi", 50) > 70:
        bearish_arguments.append("RSI处于超买区，可能回调")

    if indicators.get("macd_histogram", 0) < 0:
        bearish_arguments.append("MACD死叉确认")

    if volume_analysis.get("money_flow") == "outflow":
        bearish_arguments.append("资金持续流出")

    # Pattern arguments
    pattern_strength = patterns.get("pattern_strength", 0)
    if pattern_strength > 0.2:
        bullish_arguments.append("K线形态显示多头信号")
    elif pattern_strength < -0.2:
        bearish_arguments.append("K线形态显示空头信号")

    # Determine recommendation
    bullish_count = len(bullish_arguments)
    bearish_count = len(bearish_arguments)

    if bullish_count > bearish_count + 1:
        recommendation = Recommendation.BUY
        confidence = min(0.3 + bullish_count * 0.1, 0.9)
        arguments = bullish_arguments
    elif bearish_count > bullish_count + 1:
        recommendation = Recommendation.SELL
        confidence = min(0.3 + bearish_count * 0.1, 0.9)
        arguments = bearish_arguments
    else:
        recommendation = Recommendation.HOLD
        confidence = 0.5
        arguments = ["技术面信号不明确，建议观望"]
        if bullish_arguments:
            arguments.append(f"多头因素: {', '.join(bullish_arguments)}")
        if bearish_arguments:
            arguments.append(f"空头因素: {', '.join(bearish_arguments)}")

    logger.info(
        f"[{run_id}] Recommendation: {recommendation.value}, "
        f"confidence: {confidence:.2f}, arguments: {arguments}"
    )

    return (recommendation, round(confidence, 2), arguments)


# ============== Fallback Result ==============


def _create_fallback_result(
    stock: Stock, run_id: str, error_msg: str = "数据获取失败"
) -> TechAnalysisResult:
    """
    Create a fallback TechAnalysisResult when analysis fails

    Args:
        stock: Stock info
        run_id: Run ID for logging
        error_msg: Error message

    Returns:
        TechAnalysisResult with HOLD recommendation and low confidence
    """
    logger.warning(f"[{run_id}] Creating fallback result for {stock.code}: {error_msg}")

    return TechAnalysisResult(
        stock_code=stock.code,
        stock_name=stock.name,
        trend_direction="neutral",
        signals=[f"分析失败: {error_msg}"],
        recommendation=Recommendation.HOLD,
        confidence=0.3,
        arguments=["技术分析数据不足，建议观望或结合基本面分析"],
    )