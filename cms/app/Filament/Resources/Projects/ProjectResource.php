<?php

namespace App\Filament\Resources\Projects;

use App\Filament\Resources\EditorialResource;
use App\Filament\Support\ContentFields as F;
use App\Models\Project;
use BackedEnum;
use Filament\Forms\Components\Repeater;
use Filament\Forms\Components\Select;
use Filament\Forms\Components\Textarea;
use Filament\Forms\Components\TextInput;
use Filament\Schemas\Components\Section;
use Filament\Schemas\Schema;

class ProjectResource extends EditorialResource
{
    protected static ?string $model = Project::class;

    protected static ?string $modelLabel = 'работа';

    protected static ?string $pluralModelLabel = 'Наши работы';

    protected static ?string $navigationLabel = 'Наши работы';

    protected static string|BackedEnum|null $navigationIcon = 'heroicon-o-photo';

    protected static ?int $navigationSort = 3;

    public static function form(Schema $schema): Schema
    {
        return $schema->columns(1)->components([
            Section::make('Об этой работе')->schema([
                F::text('title', 'Название работы'),
                Textarea::make('summary')->label('Короткое описание')->rows(3)->required()->maxLength(700)->helperText('Показывается в списке работ.'),
                F::rich('description', 'Описание работы')->required(),
                Textarea::make('details')->label('Что сделано')->rows(4)->maxLength(5000)->helperText('Необязательно. Каждый пункт — с новой строки.'),
                TextInput::make('location')->label('Адрес или название объекта')->maxLength(240)->helperText('Необязательно. Укажите, если адрес можно публиковать.'),
                Select::make('category')->label('Направление')->options(['outside' => 'Наружные сети', 'inside' => 'Внутренние системы', 'insulation' => 'Теплоизоляция'])->default('inside')->required()->native(),
                Select::make('service_id')->label('Связанная услуга')->relationship('service', 'title')->placeholder('Не выбрана')->native(),
            ]),
            Section::make('Фотографии')->description('Первая фотография станет обложкой работы. Перетаскивайте фото, чтобы изменить порядок. Для публикации нужно хотя бы одно фото.')->schema([
                Repeater::make('photos')->label('Фотографии')->hiddenLabel()->relationship()->orderColumn('position')->reorderable()->addActionLabel('Добавить фотографию')->defaultItems(0)
                    ->itemLabel(fn (array $state): string => $state['caption'] ?: 'Фотография')->schema([
                        F::image()->required(),
                        TextInput::make('caption')->label('Подпись под фото')->maxLength(240)->helperText('Необязательно. Без подписи используем название работы.'),
                    ]),
            ]),
            Section::make('Порядок в списке')->schema([F::order()]),
            F::seo(),
        ]);
    }

    public static function getPages(): array
    {
        return [
            'index' => Pages\ListProjects::route('/'),
            'create' => Pages\CreateProject::route('/create'),
            'edit' => Pages\EditProject::route('/{record}/edit'),
        ];
    }
}
