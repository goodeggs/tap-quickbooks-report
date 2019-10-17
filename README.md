# tap-quickbooks-report
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Python Versions](https://img.shields.io/badge/python-3.6%20%7C%203.7-blue.svg)](https://pypi.python.org/pypi/ansicolortags/)
[![Build Status](https://travis-ci.com/goodeggs/tap-quickbooks-report.svg?branch=master)](https://travis-ci.com/goodeggs/tap-quickbooks-report.svg?branch=master)

A [Singer](https://www.singer.io/) tap for extracting data from the Report Entities in the [Quickbooks Online API](https://developer.intuit.com/app/developer/qbo/docs/api/accounting/report-entities).

## Configuration

The Quickbooks Online API provides authentication via OAuth2.0. The tap expects the user to provide a valid Refresh Token via a config file. You can kick off
a OAuth2.0 User Consent process using the `--auth` argument while running the tap:

```bash
(tap-quickbooks-report) bash-3.2$ tap-quickbooks-report --auth
```

If you are an admin of the Quickbooks account, you will be able to authorize the Singer Tap application to access your account. You will then be redirected to a developer portal where you can access a valid Authentication Code and Realm ID. Copy and paste these values into the corresponding prompts in your terminal:

```bash
(tap-quickbooks-report) bash-3.2$ tap-quickbooks-report --auth
INFO Starting User Consent process..
Enter the Authorization Code: <auth-code>
Enter the Realm ID: <realm-id>
```

After entering the Authorization Code and Realm ID values, the tap will return a new config file. Replace your existing config file with these new values:

```
(tap-quickbooks-report) bash-3.2$ tap-quickbooks-report --auth
INFO Starting User Consent process..
Enter the Authorization Code: <auth-code>
Enter the Realm ID: <realm-id>
INFO Generating new config..
{
 "client_id": "<client-id>",
 "client_secret": "<client-secret>",
 "redirect_uri": "https://developer.intuit.com/v2/OAuth2Playground/RedirectUrl",
 "environment": "production",
 "realm_id": "<realm-id>",
 "refresh_token": "<refresh-token>",
 "refresh_token_expires_at": "<refresh-token-expires-at"
}
```
