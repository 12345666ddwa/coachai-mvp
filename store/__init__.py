"""CoachAI persistence package — SQLite data layer.

Exposes :mod:`store.db` as the single entry point::

    from store import db
    db.init_db()
"""

from . import db  # noqa: F401

__all__ = ["db"]
