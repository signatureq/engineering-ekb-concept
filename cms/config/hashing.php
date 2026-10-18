<?php

return ['driver' => env('HASH_DRIVER', 'django-compatible'), 'bcrypt' => ['rounds' => 12, 'verify' => true, 'limit' => null], 'rehash_on_login' => true];
