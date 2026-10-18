<?php
return [
    'file_upload' => [
        'placeholder' => 'Фотография пока не выбрана',
        'actions' => ['download' => ['label' => 'Скачать'], 'open' => ['label' => 'Открыть фотографию']],
    ],
    'repeater' => [
        'reordering' => ['item' => 'Фотография', 'position' => ':label, место :position из :count', 'moved' => ':label перемещена на место :position из :count'],
        'columns' => ['actions' => ['label' => 'Действия'], 'reorder' => ['label' => 'Изменить порядок']],
    ],
    'rich_editor' => ['toolbar' => ['label' => 'Форматирование текста'], 'actions' => ['close_panel' => ['label' => 'Закрыть настройки']]],
    'select' => ['actions' => ['clear' => ['label' => 'Убрать выбор'], 'remove_option' => ['label' => 'Убрать :label']], 'error_message' => 'Не удалось загрузить список. Обновите страницу.', 'required_description' => 'Выберите вариант.', 'search_label' => 'Поиск'],
];
