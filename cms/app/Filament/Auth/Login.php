<?php

namespace App\Filament\Auth;

use Filament\Forms\Components\TextInput;
use Filament\Schemas\Components\Component;
use Illuminate\Contracts\Support\Htmlable;
use Illuminate\Validation\ValidationException;

class Login extends \Filament\Auth\Pages\Login
{
    protected function getEmailFormComponent(): Component
    {
        return TextInput::make('username')->label('Логин')->required()->autocomplete('username')->autofocus();
    }

    protected function getCredentialsFromFormData(array $data): array
    {
        return ['username' => $data['username'], 'password' => $data['password'], 'is_active' => true, 'is_staff' => true];
    }

    protected function throwFailureValidationException(): never
    {
        throw ValidationException::withMessages(['data.username' => 'Не подошёл логин или пароль. Проверьте данные и попробуйте ещё раз.']);
    }

    public function getHeading(): string|Htmlable|null
    {
        return 'Вход в управление сайтом';
    }

    public function getSubheading(): string|Htmlable|null
    {
        return 'Используйте ваши логин и пароль.';
    }
}
