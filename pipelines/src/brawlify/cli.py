"""`brawlify <command>`: the single entry point. Nothing imports this module."""

import argparse

from brawlify.core.dump import Dump


def cmd_fetch(args: argparse.Namespace) -> None:
    from brawlify.fetch.run import run

    run(full=args.full)


def cmd_derive(args: argparse.Namespace) -> None:
    from brawlify.derive.pipeline import DEFAULT_LOCALES, run

    run(args.locales or DEFAULT_LOCALES)


def cmd_review(args: argparse.Namespace) -> None:
    from brawlify.core import log
    from brawlify.tools import review

    log.header("check" if args.check else "review", args.brawler or "all brawlers")
    if args.check:
        review.check()
    else:
        review.generate(args.brawler, args.positional)


def cmd_trace(args: argparse.Namespace) -> None:
    from brawlify.tools.trace import trace

    trace(args.desc_tid, args.token)


def cmd_coverage(args: argparse.Namespace) -> None:
    from brawlify.tools.coverage import report

    report()


def cmd_check_texts(args: argparse.Namespace) -> None:
    from brawlify.tools import check_texts

    for locale in args.locales or check_texts.generated_locales():
        check_texts.audit(locale)


def cmd_literals(args: argparse.Namespace) -> None:
    from brawlify.tools import literals

    if args.action == "list":
        literals.list_entries()
    elif args.action == "check":
        literals.check()
    elif args.action == "set":
        literals.set_value(args.card, args.token, args.number, args.why)
    else:
        literals.scale(args.card, args.token, args.number, args.why)


def parser() -> argparse.ArgumentParser:
    locales = Dump().locales()
    root = argparse.ArgumentParser(
        prog="brawlify", description="BrawlAPI dump fetcher and reference-layer builder."
    )
    commands = root.add_subparsers(dest="command", required=True)

    fetch = commands.add_parser("fetch", help="download the BrawlAPI dump into data/raw/brawlify/")
    fetch.add_argument("--full", action="store_true", help="ignore stored ETags")
    fetch.set_defaults(run=cmd_fetch)

    derive = commands.add_parser("derive", help="build data/reference/ and data/build/brawlify/ from data/raw/brawlify/")
    derive.add_argument(
        "locales", nargs="*", choices=locales, metavar="LOCALE", help="default: fr en"
    )
    derive.set_defaults(run=cmd_derive)

    review = commands.add_parser("review", help="write pipelines/inputs/brawlify/review/<brawler>.txt, or --check them")
    review.add_argument("brawler", nargs="?", default="", help="only brawlers matching this")
    review.add_argument("--positional", action="store_true", help="only <VALUEn> slots")
    review.add_argument("--check", action="store_true", help="compare answers to the pipeline")
    review.set_defaults(run=cmd_review)

    trace = commands.add_parser("trace", help="replay one token segment by segment")
    trace.add_argument("desc_tid")
    trace.add_argument("token", help="a path without the <! > wrapper, or VALUE1")
    trace.set_defaults(run=cmd_trace)

    coverage = commands.add_parser("coverage", help="token coverage over the whole corpus")
    coverage.set_defaults(run=cmd_coverage)

    check_texts = commands.add_parser("check-texts", help="count raw tokens left in served texts")
    check_texts.add_argument("locales", nargs="*", choices=locales, metavar="LOCALE")
    check_texts.set_defaults(run=cmd_check_texts)

    literals = commands.add_parser("literals", help="manage literals.json")
    actions = literals.add_subparsers(dest="action", required=True)
    actions.add_parser("list")
    actions.add_parser("check")
    for action, number in (("set", "value"), ("scale", "factor")):
        sub = actions.add_parser(action)
        sub.add_argument("card")
        sub.add_argument("token")
        sub.add_argument("number", type=float, metavar=number)
        sub.add_argument("--why")
    literals.set_defaults(run=cmd_literals)
    return root


def main() -> None:
    args = parser().parse_args()
    args.run(args)
