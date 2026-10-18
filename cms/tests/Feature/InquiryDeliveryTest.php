<?php

namespace Tests\Feature;

use App\Models\Service;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Http\Client\ConnectionException;
use Illuminate\Http\Client\Request as OutboundRequest;
use Illuminate\Http\UploadedFile;
use Illuminate\Support\Carbon;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Str;
use Tests\TestCase;

class InquiryDeliveryTest extends TestCase
{
    use RefreshDatabase;

    protected array $data;

    protected function setUp(): void
    {
        parent::setUp();
        config(['cms.inquiry_to_email' => 'owner@example.com', 'cms.site_url' => 'https://site.example']);
        Http::preventStrayRequests();
        Service::create(['slug' => 'insulation', 'title' => 'Неопубликованное название', 'summary' => 'Кратко', 'intro' => 'Описание', 'scope' => 'Задача', 'prepare' => 'Фотографии',
            'published_payload' => ['slug' => 'insulation', 'title' => 'Теплоизоляция']]);
        $this->data = ['name' => 'Тестовый клиент', 'phone' => '+7 (999) 123-45-67', 'service' => 'insulation',
            'message' => 'Нужно обсудить работы.', 'request_id' => (string) Str::uuid()];
    }

    private function fakeSuccess(): void
    {
        Http::fake(['formsubmit.co/*' => Http::response(['success' => 'true'], 200)]);
    }

    public function test_sends_all_russian_fields_full_message_and_both_private_attachments(): void
    {
        $this->fakeSuccess();
        Carbon::setTestNow(Carbon::parse('2026-10-18 19:43:00', 'UTC'));
        $this->beforeApplicationDestroyed(fn () => Carbon::setTestNow());
        $message = "Нужен монтаж: 120 м труб.\nВторой этаж, вход со двора.\nСхема & фотографии во вложениях.";
        $pdf = "%PDF-1.4\nTest drawing\n%%EOF";
        $png = "\x89PNG\r\n\x1a\n\x00\xff";
        $this->post('/api/inquiry/', [...$this->data, 'to' => 'attacker@example.com', 'message' => $message,
            'files' => [UploadedFile::fake()->createWithContent('plan.pdf', $pdf), UploadedFile::fake()->createWithContent('фото.png', $png)]])
            ->assertOk()->assertExactJson(['ok' => true])->assertHeader('Cache-Control', 'no-store, private');
        Http::assertSent(function (OutboundRequest $request) use ($message, $pdf, $png): bool {
            $fields = collect($request->data())->filter(fn ($part) => ! isset($part['filename']))->pluck('contents', 'name')->all();
            $this->assertSame('Тестовый клиент', $fields['Имя']);
            $this->assertSame($this->data['phone'], $fields['Телефон']);
            $this->assertSame('Теплоизоляция', $fields['Какие работы нужны']);
            $this->assertSame($message, $fields['Сообщение']);
            $this->assertSame("plan.pdf\nфото.png", $fields['Приложенные файлы']);
            $this->assertSame('19.10.2026 00:43 (Екатеринбург)', $fields['Дата заявки']);
            $this->assertSame($this->data['request_id'], $fields['Номер заявки']);
            $this->assertSame('Новая заявка с сайта СК Орион', $fields['_subject']);
            $this->assertSame('basic', $fields['_template']);
            $this->assertNotContains('attacker@example.com', $fields);

            return $request->url() === 'https://formsubmit.co/ajax/owner%40example.com'
                && $request->hasFile('attachment', $pdf, 'plan.pdf') && $request->hasFile('attachment1', $png, 'фото.png')
                && $request->hasHeader('Origin', 'https://site.example') && $request->hasHeader('Referer', 'https://site.example/request.html');
        });
    }

    public function test_all_five_files_and_empty_optional_fields_are_forwarded(): void
    {
        $this->fakeSuccess();
        $files = [];
        for ($index = 0; $index < 5; $index++) {
            $files[] = UploadedFile::fake()->createWithContent('plan-'.$index.'.pdf', '%PDF-'.$index);
        }
        $this->post('/api/inquiry/', [...$this->data, 'service' => '', 'message' => '', 'files' => $files])->assertOk();
        Http::assertSent(function (OutboundRequest $request): bool {
            $fields = collect($request->data())->filter(fn ($part) => ! isset($part['filename']))->pluck('contents', 'name');
            $this->assertSame('Не указано', $fields['Какие работы нужны']);
            $this->assertSame('Сообщение не указано.', $fields['Сообщение']);
            for ($index = 0; $index < 5; $index++) {
                $this->assertTrue($request->hasFile($index === 0 ? 'attachment' : 'attachment'.$index, '%PDF-'.$index, 'plan-'.$index.'.pdf'));
            }

            return true;
        });
    }

    public function test_invalid_contacts_bots_unknown_services_file_counts_sizes_and_formats_never_send(): void
    {
        $this->fakeSuccess();
        $cases = [
            ['phone' => '123'], ['website' => 'spam'], ['service' => 'unpublished'], ['name' => "bad\nname"], ['name' => ['bad']],
            ['message' => str_repeat('x', 5001)], ['request_id' => 'invalid'], ['files' => [UploadedFile::fake()->create('bad.exe', 1)]],
            ['files' => array_map(fn ($index) => UploadedFile::fake()->create('plan-'.$index.'.pdf', 1), range(1, 6))],
            ['files' => [UploadedFile::fake()->create('large.pdf', 10241)]],
        ];
        foreach ($cases as $overrides) {
            $this->post('/api/inquiry/', [...$this->data, ...$overrides])->assertStatus(400);
        }
        Http::assertNothingSent();
    }

    public function test_provider_false_activation_rejection_and_timeout_never_claim_delivery(): void
    {
        $answer = [];
        $status = 200;
        $disconnect = false;
        Http::fake(function () use (&$answer, &$status, &$disconnect) {
            if ($disconnect) {
                throw new ConnectionException('Test timeout');
            }

            return Http::response($answer, $status);
        });
        foreach ([['success' => 'false', 'message' => 'Needs Activation'], ['success' => 'false'], ['success' => false], ['message' => 'invalid']] as $index => $body) {
            $answer = $body;
            $this->post('/api/inquiry/', $this->data)->assertStatus($index === 0 ? 503 : 502)->assertJsonMissing(['ok' => true]);
        }
        $answer = 'private provider details';
        $status = 403;
        $this->post('/api/inquiry/', $this->data)->assertStatus(502)->assertDontSee('private provider details');
        $disconnect = true;
        $this->post('/api/inquiry/', $this->data)->assertStatus(502)->assertJsonMissing(['ok' => true]);
    }

    public function test_disabled_configuration_and_unpublished_services_are_not_submitted(): void
    {
        $this->fakeSuccess();
        $this->get('/api/inquiry/')->assertOk()->assertJsonPath('enabled', true)->assertJsonStructure(['csrfToken']);
        Service::first()->update(['published_payload' => null]);
        $this->post('/api/inquiry/', $this->data)->assertStatus(400);
        config(['cms.inquiry_to_email' => '']);
        $this->get('/api/inquiry/')->assertJsonPath('enabled', false);
        $this->post('/api/inquiry/', $this->data)->assertStatus(503);
        Http::assertNothingSent();
    }

    public function test_csrf_is_required_and_a_foreign_origin_is_rejected_even_with_token(): void
    {
        $this->fakeSuccess();
        $this->app->detectEnvironment(fn () => 'local');
        $this->post('/api/inquiry/', $this->data)->assertStatus(419);
        $this->withSession(['_token' => 'known-test-csrf-token'])->withHeader('X-CSRFToken', 'known-test-csrf-token')
            ->withHeader('Origin', 'https://untrusted.example')->post('/api/inquiry/', $this->data)->assertStatus(419);
        Http::assertNothingSent();
        $this->withSession(['_token' => 'known-test-csrf-token'])->withHeader('X-CSRFToken', 'known-test-csrf-token')
            ->withHeader('Origin', 'http://localhost')->post('http://localhost/api/inquiry/', $this->data)->assertOk();
        Http::assertSentCount(1);
    }
}
