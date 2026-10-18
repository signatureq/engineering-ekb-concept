<?php

namespace App\Filament\Resources\SitePages\Pages;

use App\Filament\Resources\SitePages\SitePageResource;
use Filament\Resources\Pages\ListRecords;
use Illuminate\Contracts\Support\Htmlable;

class ListSitePages extends ListRecords
{
    protected static string $resource = SitePageResource::class;

    public function getSubheading(): string|Htmlable|null
    {
        return 'Выберите страницу и измените её текст или фотографии. Существующие адреса и расположение блоков сохраняются.';
    }

    protected function getHeaderActions(): array
    {
        return [];
    }
}
