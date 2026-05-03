"""Trading Agent CLI - 命令行界面"""

import argparse
import json
import sys
from datetime import datetime

from trading_agent.core.logger import logger
from trading_agent.workflows.market_analysis import run_market_analysis
from trading_agent.workflows.stock_analysis import run_stock_analysis
from trading_agent.scheduler.task_queue import task_queue
from trading_agent.scheduler.workspace_manager import list_all_tasks, get_task_folder_by_id, get_task_detail


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
    from trading_agent.web.app import app

    host = args.host or "127.0.0.1"
    port = args.port or 8000

    print(f"启动 Web 服务: http://{host}:{port}")
    print("按 Ctrl+C 停止服务\n")

    uvicorn.run(app, host=host, port=port)


def cli_update_data(args):
    """更新股票数据"""
    from trading_agent.data_sources.update_stock_daily import update_all_stocks, update_specific_stocks

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


def main():
    parser = argparse.ArgumentParser(
        description="Trading Agent - A股交易辅助系统",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
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
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='可用命令')

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

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    args.func(args)


if __name__ == '__main__':
    main()