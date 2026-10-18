<?php

namespace App\Services;

use App\Exceptions\PublicationException;
use Illuminate\Http\UploadedFile;
use Illuminate\Support\Facades\URL;
use Illuminate\Support\Str;
use Illuminate\Validation\ValidationException;
use Symfony\Component\Process\Process;

class ImageStore
{
    public function store(UploadedFile $file): string
    {
        if (! $file->isValid() || $file->getSize() > 5 * 1024 * 1024) {
            throw ValidationException::withMessages(['image_upload' => 'Фотография больше 5 МБ или загружена не полностью.']);
        }
        $relative = 'content/'.Str::uuid()->getHex().'.webp';
        $target = rtrim(config('cms.media_root'), '/').'/'.$relative;
        if (! is_dir(dirname($target)) && ! mkdir(dirname($target), 0700, true) && ! is_dir(dirname($target))) {
            throw new PublicationException('Не удалось сохранить фотографию. Повторите загрузку.');
        }
        $process = new Process([config('cms.python_binary'), config('cms.site_root').'/scripts/filament_image.py', $file->getPathname(), $target]);
        $process->setTimeout(30);
        try {
            $process->run();
        } catch (\Throwable $error) {
            @unlink($target);
            throw new PublicationException('Не удалось обработать фотографию. Повторите загрузку.', previous: $error);
        }
        if (! $process->isSuccessful() || ! is_file($target)) {
            @unlink($target);
            $message = trim($process->getErrorOutput());
            $safe = str_starts_with($message, 'Нужен ') || str_starts_with($message, 'Фотография ') || str_starts_with($message, 'Не удалось прочитать ');
            throw ValidationException::withMessages(['image_upload' => $safe ? $message : 'Не удалось прочитать фотографию. Загрузите JPG, PNG или WebP до 5 МБ.']);
        }
        chmod($target, 0600);

        return $relative;
    }

    public function privatePath(string $relative): string
    {
        return $this->safePath(config('cms.media_root'), $relative);
    }

    public function sourcePath(string $relative): string
    {
        if (! str_starts_with($relative, 'assets/')) {
            throw new PublicationException('Выберите фотографию сайта или загрузите новый файл.');
        }

        return $this->safePath(config('cms.site_root'), $relative);
    }

    private function safePath(string $root, string $relative): string
    {
        $parts = explode('/', str_replace('\\', '/', $relative));
        if (! $relative || str_starts_with($relative, '/') || preg_match('/[\x00-\x1f]/', $relative) || in_array('..', $parts, true) || in_array('.', $parts, true) || collect($parts)->contains(fn ($part) => str_starts_with($part, '.'))) {
            throw new PublicationException('Недопустимый путь фотографии.');
        }
        $root = realpath($root);
        $path = $root ? realpath($root.'/'.$relative) : false;
        if (! $path || ! is_file($path) || ! str_starts_with($path, $root.DIRECTORY_SEPARATOR)) {
            throw new PublicationException('Фотография не найдена. Загрузите её снова.');
        }

        return $path;
    }

    public function image(string $source, ?string $uploaded = null, string $caption = 'Фотография'): array
    {
        // Legacy copies exist only so the form can display the current source
        // photograph. Merely opening or saving a record must not change its URL.
        $usesUpload = $uploaded && ! str_starts_with($uploaded, 'legacy/');
        $path = $usesUpload ? $this->privatePath($uploaded) : $this->sourcePath($source);
        $dimensions = @getimagesize($path);
        if (! $dimensions || ! in_array($dimensions[2], [IMAGETYPE_JPEG, IMAGETYPE_PNG, IMAGETYPE_WEBP], true)) {
            throw new PublicationException('Не удалось прочитать фотографию. Загрузите её снова.');
        }
        $src = $usesUpload ? 'assets/uploads/'.basename($path) : $source;

        return ['src' => $src, 'small' => $src, 'width' => $dimensions[0], 'height' => $dimensions[1], 'small_width' => $dimensions[0], 'caption' => $caption];
    }

    public function uploadForPublic(string $publicPath): ?string
    {
        $name = basename($publicPath);
        if (! preg_match('/\A[a-zA-Z0-9_-]+\.(?:webp|jpg|jpeg|png)\z/i', $name)) {
            return null;
        }
        foreach (['articles', 'content'] as $folder) {
            try {
                return $this->privatePath($folder.'/'.$name);
            } catch (PublicationException) {
                // Try the other private upload collection.
            }
        }

        return null;
    }

    public function privateUrl(string $relative): string
    {
        return URL::temporarySignedRoute('cms.media', now()->addHour(), ['path' => $relative]);
    }
}
