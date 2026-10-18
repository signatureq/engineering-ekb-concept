<?php

namespace App\Models;

use App\Services\ContentFields;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class ProjectPhoto extends Model
{
    public $timestamps = false;

    protected $guarded = [];

    protected $attributes = ['caption' => '', 'image_upload' => '', 'source' => '{}', 'position' => 10];

    protected function casts(): array
    {
        return ['source' => 'array'];
    }

    protected static function booted(): void
    {
        static::saving(fn (self $record) => ContentFields::normalizeStrings($record, ['caption', 'image_upload']));
    }

    public function project(): BelongsTo
    {
        return $this->belongsTo(Project::class);
    }
}
