
# второй вариант: реализация на PyQt5

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget,
                             QVBoxLayout, QPushButton, QLabel,
                             QStackedWidget, QHBoxLayout, QMessageBox,
                             QGridLayout, QLineEdit, QDialog,
                             QSlider)
from PyQt5.QtCore import (Qt, QSettings, QSize, QTimer, QUrl, QOperatingSystemVersion, QStandardPaths)
from PyQt5.QtMultimedia import (QSoundEffect, QMediaPlayer, QMediaContent)
from PyQt5 import QtGui

import os
import sqlite3
import csv
import sys

from pathlib import Path

class ResourceManager: # менеджер путей к файлам проекта
    @staticmethod
    def get_base_path():
        if getattr(sys, 'frozen', False):
            return Path(sys._MEIPASS) # режим собранного приложения (после сборки PyInstaller)
        return Path(__file__).parent

    @staticmethod
    def resource_path(relative_path): # полный путь файла по названию
        base_path = ResourceManager.get_base_path()
        full_path = base_path / "data" / relative_path
        # Создаем папку, если ее нет
        os.makedirs(full_path.parent, exist_ok=True)
        return str(full_path)

    @staticmethod
    def get_icon_path(relative_path): # полный путь иконки по названию
        base_path = ResourceManager.get_base_path()
        full_path = base_path / "assets" / relative_path
        os.makedirs(full_path.parent, exist_ok=True)
        return str(full_path)

db_path = ResourceManager.resource_path("crossword_clues.db")
con = sqlite3.connect(db_path)
cur = con.cursor()

class WordCheckWindow(QDialog): # слишком много методов, поэтому окошко для воода и проверки слова отдельным классом
    def __init__(self, row_number, crossword_grid, grid_widget, words, parent=None):
        super().__init__(parent)
        self.row_number = row_number
        self.crossword_grid = crossword_grid
        self.grid_widget = grid_widget
        self.words = words
        self.correct_word = self.words[self.row_number]
        self.setWindowTitle(f"Слово №{self.row_number + 1}")
        self.setModal(True)
        self.resize(1000, 300)

        # настройка звуков на правильный/неправильный ответ
        # self.correct_sound = QSoundEffect()
        # self.correct_sound.setSource(QUrl.fromLocalFile("applause.wav"))

        correct_sound_path = ResourceManager.resource_path("applause.wav")
        self.correct_sound = QMediaPlayer()
        self.correct_sound.setMedia(QMediaContent(QUrl.fromLocalFile(correct_sound_path)))

        # self.wrong_sound = QSoundEffect()
        # self.wrong_sound.setSource(QUrl.fromLocalFile("error.wav"))

        wrong_sound_path = ResourceManager.resource_path("error.wav")
        self.wrong_sound = QMediaPlayer()
        self.wrong_sound.setMedia(QMediaContent(QUrl.fromLocalFile(wrong_sound_path)))
        
        word_check_layout = QVBoxLayout()
        
        # определение берется из базы знаний
        clue = self.get_clue()
        clue_label = QLabel(f"{clue}")
        clue_label.setAccessibleName(f"Определение слова: {clue}")
        clue_label.setAccessibleDescription("Введите слово, соответствующее описанию")
        clue_label.setAlignment(Qt.AlignCenter)
        clue_label.setWordWrap(True)
        
        self.user_input = QLineEdit() # будет меняться
        self.user_input.setPlaceholderText("Введите слово...")
        self.user_input.setAccessibleName("Поле ввода текста")
        self.user_input.setAccessibleDescription("Введите текст, затем нажмите Enter")
        self.user_input.setFocusPolicy(Qt.StrongFocus)
        
        check_button = QPushButton("Проверить")
        check_button.setAccessibleName('Кнопка "Проверить"')
        check_button.setAccessibleDescription("Нажмите на кнопку, чтобы проверить правильность введенного слова")
        check_button.setFocusPolicy(Qt.StrongFocus)
        check_button.clicked.connect(self.check_word)
        
        self.result_label = QLabel() # буднт меняться в зависимости от ответа
        self.result_label.setAlignment(Qt.AlignCenter)
        
        word_check_layout.addWidget(clue_label)
        word_check_layout.addWidget(self.user_input)
        word_check_layout.addWidget(check_button)
        word_check_layout.addWidget(self.result_label)
        
        self.setLayout(word_check_layout)

    def get_clue(self):
        cur.execute("SELECT clue_1 FROM lvl_1 WHERE word = ?", (self.correct_word,))
        clue = cur.fetchone()[0]
        return clue
    
    def check_word(self):
        user_word = self.user_input.text().strip().lower()

        if user_word == self.correct_word: # задать последовательность: текстовый отклик в окне, заполнение сетки на заднем плане, закрытие окна через 2 секунды
            self.result_label.setText("Правильно!")
            self.result_label.setStyleSheet("color: green; font-weight: bold;")
            self.result_label.setWordWrap(True)
            self.result_label.setAccessibleName("Правильно!")
            self.result_label.setAccessibleDescription("Вы правильно ответили на вопрос!")
            self.correct_sound.play()

            self.fill_crossword(self.row_number, user_word)

            self.timer = QTimer(self)
            self.timer.setSingleShot(True)
            self.timer.timeout.connect(self.accept)
            self.timer.start(2000)

        else: # то же самое, что при правильном ответе, но окошко не исчезает, давая возможность заполнить строку ввода повторно
            self.result_label.setText("Слово неверное! Попробуйте еще раз")
            self.result_label.setStyleSheet("color: red; font-weight: bold;")
            self.result_label.setWordWrap(True)
            self.result_label.setAccessibleName("Слово неверное!")
            self.result_label.setAccessibleDescription("Вы ввели неверное слово! Попробуйте еще раз")
            self.wrong_sound.play()

    def fill_crossword(self, row_num, word):
        word_chars = list(word.upper())
        char_index = 0
        column_count = self.grid_widget.columnCount()
        
        for col in range(column_count):
            # получаем виджет из сетки
            item = self.grid_widget.itemAtPosition(row_num, col)
            if item is not None:
                widget = item.widget()
                # Если это QLineEdit и есть еще буквы, то продолжать заполнять
                if isinstance(widget, QLineEdit) and char_index < len(word_chars):
                    widget.setText(word_chars[char_index])
                    widget.setStyleSheet("""
                        QLineEdit {
                            background-color: #ccffcc;
                            border: 1px solid #999;
                            font-weight: bold;
                        }
                    """)
                    widget.setAccessibleName(f"Cимвол {word_chars[char_index]}")
                    widget.setAccessibleDescription("Используйте стрелки влево-вправо и вверх-вниз для перехода на соседние клетки с символами")
                    char_index += 1

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        icon_path = ResourceManager.get_icon_path("crossword.ico")
        self.setWindowIcon(QtGui.QIcon(icon_path))
        self.setWindowTitle("CrossLex")
        self.setGeometry(100, 100, 400, 300)

        # настройки (инициализация тут, а не в странице)
        self.settings = QSettings("MyCompany", "CrossLex")
        self.app_font_size = QApplication.font()
        self.app_volume = 50
        self.media_players = []
        
        # стек виджетов для переключения между страницами, иначе в PyQt5 многостраничность не получалась
        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)
        
        # все страницы, кроме кроссворда, который сформируется на основе выбранного режима
        self.create_home_page()
        self.create_settings_page()
        self.create_end_game_page()

        self.load_settings()

        # кроссворд создастся динамически при выборе режима
        self.game_page_colors = None
        self.game_page_homonyms = None
        
        self.stacked_widget.setCurrentIndex(0) # главная страница в стеке, она же home_page

        self.showMaximized()
        
    def create_home_page(self):
        self.home_page = QWidget()
        home_layout = QVBoxLayout()

        home_title = QLabel("КроссЛекс")
        home_title.setAlignment(Qt.AlignCenter)
        home_title.setStyleSheet("font-size: 50px; font-weight: bold;") # по умолчанию весь текст 40px, заголовки с кастомизацией: 50px и полужирный
        home_layout.addWidget(home_title)
        
        welcome_text = """Добро пожаловать в КроссЛекс, приложение с доступными кроссвордами!

Прежде, чем приступить к игре, Вы можете отрегулировать уровень громкости или размер шрифта в настройках.
Удачи и приятной игры!"""
        welcome_label = QLabel(welcome_text)
        welcome_label.setStyleSheet("margin: 60px;")
        welcome_label.setWordWrap(True)
        welcome_label.setAccessibleName("Добро пожаловать! ")
        welcome_label.setAccessibleDescription("""Добро пожаловать в КроссЛекс, приложение с доступными кроссвордами!

Прежде, чем приступить к игре, Вы можете отрегулировать уровень громкости или размер шрифта в настройках.
Удачи и приятной игры!""")
        home_layout.addWidget(welcome_label, alignment=Qt.AlignmentFlag.AlignCenter)

        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        settings_button = QPushButton("Настройки")
        settings_button.setFixedHeight(200)
        settings_button.setAccessibleName('Кнопка "Настройки"')
        settings_button.setAccessibleDescription("Нажмите, чтобы перейти на страницу настроек")
        settings_button.setFocusPolicy(Qt.StrongFocus)
        settings_button.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(1))
        
        game_button = QPushButton("Играть")
        game_button.setFixedHeight(200)
        game_button.setAccessibleName('Кнопка "Играть"')
        game_button.setAccessibleDescription("Нажмите, чтобы выбрать режим игры")
        game_button.setFocusPolicy(Qt.StrongFocus)
        # game_button.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(2))
        game_button.clicked.connect(self.select_mode)
        
        exit_button = QPushButton("Выход")
        exit_button.setFixedHeight(200)
        exit_button.setAccessibleName('Кнопка "Выход"')
        exit_button.setAccessibleDescription("Нажмите, чтобы выйти из приложения")
        exit_button.setFocusPolicy(Qt.StrongFocus)
        exit_button.clicked.connect(self.close)
        
        button_layout.addWidget(settings_button)
        button_layout.addWidget(game_button)
        button_layout.addWidget(exit_button)
        home_layout.addLayout(button_layout)
        self.setLayout(home_layout)
        
        self.home_page.setLayout(home_layout)
        self.stacked_widget.addWidget(self.home_page)

    def create_settings_page(self):
        self.settings_page = QWidget()

        test_sound_path = ResourceManager.resource_path("beep.wav")
        self.test_player = QMediaPlayer()
        self.test_player.setMedia(QMediaContent(QUrl.fromLocalFile(test_sound_path)))

        settings_layout = QVBoxLayout()
        
        settings_title = QLabel("Страница настроек")
        settings_title.setStyleSheet("font-size: 50px; font-weight: bold;")
        settings_title.setAccessibleName("Страница настроек")
        settings_title.setAccessibleDescription("На данной странице вы можете отрегулировать громкость аудио и размер шрифта")
        settings_layout.addWidget(settings_title, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # ползунок громкости
        self.volume_label = QLabel("Громкость звука:")
        self.volume_label.setStyleSheet("margin: 70px;")
        self.volume_label.setAccessibleName("Громкость звука")
        self.volume_label.setAccessibleDescription("Громкость аудио в приложении")
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(self.app_volume)
        self.volume_slider.setAccessibleName("Слайдер громкости")
        self.volume_slider.setAccessibleDescription("Используйте стрелки влево-вправо для регулировки")
        self.volume_slider.setFocusPolicy(Qt.StrongFocus)
        self.volume_slider.valueChanged.connect(self.update_volume)

        volume_layout = QVBoxLayout()
        volume_layout.addWidget(self.volume_label)
        volume_layout.addWidget(self.volume_slider)

        # ползунок размера шрифта
        self.font_size_label = QLabel(f"Размер шрифта:")
        self.font_size_label.setStyleSheet("margin: 70px;")
        self.font_size_label.setAccessibleName(f"Размер шрифта")
        self.font_size_label.setAccessibleDescription("Размер шрифта в приложении")
        self.font_size_slider = QSlider(Qt.Horizontal)
        self.font_size_slider.setRange(8, 50)
        self.font_size_slider.setValue(self.app_font_size.pointSize())
        self.font_size_slider.setAccessibleName("Слайдер размера шрифта")
        self.font_size_slider.setAccessibleDescription("Используйте стрелки влево-вправо для регулировки")
        self.font_size_slider.setFocusPolicy(Qt.StrongFocus)
        self.font_size_slider.valueChanged.connect(self.update_font_size)

        font_size_layout = QVBoxLayout()
        font_size_layout.addWidget(self.font_size_label)
        font_size_layout.addWidget(self.font_size_slider)
        
        save_button = QPushButton("Сохранить и вернуться")
        save_button.setFixedHeight(200)
        save_button.setAccessibleName('Кнопка "Сохранить и вернуться"')
        save_button.setAccessibleDescription("Нажмите, чтобы сохранить настройки и перейти на главную страницу")
        save_button.setFocusPolicy(Qt.StrongFocus)
        save_button.clicked.connect(self.save_settings)

        settings_layout.addLayout(volume_layout)
        settings_layout.addLayout(font_size_layout)
        
        settings_layout.addWidget(save_button)

        self.settings_page.setLayout(settings_layout)
        self.stacked_widget.addWidget(self.settings_page)

    def update_volume(self, value):
        self.volume_label.setText(f"Громкость звука: {value}%")
        self.app_volume = value
        
        # обновление громкости для всех медиаплееров
        for player in self.media_players:
            player.setVolume(value)
        
        # для демонстрации тестовый звук
        self.test_player.setVolume(value)
        self.test_player.play()

    def update_font_size(self, value):
        self.font_size_label.setText(f"Размер шрифта: {value}px")
        
        # обновление шрифта во всем приложении
        new_font_size = QApplication.font()
        new_font_size.setPointSize(value)
        QApplication.setFont(new_font_size)
        self.app_font_size = new_font_size

    def load_settings(self): # тут значения по умолчанию
        volume = self.settings.value("volume", 50, type=int)
        self.volume_slider.setValue(volume)
        self.update_volume(volume)
        
        font_size = self.settings.value("font_size", 20, type=int)
        self.font_size_slider.setValue(font_size)
        self.update_font_size(font_size)

    def save_settings(self):
        self.settings.setValue("volume", self.volume_slider.value())
        self.settings.setValue("font_size", self.font_size_slider.value())
        self.stacked_widget.setCurrentIndex(0)

    def select_mode(self):
        dialog = QMessageBox()
        dialog.setWindowTitle("Выбор режима")
        dialog.setText("Выберите режим игры")
        dialog.resize(1000, 300)
        
        colors_button = dialog.addButton("Цвета\n(русский\nязык)", QMessageBox.AcceptRole)
        colors_button.setAccessibleName('Кнопка "Цвета (русский язык)"')
        colors_button.setAccessibleDescription("Нажмите, чтобы перейти к кроссворду с цветами")
        colors_button.setFocusPolicy(Qt.StrongFocus)
        colors_button.setFixedSize(250, 200)

        homonyms_button = dialog.addButton("Омонимы\n(английский\nязык)", QMessageBox.AcceptRole)
        homonyms_button.setAccessibleName('Кнопка "Омонимы (английский язык)"')
        homonyms_button.setAccessibleDescription("Нажмите, чтобы перейти к кроссворду с омонимами")
        homonyms_button.setFocusPolicy(Qt.StrongFocus)
        homonyms_button.setFixedSize(250, 200)
        
        dialog.exec_()
        
        if dialog.clickedButton() == colors_button:
            self.start_game(ResourceManager.resource_path("Buran_benchmark.csv"))
        elif dialog.clickedButton() == homonyms_button:
            self.start_game(ResourceManager.resource_path("Light_benchmark.csv"))
    
    def start_game(self, crossword_file):
        # удаляем старые страницы игры если они есть, пока что не будем реализовывать сохранение игр
        if self.game_page_colors and self.game_page_colors in [self.stacked_widget.widget(i) for i in range(self.stacked_widget.count())]:
            self.stacked_widget.removeWidget(self.game_page_colors)
        if self.game_page_homonyms and self.game_page_homonyms in [self.stacked_widget.widget(i) for i in range(self.stacked_widget.count())]:
            self.stacked_widget.removeWidget(self.game_page_homonyms)
        
        # новая страница на базе выбранного режима
        game_page = self.create_crossword_page(crossword_file)
        
        # созданную страницу в стек
        self.stacked_widget.addWidget(game_page)
        self.stacked_widget.setCurrentWidget(game_page)
    
    def create_crossword_page(self, crossword_file):
        game_page = QWidget()
        crossword_layout = QVBoxLayout()
        game_layout = QHBoxLayout()
        game_layout.setSpacing(15)

        crossword_title = QLabel("КроссЛекс")
        crossword_title.setAlignment(Qt.AlignCenter)
        crossword_title.setStyleSheet("font-size: 50px; font-weight: bold; margin: 20px;")
        crossword_layout.addWidget(crossword_title)

        clues_layout = QVBoxLayout()
        for i in range(0, 5): # вместо 6 максимумом назначить кол-во строк в csv-файле
            clue_button = QPushButton(f"{str(i + 1)}")
            clue_button.setAccessibleName(f'Слово №{str(i + 1)}')
            clue_button.setAccessibleDescription(f"Нажмите, чтобы ввести слово №{str(i + 1)}")
            clue_button.setFocusPolicy(Qt.StrongFocus)
            clue_button.setFixedSize(120, 120)
            clue_button.setStyleSheet("font-weight: bold;")
            clue_button.clicked.connect(lambda _, num=i: self.show_word_check(num))
            clues_layout.addWidget(clue_button)

        game_layout.addLayout(clues_layout)

        self.grid = QGridLayout()
        self.grid.setSpacing(0)          # без промежутков между ячейками
        self.grid.setContentsMargins(0, 0, 0, 0)  # без отступов вокруг всего лейаута

        with open(crossword_file, "r", encoding="utf-8") as file:
            reader = csv.reader(file)
            self.crossword_grid = [list(row) for row in reader] # список со списками букв и пустых строк
            self.words = ["".join([cell for cell in row if cell != ""]) for row in self.crossword_grid] # список со строками-словами

        # создание клеток кроссворда
        for row_idx, row in enumerate(self.crossword_grid):
            for col_idx, cell in enumerate(row):
                if cell.strip() == "":  # на месте пустой строки пустая клетка (черная)
                    empty_cell = QLabel()
                    empty_cell.setStyleSheet("background-color: black; padding: 0px; margin: 0px;")
                    empty_cell.setFixedHeight(145)
                    empty_cell.setAccessibleName("Пустая клетка")
                    empty_cell.setAccessibleDescription("В данной клетке кроссворда не содержатся никакие символы")
                    self.grid.addWidget(empty_cell, row_idx, col_idx)
                else:  # на месте строки с буквой клетка для ввода буквы (белая)
                    input_cell = QLineEdit()
                    input_cell.setReadOnly(True)
                    input_cell.setAlignment(Qt.AlignCenter)
                    input_cell.setMaxLength(1)  # можно ввести только 1 символ
                    input_cell.setStyleSheet("""
                        QLineEdit {
                            background-color: white;
                            border: 1px solid gray;
                            padding: 0px;
                            margin: 0px;
                        }
                    """)
                    input_cell.setFixedHeight(145)
                    input_cell.setFocusPolicy(Qt.StrongFocus)
                    self.grid.addWidget(input_cell, row_idx, col_idx)
        game_layout.addLayout(self.grid)

        crossword_layout.addLayout(game_layout)

        button_layout = QHBoxLayout()
        
        back_button = QPushButton("Назад")
        back_button.setFixedHeight(200)
        back_button.setAccessibleName('Кнопка "Назад"')
        back_button.setAccessibleDescription("Нажмите, чтобы вернуться на главную страницу")
        back_button.setFocusPolicy(Qt.StrongFocus)
        back_button.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(0))
        
        finish_button = QPushButton("Завершить игру")
        finish_button.setFixedHeight(200)
        finish_button.setAccessibleName('Кнопка "Завершить игру"')
        finish_button.setAccessibleDescription("Нажмите, чтобы завершить текущую игру")
        finish_button.setFocusPolicy(Qt.StrongFocus)
        finish_button.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(2))
        
        crossword_layout.addStretch()
        button_layout.addWidget(back_button)
        button_layout.addWidget(finish_button)

        crossword_layout.addLayout(button_layout)
        
        game_page.setLayout(crossword_layout)
        self.stacked_widget.addWidget(game_page)
        return game_page
    
    def show_word_check(self, row_number): # ввод пользователем и проверка в отдельном окошке
        dialog = WordCheckWindow(
            row_number=row_number,
            crossword_grid=self.crossword_grid,
            grid_widget=self.grid,
            words=self.words,
            parent=self
        )
        dialog.exec_()
    
    def create_end_game_page(self):
        self.end_game_page = QWidget()
        end_game_layout = QVBoxLayout()
        
        end_game_title = QLabel("Игра завершена")
        end_game_title.setStyleSheet("font-size: 50px; font-weight: bold;") # margin: 20px;
        end_game_title.setAccessibleName("Конец игры")
        end_game_title.setAccessibleDescription("Игра завершена")
        end_game_layout.addWidget(end_game_title, alignment=Qt.AlignmentFlag.AlignCenter)

        end_game_label = QLabel("Вы завершили игру.\nСпасибо за то, что приняли участие в тестировании нашего приложения!")
        end_game_label.setAccessibleName("Спасибо за игру!")
        end_game_label.setAccessibleDescription("Вы завершили игру. Спасибо за то, что приняли участие в тестировании нашего приложения!")
        # end_game_label.setStyleSheet("margin: 10px;")
        end_game_label.setWordWrap(True)
        end_game_layout.addWidget(end_game_label, alignment=Qt.AlignmentFlag.AlignCenter)
        
        home_button = QPushButton("На главную")
        home_button.setFixedHeight(200)
        home_button.setAccessibleName('Кнопка "На главную"')
        home_button.setAccessibleDescription("Нажмите, чтобы перейти на главную страницу")
        home_button.setFocusPolicy(Qt.StrongFocus)
        home_button.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(0))
        
        end_game_layout.addWidget(home_button)
        
        self.end_game_page.setLayout(end_game_layout)
        self.stacked_widget.addWidget(self.end_game_page)

if __name__ == "__main__":
    if getattr(sys, 'frozen', False):
        import os
        os.environ['PATH'] = sys._MEIPASS + os.pathsep + os.environ['PATH']

    app = QApplication(sys.argv)
    app.setStyleSheet("""
        QPushButton { font-size: 40px; }
        QLabel { font-size: 40px; }
        QLineEdit { font-size: 40px; }
        """)
    window = MainWindow()
    # в итоге не было деплоя для iOS, но пусть код будет
    # if QOperatingSystemVersion.current() == QOperatingSystemVersion.Android:
    # window.setFixedSize(QSize(360, 640))
    # elif QOperatingSystemVersion.current() == QOperatingSystemVersion.IOS:
    # window.setFixedSize(375, 667)
    window.show()
    sys.exit(app.exec_())

# далее создаем установочные файлы
# сначала сохраняем требования: pip freeze > requirements.txt

# структура проекта:
# 
# CrossLex/
# ├── src/
# │   ├── main.py          # Основной код
# │   ├── data/
# │   │   ├── Buran_benchmark.csv     # CSV-файлы
# │   │   ├── Light_benchmark.csv
# │   │   ├── applause.wav    # Аудио
# │   │   ├── beep.wav
# │   │   ├── error.wav
# │   │   └── crossword_clues.db  # База данных
# │   └── assets/
# │       └── crossword.ico     # Иконка приложения
# └── requirements.txt     # Зависимости

# команда для PyInstaller: pyinstaller --onefile --windowed --add-data "src/assets/crossword.ico;assets" --icon=src/assets/crossword.ico --add-data "src/data/*.csv;data" --add-data "src/data/*.wav;data" --add-data "src/data/*.db;data" src/main.py
