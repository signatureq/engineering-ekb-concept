<?php

namespace App\Filament\Resources\Articles\Pages;

use App\Filament\Resources\Articles\ArticleResource;
use App\Filament\Resources\Pages\CreateContent;

class CreateArticle extends CreateContent
{
    protected static string $resource = ArticleResource::class;
}
