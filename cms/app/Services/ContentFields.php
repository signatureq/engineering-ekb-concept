<?php

namespace App\Services;

use App\Models\Article;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Support\Str;

class ContentFields
{
    public static function normalizeStrings(Model $record, array $fields): void
    {
        foreach ($fields as $field) {
            $value = $record->getAttribute($field);
            if ($value === null || is_string($value)) {
                $record->setAttribute($field, str_replace("\u{00a0}", ' ', $value ?? ''));
            }
        }
    }

    public static function slug(Model $record, string $title): string
    {
        $source = preg_split('//u', 'абвгдеёжзийклмнопрстуфхцчшщъыьэюя', -1, PREG_SPLIT_NO_EMPTY);
        $latin = ['a', 'b', 'v', 'g', 'd', 'e', 'e', 'zh', 'z', 'i', 'y', 'k', 'l', 'm', 'n', 'o', 'p', 'r', 's', 't', 'u', 'f', 'h', 'ts', 'ch', 'sh', 'sch', '', 'y', '', 'e', 'yu', 'ya'];
        $base = substr(Str::slug(strtr(mb_strtolower($title), array_combine($source, $latin))), 0, 110);
        $base = trim($base, '-') ?: 'stranitsa-'.Str::lower(Str::random(8));
        $candidate = $base;
        $suffix = 2;
        while ($record->newQuery()->where('slug', $candidate)->when($record->exists, fn ($query) => $query->whereKeyNot($record->getKey()))->exists()) {
            $candidate = $base.'-'.$suffix++;
        }

        return $candidate;
    }

    public static function article(Article $article): void
    {
        $article->cover_alt = mb_substr($article->title ?? '', 0, 240);
        if ($article->isDirty('body') || ! $article->summary) {
            $plain = html_entity_decode(strip_tags(Str::markdown($article->body ?? '', ['html_input' => 'strip', 'allow_unsafe_links' => false])), ENT_QUOTES | ENT_HTML5, 'UTF-8');
            $plain = trim(preg_replace('/\s+/u', ' ', $plain));
            $article->summary = mb_strlen($plain) <= 260 ? $plain : preg_replace('/\s+\S*$/u', '', mb_substr($plain, 0, 260)).'…';
        }
        if (! $article->category) {
            $title = mb_strtolower($article->title ?? '');
            [$article->category, $article->service] = match (true) {
                str_contains($title, 'изол') => ['Теплоизоляция', 'insulation'],
                str_contains($title, 'учёт'), str_contains($title, 'учет') => ['Узлы учёта', 'metering'],
                str_contains($title, 'авар') => ['Аварийные работы', 'emergency'],
                str_contains($title, 'монтаж'), str_contains($title, 'труб'), str_contains($title, 'свар') => ['Монтаж трубопроводов', 'pipeline-installation'],
                default => ['Инженерные сети', ''],
            };
        }
    }
}
