<?php

namespace App\Providers;

use App\Support\DjangoCompatibleHasher;
use Illuminate\Support\Facades\Hash;
use Illuminate\Support\Facades\Storage;
use Illuminate\Support\Facades\URL;
use Illuminate\Support\ServiceProvider;

class AppServiceProvider extends ServiceProvider
{
    public function register(): void
    {
        if ($path = env('LARAVEL_STORAGE_PATH')) {
            $this->app->useStoragePath($path);
        }
    }

    public function boot(): void
    {
        Hash::extend('django-compatible', fn () => new DjangoCompatibleHasher(config('hashing.bcrypt')));
        Storage::disk('cms-private')->buildTemporaryUrlsUsing(fn (string $path, $expiration) => URL::temporarySignedRoute('cms.photo', $expiration, ['path' => 'Фотография.'.pathinfo($path, PATHINFO_EXTENSION), 'photo' => $path]));
    }
}
