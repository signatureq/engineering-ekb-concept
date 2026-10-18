<?php

namespace Tests\Feature;

use App\Exceptions\PublicationException;
use App\Models\Article;
use App\Models\Project;
use App\Models\ProjectPhoto;
use App\Models\Service;
use App\Models\SitePage;
use App\Models\User;
use App\Services\ImageStore;
use App\Services\Publisher;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Http\UploadedFile;
use Illuminate\Support\Facades\File;
use Illuminate\Support\Facades\URL;
use Illuminate\Validation\ValidationException;
use Tests\Concerns\UsesCmsContent;
use Tests\TestCase;

class CmsPublishingTest extends TestCase
{
    use RefreshDatabase, UsesCmsContent;

    protected function setUp(): void
    {
        parent::setUp();
        $this->configureCmsTest();
        $this->importContent();
    }

    public function test_publishing_one_record_keeps_other_drafts_related_titles_and_positions_private(): void
    {
        $publisher = app(Publisher::class);
        $publisher->build();
        $home = SitePage::where('route', 'index.html')->firstOrFail();
        $home->update(['intro' => 'PRIVATE HOME INTRO']);
        $home->sections()->first()->update(['body' => 'PRIVATE SECTION BODY']);
        [$first, $second] = Service::orderBy('position')->get()->take(2)->all();
        $firstPublishedTitle = $first->published_payload['title'];
        $first->update(['title' => 'PRIVATE SERVICE TITLE', 'position' => 999]);
        $second->update(['title' => 'Проверенная опубликованная услуга']);
        $publisher->publish($second);
        $html = File::get(config('cms.public_root').'/services.html');
        $this->assertStringContainsString('Проверенная опубликованная услуга', $html);
        $this->assertStringNotContainsString('PRIVATE SERVICE TITLE', $html);
        $this->assertLessThan(strpos($html, 'Проверенная опубликованная услуга'), strpos($html, $firstPublishedTitle));
        $this->assertStringNotContainsString('PRIVATE HOME INTRO', File::get(config('cms.public_root').'/index.html'));
        $this->assertStringNotContainsString('PRIVATE SECTION BODY', File::get(config('cms.public_root').'/index.html'));
        $publisher->publish($home);
        $this->assertStringContainsString('PRIVATE HOME INTRO', File::get(config('cms.public_root').'/index.html'));
        $this->assertStringContainsString('PRIVATE SECTION BODY', File::get(config('cms.public_root').'/index.html'));
        $this->assertStringNotContainsString('PRIVATE SERVICE TITLE', File::get(config('cms.public_root').'/index.html'));
    }

    public function test_private_gallery_upload_preview_publication_hiding_and_stable_automatic_address(): void
    {
        $publisher = app(Publisher::class);
        $publisher->build();
        $project = Project::create(['title' => 'Монтаж на новом объекте', 'summary' => 'О выполненных работах', 'description' => 'Описание **выполненных работ**.', 'category' => 'inside']);
        $slug = $project->slug;
        $this->assertSame('montazh-na-novom-obekte', $slug);
        $photoPath = app(ImageStore::class)->store(new UploadedFile(config('cms.site_root').'/assets/client/pipeline-installation.jpg', 'photo.jpg', 'image/jpeg', null, true));
        ProjectPhoto::create(['project_id' => $project->id, 'image_upload' => $photoPath, 'caption' => 'Монтаж оборудования']);
        $this->assertSame(IMAGETYPE_WEBP, getimagesize(config('cms.media_root').'/'.$photoPath)[2]);
        $publicPhoto = config('cms.public_root').'/assets/uploads/'.basename($photoPath);
        $this->assertFileDoesNotExist($publicPhoto);
        $this->get(route('cms.preview', ['kind' => 'project', 'id' => $project->id]))->assertRedirect('/admin/login');
        $this->get(URL::temporarySignedRoute('cms.media', now()->addHour(), ['path' => $photoPath]))->assertRedirect('/admin/login');
        $this->actingAs(User::findOrFail(7));
        $previousBuild = readlink(config('cms.public_root'));
        $preview = $this->get(route('cms.preview', ['kind' => 'project', 'id' => $project->id]));
        $preview->assertOk()->assertSee('Предпросмотр сохранённой версии')->assertSee('/admin/media/content/', false);
        $this->assertStringContainsString('noindex', $preview->headers->get('X-Robots-Tag'));
        $this->assertSame($previousBuild, readlink(config('cms.public_root')));
        $this->assertFileDoesNotExist($publicPhoto);
        $this->get(URL::temporarySignedRoute('cms.media', now()->addHour(), ['path' => $photoPath]))->assertOk();
        $publisher->publish($project);
        $this->assertFileExists($publicPhoto);
        $this->assertStringContainsString('<strong>выполненных работ</strong>', File::get(config('cms.public_root').'/works/'.$slug.'.html'));
        $project->refresh()->update(['title' => 'Другое название']);
        $publisher->publish($project);
        $this->assertSame($slug, $project->fresh()->slug);
        $publisher->unpublish($project);
        $this->assertFileDoesNotExist(config('cms.public_root').'/works/'.$slug.'.html');
        $this->assertStringNotContainsString('/works/'.$slug.'.html', File::get(config('cms.public_root').'/sitemap.xml'));
    }

    public function test_failed_build_rolls_back_snapshot_and_keeps_live_website_and_saved_draft(): void
    {
        $publisher = app(Publisher::class);
        $publisher->build();
        $home = SitePage::where('route', 'index.html')->firstOrFail();
        $snapshot = $home->published_payload;
        $home->update(['title' => 'Сохранённый черновик после ошибки']);
        $previous = readlink(config('cms.public_root'));
        $failing = new class(app(ImageStore::class)) extends Publisher
        {
            protected function runGenerator(array $command): void
            {
                throw new PublicationException('Контрольный сбой генератора');
            }
        };
        try {
            $failing->publish($home);
            $this->fail('The failed build must not publish.');
        } catch (PublicationException) {
            $home->refresh();
            $this->assertSame($snapshot, $home->published_payload);
            $this->assertSame('Сохранённый черновик после ошибки', $home->title);
            $this->assertSame($previous, readlink(config('cms.public_root')));
        }
    }

    public function test_preview_explains_missing_gallery_and_private_paths_require_active_editor(): void
    {
        $project = Project::create(['title' => 'Новая работа', 'summary' => 'Описание работы', 'description' => 'Подробности']);
        $this->actingAs(User::findOrFail(7));
        $this->get(route('cms.preview', ['kind' => 'project', 'id' => $project->id]))->assertStatus(400)->assertSee('Добавьте хотя бы одну фотографию');
        $path = Article::first()->cover_upload;
        $this->get('/admin/media/'.$path)->assertForbidden();
        $this->get(URL::temporarySignedRoute('cms.media', now()->addHour(), ['path' => '../import.json']))->assertNotFound();
        User::findOrFail(7)->update(['is_active' => false]);
        $this->actingAs(User::findOrFail(7));
        $this->get(URL::temporarySignedRoute('cms.media', now()->addHour(), ['path' => $path]))->assertNotFound();
    }

    public function test_published_addresses_cannot_be_changed_and_main_pages_cannot_be_hidden(): void
    {
        $service = Service::first();
        try {
            $service->update(['slug' => 'different-address']);
            $this->fail('A published address must remain stable.');
        } catch (ValidationException) {
            $this->assertNotSame('different-address', $service->fresh()->slug);
        }
        $this->expectException(PublicationException::class);
        app(Publisher::class)->unpublish(SitePage::first());
    }

    public function test_svg_and_oversize_images_are_rejected_without_creating_public_files(): void
    {
        foreach ([UploadedFile::fake()->createWithContent('bad.svg', '<svg xmlns="http://www.w3.org/2000/svg"><script/></svg>'), UploadedFile::fake()->create('large.jpg', 5121)] as $file) {
            try {
                app(ImageStore::class)->store($file);
                $this->fail('Invalid photographs must be rejected.');
            } catch (ValidationException) {
                $this->assertFalse(is_dir(config('cms.public_root').'/assets/uploads'));
            }
        }
    }

    public function test_empty_optional_form_values_are_normalized_without_losing_nullable_state(): void
    {
        $article = Article::create(['title' => 'Новая статья', 'body' => 'Первый абзац статьи.', 'cover' => 'assets/client/pipeline-installation.jpg',
            'seo_title' => null, 'seo_description' => null, 'cover_upload' => null]);
        $this->assertSame('', $article->seo_title);
        $this->assertSame('', $article->cover_upload);
        $this->assertNull($article->published_payload);
        $this->assertNull($article->first_published_at);
        $page = SitePage::first();
        $page->update(['intro' => null, 'seo_title' => null, 'image_upload' => null]);
        $this->assertSame('', $page->fresh()->intro);
        $this->assertNotNull($page->fresh()->published_payload);
        $section = $page->sections()->first();
        $section->update(['body' => null, 'image_upload' => null]);
        $this->assertSame('', $section->fresh()->body);
        $photo = ProjectPhoto::first();
        $source = $photo->source;
        $photo->update(['caption' => null]);
        $this->assertSame('', $photo->fresh()->caption);
        $this->assertSame($source, $photo->fresh()->source);
    }

    public function test_rebuilds_keep_exactly_current_and_two_previous_complete_versions(): void
    {
        $builds = [];
        for ($index = 0; $index < 5; $index++) {
            $builds[] = app(Publisher::class)->build();
        }
        $this->assertCount(3, File::directories($this->cmsTemporary.'/builds'));
        foreach (array_slice($builds, -3) as $build) {
            $this->assertFileExists($build.'/public/index.html');
        }
        $this->assertSame($builds[4].'/public', readlink(config('cms.public_root')));
        $this->assertDirectoryDoesNotExist($builds[0]);
        $this->assertDirectoryDoesNotExist($builds[1]);
    }
}
