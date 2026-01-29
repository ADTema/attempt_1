from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass

import typer
from github import Github

app = typer.Typer(add_completion=False)


@dataclass(frozen=True)
class Ctx:
    token: str
    repo_full: str
    issue_number: int
    base_branch: str


def _require_env(name: str) -> str:
    v = os.getenv(name)
    if not v:
        raise typer.BadParameter(f"Missing env var: {name}")
    return v


def _get_ctx() -> Ctx:
    token = _require_env("AGENT_GH_TOKEN")
    repo_full = _require_env("GITHUB_REPOSITORY")
    issue_number = int(_require_env("ISSUE_NUMBER"))
    base_branch = os.getenv("BASE_BRANCH") or "main"
    return Ctx(token=token, repo_full=repo_full, issue_number=issue_number, base_branch=base_branch)


def _sh(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)


def _sanitize_branch(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r"[^a-z0-9._-]+", "-", s)
    s = re.sub(r"-{2,}", "-", s).strip("-")
    return s or "issue"


@app.command()
def run() -> None:
    """
    Entry point for GitHub Actions.
    Reads env: AGENT_GH_TOKEN, GITHUB_REPOSITORY, ISSUE_NUMBER, BASE_BRANCH
    Creates a branch, commits a small change, opens a PR, comments back to the issue.
    """
    ctx = _get_ctx()

    gh = Github(ctx.token)
    repo = gh.get_repo(ctx.repo_full)
    issue = repo.get_issue(number=ctx.issue_number)

    title = issue.title or f"Issue {ctx.issue_number}"
    body = issue.body or ""

    branch_name = f"agent/issue-{ctx.issue_number}-{_sanitize_branch(title)[:40]}"
    pr_title = f"Agent: {title}"
    pr_body = (
        "Automated PR created from issue.\n\n"
        f"- Source issue: #{ctx.issue_number}\n\n"
        "Issue body (for context):\n"
        "```\n"
        f"{body}\n"
        "```\n"
    )

    # Make a deterministic tiny change so we can verify the whole pipeline.
    # You can later replace this with real patch logic.
    file_path = "_agent_ok.txt"
    content = f"ok (issue #{ctx.issue_number})\n"

    typer.echo(f"Repo: {ctx.repo_full}")
    typer.echo(f"Issue: #{ctx.issue_number} / {title}")
    typer.echo(f"Base branch: {ctx.base_branch}")
    typer.echo(f"Branch: {branch_name}")

    # Ensure base is up to date locally
    _sh(["git", "fetch", "origin", ctx.base_branch])
    _sh(["git", "checkout", "-B", ctx.base_branch, f"origin/{ctx.base_branch}"])

    # Create branch
    _sh(["git", "checkout", "-b", branch_name])

    # Write file
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)

    # Commit
    _sh(["git", "add", file_path])
    _sh(["git", "commit", "-m", f"chore: agent run for issue #{ctx.issue_number}"])

    # Push
    _sh(["git", "push", "-u", "origin", branch_name])

    # Create PR (via API)
    pr = repo.create_pull(
        title=pr_title,
        body=pr_body,
        head=branch_name,
        base=ctx.base_branch,
        draft=False,
    )

    # Comment back to issue
    issue.create_comment(f"✅ PR created: {pr.html_url}")

    typer.echo(f"PR: {pr.html_url}")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
