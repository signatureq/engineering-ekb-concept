<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Database\Eloquent\Relations\HasMany;

class Project extends Publishable
{
    protected $attributes = ['slug' => '', 'details' => '', 'location' => '', 'category' => 'inside', 'position' => 10, 'seo_title' => '', 'seo_description' => ''];

    public function service(): BelongsTo
    {
        return $this->belongsTo(Service::class);
    }

    public function photos(): HasMany
    {
        return $this->hasMany(ProjectPhoto::class)->orderBy('position')->orderBy('id');
    }
}
