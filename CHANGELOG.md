# CHANGELOG

All notable changes to this project will be documented in this file.

## [v0.5.0] - 2026-07-14
### Added
- Added Anomaly alerts with alertsmanager.
- Added DB migrations using alembic.
- Added port for prometheus(Cluster).

### Changed
- Upgraded to SQLAlchemy 2.0 (ML, Tasks).
- Changed port for prometheus(Monitoring devices), from localhost:30091 to localhost:30391.
- Cleared jobs for prometheus(Monitoring devices).


## [v0.4.0] - 2026-07-13
### Added
- Added AuthZ
- Added tests for API(AuthZ).
- Added validation to "[POST] /devices" for frontend and backend.
- Added support for multiple creating admins or users on startup. 

### Changed
Splited main.py to 3 files:
* security.py
* validators.py
* main.py



## [v0.3.0] - 2026-07-11
### Added
- Added tests for API, tasks, DB and ML.
- Added AuthN and sessions.
- Added login window for frontend.


## [v0.2.0] - 2026-07-10
### Added
- Added uv for dependencies

### Deleted
- ruff.toml (Moved to pyproject.toml)
- pytest.ini (Moved to pyproject.toml)
- mypy.ini (Moved to pyproject.toml)


## [v0.1.0] - 2026-07-09

### Added
- Added Indexes to DB.
- Added tests with Pytest.
- Added test and MyPy checks into CI.
- Added Dockerignore.
- Added limit, cap and offset to some endpoints.

### Changed
- Upgraded to SQLAlchemy 2.0 (API, DB).
- Improved Docker images.