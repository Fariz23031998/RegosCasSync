from kivy.app import App
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
from kivy.core.window import Window
from datetime import datetime
from kivy.clock import Clock

from updater import UpdateData
from updater import GetFromRegos

update_data = UpdateData()
get_from_regos = GetFromRegos()

with open("config.txt") as config_file:
    config = eval(config_file.read())

check_time = config["check_time"]


class RegosCasUpdaterApp(App):
    def build(self):
        self.button = Button(text='Обновить база данных!', size_hint=(None, None), height=40, width=240)
        self.button.bind(on_press=self.on_button_click)
        self.text_info = "Последная синхронизация (Cash Server) было в"
        self.label = Label(text="Проверяется", font_size='20sp')
        self.label.text_size = (600, None)
        self.label.halign = "center"

        self.sync_status = Label(text="",
                                 font_size='20sp')

        layout = BoxLayout(orientation="vertical")
        layout.add_widget(self.button)
        layout.add_widget(self.label)
        layout.add_widget(self.sync_status)

        Window.bind(on_key_down=self.on_hotkey)
        Clock.schedule_interval(self.synchronize, check_time)

        return layout

    def on_button_click(self, instance):
        if get_from_regos.connect_fdb():
            self.sync_status.text = update_data.update_mdb()
            self.label.text = f"{self.text_info} {self.timestamp_to_string(get_from_regos.last_sync)}"

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


if __name__ == '__main__':
    RegosCasUpdaterApp().run()
