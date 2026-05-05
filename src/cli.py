"""Trading Agent CLI - 命令行界面"""

import argparse
import json
import sys
from datetime import datetime

from src.core.logger import logger
from src.workflows.market_analysis import run_market_analysis
from src.workflows.stock_analysis import run_stock_analysis
from src.scheduler.task_queue import task_queue
from src.scheduler.workspace_manager import list_all_tasks, get_task_folder_by_id, get_task_detail


def cli_query(args):
    """AI 自然语言查询"""
    from src.query.ai_query import get_service

    print("=" * 60)
    print("AI 智能查询")
    print("=" * 60)
    print(f"问题: {args.query}\n")

    try:
        service = get_service()
        result = service.query(args.query)

        if not result.get("success"):
            print(f"\n查询失败: {result.get('error', '未知错误')}")
            sys.exit(1)

        # 显示 AI 解释
        intent = result.get("intent", {})
        print(f"AI 理解: {intent.get('explanation', '')}\n")

        # 显示结果
        stocks = result.get("data", {}).get("stocks", [])
        count = result.get("data", {}).get("count", 0)

        print(f"查询结果: 共 {count} 只股票\n")

        if stocks:
            print("代码      名称            行业        涨幅     5日涨幅  20日涨幅  换手率")
            print("-" * 70)
            for s in stocks[:20]:
                print(
                    f"{s['code']:8} {s['name']:12} "
                    f"{s.get('industry', '未知')[:8]:8} "
                    f"{s.get('change_pct', 0):>6.2f}% "
                    f"{s.get('change_5d', 0):>6.2f}% "
                    f"{s.get('change_20d', 0):>6.2f}% "
                    f"{s.get('turnover', 0):>6.2f}%"
                )

        # 显示 AI 回答
        print(f"\n{result.get('response', '')}")

        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"\n结果已保存到: {args.output}")

    except Exception as e:
        print(f"\n查询失败: {e}")
        logger.error(f"AI 查询失败: {e}")
        sys.exit(1)


def cli_template_query(args):
    """模板查询（快速查询）"""
    from src.query import get_engine

    print("=" * 60)
    print("模板查询")
    print("=" * 60)

    engine = get_engine()

    # 构建参数
    params = {}
    if args.threshold:
        params["threshold"] = args.threshold
    if args.n:
        params["n"] = args.n

    try:
        result = engine.query(args.template, **params)

        if "error" in result:
            print(f"\n查询失败: {result['error']}")
            sys.exit(1)

        print(f"\n{result.get('name', args.template)}: {result.get('count', 0)} 只\n")

        stocks = result.get("stocks", [])
        if stocks:
            print("代码      名称            涨幅     换手率    流通市值")
            print("-" * 50)
            for s in stocks[:args.n or 20]:
                circ_mv = s.get("circ_mv", 0)
                circ_str = f"{circ_mv/1e8:.1f}亿" if circ_mv > 1e8 else f"{circ_mv/1e4:.1f}万"
                print(
                    f"{s['code']:8} {s['name']:12} "
                    f"{s.get('change_pct', 0):>6.2f}% "
                    f"{s.get('turnover_rate', 0):>6.2f}% "
                    f"{circ_str:>8}"
                )

        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)

    except Exception as e:
        print(f"\n查询失败: {e}")
        sys.exit(1)


def cli_market_stats(args):
    """市场统计"""
    from src.query import get_engine

    engine = get_engine()
    stats = engine.get_market_stats()

    print("=" * 60)
    print("市场统计")
    print("=" * 60)
    print(f"日期: {stats.get('date', '')}\n")

    print(f"总股票数: {stats.get('total', 0)}")
    print(f"上涨家数: {stats.get('up_count', 0)} ({stats.get('up_ratio', 0):.1f}%)")
    print(f"下跌家数: {stats.get('down_count', 0)}")
    print(f"平盘家数: {stats.get('flat_count', 0)}")
    print(f"涨停家数: {stats.get('limit_up_count', 0)}")
    print(f"跌停家数: {stats.get('limit_down_count', 0)}")


def cli_list_templates(args):
    """列出查询模板"""
    from src.query import get_template_list

    templates = get_template_list()

    print("=" * 60)
    print("查询模板列表")
    print("=" * 60)
    print(f"共 {len(templates)} 个模板\n")

    for t in templates:
        print(f"  {t['id']:15} - {t['name']}")
        print(f"                    {t['description']}")
        if t.get("params"):
            params_desc = ", ".join(
                [f"{k}={v.get('default')}" for k, v in t["params"].items()]
            )
            print(f"                    参数: {params_desc}")
        print()


def cli_market_analysis(args):
    """执行市场分析"""
    print("=" * 60)
    print("市场分析")
    print("=" * 60)
    print("正在分析A股市场形势...\n")

    try:
        result = run_market_analysis()

        print("\n" + "=" * 60)
        print("分析结果")
        print("=" * 60)

        print(f"\n市场形势: {result.get('market_sentiment', 'N/A')}")
        print(f"\n热点板块:")
        for i, sector in enumerate(result.get('hot_sectors', [])[:5], 1):
            print(f"  {i}. {sector.get('name', 'N/A')} - 潜力: {sector.get('potential', 'N/A')}")

        print(f"\n推荐个股:")
        for i, stock in enumerate(result.get('recommended_stocks', [])[:10], 1):
            print(f"  {i}. {stock.get('code', 'N/A')} {stock.get('name', 'N/A')} - {stock.get('reason', 'N/A')}")

        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"\n结果已保存到: {args.output}")

    except Exception as e:
        print(f"\n分析失败: {e}")
        logger.error(f"市场分析失败: {e}")
        sys.exit(1)


def cli_stock_analysis(args):
    """执行股票分析"""
    stock_codes = args.codes.split(',')
    current_position = args.position or 0

    print("=" * 60)
    print("股票分析")
    print("=" * 60)
    print(f"股票代码: {stock_codes}")
    print(f"当前持仓: {current_position} 元\n")

    if len(stock_codes) == 1:
        try:
            result = run_stock_analysis(stock_codes[0], current_position)

            print_stock_result(result)

            if args.output:
                with open(args.output, 'w', encoding='utf-8') as f:
                    json.dump(result, f, ensure_ascii=False, indent=2)
                print(f"\n结果已保存到: {args.output}")

        except Exception as e:
            print(f"\n分析失败: {e}")
            logger.error(f"股票分析失败: {e}")
            sys.exit(1)
    else:
        print("批量分析模式...\n")
        results = {}
        for code in stock_codes:
            print(f"\n分析 {code}...")
            try:
                results[code] = run_stock_analysis(code, current_position)
                print_stock_result(results[code], brief=True)
            except Exception as e:
                print(f"  分析失败: {e}")
                results[code] = {"error": str(e)}

        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            print(f"\n所有结果已保存到: {args.output}")


def print_stock_result(result: dict, brief: bool = False):
    """打印股票分析结果"""
    print("\n" + "-" * 60)

    if brief:
        decision = result.get('final_decision', {})
        print(f"决策: {decision.get('decision', 'N/A')}")
        print(f"建议: {result.get('suggested_action', 'N/A')}")
        print(f"金额: {result.get('suggested_amount', 0)} 元")
    else:
        print("基本面分析:")
        fundamentals = result.get('fundamentals', {})
        print(f"  评分: {fundamentals.get('score', 'N/A')}")
        print(f"  优势: {fundamentals.get('strengths', [])}")
        print(f"  劣势: {fundamentals.get('weaknesses', [])}")

        print("\n技术面分析:")
        technical = result.get('technical', {})
        print(f"  评分: {technical.get('score', 'N/A')}")
        print(f"  趋势: {technical.get('trend', 'N/A')}")
        print(f"  买入信号: {technical.get('buy_signal', False)}")
        print(f"  卖出信号: {technical.get('sell_signal', False)}")

        print("\n辩论历史:")
        for i, history in enumerate(result.get('debate_history', [])[-6:], 1):
            print(f"  {i}. {history[:100]}...")

        print("\n最终决策:")
        decision = result.get('final_decision', {})
        print(f"  决策: {decision.get('decision', 'N/A')}")
        print(f"  置信度: {decision.get('confidence', 0)}")
        print(f"  理由: {decision.get('reason', 'N/A')}")

        print("\n持仓建议:")
        print(f"  操作: {result.get('suggested_action', 'N/A')}")
        print(f"  金额: {result.get('suggested_amount', 0)} 元")
        print(f"  风险提示: {result.get('risk_warnings', [])}")

    print("-" * 60)


def cli_list_tasks(args):
    """列出任务"""
    tasks = list_all_tasks()

    print("=" * 60)
    print("任务列表")
    print("=" * 60)
    print(f"共 {len(tasks)} 个任务\n")

    for i, task in enumerate(tasks[:20], 1):
        status_emoji = {
            "pending": "⏳",
            "running": "🔄",
            "completed": "✅",
            "failed": "❌"
        }.get(task["status"], "❓")

        print(f"{i}. [{status_emoji}] {task['folder_name']}")
        print(f"   类型: {task['task_type']}")
        print(f"   状态: {task['status']}")
        if task['created_at']:
            print(f"   创建: {task['created_at'][:19]}")
        print()


def cli_show_task(args):
    """显示任务详情"""
    folder = get_task_folder_by_id(args.task_id)

    if not folder:
        print(f"任务不存在: {args.task_id}")
        sys.exit(1)

    task = get_task_detail(folder)

    print("=" * 60)
    print("任务详情")
    print("=" * 60)
    print(f"任务ID: {task['task_id']}")
    print(f"文件夹: {task['folder_name']}")
    print(f"类型: {task['task_type']}")
    print(f"状态: {task['status']}")
    if task['created_at']:
        print(f"创建时间: {task['created_at']}")

    if task['stocks']:
        print(f"股票列表: {task['stocks']}")

    if task['result']:
        print("\n分析结果:")
        if task['task_type'] == "market_analysis":
            print_market_result(task['result'])
        else:
            print_stock_result(task['result'])

    print("\n执行日志:")
    for i, log in enumerate(task['logs'][:20], 1):
        print(f"  {i}. {log}")

    if task['summary']:
        print("\n摘要:")
        if isinstance(task['summary'], list):
            for item in task['summary']:
                print(f"  {item.get('code', 'N/A')}: {item.get('decision', item.get('error', 'N/A'))}")
        else:
            for k, v in task['summary'].items():
                print(f"  {k}: {v}")


def print_market_result(result: dict):
    """打印市场分析结果"""
    print(f"市场形势: {result.get('market_sentiment', 'N/A')}")

    sectors = result.get('hot_sectors', [])
    if sectors:
        print("\n热点板块:")
        for i, s in enumerate(sectors[:5], 1):
            print(f"  {i}. {s.get('name', 'N/A')}")

    stocks = result.get('recommended_stocks', [])
    if stocks:
        print("\n推荐个股:")
        for i, s in enumerate(stocks[:10], 1):
            print(f"  {i}. {s.get('code', 'N/A')} {s.get('name', 'N/A')}")


def cli_web(args):
    """启动 Web 服务"""
    import uvicorn
    from src.web.app import app

    host = args.host or "127.0.0.1"
    port = args.port or 8000

    print(f"启动 Web 服务: http://{host}:{port}")
    print("按 Ctrl+C 停止服务\n")

    uvicorn.run(app, host=host, port=port)


def cli_update_data(args):
    """更新股票数据"""
    from src.data.update_stock_daily import update_all_stocks, update_specific_stocks

    if args.all:
        print("警告：更新所有股票数据将需要较长时间（约 5500 个股票）")
        print("建议使用 --batch-size 和 --delay 参数控制速度")
        print()

        update_all_stocks(
            end_date=args.end_date,
            batch_size=args.batch_size,
            delay=args.delay
        )
    elif args.codes:
        update_specific_stocks(args.codes, args.end_date)
    else:
        print("请指定 --all 或 --codes")


def cli_trend(args):
    """显示市场趋势分析"""
    from src.data.index_daily import get_market_overview, analyze_market_trend

    if args.code:
        # 分析单个指数
        trend = analyze_market_trend(args.code)
        if 'status' not in trend or trend['status'] == 'unknown':
            print(f"无法获取指数 {args.code} 数据")
            sys.exit(1)

        print("=" * 70)
        print(f"{trend['name']} ({trend['code']}) 趋势分析")
        print("=" * 70)

        # 历史数据概览
        print(f"\n【历史数据概览】")
        print(f"数据范围: {trend['earliest_date']} ~ {trend['latest_date']} ({trend['total_days']} 天)")
        print(f"历史最高: {trend['hist_high']:.2f} ({trend['hist_high_date']})")
        print(f"历史最低: {trend['hist_low']:.2f} ({trend['hist_low_date']})")
        print(f"当前回撤: {trend['drawdown_from_high']:.2f}% (距离历史最高)")

        # 当前行情
        print(f"\n【当前行情】")
        print(f"当前价: {trend['price']:.2f}")
        print(f"MA5: {trend['ma5']:.2f}, MA10: {trend['ma10']:.2f}, MA20: {trend['ma20']:.2f}, MA60: {trend['ma60']:.2f}")

        # 近期涨跌
        print(f"\n【近期涨跌】")
        print(f"近5日: {trend['recent_5d_pct']:.2f}%")
        print(f"近20日: {trend['recent_20d_pct']:.2f}%")
        print(f"近60日: {trend['recent_60d_pct']:.2f}%")
        print(f"近250日(一年): {trend.get('recent_250d_pct', 0):.2f}%")

        # 市场状态
        print(f"\n【市场状态】")
        print(f"状态: {trend['status']}")
        print(f"趋势强度: {trend['trend_strength']}")
        print(f"成交量比率: {trend['vol_ratio']:.2f}")
        print("\n信号:")
        for signal in trend['signals']:
            print(f"  - {signal}")

        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(trend, f, ensure_ascii=False, indent=2)
            print(f"\n结果已保存到: {args.output}")

    else:
        # 显示市场整体概览
        overview = get_market_overview()

        print("=" * 70)
        print("A股市场整体趋势")
        print("=" * 70)
        print(f"市场状态: {overview['overall_status']}")
        print(f"趋势强度: {overview['overall_strength']:.1f}")
        print(f"投资建议: {overview['recommendation']}")
        print("=" * 70)

        for code, trend in overview['indices'].items():
            if 'status' not in trend or trend['status'] == 'unknown':
                continue
            print(f"\n{trend['name']} ({code}):")
            print(f"  数据范围: {trend['earliest_date']} ~ {trend['latest_date']}")
            print(f"  当前价: {trend['price']:.2f} (距历史最高 {trend['drawdown_from_high']:.1f}%)")
            print(f"  历史最高: {trend['hist_high']:.2f} ({trend['hist_high_date']})")
            print(f"  MA5/20/60: {trend['ma5']:.0f}/{trend['ma20']:.0f}/{trend['ma60']:.0f}")
            print(f"  近20日涨跌: {trend['recent_20d_pct']:.2f}%")
            print(f"  近一年涨跌: {trend.get('recent_250d_pct', 0):.2f}%")
            print(f"  状态: {trend['status']}")
            for signal in trend['signals']:
                print(f"  - {signal}")

        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(overview, f, ensure_ascii=False, indent=2)
            print(f"\n结果已保存到: {args.output}")


def cli_update_index(args):
    """更新指数日线数据"""
    from src.data.index_daily import update_all_index_daily, get_index_daily_akshare, save_index_daily

    full_history = not args.recent  # 默认获取全部历史，除非指定 --recent

    if args.all:
        if full_history:
            print("更新所有主要指数全部历史数据...")
        else:
            print(f"更新所有主要指数最近 {args.days} 天数据...")
        update_all_index_daily(full_history=full_history, days=args.days)
        print("更新完成")
    elif args.code:
        print(f"更新指数 {args.code} 日线数据...")
        df = get_index_daily_akshare(args.code, full_history=full_history, days=args.days)
        if df is not None:
            save_index_daily(args.code, df)
            print(f"更新成功: {len(df)} 条数据 ({df.iloc[0]['date']} ~ {df.iloc[-1]['date']})")
        else:
            print(f"更新失败")
    else:
        print("请指定 --all 或 --code")


def cli_backtest(args):
    """自然语言回测命令"""
    from src.backtest import BacktestRunner

    print("=" * 70)
    print("自然语言回测")
    print("=" * 70)


def cli_stock_info(args):
    """股票信息查询"""
    from src.data.collectors.stock_info_collector import StockInfoCollector
    from pathlib import Path

    collector = StockInfoCollector()
    code = args.code

    # 检查是否已有缓存数据
    stock_dir = Path(f"data/stock_info/{code}")
    cache_file = stock_dir / "full_info.json"

    use_cache = cache_file.exists() and not args.refresh

    if use_cache:
        print("=" * 70)
        print(f"股票信息（缓存）")
        print("=" * 70)
        print(f"股票代码: {code}\n")

        data = collector.load(code)
        if not data:
            print("缓存数据损坏，重新获取...")
            use_cache = False

    if not use_cache:
        print("=" * 70)
        print(f"股票信息（实时获取）")
        print("=" * 70)
        print(f"股票代码: {code}")
        print(f"查询范围: {args.days} 天\n")

        data = collector.collect_all(code, days=args.days)
        collector.save(code, data)

    # 打印基本信息
    basic = data.get("basic", {})
    print("【基本信息】")
    print(f"  名称: {basic.get('name', 'N/A')}")
    print(f"  行业: {basic.get('industry', 'N/A')}")
    market_cap = basic.get('market_cap', 0)
    if market_cap:
        print(f"  市值: {market_cap/1e8:.1f} 亿元")

    # 打印实时行情
    market = data.get("market", {})
    realtime = market.get("realtime", {})
    if realtime:
        print("\n【实时行情】")
        price = realtime.get('price', 0)
        change = realtime.get('change_pct', 0)
        print(f"  最新价: {price:.2f} 元")
        print(f"  涨跌幅: {change:.2f}%")
        if realtime.get('high'):
            print(f"  最高: {realtime.get('high', 0):.2f}")
        if realtime.get('low'):
            print(f" 最低: {realtime.get('low', 0):.2f}")
        if realtime.get('volume'):
            vol = realtime.get('volume', 0)
            print(f"  成交量: {vol/1e4:.0f} 万手")

    # 打印估值数据
    financial = data.get("financial", {})
    valuation = financial.get("valuation", {})
    indicators = financial.get("indicators", {})

    # 如果 valuation 有数据，优先使用
    if valuation and valuation.get("pe_ttm"):
        print("\n【估值数据】")
        print(f"  PE(TTM): {valuation.get('pe_ttm', 0):.2f}")
        print(f"  PB: {valuation.get('pb', 0):.2f}")
        print(f"  PS(TTM): {valuation.get('ps_ttm', 0):.2f}")
        print(f"  股息率: {valuation.get('dv_ratio', 0):.2f}%")
    # 否则检查 indicators 是否有估值数据
    elif indicators and indicators.get("pe_ttm"):
        print("\n【估值数据】")
        pe = indicators.get('pe_ttm')
        if pe and pe > 0:
            print(f"  PE(TTM): {pe:.2f}")
        pb = indicators.get('pb')
        if pb and pb > 0:
            print(f"  PB: {pb:.2f}")
        ps = indicators.get('ps_ttm')
        if ps and ps > 0:
            print(f"  PS(TTM): {ps:.2f}")
        dv = indicators.get('dividend_ratio')
        if dv and dv > 0:
            print(f"  股息率: {dv:.2f}%")

    # 财务指标（ROE、毛利率等）
    if indicators:
        roe = indicators.get('roe', 0)
        gross_margin = indicators.get('gross_profit_margin', 0)
        net_margin = indicators.get('net_profit_margin', 0)
        if roe or gross_margin or net_margin:
            print("\n【财务指标】")
            if roe:
                print(f"  ROE: {roe:.2f}%")
            if gross_margin:
                print(f"  毛利率: {gross_margin:.2f}%")
            if net_margin:
                print(f"  净利率: {net_margin:.2f}%")

    # 打印近期新闻
    news = data.get("news", {})
    if news and news.get("count", 0) > 0:
        print("\n【近期新闻】")
        print(f"  共 {news.get('count', 0)} 条新闻")
        latest = news.get("latest", [])
        for i, item in enumerate(latest[:5], 1):
            title = item.get('title', '')
            # 截断过长的标题
            if len(title) > 50:
                title = title[:50] + "..."
            print(f"  {i}. {title}")
            print(f"     时间: {item.get('publish_time', 'N/A')}")

    # 打印板块归属
    sectors = data.get("sectors", [])
    if sectors:
        print("\n【板块归属】")
        sector_names = [s.get('name', '') for s in sectors[:5]]
        print(f"  {', '.join(sector_names)}")

    # 打印更新时间
    print(f"\n【数据时间】")
    print(f"  收集时间: {data.get('collect_time', 'N/A')}")
    print(f"  数据范围: {data.get('data_range_days', 0)} 天")

    # 保存输出
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"\n完整数据已保存到: {args.output}")

    print("=" * 70)


def cli_backtest(args):
    """自然语言回测命令"""
    from src.backtest import BacktestRunner

    print("=" * 70)
    print("自然语言回测")
    print("=" * 70)

    runner = BacktestRunner()

    # 列出已生成的策略
    if args.list:
        strategies = runner.list_saved_strategies()
        print(f"\n已保存的策略: {len(strategies)} 个\n")
        for s in strategies:
            print(f"  - {s}")
        return

    # 使用已保存的策略
    if args.strategy:
        print(f"\n使用策略: {args.strategy}")
        result = runner.run_from_saved_strategy(
            strategy_name=args.strategy,
            start_date=args.start,
            end_date=args.end,
            initial_capital=args.capital,
        )
    else:
        # 自然语言描述
        if not args.description:
            print("请提供策略描述或使用 --strategy 指定已保存的策略")
            print("示例: trading-agent backtest \"涨停板策略，止盈8%，止损3%\"")
            sys.exit(1)

        print(f"\n策略描述: {args.description}")
        result = runner.run_from_description(
            description=args.description,
            start_date=args.start,
            end_date=args.end,
            initial_capital=args.capital,
            save_strategy_code=args.save,
        )

    # 显示结果
    if result.get("success"):
        summary = result.get("summary", {})
        print("\n" + "=" * 70)
        print("回测结果")
        print("=" * 70)
        print(f"总收益率: {summary.get('total_return', 0):.2f}%")
        print(f"年化收益: {summary.get('annual_return', 0):.2f}%")
        print(f"最大回撤: {summary.get('max_drawdown', 0):.2f}%")
        print(f"胜率: {summary.get('win_rate', 0):.2f}%")
        print(f"总交易次数: {summary.get('total_trades', 0)}")

        if args.output:
            import json
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"\n结果已保存到: {args.output}")
    else:
        print(f"\n回测失败: {result.get('error', '未知错误')}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Trading Agent - A股交易辅助系统",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # AI 自然语言查询
  trading-agent query "涨幅超过5%的银行股"
  trading-agent query "最近一周上涨的科技股" -o result.json

  # 模板查询
  trading-agent tpl limit_up
  trading-agent tpl high_turnover --threshold 15
  trading-agent tpl top_gainers --n 30

  # 市场统计
  trading-agent stats

  # 查询模板列表
  trading-agent templates

  # 股票信息查询
  trading-agent info 603629
  trading-agent info 603773 --days 30 --refresh
  trading-agent info 000001 -o stock_data.json

  # 市场趋势分析（判断牛熊市）
  trading-agent trend
  trading-agent trend --code 000001

  # 市场分析
  trading-agent market

  # 分析单个股票
  trading-agent stock 000001

  # 分析多个股票（持仓1万元）
  trading-agent stock 000001,600000 --position 10000

  # 启动 Web 服务
  trading-agent web --port 8080

  # 查看任务列表
  trading-agent tasks

  # 查看任务详情
  trading-agent task <task_id>

  # 更新单个股票数据
  trading-agent update --codes 600036 000001

  # 更新所有股票数据（慎用，耗时较长）
  trading-agent update --all --batch-size 100 --delay 1.0

  # 更新指数日线数据
  trading-agent update-index --all
  trading-agent update-index --code 000001 --days 250

  # 自然语言回测
  trading-agent backtest "涨停板追涨策略，止盈8%，止损3%，非熊市参与"
  trading-agent backtest "..." --start 2020-01-01 --capital 100000 --save

  # 使用已保存的策略
  trading-agent backtest --strategy limit_up_strategy

  # 列出已保存的策略
  trading-agent backtest --list
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='可用命令')

    # AI 查询命令
    query_parser = subparsers.add_parser('query', help='AI 自然语言查询')
    query_parser.add_argument('query', help='自然语言查询问题')
    query_parser.add_argument('-o', '--output', help='保存结果到文件 (JSON)')
    query_parser.set_defaults(func=cli_query)

    # 模板查询命令
    tpl_parser = subparsers.add_parser('tpl', help='模板快速查询')
    tpl_parser.add_argument('template', help='模板ID（如 limit_up, high_turnover）')
    tpl_parser.add_argument('--threshold', type=float, help='阈值参数')
    tpl_parser.add_argument('--n', type=int, help='返回数量')
    tpl_parser.add_argument('-o', '--output', help='保存结果到文件 (JSON)')
    tpl_parser.set_defaults(func=cli_template_query)

    # 市场统计命令
    stats_parser = subparsers.add_parser('stats', help='市场涨跌统计')
    stats_parser.set_defaults(func=cli_market_stats)

    # 模板列表命令
    templates_parser = subparsers.add_parser('templates', help='查询模板列表')
    templates_parser.set_defaults(func=cli_list_templates)

    # 市场分析命令
    market_parser = subparsers.add_parser('market', help='市场分析')
    market_parser.add_argument('-o', '--output', help='保存结果到文件 (JSON)')
    market_parser.set_defaults(func=cli_market_analysis)

    # 股票分析命令
    stock_parser = subparsers.add_parser('stock', help='股票分析')
    stock_parser.add_argument('codes', help='股票代码（多个用逗号分隔）')
    stock_parser.add_argument('-p', '--position', type=float, help='当前持仓金额')
    stock_parser.add_argument('-o', '--output', help='保存结果到文件 (JSON)')
    stock_parser.set_defaults(func=cli_stock_analysis)

    # Web 服务命令
    web_parser = subparsers.add_parser('web', help='启动 Web 服务')
    web_parser.add_argument('--host', default='127.0.0.1', help='服务地址')
    web_parser.add_argument('--port', type=int, default=8000, help='服务端口')
    web_parser.set_defaults(func=cli_web)

    # 任务列表命令
    tasks_parser = subparsers.add_parser('tasks', help='查看任务列表')
    tasks_parser.set_defaults(func=cli_list_tasks)

    # 任务详情命令
    task_parser = subparsers.add_parser('task', help='查看任务详情')
    task_parser.add_argument('task_id', help='任务ID')
    task_parser.set_defaults(func=cli_show_task)

    # 数据更新命令
    update_parser = subparsers.add_parser('update', help='更新股票日线数据')
    update_parser.add_argument('--all', action='store_true', help='更新所有股票')
    update_parser.add_argument('--codes', nargs='+', help='指定股票代码（如 600036 000001）')
    update_parser.add_argument('--end-date', help='结束日期 YYYYMMDD（默认今天）')
    update_parser.add_argument('--batch-size', type=int, default=50, help='每批次数量')
    update_parser.add_argument('--delay', type=float, default=0.5, help='批次间隔秒数')
    update_parser.set_defaults(func=cli_update_data)

    # 市场趋势命令
    trend_parser = subparsers.add_parser('trend', help='市场趋势分析（判断牛熊市）')
    trend_parser.add_argument('--code', help='指定指数代码（如 000001），默认显示整体')
    trend_parser.add_argument('-o', '--output', help='保存结果到文件 (JSON)')
    trend_parser.set_defaults(func=cli_trend)

    # 指数数据更新命令
    idx_parser = subparsers.add_parser('update-index', help='更新指数日线数据')
    idx_parser.add_argument('--all', action='store_true', help='更新所有主要指数')
    idx_parser.add_argument('--code', help='指定指数代码')
    idx_parser.add_argument('--days', type=int, default=120, help='获取天数（仅当 --recent 时有效）')
    idx_parser.add_argument('--recent', action='store_true', help='只获取最近数据（默认获取全部历史）')
    idx_parser.set_defaults(func=cli_update_index)

    # 回测命令
    backtest_parser = subparsers.add_parser('backtest', help='自然语言回测策略')
    backtest_parser.add_argument('description', nargs='?', help='自然语言策略描述')
    backtest_parser.add_argument('--strategy', help='使用已保存的策略名称')
    backtest_parser.add_argument('--start', default='2020-01-01', help='开始日期')
    backtest_parser.add_argument('--end', help='结束日期（默认今天）')
    backtest_parser.add_argument('--capital', type=float, default=100000, help='初始资金')
    backtest_parser.add_argument('--save', action='store_true', help='保存生成的策略代码')
    backtest_parser.add_argument('--list', action='store_true', help='列出已保存的策略')
    backtest_parser.add_argument('-o', '--output', help='保存结果到文件 (JSON)')
    backtest_parser.set_defaults(func=cli_backtest)

    # 股票信息查询命令
    info_parser = subparsers.add_parser('info', help='股票信息查询')
    info_parser.add_argument('code', help='股票代码（如 603629）')
    info_parser.add_argument('--days', type=int, default=90, help='查询天数（默认90天）')
    info_parser.add_argument('--refresh', action='store_true', help='强制重新获取（忽略缓存）')
    info_parser.add_argument('-o', '--output', help='保存完整数据到文件 (JSON)')
    info_parser.set_defaults(func=cli_stock_info)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    args.func(args)


if __name__ == '__main__':
    main()