<?php

namespace App\Providers\Filament;

use App\Filament\Auth\Login;
use App\Filament\Pages\Dashboard;
use App\Http\Middleware\PrivateResponse;
use Filament\Actions\Action;
use Filament\Enums\ThemeMode;
use Filament\FontProviders\LocalFontProvider;
use Filament\Http\Middleware\Authenticate;
use Filament\Http\Middleware\AuthenticateSession;
use Filament\Http\Middleware\DisableBladeIconComponents;
use Filament\Http\Middleware\DispatchServingFilamentEvent;
use Filament\Panel;
use Filament\PanelProvider;
use Filament\Support\Assets\Css;
use Filament\Support\Colors\Color;
use Filament\Support\Enums\Width;
use Illuminate\Cookie\Middleware\AddQueuedCookiesToResponse;
use Illuminate\Cookie\Middleware\EncryptCookies;
use Illuminate\Foundation\Http\Middleware\PreventRequestForgery;
use Illuminate\Routing\Middleware\SubstituteBindings;
use Illuminate\Session\Middleware\StartSession;
use Illuminate\View\Middleware\ShareErrorsFromSession;

class AdminPanelProvider extends PanelProvider
{
    public function panel(Panel $panel): Panel
    {
        return $panel->default()->id('admin')->path('admin')->login(Login::class)
            ->brandName('СК Орион')->favicon(asset('favicon.ico'))->darkMode(true, isForced: true)->defaultThemeMode(ThemeMode::Dark)
            ->font('Onest', url: asset('admin-assets/fonts.css'), provider: LocalFontProvider::class)
            ->assets([Css::make('orion-editor', asset('admin-assets/editor.css?v=20261019-filament'))])
            ->colors(['primary' => Color::Orange, 'gray' => Color::Zinc])
            ->sidebarWidth('17rem')->maxContentWidth(Width::Full)->globalSearch(false)->unsavedChangesAlerts()->databaseTransactions()
            ->discoverResources(in: app_path('Filament/Resources'), for: 'App\Filament\Resources')
            ->discoverPages(in: app_path('Filament/Pages'), for: 'App\Filament\Pages')
            ->pages([Dashboard::class])->widgets([])
            ->userMenuItems([Action::make('site')->label('Открыть сайт')->icon('heroicon-o-arrow-top-right-on-square')->url('/')->openUrlInNewTab()])
            ->middleware([
                EncryptCookies::class, AddQueuedCookiesToResponse::class, StartSession::class, AuthenticateSession::class,
                ShareErrorsFromSession::class, PreventRequestForgery::class, SubstituteBindings::class,
                DisableBladeIconComponents::class, DispatchServingFilamentEvent::class, PrivateResponse::class,
            ])->authMiddleware([Authenticate::class]);
    }
}
