#!/usr/bin/env python3
"""ADR enforcement proof of concept"""

import re
import subprocess
from pathlib import Path

import click
import yaml


@click.group()
def cli():
    """ADR enforcement tooling"""


@cli.command()
@click.option("--adr-dir", default="docs/adr", help="ADR directory")
@click.option("--output", default=".semgrep/adr-rules.yml", help="Output semgrep config")
def extract(adr_dir, output):
    """Extract semgrep rules from ADRs"""
    adr_path = Path(adr_dir)
    if not adr_path.exists():
        click.echo(f"Error: {adr_dir} does not exist", err=True)
        return

    all_rules = {"rules": []}

    for adr_file in sorted(adr_path.glob("*.md")):
        content = adr_file.read_text()

        # Check if Active
        if "## Status\nActive" not in content and "## Status\n\nActive" not in content:
            continue

        # Extract YAML block after ### Pattern or ### Patterns
        pattern_match = re.search(
            r"### Patterns?\s*\n```yaml\s*\n(.*?)\n```",
            content,
            re.DOTALL,
        )

        if pattern_match:
            yaml_content = pattern_match.group(1)
            try:
                parsed = yaml.safe_load(yaml_content)
                if "rules" in parsed:
                    all_rules["rules"].extend(parsed["rules"])
                    click.echo(f"✓ Extracted rules from {adr_file.name}")
            except yaml.YAMLError as e:
                click.echo(f"✗ YAML error in {adr_file.name}: {e}", err=True)

    if not all_rules["rules"]:
        click.echo("No rules extracted", err=True)
        return

    # Write output
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(yaml.dump(all_rules, sort_keys=False))
    click.echo(f"\n✓ Wrote {len(all_rules['rules'])} rules to {output}")


@cli.command()
@click.option("--target", default=".", help="Directory to scan")
@click.option("--config", default=".semgrep/adr-rules.yml", help="Semgrep config file")
def check(target, config):
    """Run semgrep with extracted rules"""
    config_path = Path(config)
    if not config_path.exists():
        click.echo(f"Error: {config} not found. Run 'extract' first.", err=True)
        return None

    click.echo(f"Running semgrep on {target}...")
    result = subprocess.run(
        ["semgrep", "--config", config, target, "--force-color"],
        check=False, capture_output=True,
        text=True,
    )

    click.echo(result.stdout)
    if result.stderr:
        click.echo(result.stderr, err=True)

    return result.returncode


@cli.command()
@click.option("--adr-dir", default="docs/adr", help="ADR directory")
@click.option("--target", default=".", help="Directory to scan")
def enforce(adr_dir, target):
    """Extract rules and check code"""
    ctx = click.get_current_context()

    # Extract
    ctx.invoke(extract, adr_dir=adr_dir)

    # Check
    exit_code = ctx.invoke(check, target=target)
    ctx.exit(exit_code or 0)


if __name__ == "__main__":
    cli()
