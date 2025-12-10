"""Infrastructure management CLI commands."""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import click


class MonorepoRootNotFoundError(Exception):
    """Raised when monorepo root cannot be found."""

    def __init__(self) -> None:
        """Initialize the MonorepoRootNotFoundError exception."""
        super().__init__("Could not find monorepo root directory")


def get_monorepo_root() -> Path:
    """Get the monorepo root directory."""
    # Start from this file and go up to find the root
    current = Path(__file__).resolve()
    while current.parent != current:
        if (current / "repoctl").exists() and (current / "infra").exists():
            return current
        current = current.parent
    raise MonorepoRootNotFoundError


def get_global_compose_file() -> Path:
    """Get path to global compose file."""
    return get_monorepo_root() / "infra" / "compose.global.yml"


def get_global_env_file() -> Path:
    """Get path to global env file."""
    return get_monorepo_root() / "infra" / ".env.global"


def get_project_infra_dir(project_name: str) -> Path:
    """Get path to project infrastructure directory."""
    return get_monorepo_root() / "backends" / project_name / "infra"


def run_docker_compose(compose_file: Path, env_file: Path | None, *args: str) -> int:
    """Run docker compose with the given arguments."""
    cmd = ["docker", "compose", "-f", str(compose_file)]
    if env_file and env_file.exists():
        cmd.extend(["--env-file", str(env_file)])
    cmd.extend(args)

    result = subprocess.run(cmd, check=False)
    return result.returncode


def ensure_global_env() -> None:
    """Ensure global .env file exists."""
    env_file = get_global_env_file()
    if not env_file.exists():
        click.secho("⚠", fg="yellow", nl=False)
        click.echo(f" Global .env file not found at {env_file}")
        click.echo("   Please create it with required configuration")
        sys.exit(1)


def ensure_network() -> None:
    """Ensure monorepo network exists."""
    result = subprocess.run(
        ["docker", "network", "inspect", "monorepo_net"],
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        click.secho("⚠", fg="yellow", nl=False)
        click.echo(" Network 'monorepo_net' not found. Creating...")
        subprocess.run(["docker", "network", "create", "monorepo_net"], check=True)
        click.secho("✓", fg="green", nl=False)
        click.echo(" Network created")


@click.group()
def infra() -> None:
    """Infrastructure management commands."""


@infra.group()
def global_cmd() -> None:
    """Manage global infrastructure (Redis, MinIO)."""


@global_cmd.command(name="start")
def global_start() -> None:
    """Start global infrastructure services."""
    click.secho("i", fg="blue", nl=False)
    click.echo(" Starting global infrastructure (Redis, MinIO)...")

    ensure_global_env()

    compose_file = get_global_compose_file()
    env_file = get_global_env_file()

    exit_code = run_docker_compose(compose_file, env_file, "up", "-d")

    if exit_code == 0:
        click.secho("✓", fg="green", nl=False)
        click.echo(" Global infrastructure started")
        click.echo("")
        click.secho("i", fg="blue", nl=False)
        click.echo(" Services available at:")
        click.echo("  - Redis: localhost:6379")
        click.echo("  - RedisInsight UI: http://localhost:5540")
        click.echo("  - MinIO API: http://localhost:9000")
        click.echo("  - MinIO Console: http://localhost:9001")
    else:
        click.secho("✗", fg="red", nl=False)
        click.echo(" Failed to start global infrastructure")
        sys.exit(exit_code)


@global_cmd.command(name="stop")
def global_stop() -> None:
    """Stop global infrastructure services."""
    click.secho("i", fg="blue", nl=False)
    click.echo(" Stopping global infrastructure...")

    compose_file = get_global_compose_file()
    env_file = get_global_env_file()

    exit_code = run_docker_compose(compose_file, env_file, "down")

    if exit_code == 0:
        click.secho("✓", fg="green", nl=False)
        click.echo(" Global infrastructure stopped")
    else:
        click.secho("✗", fg="red", nl=False)
        click.echo(" Failed to stop global infrastructure")
        sys.exit(exit_code)


@global_cmd.command(name="status")
def global_status() -> None:
    """Check global infrastructure status."""
    click.secho("i", fg="blue", nl=False)
    click.echo(" Global infrastructure status:")

    compose_file = get_global_compose_file()
    env_file = get_global_env_file()

    run_docker_compose(compose_file, env_file, "ps")


@infra.group()
def project() -> None:
    """Manage project-specific infrastructure."""


@project.command(name="start")
@click.argument("project_name")
def project_start(project_name: str) -> None:
    """Start project infrastructure services."""
    project_infra = get_project_infra_dir(project_name)

    if not project_infra.exists():
        click.secho("✗", fg="red", nl=False)
        click.echo(f" Project infrastructure not found: {project_infra}")
        click.echo(f"   Run: repoctl infra init {project_name}")
        sys.exit(1)

    # Ensure global infrastructure is running
    ensure_network()

    click.secho("i", fg="blue", nl=False)
    click.echo(f" Starting infrastructure for project: {project_name}")

    compose_file = project_infra / "compose.yml"
    env_file = project_infra / ".env"

    # Change to project infra directory for docker compose context
    original_dir = Path.cwd()
    os.chdir(project_infra)

    try:
        exit_code = run_docker_compose(compose_file, env_file, "up", "-d")

        if exit_code == 0:
            click.secho("✓", fg="green", nl=False)
            click.echo(" Project infrastructure started")
        else:
            click.secho("✗", fg="red", nl=False)
            click.echo(" Failed to start project infrastructure")
            sys.exit(exit_code)
    finally:
        os.chdir(original_dir)


@project.command(name="stop")
@click.argument("project_name")
def project_stop(project_name: str) -> None:
    """Stop project infrastructure services."""
    project_infra = get_project_infra_dir(project_name)

    if not project_infra.exists():
        click.secho("✗", fg="red", nl=False)
        click.echo(f" Project infrastructure not found: {project_infra}")
        sys.exit(1)

    click.secho("i", fg="blue", nl=False)
    click.echo(f" Stopping infrastructure for project: {project_name}")

    compose_file = project_infra / "compose.yml"
    env_file = project_infra / ".env"

    original_dir = Path.cwd()
    os.chdir(project_infra)

    try:
        exit_code = run_docker_compose(compose_file, env_file, "down")

        if exit_code == 0:
            click.secho("✓", fg="green", nl=False)
            click.echo(" Project infrastructure stopped")
        else:
            click.secho("✗", fg="red", nl=False)
            click.echo(" Failed to stop project infrastructure")
            sys.exit(exit_code)
    finally:
        os.chdir(original_dir)


@project.command(name="status")
@click.argument("project_name")
def project_status(project_name: str) -> None:
    """Check project infrastructure status."""
    project_infra = get_project_infra_dir(project_name)

    if not project_infra.exists():
        click.secho("✗", fg="red", nl=False)
        click.echo(f" Project infrastructure not found: {project_infra}")
        sys.exit(1)

    click.secho("i", fg="blue", nl=False)
    click.echo(f" Project infrastructure status: {project_name}")

    compose_file = project_infra / "compose.yml"
    env_file = project_infra / ".env"

    original_dir = Path.cwd()
    os.chdir(project_infra)

    try:
        run_docker_compose(compose_file, env_file, "ps")
    finally:
        os.chdir(original_dir)


@infra.command(name="init")
@click.argument("project_name")
def init_project(project_name: str) -> None:
    """Initialize infrastructure directory and templates for a given project.

    Parameters
    ----------
    project_name : str
        Name of the project to initialize infrastructure for.

    Exits with code 1 if the project directory does not exist or infra already exists.
    """
    monorepo_root = get_monorepo_root()
    project_path = monorepo_root / "backends" / project_name
    project_path = monorepo_root / "backends" / project_name
    project_infra = project_path / "infra"

    if not project_path.exists():
        click.secho("✗", fg="red", nl=False)
        click.echo(f" Project directory not found: {project_path}")
        sys.exit(1)

    if project_infra.exists():
        click.secho("✗", fg="red", nl=False)
        click.echo(f" Infrastructure directory already exists: {project_infra}")
        sys.exit(1)

    click.secho("i", fg="blue", nl=False)
    click.echo(f" Initializing infrastructure for project: {project_name}")

    # Create infra directory
    project_infra.mkdir(parents=True, exist_ok=True)

    # Copy templates
    templates_dir = monorepo_root / "infra" / "templates"

    shutil.copy(templates_dir / "compose.project.yml", project_infra / "compose.yml")
    shutil.copy(templates_dir / ".env.project", project_infra / ".env.template")
    shutil.copy(templates_dir / "Dockerfile", project_infra / "Dockerfile")

    click.secho("✓", fg="green", nl=False)
    click.echo(f" Infrastructure template created at: {project_infra}")
    click.secho("⚠", fg="yellow", nl=False)
    click.echo(" Next steps:")
    click.echo(f"  1. cd {project_infra}")
    click.echo("  2. cp .env.template .env")
    click.echo("  3. Edit .env and customize for your project")
    click.echo("  4. Edit compose.yml and Dockerfile as needed")
    click.echo(f"  5. Run: repoctl infra project start {project_name}")


@infra.command(name="list")
def list_projects() -> None:
    """List all projects with infrastructure."""
    monorepo_root = get_monorepo_root()
    backends_dir = monorepo_root / "backends"

    click.secho("i", fg="blue", nl=False)
    click.echo(" Projects with infrastructure:")

    found_any = False
    for project_dir in sorted(backends_dir.iterdir()):
        if project_dir.is_dir() and (project_dir / "infra").exists():
            click.echo(f"  - {project_dir.name}")
            found_any = True

    if not found_any:
        click.echo("  (none)")


@infra.command(name="status")
def show_all_status() -> None:
    """Show status of all infrastructure."""
    click.echo("")
    click.secho("i", fg="blue", nl=False)
    click.echo(" ═══════════════════════════════════════")
    click.secho("i", fg="blue", nl=False)
    click.echo(" Global Infrastructure Status")
    click.secho("i", fg="blue", nl=False)
    click.echo(" ═══════════════════════════════════════")

    compose_file = get_global_compose_file()
    env_file = get_global_env_file()
    run_docker_compose(compose_file, env_file, "ps")

    click.echo("")
    click.secho("i", fg="blue", nl=False)
    click.echo(" ═══════════════════════════════════════")
    click.secho("i", fg="blue", nl=False)
    click.echo(" Project Infrastructure Status")
    click.secho("i", fg="blue", nl=False)
    click.echo(" ═══════════════════════════════════════")

    monorepo_root = get_monorepo_root()
    backends_dir = monorepo_root / "backends"

    original_dir = Path.cwd()

    for project_dir in sorted(backends_dir.iterdir()):
        project_infra = project_dir / "infra"
        if project_dir.is_dir() and project_infra.exists():
            click.echo("")
            click.secho("i", fg="blue", nl=False)
            click.echo(f" Project: {project_dir.name}")

            compose_file = project_infra / "compose.yml"
            env_file = project_infra / ".env"

            os.chdir(project_infra)
            try:
                result = subprocess.run(
                    ["docker", "compose", "-f", str(compose_file), "ps"],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if result.returncode == 0:
                    click.echo(result.stdout)
                else:
                    click.echo("  Not running")
            except Exception:
                click.echo("  Not running")

    os.chdir(original_dir)


# Register the global command with proper name
infra.add_command(global_cmd, name="global")

