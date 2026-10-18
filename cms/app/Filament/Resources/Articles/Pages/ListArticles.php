<?php

namespace App\Filament\Resources\Articles\Pages;

use App\Filament\Resources\Articles\ArticleResource;
use Filament\Actions\CreateAction;
use Filament\Resources\Pages\ListRecords;
use Illuminate\Contracts\Support\Htmlable;

class ListArticles extends ListRecords
{
    protected static string $resource = ArticleResource::class;

    public function getSubheading(): string|Htmlable|null
    {
        return 'Публикуйте полезные статьи. Достаточно названия и текста — адрес и краткое описание заполнятся автоматически.';
    }

    protected function getHeaderActions(): array
    {
        return [CreateAction::make()->label('Добавить статью')];
    }
}
