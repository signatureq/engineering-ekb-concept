<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Relations\HasMany;

class Service extends Publishable
{
    protected $attributes = ['slug' => '', 'image' => 'assets/client/pipeline-installation.jpg', 'image_upload' => '', 'position' => 10, 'seo_title' => '', 'seo_description' => ''];

    public function projects(): HasMany
    {
        return $this->hasMany(Project::class, 'service_id')->orderBy('position')->orderBy('id');
    }
}
