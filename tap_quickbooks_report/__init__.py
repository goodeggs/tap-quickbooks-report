import os

import rollbar
import singer

from .streams import (ProfitAndLossDetailStream, ProfitAndLossStream,
                      QuickbooksStream)
from .utils import parse_args

LOGGER = singer.get_logger()


try:
    ROLLBAR_ACCESS_TOKEN = os.environ["ROLLBAR_ACCESS_TOKEN"]
    ROLLBAR_ENVIRONMENT = os.environ["ROLLBAR_ENVIRONMENT"]
except KeyError:
    LOGGER.info("No Rollbar environment variables found. Rollbar logging disabled..")
    log_to_rollbar = False
else:
    rollbar.init(ROLLBAR_ACCESS_TOKEN, ROLLBAR_ENVIRONMENT)
    log_to_rollbar = True

AUTH_REQUIRED_CONFIG_KEYS = [
    "client_id",
    "client_secret",
    "environment",
    "redirect_uri"
]

SYNC_REQUIRED_CONFIG_KEYS = [
    "client_id",
    "client_secret",
    "environment",
    "redirect_uri",
    "realm_id",
    "refresh_token",
    "refresh_token_expires_at"
]


def user_consent(config, args):
    LOGGER.info('Starting User Consent process..')
    stream = QuickbooksStream(config=config, args=args)
    stream.user_consent()


def sync(config, args):
    LOGGER.info('Starting sync..')
    stream = ProfitAndLossStream(config=config, args=args)
    stream.write_schema_message()
    stream.sync()
    stream = ProfitAndLossDetailStream(config=config, args=args)
    stream.write_schema_message()
    stream.sync()


def main_impl():
    args = parse_args(required_config_keys=AUTH_REQUIRED_CONFIG_KEYS)
    if args.auth is True:
        user_consent(config=args.config, args=args)
    else:
        args = parse_args(required_config_keys=SYNC_REQUIRED_CONFIG_KEYS)
        sync(config=args.config, args=args)


def main():
    try:
        main_impl()
    except Exception as exc:
        if log_to_rollbar is True:
            LOGGER.info("Reporting exception info to Rollbar..")
            rollbar.report_exc_info()
        LOGGER.critical(exc)
        raise


if __name__ == "__main__":
    main()
