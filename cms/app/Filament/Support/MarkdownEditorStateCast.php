<?php

namespace App\Filament\Support;

use Filament\Forms\Components\RichEditor\StateCasts\RichEditorStateCast;
use Illuminate\Support\Str;

class MarkdownEditorStateCast extends RichEditorStateCast
{
    public function set(mixed $state): array
    {
        if (is_string($state)) {
            $state = Str::markdown($state, ['html_input' => 'strip', 'allow_unsafe_links' => false]);
            if (trim($state) === '') {
                $state = '<p></p>';
            }
        }

        return parent::set($state);
    }
}
