"""Click CLI for Note Watcher.

Provides two commands:
- `watch`: Starts the file watcher daemon
- `process`: Batch processes all pending instructions
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import click

from note_watcher.config import load_config
from note_watcher.dispatcher import AgentDispatcher
from note_watcher.watcher import process_file_reparse, start_watcher


def setup_logging(verbose: bool = False) -> None:
    """Configure logging to stdout/stderr."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stderr,
    )


@click.group()
@click.option("--verbose", "-v", is_flag=True, help="Enable debug logging.")
def main(verbose: bool) -> None:
    """Note Watcher - Detect @ mentions in Obsidian notes and dispatch to AI agents."""
    setup_logging(verbose)


@main.command()
@click.option(
    "--vault",
    type=click.Path(exists=True, file_okay=False, resolve_path=True),
    help="Path to the Obsidian vault directory.",
)
@click.option(
    "--config",
    "config_path",
    type=click.Path(exists=True, dir_okay=False, resolve_path=True),
    help="Path to the configuration file.",
)
def watch(vault: str | None, config_path: str | None) -> None:
    """Start the file watcher daemon.

    Monitors the vault directory for changes to .md files and processes
    @ mention instructions as they appear.
    """
    config = load_config(config_path)

    if vault:
        config.vault = Path(vault)

    if not config.vault.is_dir():
        click.echo(f"Error: Vault directory does not exist: {config.vault}", err=True)
        sys.exit(1)

    click.echo(f"Watching vault: {config.vault}")
    start_watcher(config)


@main.command()
@click.option(
    "--all",
    "process_all",
    is_flag=True,
    required=True,
    help="Process all pending instructions.",
)
@click.option(
    "--vault",
    type=click.Path(exists=True, file_okay=False, resolve_path=True),
    help="Path to the Obsidian vault directory.",
)
@click.option(
    "--config",
    "config_path",
    type=click.Path(exists=True, dir_okay=False, resolve_path=True),
    help="Path to the configuration file.",
)
def process(process_all: bool, vault: str | None, config_path: str | None) -> None:
    """Batch process all pending @ mention instructions.

    Scans all .md files in the vault for unprocessed instructions,
    dispatches them to configured agents, and writes results inline.
    """
    config = load_config(config_path)

    if vault:
        config.vault = Path(vault)

    if not config.vault.is_dir():
        click.echo(f"Error: Vault directory does not exist: {config.vault}", err=True)
        sys.exit(1)

    dispatcher = AgentDispatcher(config)
    vault_path = config.vault

    # Find all .md files
    md_files = sorted(vault_path.rglob("*.md"))
    total_processed = 0

    for md_file in md_files:
        count = process_file_reparse(str(md_file), dispatcher)
        if count > 0:
            click.echo(f"Processed {count} instruction(s) in {md_file}")
            total_processed += count

    click.echo(f"Done. Processed {total_processed} instruction(s) total.")
