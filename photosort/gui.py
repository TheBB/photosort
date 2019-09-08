from string import ascii_lowercase
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QPixmap
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QLabel, QVBoxLayout


KEY_MAP = {
    Qt.Key_Space: 'SPC',
    Qt.Key_Escape: 'ESC',
    Qt.Key_Tab: 'TAB',
    Qt.Key_Return: 'RET',
    Qt.Key_Backspace: 'BSP',
    Qt.Key_Delete: 'DEL',
    Qt.Key_Up: 'UP',
    Qt.Key_Down: 'DOWN',
    Qt.Key_Left: 'LEFT',
    Qt.Key_Right: 'RIGHT',
    Qt.Key_Minus: '-',
    Qt.Key_Plus: '+',
    Qt.Key_Equal: '=',
}
KEY_MAP.update({
    getattr(Qt, 'Key_{}'.format(s.upper())): s
    for s in ascii_lowercase
})

def key_to_text(event):
    ctrl = event.modifiers() & Qt.ControlModifier
    shift = event.modifiers() & Qt.ShiftModifier

    try:
        text = KEY_MAP[event.key()]
    except KeyError:
        return

    if shift and text.isupper():
        text = 'S-{}'.format(text)
    elif shift:
        text = text.upper()
    if ctrl:
        text = 'C-{}'.format(text)

    return text


class ImageView(QLabel):

    def __init__(self):
        super(ImageView, self).__init__()
        self.setMinimumSize(1,1)
        self.setAlignment(Qt.Alignment(0x84))
        self.orig_pixmap = None

    def load(self, filename):
        if not filename:
            self.orig_pixmap = QPixmap()
        else:
            self.orig_pixmap = QPixmap(filename)
        self.resize()

    def resize(self):
        if not self.orig_pixmap:
            return
        if not self.orig_pixmap.isNull():
            pixmap = self.orig_pixmap.scaled(self.width(), self.height(), 1, 1)
        else:
            pixmap = self.orig_pixmap
        self.setPixmap(pixmap)

    def resizeEvent(self, event):
        self.resize()


class MainWidget(QWidget):

    def __init__(self):
        super(MainWidget, self).__init__()

        self.image = ImageView()
        self.label = QLabel()
        self.label.setMaximumHeight(25)
        self.label.setStyleSheet('color: rgb(200, 200, 200);')

        font = QFont()
        font.setPixelSize(20)
        font.setWeight(QFont.Bold)
        self.label.setFont(font)

        self.setLayout(QVBoxLayout())
        self.layout().addWidget(self.image)
        self.layout().addWidget(self.label)

    def load(self, filename):
        self.image.load(filename)

    def message(self, msg):
        self.label.setText('<div align="center">{}</div>'.format(msg))


class MainWindow(QMainWindow):

    def __init__(self, media):
        QMainWindow.__init__(self)
        self.setStyleSheet('background-color: black;')

        self.main = MainWidget()
        self.setCentralWidget(self.main)

        self.media = media
        self.load(0)

        self.num = None

    def load(self, index):
        self.index = max(min(index, len(self.media)-1), 0)
        media = self.media[self.index]

        self.main.load(media.filename if media.has_photo else None)
        when = media.when.strftime('%Y-%m-%d %H:%M')
        roles = ', '.join(media.roles())
        self.main.message(f'{media.root} ({when}; {roles})')

    def keyPressEvent(self, event):
        text = key_to_text(event)
        if text is None:
            return
        if text in ('SPC', 'RIGHT', 'l'):
            self.load(self.index + 1)
        elif text in ('S-SPC', 'S-RIGHT', 'L'):
            self.load(self.index + 10)
        elif text in ('BSP', 'LEFT', 'h'):
            self.load(self.index - 1)
        elif text in ('S-BSP', 'S-LEFT', 'H'):
            self.load(self.index - 10)
        elif text in ('RET',):
            self.num = self.index + 1
            self.close()
        elif text in ('q', 'ESC'):
            self.close()


def run_gui(media):
    app = QApplication([])
    win = MainWindow(media)
    win.showMaximized()
    app.exec_()
    return win.num
