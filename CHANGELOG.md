# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.4.0] - 2023-11-14

### Added
- Adding cloud events to kafka topic 'plc.events' when
the write API is used.

## [1.3.0] - 2023-11-01

### Added
- Added support for app.kubernetes.io/version which will be used to deploy the corresponding image tags

### Fixed
- Updated opentelemetry package version to 1.20.0 for 1.15.0 which includes a bug fix for the MetricsTimeoutError mentioned below.

## [1.2.0] - 2023-09-22

### Added
- Added workaround for python-otel bug caused from MetricsTimeoutError. The readiness probe endpoint will now check if the PLC is reachable or unreachable to decide whether the telemetry should be observed.

### Fixed
- Fixes flask dependencie issue - werkzeug compatibility was broken (force install to 2.2.2)

## [1.1.0] - 2023-09-22

### Added
- Otel collector environment variables to operator deployment

### Removed
- Unused environment variables and refereences to farm_code, site_id, and operating_site

### Fixed
- Operator cluster role was missing the patch verb for services

## [1.0.0] - 2023-09-07

### Added

- Initial release of the PLC service.
- Settings for Avalon Barge PTY02