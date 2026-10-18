<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        $common = function (Blueprint $table): void {
            $table->id();
            $table->string('title', 200);
            $table->string('seo_title', 100)->default('');
            $table->string('seo_description', 200)->default('');
            $table->json('published_payload')->nullable();
            $table->timestamp('first_published_at')->nullable();
            $table->timestamp('updated_at')->nullable();
        };
        Schema::create('articles', function (Blueprint $table) use ($common): void {
            $common($table);
            $table->string('slug', 140)->unique();
            $table->string('category', 60)->default('');
            $table->text('summary');
            $table->longText('body');
            $table->string('cover', 240)->default('assets/client/pipeline-installation.jpg');
            $table->string('cover_upload', 300)->default('');
            $table->string('cover_alt', 240)->default('');
            $table->unsignedInteger('cover_width')->default(1200);
            $table->unsignedInteger('cover_height')->default(1600);
            $table->string('service', 140)->default('');
            $table->boolean('featured')->default(false);
            $table->timestamp('last_published_at')->nullable();
            $table->timestamp('created_at')->nullable();
        });
        Schema::create('site_settings', function (Blueprint $table): void {
            $table->id();
            $table->string('company_name', 60);
            $table->string('phone', 30);
            $table->string('company_subtitle', 100);
            $table->string('region', 200);
            $table->string('footer_description', 300);
            $table->string('emergency_notice', 200);
            $table->text('hero_description');
            $table->json('published_payload')->nullable();
            $table->timestamp('updated_at')->nullable();
        });
        Schema::create('site_pages', function (Blueprint $table) use ($common): void {
            $common($table);
            $table->string('route', 80)->unique();
            $table->string('label', 80);
            $table->text('intro')->default('');
            $table->string('image', 240)->default('');
            $table->string('image_upload', 300)->default('');
        });
        Schema::create('page_sections', function (Blueprint $table): void {
            $table->id();
            $table->foreignId('page_id')->constrained('site_pages')->cascadeOnDelete();
            $table->string('key', 60);
            $table->string('title', 200)->default('');
            $table->longText('body')->default('');
            $table->string('image', 240)->default('');
            $table->string('image_upload', 300)->default('');
            $table->unsignedInteger('position')->default(0);
            $table->unique(['page_id', 'key']);
        });
        Schema::create('services', function (Blueprint $table) use ($common): void {
            $common($table);
            $table->string('slug', 140)->unique();
            $table->text('summary');
            $table->longText('intro');
            $table->text('scope');
            $table->text('prepare');
            $table->string('image', 240)->default('assets/client/pipeline-installation.jpg');
            $table->string('image_upload', 300)->default('');
            $table->unsignedInteger('position')->default(10);
        });
        Schema::create('projects', function (Blueprint $table) use ($common): void {
            $common($table);
            $table->string('slug', 140)->unique();
            $table->text('summary');
            $table->longText('description');
            $table->text('details')->default('');
            $table->string('location', 240)->default('');
            $table->string('category', 20)->default('inside');
            $table->foreignId('service_id')->nullable()->constrained('services')->nullOnDelete();
            $table->unsignedInteger('position')->default(10);
        });
        Schema::create('project_photos', function (Blueprint $table): void {
            $table->id();
            $table->foreignId('project_id')->constrained('projects')->cascadeOnDelete();
            $table->string('caption', 240)->default('');
            $table->string('image_upload', 300)->default('');
            $table->json('source');
            $table->unsignedInteger('position')->default(10);
        });
        Schema::create('content_imports', function (Blueprint $table): void {
            $table->id();
            $table->string('key', 60)->unique();
        });
    }

    public function down(): void
    {
        foreach (['content_imports', 'project_photos', 'projects', 'services', 'page_sections', 'site_pages', 'site_settings', 'articles'] as $table) {
            Schema::dropIfExists($table);
        }
    }
};
