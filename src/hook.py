# для PyInstaller
import os
import sys
from PyInstaller.utils.hooks import collect_data_files

datas = [
    *collect_data_files('src'),
    ('src/data/*', 'data'),
    ('src/assets/*', 'assets')
]

# настройки для macOS
if sys.platform == 'darwin':
    extra_args = [
        '--osx-bundle-identifier', 'com.yourdomain.crossword',
        '--icon', 'src/assets/crossword.icns'  # Конвертируйте ico в icns заранее
    ]