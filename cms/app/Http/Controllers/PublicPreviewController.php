<?php

namespace App\Http\Controllers;

use App\Exceptions\PublicationException;
use App\Models\Article;
use App\Models\Project;
use App\Models\Service;
use App\Models\SitePage;
use App\Models\SiteSetting;
use App\Services\Publisher;
use Illuminate\Http\Request;
use Illuminate\Http\Response;

class PublicPreviewController extends Controller
{
    public function __invoke(Request $request, string $kind, int $id, Publisher $publisher): Response
    {
        abort_unless($request->user()?->is_staff && $request->user()?->is_active, 404);
        $model = match ($kind) {
            'article' => Article::class, 'service' => Service::class, 'project' => Project::class,
            'page', 'sitepage' => SitePage::class, 'settings' => SiteSetting::class,
            default => abort(404),
        };
        $record = $model::query()->findOrFail($id);
        try {
            $html = $publisher->preview($record);
            $status = 200;
        } catch (PublicationException $error) {
            $html = '<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Дополните материал</title><main style="max-width:640px;margin:10vh auto;padding:24px;font:18px/1.6 sans-serif"><h1>Дополните материал</h1><p>'.e($error->getMessage()).'</p><a href="/admin">Вернуться в админку</a></main></html>';
            $status = 400;
        }

        return response($html, $status)->header('Cache-Control', 'private,no-store')->header('X-Robots-Tag', 'noindex,nofollow');
    }
}
