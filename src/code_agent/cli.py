from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass

import typer

app = typer.Typer(add_completion=False, no_args_is_help=True)


@dataclass(frozen=True)
class Env:
    token: str
    repo: str
    issue_number: int
    base_branch: str


def _get_env() -> Env:
    token = os.getenv("AGENT_GH_TOKEN", "").strip()
    repo = os.getenv("GITHUB_REPOSITORY", "").strip()
    issue_number_raw = os.getenv("ISSUE_NUMBER", "").strip()
    base_branch = os.getenv("BASE_BRANCH", "main").strip() or "main"

    if not token:
        raise typer.BadParameter("AGENT_GH_TOKEN is missing")
    if not repo:
        raise typer.BadParameter("GITHUB_REPOSITORY is missing")
    if not issue_number_raw.isdigit():
        raise typer.BadParameter("ISSUE_NUMBER must be an integer")

    return Env(token=token, repo=repo, issue_number=int(issue_number_raw), base_branch=base_branch)


def _run(cmd: list[str]) -> None:
    typer.echo(f"$ {' '.join(cmd)}")
    subprocess.run(cmd, check=True)


@app.command()
def run() -> None:
    """
    Run agent in GitHub Actions:
    - creates branch
    - commits a trivial change
    - pushes and opens PR
    """
    env = _get_env()

    branch = f"agent/issue-{env.issue_number}"
    filename = "_agent_ok.txt"
    content = f"ok from issue #{env.issue_number}\n"

    # Ensure git identity exists for commits inside GH Actions runner
    _run(["git", "config", "user.name", "code-agent"])
    _run(["git", "config", "user.email", "code-agent@users.noreply.github.com"])

    # Ensure we are on base branch and up-to-date
    _run(["git", "fetch", "origin", env.base_branch])
    _run(["git", "checkout", env.base_branch])
    _run(["git", "reset", "--hard", f"origin/{env.base_branch}"])

    # Create/overwrite branch
    _run(["git", "checkout", "-B", branch])

    # Make a trivial change
    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)

    _run(["git", "add", filename])
    _run(["git", "commit", "-m", f"chore: agent ok for issue #{env.issue_number}"])

    # Push branch using token-auth remote already set in workflow
    _run(["git", "push", "-u", "origin", branch, "--force"])

    # Create PR via GitHub CLI (works reliably in Actions)
    _run(
        [
            "gh",
            "pr",
            "create",
            "--title",
            f"Agent: issue #{env.issue_number}",
            "--body",
            f"Auto PR created from issue #{env.issue_number}.",
            "--base",
            env.base_branch,
            "--head",
            branch,
        ]
    )

    typer.echo("done")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
