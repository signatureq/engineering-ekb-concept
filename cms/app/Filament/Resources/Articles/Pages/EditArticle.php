<?php

namespace App\Filament\Resources\Articles\Pages;

use App\Filament\Resources\Articles\ArticleResource;
use App\Filament\Resources\Pages\EditContent;

class EditArticle extends EditContent
{
    protected static string $resource = ArticleResource::class;
}
