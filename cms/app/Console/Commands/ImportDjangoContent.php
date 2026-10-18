<?php

namespace App\Console\Commands;

use App\Exceptions\PublicationException;
use App\Services\ContentImporter;
use Illuminate\Console\Command;

class ImportDjangoContent extends Command
{
    protected $signature = 'cms:import {path : Private JSON export} {--media= : Private media backup directory}';

    protected $description = 'Import the private Django backup into an empty Laravel database once.';

    public function handle(ContentImporter $importer): int
    {
        try {
            $counts = $importer->import($this->argument('path'), $this->option('media'));
        } catch (\Throwable $error) {
            $this->error('Импорт остановлен. '.($error instanceof PublicationException ? $error->getMessage() : 'Проверьте файл переноса и соответствие структуры базы. Данные не изменены.'));

            return self::FAILURE;
        }
        $this->info('Данные и учётные записи перенесены. Пароли и опубликованные адреса сохранены.');
        $this->line(collect($counts)->map(fn ($count, $table) => $table.': '.$count)->implode(', '));

        return self::SUCCESS;
    }
}
