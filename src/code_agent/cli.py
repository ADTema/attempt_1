from __future__ import annotations

import os
from dataclasses import dataclass

import typer

app = typer.Typer(add_completion=False)


@dataclass(frozen=True)
class Env:
    token: str
    repo_full: str
    issue_number: int
    base_branch: str


def _need(name: str) -> str:
    v = os.getenv(name)
    if not v:
        raise RuntimeError(f"Missing required env var: {name}")
    return v


def _load_env() -> Env:
    return Env(
        token=_need("AGENT_GH_TOKEN"),
        repo_full=_need("GITHUB_REPOSITORY"),
        issue_number=int(_need("ISSUE_NUMBER")),
        base_branch=_need("BASE_BRANCH"),
    )


@app.command()
def run() -> None:
    """Run agent in GitHub Actions: issue -> branch -> commit -> PR."""
    env = _load_env()

    # PyGithub imports (types may be missing, that's ok with mypy overrides below)
    from github import Github  # type: ignore[import-not-found]
    from github.GithubException import GithubException  # type: ignore[import-not-found]

    gh = Github(env.token)
    repo = gh.get_repo(env.repo_full)

    issue = repo.get_issue(number=env.issue_number)

    branch = f"agent/issue-{env.issue_number}"
    path = f"agent_pr/issue-{env.issue_number}.md"

    base_sha = repo.get_branch(env.base_branch).commit.sha

    # Create branch if missing
    try:
        repo.get_git_ref(f"heads/{branch}")
    except GithubException as e:
        if getattr(e, "status", None) == 404:
            repo.create_git_ref(ref=f"refs/heads/{branch}", sha=base_sha)
        else:
            raise

    content = (
        f"# Agent PR for issue #{env.issue_number}\n\n"
        f"Title: {issue.title}\n\n"
        "Body:\n\n"
        f"{issue.body or '(empty)'}\n"
    )

    # Create/update file on that branch
    try:
        existing = repo.get_contents(path, ref=branch)
        if isinstance(existing, list):
            raise RuntimeError(f"Expected file at {path}, got directory")
        repo.update_file(
            path=path,
            message=f"chore: update agent file for issue #{env.issue_number}",
            content=content,
            sha=existing.sha,
            branch=branch,
        )
    except GithubException as e:
        if getattr(e, "status", None) == 404:
            repo.create_file(
                path=path,
                message=f"chore: add agent file for issue #{env.issue_number}",
                content=content,
                branch=branch,
            )
        else:
            raise

    # Create PR if missing
    head = f"{repo.owner.login}:{branch}"
    pulls = list(repo.get_pulls(state="open", head=head))
    if pulls:
        pr = pulls[0]
    else:
        pr = repo.create_pull(
            title=f"Agent: {issue.title}",
            body=f"Auto-created from issue #{env.issue_number}.",
            head=branch,
            base=env.base_branch,
        )

    issue.create_comment(f"Created/updated PR: {pr.html_url}")
    typer.echo(f"ok: {pr.html_url}")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
