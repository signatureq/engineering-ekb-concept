<?php

namespace App\Models;

use App\Services\ContentFields;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class PageSection extends Model
{
    public $timestamps = false;

    protected $guarded = [];

    protected $attributes = ['title' => '', 'body' => '', 'image' => '', 'image_upload' => '', 'position' => 0];

    protected static function booted(): void
    {
        static::saving(fn (self $record) => ContentFields::normalizeStrings($record, ['key', 'title', 'body', 'image', 'image_upload']));
    }

    public function page(): BelongsTo
    {
        return $this->belongsTo(SitePage::class, 'page_id');
    }
}
