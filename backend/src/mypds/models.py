"""Import de tous les modèles (métadonnées Alembic)."""

from mypds.alerts.models import Alert  # noqa: F401
from mypds.auth.models import AuditLog, LoginAttempt, Session, User, UserAvatar  # noqa: F401
from mypds.cockpit.models import CockpitLayoutRow, IconAsset  # noqa: F401
from mypds.config.models import AppSetting, BrandingAsset, UserPreference, Wallpaper  # noqa: F401
from mypds.connectors.models import ConnectorInstance  # noqa: F401
from mypds.core.db import Base  # noqa: F401
from mypds.landing.models import LandingLayoutRow  # noqa: F401
from mypds.widgets.calendar.models import CalendarSource  # noqa: F401
from mypds.widgets.notes.models import Note  # noqa: F401
from mypds.widgets.rss.models import RssCategory, RssFeed, RssItem  # noqa: F401
from mypds.widgets.todo.models import TodoItem  # noqa: F401
