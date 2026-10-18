<?php

namespace App\Filament\Resources\Pages;

use App\Exceptions\PublicationException;
use App\Models\Article;
use App\Models\Project;
use App\Models\Service;
use App\Models\SitePage;
use App\Services\Publisher;
use Filament\Actions\Action;
use Filament\Actions\DeleteAction;
use Filament\Notifications\Notification;
use Filament\Resources\Pages\EditRecord;
use Illuminate\Contracts\Support\Htmlable;

abstract class EditContent extends EditRecord
{
    public static bool $formActionsAreSticky = true;

    public function getTitle(): string|Htmlable
    {
        return match (true) {
            $this->record instanceof Article => 'Редактировать статью',
            $this->record instanceof Service => 'Редактировать услугу',
            $this->record instanceof Project => 'Редактировать работу',
            default => 'Редактировать страницу',
        };
    }

    public function getSubheading(): string|Htmlable|null
    {
        return 'Сохраните изменения, чтобы продолжить позже. Нажмите «Опубликовать», когда материал будет готов для сайта.';
    }

    protected function getHeaderActions(): array
    {
        return [Action::make('openSite')->label('Открыть на сайте')->color('gray')->icon('heroicon-o-arrow-top-right-on-square')->url(fn (): string => $this->record->publicUrl())->openUrlInNewTab()->visible(fn (): bool => $this->record->published_payload !== null)];
    }

    protected function getFormActions(): array
    {
        return [
            $this->getSaveFormAction()->label('Сохранить')->color('gray'),
            Action::make('preview')->label('Посмотреть')->color('gray')->icon('heroicon-o-eye')
                ->action(function (): void {
                    $this->save(false, false);
                    session()->flash('preview_ready', true);
                    $this->redirect(route('cms.preview', ['kind' => match (true) {
                        $this->record instanceof Article => 'article', $this->record instanceof Service => 'service', $this->record instanceof Project => 'project', default => 'page',
                    }, 'id' => $this->record->id]));
                }),
            Action::make('publish')->label('Опубликовать')->icon('heroicon-o-check')->action(function (): void {
                $this->save(false, false);
                try {
                    app(Publisher::class)->publish($this->record->fresh());
                    $this->record->refresh();
                    $this->refreshFormData(['published_payload', 'first_published_at']);
                    Notification::make()->title('Изменения опубликованы')->body('Обновлённый материал уже на сайте.')->success()->send();
                } catch (PublicationException $exception) {
                    Notification::make()->title('Не удалось опубликовать')->body($exception->getMessage())->danger()->persistent()->send();
                }
            }),
            Action::make('unpublish')->label('Снять с публикации')->color('gray')->requiresConfirmation()->modalHeading('Убрать материал с сайта?')->modalDescription('Он останется в админке. Позже вы сможете опубликовать его снова.')
                ->modalSubmitActionLabel('Убрать с сайта')->visible(fn (): bool => ! ($this->record instanceof SitePage) && $this->record->published_payload !== null)
                ->action(function (): void {
                    try {
                        app(Publisher::class)->unpublish($this->record);
                        $this->record->refresh();
                        Notification::make()->title('Материал убран с сайта')->success()->send();
                        $this->refreshFormData(['published_payload']);
                    } catch (PublicationException $exception) {
                        Notification::make()->title('Не удалось убрать материал')->body($exception->getMessage())->danger()->send();
                    }
                }),
            DeleteAction::make()->label('Удалить черновик')->authorize(fn (): bool => static::getResource()::canDelete($this->record))->visible(fn (): bool => static::getResource()::canDelete($this->record))->modalHeading('Удалить черновик?')->modalDescription('Восстановить его из админки будет нельзя.'),
        ];
    }

    protected function getSavedNotificationTitle(): ?string
    {
        return 'Изменения сохранены. На сайте пока остаётся опубликованная версия.';
    }

    protected function getRedirectUrl(): ?string
    {
        return null;
    }
}
