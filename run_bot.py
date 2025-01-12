from src.dependencies import check_dependencies
import argparse


def parse_args():
    parser = argparse.ArgumentParser(description="Run the bot with specified arguments.")
    parser.add_argument('-r', '--run-init', action='store_true', help='Run the script when the bot is starting.')
    return parser.parse_args()


def main():
    from src.bot import run
    
    args = parse_args()
    if args.run_init:
        run(True)
    else:
        run(False)


if __name__ == "__main__":
    check_dependencies()
    main()