<?php

namespace App\Console\Commands;

use App\Services\Publisher;
use Illuminate\Console\Command;

class BuildSite extends Command
{
    protected $signature = 'cms:build';

    protected $description = 'Atomically rebuild the public website from published snapshots only.';

    public function handle(Publisher $publisher): int
    {
        try {
            $publisher->build();
        } catch (\Throwable $error) {
            $this->error($error->getMessage());

            return self::FAILURE;
        }
        $this->info('Сайт собран из опубликованных материалов. Черновики не затронуты.');

        return self::SUCCESS;
    }
}
