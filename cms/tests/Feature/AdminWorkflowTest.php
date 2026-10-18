<?php

namespace Tests\Feature;

use App\Filament\Auth\Login;
use App\Filament\Resources\Articles\Pages\CreateArticle;
use App\Filament\Resources\Articles\Pages\EditArticle;
use App\Filament\Resources\Projects\Pages\EditProject;
use App\Filament\Resources\SitePages\Pages\EditSitePage;
use App\Models\Article;
use App\Models\Project;
use App\Models\SitePage;
use App\Models\User;
use App\Services\Publisher;
use Filament\Actions\Testing\TestAction;
use Filament\Facades\Filament;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Hash;
use Livewire\Livewire;
use Tests\TestCase;

class AdminWorkflowTest extends TestCase
{
    use RefreshDatabase;

    protected function setUp(): void
    {
        parent::setUp();
        Filament::setCurrentPanel(Filament::getPanel('admin'));
    }

    private function editor(): User
    {
        return User::factory()->create(['username' => 'editor', 'name' => 'Редактор', 'is_staff' => true, 'is_active' => true]);
    }

    public function test_existing_django_password_logs_in_without_reset(): void
    {
        $password = 'A-local-test-password';
        $django = 'pbkdf2_sha256$1000$local-salt$'.base64_encode(hash_pbkdf2('sha256', $password, 'local-salt', 1000, 32, true));
        $user = $this->editor();
        $user->update(['password' => $django]);
        Livewire::test(Login::class)->fillForm(['username' => 'editor', 'password' => $password])->call('authenticate')->assertHasNoFormErrors()->assertRedirect();
        $this->assertAuthenticatedAs($user);
        $this->assertTrue(Hash::check($password, $user->fresh()->password));
        $this->assertFalse(Hash::check('wrong-password', $django));
    }

    public function test_inactive_editor_cannot_sign_in(): void
    {
        $user = $this->editor();
        $user->update(['is_active' => false, 'password' => Hash::make('test-password')]);
        Livewire::test(Login::class)->fillForm(['username' => 'editor', 'password' => 'test-password'])->call('authenticate')->assertHasFormErrors(['username']);
        $this->assertGuest();
    }

    public function test_article_editor_preserves_rich_text_and_keeps_saved_draft_private(): void
    {
        $this->actingAs($this->editor());
        $article = Article::create(['title' => 'Тестовая статья', 'body' => "## Важный раздел\n\nТекст **с выделением** и [ссылкой](https://example.com).", 'published_payload' => ['title' => 'Ранее опубликовано'], 'first_published_at' => now()]);
        $oldSlug = $article->slug;
        Livewire::test(EditArticle::class, ['record' => $article->id])
            ->assertSuccessful()->assertSee('Дополнительно — вид в поиске')
            ->assertDontSee('Удалить черновик')->assertFormFieldDoesNotExist('slug')->assertFormFieldDoesNotExist('category')
            ->fillForm(['title' => 'Исправленное название', 'seo_title' => 'Поисковое название'])
            ->call('save', false)->assertHasNoFormErrors();
        $article->refresh();
        $this->assertSame($oldSlug, $article->slug);
        $this->assertSame(['title' => 'Ранее опубликовано'], $article->published_payload);
        $this->assertStringContainsString('## Важный раздел', $article->body);
        $this->assertStringContainsString('**с выделением**', $article->body);
        $this->assertStringContainsString('[ссылкой](https://example.com)', $article->body);
        $this->assertSame('Поисковое название', $article->seo_title);
    }

    public function test_new_article_requires_only_human_fields_and_generates_internal_values(): void
    {
        $this->actingAs($this->editor());
        Livewire::test(CreateArticle::class)->fillForm(['title' => 'Как подготовить объект', 'body' => "## Начало\n\nПроверьте доступ и подготовьте фотографии.", 'cover' => 'assets/client/pipeline-installation.jpg'])
            ->call('create')->assertHasNoFormErrors()->assertRedirect();
        $article = Article::firstOrFail();
        $this->assertSame('kak-podgotovit-obekt', $article->slug);
        $this->assertNotEmpty($article->summary);
        $this->assertNotEmpty($article->category);
        $this->assertNull($article->published_payload);
    }

    public function test_fixed_page_blocks_are_editable_without_system_names(): void
    {
        $this->actingAs($this->editor());
        $page = SitePage::create(['route' => 'about.html', 'label' => 'О компании', 'title' => 'О компании']);
        $block = $page->sections()->create(['key' => 'about', 'title' => 'Наш подход', 'body' => "Обычный текст.\n\n## Подзаголовок", 'position' => 0]);
        Livewire::test(EditSitePage::class, ['record' => $page->id])->assertSuccessful()->assertSee('Наш подход')
            ->assertFormFieldDoesNotExist('route')->fillForm(['title' => 'Команда Орион'])->call('save', false)->assertHasNoFormErrors();
        $this->assertSame('about.html', $page->fresh()->route);
        $this->assertStringContainsString('## Подзаголовок', $block->fresh()->body);
    }

    public function test_published_work_cannot_be_deleted_through_custom_action(): void
    {
        $this->actingAs($this->editor());
        $project = Project::create(['title' => 'Работа', 'summary' => 'Описание', 'description' => 'Текст', 'published_payload' => ['title' => 'Работа']]);
        Livewire::test(EditProject::class, ['record' => $project->id])->assertDontSee('Удалить черновик');
        $this->assertDatabaseHas('projects', ['id' => $project->id]);
    }

    public function test_publish_action_immediately_updates_visible_actions(): void
    {
        $this->actingAs($this->editor());
        $article = Article::create(['title' => 'Готовая статья', 'body' => 'Содержательный текст статьи.']);
        $this->mock(Publisher::class)->shouldReceive('publish')->once()->andReturnUsing(function ($record): string {
            $record->update(['published_payload' => ['title' => $record->title], 'first_published_at' => now()]);

            return 'test-build';
        });
        Livewire::test(EditArticle::class, ['record' => $article->id])
            ->callAction(TestAction::make('publish')->schemaComponent('form-actions', 'content'))
            ->assertHasNoFormErrors()->assertSee('Снять с публикации')->assertDontSee('Удалить черновик');
        $this->assertNotNull($article->fresh()->published_payload);
    }
}
