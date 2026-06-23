# /// script
# dependencies = [
#   "pythonnet",
#   "winotify",
#   "pystray",
#   "pillow",
#   "pywin32",
# ]
# ///

import os
import signal
import sys
import threading
import time

import pystray
from PIL import Image, ImageDraw, ImageFont
from winotify import Notification

# Добавляем текущую директорию в пути поиска для .NET, чтобы скрипт увидел DLL
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(script_dir)

import clr  # Подключаем Python.NET

# Загружаем библиотеку мониторинга железа
try:
    clr.AddReference(r"LibreHardwareMonitor\LibreHardwareMonitorLib")
    from LibreHardwareMonitor.Hardware import Computer
except Exception as e:
    print(
        f"Ошибка: Не удалось загрузить LibreHardwareMonitorLib.dll. Убедитесь, что файл лежит рядом со скриптом.\nДетали: {e}"
    )
    sys.exit(1)

# --- НАСТРОЙКИ ---
THRESHOLD_TEMP = 75  # Граница паники в градусах
CHECK_INTERVAL = 5  # Интервал проверки (в секундах)
is_running = True

DEVICES_COLOR = {
    'cpu': (255, 255, 255),
    'nvidia': (50, 255, 50),
    'amd': (255, 50, 50)
}


# Настройка уведомления "ХУЯ ПИЧОТ"
toast = Notification(
    # app_id="Мониторинг CPU",
    app_id="Microsoft.Windows.Powershell",
    title="🔥 ХУЯ ПИЧОТ! 🔥",
    msg="Ноутбук сильно нагрелся!",
    duration="long",
)

# Инициализируем движок мониторинга процессора
computer = Computer()
computer.IsCpuEnabled = True
computer.IsGpuEnabled = True
try:
    computer.Open()
except Exception as e:
    print(f"Ошибка инициализации датчиков (запустили без админа?): {e}")

import tkinter as tk

type DeviceTemp = dict[str, int]


def show_fullscreen_alert(temp):
    """Создает полноэкранные красные окна предупреждения на ВСЕХ подключенных дисплеях."""
    # Создаем базовый корневой процесс Tkinter
    root = tk.Tk()
    root.withdraw()  # Скрываем главное невидимое окно

    # Получаем список всех мониторов через системный вызов Windows
    # Для этого временно задействуем win32api (он уже есть в составе pywin32)
    import win32api

    monitors = win32api.EnumDisplayMonitors()
    windows = []

    # Перебираем каждый найденный экран
    for i, monitor in enumerate(monitors):
        # Получаем координаты конкретного монитора (лево, верх, право, низ)
        monitor_info = win32api.GetMonitorInfo(monitor[0])
        coords = monitor_info["Monitor"]

        x = coords[0]
        y = coords[1]
        width = coords[2] - coords[0]
        height = coords[3] - coords[1]

        # Создаем отдельное окно для этого монитора
        win = tk.Toplevel(root)

        # Оформление окна: убираем рамки Windows, красим в красный
        win.overrideredirect(True)
        win.configure(bg="#CC0000")

        # Делаем окно ПОВЕРХ ВСЕХ ОКОН (даже поверх игр в полноэкранном режиме)
        win.attributes("-topmost", True)

        # Задаем геометрию окна четко под размеры текущего монитора
        win.geometry(f"{width}x{height}+{x}+{y}")

        # Добавляем страшный текст по центру
        label_title = tk.Label(
            win,
            text="🔥 ХУЯ ПИЧОТ!!! 🔥",
            font=("Arial", 46, "bold"),
            fg="white",
            bg="#CC0000",
        )
        label_title.pack(expand=True, anchor="s", pady=20)

        label_msg = tk.Label(
            win,
            text=f"Температура системы: {temp}°C\nПроверь охлаждающую подставку!",
            font=("Arial", 28, "normal"),
            fg="#FFFF00",
            bg="#CC0000",
        )
        label_msg.pack(expand=True, anchor="n", pady=20)

        windows.append(win)

    # Функция автоматического закрытия окон через 5 секунд, чтобы не вешать систему
    def close_all():
        root.destroy()

    root.after(5000, close_all)

    # Запуск цикла отрисовки окон (заблокирует поток выполнения на 5 секунд)
    root.mainloop()


def show_corner_alert(temp: int, device: str = "cpu"):
    """Создает маленькие красные окошки предупреждения в правом нижнем углу КАЖДОГО физического экрана."""
    # Получаем список всех мониторов через системный вызов Windows
    # Для этого временно задействуем win32api (он уже есть в составе pywin32)
    import win32api

    root = tk.Tk()
    root.withdraw()  # Скрываем основное окно

    # Размеры нашего аккуратного окошка
    win_width = 350
    win_height = 110

    # Отступы от правого и нижнего края экрана (чтобы не перекрывать важные элементы)
    offset_x = 30
    offset_y = 60

    windows = []

    # win32api возвращает реальные физические границы каждого подключенного монитора
    for monitor in win32api.EnumDisplayMonitors():
        monitor_info = win32api.GetMonitorInfo(monitor[0])
        coords = monitor_info["Monitor"]

        # coords содержит: [левая_граница, верхняя, правая, нижняя]
        monitor_right = coords[2]
        monitor_bottom = coords[3]

        # Вычисляем правый нижний угол конкретно для этого монитора
        x = monitor_right - win_width - offset_x
        y = monitor_bottom - win_height - offset_y

        win = tk.Toplevel(root)

        # --- МАГИЯ ДЛЯ ЗАЩИТЫ ФОКУСА ИГРЫ ---
        # 1. Запрещаем окну принимать фокус ввода (оно станет "сквозным" для клавиатуры)
        win.attributes("-disabled", True)

        # 2. Подсказываем Windows, что окно не нужно делать активным при показе
        win.wm_attributes("-topmost", True)
        # ------------------------------------

        # Убираем рамки Windows, делаем поверх всех окон
        win.overrideredirect(True)
        win.attributes("-topmost", True)

        # Делаем окно слегка прозрачным (85% видимости), чтобы сквозь него было видно игру
        win.attributes("-alpha", 0.85)
        win.configure(bg="#CC0000")

        # Задаем геометрию окна четко в угол этого монитора
        win.geometry(f"{win_width}x{win_height}+{x}+{y}")

        # Текст предупреждения
        tk.Label(
            win,
            text="🔥 ХУЯ ПИЧОТ! 🔥",
            font=("Arial", 22, "bold"),
            fg="#FFFF00",
            bg="#CC0000",
        ).pack(pady=(10, 0))

        tk.Label(
            win,
            text=f"Температура {device.upper()}: {temp}°C",
            font=("Arial", 14, "bold"),
            fg="white",
            bg="#CC0000",
        ).pack(pady=5)

        windows.append(win)

    # Эффект мигания для привлечения внимания
    def blink(state=True):
        if not root.winfo_exists():
            return
        for w in windows:
            if w.winfo_exists():
                w.configure(bg="#CC0000" if state else "#550000")
                for child in w.winfo_children():
                    child.configure(bg="#CC0000" if state else "#550000")
        root.after(500, blink, not state)

    blink()

    # Закрываем окошки сами через 7 секунд
    root.after(7000, root.destroy)
    root.mainloop()


def print_sensors():
    print("Debug Sensors:")

    for hardware in computer.Hardware:
        hardware.Update()  # Опрашиваем железо
        print(
            f"{hardware.Name} ({hardware.HardwareType}: {int(hardware.HardwareType)})"
        )

        for s in hardware.Sensors:
            print(f"{s.Name}({s.SensorType}:{int(s.SensorType)}): {s.Value}")


def get_cpu_temp():
    """Считывает точную температуру ядер процессора напрямую через драйвер.

    Требует запуска от Администратора!
    """
    try:
        for hardware in computer.Hardware:
            hardware.Update()  # Опрашиваем железо
            for sensor in hardware.Sensors:
                # Нам нужен датчик температуры (SensorType = 2) и общий нагрев (Core Average или Package)
                if int(sensor.SensorType) == 4 and (
                    "package" in sensor.Name.lower()
                    or "average" in sensor.Name.lower()
                    or "core #0" in sensor.Name.lower()
                ):
                    if sensor.Value is not None:
                        return int(sensor.Value)
    except Exception as e:
        print(e)
        pass
    return -10  # Заглушка


def get_devices_temp() -> dict[str, int]:
    devices: dict[str, int] = {}
    for hardware in computer.Hardware:
        hardware.Update()  # Опрашиваем устройство

        # Получаем имя и тип в нижнем регистре для удобного поиска
        hw_name = hardware.Name.lower()
        hw_type = str(hardware.HardwareType).lower()

        # Точечно определяем, с какой видеокартой мы сейчас работаем
        if "nvidia" in hw_name or "nvidia" in hw_type:
            current_device = "nvidia"
        elif "amd" in hw_name or "radeon" in hw_name or "amd" in hw_type:
            current_device = "amd"
        elif "cpu" in hw_type:
            current_device = "cpu"
        else:
            continue  # Пропускаем материнскую плату, диски и т.д.

        # Теперь перебираем датчики этого конкретного устройства
        for sensor in hardware.Sensors:
            sensor_type = str(sensor.SensorType).lower()
            sensor_name = sensor.Name.lower()

            if "temperature" in sensor_type and sensor.Value is not None:
                if current_device == "cpu" and (
                    "package" in sensor_name
                    or "average" in sensor_name
                    or "core #0" in sensor_name
                ):
                    devices[current_device] = int(sensor.Value)
                else:
                    devices[current_device] = int(sensor.Value)
    return devices

def get_max_temp() -> tuple[str, int]:
    devices_temp = get_devices_temp()

    (device, temp) = list(sorted(devices_temp.items(), key=lambda i: i[1], reverse=True))[0]
    return (device, temp)

type ColorRGB = tuple[int, int, int]

def create_temp_icon(temp, color: ColorRGB=(255, 255, 255)):
    """Динамически создает квадратную иконку 32x32 с числом температуры"""
    img = Image.new("RGBA", (32, 32), color=(0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    text_color = color

    try:
        font = ImageFont.truetype("arial.ttf", 20)
    except IOError:
        font = ImageFont.load_default()

    text = str(temp)
    position = (4, 4) if len(text) == 2 else (0, 4)

    draw.text(position, text, fill=text_color, font=font)
    return img


def monitor_loop():
    """Фоновый цикл проверки температуры"""
    global is_running
    last_notification_time = 0

    while is_running:
        [device, temp] = get_max_temp()
        if temp >= THRESHOLD_TEMP:
            current_time = time.time()
            if current_time - last_notification_time > 30:
                show_corner_alert(temp, device)
                last_notification_time = current_time

        time.sleep(CHECK_INTERVAL)


def menu_on_exit(icon, item):
    """Корректный выход из скрипта"""
    icon.stop()
    on_exit()

def on_exit():
    """Корректный выход из скрипта"""
    global is_running
    is_running = False
    computer.Close()  # Освобождаем низкоуровневый драйвер
    os._exit(0)

def check_notify():

    (device, temp) = get_max_temp()
    show_corner_alert(temp, device)

def start_icon_thread(device_name, text_color):
    # Создаем уникальный объект иконки для конкретного устройства
    icon = pystray.Icon(
        name=f"monitor_{device_name}",
        icon=create_temp_icon(45, text_color),
        title=f"{device_name}: Ожидание...",
        menu=pystray.Menu(
            pystray.MenuItem("Проверка оповещения", check_notify),
            pystray.MenuItem("Выход", on_exit)
        ),
    )

    # Фоновый цикл, который обновляет ТОЛЬКО ЭТУ иконку
    def device_loop():
        while is_running:
            # Получаем температуру конкретно для device_name (CPU/GPU)
            temp = get_devices_temp()[device_name]

            icon.icon = create_temp_icon(temp, text_color)
            icon.title = f"{device_name}: {temp}°C"

            time.sleep(3)

    # Запускаем обновление датчика
    threading.Thread(target=device_loop, daemon=True).start()

    # Запускаем саму иконку в трее (этот вызов заблокирует текущий поток)
    icon.run()

def main():
    print_sensors()
    initial_temp = get_devices_temp()
    print(initial_temp)

    # toast.msg = f"Текущая температура: {initial_temp}°C! ХУЯ ПИЧОТ!"
    # toast.show()

    # Функция, которая выполнится при нажатии Ctrl+C в консоли
    def handle_ctrl_c(signum, frame):
        print("\nПолучен сигнал Ctrl+C. Завершаю работу...")
        on_exit()  # Вызываем ваш готовый корректный выход

    # Регистрируем перехват Ctrl+C (SIGINT)
    signal.signal(signal.SIGINT, handle_ctrl_c)

    # Запускаем ци
    for device_name in initial_temp:
        threading.Thread(
            target=start_icon_thread, args=(device_name, DEVICES_COLOR[device_name])
        ).start()

    monitor_thread = threading.Thread(target=monitor_loop)
    monitor_thread.daemon = True
    monitor_thread.start()


if __name__ == "__main__":
    main()
