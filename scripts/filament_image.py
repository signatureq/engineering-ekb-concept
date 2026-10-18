#!/usr/bin/env python3
"""Validate and optimise a CMS photograph without retaining EXIF metadata."""
import argparse
import json
from pathlib import Path
import warnings
from PIL import Image, ImageOps, UnidentifiedImageError


def optimize(source, destination):
    source, destination = Path(source), Path(destination)
    if source.stat().st_size > 5 * 1024 * 1024:
        raise ValueError('Фотография больше 5 МБ. Уменьшите файл и загрузите снова.')
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(source) as image:
                if image.format not in ('JPEG', 'PNG', 'WEBP') or image.width * image.height > 16_000_000:
                    raise ValueError('Нужен JPG, PNG или WebP до 16 мегапикселей.')
                image = ImageOps.exif_transpose(image).convert('RGB')
                image.thumbnail((1800, 1800))
                destination.parent.mkdir(parents=True, exist_ok=True)
                image.save(destination, 'WEBP', quality=84)
                return {'width': image.width, 'height': image.height}
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError, Image.DecompressionBombWarning) as error:
        raise ValueError('Не удалось прочитать фотографию. Загрузите другой JPG, PNG или WebP.') from error


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('destination', type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(optimize(args.source, args.destination)))
    except ValueError as error:
        parser.exit(1, str(error) + '\n')


if __name__ == '__main__':
    main()
