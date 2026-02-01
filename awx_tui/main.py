"""
AWX TUI - Main Entry Point

Handles command-line arguments and application startup.
"""

import argparse
import os
import sys
from pathlib import Path

from awx_tui import ROTATING_NAMES, TAGLINE, __version__


def parse_args():
    """Parse command-line arguments"""
    parser = argparse.ArgumentParser(
        prog="awx-tui",
        description=f"{ROTATING_NAMES[0]} - {TAGLINE}",
        epilog="For more information, see https://github.com/ansible-community/awx-tui",
    )

    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    parser.add_argument("--mock", action="store_true", help="Run in mock mode (no real AWX connection, use test data)")

    parser.add_argument("--host", type=str, metavar="URL", help="AWX URL (e.g., https://awx.example.com)")

    parser.add_argument("--token", type=str, metavar="TOKEN", help="AWX API token (overrides config)")

    parser.add_argument("--user", type=str, metavar="USERNAME", help="AWX username (if using password auth)")

    parser.add_argument(
        "--password", type=str, metavar="PASSWORD", help="AWX password (not recommended, use token instead)"
    )

    parser.add_argument(
        "--no-verify-ssl", action="store_true", help="Disable SSL certificate verification (not recommended)"
    )

    parser.add_argument(
        "--dashboard",
        type=str,
        metavar="NAME",
        choices=["classic", "sleek"],
        help="Dashboard layout to use (classic or sleek)",
    )

    parser.add_argument(
        "--config", type=Path, metavar="PATH", help="Path to config file (default: ~/.config/awx-tui/config.yaml)"
    )

    parser.add_argument("--debug", action="store_true", help="Enable debug mode (verbose logging)")

    return parser.parse_args()


def main():
    """Main entry point"""
    try:
        args = parse_args()

        # Import app here
        from awx_tui.app import AWXTUIApp

        # Determine mock mode
        mock_mode = args.mock or os.environ.get("AWX_MOCK", "").lower() in ("true", "1", "yes")

        # Create and run app, passing CLI args separately
        app = AWXTUIApp(
            config_path=args.config,
            mock_mode=mock_mode,
            cli_args=args,  # Pass CLI args to create @cli-args instance if present
        )

        # Run app
        app.run()

        return 0

    except KeyboardInterrupt:
        print("\nExiting AWX TUI...")
        return 0
    except Exception as e:
        print(f"\n❌ Error starting AWX TUI: {e}", file=sys.stderr)
        print("\nTroubleshooting:", file=sys.stderr)
        print("  1. Check your configuration file: ~/.config/awx-tui/config.yaml", file=sys.stderr)
        print("  2. Ensure YAML syntax is valid", file=sys.stderr)
        print("  3. Try running with --mock flag to test: awx-tui --mock", file=sys.stderr)
        print("  4. Check logs for more details", file=sys.stderr)

        if args.debug:
            import traceback

            print("\nFull traceback:", file=sys.stderr)
            traceback.print_exc()

        return 1


if __name__ == "__main__":
    sys.exit(main())
