<?php

namespace App\Filament\Support;

use App\Services\ImageStore;
use Filament\Forms\Components\FileUpload;
use Filament\Forms\Components\RichEditor;
use Filament\Forms\Components\Textarea;
use Filament\Forms\Components\TextInput;
use Filament\Schemas\Components\Section;
use Illuminate\Support\Facades\Storage;
use League\HTMLToMarkdown\HtmlConverter;
use Livewire\Features\SupportFileUploads\TemporaryUploadedFile;

class ContentFields
{
    public static function text(string $name, string $label, int $limit = 200): TextInput
    {
        return TextInput::make($name)->label($label)->maxLength($limit)->required();
    }

    public static function rich(string $name, string $label, int $limit = 30000): RichEditor
    {
        return MarkdownRichEditor::make($name)->label($label)
            ->toolbarButtons([['bold', 'italic', 'link'], ['h2', 'h3'], ['bulletList', 'orderedList'], ['undo', 'redo']])
            ->dehydrateStateUsing(fn (?string $state): string => (new HtmlConverter(['strip_tags' => true, 'remove_nodes' => 'script style iframe', 'hard_break' => true, 'header_style' => 'atx']))->convert($state ?? ''))
            ->maxLength($limit)->helperText('Пишите как в обычном документе. Подзаголовки, списки и ссылки добавляются кнопками.')->columnSpanFull();
    }

    public static function image(string $name = 'image_upload', string $label = 'Фотография'): FileUpload
    {
        return FileUpload::make($name)->label($label)->disk('cms-private')->visibility('private')
            ->extraAttributes(['class' => 'orion-photo-upload'])->image()->acceptedFileTypes(['image/jpeg', 'image/png', 'image/webp'])->maxSize(5120)
            ->maxFiles(1)->imagePreviewHeight('200')->downloadable(false)->openable(false)
            ->getUploadedFileUsing(function (string $file): ?array {
                $disk = Storage::disk('cms-private');
                if (! $disk->exists($file)) {
                    return null;
                }

                return ['name' => 'Текущая фотография', 'size' => $disk->size($file), 'type' => $disk->mimeType($file), 'url' => $disk->temporaryUrl($file, now()->addMinutes(30))];
            })
            ->saveUploadedFileUsing(fn (TemporaryUploadedFile $file): string => app(ImageStore::class)->store($file))
            ->helperText('JPG, PNG или WebP до 5 МБ. Фото появится на сайте после публикации.');
    }

    public static function seo(): Section
    {
        return Section::make('Дополнительно — вид в поиске')->description('Заполнять необязательно. Если оставить поля пустыми, сайт составит их из основного текста.')
            ->collapsible()->collapsed()->schema([
                TextInput::make('seo_title')->label('Название в поиске')->maxLength(100),
                Textarea::make('seo_description')->label('Описание в поиске')->rows(3)->maxLength(200),
            ])->columnSpanFull();
    }

    public static function order(): TextInput
    {
        return TextInput::make('position')->label('Место в списке')->numeric()->minValue(0)->maxValue(10000)->default(10)->required()->helperText('Меньшее число — ближе к началу.');
    }
}
