import logging
import requests


class TelegrafLogger:
    def __init__(self, telegraf_url):
        self.telegraf_url = telegraf_url

    def log_metrics(self, measurement, tags, fields):
        """
        Logs metrics to Telegraf via the HTTP listener.
        :param measurement: The measurement name (e.g., "state_tracker")
        :param tags: A dictionary of tag key-value pairs
        :param fields: A dictionary of field key-value pairs
        """
        data = [f"{measurement}," + ",".join([f"{k}={v}" for k, v in tags.items()])
                + " " + ",".join([f"{k}={v}" for k, v in fields.items()])]
        try:
            response = requests.post(self.telegraf_url, data="\n".join(data), timeout=10)
            response.raise_for_status()
            logging.debug('Telegraf metrics sent successfully! Data: %s', data)
        except requests.exceptions.RequestException as e:
            logging.error(f"Error sending metrics to Telegraf: {e}")
