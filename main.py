import sys
import requests

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QApplication, QMainWindow
from interface2 import Ui_MainWindow


class Map(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.no_point = None
        self.point_coordinates_text = None
        self.previous_toponym_coordinates = None
        self.upper = None
        self.lower = None
        self.previous_toponym_coordinates_text = None
        self.previous_delta_1 = None
        self.previous_delta_2 = None

        self.maps = {
            'Схема': 'map',
            'Спутник': 'sat',
            'Смешанная': 'skl',
            'Пробки': 'trf'
        }

        self.setupUi(self)
        self.setWindowTitle('Map')

        self.btn.clicked.connect(self.find_place)
        self.input.returnPressed.connect(self.find_place)
        self.clear_btn.clicked.connect(self.clear)

        self.statusBar.showMessage('Для перемещения нажмите на карту и используйте PgDn и PgUp!')

    def keyPressEvent(self, event):
        try:
            if event.key() == Qt.Key_Escape:
                self.close()

            elif event.key() == Qt.Key_Enter:
                self.find_place()

            if event.key() in (Qt.Key_PageUp, Qt.Key_PageDown):
                if event.key() == Qt.Key_PageDown and (self.previous_delta_1 < 100 or self.previous_delta_2 < 50):
                    self.previous_delta_1 = min(self.previous_delta_1 * 2, 100)
                    self.previous_delta_2 = min(self.previous_delta_2 * 2, 50)

                elif event.key() == Qt.Key_PageUp and (self.previous_delta_1 > 0.001 or self.previous_delta_2 > 0.0005):
                    self.previous_delta_1 = max(self.previous_delta_1 / 2, 0.001)
                    self.previous_delta_2 = max(self.previous_delta_2 / 2, 0.0005)
                image = self.get_image(self.previous_toponym_coordinates_text, no_point=self.no_point)
                self.pix_map(image)

            elif event.key() == Qt.Key_Up:
                self.move_map('up')
            elif event.key() == Qt.Key_Down:
                self.move_map('down')
            elif event.key() == Qt.Key_Left:
                self.move_map('left')
            elif event.key() == Qt.Key_Right:
                self.move_map('right')

        except TypeError:
            self.statusBar.showMessage('Для начала найдите объект!')

    def clear(self):
        self.no_point = True
        image = self.get_image(self.previous_toponym_coordinates_text, no_point=True)
        self.pix_map(image)
        self.address_area.clear()

    def move_map(self, direction):
        if self.lower and self.upper:
            if direction == 'up':
                coordinate_1 = self.previous_toponym_coordinates[0]
                coordinate_2 = self.previous_toponym_coordinates[1] + self.previous_delta_2 / 2
                if coordinate_2 > 80:
                    coordinate_2 = 80
            elif direction == 'down':
                coordinate_1 = self.previous_toponym_coordinates[0]
                coordinate_2 = self.previous_toponym_coordinates[1] - self.previous_delta_2 / 2
                if coordinate_2 < -80:
                    coordinate_2 = -80
            elif direction == 'left':
                coordinate_1 = self.previous_toponym_coordinates[0] - self.previous_delta_1
                if coordinate_1 < -180:
                    coordinate_1 = -180
                coordinate_2 = self.previous_toponym_coordinates[1]
            elif direction == 'right':
                coordinate_1 = self.previous_toponym_coordinates[0] + self.previous_delta_1
                if coordinate_1 > 179:
                    coordinate_1 = 179
                coordinate_2 = self.previous_toponym_coordinates[1]

            self.previous_toponym_coordinates = [coordinate_1, coordinate_2]
            self.previous_toponym_coordinates_text = ','.join(list(map(str, self.previous_toponym_coordinates)))

            image = self.get_image(f'{coordinate_1},{coordinate_2}', no_point=self.no_point)
            self.pix_map(image)

    def find_place(self):
        self.no_point = False
        coordinates = self.find_toponym_coordinates()
        if coordinates is None:
            self.statusBar.showMessage('Введите место для поиска!')
            return None
        image = self.get_image(coordinates, no_point=self.no_point)
        self.pix_map(image)

    def pix_map(self, image):
        pixmap = QPixmap()
        pixmap.loadFromData(image)
        self.map.setPixmap(pixmap)

    def find_toponym_coordinates(self):
        toponym_to_find = self.input.text()
        geocoder_api_server = "http://geocode-maps.yandex.ru/1.x/"

        geocoder_params = {
            "apikey": "40d1649f-0493-4b70-98ba-98533de7710b",
            "geocode": toponym_to_find,
            "format": "json"}

        geocoder_response = requests.get(geocoder_api_server, params=geocoder_params)

        if not geocoder_response:
            return

        self.statusBar.clearMessage()

        json_geocoder_response = geocoder_response.json()

        toponym = json_geocoder_response["response"]["GeoObjectCollection"]["featureMember"][0]["GeoObject"]
        toponym_address = toponym["metaDataProperty"]["GeocoderMetaData"]["Address"]["formatted"]
        try:
            toponym_index = toponym["metaDataProperty"]["GeocoderMetaData"]["Address"]["postal_code"]
        except KeyError:
            toponym_index = 'нет почтового индекса'
        toponym_coordinates = list(map(float, toponym["Point"]["pos"].split()))
        toponym_coordinates_text = ','.join(list(map(str, toponym_coordinates)))

        if self.index.isChecked():
            self.address_area.setText(f'{toponym_address}; почтовый индекс: {toponym_index}')
        else:
            self.address_area.setText(toponym_address)

        self.lower = list(map(float, toponym["boundedBy"]["Envelope"]['lowerCorner'].split()))
        self.upper = list(map(float, toponym["boundedBy"]["Envelope"]['upperCorner'].split()))

        if not (self.previous_delta_1 and self.previous_delta_2):
            self.previous_delta_1 = self.upper[0] - self.lower[0]
            self.previous_delta_2 = self.upper[1] - self.lower[1]

        self.previous_toponym_coordinates_text = toponym_coordinates_text
        self.previous_toponym_coordinates = toponym_coordinates
        self.point_coordinates_text = toponym_coordinates_text

        return toponym_coordinates_text

    def get_image(self, toponym_coordinates_text, no_point=False):
        map_params = {
            "ll": toponym_coordinates_text,
            "spn": f"{self.previous_delta_1},{self.previous_delta_2}",
            "l": self.maps[self.drop_list.currentText()],
            "pt": f"{self.point_coordinates_text},org",
            "size": '650,450'
        }

        if no_point:
            del map_params["pt"]

        map_api_server = "http://static-maps.yandex.ru/1.x/"
        static_map_response = requests.get(map_api_server, params=map_params)

        return static_map_response.content

    def get_image_size(self):
        width, height = self.size().width(), self.size().height()
        print(width, height)
        return f'{width},{height}'


def except_hook(cls, exception, traceback):
    sys.__excepthook__(cls, exception, traceback)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = Map()
    ex.show()
    sys.excepthook = except_hook
    sys.exit(app.exec())
