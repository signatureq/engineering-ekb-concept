<?php

namespace App\Services;

use App\Exceptions\PublicationException;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\File;
use Illuminate\Support\Facades\Schema;

class ContentImporter
{
    public const TABLES = ['users', 'articles', 'site_settings', 'site_pages', 'page_sections', 'services', 'projects', 'project_photos', 'content_imports'];

    public function __construct(protected ImageStore $images, protected Publisher $publisher) {}

    public function import(string $path, ?string $mediaSource = null): array
    {
        $payload = json_decode(File::get($path), true, 512, JSON_THROW_ON_ERROR);
        if (($payload['format'] ?? '') !== 'orion-django-export' || ($payload['version'] ?? 0) !== 1 || array_diff(self::TABLES, array_keys($payload['tables'] ?? []))) {
            throw new PublicationException('Файл переноса имеет неподдерживаемый формат.');
        }

        return $this->publisher->withLock(function () use ($payload, $mediaSource): array {
            foreach (self::TABLES as $table) {
                if (DB::table($table)->exists()) {
                    throw new PublicationException('База уже содержит данные. Повторный импорт запрещён, чтобы сохранить изменения редактора.');
                }
            }
            if ($mediaSource !== null) {
                $this->copyPrivateMedia($mediaSource);
            }

            return DB::transaction(function () use ($payload): array {
                $counts = [];
                foreach (self::TABLES as $table) {
                    $columns = Schema::getColumnListing($table);
                    $rows = $payload['tables'][$table];
                    if (! is_array($rows)) {
                        throw new PublicationException('Файл переноса повреждён.');
                    }
                    foreach ($rows as $row) {
                        if (! is_array($row) || array_diff(array_keys($row), $columns)) {
                            throw new PublicationException('Поля базы не совпали с файлом переноса. Данные не изменены.');
                        }
                        $row = $this->addLegacyImage($table, $row);
                        foreach (['published_payload', 'source'] as $field) {
                            if (array_key_exists($field, $row) && $row[$field] !== null) {
                                $row[$field] = json_encode($row[$field], JSON_UNESCAPED_UNICODE | JSON_THROW_ON_ERROR);
                            }
                        }
                        DB::table($table)->insert($row);
                    }
                    $counts[$table] = count($rows);
                }
                DB::table('content_imports')->insert(['key' => 'laravel-import-v1']);

                return $counts;
            });
        });
    }

    private function addLegacyImage(string $table, array $row): array
    {
        $mapping = match ($table) {
            'articles' => ['cover', 'cover_upload'],
            'site_pages', 'page_sections', 'services' => ['image', 'image_upload'],
            'project_photos' => ['source', 'image_upload'],
            default => null,
        };
        if (! $mapping) {
            return $row;
        }
        [$sourceField, $uploadField] = $mapping;
        if (! empty($row[$uploadField])) {
            $this->images->privatePath($row[$uploadField]);

            return $row;
        }
        $source = $sourceField === 'source' ? ($row['source']['src'] ?? '') : ($row[$sourceField] ?? '');
        if (! $source) {
            return $row;
        }
        $original = $this->images->sourcePath($source);
        $relative = 'legacy/'.$source;
        $target = rtrim(config('cms.media_root'), '/').'/'.$relative;
        $this->copyFile($original, $target);
        $row[$uploadField] = $relative;

        return $row;
    }

    private function copyPrivateMedia(string $source): void
    {
        $source = realpath($source);
        if (! $source || ! is_dir($source)) {
            throw new PublicationException('Приватная папка фотографий для переноса не найдена.');
        }
        $iterator = new \RecursiveIteratorIterator(new \RecursiveDirectoryIterator($source, \FilesystemIterator::SKIP_DOTS));
        foreach ($iterator as $item) {
            if ($item->isLink()) {
                throw new PublicationException('В папке переноса обнаружена недопустимая ссылка.');
            }
            if (! $item->isFile()) {
                continue;
            }
            $relative = substr($item->getPathname(), strlen($source) + 1);
            if (! preg_match('~\A(?:articles|content)/[A-Za-z0-9_-]+\.(?:webp|jpg|jpeg|png)\z~i', $relative)) {
                throw new PublicationException('В папке переноса обнаружен неподдерживаемый файл.');
            }
            $this->copyFile($item->getPathname(), rtrim(config('cms.media_root'), '/').'/'.$relative);
        }
    }

    private function copyFile(string $source, string $target): void
    {
        File::ensureDirectoryExists(dirname($target), 0700);
        if (is_file($target)) {
            if (hash_file('sha256', $target) !== hash_file('sha256', $source)) {
                throw new PublicationException('Фотография с таким именем уже существует. Перенос остановлен без замены файла.');
            }

            return;
        }
        if (! File::copy($source, $target)) {
            throw new PublicationException('Не удалось перенести приватную фотографию.');
        }
        chmod($target, 0600);
    }
}
