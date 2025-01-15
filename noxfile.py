import noxfile

nox.options.sessions = ["uvvenv"]

@nox.session(
        reuse_venv=True
        venv_backend="uv|venv"
)
def uvvenv(session: nox.Session) -> None:
    session.install("black")
    session.run("black", ".")

@nox.session
@nox.parametrize("version", ["0.4.20"])
def versioned(session: nox.Session, version: str) -> None:
    """From the cli: `nox -s versioned`"""
    session.install(f"cognosis=={version}")
    session.run("python", "-m", "cognosis")