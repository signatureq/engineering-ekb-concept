<?php

namespace App\Filament\Resources\Services\Pages;

use App\Filament\Resources\Services\ServiceResource;
use Filament\Actions\CreateAction;
use Filament\Resources\Pages\ListRecords;
use Illuminate\Contracts\Support\Htmlable;

class ListServices extends ListRecords
{
    protected static string $resource = ServiceResource::class;

    public function getSubheading(): string|Htmlable|null
    {
        return 'Добавляйте услуги, меняйте описания и фотографии. Сохранённый черновик появится на сайте только после публикации.';
    }

    protected function getHeaderActions(): array
    {
        return [CreateAction::make()->label('Добавить услугу')];
    }
}
