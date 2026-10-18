<?php

namespace App\Filament\Support;

use Filament\Forms\Components\RichEditor;
use Filament\Forms\Components\RichEditor\StateCasts\RichEditorStateCast;

class MarkdownRichEditor extends RichEditor
{
    public function getDefaultStateCasts(): array
    {
        return array_map(fn ($cast) => $cast instanceof RichEditorStateCast ? new MarkdownEditorStateCast($this) : $cast, parent::getDefaultStateCasts());
    }
}
