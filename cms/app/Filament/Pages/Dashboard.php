<?php

namespace App\Filament\Pages;

use Filament\Actions\Action;
use Illuminate\Contracts\Support\Htmlable;

class Dashboard extends \Filament\Pages\Dashboard
{
    protected static ?string $title = 'Управление сайтом';

    protected static ?string $navigationLabel = 'Начало';

    protected string $view = 'filament.pages.dashboard';

    public function getSubheading(): string|Htmlable|null
    {
        return 'Выберите, что хотите изменить. Служебные настройки сайт заполнит сам.';
    }

    protected function getHeaderActions(): array
    {
        return [Action::make('site')->label('Открыть сайт')->icon('heroicon-o-arrow-top-right-on-square')->url('/')->openUrlInNewTab()->color('gray')];
    }
}
