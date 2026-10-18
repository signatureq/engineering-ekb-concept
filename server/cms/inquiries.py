"""Same-origin inquiry endpoint backed by FormSubmit."""
import json
import logging
import re
import uuid
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from django.conf import settings
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.views.decorators.http import require_http_methods

logger = logging.getLogger(__name__)
MAX_ATTACHMENTS = 5
MAX_BYTES = 10 * 1024 * 1024
EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.dwg', '.dxf', '.zip'}
SERVICES = {
    '': 'Не указано',
    'pipeline-installation': 'Монтаж трубопроводов',
    'insulation': 'Теплоизоляция',
    'metering': 'Узлы учёта',
    'emergency': 'Аварийные работы',
}


def response(data, status=200):
    result = JsonResponse(data, status=status)
    result['Cache-Control'] = 'no-store'
    result['X-Robots-Tag'] = 'noindex,nofollow'
    return result


def multipart_body(fields, files):
    boundary = 'orion-' + uuid.uuid4().hex
    parts = []
    for key, value in fields.items():
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n'.encode())
    for index, file in enumerate(files):
        filename = file.name.replace('\r', '').replace('\n', '').replace('"', "'").replace('\\', '_')
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="attachment{index}"; filename="{filename}"\r\nContent-Type: application/octet-stream\r\n\r\n'.encode())
        parts.extend([file.read(), b'\r\n'])
    parts.append(f'--{boundary}--\r\n'.encode())
    return b''.join(parts), 'multipart/form-data; boundary=' + boundary


@require_http_methods(['GET', 'POST'])
def inquiry(request):
    enabled = bool(settings.INQUIRY_TO_EMAIL)
    if request.method == 'GET':
        return response({'enabled': enabled, 'csrfToken': get_token(request)})
    if not enabled:
        return response({'error': 'Отправка пока недоступна. Пожалуйста, позвоните нам.'}, 503)

    name = request.POST.get('name', '').strip()
    phone = request.POST.get('phone', '').strip()
    message = request.POST.get('message', '').strip()
    service = request.POST.get('service', '')
    if (request.POST.get('website') or not name or len(name) > 100 or
            any(char in name for char in '\r\n') or len(phone) > 40 or
            not re.fullmatch(r'[+\d\s()\-]+', phone) or
            not 10 <= len(re.sub(r'\D', '', phone)) <= 15 or
            len(message) > 5000 or service not in SERVICES):
        return response({'error': 'Проверьте имя и телефон. В описании допускается до 5000 символов.'}, 400)
    try:
        request_id = str(uuid.UUID(request.POST.get('request_id', '')))
    except (ValueError, AttributeError):
        return response({'error': 'Обновите страницу и попробуйте ещё раз.'}, 400)
    files = request.FILES.getlist('files')
    if (len(files) > MAX_ATTACHMENTS or sum(file.size for file in files) > MAX_BYTES or
            any(Path(file.name).suffix.lower() not in EXTENSIONS for file in files)):
        return response({'error': 'Приложите до 5 файлов общим размером до 10 МБ в указанных форматах.'}, 400)

    fields = {
        'Имя': name,
        'Телефон': phone,
        'Направление работ': SERVICES[service],
        'Описание задачи': message or 'Описание не указано.',
        'Номер заявки': request_id,
        '_subject': 'Новая заявка с сайта СК Орион',
        '_template': 'table',
        # CSRF, bot-trap and IP rate limiting are enforced by our own server.
        '_captcha': 'false',
    }
    body, content_type = multipart_body(fields, files)
    outbound = Request('https://formsubmit.co/ajax/' + quote(settings.INQUIRY_TO_EMAIL, safe='@'),
                       data=body, method='POST',
                       headers={'Content-Type': content_type, 'Accept': 'application/json',
                                'Origin': settings.INQUIRY_SITE_URL,
                                'Referer': settings.INQUIRY_SITE_URL + '/request.html',
                                'User-Agent': 'OrionWebsite/1.0'})
    try:
        with urlopen(outbound, timeout=20) as sent:
            result = json.loads(sent.read(65536))
        if not isinstance(result, dict):
            raise ValueError('Invalid provider response')
        if not (result.get('success') is True or result.get('success') == 'true'):
            if 'activat' in str(result.get('message', '')).lower():
                return response({'error': 'Приём заявок ещё настраивается. Пожалуйста, позвоните нам.'}, 503)
            raise ValueError('Provider rejected submission')
    except (HTTPError, URLError, TimeoutError, OSError, ValueError) as error:
        # Do not log contact data, file contents, API responses or credentials.
        logger.warning('Inquiry delivery failed (%s).', type(error).__name__)
        return response({'error': 'Не удалось отправить заявку. Данные остались в форме — попробуйте ещё раз или позвоните нам.'}, 502)
    return response({'ok': True})
