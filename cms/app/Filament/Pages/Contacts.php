<?php

namespace App\Filament\Pages;

use App\Exceptions\PublicationException;
use App\Filament\Support\ContentFields as F;
use App\Models\SiteSetting;
use App\Services\Publisher;
use BackedEnum;
use Filament\Forms\Components\Textarea;
use Filament\Forms\Components\TextInput;
use Filament\Notifications\Notification;
use Filament\Pages\Page;
use Filament\Schemas\Components\Section;
use Filament\Schemas\Schema;

class Contacts extends Page
{
    protected static string|BackedEnum|null $navigationIcon = 'heroicon-o-phone';

    protected static ?string $navigationLabel = 'Контакты компании';

    protected static ?string $title = 'Контакты компании';

    protected static ?int $navigationSort = 5;

    protected string $view = 'filament.pages.contacts';

    public ?array $data = [];

    public function mount(): void
    {
        $this->form->fill(SiteSetting::firstOrFail()->toArray());
    }

    public function form(Schema $schema): Schema
    {
        return $schema->statePath('data')->components([
            Section::make('Общие данные сайта')->description('Эти данные используются в шапке, подвале и контактных блоках. Сохранение сразу обновит их на сайте.')->schema([
                F::text('company_name', 'Название компании', 60),
                TextInput::make('company_subtitle')->label('Подпись под логотипом')->maxLength(100),
                F::text('phone', 'Телефон', 30)->tel()->rule('regex:/^\+?[0-9()\s-]{10,30}$/')->helperText('Этот номер будет во всех кнопках «Позвонить».'),
                F::text('region', 'Где работаем', 200),
                Textarea::make('footer_description')->label('Коротко о компании')->rows(3)->maxLength(300)->helperText('Описание внизу каждой страницы.'),
                TextInput::make('emergency_notice')->label('Подпись об аварийных обращениях')->maxLength(200),
            ]),
        ])->columns(1);
    }

    public function save(): void
    {
        $record = SiteSetting::firstOrFail();
        $record->fill($this->form->getState())->save();
        try {
            app(Publisher::class)->publishSettings($record);
            Notification::make()->title('Контакты обновлены на сайте')->success()->send();
        } catch (PublicationException $exception) {
            Notification::make()->title('Данные сохранены, но сайт пока не обновлён')->body($exception->getMessage().' Попробуйте сохранить ещё раз.')->danger()->persistent()->send();
        }
    }
}
