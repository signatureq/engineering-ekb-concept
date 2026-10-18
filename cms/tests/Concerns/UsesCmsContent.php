<?php

namespace Tests\Concerns;

use App\Models\SiteSetting;
use App\Services\ContentImporter;
use Illuminate\Support\Facades\File;
use Illuminate\Support\Str;

trait UsesCmsContent
{
    protected string $cmsTemporary;

    protected function configureCmsTest(): void
    {
        $this->cmsTemporary = sys_get_temp_dir().'/orion-cms-test-'.Str::uuid();
        File::ensureDirectoryExists($this->cmsTemporary.'/media', 0700);
        config([
            'cms.data_dir' => $this->cmsTemporary,
            'cms.media_root' => $this->cmsTemporary.'/media',
            'cms.public_root' => $this->cmsTemporary.'/public',
            'cms.site_root' => dirname(base_path()),
            'cms.site_url' => 'https://site.example',
        ]);
        $this->beforeApplicationDestroyed(fn () => File::deleteDirectory($this->cmsTemporary));
    }

    protected function publicContentExport(): array
    {
        $root = config('cms.site_root');
        $load = fn ($name) => json_decode(File::get($root.'/content/'.$name.'.json'), true, 512, JSON_THROW_ON_ERROR);
        $timestamp = '2026-10-19 00:00:00';
        $common = ['seo_title' => '', 'seo_description' => '', 'first_published_at' => $timestamp, 'updated_at' => $timestamp];
        $tables = array_fill_keys(ContentImporter::TABLES, []);
        $tables['users'][] = ['id' => 7, 'username' => 'client', 'name' => 'Редактор', 'email' => null,
            'password' => 'pbkdf2_sha256$1000$fixture-salt$'.base64_encode(hash_pbkdf2('sha256', 'test-password-not-secret', 'fixture-salt', 1000, 32, true)),
            'is_staff' => true, 'is_active' => true, 'created_at' => $timestamp, 'updated_at' => $timestamp];
        $profile = [...(new SiteSetting)->only(SiteSetting::CONTENT_FIELDS), ...array_intersect_key($load('site'), array_flip(SiteSetting::CONTENT_FIELDS))];
        $tables['site_settings'][] = ['id' => 1, ...$profile, 'published_payload' => $profile, 'updated_at' => $timestamp];
        foreach ($load('pages') as $index => $page) {
            $tables['site_pages'][] = ['id' => $index + 1, ...$common, ...array_intersect_key($page, array_flip(['title', 'route', 'label', 'intro', 'image'])),
                'image_upload' => '', 'published_payload' => [...$page, 'seo_title' => '', 'seo_description' => '']];
            foreach ($page['sections'] as $position => $section) {
                $tables['page_sections'][] = ['id' => count($tables['page_sections']) + 1, 'page_id' => $index + 1, ...$section, 'image_upload' => '', 'position' => $position];
            }
        }
        $serviceIds = [];
        foreach ($load('services') as $index => $service) {
            $serviceIds[$service['slug']] = $index + 1;
            $tables['services'][] = ['id' => $index + 1, ...$common, ...array_intersect_key($service, array_flip(['slug', 'title', 'summary', 'intro', 'prepare', 'image'])),
                'scope' => implode("\n", $service['scope']), 'position' => $index, 'image_upload' => '',
                'published_payload' => [...$service, 'position' => $index, 'seo_title' => '', 'seo_description' => '']];
        }
        foreach ($load('projects') as $index => $project) {
            $description = is_array($project['description']) ? implode("\n\n", $project['description']) : $project['description'];
            $tables['projects'][] = ['id' => $index + 1, ...$common, ...array_intersect_key($project, array_flip(['slug', 'title', 'summary', 'category'])),
                'description' => $description, 'details' => implode("\n", $project['details']), 'location' => $project['location'] ?? '',
                'service_id' => $serviceIds[$project['service']] ?? null, 'position' => $index,
                'published_payload' => [...$project, 'description' => $description, 'position' => $index, 'seo_title' => '', 'seo_description' => '']];
            foreach ($project['photos'] as $position => $photo) {
                $tables['project_photos'][] = ['id' => count($tables['project_photos']) + 1, 'project_id' => $index + 1, 'source' => $photo,
                    'caption' => $photo['caption'], 'position' => $position, 'image_upload' => ''];
            }
        }
        foreach ($load('articles') as $index => $article) {
            $body = isset($article['body_path']) ? File::get($root.'/'.$article['body_path']) : $article['body'];
            $tables['articles'][] = ['id' => $index + 1, ...$common, ...array_intersect_key($article, array_flip(['slug', 'title', 'category', 'summary', 'cover', 'cover_alt', 'cover_width', 'cover_height', 'service', 'featured', 'seo_title', 'seo_description'])),
                'body' => $body, 'cover_upload' => '', 'created_at' => $timestamp, 'last_published_at' => $timestamp,
                'published_payload' => [...$article, 'body' => $body]];
        }
        $tables['content_imports'] = [['id' => 1, 'key' => 'articles'], ['id' => 2, 'key' => 'site-sections']];

        return ['format' => 'orion-django-export', 'version' => 1, 'tables' => $tables];
    }

    protected function importContent(?array $export = null): array
    {
        $export ??= $this->publicContentExport();
        $path = $this->cmsTemporary.'/import.json';
        File::put($path, json_encode($export, JSON_UNESCAPED_UNICODE | JSON_THROW_ON_ERROR));
        app(ContentImporter::class)->import($path);

        return $export;
    }
}
