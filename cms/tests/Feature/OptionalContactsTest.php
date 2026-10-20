<?php

namespace Tests\Feature;

use App\Filament\Pages\Contacts;
use App\Models\SiteSetting;
use App\Models\User;
use Filament\Facades\Filament;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\File;
use Livewire\Livewire;
use Tests\Concerns\UsesCmsContent;
use Tests\TestCase;

class OptionalContactsTest extends TestCase
{
    use RefreshDatabase, UsesCmsContent;

    protected function setUp(): void
    {
        parent::setUp();
        $this->configureCmsTest();
        $this->importContent();
        Filament::setCurrentPanel(Filament::getPanel('admin'));
        $this->actingAs(User::findOrFail(7));
    }

    public function test_optional_contacts_publish_from_simple_form_and_disappear_when_cleared(): void
    {
        $maxUrl = 'https://max.ru/u/example-profile-for-local-test';
        $address = 'Тестовый адрес офиса для проверки';
        Livewire::test(Contacts::class)->fillForm(['max_url' => $maxUrl, 'office_address' => $address])
            ->call('save')->assertHasNoFormErrors();
        $record = SiteSetting::firstOrFail();
        $this->assertSame($maxUrl, $record->published_payload['max_url']);
        $html = File::get(config('cms.public_root').'/contacts.html');
        $this->assertStringContainsString('href="'.$maxUrl.'"', $html);
        $this->assertStringContainsString('<address>'.$address.'</address>', $html);
        $this->assertStringContainsString('contact-dock has-messenger', $html);

        Livewire::test(Contacts::class)->fillForm(['max_url' => '', 'office_address' => ''])
            ->call('save')->assertHasNoFormErrors();
        $html = File::get(config('cms.public_root').'/contacts.html');
        $this->assertStringNotContainsString($maxUrl, $html);
        $this->assertStringNotContainsString('<address>', $html);
        $this->assertStringNotContainsString('has-messenger', $html);
    }

    public function test_unrelated_urls_are_rejected_without_publishing_contacts(): void
    {
        $published = SiteSetting::firstOrFail()->published_payload;
        Livewire::test(Contacts::class)->fillForm(['max_url' => 'https://example.com/not-max'])
            ->call('save')->assertHasFormErrors(['max_url' => 'regex']);
        $this->assertSame($published, SiteSetting::firstOrFail()->published_payload);
    }

    public function test_existing_published_settings_are_not_marked_changed_by_new_empty_fields(): void
    {
        $record = SiteSetting::firstOrFail();
        $oldSnapshot = $record->published_payload;
        unset($oldSnapshot['max_url'], $oldSnapshot['office_address']);
        $record->update(['published_payload' => $oldSnapshot]);
        $this->assertSame('Опубликовано', $record->fresh()->publicationStatus());
        $record->update(['max_url' => 'https://max.ru/u/example-profile-for-local-test']);
        $this->assertSame('Есть изменения', $record->fresh()->publicationStatus());
        $this->assertSame($oldSnapshot, $record->fresh()->published_payload);
    }
}
