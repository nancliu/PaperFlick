"""Read-only health check for verify-paperflick Doctor."""

from __future__ import annotations

from paperflick.core.settings import Settings, load

settings = Settings()
assert settings.interval_seconds == 2.0
assert settings.wait_for_empty_queue is False
assert settings.dry_run is False
_ = load()
print(settings)
print("ok")
