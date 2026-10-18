<?php

namespace App\Models;

use App\Services\ContentFields;
use App\Services\Publisher;
use Illuminate\Database\Eloquent\Model;

class SiteSetting extends Model
{
    public const CREATED_AT = null;

    public const CONTENT_FIELDS = ['company_name', 'phone', 'hero_description', 'company_subtitle', 'region', 'footer_description', 'emergency_notice'];

    protected $guarded = [];

    protected $attributes = [
        'company_name' => 'СК Орион', 'phone' => '+7 (902) 445-30-01',
        'company_subtitle' => 'строительная компания', 'region' => 'Екатеринбург и Свердловская область',
        'footer_description' => 'Монтаж, теплоизоляция и аварийные работы.', 'emergency_notice' => 'Аварийные обращения — 24/7',
        'hero_description' => 'Работаем с трубопроводами любого диаметра. Делаем теплоизоляцию инженерных систем и устраняем аварии.',
    ];

    protected function casts(): array
    {
        return ['published_payload' => 'array'];
    }

    protected static function booted(): void
    {
        static::saving(fn (self $record) => ContentFields::normalizeStrings($record, self::CONTENT_FIELDS));
    }

    public function publicationStatus(): string
    {
        if ($this->published_payload === null) {
            return 'Черновик';
        }

        return app(Publisher::class)->draftPayload($this) == $this->published_payload ? 'Опубликовано' : 'Есть изменения';
    }

    public function publicUrl(): string
    {
        return '/';
    }
}
