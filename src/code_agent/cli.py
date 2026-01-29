import os
import subprocess
from datetime import datetime

import typer
from github import Github

app = typer.Typer(add_completion=False)


def sh(cmd: list[str]) -> str:
    p = subprocess.run(cmd, check=True, text=True, capture_output=True)
    return p.stdout.strip()


def must_env(name: str) -> str:
    v = os.getenv(name)
    if not v:
        raise RuntimeError(f"Missing env var: {name}")
    return v


def ensure_git_identity() -> None:
    sh(["git", "config", "user.name", "code-agent"])
    sh(["git", "config", "user.email", "code-agent@users.noreply.github.com"])


def touch_readme(issue_number: int) -> None:
    path = "README.md"
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            f.write("# attempt_1\n")
    with open(path, "a", encoding="utf-8") as f:
        f.write(f"\nAgent touch for issue #{issue_number} at {datetime.utcnow().isoformat()}Z\n")


@app.command()
def run() -> None:
    token = must_env("AGENT_GH_TOKEN")
    repo_full = must_env("GITHUB_REPOSITORY")
    issue_number = int(must_env("ISSUE_NUMBER"))
    base_branch = os.getenv("BASE_BRANCH", "main")

    ensure_git_identity()

    gh = Github(token)
    repo = gh.get_repo(repo_full)
    issue = repo.get_issue(number=issue_number)

    branch = f"agent/issue-{issue_number}"

    sh(["git", "fetch", "origin", base_branch])
    sh(["git", "checkout", base_branch])
    sh(["git", "pull", "origin", base_branch])

    existing = sh(["git", "branch", "--list", branch])
    if existing:
        sh(["git", "checkout", branch])
    else:
        sh(["git", "checkout", "-b", branch])

    touch_readme(issue_number)

    sh(["git", "add", "-A"])
    if sh(["git", "status", "--porcelain"]):
        sh(["git", "commit", "-m", f"agent: touch README for issue #{issue_number}"])
    sh(["git", "push", "-u", "origin", branch])

    title = f"[agent] Issue #{issue_number}: {issue.title}"
    body = f"Auto-generated PR for issue #{issue_number}\n\nIssue: {issue.html_url}\n"
    pr = repo.create_pull(title=title, body=body, head=branch, base=base_branch)

    issue.create_comment(f"PR created: {pr.html_url}")
    typer.echo(f"Created PR: {pr.html_url}")
