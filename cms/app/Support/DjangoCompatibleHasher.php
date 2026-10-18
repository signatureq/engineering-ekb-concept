<?php

namespace App\Support;

use Illuminate\Hashing\BcryptHasher;
use SensitiveParameter;

class DjangoCompatibleHasher extends BcryptHasher
{
    public function check(#[SensitiveParameter] $value, $hashedValue, array $options = []): bool
    {
        if (str_starts_with((string) $hashedValue, 'pbkdf2_sha256$')) {
            $parts = explode('$', $hashedValue);
            if (count($parts) !== 4 || ! ctype_digit($parts[1]) || (int) $parts[1] < 1 || (int) $parts[1] > 10000000) {
                return false;
            }

            return hash_equals($parts[3], base64_encode(hash_pbkdf2('sha256', (string) $value, $parts[2], (int) $parts[1], 32, true)));
        }

        return parent::check($value, $hashedValue, $options);
    }

    public function needsRehash($hashedValue, array $options = []): bool
    {
        return str_starts_with((string) $hashedValue, 'pbkdf2_sha256$') || parent::needsRehash($hashedValue, $options);
    }

    public function verifyConfiguration($value): bool
    {
        return str_starts_with((string) $value, 'pbkdf2_sha256$') || parent::verifyConfiguration($value);
    }
}
