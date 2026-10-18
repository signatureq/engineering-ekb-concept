<?php

namespace App\Http\Middleware;

use Closure;
use Illuminate\Foundation\Http\Middleware\PreventRequestForgery;
use Illuminate\Session\TokenMismatchException;

class VerifyInquiryCsrf extends PreventRequestForgery
{
    public function handle($request, Closure $next)
    {
        if ($request->is('api/inquiry') && $request->isMethod('POST')) {
            $origin = $request->header('Origin');
            if ($origin !== null && rtrim($origin, '/') !== $request->getSchemeAndHttpHost()) {
                throw new TokenMismatchException('Источник запроса не совпадает с сайтом. Обновите страницу и попробуйте снова.');
            }
        }

        return parent::handle($request, $next);
    }

    protected function getTokenFromRequest($request)
    {
        return $request->header('X-CSRFToken') ?: parent::getTokenFromRequest($request);
    }
}
