from pystray import Icon, Menu, MenuItem
from PIL import Image
import threading
import sys

from kivy.config import Config
Config.set('graphics', 'position', 'custom')
Config.set('graphics', 'left', 500)
Config.set('graphics', 'top', 200)

from kivy.app import App
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
from kivy.core.window import Window
from datetime import datetime
from kivy.clock import Clock

from updater import UpdateData
from updater import GetFromRegos
import ctypes


Window.set_system_cursor = 'arrow'
Window.set_icon('logo.png')


update_data = UpdateData()
get_from_regos = GetFromRegos()

with open("config.txt") as config_file:
    config = eval(config_file.read())

check_time = config["check_time"]


class RegosCasUpdaterApp(App):
    def build(self):
        self.icon_thread = None
        self.button = Button(text='Обновить база данных!', size_hint=(None, None), height=40, width=240)
        self.button.bind(on_press=self.on_button_click)
        self.text_info = "Последная синхронизация (Cash Server) было в"
        self.label = Label(text="Проверяется", font_size='20sp')
        self.label.text_size = (600, None)
        self.label.halign = "center"


        self.title = "RegosCasSync"

        Window.size = (700, 400)
        Window.borderless = True

        self.sync_status = Label(text="",
                                 font_size='20sp')
        self.sync_status.text_size = (600, None)
        self.sync_status.halign = "center"

        self.close_button = Button(text="Выход", size_hint=(None, None), height=40, width=220)
        self.close_button.bind(on_release=self.on_close)

        button_layout = BoxLayout(orientation="horizontal", spacing=20, padding=[20, 20, 20, 20])
        button_layout.add_widget(self.button)
        button_layout.add_widget(self.close_button)
        button_layout.size_hint_y = None
        button_layout.height = 80

        layout = BoxLayout(orientation="vertical")
        layout.add_widget(button_layout)
        layout.add_widget(self.label)
        layout.add_widget(self.sync_status)

        Window.bind(on_key_down=self.on_hotkey)
        Clock.schedule_interval(self.synchronize, check_time)

        return layout

    def on_button_click(self, instance):
        if get_from_regos.connect_fdb():
            self.sync_status.text = update_data.update_mdb()
            self.label.text = f"{self.text_info} {self.timestamp_to_string(get_from_regos.last_sync)}"
        else:
            self.label.text = "Не получается подключится к База Regos"

    def synchronize(self, dt):
        if get_from_regos.connect_fdb() and get_from_regos.check_cash_status():
            self.sync_status.text = update_data.update_mdb()
            self.label.text = f"{self.text_info} {self.timestamp_to_string(get_from_regos.last_sync)}"

    def on_hotkey(self, window, key, scancode, codepoint, modifier):
        # Check if Ctrl is pressed and the key is 'U'
        if 'ctrl' in modifier and codepoint == 'u':
            self.button.trigger_action()

    def timestamp_to_string(self, ts):
        date_obj = datetime.fromtimestamp(ts)
        date_str = date_obj.strftime("%d.%m.%Y %H:%M:%S")
        return date_str

    def on_close(self, *args):
        self.hide_to_tray()

    def hide_to_tray(self):
        # Minimize the app window (or hide it)
        Window.minimize()

        # Create a system tray icon in a separate thread
        if not self.icon_thread:
            self.icon_thread = threading.Thread(target=self.add_to_tray)
            self.icon_thread.daemon = True
            self.icon_thread.start()

    def add_to_tray(self):
        # Load an icon image for the tray (Pillow image required by pystray)
        image = Image.open("logo.png")  # Path to your icon image

        # Define what happens when user clicks "Exit" in tray menu
        def on_quit(icon, item):
            icon.stop()  # Stop the tray icon
            sys.exit()   # Exit the application

        # Define the tray menu
        menu = Menu(MenuItem("Exit", on_quit))

        # Create the tray icon
        icon = Icon("RegosCasSync", image, menu=menu)

        # Run the tray icon (this blocks, so it's on a separate thread)
        icon.run()

    def on_stop(self):
        if self.icon_thread:
            sys.exit()

def prevent_multiple_instances():
    """ Use a Windows mutex to prevent multiple instances of the application. """
    mutex_name = "MyUniqueKivyAppMutex"
    # Create a named mutex
    kernel32 = ctypes.windll.kernel32
    mutex = kernel32.CreateMutexW(None, False, mutex_name)

    # Check if another instance already has the mutex
    last_error = kernel32.GetLastError()

    ERROR_ALREADY_EXISTS = 183  # Error code for already existing mutex
    if last_error == ERROR_ALREADY_EXISTS:
        return False  # Another instance is already running
    return True  # No other instance is running


if __name__ == '__main__':
    if prevent_multiple_instances():
        RegosCasUpdaterApp().run()

