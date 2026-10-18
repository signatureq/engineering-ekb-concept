<?php

use App\Http\Controllers\InquiryController;
use App\Http\Controllers\MediaController;
use App\Http\Controllers\PublicPreviewController;
use App\Http\Middleware\PrivateResponse;
use Illuminate\Support\Facades\Route;

Route::match(['get', 'post'], '/api/inquiry/', InquiryController::class)->name('inquiry');
Route::middleware(['auth', PrivateResponse::class])->group(function (): void {
    Route::get('/admin/photo/{path}', MediaController::class)->middleware('signed')->name('cms.photo');
    Route::get('/admin/media/{path}', MediaController::class)->where('path', '.*')->middleware('signed')->name('cms.media');
    Route::get('/cms-preview/{kind}/{id}', PublicPreviewController::class)->whereNumber('id')->name('cms.preview');
});
Route::fallback(function () {
    $path = request()->path() === '/' ? 'index.html' : request()->path();
    abort_if(str_contains($path, '..') || str_starts_with($path, '.') || preg_match('/\\.(php|py|env|sqlite3?|md|ya?ml)$/i', $path), 404);
    $root = realpath(config('cms.data_dir').'/public');
    $file = $root ? realpath($root.'/'.$path) : false;
    abort_unless($file && str_starts_with($file, $root.'/') && is_file($file), 404);
    $type = match (strtolower(pathinfo($file, PATHINFO_EXTENSION))) {
        'css' => 'text/css', 'js' => 'application/javascript', 'svg' => 'image/svg+xml', 'html' => 'text/html', 'txt' => 'text/plain', 'xml' => 'application/xml', default => mime_content_type($file),
    };

    return response()->file($file, ['Content-Type' => $type, 'X-Content-Type-Options' => 'nosniff']);
});
