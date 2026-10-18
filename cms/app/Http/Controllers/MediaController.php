<?php

namespace App\Http\Controllers;

use App\Exceptions\PublicationException;
use App\Services\ImageStore;
use Illuminate\Http\Request;
use Symfony\Component\HttpFoundation\BinaryFileResponse;
use Symfony\Component\HttpFoundation\ResponseHeaderBag;

class MediaController extends Controller
{
    public function __invoke(Request $request, string $path, ImageStore $images): BinaryFileResponse
    {
        abort_unless($request->user()?->is_staff && $request->user()?->is_active, 404);
        if ($request->routeIs('cms.photo')) {
            $path = $request->query('photo');
            abort_unless(is_string($path), 404);
        }
        try {
            $file = $images->privatePath($path);
        } catch (PublicationException) {
            abort(404);
        }
        $dimensions = @getimagesize($file);
        abort_unless($dimensions && in_array($dimensions[2], [IMAGETYPE_JPEG, IMAGETYPE_PNG, IMAGETYPE_WEBP], true), 404);

        $extension = match ($dimensions[2]) {
            IMAGETYPE_JPEG => 'jpg', IMAGETYPE_PNG => 'png', default => 'webp',
        };

        return response()->file($file, [
            'Content-Type' => $dimensions['mime'], 'Cache-Control' => 'private,no-store',
            'X-Robots-Tag' => 'noindex,nofollow', 'X-Content-Type-Options' => 'nosniff',
        ])->setContentDisposition(ResponseHeaderBag::DISPOSITION_INLINE, 'Фотография.'.$extension, 'photo.'.$extension);
    }
}
