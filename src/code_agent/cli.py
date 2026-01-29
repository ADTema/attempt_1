import typer

app = typer.Typer(add_completion=False, invoke_without_command=True)


@app.callback()
def _entry(ctx: typer.Context) -> None:
    """Run agent in GitHub Actions."""
    # если запустили просто `code-agent` без подкоманды — выполняем run()
    if ctx.invoked_subcommand is None:
        run()


@app.command()
def run() -> None:
    """Run agent in GitHub Actions."""
    typer.echo("code-agent run: ok")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
