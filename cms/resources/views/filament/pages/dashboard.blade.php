<x-filament-panels::page>
    <div class="orion-editor-guide">
        <x-heroicon-o-information-circle class="orion-guide-icon" />
        <p><strong>Сохранить</strong> — оставить изменения в админке. <strong>Посмотреть</strong> — проверить результат. <strong>Опубликовать</strong> — обновить сайт.</p>
    </div>
    <div class="orion-destinations">
        @foreach ([
            [\App\Filament\Resources\SitePages\SitePageResource::getUrl(), 'Страницы', 'Тексты и фотографии главной и остальных страниц', 'heroicon-o-document-duplicate'],
            [\App\Filament\Resources\Services\ServiceResource::getUrl(), 'Услуги', 'Названия, описания и фотографии услуг', 'heroicon-o-wrench-screwdriver'],
            [\App\Filament\Resources\Projects\ProjectResource::getUrl(), 'Наши работы', 'Выполненные работы, адреса объектов и фотогалереи', 'heroicon-o-photo'],
            [\App\Filament\Resources\Articles\ArticleResource::getUrl(), 'Статьи', 'Полезные материалы и советы для посетителей', 'heroicon-o-pencil-square'],
            [\App\Filament\Pages\Contacts::getUrl(), 'Контакты компании', 'Телефон, название компании и общие подписи', 'heroicon-o-phone'],
        ] as [$url, $title, $description, $icon])
            <a href="{{ $url }}" class="orion-destination">
                @svg($icon, 'orion-destination-icon')
                <span><strong>{{ $title }}</strong><span>{{ $description }}</span></span>
                <x-heroicon-o-chevron-right class="orion-destination-arrow" />
            </a>
        @endforeach
    </div>
</x-filament-panels::page>
