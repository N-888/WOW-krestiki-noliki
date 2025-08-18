# -*- coding: utf-8 -*-
# Игра "Крестики-нолики" с графическим интерфейсом
# Разработано N-888 (2023)
# Особенности: несколько уровней сложности, смена тем оформления, сохранение статистики

# Импортируем необходимые модули
from typing import Any, Dict, List, Optional, Set, Tuple  # Для указания типов данных
import json  # Для работы с JSON-файлами (чтение/запись)
import os  # Для работы с файловой системой (проверка файлов)
import threading  # Для много поточности (для звуковых эффектов)
from datetime import datetime, timedelta  # Для работы с датой и временем
import importlib  # Для динамической загрузки модулей (pygame)
import random  # Для генерации случайных чисел (ходы ИИ)

import tkinter as tk  # Основная библиотека для создания графического интерфейса
from tkinter import messagebox, simpledialog  # Готовые диалоговые окна

# Константы для файлов сохранения
HISTORY_FILE: str = "tic_tac_toe_history.json"  # Файл для сохранения истории игр
SCORE_FILE: str = "tic_tac_toe_score.json"  # Файл для сохранения статистики игроков

# Ограничения для хранения данных
MAX_DAYS: int = 90  # Максимальный возраст записей в днях (3 месяца)
MAX_GAMES: int = 100  # Максимальное количество хранимых игр в истории

# Цветовые темы интерфейса
THEMES: Dict[str, Dict[str, str]] = {
    "light": {
        "bg": "#f0f0f0",  # Цвет фона окна
        "btn_bg": "#ffffff",  # Цвет фона кнопок
        "btn_fg": "#000000",  # Цвет текста кнопок
        "highlight": "#90ee90",  # Цвет победной линии
        "text_highlight": "#006400",  # Цвет текста на победной линии
        "title": "Светлая",  # Название темы для меню
    },
    "dark": {
        "bg": "#2e2e2e",  # Темный фон
        "btn_bg": "#444444",  # Темные кнопки
        "btn_fg": "#ffffff",  # Белый текст
        "highlight": "#32cd32",  # Зеленая подсветка
        "text_highlight": "#98fb98",  # Светло-зеленый текст
        "title": "Тёмная",  # Название темы
    },
    "neon_night": {
        "bg": "#000000",  # Черный фон
        "btn_bg": "#111111",  # Очень темные кнопки
        "btn_fg": "#00ff88",  # Неоново-зеленый текст
        "highlight": "#00ffcc",  # Бирюзовая подсветка
        "text_highlight": "#00ffff",  # Голубой текст
        "border": "#00ff88",  # Цвет границ кнопок
        "glow": "#00ff88",  # Цвет свечения уведомлений
        "title": "Ночной неон",  # Название темы
    },
    "neon_day": {
        "bg": "#e0ffe0",  # Светло-зеленый фон
        "btn_bg": "#ffffff",  # Белые кнопки
        "btn_fg": "#ff0066",  # Розовый текст
        "highlight": "#ff66cc",  # Розовая подсветка
        "text_highlight": "#ff00aa",  # Ярко-розовый текст
        "border": "#ff0066",  # Розовые границы
        "glow": "#ff0066",  # Розовое свечение
        "title": "Дневной неон",  # Название темы
    },
    "cosmos": {
        "bg": "#0a0020",  # Темно-синий фон (космос)
        "btn_bg": "#1a0a3a",  # Фиолетовые кнопки
        "btn_fg": "#00aaff",  # Голубой текст
        "highlight": "#00ffff",  # Бирюзовая подсветка
        "text_highlight": "#ff9900",  # Оранжевый текст
        "border": "#5500ff",  # Фиолетовые границы
        "glow": "#0077ff",  # Синее свечение
        "title": "Космос",  # Название темы
    },
}

# Пороговые значения для уведомлений о рекордах
RECORDS: List[int] = [3, 5, 10, 15, 20, 25, 30]  # Количество побед для показа уведомлений

# Пытаемся загрузить pygame для звуковых эффектов
try:
    # Динамически импортируем pygame (если установлен)
    PYGAME: Any = importlib.import_module("pygame")
    # Инициализируем звуковую систему
    PYGAME.mixer.init()
    # Флаг, что звук доступен
    AUDIO_OK: bool = True
except Exception as _audio_exc:
    # Если pygame недоступен, продолжаем без звука
    print(f"[WARN] pygame недоступен или ошибка аудио: {_audio_exc}")
    PYGAME = None
    AUDIO_OK = False


class TicTacToeApp:
    """Основной класс приложения для игры в крестики-нолики."""

    def __init__(self, window: tk.Tk) -> None:
        """Инициализация игрового приложения."""
        # Сохраняем ссылку на главное окно
        self.window: tk.Tk = window
        # Устанавливаем заголовок окна
        self.window.title("Крестики-нолики | N-888")
        # Устанавливаем размер окна (ширина x высота)
        self.window.geometry("350x600")
        # Запрещаем изменение размера окна
        self.window.resizable(False, False)

        # Создаем главный фрейм для всего контента
        self.main_frame = tk.Frame(self.window)
        # Размещаем фрейм с отступами 10 пикселей со всех сторон
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # --- Инициализация игрового состояния ---
        # Текущий игрок (X или O)
        self.current_player: str = "X"
        # Флаг завершения игры
        self.game_over: bool = False
        # Массив кнопок игрового поля (3x3)
        self.buttons: List[List[tk.Button]] = []
        # Координаты выигрышной линии (если есть)
        self.win_line: List[Tuple[int, int]] = []
        # Режим игры: против ИИ (True) или два игрока (False)
        self.vs_ai: bool = False
        # Уровень сложности ИИ (easy, normal, hard)
        self.ai_difficulty: str = "normal"
        # Окно для уведомлений о рекордах
        self.record_notification: Optional[tk.Toplevel] = None

        # --- Статистика и настройки ---
        # Имена игроков (для X и O)
        self.player_names: Dict[str, str] = {"X": "Игрок X", "O": "Игрок O"}
        # Количество побед каждого игрока
        self.win_count: Dict[str, int] = {"X": 0, "O": 0}
        # Уже показанные рекорды (чтобы не показывать повторно)
        self.shown_records: Dict[str, Set[int]] = {"X": set(), "O": set()}
        # Текущая цветовая тема
        self.current_theme: str = "light"

        # --- Элементы интерфейса (инициализируются позже) ---
        self.score_label: Optional[tk.Label] = None
        self.reset_button: Optional[tk.Button] = None
        self.mode_button: Optional[tk.Button] = None
        self.difficulty_button: Optional[tk.Button] = None
        self.theme_button: Optional[tk.Button] = None
        self.history_button: Optional[tk.Button] = None
        self.names_button: Optional[tk.Button] = None

        # Создаем верхнее меню
        self.create_menu()
        # Загружаем сохраненную статистику
        self.load_score()
        # Создаем элементы интерфейса
        self.create_widgets()

    def create_menu(self) -> None:
        """Создает верхнее меню приложения."""
        # Создаем панель меню
        menu_bar = tk.Menu(self.window)

        # Создаем меню "Игра"
        game_menu = tk.Menu(menu_bar, tearoff=0)
        # Добавляем пункты в меню "Игра"
        game_menu.add_command(label="Новая игра", command=self.reset_game)
        game_menu.add_command(label="Выбрать имена игроков", command=self.set_player_names)
        game_menu.add_command(label="История игр", command=self.show_history)
        game_menu.add_separator()  # Разделительная линия

        # Создаем подпункт меню "Тема"
        theme_menu = tk.Menu(game_menu, tearoff=0)
        # Добавляем все темы в подменю
        for key, theme in THEMES.items():
            theme_menu.add_command(
                label=theme["title"],
                command=lambda k=key: self.set_theme(k)
            )
        # Добавляем подменю "Тема" в меню "Игра"
        game_menu.add_cascade(label="Выбрать тему", menu=theme_menu)
        game_menu.add_separator()
        # Пункт "Выход"
        game_menu.add_command(label="Выход", command=self.window.quit)

        # Добавляем меню "Игра" в панель меню
        menu_bar.add_cascade(label="Игра", menu=game_menu)

        # Создаем меню "Справка"
        help_menu = tk.Menu(menu_bar, tearoff=0)
        help_menu.add_command(label="О программе", command=self.show_about)
        # Добавляем меню "Справка" в панель меню
        menu_bar.add_cascade(label="Справка", menu=help_menu)

        # Устанавливаем созданное меню в главное окно
        self.window.config(menu=menu_bar)

    def create_widgets(self) -> None:
        """Создает все элементы интерфейса внутри главного фрейма."""
        # --- Создаем игровое поле 3x3 ---
        # Фрейм для игрового поля с выравниванием по центру
        game_frame = tk.Frame(self.main_frame)
        game_frame.pack(pady=(10, 20))

        # Создаем кнопки для каждой клетки поля
        for row in range(3):
            button_row = []
            for col in range(3):
                # Создаем кнопку с пустым текстом
                btn = tk.Button(
                    game_frame,
                    text="",
                    font=("Arial", 28, "bold"),  # Крупный жирный шрифт
                    width=3,  # Ширина в символах
                    height=1,  # Высота в линиях текста
                    # Обработчик клика по кнопке
                    command=lambda r=row, c=col: self.on_click(r, c)
                )
                # Размещаем кнопку в сетке с небольшими отступами
                btn.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")
                button_row.append(btn)
            self.buttons.append(button_row)

        # Настраиваем пропорции столбцов игрового поля
        for i in range(3):
            game_frame.grid_columnconfigure(i, weight=1, uniform="columns")
            game_frame.grid_rowconfigure(i, weight=1, uniform="rows")

        # --- Панель счета ---
        # Создание фрейма для панели счета с выравниванием по центру
        score_frame = tk.Frame(self.main_frame)
        score_frame.pack(fill=tk.X, pady=(0, 10))

        # Метка для отображения счета
        self.score_label = tk.Label(
            score_frame,
            text="",  # Текст будет установлен позже
            font=("Arial", 12)  # Шрифт среднего размера
        )
        # Размещаем метку по центру
        self.score_label.pack(expand=True)

        # --- Кнопки управления ---
        # Фрейм для кнопок управления с выравниванием по центру
        control_frame = tk.Frame(self.main_frame)
        control_frame.pack(fill=tk.X, pady=5)

        # Кнопка "Новая игра"
        self.reset_button = tk.Button(
            control_frame,
            text="🔄 Новая игра",
            font=("Arial", 10),
            bg="#add8e6",  # Светло-голубой фон
            command=self.reset_game
        )
        self.reset_button.pack(fill=tk.X, pady=3)

        # Кнопка переключения режима игры
        self.mode_button = tk.Button(
            control_frame,
            text="🎮 Режим: 2 игрока",
            font=("Arial", 10),
            bg="#90ee90",  # Светло-зеленый фон
            command=self.toggle_game_mode
        )
        self.mode_button.pack(fill=tk.X, pady=3)

        # Кнопка выбора сложности ИИ
        self.difficulty_button = tk.Button(
            control_frame,
            text="📊 Сложность: Normal",
            font=("Arial", 10),
            bg="#f08080",  # Светло-красный фон
            command=self.set_ai_difficulty
        )
        self.difficulty_button.pack(fill=tk.X, pady=3)

        # Кнопка выбора темы оформления
        self.theme_button = tk.Button(
            control_frame,
            text=f"🎨 Тема: {THEMES[self.current_theme]['title']}",
            font=("Arial", 10),
            bg="#dda0dd",  # Светло-фиолетовый фон
            command=self.show_theme_menu
        )
        self.theme_button.pack(fill=tk.X, pady=3)

        # Кнопка просмотра истории игр
        self.history_button = tk.Button(
            control_frame,
            text="📜 История игр",
            font=("Arial", 10),
            bg="#ffcc80",  # Оранжевый фон
            command=self.show_history
        )
        self.history_button.pack(fill=tk.X, pady=3)

        # Кнопка для изменения имен игроков
        self.names_button = tk.Button(
            control_frame,
            text="👤 Имена игроков",
            font=("Arial", 10),
            bg="#80deea",  # Голубой фон
            command=self.set_player_names
        )
        self.names_button.pack(fill=tk.X, pady=3)

        # Применяем текущую тему к интерфейсу
        self.apply_theme()
        # Обновляем метку счета
        self.update_score_label()

    @staticmethod
    def show_about() -> None:
        """Показывает окно 'О программе'."""
        messagebox.showinfo(
            "О программе",
            "Крестики-нолики\n\n"
            "Версия 3.0\n"
            "Разработчик: N-888\n\n"
            "Особенности:\n"
            "- Несколько уровней сложности ИИ\n"
            "- Подробная статистика игр\n"
            "- История последних партий\n"
            "- Смена цветовых тем\n"
            "- Звуковые эффекты\n"
            "- Современный симметричный интерфейс"
        )

    def show_theme_menu(self, event: Optional[tk.Event] = None) -> None:
        """Показывает контекстное меню для выбора темы оформления.

        Args:
            event: Необязательный объект события, если вызов был по клику мыши
        """
        # Создаем всплывающее меню
        menu = tk.Menu(self.window, tearoff=0)

        # Добавляем пункты для каждой темы
        for key, theme in THEMES.items():
            menu.add_command(
                label=theme["title"],  # Название темы
                command=lambda k=key: self.set_theme(k)  # Обработчик выбора
            )

        # Получаем координаты кнопки выбора темы
        x_pos = self.theme_button.winfo_rootx()
        y_pos = self.theme_button.winfo_rooty() + self.theme_button.winfo_height()

        # Показываем меню под кнопкой
        menu.post(x_pos, y_pos)

    def load_score(self) -> None:
        """Загружает статистику игроков из файла, если он существует."""
        # Проверяем существование файла
        if not os.path.exists(SCORE_FILE):
            return  # Файла нет, ничего не загружаем

        try:
            # Открываем файл для чтения
            with open(SCORE_FILE, "r", encoding="utf-8") as f:
                # Загружаем данные из JSON
                data: Dict[str, Any] = json.load(f)

            # Проверяем наличие даты последней игры
            last_played_str = data.get("last_played", "")
            if not last_played_str:
                return  # Нет даты, пропускаем

            # Преобразуем строку в объект даты
            last_played = datetime.strptime(last_played_str, "%Y-%m-%d %H:%M:%S")

            # Проверяем, не устарели ли данные (больше MAX_DAYS дней)
            if datetime.now() - last_played > timedelta(days=MAX_DAYS):
                return  # Данные устарели, не загружаем

            # Обновляем счет побед
            wins = data.get("wins", {})
            self.win_count["X"] = int(wins.get("X", 0))
            self.win_count["O"] = int(wins.get("O", 0))

            # Обновляем имена игроков
            names = data.get("names", {})
            self.player_names["X"] = str(names.get("X", "Игрок X"))
            self.player_names["O"] = str(names.get("O", "Игрок O"))

            # Обновляем информацию о показанных рекордах
            shown = data.get("shown_records", {"X": [], "O": []})
            self.shown_records["X"] = set(shown.get("X", []))
            self.shown_records["O"] = set(shown.get("O", []))

        except (json.JSONDecodeError, OSError, ValueError) as exc:
            # Обрабатываем возможные ошибки
            print(f"Ошибка загрузки счета: {exc}")

    def save_score(self) -> None:
        """Сохраняет текущую статистику игроков в файл."""
        # Формируем данные для сохранения
        data = {
            "wins": self.win_count.copy(),  # Копируем счет
            "names": self.player_names.copy(),  # Копируем имена
            "last_played": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),  # Текущая дата
            "shown_records": {  # Конвертируем множества в списки
                "X": list(self.shown_records["X"]),
                "O": list(self.shown_records["O"])
            },
        }

        try:
            # Открываем файл для записи
            with open(SCORE_FILE, "w", encoding="utf-8") as f:
                # Записываем данные в JSON с форматированием
                json.dump(data, f, ensure_ascii=False, indent=4)
        except OSError as exc:
            # Обрабатываем ошибки записи
            print(f"Ошибка сохранения счета: {exc}")

    def update_score_label(self) -> None:
        """Обновляет текст метки с текущим счетом игроков."""
        if self.score_label:
            # Форматируем текст с именами и счетом
            text = f"{self.player_names['X']}: {self.win_count['X']} — {self.player_names['O']}: {self.win_count['O']}"
            # Устанавливаем новый текст
            self.score_label.config(text=text)

    def set_player_names(self) -> None:
        """Открывает диалоговые окна для ввода имен игроков."""
        # Запрашиваем имя для игрока X
        x_name = simpledialog.askstring(
            "Имя игрока X",  # Заголовок окна
            "Введите имя для игрока X:",  # Подсказка
            initialvalue=self.player_names["X"]  # Текущее значение
        )

        # Запрашиваем имя для игрока O
        o_name = simpledialog.askstring(
            "Имя игрока O",
            "Введите имя для игрока O:",
            initialvalue=self.player_names["O"]
        )

        # Обновляем имена, если введены непустые значения
        if x_name:
            self.player_names["X"] = x_name
        if o_name:
            self.player_names["O"] = o_name

        # Обновляем отображение счета
        self.update_score_label()
        # Сохраняем изменения
        self.save_score()

    @staticmethod
    def load_history() -> List[Dict[str, str]]:
        """Загружает историю игр из файла.

        Returns:
            Список словарей с историей игр в формате [{"date": строка, "result": строка}]
        """
        # Проверяем существование файла
        if not os.path.exists(HISTORY_FILE):
            return []  # Файла нет, возвращаем пустой список

        try:
            # Открываем файл для чтения
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                # Загружаем данные из JSON
                data = json.load(f)

            # Проверяем, что данные в правильном формате (список)
            if not isinstance(data, list):
                return []  # Неверный формат, возвращаем пустой список

            # Нормализуем данные (убеждаемся, что все строки)
            normalized: List[Dict[str, str]] = []
            for item in data:
                if isinstance(item, dict):
                    normalized.append({
                        "date": str(item.get("date", "")),
                        "result": str(item.get("result", ""))
                    })
            return normalized

        except (json.JSONDecodeError, OSError) as exc:
            # Обрабатываем ошибки чтения
            print(f"Ошибка загрузки истории: {exc}")
            return []

    def save_game_result(self, result: str) -> None:
        """Сохраняет результат текущей игры в историю.

        Args:
            result: Строка с результатом игры (например, "Победа: Игрок X")
        """
        # Загружаем текущую историю игр
        history = self.load_history()
        # Добавляем новую запись с текущей датой и результатом
        history.append({
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "result": result
        })

        # Рассчитываем пороговую дату (текущая дата минус MAX_DAYS)
        cutoff_date = datetime.now() - timedelta(days=MAX_DAYS)
        # Фильтруем записи, оставляя только свежие
        filtered = [
            game for game in history
            if datetime.strptime(game["date"], "%Y-%m-%d %H:%M:%S") >= cutoff_date
        ]

        # Ограничиваем количество записей до MAX_GAMES
        filtered = filtered[-MAX_GAMES:]

        try:
            # Сохраняем обновленную историю в файл
            with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump(filtered, f, ensure_ascii=False, indent=4)
        except OSError as exc:
            # Обрабатываем ошибки записи
            print(f"Ошибка сохранения истории: {exc}")

    def show_history(self) -> None:
        """Показывает окно с историей последних игр."""
        # Загружаем историю игр
        history = self.load_history()
        # Если история пуста, показываем сообщение
        if not history:
            messagebox.showinfo("История игр", "История игр пуста.")
            return

        # Создаем новое окно для отображения истории
        hist_window = tk.Toplevel(self.window)
        hist_window.title("История игр")  # Заголовок окна
        hist_window.geometry("500x400")  # Размер окна
        hist_window.transient(self.window)  # Делаем окно зависимым
        hist_window.grab_set()  # Блокируем главное окно

        # Создаем заголовок
        tk.Label(
            hist_window,
            text="Последние игры",  # Текст заголовка
            font=("Arial", 14, "bold")  # Жирный шрифт
        ).pack(pady=10)  # Размещаем с отступом

        # Создаем область с прокруткой
        canvas = tk.Canvas(hist_window)  # Холст для прокрутки
        scrollbar = tk.Scrollbar(hist_window, orient="vertical", command=canvas.yview)  # Вертикальный скроллбар
        scroll_frame = tk.Frame(canvas)  # Фрейм для контента

        # Настраиваем прокрутку
        scroll_frame.bind(
            "<Configure>",  # При изменении размера фрейма
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))  # Обновляем область прокрутки
        )
        # Создаем окно на холсте для нашего фрейма
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        # Связываем прокручивание и холст
        canvas.configure(yscrollcommand=scrollbar.set)

        # Добавляем записи об играх
        for idx, game in enumerate(reversed(history), 1):
            # Создаем метку для каждой игры
            tk.Label(
                scroll_frame,
                text=f"{idx}. {game['date']} — {game['result']}",  # Форматируем текст
                font=("Arial", 10),  # Обычный шрифт
                anchor="w",  # Выравнивание по левому краю
                justify="left"  # Выравнивание текста
            ).pack(fill="x", pady=2)  # Размещаем с заполнением по ширине

        # Размещаем элементы в окне
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    @staticmethod
    def destroy_notification_safely(widget: Optional[tk.Toplevel]) -> None:
        """Безопасно закрывает окно уведомления, если оно существует.

        Args:
            widget: Окно уведомления, которое нужно закрыть
        """
        if widget is None:
            return  # Окна нет, ничего не делаем

        try:
            # Проверяем, существует ли окно
            if widget.winfo_exists():
                # Закрываем окно
                widget.destroy()
        except tk.TclError:
            # Игнорируем ошибки (если окно уже закрыто)
            pass

    def show_record_notification(self, player_key: str) -> None:
        """Показывает уведомление о достижении рекорда.

        Args:
            player_key: Ключ игрока ('X' или 'O'), достигшего рекорда
        """
        # Закрываем предыдущее уведомление (если было)
        self.destroy_notification_safely(self.record_notification)

        # Создаем новое окно уведомления
        self.record_notification = tk.Toplevel(self.window)
        self.record_notification.overrideredirect(True)  # Убираем рамки
        self.record_notification.geometry("300x80+100+50")  # Размер и позиция
        self.record_notification.attributes("-topmost", True)  # Поверх всех окон

        # Получаем параметры текущей темы
        theme = THEMES[self.current_theme]
        # Цвет фона (используем glow, если есть, иначе highlight)
        bg_color = theme.get("glow", theme["highlight"])
        self.record_notification.config(bg=bg_color)  # Устанавливаем фон

        # Подготовка сообщения
        name = self.player_names[player_key]  # Имя игрока
        count = self.win_count[player_key]  # Количество побед

        # Список возможных сообщений
        messages = [
            f"🚀 Вау, {name}! Это уже {count}-я победа!",
            f"🎉 Поздравляем, {name}! Рекорд достигнут!",
            f"🏆 {name}, ты становишься легендой! {count} побед!",
            f"💫 Блестяще, {name}! {count} раз ты выиграл!",
        ]
        # Выбираем случайное сообщение
        msg = random.choice(messages)

        # Создаем текстовую метку
        label = tk.Label(
            self.record_notification,
            text=msg,  # Текст сообщения
            font=("Arial", 10, "bold"),  # Жирный шрифт
            bg=bg_color,  # Цвет фона
            fg="white",  # Белый текст
            wraplength=280,  # Максимальная ширина текста
            justify="center"  # Выравнивание по центру
        )
        # Размещаем метку
        label.pack(expand=True)

        # Закрываем уведомление через 3 секунды
        self.window.after(3000, lambda: self.destroy_notification_safely(self.record_notification))

    @staticmethod
    def play_victory_sound() -> None:
        """Воспроизводит звук победы, если доступен."""
        # Проверяем, доступен ли звук
        if not AUDIO_OK or PYGAME is None:
            return

        def _play() -> None:
            """Внутренняя функция для воспроизведения звука в отдельном потоке."""
            try:
                # Загружаем звуковой файл
                PYGAME.mixer.music.load("victory.mp3")
                # Воспроизводим звук
                PYGAME.mixer.music.play()
            except Exception as exc:
                # Обрабатываем ошибки воспроизведения
                print(f"Ошибка звука: {exc}")

        # Запускаем звук в отдельном потоке
        threading.Thread(target=_play, daemon=True).start()

    def check_winner_with_line(self) -> Optional[str]:
        """Проверяет, есть ли победитель, и запоминает выигрышную линию.

        Returns:
            Символ победителя ('X' или 'O') или None, если победителя нет
        """
        # Сбрасываем предыдущую выигрышную линию
        self.win_line = []

        # Проверяем строки
        for row in range(3):
            if (self.buttons[row][0]["text"] ==
                    self.buttons[row][1]["text"] ==
                    self.buttons[row][2]["text"] != ""):
                # Запоминаем выигрышную линию
                self.win_line = [(row, 0), (row, 1), (row, 2)]
                # Возвращаем символ победителя
                return self.buttons[row][0]["text"]

        # Проверяем столбцы
        for col in range(3):
            if (self.buttons[0][col]["text"] ==
                    self.buttons[1][col]["text"] ==
                    self.buttons[2][col]["text"] != ""):
                self.win_line = [(0, col), (1, col), (2, col)]
                return self.buttons[0][col]["text"]

        # Проверяем диагонали
        # Главная диагональ (слева направо вниз)
        if (self.buttons[0][0]["text"] ==
                self.buttons[1][1]["text"] ==
                self.buttons[2][2]["text"] != ""):
            self.win_line = [(0, 0), (1, 1), (2, 2)]
            return self.buttons[0][0]["text"]

        # Побочная диагональ (справа налево вниз)
        if (self.buttons[0][2]["text"] ==
                self.buttons[1][1]["text"] ==
                self.buttons[2][0]["text"] != ""):
            self.win_line = [(0, 2), (1, 1), (2, 0)]
            return self.buttons[0][2]["text"]

        # Победителя нет
        return None

    def check_draw(self) -> bool:
        """Проверяет, закончилась ли игра вничью (все клетки заполнены).

        Returns:
            True, если все клетки заполнены и нет победителя, иначе False
        """
        # Проходим по всем клеткам поля
        for row in self.buttons:
            for btn in row:
                # Если найдена пустая клетка - ничьи еще нет
                if btn["text"] == "":
                    return False
        # Все клетки заполнены - ничья
        return True

    def highlight_win_line(self) -> None:
        """Подсвечивает выигрышную линию на поле."""
        # Получаем параметры текущей темы
        theme = THEMES[self.current_theme]
        # Цвет подсветки
        color = theme.get("highlight", "#90ee90")
        # Цвет текста на подсвеченных клетках
        text_color = theme.get("text_highlight", "green")

        # Проходим по всем клеткам выигрышной линии
        for i, j in self.win_line:
            # Изменяем стиль кнопки
            self.buttons[i][j].config(
                bg=color,  # Цвет фона
                fg=text_color,  # Цвет текста
                font=("Arial", 28, "bold")  # Жирный шрифт
            )

    def reset_button_colors(self) -> None:
        """Сбрасывает цвета всех кнопок к значениям по умолчанию."""
        # Получаем параметры текущей темы
        theme = THEMES[self.current_theme]
        # Основной цвет фона кнопок
        bg = theme["btn_bg"]
        # Основной цвет текста кнопок
        fg = theme["btn_fg"]

        # Проходим по всем кнопкам поля
        for row in self.buttons:
            for btn in row:
                # Сбрасываем стили кнопки
                btn.config(
                    bg=bg,  # Цвет фона
                    fg=fg,  # Цвет текста
                    font=("Arial", 28, "bold"),  # Шрифт
                    text=""  # Очищаем текст
                )
                # Настройка границ (если есть в теме)
                border_color = theme.get("border")
                if border_color is not None:
                    # Устанавливаем границы
                    btn.config(
                        highlightthickness=2,  # Толщина границы
                        highlightbackground=border_color  # Цвет границы
                    )
                else:
                    # Убираем границы
                    btn.config(highlightthickness=0)

        # Сбрасываем выигрышную линию
        self.win_line = []

    def animate_move(self, btn: tk.Button, symbol: str) -> None:
        """Гримирует установку символа на поле.

        Args:
            btn: Кнопка игрового поля
            symbol: Символ для отображения ('X' или 'O')
        """
        # Начальное состояние - пробел
        btn.config(text=" ")

        if symbol == "X":
            # Анимация для X: сначала показываем "/", потом "X"
            self.window.after(50, lambda: btn.config(text="/"))
            self.window.after(150, lambda: btn.config(text="X"))
        else:
            # Анимация для O: постепенно увеличиваем символ
            for step in range(1, 6):  # 5 шагов анимации
                delay = step * 50  # Задержка для каждого шага
                # Для первых 4 шагов используем "о", на последнем - "O"
                char = "o" if step < 5 else "O"
                # Планируем изменение текста кнопки
                self.window.after(delay, lambda c=char: btn.config(text=c))

    def on_click(self, row: int, col: int) -> None:
        """Обрабатывает клик игрока по клетке поля.

        Args:
            row: Номер строки (0-2)
            col: Номер столбца (0-2)
        """
        # Если игра завершена или клетка уже занята - игнорируем клик
        if self.game_over or self.buttons[row][col]["text"] != "":
            return

        # Получаем кнопку, по которой кликнули
        btn = self.buttons[row][col]
        # Запускаем анимацию для текущего игрока
        self.animate_move(btn, self.current_player)
        # Планируем проверку состояния игры через 200 мс
        self.window.after(200, self.check_and_end_game)

    def check_and_end_game(self) -> None:
        """Проверяет состояние игры и обрабатывает завершение партии."""
        # Проверяем, есть ли победитель
        winner = self.check_winner_with_line()
        if winner:
            # Подсвечиваем выигрышную линию
            self.highlight_win_line()
            # Получаем имя победителя
            winner_name = self.player_names[winner]
            # Показываем сообщение о победе
            messagebox.showinfo("Победа!", f"🎉 {winner_name} победил(а)!")
            # Сохраняем результат игры
            self.save_game_result(f"Победа: {winner_name}")
            # Воспроизводим звук победы
            self.play_victory_sound()
            # Увеличиваем счет победителя
            self.win_count[winner] += 1
            # Обновляем отображение счета
            self.update_score_label()
            # Сохраняем обновленную статистику
            self.save_score()
            # Проверяем, нужно ли показать уведомление о рекорде
            self.check_records(winner)
            # Помечаем игру как завершенную
            self.game_over = True
            return

        # Проверяем, закончилась ли игра вничью
        if self.check_draw():
            # Показываем сообщение о ничье
            messagebox.showinfo("Ничья!", "🤝")
            # Сохраняем результат игры
            self.save_game_result("Ничья")
            # Помечаем игру как завершенную
            self.game_over = True
            return

        # Меняем текущего игрока
        self.current_player = "O" if self.current_player == "X" else "X"

        # Если играем против ИИ и сейчас его ход
        if self.vs_ai and self.current_player == "O" and not self.game_over:
            # Планируем ход ИИ через 300 мс
            self.window.after(300, self.ai_move)

    def ai_move(self) -> None:
        """Выполняет ход компьютерного игрока (ИИ)."""
        # Если игра завершена - выходим
        if self.game_over:
            return

        # Собираем список свободных клеток
        empty_cells = [
            (i, j)
            for i in range(3)
            for j in range(3)
            if self.buttons[i][j]["text"] == ""
        ]

        # Если свободных клеток нет - выходим
        if not empty_cells:
            return

        # Переменная для лучшего хода
        best_move: Optional[Tuple[int, int]] = None

        # Выбираем стратегию в зависимости от уровня сложности
        if self.ai_difficulty == "hard":
            # Используем оптимизированный минимакс для сложного уровня
            _, best_move = self.optimized_minimax(True)
        elif self.ai_difficulty == "normal":
            # Для среднего уровня ищем выигрышные ходы или блокировки
            # Поиск хода для победы ИИ
            winning_move = self.find_winning_move("O")
            # Поиск хода для блокировки игрока
            blocking_move = self.find_winning_move("X")

            if winning_move is not None:
                best_move = winning_move  # Выбираем выигрышный ход
            elif blocking_move is not None:
                best_move = blocking_move  # Блокируем игрока
            else:
                # Если нет выигрышных ходов - случайный ход
                best_move = random.choice(empty_cells)
        else:
            # Для легкого уровня - всегда случайный ход
            best_move = random.choice(empty_cells)

        # Если ход не найден (маловероятно) - выходим
        if best_move is None:
            return

        # Извлекаем координаты хода
        i, j = best_move
        # Получаем кнопку по координатам
        btn = self.buttons[i][j]
        # Запускаем анимацию для символа O
        self.animate_move(btn, "O")
        # Планируем проверку состояния игры через 200 мс
        self.window.after(200, self.check_and_end_game)

    def find_winning_move(self, player_symbol: str) -> Optional[Tuple[int, int]]:
        """Ищет выигрышный ход для указанного символа.

        Args:
            player_symbol: Символ игрока ('X' или 'O')

        Returns:
            Кортеж (строка, столбец) с координатами выигрышного хода или None
        """
        # Проходим по всем клеткам поля
        for i in range(3):
            for j in range(3):
                # Если клетка свободна
                if self.buttons[i][j]["text"] == "":
                    # Пробуем поставить символ
                    self.buttons[i][j]["text"] = player_symbol
                    # Проверяем, привело ли это к победе
                    is_win = self.check_winner_with_line() == player_symbol
                    # Отменяем ход (возвращаем пустую клетку)
                    self.buttons[i][j]["text"] = ""

                    # Если это выигрышный ход - возвращаем координаты
                    if is_win:
                        return (i, j)
        # Выигрышных ходов не найдено
        return None

    def optimized_minimax(self, is_maximizing: bool, depth: int = 0, alpha: float = -float('inf'),
                          beta: float = float('inf')) -> Tuple[float, Optional[Tuple[int, int]]]:
        """Оптимизированный алгоритм минимакс с альфа-бета отсечением.

        Args:
            is_maximizing: True если это ход активизирующего игрока (ИИ)
            depth: Глубина рекурсии
            alpha: Лучшее значение для активизирующего игрока
            beta: Лучшее значение для минимизирующего игрока

        Returns:
            Кортеж (оценка позиции, лучший ход)
        """
        # Проверяем терминальные состояния (победа, поражение, ничья)
        winner = self.check_winner_with_line()
        if winner == "O":  # Победа ИИ
            return 1, None
        if winner == "X":  # Победа игрока
            return -1, None
        if self.check_draw():  # Ничья
            return 0, None

        # Переменная для лучшего хода
        best_move: Optional[Tuple[int, int]] = None

        if is_maximizing:  # Ход ИИ (максимизация выигрыша)
            max_eval = -float('inf')  # Начальное значение оценки
            for i in range(3):
                for j in range(3):
                    # Для каждой свободной клетки
                    if self.buttons[i][j]["text"] == "":
                        # Делаем ход вместо ИИ (символ O)
                        self.buttons[i][j]["text"] = "O"
                        # Рекурсивно вызываем минимакс для следующего хода
                        eval_val, _ = self.optimized_minimax(False, depth + 1, alpha, beta)
                        # Отменяем ход
                        self.buttons[i][j]["text"] = ""

                        # Если оценка лучше текущей - обновляем
                        if eval_val > max_eval:
                            max_eval = eval_val
                            best_move = (i, j)

                        # Альфа-бета отсечение
                        alpha = max(alpha, eval_val)
                        if beta <= alpha:
                            break  # Прерываем цикл
            return max_eval, best_move
        else:  # Ход игрока (минимизация выигрыша ИИ)
            min_eval = float('inf')  # Начальное значение оценки
            for i in range(3):
                for j in range(3):
                    # Для каждой свободной клетки
                    if self.buttons[i][j]["text"] == "":
                        # Делаем ход за игрока (символ X)
                        self.buttons[i][j]["text"] = "X"
                        # Рекурсивно вызываем минимакс для следующего хода
                        eval_val, _ = self.optimized_minimax(True, depth + 1, alpha, beta)
                        # Отменяем ход
                        self.buttons[i][j]["text"] = ""

                        # Если оценка лучше текущей - обновляем
                        if eval_val < min_eval:
                            min_eval = eval_val
                            best_move = (i, j)

                        # Альфа-бета отсечение
                        beta = min(beta, eval_val)
                        if beta <= alpha:
                            break  # Прерываем цикл
            return min_eval, best_move

    def reset_game(self) -> None:
        """Начинает новую игру, сбрасывая состояние."""
        # Устанавливаем первого игрока (X)
        self.current_player = "X"
        # Сбрасываем флаг завершения игры
        self.game_over = False
        # Сбрасываем цвета кнопок и очищаем поле
        self.reset_button_colors()

    def toggle_game_mode(self) -> None:
        """Переключает режим игры между 'против ИИ' и 'два игрока'."""
        # Инвертируем текущий режим
        self.vs_ai = not self.vs_ai

        # Обновляем текст кнопки в соответствии с новым режимом
        if self.mode_button:
            text = "🎮 Режим: ИИ" if self.vs_ai else "🎮 Режим: 2 игрока"
            self.mode_button.config(text=text)

        # Начинаем новую игру
        self.reset_game()

    def set_ai_difficulty(self) -> None:
        """Показывает диалоговое окно для выбора сложности ИИ."""

        def apply_diff(chosen: str) -> None:
            """Применяет выбранную сложность и закрывает окно.

            Args:
                chosen: Выбранный уровень сложности
            """
            # Сохраняем выбранный уровень сложности
            self.ai_difficulty = chosen
            # Обновляем текст кнопки
            if self.difficulty_button:
                self.difficulty_button.config(text=f"📊 Сложность: {chosen.capitalize()}")
            # Закрываем окно выбора сложности
            diff_window.destroy()

        # Создаем диалоговое окно
        diff_window = tk.Toplevel(self.window)
        diff_window.title("Уровень сложности ИИ")  # Заголовок
        diff_window.geometry("250x200")  # Размер окна
        diff_window.resizable(False, False)  # Запрет изменения размера
        diff_window.transient(self.window)  # Делаем окно зависимым
        diff_window.grab_set()  # Блокируем главное окно

        # Создаем заголовок
        tk.Label(
            diff_window,
            text="Выберите уровень сложности:",  # Текст
            font=("Arial", 12)  # Шрифт
        ).pack(pady=10)  # Размещаем с отступом

        # Кнопки для каждого уровня сложности
        for level in ["easy", "normal", "hard"]:
            # Создаем кнопку
            btn = tk.Button(
                diff_window,
                text=level.capitalize(),  # Текст с заглавной буквы
                font=("Arial", 10),  # Шрифт
                width=15,  # Ширина
                command=lambda l=level: apply_diff(l)  # Обработчик
            )
            btn.pack(pady=5)  # Размещаем с отступом

    def set_theme(self, theme_key: str) -> None:
        """Устанавливает указанную цветовую тему.

        Args:
            theme_key: Ключ темы (например, "light", "dark")
        """
        # Проверяем, существует ли тема
        if theme_key not in THEMES:
            return

        # Сохраняем выбранную тему
        self.current_theme = theme_key

        # Обновляем текст кнопки выбора темы
        if self.theme_button:
            # Получаем название темы
            title = THEMES[theme_key]["title"]
            # Устанавливаем новый текст
            self.theme_button.config(text=f"🎨 Тема: {title}")

        # Применяем новую тему ко всем элементам интерфейса
        self.apply_theme()

    def apply_theme(self) -> None:
        """Применяет текущую тему ко всем элементам интерфейса."""
        # Получаем параметры текущей темы
        theme = THEMES[self.current_theme]

        # Устанавливаем фон главного окна
        self.window.config(bg=theme["bg"])
        # Устанавливаем фон главного фрейма
        self.main_frame.config(bg=theme["bg"])

        # Обновляем кнопки игрового поля
        for row in self.buttons:
            for btn in row:
                # Основные цвета
                btn.config(
                    bg=theme["btn_bg"],  # Цвет фона
                    fg=theme["btn_fg"]  # Цвет текста
                )
                # Настройка границ (если есть в теме)
                border_color = theme.get("border")
                if border_color is not None:
                    # Устанавливаем границы
                    btn.config(
                        highlightthickness=2,  # Толщина границы
                        highlightbackground=border_color  # Цвет границы
                    )
                else:
                    # Убираем границы
                    btn.config(highlightthickness=0)

        # Обновляем метку счета
        if self.score_label:
            self.score_label.config(
                bg=theme["bg"],  # Цвет фона
                fg=theme["btn_fg"]  # Цвет текста
            )

        # Обновляем кнопки управления
        # Мы сохраняем их базовые цвета, но обновляем текстовые цвета
        buttons_to_update = [
            (self.reset_button, "#add8e6"),
            (self.mode_button, "#90ee90"),
            (self.difficulty_button, "#f08080"),
            (self.theme_button, "#dda0dd"),
            (self.history_button, "#ffcc80"),
            (self.names_button, "#80deea")
        ]

        for btn, base_color in buttons_to_update:
            if btn:
                btn.config(
                    bg=base_color,  # Сохраняем базовый цвет фона
                    fg=theme["btn_fg"]  # Обновляем цвет текста
                )

    def check_records(self, player_key: str) -> None:
        """Проверяет и показывает уведомление о достижении рекорда.

        Args:
            player_key: Ключ игрока ('X' или 'O')
        """
        # Текущее количество побед игрока
        count = self.win_count[player_key]

        # Проверяем, достигнут ли порог рекорда и не показывали ли его ранее
        if count in RECORDS and count not in self.shown_records[player_key]:
            # Добавляем рекорд в показанные
            self.shown_records[player_key].add(count)
            # Сохраняем обновленные данные
            self.save_score()
            # Планируем показ уведомления
            self.window.after(600, lambda: self.show_record_notification(player_key))


# Точка входа в приложение
if __name__ == "__main__":
    # Создаем главное окно приложения
    root_window = tk.Tk()
    # Создаем экземпляр нашего приложения
    app = TicTacToeApp(root_window)
    # Запускаем главный цикл обработки событий
    root_window.mainloop()