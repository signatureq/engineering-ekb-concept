<?php

namespace App\Services;

use App\Exceptions\PublicationException;
use App\Models\Article;
use App\Models\Project;
use App\Models\Service;
use App\Models\SitePage;
use App\Models\SiteSetting;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\File;
use Illuminate\Support\Facades\Log;
use Illuminate\Support\Facades\Validator;
use Illuminate\Support\Str;
use Symfony\Component\Process\Process;

class Publisher
{
    public function __construct(protected ImageStore $images) {}

    public function draftPayload(Model $record): array
    {
        if ($record instanceof SiteSetting) {
            return $record->only(SiteSetting::CONTENT_FIELDS);
        }
        $common = $record->only(['title', 'seo_title', 'seo_description']);
        if ($record instanceof Article) {
            $photo = $this->images->image($record->cover, $record->cover_upload, $record->cover_alt ?: $record->title);
            $today = now(config('cms.timezone'))->toDateString();

            return [
                'slug' => $record->slug, 'title' => $record->title, 'category' => $record->category,
                'summary' => $record->summary, 'body' => $record->body,
                'seo_title' => $record->seo_title, 'seo_description' => $record->seo_description,
                'cover' => $photo['src'], 'cover_alt' => $record->cover_alt ?: $record->title,
                'cover_width' => $photo['width'], 'cover_height' => $photo['height'],
                'service' => $record->service, 'featured' => (bool) $record->featured,
                'published_at' => $record->first_published_at?->setTimezone(config('cms.timezone'))->toDateString() ?? $today,
                'updated_at' => $today,
            ];
        }
        if ($record instanceof SitePage) {
            $sections = $record->sections()->get()->map(fn ($section) => [
                'key' => $section->key, 'title' => $section->title, 'body' => $section->body,
                'image' => $section->image || $section->image_upload ? $this->images->image($section->image, $section->image_upload, $section->title)['src'] : '',
            ])->all();

            return [...$common, 'route' => $record->route, 'label' => $record->label, 'intro' => $record->intro,
                'image' => $record->image || $record->image_upload ? $this->images->image($record->image, $record->image_upload, $record->title)['src'] : '',
                'sections' => $sections];
        }
        if ($record instanceof Service) {
            $photo = $this->images->image($record->image, $record->image_upload, $record->title);
            $related = Project::query()->whereNotNull('published_payload')->orderBy('id')->get()
                ->map(fn ($project) => $project->published_payload)
                ->filter(fn ($payload) => ($payload['service'] ?? '') === $record->slug)
                ->pluck('slug')->values()->all();

            return [...$common, 'position' => (int) $record->position, 'slug' => $record->slug, 'summary' => $record->summary,
                'intro' => $record->intro, 'scope' => $this->lines($record->scope), 'prepare' => $record->prepare,
                'image' => $photo['src'], 'width' => $photo['width'], 'height' => $photo['height'], 'alt' => $record->title, 'works' => $related];
        }
        if ($record instanceof Project) {
            $photos = $record->photos()->get()->map(function ($photo) use ($record): array {
                $caption = $photo->caption ?: $record->title;
                if ($photo->image_upload && ! str_starts_with($photo->image_upload, 'legacy/')) {
                    return $this->images->image('', $photo->image_upload, $caption);
                }
                $source = $photo->source ?? [];
                $this->images->image($source['src'] ?? '', null, $caption);

                return [...$source, 'caption' => $caption];
            })->all();
            if (! $photos) {
                throw new PublicationException('Добавьте хотя бы одну фотографию работы перед публикацией.');
            }

            return [...$common, 'position' => (int) $record->position, 'slug' => $record->slug, 'summary' => $record->summary,
                'description' => $record->description, 'details' => $this->lines($record->details), 'location' => $record->location ?: null,
                'category' => $record->category, 'service' => $record->service?->slug ?? '',
                'cover_position' => ($record->published_payload ?? [])['cover_position'] ?? '50% 50%', 'photos' => $photos];
        }
        throw new PublicationException('Раздел не найден.');
    }

    public function publish(Model $record): string
    {
        if ($record instanceof SiteSetting) {
            return $this->publishSettings($record);
        }

        return $this->changeAndBuild(function () use ($record): void {
            $fresh = $record->newQuery()->lockForUpdate()->findOrFail($record->getKey());
            $this->validate($fresh);
            $fresh->published_payload = $this->draftPayload($fresh);
            $fresh->first_published_at ??= now();
            if ($fresh instanceof Article) {
                $fresh->last_published_at = now();
            }
            $fresh->saveQuietly();
        });
    }

    public function unpublish(Model $record): string
    {
        if (! $record instanceof Article && ! $record instanceof Service && ! $record instanceof Project) {
            throw new PublicationException('Основную страницу сайта нельзя скрыть.');
        }

        return $this->changeAndBuild(function () use ($record): void {
            $changes = ['published_payload' => null];
            if ($record instanceof Article) {
                $changes['last_published_at'] = null;
            }
            $record->newQuery()->whereKey($record->getKey())->update($changes);
        });
    }

    public function publishSettings(SiteSetting $record): string
    {
        return $this->changeAndBuild(function () use ($record): void {
            $fresh = SiteSetting::query()->lockForUpdate()->findOrFail($record->getKey());
            $this->validate($fresh);
            $fresh->published_payload = $this->draftPayload($fresh);
            $fresh->saveQuietly();
        });
    }

    public function build(): string
    {
        return $this->changeAndBuild();
    }

    public function preview(Model $record): string
    {
        $payload = $this->draftPayload($record->fresh());
        $kind = $this->kind($record);
        $build = rtrim(config('cms.data_dir'), '/').'/previews/'.Str::uuid();
        try {
            $this->withLock(fn () => $this->prepareBuild($build, [$kind => $payload]));
            $route = $record->publicUrl();
            $path = $build.'/public/'.ltrim($route, '/');
            if ($route === '/') {
                $path .= 'index.html';
            }
            $html = File::get($path);
            $html = preg_replace_callback('~(?:(?:\.\./)*|/)?assets/uploads/([A-Za-z0-9_-]+\.(?:webp|jpg|jpeg|png))~i', function ($match): string {
                $private = $this->images->uploadForPublic($match[0]);
                if (! $private) {
                    throw new PublicationException('Фотография предпросмотра не найдена. Загрузите её снова.');
                }
                $relative = substr($private, strlen(rtrim(realpath(config('cms.media_root')), '/')) + 1);

                return $this->images->privateUrl($relative);
            }, $html);
            $html = str_replace('<head>', '<head><meta name="robots" content="noindex,nofollow" /><base href="'.e($route === '/' ? '/index.html' : $route).'" />', $html);
            $editorSection = match (true) {
                $record instanceof Article => 'articles', $record instanceof Service => 'services',
                $record instanceof Project => 'projects', default => 'site-pages',
            };
            $banner = '<div class="cms-preview-banner"><span>Предпросмотр сохранённой версии · пока не опубликовано</span><a href="/admin/'.$editorSection.'/'.$record->id.'/edit">Вернуться к редактированию</a></div>';

            return str_replace('<main id="main">', '<main id="main">'.$banner, $html);
        } finally {
            File::deleteDirectory($build);
        }
    }

    public function withLock(callable $callback): mixed
    {
        File::ensureDirectoryExists(config('cms.data_dir'), 0755);
        $lock = fopen(config('cms.data_dir').'/publication.lock', 'c');
        if (! $lock) {
            throw new PublicationException('Публикация временно недоступна. Повторите попытку.');
        }
        try {
            if (! flock($lock, LOCK_EX)) {
                throw new PublicationException('Другая публикация ещё не завершена. Повторите попытку.');
            }

            return $callback();
        } finally {
            flock($lock, LOCK_UN);
            fclose($lock);
        }
    }

    protected function validate(Model $record): void
    {
        $rules = $record instanceof SiteSetting ? [
            'company_name' => 'required|string|max:60', 'phone' => ['required', 'string', 'max:30', 'regex:/^\+?[0-9()\s-]{10,30}$/'],
            'hero_description' => 'required|string|max:500', 'region' => 'required|string|max:200',
        ] : ['title' => 'required|string|max:200', 'seo_title' => 'nullable|string|max:100', 'seo_description' => 'nullable|string|max:200'];
        if ($record instanceof Article || $record instanceof Service || $record instanceof Project) {
            $rules['slug'] = ['required', 'max:140', 'regex:/\A[a-z0-9]+(?:-[a-z0-9]+)*\z/'];
            $rules['summary'] = 'required|string|max:'.($record instanceof Project ? 700 : ($record instanceof Service ? 500 : 400));
        }
        if ($record instanceof Article) {
            $rules['body'] = 'required|string|max:100000';
        }
        if ($record instanceof Service) {
            $rules += ['intro' => 'required|string|max:20000', 'scope' => 'required|string|max:4000', 'prepare' => 'required|string|max:6000'];
        }
        if ($record instanceof Project) {
            $rules += ['description' => 'required|string|max:30000', 'details' => 'nullable|string|max:5000', 'location' => 'nullable|string|max:240', 'category' => 'in:outside,inside,insulation'];
        }
        $validator = Validator::make($record->getAttributes(), $rules);
        if ($validator->fails()) {
            throw new PublicationException('Заполните обязательные поля и проверьте длину текста перед публикацией.');
        }
    }

    protected function changeAndBuild(?callable $change = null): string
    {
        return $this->withLock(function () use ($change): string {
            $public = config('cms.public_root');
            $previous = is_link($public) ? readlink($public) : null;
            $build = rtrim(config('cms.data_dir'), '/').'/builds/'.Str::uuid();
            $activated = false;
            try {
                DB::transaction(function () use ($change, $build, &$activated): void {
                    if ($change) {
                        $change();
                    }
                    $this->prepareBuild($build);
                    if (File::put($build.'/.published-at', sprintf('%.6f', microtime(true))) === false) {
                        throw new PublicationException('Не удалось сохранить готовую сборку. Повторите публикацию.');
                    }
                    $this->activate($build.'/public');
                    $activated = true;
                });
            } catch (\Throwable $error) {
                if ($activated) {
                    if ($previous) {
                        $this->activate($previous);
                    } elseif (is_link($public)) {
                        unlink($public);
                    }
                }
                File::deleteDirectory($build);
                if ($error instanceof PublicationException) {
                    throw $error;
                }
                Log::error('CMS publication failed.', ['exception' => $error::class]);
                throw new PublicationException('Не удалось опубликовать изменения. Действующая версия сохранена; черновик доступен в админке.', previous: $error);
            }
            $previousBuilds = collect(File::directories(dirname($build)))
                ->reject(fn ($path) => $path === $build)
                ->sortByDesc(fn ($path) => is_file($path.'/.published-at') ? (float) File::get($path.'/.published-at') : filemtime($path))
                ->values();
            foreach ($previousBuilds->slice(2) as $obsolete) {
                File::deleteDirectory($obsolete);
            }

            return $build;
        });
    }

    protected function activate(string $target): void
    {
        $public = config('cms.public_root');
        File::ensureDirectoryExists(dirname($public), 0700);
        $next = dirname($public).'/.public-next-'.Str::uuid();
        try {
            if (! symlink($target, $next) || ! rename($next, $public)) {
                throw new PublicationException('Не удалось переключить сайт на новую версию.');
            }
        } finally {
            if (is_link($next)) {
                unlink($next);
            }
        }
    }

    protected function prepareBuild(string $build, array $overrides = []): void
    {
        $profile = SiteSetting::query()->first()?->published_payload;
        if (! $profile && ! isset($overrides['settings'])) {
            throw new PublicationException('Сначала опубликуйте контакты компании.');
        }
        $collections = [
            'articles' => $this->published(Article::class), 'pages' => $this->published(SitePage::class),
            'services' => $this->published(Service::class, true), 'projects' => $this->published(Project::class, true),
        ];
        foreach ($overrides as $kind => $payload) {
            if ($kind === 'settings') {
                $profile = $payload;

                continue;
            }
            $name = ['article' => 'articles', 'sitepage' => 'pages', 'service' => 'services', 'project' => 'projects'][$kind];
            $identity = $kind === 'sitepage' ? 'route' : 'slug';
            $collections[$name] = array_values(array_filter($collections[$name], fn ($row) => $row[$identity] !== $payload[$identity]));
            $collections[$name][] = $payload;
            if (in_array($name, ['services', 'projects'], true)) {
                usort($collections[$name], fn ($a, $b) => ($a['position'] ?? 0) <=> ($b['position'] ?? 0));
            }
        }
        $public = $build.'/public';
        File::ensureDirectoryExists($public, 0755);
        $oldUploads = config('cms.public_root').'/assets/uploads';
        if (is_dir($oldUploads)) {
            File::copyDirectory($oldUploads, $public.'/assets/uploads');
        }
        foreach (array_unique($this->uploads($collections)) as $upload) {
            $original = $this->images->uploadForPublic($upload);
            if (! $original) {
                throw new PublicationException('Не найдена опубликованная фотография. Восстановите её из резервной копии.');
            }
            File::ensureDirectoryExists($public.'/assets/uploads', 0755);
            File::copy($original, $public.'/'.$upload);
        }
        $command = [config('cms.python_binary'), config('cms.site_root').'/scripts/build_site.py', '--output-dir', $public];
        foreach ([...$collections, 'site' => $profile] as $name => $payload) {
            $path = $build.'/'.$name.'.json';
            File::put($path, json_encode($payload, JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT | JSON_THROW_ON_ERROR));
            $command[] = '--'.$name.'-file';
            $command[] = $path;
        }
        $this->runGenerator($command);
        if (! is_file($public.'/index.html') || ! is_file($public.'/sitemap.xml')) {
            throw new PublicationException('Сборка не создала обязательные страницы. Действующая версия сохранена.');
        }
    }

    protected function runGenerator(array $command): void
    {
        $process = new Process($command, config('cms.site_root'), ['PUBLIC_SITE_URL' => config('cms.site_url')]);
        $process->setTimeout(90);
        try {
            $process->run();
        } catch (\Throwable $error) {
            throw new PublicationException('Сборка сайта не завершилась. Повторите публикацию.', previous: $error);
        }
        if (! $process->isSuccessful()) {
            Log::error('CMS static generator failed.', ['exit_code' => $process->getExitCode()]);
            throw new PublicationException('Не удалось собрать страницы. Действующая версия сохранена; повторите публикацию.');
        }
    }

    protected function published(string $model, bool $ordered = false): array
    {
        $snapshots = $model::query()->whereNotNull('published_payload')->orderBy('id')->get()->pluck('published_payload')->all();
        if ($ordered) {
            usort($snapshots, fn ($a, $b) => ($a['position'] ?? 0) <=> ($b['position'] ?? 0));
        }

        return $snapshots;
    }

    protected function uploads(array $values): array
    {
        $uploads = [];
        array_walk_recursive($values, function ($value) use (&$uploads): void {
            if (is_string($value) && str_starts_with($value, 'assets/uploads/')) {
                $uploads[] = $value;
            }
        });

        return $uploads;
    }

    protected function lines(?string $text): array
    {
        return array_values(array_filter(array_map('trim', preg_split('/\R/u', $text ?? '')), fn ($line) => $line !== ''));
    }

    protected function kind(Model $record): string
    {
        return match ($record::class) {
            Article::class => 'article', SitePage::class => 'sitepage', Service::class => 'service', Project::class => 'project', SiteSetting::class => 'settings',
            default => throw new PublicationException('Раздел не найден.'),
        };
    }
}
