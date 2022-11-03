"""
Objects from this package will be shared across modules, so there should not be imports
from other modules at the top of the file to avoid circular imports.
"""
import os


def get_from_env(name: str, example: str) -> str:
    env_var = os.getenv(name)
    if not env_var:
        raise EnvironmentError(f"Missing .env_public file or the file lacks variable {name}. Example:\n{example}")
    return env_var
