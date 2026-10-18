<?php

namespace Tests\Feature;

use App\Exceptions\PublicationException;
use App\Models\Article;
use App\Models\Project;
use App\Models\ProjectPhoto;
use App\Models\Service;
use App\Models\SitePage;
use App\Models\User;
use App\Services\ContentImporter;
use App\Services\Publisher;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Hash;
use Tests\Concerns\UsesCmsContent;
use Tests\TestCase;

class CmsMigrationTest extends TestCase
{
    use RefreshDatabase, UsesCmsContent;

    protected function setUp(): void
    {
        parent::setUp();
        $this->configureCmsTest();
    }

    public function test_import_preserves_ids_snapshots_private_drafts_timestamps_and_password_hashes(): void
    {
        $export = $this->publicContentExport();
        $export['tables']['articles'][0]['title'] = 'Неопубликованное название';
        $export['tables']['site_pages'][0]['intro'] = 'Неопубликованный первый экран';
        $this->importContent($export);
        $article = Article::findOrFail(1);
        $this->assertSame('Неопубликованное название', $article->title);
        $this->assertSame($export['tables']['articles'][0]['published_payload'], $article->published_payload);
        $this->assertSame($export['tables']['articles'][0]['created_at'], $article->getRawOriginal('created_at'));
        $this->assertSame($export['tables']['users'][0]['password'], User::findOrFail(7)->getRawOriginal('password'));
        $this->assertTrue(Hash::check('test-password-not-secret', User::findOrFail(7)->password));
        $this->assertSame($export['tables']['project_photos'][0]['source'], ProjectPhoto::findOrFail(1)->source);
        $this->assertSame($export['tables']['projects'][0]['service_id'], Project::findOrFail(1)->service_id);
        $this->assertSame($export['tables']['site_pages'][0]['published_payload'], SitePage::findOrFail(1)->published_payload);
        $this->assertStringStartsWith('legacy/assets/', Article::findOrFail(2)->cover_upload);
        $this->assertFileExists(config('cms.media_root').'/'.Article::findOrFail(2)->cover_upload);
        $this->assertSame('Опубликовано', Article::findOrFail(2)->publicationStatus());
        $this->assertSame('Опубликовано', Service::first()->publicationStatus());
        $this->assertSame('Есть изменения', $article->publicationStatus());
    }

    public function test_reimport_refuses_editor_changes_and_never_restores_deleted_records(): void
    {
        $this->importContent();
        Article::query()->delete();
        Project::query()->delete();
        Service::query()->delete();
        $page = SitePage::first();
        $page->update(['title' => 'Изменено редактором']);
        try {
            app(ContentImporter::class)->import($this->cmsTemporary.'/import.json');
            $this->fail('A second import must fail.');
        } catch (PublicationException $error) {
            $this->assertStringContainsString('Повторный импорт запрещён', $error->getMessage());
        }
        $this->assertSame(0, Article::count());
        $this->assertSame(0, Service::count());
        $this->assertSame(0, Project::count());
        $this->assertSame('Изменено редактором', $page->fresh()->title);
        app(Publisher::class)->build();
        $this->assertStringNotContainsString('works/naruzhnye-seti.html', file_get_contents(config('cms.public_root').'/works.html'));
        $this->assertStringNotContainsString('services/pipeline-installation.html', file_get_contents(config('cms.public_root').'/sitemap.xml'));
    }

    public function test_invalid_import_rolls_back_all_rows_without_logging_private_values(): void
    {
        $export = $this->publicContentExport();
        $export['tables']['projects'][0]['service_id'] = 987654;
        try {
            $this->importContent($export);
            $this->fail('Broken foreign keys must fail.');
        } catch (\Throwable) {
            $this->assertSame(0, User::count());
            $this->assertSame(0, SitePage::count());
            $this->assertSame(0, DB::table('content_imports')->count());
        }
    }
}
