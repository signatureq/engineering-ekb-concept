<?php

namespace App\Http\Controllers;

use App\Models\Service;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Http\UploadedFile;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Log;
use Illuminate\Support\Str;

class InquiryController extends Controller
{
    private const EXTENSIONS = ['jpg', 'jpeg', 'png', 'webp', 'pdf', 'doc', 'docx', 'xls', 'xlsx', 'dwg', 'dxf', 'zip'];

    public function __invoke(Request $request): JsonResponse
    {
        $recipient = config('cms.inquiry_to_email');
        if ($request->isMethod('get')) {
            return $this->respond(['enabled' => (bool) $recipient, 'csrfToken' => csrf_token()]);
        }
        if (! $recipient) {
            return $this->respond(['error' => 'Отправка пока недоступна. Пожалуйста, позвоните нам.'], 503);
        }
        foreach (['name', 'phone', 'message', 'service'] as $field) {
            if ($request->input($field) !== null && ! is_string($request->input($field))) {
                return $this->respond(['error' => 'Проверьте заполненные поля заявки.'], 400);
            }
        }
        $name = trim((string) $request->input('name', ''));
        $phone = trim((string) $request->input('phone', ''));
        $message = trim((string) $request->input('message', ''));
        $service = (string) $request->input('service', '');
        $services = ['' => 'Не указано'];
        foreach (Service::query()->whereNotNull('published_payload')->get() as $record) {
            $payload = $record->published_payload;
            $services[$payload['slug']] = $payload['title'];
        }
        $digits = preg_replace('/\D/', '', $phone);
        if ($request->input('website') || ! $name || mb_strlen($name) > 100 || preg_match('/[\r\n]/', $name)
            || mb_strlen($phone) > 40 || ! preg_match('/\A[+\d\s()\-]+\z/u', $phone)
            || strlen($digits) < 10 || strlen($digits) > 15 || mb_strlen($message) > 5000 || ! array_key_exists($service, $services)) {
            return $this->respond(['error' => 'Проверьте имя и телефон. В описании допускается до 5000 символов.'], 400);
        }
        $requestId = $request->input('request_id', '');
        if (! is_string($requestId) || ! Str::isUuid($requestId)) {
            return $this->respond(['error' => 'Обновите страницу и попробуйте ещё раз.'], 400);
        }
        $files = $request->file('files', []);
        if ($files instanceof UploadedFile) {
            $files = [$files];
        }
        if (! is_array($files) || count($files) > 5 || array_sum(array_map(fn ($file) => $file instanceof UploadedFile ? $file->getSize() : 11 * 1024 * 1024, $files)) > 10 * 1024 * 1024) {
            return $this->badFiles();
        }
        foreach ($files as $file) {
            if (! $file instanceof UploadedFile || ! $file->isValid() || ! in_array(strtolower($file->getClientOriginalExtension()), self::EXTENSIONS, true)) {
                return $this->badFiles();
            }
        }
        $fields = [
            'Имя' => $name, 'Телефон' => $phone, 'Какие работы нужны' => $services[$service],
            'Сообщение' => $message ?: 'Сообщение не указано.',
            'Приложенные файлы' => implode("\n", array_map(fn ($file) => $this->filename($file), $files)) ?: 'Без вложений',
            'Дата заявки' => now(config('cms.timezone'))->format('d.m.Y H:i').' (Екатеринбург)',
            'Номер заявки' => $requestId, '_subject' => 'Новая заявка с сайта СК Орион', '_template' => 'basic', '_captcha' => 'false',
        ];
        $origin = config('cms.site_url');
        $outbound = Http::acceptJson()->timeout(20)->connectTimeout(10)->withHeaders([
            'Origin' => $origin, 'Referer' => $origin.'/request.html', 'User-Agent' => 'OrionWebsite/2.0',
        ])->asMultipart();
        foreach ($files as $index => $file) {
            $outbound->attach($index === 0 ? 'attachment' : 'attachment'.$index, file_get_contents($file->getPathname()), $this->filename($file), ['Content-Type' => $file->getMimeType() ?: 'application/octet-stream']);
        }
        try {
            $sent = $outbound->post('https://formsubmit.co/ajax/'.rawurlencode($recipient), $fields);
            $result = $sent->json();
            if (! $sent->successful() || ! is_array($result) || ! in_array($result['success'] ?? null, [true, 'true'], true)) {
                if (is_array($result) && str_contains(strtolower((string) ($result['message'] ?? '')), 'activat')) {
                    return $this->respond(['error' => 'Приём заявок ещё настраивается. Пожалуйста, позвоните нам.'], 503);
                }
                throw new \RuntimeException('Provider rejected submission');
            }
        } catch (\Throwable $error) {
            Log::warning('Inquiry delivery failed.', ['exception' => $error::class]);

            return $this->respond(['error' => 'Не удалось отправить заявку. Данные остались в форме — попробуйте ещё раз или позвоните нам.'], 502);
        }

        return $this->respond(['ok' => true]);
    }

    private function filename(UploadedFile $file): string
    {
        return str_replace(["\r", "\n", '"', '\\'], ['', '', "'", '_'], $file->getClientOriginalName());
    }

    private function badFiles(): JsonResponse
    {
        return $this->respond(['error' => 'Приложите до 5 файлов общим размером до 10 МБ в указанных форматах.'], 400);
    }

    private function respond(array $data, int $status = 200): JsonResponse
    {
        return response()->json($data, $status)->header('Cache-Control', 'no-store')->header('X-Robots-Tag', 'noindex,nofollow');
    }
}
