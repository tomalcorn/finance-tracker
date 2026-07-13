"""``python -m migrations`` entry point.

Delegates to the pydantic-settings CLI app in ``migrations.cli``.
"""

from pydantic_settings import CliApp

from migrations.cli import MigrateCli

if __name__ == "__main__":
    CliApp.run(MigrateCli)
