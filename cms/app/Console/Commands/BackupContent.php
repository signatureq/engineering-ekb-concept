<?php

namespace App\Console\Commands;

use App\Services\Publisher;
use Illuminate\Console\Command;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\File;

class BackupContent extends Command
{
    protected $signature = 'cms:backup {--output= : New private directory outside the public site}';

    protected $description = 'Create a consistent private SQLite and media backup.';

    public function handle(Publisher $publisher): int
    {
        $output = $this->option('output');
        $database = config('database.connections.sqlite.database');
        if (! $output || $output[0] !== '/' || file_exists($output) || ! is_file($database) || config('database.default') !== 'sqlite') {
            $this->error('Choose a new absolute private directory and an existing SQLite database.');

            return self::FAILURE;
        }
        $public = realpath(config('cms.public_root'));
        $parent = realpath(dirname($output));
        if (! $parent || ($public && ($parent === $public || str_starts_with($parent, $public.'/')))) {
            $this->error('The backup must be outside the public website.');

            return self::FAILURE;
        }
        try {
            $publisher->withLock(function () use ($output): void {
                File::ensureDirectoryExists($output, 0700);
                $pdo = DB::connection()->getPdo();
                $pdo->exec('VACUUM INTO '.$pdo->quote($output.'/cms.sqlite3'));
                chmod($output.'/cms.sqlite3', 0600);
                if (is_dir(config('cms.media_root'))) {
                    File::copyDirectory(config('cms.media_root'), $output.'/media');
                    chmod($output.'/media', 0700);
                }
            });
        } catch (\Throwable $error) {
            $this->error('Backup failed: '.$error::class);

            return self::FAILURE;
        }
        $this->info('Private database and media backup created.');

        return self::SUCCESS;
    }
}
