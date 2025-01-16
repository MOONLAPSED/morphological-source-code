import nox

# Default sessions to run
nox.options.sessions = ["uvvenv"]


@nox.session(
    reuse_venv=True,
    venv_backend="venv",
)
def uvvenv(session: nox.Session) -> None:
    """Create a virtual environment and run Black."""
    session.install("black")
    session.run("black", ".")


@nox.session
@nox.parametrize("version", ["0.4.20"])
def versioned(session: nox.Session, version: str) -> None:
    """
    Run a versioned session.
    From the CLI: `nox -s versioned -- 0.4.20`
    """
    session.install(f"cognosis=={version}")
    session.run("python", "-m", "cognosis")
