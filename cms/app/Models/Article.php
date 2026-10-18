<?php

namespace App\Models;

class Article extends Publishable
{
    public const CREATED_AT = 'created_at';

    protected $attributes = [
        'slug' => '', 'category' => '', 'summary' => '', 'seo_title' => '', 'seo_description' => '',
        'cover' => 'assets/client/pipeline-installation.jpg', 'cover_upload' => '', 'cover_alt' => '',
        'cover_width' => 1200, 'cover_height' => 1600, 'service' => '', 'featured' => false,
    ];

    protected function casts(): array
    {
        return [...parent::casts(), 'featured' => 'boolean', 'last_published_at' => 'datetime'];
    }
}
