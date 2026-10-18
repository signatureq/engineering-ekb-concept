<x-filament-panels::page>
    <form wire:submit="save" class="orion-settings-form">
        {{ $this->form }}
        <div class="orion-form-footer">
            <x-filament::button type="submit" wire:loading.attr="disabled" wire:target="save">Сохранить и опубликовать</x-filament::button>
        </div>
    </form>
</x-filament-panels::page>
