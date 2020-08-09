from __future__ import print_function

from copy import deepcopy
from io import StringIO

from lxml import etree

from bases.FrameworkServices.UrlService import UrlService

priority = 90000

ORDER = [
    'downstream_frequency',
    'downstream_power',
    'downstream_signal_to_noise',
    'downstream_octets',
    'downstream_corrected_errors',
    'downstream_uncorrected_errors',
]

CHARTS = {
    'downstream_frequency': {
        'options': [None, 'Frequency', 'mHz', 'arris', 'arris.frequency', 'line'],
        'lines': [
            ['downstream_{n}_frequency', '{n}', 'absolute', 1, 100],
        ],
    },
    'downstream_power': {
        'options': [None, 'Power', 'dBmV', 'arris', 'arris.power', 'line'],
        'lines': [
            ['downstream_{n}_power', '{n}', 'absolute', 1, 100],
        ],
    },
    'downstream_signal_to_noise': {
        'options': [None, 'Signal to Noise', 'dB', 'arris', 'arris.signal_to_noise', 'line'],
        'lines': [
            ['downstream_{n}_signal_to_noise', '{n}', 'absolute', 1, 100],
        ],
    },
    'downstream_octets': {
        'options': [None, 'Octets Received', 'octets', 'arris', 'arris.octets', 'line'],
        'lines': [
            ['downstream_{n}_octets', '{n}', 'incremental'],
        ],
    },
    'downstream_corrected_errors': {
        'options': [None, 'Corrected Errors', 'correcteds', 'arris', 'arris.corrected_errors', 'line'],
        'lines': [
            ['downstream_{n}_corrected_errors', '{n}', 'incremental'],
        ],
    },
    'downstream_uncorrected_errors': {
        'options': [None, 'Uncorrected Errors', 'uncorrectables', 'arris', 'arris.uncorrected_errors', 'line'],
        'lines': [
            ['downstream_{n}_uncorrected_errors', '{n}', 'incremental'],
        ],
    },
}

html_parser = etree.HTMLParser()


class Service(UrlService):
    def __init__(self, configuration=None, name=None):
        if configuration is None:
            configuration = {}
        configuration.setdefault('url', 'http://192.168.100.1/cgi-bin/status_cgi')

        super(Service, self).__init__(configuration=configuration, name=name)

        self.order = ORDER
        self.definitions = deepcopy(CHARTS)

    def create_definitions(self):
        num_downstreams = len(self.get_downstream_rows())

        for chart in self.definitions.values():
            lines = chart['lines']
            line_tmpl = lines.pop()

            for n in range(1, num_downstreams + 1):
                line = list(line_tmpl)
                line[0] = line[0].format(n=n)
                line[1] = line[1].format(n=n)
                lines.append(line)

    def get_downstream_rows(self):
        try:
            html = self._get_raw_data().decode('utf8')
            root = etree.parse(StringIO(html), html_parser)
            rows = root.xpath('//h4[contains(text(), "Downstream")]'
                              '/following-sibling::table[1]'
                              '//tr[td[1][contains(text(), "Downstream")]]')

            return [
                {
                    'frequency': float(row[2].text.split(' ', 1)[0]) * 100,
                    'power': float(row[3].text.split(' ', 1)[0]) * 100,
                    'signal_to_noise': float(row[4].text.split(' ', 1)[0]) * 100,
                    'octets': int(row[6].text),
                    'corrected_errors': int(row[7].text),
                    'uncorrected_errors': int(row[8].text),
                }
                for row in rows
            ]
        except (ValueError, AttributeError):
            return ()

    def _get_data(self):
        return {
            '_'.join(('downstream', str(n), key)): value
            for n, downstream in enumerate(self.get_downstream_rows())
            for key, value in downstream.items()
        }

    def check(self):
        if not (self.url and isinstance(self.url, str)):
            self.error('URL is not defined or type is not <str>')
            return False

        self._manager = self._build_manager()
        if not self._manager:
            return False

        self.create_definitions()

        try:
            data = self._get_data()
        except Exception as error:
            self.error('_get_data() failed. Url: {url}. Error: {error}'.format(url=self.url, error=error))
            return False

        if isinstance(data, dict) and data:
            return True
        self.error('_get_data() returned no data or type is not <dict>')
        return False
