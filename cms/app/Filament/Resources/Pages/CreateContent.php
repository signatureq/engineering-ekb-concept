<?php

namespace App\Filament\Resources\Pages;

use App\Models\Article;
use App\Models\Project;
use App\Models\Service;
use Filament\Actions\Action;
use Filament\Resources\Pages\CreateRecord;
use Illuminate\Contracts\Support\Htmlable;

abstract class CreateContent extends CreateRecord
{
    protected static bool $canCreateAnother = false;

    public static bool $formActionsAreSticky = true;

    public function getTitle(): string|Htmlable
    {
        return match (static::getResource()::getModel()) {
            Article::class => 'Добавить статью',
            Service::class => 'Добавить услугу',
            Project::class => 'Добавить работу',
            default => 'Добавить материал',
        };
    }

    public function getSubheading(): string|Htmlable|null
    {
        return 'Заполните основные поля и сохраните. Затем можно посмотреть результат и опубликовать его на сайте.';
    }

    protected function getCreateFormAction(): Action
    {
        return parent::getCreateFormAction()->label('Сохранить и продолжить');
    }

    protected function getRedirectUrl(): string
    {
        return $this->getResourceUrl('edit', ['record' => $this->record]);
    }

    protected function getCreatedNotificationTitle(): ?string
    {
        return 'Черновик сохранён';
    }
}
