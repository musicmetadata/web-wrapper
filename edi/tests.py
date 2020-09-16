from django.test import SimpleTestCase
from .urls import urlpatterns
from django.urls import reverse
from music_metadata.edi.tests import CWR2_PATH, CWR3_PATH
import json


class EdiTest(SimpleTestCase):
    def test_urlpatterns(self):
        for urlpattern in urlpatterns:
            url = reverse(urlpattern.name)
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            response = self.client.post(url, {})
            self.assertIn(response.status_code, [200, 405])

    def test_json(self):
        url = reverse('edi_to_json')
        # CWR2 with download
        with open(CWR2_PATH) as f:
            response = self.client.post(url, {
                'file': f,
                'verbosity': '0',
                'download': '1'})
            data = json.loads(b''.join(response.streaming_content))
            submitter = data.get('submitter')
            work_registrations = data.get('work_registrations')
            file = data.get('file')
            self.assertEqual(
                submitter.get('submitter_name'),
                'MUSIC PUB CARTOONS')
            self.assertEqual(
                file.get('name'),
                'CW190001MPC_000.V21')
            self.assertFalse(file.get('valid'))
            self.assertEqual(
                len(work_registrations), 100)
            self.assertEqual(response.status_code, 200)
        with open(CWR2_PATH) as f:
            response = self.client.post(url, {
                'file': f,
                'verbosity': '0'})
            self.assertIn(
                b'MUSIC PUB CARTOONS',
                b''.join(response.streaming_content))
            self.assertEqual(response.status_code, 200)

        with open(CWR3_PATH) as f:
            response = self.client.post(url, {
                'file': f,
                'verbosity': '0',
                'download': '1'})
            data = json.loads(b''.join(response.streaming_content))
            submitter = data.get('submitter')
            work_registrations = data.get('work_registrations')
            file = data.get('file')
            self.assertEqual(
                file.get('name'),
                'CW190008MPC_0000_V3-0-0.ISR')
            self.assertEqual(
                len(work_registrations), 19)
            self.assertEqual(response.status_code, 200)

    def test_visual_validator(self):
        url = reverse('visual_validator')
        with open(CWR2_PATH) as f:
            response = self.client.post(url, {'file': f})
            self.assertIn(b'MUSIC PUB CARTOONS', b''.join(response.streaming_content))
            self.assertEqual(response.status_code, 200)
        with open(CWR3_PATH) as f:
            response = self.client.post(url, {'file': f})
            c = b''
            self.assertEqual(response.status_code, 200)
            for b in response.streaming_content:
                c += b
            self.assertIn(b'MUSIC PUB ARTISTS', c)
