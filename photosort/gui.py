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

    def __init__(self, media, allow_modify_date=False):
        QMainWindow.__init__(self)
        self.setStyleSheet('background-color: black;')

        self.main = MainWidget()
        self.setCentralWidget(self.main)

        self.media = media
        self.load(0)

        self.num = None
        self.allow_modify_date = allow_modify_date

    def load(self, index):
        self.index = max(min(index, len(self.media)-1), 0)
        media = self.media[self.index]
        self.main.load(media.filename if media.has_photo else None)
        self.update_msg()

    def update_msg(self):
        media = self.media[self.index]
        when = media.when.strftime('%Y-%m-%d %H:%M')
        roles = ', '.join(media.roles())
        desc = f'; {media.description}' if media.description else ''
        self.main.message(f'({self.index+1}/{len(self.media)}) {media.root} ({when}; {roles}{desc})')

    def keyPressEvent(self, event):
        text = key_to_text(event)
        if text is None:
            return
        if text in ('SPC', 'RIGHT', 'l', 'j'):
            self.load(self.index + 1)
        elif text in ('S-SPC', 'S-RIGHT', 'L', 'J'):
            self.load(self.index + 10)
        elif text in ('BSP', 'LEFT', 'h', 'k'):
            self.load(self.index - 1)
        elif text in ('S-BSP', 'S-LEFT', 'H', 'K'):
            self.load(self.index - 10)
        elif text in ('RET',):
            self.num = self.index + 1
            self.close()
        elif text in ('q', 'ESC'):
            self.close()
        elif text in ('C-c',) and self.allow_modify_date:
            self._date = self.media[self.index].when.replace(hour=0, minute=0, second=0)
        elif text in ('C-v',) and self.allow_modify_date:
            self.media[self.index]._when = self._date
            self.update_msg()
        elif text in ('y', 'Y', 'm', 'M', 'd', 'D') and self.allow_modify_date:
            attrname = {'y': 'year', 'm': 'month', 'd': 'day'}[text.lower()]
            step = 1 if text.upper() == text else -1
            media = self.media[self.index]
            date = media.when
            try:
                media._when = date.replace(hour=0, minute=0, second=0, **{attrname: getattr(date, attrname) + step})
            except ValueError:
                pass
            self.update_msg()


def run_gui(media, **kwargs):
    app = QApplication([])
    win = MainWindow(media, **kwargs)
    win.showMaximized()
    app.exec_()
    return win.num
