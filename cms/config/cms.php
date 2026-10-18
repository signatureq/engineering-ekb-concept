<?php

return [
    'site_root' => env('CMS_SITE_ROOT', dirname(base_path())),
    'data_dir' => env('CMS_DATA_DIR', storage_path('app/cms')),
    'media_root' => env('CMS_MEDIA_ROOT', env('CMS_DATA_DIR', storage_path('app/cms')).'/media'),
    'public_root' => env('CMS_PUBLIC_ROOT', env('CMS_DATA_DIR', storage_path('app/cms')).'/public'),
    'python_binary' => env('CMS_PYTHON_BINARY', 'python3'),
    'site_url' => rtrim(env('PUBLIC_SITE_URL', 'https://xn---96-6cdfvaagt9ccbsyd1b9kh.xn--p1ai'), '/'),
    'inquiry_to_email' => env('INQUIRY_TO_EMAIL', ''),
    'timezone' => 'Asia/Yekaterinburg',
];
