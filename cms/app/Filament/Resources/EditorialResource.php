<?php

namespace App\Filament\Resources;

use App\Models\SitePage;
use Filament\Actions\EditAction;
use Filament\Resources\Resource;
use Filament\Tables\Columns\TextColumn;
use Filament\Tables\Table;
use Illuminate\Database\Eloquent\Model;

abstract class EditorialResource extends Resource
{
    protected static ?string $recordTitleAttribute = 'title';

    protected static bool $isGloballySearchable = false;

    protected static bool $hasTitleCaseModelLabel = false;

    public static function table(Table $table): Table
    {
        return $table->columns([
            TextColumn::make('title')->label('Название')->searchable()->wrap()->weight('medium'),
            TextColumn::make('publication')->label('На сайте')->state(fn (Model $record): string => $record->publicationStatus())
                ->badge()->visibleFrom('sm')->color(fn (string $state): string => match ($state) {
                    'Опубликовано' => 'success', 'Есть изменения' => 'warning', default => 'gray'
                }),
            TextColumn::make('updated_at')->label('Изменено')->dateTime('d.m.Y, H:i')->timezone('Asia/Yekaterinburg')->sortable()->visibleFrom('md'),
        ])->recordActions([EditAction::make()->label('Изменить')])->defaultSort('id')
            ->emptyStateHeading('Здесь пока ничего нет')->emptyStateDescription('Добавьте первый материал. Он появится на сайте после публикации.')
            ->searchPlaceholder('Поиск по названию')->paginated([10, 25])->defaultPaginationPageOption(10);
    }

    public static function canDelete(Model $record): bool
    {
        return $record->published_payload === null && ! ($record instanceof SitePage);
    }

    public static function canDeleteAny(): bool
    {
        return false;
    }
}
