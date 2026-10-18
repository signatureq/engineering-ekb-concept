<?php

namespace App\Filament\Resources\SitePages;

use App\Filament\Resources\EditorialResource;
use App\Filament\Support\ContentFields as F;
use App\Models\PageSection;
use App\Models\SitePage;
use BackedEnum;
use Filament\Forms\Components\Repeater;
use Filament\Forms\Components\Textarea;
use Filament\Forms\Components\TextInput;
use Filament\Schemas\Components\Section;
use Filament\Schemas\Schema;

class SitePageResource extends EditorialResource
{
    protected static ?string $model = SitePage::class;

    protected static ?string $modelLabel = 'страница';

    protected static ?string $pluralModelLabel = 'Страницы';

    protected static ?string $navigationLabel = 'Страницы';

    protected static string|BackedEnum|null $navigationIcon = 'heroicon-o-document-duplicate';

    protected static ?int $navigationSort = 1;

    public static function form(Schema $schema): Schema
    {
        return $schema->columns(1)->components([
            Section::make('Содержимое страницы')->schema([
                F::text('title', 'Заголовок страницы'),
                Textarea::make('intro')->label('Вступление')->rows(4)->maxLength(2000),
                F::image()->visible(fn (?SitePage $record): bool => filled($record?->image) || filled($record?->image_upload)),
            ]),
            Section::make('Блоки страницы')->description('Редактируйте текст и фото в существующих блоках. Их расположение на сайте сохраняется.')->schema([
                Repeater::make('sections')->label('Блоки страницы')->hiddenLabel()->relationship()->orderColumn('position')->addable(false)->deletable(false)->reorderable(false)
                    ->itemLabel(fn (array $state): string => $state['title'] ?: 'Текстовый блок')->collapsible()->schema([
                        TextInput::make('title')->label('Заголовок блока')->maxLength(200),
                        F::rich('body', 'Текст блока', 20000),
                        F::image()->visible(fn (?PageSection $record): bool => filled($record?->image) || filled($record?->image_upload)),
                    ]),
            ]),
            F::seo(),
        ]);
    }

    public static function canCreate(): bool
    {
        return false;
    }

    public static function getPages(): array
    {
        return [
            'index' => Pages\ListSitePages::route('/'),
            'edit' => Pages\EditSitePage::route('/{record}/edit'),
        ];
    }
}
