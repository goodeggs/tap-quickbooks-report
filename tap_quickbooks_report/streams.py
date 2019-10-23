import json
import os
import webbrowser
from datetime import datetime, timedelta
from typing import Dict

import attr
import pytz
import requests
import singer
from intuitlib.client import AuthClient
from intuitlib.enums import Scopes

from .version import __version__

LOGGER = singer.get_logger()


@attr.s
class QuickbooksStream:
    BASE_URL = "https://quickbooks.api.intuit.com"
    API_VERSION = "v3"
    API_MINOR_VERSION = 40

    config: Dict = attr.ib()
    args: Dict = attr.ib()
    @config.validator
    def check(self, attribute, value):
        if value.get("environment") not in ["sandbox", "production"]:
            raise ValueError('environment attribute must be either "sandbox" or "production".')

    def _get_abs_path(self, path: str) -> str:
        return os.path.join(os.path.dirname(os.path.realpath(__file__)), path)

    def _load_schema(self) -> Dict:
        '''Loads a JSON schema file for a given
        Quickbooks Report resource into a dict representation.
        '''
        schema_path = self._get_abs_path("schemas")
        return singer.utils.load_json(f"{schema_path}/{self.tap_stream_id}.json")

    def _generate_token_expiration(self, refresh_token_expires_in_seconds: int) -> str:
        '''Generates a string-formatted expiration date using the
        refresh_token_expires_in_seconds value attached to the Auth Client.
        '''
        return datetime.strftime((datetime.utcnow().replace(tzinfo=pytz.UTC) + timedelta(seconds=refresh_token_expires_in_seconds)), '%Y-%m-%d %H:%M:%S %Z')

    def user_consent(self):
        '''Triggers the User Consent OAuth2.0 flow
        in order to retrieve an Authorization Code
        and a Realm ID.
        '''
        auth_client = AuthClient(self.config.get("client_id"),
                                 self.config.get("client_secret"),
                                 self.config.get("redirect_uri"),
                                 self.config.get("environment"))

        scopes = [Scopes.ACCOUNTING]
        auth_url = auth_client.get_authorization_url(scopes)
        webbrowser.open(auth_url)
        auth_code = input('Enter the Authorization Code: ')
        realm_id = input('Enter the Realm ID: ')
        auth_client.get_bearer_token(auth_code, realm_id=realm_id)
        self.config["realm_id"] = realm_id
        self.config["refresh_token"] = auth_client.refresh_token
        self.config["refresh_token_expires_at"] = self._generate_token_expiration(auth_client.x_refresh_token_expires_in)

        LOGGER.info('Generating new config..')
        with open(self.args.config_path, 'r+') as f:
            json.dump(self.config, f, indent=2)

    def _check_token_expiry(self, auth_client):
        '''Checks the expiration status
        of the Refresh Token supplied in the config file.
        '''
        LOGGER.info("Checking Refresh Token expiry..")
        rt_expires_in = timedelta(seconds=auth_client.x_refresh_token_expires_in)
        rt_expiration_dt_utc = datetime.utcnow() + rt_expires_in
        refresh_token_msg = f"Refresh Token expires on {rt_expiration_dt_utc} UTC"
        if rt_expires_in.days <= 30:
            LOGGER.warning(refresh_token_msg)
        else:
            LOGGER.info(refresh_token_msg)

    def _get_auth_client(self):
        '''Returns an OAuth2.0 Client for interacting
        with Quickbooks Reporting API.
        '''

        auth_client = AuthClient(self.config.get("client_id"),
                                 self.config.get("client_secret"),
                                 self.config.get("redirect_uri"),
                                 self.config.get("environment"),
                                 refresh_token=self.config.get("refresh_token"),
                                 realm_id=self.config.get("realm_id"))

        # Refresh to get new Access Token.
        auth_client.refresh()

        if auth_client.refresh_token == self.config.get("refresh_token"):
            LOGGER.info("Config file Refresh Token and Refresh Token received from Refresh Token API are identical.")
        else:
            LOGGER.info("Config file Refresh Token and Refresh Token received from Refresh Token API has drifted.")
            LOGGER.info("Overwriting Config file with new Refresh Token values..")

            self.config["refresh_token"] = auth_client.refresh_token
            self.config["refresh_token_expires_at"] = self._generate_token_expiration(auth_client.x_refresh_token_expires_in)

            with open(self.args.config_path, 'r+') as f:
                json.dump(self.config, f, indent=2)

        # Check Refresh Token Expiry.
        self._check_token_expiry(auth_client)

        return auth_client

    def _construct_headers(self, access_token) -> Dict:
        '''Constructs a standard set of headers for GET requests.'''
        headers = requests.utils.default_headers()
        headers["Accept"] = "application/json"
        headers["User-Agent"] = f"python-quickbooks-reporting-tap/{__version__}"
        headers["Authorization"] = f"Bearer {access_token}"
        headers["Content-Type"] = "application/json"
        headers["Date"] = singer.utils.strftime(singer.utils.now(), '%a, %d %b %Y %H:%M:%S %Z')
        return headers

    def _get(self, auth_client, report_entity: str, params: Dict = None) -> Dict:
        '''Constructs a standard way of making
        a GET request to the Quickbooks REST API.
        '''
        url = f"{self.BASE_URL}/{self.API_VERSION}/company/{auth_client.realm_id}/reports/{report_entity}"
        headers = self._construct_headers(access_token=auth_client.access_token)
        params.update({"minorversion": self.API_MINOR_VERSION})
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        return response.json()

    def _convert_string_value_to_float(self, value: str) -> float:
        '''Safely converts string values to floats.'''
        if value == "":
            float_value = float(0.0)
        else:
            float_value = float(value)
        return float_value

    def _get_row_data(self, resp, column_enum, input):
        for row in resp.get("Rows").get("Row"):
            if row.get("type") == "Section" and row.get("Rows") is not None:
                data_dict = {}
                key = row.get("Header").get("ColData")[0].get("value").title().replace(" ", "")
                data = {
                    key: {
                        "Lines": [],
                        "Total": self._convert_string_value_to_float(row.get("Summary").get("ColData")[column_enum].get("value"))
                    }
                }
                data_dict.update(data)
                input.append(data_dict)
                self._get_row_data(resp=row, input=data_dict[key]["Lines"], column_enum=column_enum)
            elif row.get("Summary") is not None:
                data_dict = {}
                key = row.get("Summary").get("ColData")[0].get("value").title().replace(" ", "")
                data = {
                    key: {
                        "Lines": [],
                        "Total": self._convert_string_value_to_float(row.get("Summary").get("ColData")[column_enum].get("value"))
                    }
                }
                data_dict.update(data)
                input.append(data_dict)
            else:
                data_dict = {}
                key = row.get("ColData")[0].get("value").title().replace(" ", "")
                data = {
                    key: {
                        "Lines": [],
                        "Total": self._convert_string_value_to_float(row.get("ColData")[column_enum].get("value"))
                    }
                }
                data_dict.update(data)
                input.append(data_dict)

        return input

    def _transform_columns_into_rows(self, resp):
        records = []
        for column in resp.get("Columns").get("Column"):
            if column.get("ColType") == "Money":
                record = {}
                for meta_column in column.get("MetaData"):
                    record[meta_column.get("Name")] = meta_column.get("Value")
                records.append(record)

        return records

    def write_schema_message(self):
        '''Writes a Singer schema message.'''
        return singer.write_schema(stream_name=self.stream, schema=self.schema, key_properties=self.key_properties)


class ProfitAndLossStream(QuickbooksStream):
    tap_stream_id = 'profit_and_loss'
    stream = 'profit_and_loss'
    key_properties = 'StartDate'
    replication_method = 'FULL_TABLE'

    def __init__(self, config: Dict, args: Dict):
        self.schema = self._load_schema()
        super().__init__(config, args)

    def sync(self):
        with singer.metrics.job_timer(job_type=f"sync_{self.tap_stream_id}"):
            with singer.metrics.record_counter(endpoint=self.tap_stream_id) as counter:
                client = self._get_auth_client()
                params = {
                    "start_date": "2014-01-01",
                    "accounting_method": "Accrual",
                    "summarize_column_by": "Month"
                }
                resp = self._get(auth_client=client, report_entity='ProfitAndLoss', params=params)
                rows = self._transform_columns_into_rows(resp)

                for i, row in enumerate(rows):
                    if row.get("StartDate") is None:
                        continue
                    input = []
                    data = self._get_row_data(resp=resp, column_enum=i + 1, input=input)
                    new_data = {}
                    for line in data:
                        new_data.update(line)
                    row["ReportData"] = new_data
                    row["SyncTimestampUtc"] = singer.utils.strftime(singer.utils.now(), "%Y-%m-%dT%H:%M:%SZ")

                    with singer.Transformer() as transformer:
                        transformed_record = transformer.transform(data=row, schema=self.schema)
                        singer.write_record(stream_name=self.stream, time_extracted=singer.utils.now(), record=transformed_record)
                        counter.increment()


class ProfitAndLossDetailStream(QuickbooksStream):
    tap_stream_id = 'profit_and_loss_detail'
    stream = 'profit_and_loss_detail'
    key_properties = []
    replication_method = 'FULL_TABLE'

    def __init__(self, config: Dict, args: Dict):
        self.schema = self._load_schema()
        super().__init__(config, args)

    def _get_column_metadata(self, resp):
        columns = []
        for column in resp.get("Columns").get("Column"):
            if column.get("ColTitle") == "Memo/Description":
                columns.append("Memo")
            else:
                columns.append(column.get("ColTitle").replace(" ", ""))
        columns.append("Categories")
        return columns

    def _recursive_row_search(self, row, output, categories):
        row_group = row.get("Rows")
        if 'ColData' in list(row.keys()):
            # Write the row
            data = row.get("ColData")
            values = [column.get("value") for column in data]
            categories_copy = categories.copy()
            values.append(categories_copy)
            values_copy = values.copy()
            output.append(values_copy)
        elif row_group is None or row_group == {}:
            pass
        else:
            row_array = row_group.get("Row")
            header = row.get("Header")
            if header is not None:
                categories.append(header.get("ColData")[0].get("value"))
            for row in row_array:
                self._recursive_row_search(row, output, categories)
            if header is not None:
                categories.pop()

    def sync(self):
        singer_version = int(datetime.utcnow().timestamp())
        with singer.metrics.job_timer(job_type=f"sync_{self.tap_stream_id}"):
            with singer.metrics.record_counter(endpoint=self.tap_stream_id) as counter:
                client = self._get_auth_client()
                params = {
                    "start_date": "2014-01-01",
                    "accounting_method": "Accrual"
                }
                resp = self._get(auth_client=client, report_entity='ProfitAndLossDetail', params=params)

                # Get column metadata.
                columns = self._get_column_metadata(resp)

                # Recursively get row data.
                row_group = resp.get("Rows")
                row_array = row_group.get("Row")

                if row_array is None:
                    return LOGGER.info("Report has no rows!")

                output = []
                categories = []
                for row in row_array:
                    self._recursive_row_search(row, output, categories)

                # Zip columns and row data.
                for raw_row in output:
                    row = dict(zip(columns, raw_row))
                    cleansed_row = {}
                    for k, v in row.items():
                        if v == "":
                            continue
                        else:
                            cleansed_row.update({k: v})

                    cleansed_row["Amount"] = float(row.get("Amount"))
                    cleansed_row["Balance"] = float(row.get("Balance"))
                    cleansed_row["SyncTimestampUtc"] = singer.utils.strftime(singer.utils.now(), "%Y-%m-%dT%H:%M:%SZ")

                    with singer.Transformer() as transformer:
                        transformed_record = transformer.transform(data=cleansed_row, schema=self.schema)
                        singer.write_message(singer.RecordMessage(stream=self.stream,
                                                                  record=transformed_record,
                                                                  version=singer_version,
                                                                  time_extracted=singer.utils.now()))
                        counter.increment()

        singer.write_version(stream_name=self.stream, version=singer_version)
