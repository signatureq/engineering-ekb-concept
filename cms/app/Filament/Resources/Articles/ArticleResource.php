<?php

namespace App\Filament\Resources\Articles;

use App\Filament\Resources\EditorialResource;
use App\Filament\Support\ContentFields as F;
use App\Models\Article;
use BackedEnum;
use Filament\Forms\Components\Select;
use Filament\Schemas\Components\Section;
use Filament\Schemas\Schema;

class ArticleResource extends EditorialResource
{
    protected static ?string $model = Article::class;

    protected static ?string $modelLabel = 'статья';

    protected static ?string $pluralModelLabel = 'Статьи';

    protected static ?string $navigationLabel = 'Статьи';

    protected static string|BackedEnum|null $navigationIcon = 'heroicon-o-pencil-square';

    protected static ?int $navigationSort = 4;

    public static function form(Schema $schema): Schema
    {
        return $schema->columns(1)->components([
            Section::make('Статья')->schema([
                F::text('title', 'Название статьи'),
                F::rich('body', 'Текст статьи', 100000)->required(),
            ]),
            Section::make('Фотография')->description('Загрузите свою фотографию или выберите фото из наших работ.')->schema([
                F::image('cover_upload', 'Загрузить фотографию'),
                Select::make('cover')->label('Или фото из наших работ')->options([
                    'assets/client/pipeline-installation.jpg' => 'Монтаж трубопроводов',
                    'assets/client/pipeline-welding.jpg' => 'Сварка труб',
                    'assets/client/repair-team.jpg' => 'Коммерческий узел учёта',
                    'assets/client/pipe-insulation.jpg' => 'Теплоизоляция в помещении',
                    'assets/client/heat-network-chamber.jpg' => 'Камера тепловой сети',
                    'assets/projects/nasosnyy-uzel/01.webp' => 'Насосный узел',
                    'assets/projects/naruzhnye-seti/01.webp' => 'Наружная трасса',
                    'assets/projects/teploizolyaciya-naruzhnyh-setey/01.webp' => 'Наружная теплоизоляция',
                ])->default('assets/client/pipeline-installation.jpg')->required()->native()->helperText('Используется, если загруженная фотография не выбрана.'),
            ]),
            F::seo(),
        ]);
    }

    public static function getPages(): array
    {
        return [
            'index' => Pages\ListArticles::route('/'),
            'create' => Pages\CreateArticle::route('/create'),
            'edit' => Pages\EditArticle::route('/{record}/edit'),
        ];
    }
}
