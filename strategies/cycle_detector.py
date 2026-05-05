# -*- coding: utf-8 -*-
"""牛熊周期检测策略 - 混合方法"""

import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from .base import StrategyBase

logger = logging.getLogger(__name__)


class BullBearCycleDetector(StrategyBase):
    """牛熊周期检测策略（混合方法）

    先峰谷检测识别转换点，再滑动窗口验证。

    参数：
    - min_cycle_days: 最小周期天数（默认30）
    - peak_trough_window: 峰谷识别窗口（默认20）
    - transition_threshold: 转换阈值（默认15%）
    - trend_window: 趋势强度窗口（默认60）
    """

    name = "bull_bear_cycle_detector"
    default_params = {
        "min_cycle_days": 30,
        "peak_trough_window": 20,
        "transition_threshold": 15.0,
        "trend_window": 60,
    }

    def run(self, data: pd.DataFrame) -> List[Dict[str, Any]]:
        """执行周期检测

        Args:
            data: 日线数据 DataFrame

        Returns:
            周期列表
        """
        return self.detect_cycles(data)

    def detect_cycles(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """检测历史牛熊周期（混合方法）

        步骤：
        1. find_peaks_and_troughs() - 识别峰谷点
        2. verify_transitions() - 滑动窗口验证转换
        3. mark_cycles() - 标记周期

        Args:
            df: 日线数据 DataFrame

        Returns:
            周期列表，每个周期包含：
            - start_date: 开始日期
            - end_date: 结束日期
            - type: 牛市/熊市/震荡
            - peak_price: 周期内最高价
            - trough_price: 周期内最低价
            - change_pct: 周期涨跌幅
            - duration_days: 持续天数
            - peak_date: 峰值日期
            - trough_date: 谷值日期
        """
        if df is None or df.empty or len(df) < self.get_param("min_cycle_days"):
            return []

        # 确保数据按日期排序
        df = df.sort_values("date", ascending=True).reset_index(drop=True)

        # Step 1: 识别峰谷点
        peaks_troughs = self.find_peaks_and_troughs(df)
        if not peaks_troughs:
            return []

        # Step 2: 滑动窗口验证转换点
        verified_points = self.verify_transitions(df, peaks_troughs)
        if not verified_points:
            return []

        # Step 3: 标记周期
        cycles = self.mark_cycles(df, verified_points)

        return cycles

    def find_peaks_and_troughs(
        self, df: pd.DataFrame, window: int = None
    ) -> List[Dict[str, Any]]:
        """识别局部峰谷点

        使用滑动窗口，比较中心点与窗口内其他点，
        判断是否为局部最高点（峰）或局部最低点（谷）。

        Args:
            df: 日线数据
            window: 窗口大小

        Returns:
            峰谷点列表，每个点包含：
            - date: 日期
            - price: 价格
            - type: 'peak' 或 'trough'
            - idx: 数据索引
        """
        if window is None:
            window = self.get_param("peak_trough_window")

        if len(df) < window * 2:
            return []

        peaks_troughs: List[Dict[str, Any]] = []
        close = df["close"].values

        # 滑动窗口识别峰谷
        for i in range(window, len(df) - window):
            left_window = close[i - window : i]
            right_window = close[i + 1 : i + window + 1]
            center_price = close[i]

            # 检查是否为局部峰（高于左右窗口所有点）
            if center_price > max(left_window) and center_price > max(right_window):
                peaks_troughs.append({
                    "date": str(df.iloc[i]["date"]),
                    "price": float(center_price),
                    "type": "peak",
                    "idx": i,
                })

            # 检查是否为局部谷（低于左右窗口所有点）
            elif center_price < min(left_window) and center_price < min(right_window):
                peaks_troughs.append({
                    "date": str(df.iloc[i]["date"]),
                    "price": float(center_price),
                    "type": "trough",
                    "idx": i,
                })

        logger.info(f"[周期检测] 识别到 {len(peaks_troughs)} 个峰谷点")
        return peaks_troughs

    def verify_transitions(
        self, df: pd.DataFrame, peaks_troughs: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """滑动窗口验证转换点

        在峰谷点附近计算趋势强度，验证是否确实发生了趋势转换。

        Args:
            df: 日线数据
            peaks_troughs: 峰谷点列表

        Returns:
            验证后的转换点列表，包含：
            - date: 日期
            - price: 价格
            - type: 'peak' 或 'trough'
            - idx: 数据索引
            - trend_before: 转换前趋势强度
            - trend_after: 转换后趋势强度
            - is_valid: 是否为有效转换点
        """
        verified: List[Dict[str, Any]] = []
        trend_window = self.get_param("trend_window")
        transition_threshold = self.get_param("transition_threshold")

        for point in peaks_troughs:
            idx = point["idx"]

            # 检查数据是否足够计算趋势
            if idx < trend_window or idx > len(df) - trend_window:
                continue

            # 计算转换前趋势强度（峰/谷点前一个窗口）
            trend_before = self.calc_trend_strength(df, idx - 1, trend_window)

            # 计算转换后趋势强度（峰/谷点后一个窗口）
            trend_after = self.calc_trend_strength(df, idx + trend_window, trend_window)

            # 判断是否为有效转换点
            is_valid = False

            if point["type"] == "peak":
                # 峰点：转换前应为强势（牛市），转换后应为弱势（熊市）
                # 即 trend_before 高，trend_after 低
                if trend_before > 30 and trend_after < 30:
                    is_valid = True
            else:
                # 谷点：转换前应为弱势（熊市），转换后应为强势（牛市）
                # 即 trend_before 低，trend_after 高
                if trend_before < -30 and trend_after > -30:
                    is_valid = True

            point["trend_before"] = trend_before
            point["trend_after"] = trend_after
            point["is_valid"] = is_valid

            # 即使不完全满足条件，也保留峰谷点（可能用于辅助判断）
            verified.append(point)

        # 过滤有效转换点
        valid_points = [p for p in verified if p["is_valid"]]
        logger.info(
            f"[周期检测] 验证后有效转换点: {len(valid_points)} / {len(peaks_troughs)}"
        )

        # 如果没有有效转换点，返回所有峰谷点（降低标准）
        if not valid_points:
            logger.warning("[周期检测] 无有效转换点，使用所有峰谷点")
            return verified

        return valid_points

    def calc_trend_strength(self, df: pd.DataFrame, idx: int, window: int = 60) -> int:
        """计算某点的趋势强度

        Args:
            df: 日线数据
            idx: 数据索引
            window: 计算窗口

        Returns:
            趋势强度（-100 ~ 100）
        """
        if idx < 0 or idx >= len(df):
            return 0

        # 取窗口内的数据
        start_idx = max(0, idx - window + 1)
        end_idx = idx + 1

        window_df = df.iloc[start_idx:end_idx]

        if len(window_df) < window // 2:
            return 0

        # 计算涨跌幅
        start_close = window_df.iloc[0]["close"]
        end_close = window_df.iloc[-1]["close"]

        if start_close <= 0:
            return 0

        change_pct = (end_close - start_close) / start_close * 100

        # 计算均线位置
        ma_window = min(20, len(window_df) - 1)
        if ma_window > 0:
            ma = window_df.tail(ma_window)["close"].mean()
            above_ma = end_close > ma
        else:
            above_ma = False

        # 计算趋势强度
        # 涨幅贡献: 每涨1%贡献2分，上限50分
        change_score = min(abs(change_pct) * 2, 50)

        # 均线位置贡献: 20分
        ma_score = 20 if above_ma else -20

        # 综合趋势强度
        if change_pct > 0:
            trend_strength = change_score + ma_score
        else:
            trend_strength = -change_score + ma_score

        # 限制在 -100 ~ 100
        return int(np.clip(trend_strength, -100, 100))

    def mark_cycles(
        self, df: pd.DataFrame, verified_points: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """标记牛熊周期

        根据验证后的转换点，划分牛熊周期。

        Args:
            df: 日线数据
            verified_points: 验证后的转换点

        Returns:
            周期列表
        """
        if not verified_points:
            return []

        cycles: List[Dict[str, Any]] = []
        min_cycle_days = self.get_param("min_cycle_days")

        # 按日期排序
        verified_points = sorted(verified_points, key=lambda x: x["idx"])

        # 第一个周期从数据起始点开始
        start_idx = 0
        start_date = str(df.iloc[0]["date"])
        start_price = float(df.iloc[0]["close"])

        # 初始状态判断
        first_point = verified_points[0]
        if first_point["type"] == "peak":
            # 第一个点是峰，说明之前是上涨周期（牛市）
            initial_type = "牛市"
        else:
            # 第一个点是谷，说明之前是下跌周期（熊市）
            initial_type = "熊市"

        for i, point in enumerate(verified_points):
            end_idx = point["idx"]
            end_date = point["date"]
            end_price = point["price"]

            # 计算周期内最高价和最低价
            cycle_df = df.iloc[start_idx:end_idx + 1]
            peak_price = float(cycle_df["high"].max())
            trough_price = float(cycle_df["low"].min())
            peak_date = str(cycle_df.loc[cycle_df["high"].idxmax(), "date"])
            trough_date = str(cycle_df.loc[cycle_df["low"].idxmin(), "date"])

            # 计算涨跌幅
            change_pct = (end_price - start_price) / start_price * 100 if start_price > 0 else 0

            # 持续天数
            duration_days = end_idx - start_idx + 1

            # 周期类型判断（根据涨跌幅和转换点类型）
            if change_pct > 20:
                cycle_type = "牛市"
            elif change_pct < -20:
                cycle_type = "熊市"
            else:
                cycle_type = "震荡"

            # 只记录有效周期（持续天数足够）
            if duration_days >= min_cycle_days:
                cycles.append({
                    "start_date": start_date,
                    "end_date": end_date,
                    "type": cycle_type,
                    "peak_price": peak_price,
                    "trough_price": trough_price,
                    "change_pct": round(change_pct, 2),
                    "duration_days": duration_days,
                    "peak_date": peak_date,
                    "trough_date": trough_date,
                })

            # 更新下一个周期的起点
            start_idx = end_idx
            start_date = end_date
            start_price = end_price

        # 最后一个周期（从最后一个转换点到数据结束）
        if start_idx < len(df) - 1:
            end_idx = len(df) - 1
            cycle_df = df.iloc[start_idx:end_idx + 1]
            end_date = str(df.iloc[end_idx]["date"])
            end_price = float(df.iloc[end_idx]["close"])

            peak_price = float(cycle_df["high"].max())
            trough_price = float(cycle_df["low"].min())
            peak_date = str(cycle_df.loc[cycle_df["high"].idxmax(), "date"])
            trough_date = str(cycle_df.loc[cycle_df["low"].idxmin(), "date"])

            change_pct = (end_price - start_price) / start_price * 100 if start_price > 0 else 0
            duration_days = end_idx - start_idx + 1

            # 最后周期类型
            if change_pct > 20:
                cycle_type = "牛市"
            elif change_pct < -20:
                cycle_type = "熊市"
            else:
                cycle_type = "震荡"

            if duration_days >= min_cycle_days:
                cycles.append({
                    "start_date": start_date,
                    "end_date": end_date,
                    "type": cycle_type,
                    "peak_price": peak_price,
                    "trough_price": trough_price,
                    "change_pct": round(change_pct, 2),
                    "duration_days": duration_days,
                    "peak_date": peak_date,
                    "trough_date": trough_date,
                })

        logger.info(f"[周期检测] 标记 {len(cycles)} 个周期")
        return cycles

    def get_cycle_summary(self, cycles: List[Dict[str, Any]]) -> Dict[str, Any]:
        """获取周期统计摘要

        Args:
            cycles: 周期列表

        Returns:
            统计摘要
        """
        if not cycles:
            return {}

        bull_cycles = [c for c in cycles if c["type"] == "牛市"]
        bear_cycles = [c for c in cycles if c["type"] == "熊市"]
        oscillation_cycles = [c for c in cycles if c["type"] == "震荡"]

        # 平均持续天数
        avg_bull_days = (
            sum(c["duration_days"] for c in bull_cycles) / len(bull_cycles)
            if bull_cycles else 0
        )
        avg_bear_days = (
            sum(c["duration_days"] for c in bear_cycles) / len(bear_cycles)
            if bear_cycles else 0
        )

        # 平均涨跌幅
        avg_bull_change = (
            sum(c["change_pct"] for c in bull_cycles) / len(bull_cycles)
            if bull_cycles else 0
        )
        avg_bear_change = (
            sum(c["change_pct"] for c in bear_cycles) / len(bear_cycles)
            if bear_cycles else 0
        )

        return {
            "total_cycles": len(cycles),
            "bull_count": len(bull_cycles),
            "bear_count": len(bear_cycles),
            "oscillation_count": len(oscillation_cycles),
            "avg_bull_days": int(avg_bull_days),
            "avg_bear_days": int(avg_bear_days),
            "avg_bull_change": round(avg_bull_change, 2),
            "avg_bear_change": round(avg_bear_change, 2),
            "max_bull_change": max((c["change_pct"] for c in bull_cycles), default=0),
            "min_bear_change": min((c["change_pct"] for c in bear_cycles), default=0),
        }

    def print_cycles(self, cycles: List[Dict[str, Any]], index_name: str = "上证指数") -> None:
        """打印周期列表（用于验证）

        Args:
            cycles: 周期列表
            index_name: 指数名称
        """
        if not cycles:
            print(f"\n{index_name}: 无有效周期")
            return

        print(f"\n{'=' * 70}")
        print(f"{index_name} 牛熊周期列表")
        print(f"{'=' * 70}")

        for i, cycle in enumerate(cycles, 1):
            type_icon = "📈" if cycle["type"] == "牛市" else "📉" if cycle["type"] == "熊市" else "📊"
            print(f"\n{i}. {cycle['start_date']} ~ {cycle['end_date']}: {type_icon} {cycle['type']}")
            print(f"   涨跌幅: {cycle['change_pct']:+.2f}%")
            print(f"   持续天数: {cycle['duration_days']} 天")
            print(f"   峰值: {cycle['peak_price']:.2f} ({cycle['peak_date']})")
            print(f"   谷值: {cycle['trough_price']:.2f} ({cycle['trough_date']})")

        # 打印统计摘要
        summary = self.get_cycle_summary(cycles)
        print(f"\n{'=' * 70}")
        print("统计摘要:")
        print(f"  牛市周期: {summary['bull_count']} 个, 平均持续 {summary['avg_bull_days']} 天")
        print(f"  熊市周期: {summary['bear_count']} 个, 平均持续 {summary['avg_bear_days']} 天")
        print(f"  震荡周期: {summary['oscillation_count']} 个")
        print(f"  牛市平均涨幅: {summary['avg_bull_change']:+.2f}%")
        print(f"  熊市平均跌幅: {summary['avg_bear_change']:+.2f}%")
        print(f"{'=' * 70}")