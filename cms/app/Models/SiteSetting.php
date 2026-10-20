<?php

namespace App\Models;

use App\Services\ContentFields;
use App\Services\Publisher;
use Illuminate\Database\Eloquent\Model;

class SiteSetting extends Model
{
    public const CREATED_AT = null;

    public const CONTENT_FIELDS = ['company_name', 'phone', 'hero_description', 'company_subtitle', 'region', 'footer_description', 'emergency_notice', 'max_url', 'office_address'];

    public const MAX_URL_RULE = 'regex:~\Ahttps://(?:www\.)?max\.ru/[^\s]+\z~iu';

    protected $guarded = [];

    protected $attributes = [
        'company_name' => 'СК Орион', 'phone' => '+7 (902) 445-30-01',
        'company_subtitle' => 'строительная компания', 'region' => 'Екатеринбург и Свердловская область',
        'footer_description' => 'Монтаж, теплоизоляция и аварийные работы.', 'emergency_notice' => 'Аварийные обращения — 24/7',
        'hero_description' => 'Работаем с трубопроводами любого диаметра. Делаем теплоизоляцию инженерных систем и устраняем аварии.',
        'max_url' => '', 'office_address' => '',
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

        $published = array_replace(['max_url' => '', 'office_address' => ''], $this->published_payload);

        return app(Publisher::class)->draftPayload($this) == $published ? 'Опубликовано' : 'Есть изменения';
    }

    public function publicUrl(): string
    {
        return '/';
    }
}
