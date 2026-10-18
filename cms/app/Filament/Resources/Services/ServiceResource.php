<?php

namespace App\Filament\Resources\Services;

use App\Filament\Resources\EditorialResource;
use App\Filament\Support\ContentFields as F;
use App\Models\Service;
use BackedEnum;
use Filament\Forms\Components\Textarea;
use Filament\Schemas\Components\Section;
use Filament\Schemas\Schema;

class ServiceResource extends EditorialResource
{
    protected static ?string $model = Service::class;

    protected static ?string $modelLabel = 'услуга';

    protected static ?string $pluralModelLabel = 'Услуги';

    protected static ?string $navigationLabel = 'Услуги';

    protected static string|BackedEnum|null $navigationIcon = 'heroicon-o-wrench-screwdriver';

    protected static ?int $navigationSort = 2;

    public static function form(Schema $schema): Schema
    {
        return $schema->columns(1)->components([
            Section::make('Об услуге')->schema([
                F::text('title', 'Название услуги'),
                Textarea::make('summary')->label('Короткое описание')->rows(3)->required()->maxLength(500)->helperText('Показывается на карточке услуги.'),
                F::rich('intro', 'Описание услуги', 20000)->required(),
                Textarea::make('scope')->label('Какие задачи решаем')->rows(4)->required()->maxLength(4000)->helperText('Каждый пункт — с новой строки.'),
                F::rich('prepare', 'Что подготовить для обсуждения', 6000)->required(),
            ]),
            Section::make('Фотография и порядок')->schema([F::image(), F::order()]),
            F::seo(),
        ]);
    }

    public static function getPages(): array
    {
        return [
            'index' => Pages\ListServices::route('/'),
            'create' => Pages\CreateService::route('/create'),
            'edit' => Pages\EditService::route('/{record}/edit'),
        ];
    }
}
