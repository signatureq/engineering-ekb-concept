<?php

namespace App\Models;

use App\Services\ContentFields;
use App\Services\Publisher;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Validation\ValidationException;

abstract class Publishable extends Model
{
    public const CREATED_AT = null;

    protected $guarded = [];

    protected function casts(): array
    {
        return ['published_payload' => 'array', 'first_published_at' => 'datetime'];
    }

    protected static function booted(): void
    {
        static::saving(function (self $record): void {
            $fields = match (true) {
                $record instanceof Article => ['title', 'slug', 'category', 'summary', 'body', 'cover', 'cover_upload', 'cover_alt', 'service', 'seo_title', 'seo_description'],
                $record instanceof SitePage => ['title', 'route', 'label', 'intro', 'image', 'image_upload', 'seo_title', 'seo_description'],
                $record instanceof Service => ['title', 'slug', 'summary', 'intro', 'scope', 'prepare', 'image', 'image_upload', 'seo_title', 'seo_description'],
                $record instanceof Project => ['title', 'slug', 'summary', 'description', 'details', 'location', 'category', 'seo_title', 'seo_description'],
                default => [],
            };
            ContentFields::normalizeStrings($record, $fields);
            if ($record instanceof Article || $record instanceof Service || $record instanceof Project) {
                if ($record->exists && $record->getRawOriginal('first_published_at') && $record->isDirty('slug')) {
                    throw ValidationException::withMessages(['title' => 'Адрес опубликованной страницы закреплён. Можно изменить название и текст.']);
                }
                if (! $record->slug) {
                    $record->slug = ContentFields::slug($record, $record->title ?? '');
                }
            }
            if ($record instanceof SitePage && $record->exists && $record->isDirty('route')) {
                throw ValidationException::withMessages(['title' => 'Адрес основной страницы закреплён. Можно изменить её содержимое.']);
            }
            if ($record instanceof Article) {
                ContentFields::article($record);
            }
        });
    }

    public function publicUrl(): string
    {
        return match (true) {
            $this instanceof SitePage => '/'.$this->route,
            $this instanceof Article => '/articles/'.$this->slug.'.html',
            $this instanceof Service => '/services/'.$this->slug.'.html',
            $this instanceof Project => '/works/'.$this->slug.'.html',
            default => '/',
        };
    }

    public function publicationStatus(): string
    {
        if ($this->published_payload === null) {
            return 'Черновик';
        }
        try {
            $draft = app(Publisher::class)->draftPayload($this);
            $published = $this->published_payload;
            if ($this instanceof Article) {
                unset($draft['published_at'], $draft['updated_at'], $published['published_at'], $published['updated_at'], $published['body_path']);
            }
            if ($this instanceof Service) {
                unset($draft['alt'], $draft['works'], $published['alt'], $published['works']);
            }

            return $draft == $published ? 'Опубликовано' : 'Есть изменения';
        } catch (\Throwable) {
            return 'Есть изменения';
        }
    }
}
