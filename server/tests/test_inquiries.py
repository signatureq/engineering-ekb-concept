import uuid
from email import policy
from email.parser import BytesParser
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from cms.models import Service


@override_settings(SECURE_SSL_REDIRECT=False, ALLOWED_HOSTS=['testserver'],
                   INQUIRY_TO_EMAIL='owner@example.com', INQUIRY_SITE_URL='https://site.example')
class InquiryTests(TestCase):
    def setUp(self):
        self.service = Service.objects.create(slug='insulation', title='Черновик нового названия',
            published_payload={'slug': 'insulation', 'title': 'Теплоизоляция'})
        self.client = Client(enforce_csrf_checks=True)
        self.token = self.client.get('/api/inquiry/').json()['csrfToken']
        self.data = {'name': 'Тестовый клиент', 'phone': '+7 (999) 123-45-67',
                     'service': 'insulation', 'message': 'Нужно обсудить работы.',
                     'request_id': str(uuid.uuid4())}

    def post(self, data=None, **extra):
        return self.client.post('/api/inquiry/', self.data if data is None else data,
                                HTTP_X_CSRFTOKEN=self.token, **extra)

    def provider(self, mock):
        sent = MagicMock()
        sent.__enter__.return_value.read.return_value = b'{"success":"true","message":"Thanks!"}'
        mock.return_value = sent

    @patch('cms.inquiries.urlopen')
    def test_sends_to_configured_recipient_with_private_attachments(self, outbound):
        self.provider(outbound)
        data = {**self.data, 'to': 'attacker@example.com',
                'files': SimpleUploadedFile('plan.pdf', b'%PDF-test', 'application/pdf')}
        result = self.post(data)
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json(), {'ok': True})
        request = outbound.call_args.args[0]
        self.assertEqual(request.full_url, 'https://formsubmit.co/ajax/owner@example.com')
        multipart = BytesParser(policy=policy.default).parsebytes(
            ('Content-Type: ' + request.get_header('Content-type') + '\r\n\r\n').encode() + request.data)
        parts = list(multipart.iter_parts())
        fields = {part.get_param('name', header='content-disposition'): part.get_payload(decode=True).decode()
                  for part in parts if not part.get_filename()}
        photo = next(part for part in parts if part.get_filename())
        self.assertEqual(photo.get_payload(decode=True), b'%PDF-test')
        self.assertEqual(photo.get_filename(), 'plan.pdf')
        self.assertEqual(fields['Направление работ'], 'Теплоизоляция')
        self.assertEqual(fields['Номер заявки'], self.data['request_id'])
        self.assertEqual(request.get_header('Origin'), 'https://site.example')
        self.assertEqual(request.get_header('Referer'), 'https://site.example/request.html')
        self.assertNotIn('attacker@example.com', fields.values())
        self.assertIn('no-store', result['Cache-Control'])

    @patch('cms.inquiries.urlopen')
    def test_invalid_contact_bot_and_files_do_not_send(self, outbound):
        cases = [dict(self.data, phone='123'), dict(self.data, website='spam'),
                 dict(self.data, service='unknown'), dict(self.data, name='a\nb'),
                 dict(self.data, message='x' * 5001), dict(self.data, request_id='invalid'),
                 dict(self.data, files=SimpleUploadedFile('script.exe', b'bad')),
                 dict(self.data, files=[SimpleUploadedFile(f'{n}.pdf', b'pdf') for n in range(6)]),
                 dict(self.data, files=SimpleUploadedFile('large.pdf', b'x' * (10 * 1024 * 1024 + 1)))]
        for data in cases:
            self.assertEqual(self.post(data).status_code, 400)
        outbound.assert_not_called()

    @patch('cms.inquiries.urlopen')
    def test_csrf_required_and_cross_origin_blocked(self, outbound):
        self.assertEqual(self.client.post('/api/inquiry/', self.data).status_code, 403)
        self.assertEqual(self.post(HTTP_ORIGIN='https://untrusted.example').status_code, 403)
        outbound.assert_not_called()

    @patch('cms.inquiries.urlopen')
    def test_provider_rejection_does_not_claim_success_or_expose_details(self, outbound):
        outbound.side_effect = HTTPError('https://formsubmit.co/ajax/owner@example.com', 403, 'private provider details', {}, None)
        result = self.post()
        self.assertEqual(result.status_code, 502)
        self.assertNotIn('ok', result.json())
        self.assertNotContains(result, 'private provider details', status_code=502)

    @patch('cms.inquiries.urlopen', side_effect=TimeoutError)
    def test_timeout_preserves_retry_as_an_error(self, outbound):
        self.assertEqual(self.post().status_code, 502)

    @patch('cms.inquiries.urlopen')
    def test_activation_and_false_success_are_not_delivery(self, outbound):
        self.provider(outbound)
        read = outbound.return_value.__enter__.return_value.read
        read.return_value = b'{"success":"false","message":"This form needs Activation"}'
        self.assertEqual(self.post().status_code, 503)
        read.return_value = b'{"success":"false","message":"Rejected"}'
        self.assertEqual(self.post().status_code, 502)
        read.return_value = b'{"success":true}'
        self.assertEqual(self.post().status_code, 200)

    @override_settings(INQUIRY_TO_EMAIL='')
    @patch('cms.inquiries.urlopen')
    def test_missing_configuration_disables_delivery(self, outbound):
        self.assertFalse(self.client.get('/api/inquiry/').json()['enabled'])
        self.assertEqual(self.post().status_code, 503)
        outbound.assert_not_called()

    @patch('cms.inquiries.urlopen')
    def test_added_services_use_published_name_and_reject_unpublished_entries(self, outbound):
        self.provider(outbound)
        added = Service.objects.create(slug='ventilyaciya', title='Черновик вентиляции')
        self.assertEqual(self.post(dict(self.data, service=added.slug)).status_code, 400)
        outbound.assert_not_called()
        added.published_payload = {'slug': added.slug, 'title': 'Монтаж вентиляции'}
        added.save(update_fields=['published_payload'])
        self.assertEqual(self.post(dict(self.data, service=added.slug)).status_code, 200)
        body = outbound.call_args.args[0].data.decode()
        self.assertIn('Монтаж вентиляции', body)
        self.assertNotIn('Черновик вентиляции', body)
        added.published_payload = None
        added.save(update_fields=['published_payload'])
        outbound.reset_mock()
        self.assertEqual(self.post(dict(self.data, service=added.slug)).status_code, 400)
        outbound.assert_not_called()
