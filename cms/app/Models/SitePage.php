<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Relations\HasMany;

class SitePage extends Publishable
{
    protected $attributes = ['intro' => '', 'image' => '', 'image_upload' => '', 'seo_title' => '', 'seo_description' => ''];

    public function sections(): HasMany
    {
        return $this->hasMany(PageSection::class, 'page_id')->orderBy('position')->orderBy('id');
    }
}
