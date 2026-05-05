# -*- coding: utf-8 -*-
"""牛熊判断策略 - 多指标组合"""

import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from .base import StrategyBase

logger = logging.getLogger(__name__)


class MarketTrendStrategy(StrategyBase):
    """牛熊判断策略（多指标组合）

    使用均线排列、涨跌幅、RSI、MACD、量能趋势综合判断市场状态。

    参数：
    - window_days: 滑动窗口大小（默认60）
    - bull_threshold: 牛市涨幅阈值（默认+20%）
    - bear_threshold: 熊市跌幅阈值（默认-20%）
    - ma_short: 短期均线（默认MA20）
    - ma_long: 长期均线（默认MA60）
    - volume_ratio_threshold_high: 量能放大阈值（默认1.5）
    - volume_ratio_threshold_low: 量能萎缩阈值（默认0.7）
    - rsi_period: RSI周期（默认14）
    - rsi_bull_threshold: RSI牛市阈值（默认60）
    - rsi_bear_threshold: RSI熊市阈值（默认40）
    - macd_fast: MACD快线周期（默认12）
    - macd_slow: MACD慢线周期（默认26）
    - macd_signal: MACD信号线周期（默认9）
    """

    name = "market_trend"
    default_params = {
        "window_days": 60,
        "bull_threshold": 20.0,
        "bear_threshold": -20.0,
        "ma_short": 20,
        "ma_long": 60,
        "volume_ratio_threshold_high": 1.5,
        "volume_ratio_threshold_low": 0.7,
        "rsi_period": 14,
        "rsi_bull_threshold": 60.0,
        "rsi_bear_threshold": 40.0,
        "macd_fast": 12,
        "macd_slow": 26,
        "macd_signal": 9,
    }

    def run(self, data: pd.DataFrame) -> Dict[str, Any]:
        """执行牛熊判断策略

        Args:
            data: 日线数据 DataFrame，需包含 date, close, high, low, volume 列

        Returns:
            牛熊判断结果
        """
        return self.analyze(data)

    def analyze(self, df: pd.DataFrame) -> Dict[str, Any]:
        """分析日线数据，返回牛熊状态

        Args:
            df: 日线数据 DataFrame

        Returns:
            {
                'status': '牛市' | '熊市' | '震荡市' | '偏强震荡' | '偏弱震荡',
                'trend_strength': int,  # -100 ~ 100
                'confidence': float,    # 0.0 ~ 1.0
                'signals': list[str],   # 判断信号列表
                'ma_position': dict,    # 均线位置关系
                'price_change': dict,   # 各周期涨跌幅
                'volume_trend': dict,   # 量能趋势
                'rsi': float,           # RSI值
                'macd': dict,           # MACD指标
                'date': str,            # 分析日期
                'price': float,         # 当前价格
            }
        """
        if df is None or df.empty or len(df) < 60:
            return {
                "status": "unknown",
                "trend_strength": 0,
                "confidence": 0.0,
                "signals": ["数据不足，无法判断"],
            }

        # 确保数据按日期排序
        df = df.sort_values("date", ascending=True).reset_index(drop=True)

        # 计算均线（如果数据中没有）
        df = self._calc_mas(df)

        # 计算技术指标
        rsi = self._calc_rsi(df)
        macd = self._calc_macd(df)

        # 最新数据行
        latest = df.iloc[-1]
        date = str(latest.get("date", ""))
        price = float(latest.get("close", 0))

        # 均线位置关系
        ma5 = float(latest.get("ma5", price))
        ma10 = float(latest.get("ma10", price))
        ma20 = float(latest.get("ma20", price))
        ma60 = float(latest.get("ma60", price))
        ma120 = float(latest.get("ma120", price)) if "ma120" in df.columns else price

        ma_position = {
            "above_ma5": price > ma5,
            "above_ma10": price > ma10,
            "above_ma20": price > ma20,
            "above_ma60": price > ma60,
            "above_ma120": price > ma120,
        }

        # 均线排列检查
        bullish_alignment, bearish_alignment = self._check_ma_alignment(latest)

        # 计算涨跌幅
        price_change = {
            "5d": self._calc_price_change(df, 5),
            "10d": self._calc_price_change(df, 10),
            "20d": self._calc_price_change(df, 20),
            "60d": self._calc_price_change(df, 60),
            "120d": self._calc_price_change(df, 120),
            "250d": self._calc_price_change(df, 250),
        }

        # 计算量能比
        volume_ratio = self._calc_volume_ratio(df)
        volume_trend = {
            "ratio": volume_ratio,
            "is_expanding": volume_ratio > self.get_param("volume_ratio_threshold_high"),
            "is_shrinking": volume_ratio < self.get_param("volume_ratio_threshold_low"),
        }

        # 综合判断市场状态
        status, trend_strength, signals, confidence = self._determine_market_status(
            bullish_alignment=bullish_alignment,
            bearish_alignment=bearish_alignment,
            ma_position=ma_position,
            price_change=price_change,
            rsi=rsi,
            macd=macd,
            volume_trend=volume_trend,
        )

        return {
            "status": status,
            "trend_strength": trend_strength,
            "confidence": confidence,
            "signals": signals,
            "ma_position": ma_position,
            "price_change": price_change,
            "volume_trend": volume_trend,
            "rsi": rsi,
            "macd": macd,
            "date": date,
            "price": price,
            "ma5": ma5,
            "ma10": ma10,
            "ma20": ma20,
            "ma60": ma60,
        }

    def _calc_mas(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算均线（如果数据中没有）

        Args:
            df: 日线数据

        Returns:
            添加了均线列的 DataFrame
        """
        if "ma5" not in df.columns:
            df["ma5"] = df["close"].rolling(5).mean()
        if "ma10" not in df.columns:
            df["ma10"] = df["close"].rolling(10).mean()
        if "ma20" not in df.columns:
            df["ma20"] = df["close"].rolling(20).mean()
        if "ma60" not in df.columns:
            df["ma60"] = df["close"].rolling(60).mean()
        if "ma120" not in df.columns:
            df["ma120"] = df["close"].rolling(120).mean()
        if "ma250" not in df.columns:
            df["ma250"] = df["close"].rolling(250).mean()

        return df

    def _check_ma_alignment(self, row: pd.Series) -> Tuple[bool, bool]:
        """检查均线多头/空头排列

        Args:
            row: 数据行

        Returns:
            (多头排列, 空头排列)
        """
        price = float(row.get("close", 0))
        ma5 = float(row.get("ma5", price))
        ma10 = float(row.get("ma10", price))
        ma20 = float(row.get("ma20", price))
        ma60 = float(row.get("ma60", price))

        # 多头排列: MA5 > MA10 > MA20 > MA60
        bullish = ma5 > ma10 and ma10 > ma20 and ma20 > ma60

        # 空头排列: MA5 < MA10 < MA20 < MA60
        bearish = ma5 < ma10 and ma10 < ma20 and ma20 < ma60

        return bullish, bearish

    def _calc_price_change(self, df: pd.DataFrame, days: int) -> float:
        """计算N日涨跌幅

        Args:
            df: 日线数据
            days: 天数

        Returns:
            涨跌幅百分比
        """
        if len(df) < days:
            return 0.0

        latest_close = df.iloc[-1]["close"]
        prev_close = df.iloc[-days]["close"]

        if prev_close <= 0:
            return 0.0

        return (latest_close - prev_close) / prev_close * 100

    def _calc_volume_ratio(self, df: pd.DataFrame) -> float:
        """计算量能比（近10日均量 / 前30日均量）

        Args:
            df: 日线数据

        Returns:
            量能比
        """
        if len(df) < 40 or "volume" not in df.columns:
            return 1.0

        # 近10日均量
        recent_vol = df.tail(10)["volume"].mean()

        # 前30日均量（跳过近10日）
        prev_vol = df.tail(40).head(30)["volume"].mean()

        if prev_vol <= 0:
            return 1.0

        return recent_vol / prev_vol

    def _calc_rsi(self, df: pd.DataFrame, period: int = None) -> float:
        """计算RSI指标

        Args:
            df: 日线数据
            period: RSI周期

        Returns:
            RSI值（0-100）
        """
        if period is None:
            period = self.get_param("rsi_period")

        if len(df) < period + 1:
            return 50.0  # 默认中性值

        close = df["close"]

        # 计算价格变化
        delta = close.diff()

        # 分离上涨和下跌
        gain = delta.where(delta > 0, 0.0)
        loss = -delta.where(delta < 0, 0.0)

        # 计算平均上涨和下跌
        avg_gain = gain.rolling(period).mean()
        avg_loss = loss.rolling(period).mean()

        # 计算RS和RSI
        rs = avg_gain / avg_loss
        rsi = 100.0 - (100.0 / (1.0 + rs))

        # 返回最新RSI
        latest_rsi = rsi.iloc[-1]

        if pd.isna(latest_rsi):
            return 50.0

        return float(latest_rsi)

    def _calc_macd(self, df: pd.DataFrame) -> Dict[str, float]:
        """计算MACD指标

        Args:
            df: 日线数据

        Returns:
            {'dif': float, 'dea': float, 'macd': float}
        """
        fast = self.get_param("macd_fast")
        slow = self.get_param("macd_slow")
        signal = self.get_param("macd_signal")

        if len(df) < slow + signal:
            return {"dif": 0.0, "dea": 0.0, "macd": 0.0}

        close = df["close"]

        # 计算EMA
        ema_fast = close.ewm(span=fast, adjust=False).mean()
        ema_slow = close.ewm(span=slow, adjust=False).mean()

        # DIF = EMA快线 - EMA慢线
        dif = ema_fast - ema_slow

        # DEA = DIF的EMA
        dea = dif.ewm(span=signal, adjust=False).mean()

        # MACD柱 = 2 * (DIF - DEA)
        macd_bar = 2 * (dif - dea)

        # 返回最新值
        latest_dif = dif.iloc[-1]
        latest_dea = dea.iloc[-1]
        latest_macd = macd_bar.iloc[-1]

        return {
            "dif": float(latest_dif) if pd.notna(latest_dif) else 0.0,
            "dea": float(latest_dea) if pd.notna(latest_dea) else 0.0,
            "macd": float(latest_macd) if pd.notna(latest_macd) else 0.0,
            "dif_above_dea": latest_dif > latest_dea,
            "macd_positive": latest_macd > 0,
        }

    def _determine_market_status(
        self,
        bullish_alignment: bool,
        bearish_alignment: bool,
        ma_position: Dict[str, bool],
        price_change: Dict[str, float],
        rsi: float,
        macd: Dict[str, float],
        volume_trend: Dict[str, Any],
    ) -> Tuple[str, int, List[str], float]:
        """综合判断市场状态

        Args:
            bullish_alignment: 多头排列
            bearish_alignment: 空头排列
            ma_position: 均线位置关系
            price_change: 各周期涨跌幅
            rsi: RSI值
            macd: MACD指标
            volume_trend: 量能趋势

        Returns:
            (状态, 趋势强度, 信号列表, 置信度)
        """
        signals: List[str] = []
        bull_score = 0
        bear_score = 0

        bull_threshold = self.get_param("bull_threshold")
        bear_threshold = self.get_param("bear_threshold")
        rsi_bull = self.get_param("rsi_bull_threshold")
        rsi_bear = self.get_param("rsi_bear_threshold")

        # 1. 均线排列评分
        if bullish_alignment:
            bull_score += 30
            signals.append("均线多头排列")
        elif bearish_alignment:
            bear_score += 30
            signals.append("均线空头排列")
        else:
            signals.append("均线交织，方向不明")

        # 2. 价格位置评分
        if ma_position["above_ma20"] and ma_position["above_ma60"]:
            bull_score += 20
            signals.append("价格在MA20和MA60上方")
        elif not ma_position["above_ma20"] and not ma_position["above_ma60"]:
            bear_score += 20
            signals.append("价格在MA20和MA60下方")

        # 3. 涨跌幅评分
        change_60d = price_change["60d"]
        if change_60d > bull_threshold:
            bull_score += 30
            signals.append(f"近60日涨幅{change_60d:.1f}%超阈值")
        elif change_60d < bear_threshold:
            bear_score += 30
            signals.append(f"近60日跌幅{change_60d:.1f}%超阈值")
        else:
            signals.append(f"近60日涨跌幅{change_60d:.1f}%")

        # 4. RSI评分
        if rsi > rsi_bull:
            bull_score += 10
            signals.append(f"RSI={rsi:.1f}在强势区")
        elif rsi < rsi_bear:
            bear_score += 10
            signals.append(f"RSI={rsi:.1f}在弱势区")
        else:
            signals.append(f"RSI={rsi:.1f}中性")

        # 5. MACD评分
        if macd["dif_above_dea"] and macd["macd_positive"]:
            bull_score += 10
            signals.append("MACD金叉，柱正值")
        elif not macd["dif_above_dea"] and not macd["macd_positive"]:
            bear_score += 10
            signals.append("MACD死叉，柱负值")

        # 6. 量能评分
        if volume_trend["is_expanding"]:
            bull_score += 10
            signals.append(f"量能放大{volume_trend['ratio']:.2f}倍")
        elif volume_trend["is_shrinking"]:
            bear_score += 10
            signals.append(f"量能萎缩{volume_trend['ratio']:.2f}倍")

        # 计算趋势强度和状态
        trend_strength = bull_score - bear_score

        # 状态判断
        if trend_strength >= 70:
            status = "牛市"
            confidence = 0.9
        elif trend_strength >= 40:
            status = "偏强震荡"
            confidence = 0.75
        elif trend_strength <= -70:
            status = "熊市"
            confidence = 0.9
        elif trend_strength <= -40:
            status = "偏弱震荡"
            confidence = 0.75
        else:
            status = "震荡市"
            confidence = 0.6

        # 置信度调整（信号数量越多，置信度越高）
        signal_count = len(signals)
        confidence = min(confidence + signal_count * 0.02, 1.0)

        return status, trend_strength, signals, confidence