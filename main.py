import sys
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from datetime import datetime, timedelta
from PyQt5.QtCore import QTimer, QTime
import telebot


class EditTaskDialog(QDialog):
    def __init__(self, current_task, current_priority, current_time, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Редактировать задачу')

        self.task_input = QLineEdit()
        self.task_input.setText(current_task)

        self.time_input = QTimeEdit()
        self.time_input.setDisplayFormat('HH:mm')
        if current_time:
            self.time_input.setTime(QTime.fromString(current_time, 'HH:mm'))

        self.priority_label = QLabel('Приоритет:')
        self.priority_button = QPushButton('Выбрать цвет')
        self.priority_color = QColor(current_priority)

        layout = QVBoxLayout()
        layout.addWidget(QLabel('Измените задачу:'))
        layout.addWidget(self.task_input)
        layout.addWidget(QLabel('Установите время напоминания:'))
        layout.addWidget(self.time_input)
        layout.addWidget(self.priority_label)
        layout.addWidget(self.priority_button)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)

        self.priority_button.clicked.connect(self.pick_priority_color)

    def pick_priority_color(self):
        color = QColorDialog.getColor(self.priority_color, self, 'Выберите цвет приоритета')
        if color.isValid():
            self.priority_color = color

    def get_updated_task(self):
        return self.task_input.text(), self.priority_color, self.time_input.time().toString('HH:mm')


class ToDoApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()

        # Загрузим данные о токене бота и пользователе
        self.bot_token, self.telegram_user_id = self.load_bot_info()

        # Создаем объект телеграм-бота
        self.bot = telebot.TeleBot(self.bot_token)


    def initUI(self):
        self.setWindowTitle('Простое приложение для управления задачами')
        self.setGeometry(100, 100, 600, 400)

        self.task_input = QLineEdit()
        self.add_button = QPushButton('Добавить задачу')
        self.delete_button = QPushButton('Удалить задачу')
        self.edit_button = QPushButton('Редактировать задачу')
        self.task_list = QListWidget()
        self.time_input = QTimeEdit()

        layout = QVBoxLayout()
        task_layout = QHBoxLayout()
        task_layout.addWidget(self.task_input)
        task_layout.addWidget(self.add_button)
        task_layout.addWidget(self.delete_button)
        task_layout.addWidget(self.edit_button)
        layout.addLayout(task_layout)
        layout.addWidget(self.task_list)

        main_widget = QWidget()
        main_widget.setLayout(layout)
        self.setCentralWidget(main_widget)

        self.add_button.clicked.connect(self.add_task)
        self.delete_button.clicked.connect(self.delete_task)
        self.edit_button.clicked.connect(self.edit_task)

        self.load_tasks()

    def add_task(self):
        task_text = self.task_input.text()
        if task_text:
            current_time = self.time_input.time().toString('HH:mm')
            current_time_datetime = datetime.now().replace(hour=int(current_time[:2]), minute=int(current_time[3:]),second=0, microsecond=0)

            task_with_time = f'{current_time} - {task_text}'
            new_item = QListWidgetItem(task_with_time)
            priority_color = QColorDialog.getColor()
            new_item.setForeground(priority_color)
            new_item.setData(1, priority_color)
            new_item.setData(2, current_time)
            self.task_list.addItem(new_item)

            # Устанавливаем напоминание
            self.schedule_reminder(current_time_datetime, task_text)

            self.task_input.clear()
            self.save_tasks()

    def delete_task(self):
        selected_item = self.task_list.currentItem()
        if selected_item:
            self.task_list.takeItem(self.task_list.row(selected_item))
            self.save_tasks()

    def edit_task(self):
        selected_item = self.task_list.currentItem()
        if selected_item:
            current_task = selected_item.text()
            current_priority = selected_item.data(1)
            current_time = selected_item.data(2)
            edit_dialog = EditTaskDialog(current_task, current_priority, current_time, self)
            if edit_dialog.exec_() == QDialog.Accepted:
                updated_task, updated_priority, updated_time = edit_dialog.get_updated_task()
                selected_item.setText(updated_task)
                selected_item.setData(1, updated_priority)
                selected_item.setData(2, updated_time)

                # Пересоздаем напоминание с новым временем
                updated_time_datetime = datetime.now().replace(hour=int(updated_time[:2]), minute=int(updated_time[3:]),
                                                               second=0, microsecond=0)
                self.schedule_reminder(updated_time_datetime, updated_task)

                selected_item.setForeground(updated_priority)
                self.save_tasks()

    def schedule_reminder(self, reminder_time, task_text):
        # Вычисляем время до напоминания
        time_difference = reminder_time - datetime.now()

        # Запускаем таймер для отправки сообщения в указанное время
        QTimer.singleShot(time_difference.total_seconds() * 1000, lambda: self.send_reminder(task_text))

    def send_reminder(self, task_text):
        # Отправляем напоминание в телеграм
        try:
            self.bot.send_message(self.telegram_user_id, f"Напоминание: {task_text}")
        except telebot.apihelper.ApiException as e:
            print(f"Ошибка при отправке сообщения в телеграм: {e}")

    def load_bot_info(self):
        try:
            with open('bot_info.txt', 'r') as file:
                lines = file.readlines()
                bot_token = lines[0].strip()
                telegram_user_id = int(lines[1].strip())
                return bot_token, telegram_user_id
        except FileNotFoundError:
            return None, None

    def save_bot_info(self, bot_token, telegram_user_id):
        with open('bot_info.txt', 'w') as file:
            file.write(f"{bot_token}\n{telegram_user_id}\n")

    def save_tasks(self):
        tasks = [(self.task_list.item(i).text(), self.task_list.item(i).data(1).name(), self.task_list.item(i).data(2))
                 for i in range(self.task_list.count())]
        with open('tasks.txt', 'w') as file:
            for task, priority, time in tasks:
                file.write(f'{time} - {priority} - {task}\n')

    def load_tasks(self):
        try:
            with open('tasks.txt', 'r') as file:
                for line in file:
                    time, priority, task = line.strip().split(' - ', 2)
                    color = QColor(priority)
                    new_item = QListWidgetItem(task)
                    new_item.setForeground(color)
                    new_item.setData(1, color)
                    new_item.setData
        except:
            pass


if __name__ == '__main__':
    app = QApplication(sys.argv)
    todo_app = ToDoApp()
    todo_app.show()
    sys.exit(app.exec_())
