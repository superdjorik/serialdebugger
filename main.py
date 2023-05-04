from kivy.app import App
from kivy.uix.floatlayout import FloatLayout
from kivy.factory import Factory
from kivy.properties import ObjectProperty, ListProperty
from kivy.uix.widget import Widget
from kivy.clock import Clock
from kivy.uix.popup import Popup
from kivy.utils import platform
from kivymd.app import MDApp
import os
import datetime
from pathlib import Path


class Indicator(Widget):
    color = ListProperty([1, 0, 0, 1])
    pass


def ByteToHex(byteStr):
    return ''.join(["%02X " % ord(x) for x in byteStr]).strip()


def HexToByte(hexStr):
    bytes = []
    hexStr = ''.join(hexStr.split(" "))
    for i in range(0, len(hexStr), 2):
        bytes.append(chr(int(hexStr[i:i + 2], 16)))
    return ''.join(bytes)


def HEXStringToBytesArray(hexStr: str) -> bytes:
    bytes = []

    hexStr = ''.join(hexStr.split(" "))

    for i in range(0, len(hexStr), 2):
        bytes.append(int(hexStr[i:i + 2], 16))

    return bytes



class SaveDialog(FloatLayout):
    save = ObjectProperty(None)
    text_input = ObjectProperty(None)
    cancel = ObjectProperty(None)
    homepath = str(Path.home())


class Root(FloatLayout):
    console_text = ObjectProperty(None)
    send_text = ObjectProperty(None)
    id_commport = ObjectProperty(None)
    id_baudrate = ObjectProperty(None)
    id_checksum = ObjectProperty(None)
    id_stopbit = ObjectProperty(None)
    id_databit = ObjectProperty(None)
    id_indicator = ObjectProperty(None)
    id_switch_serial = ObjectProperty(None)
    id_recv_encode = ObjectProperty(None)
    id_send_encode = ObjectProperty(None)
    id_append_linend_send = ObjectProperty(None)
    id_add_timestamp = ObjectProperty(None)
    serial_port = None

    serial_port_list = []

    def __init__(self, **kwargs):
        super(Root, self).__init__(**kwargs)
        self.serial_port = SerialPort(self.console_text)
        self.update_comm_ports()
        self.id_commport.values = self.serial_port_list
        self.id_commport.text = '-' if not self.serial_port_list else self.serial_port_list[0]
        self.count = 0

    def update_label(self, *args):
        self.count = self.count + 1
        self.ids.lb.text = str(self.count)

    def stop(self):
        Clock.unschedule(self.update_label)

    def start(self):
        Clock.schedule_interval(self.update_label, 0.5)

    def update_comm_ports(self):
        self.serial_port_list = []
        try:
            from serial.tools.list_ports import comports
        except ImportError:
            return None
        if comports:
            com_ports_list = list(comports())
            for port in com_ports_list:
                self.serial_port_list.append(port[0])

    def update_port(self, dt):  # dt is the delta time
        # update commport options
        self.update_comm_ports()
        self.id_commport.values = self.serial_port_list

    def update_serialread(self, dt):
        if not self.serial_port.print_read_task():
            # exception in read, close port
            self.console_text.text += 'Port {} disconnected or has issue, close it, please retry\n'.format(
                self.serial_port.select_port)
            self.id_switch_serial.text = 'Open'
            self.id_indicator.color = [1, 0, 0, 1]
            self.id_commport.disabled = False
            self.id_baudrate.disabled = False
            self.id_checksum.disabled = False
            self.id_stopbit.disabled = False
            self.id_databit.disabled = False
            self.serial_port.close_port()

    def on_recvencode_change(self, value):
        self.console_text.text += 'receive encoding: {}\n'.format(value)
        if value == 'ASCII':
            self.serial_port.recv_encoding = SerialEncoding.ASCII
        else:
            self.serial_port.recv_encoding = SerialEncoding.HEX
        # self.console_text.text += '{}\n'.format(self.id_recv_encode.state == 'down')

    def on_sendencode_change(self, value):
        self.console_text.text += 'send encoding: {}\n'.format(value)
        if value == 'ASCII':
            self.serial_port.send_encoding = SerialEncoding.ASCII
            try:
                self.send_text.text = HexToByte(self.send_text.text)
            except ValueError:
                self.console_text.text += 'Wrong hex data format in send area, cannot transfer to ASCII\n'
                self.send_text.text = ''
        else:
            self.serial_port.send_encoding = SerialEncoding.HEX
            # make send area into hex string
            self.send_text.text = ByteToHex(self.send_text.text)

    def on_commport_change(self, value):
        self.console_text.text += 'comm port: {} \n'.format(value)
        self.serial_port.select_port = value

    def on_baudrate_change(self, value):
        self.console_text.text += 'baudrate: {} \n'.format(value)
        self.serial_port.baud_rate = int(value)

    def on_databit_change(self, value):
        self.console_text.text += 'data bit: {} \n'.format(value)
        self.serial_port.data_bits = int(value)

    def on_stopbit_change(self, value):
        self.console_text.text += 'stop bit: {} \n'.format(value)
        self.serial_port.stop_bits = int(value)

    def on_checksum_change(self, value):
        self.console_text.text += 'check sum: {} \n'.format(value)
        if value == 'None':
            self.serial_port.checksum_bits = SerialChecksum.Non
        elif value == 'Odd':
            self.serial_port.checksum_bits = SerialChecksum.Odd
        elif value == 'Even':
            self.serial_port.checksum_bits = SerialChecksum.Even

    def switch_serial(self, value):
        # self.console_text.text += str(self.serial_port)
        if value == 'Open':
            if self.serial_port.open_port():
                self.id_switch_serial.text = 'Close'
                self.id_indicator.color = [0, 1, 0, 1]
                self.id_commport.disabled = True
                self.id_baudrate.disabled = True
                self.id_checksum.disabled = True
                self.id_stopbit.disabled = True
                self.id_databit.disabled = True
            else:
                self.console_text.text += 'Port {} open failed, please check\n'.format(self.serial_port.select_port)

        else:
            self.id_switch_serial.text = 'Open'
            self.id_indicator.color = [1, 0, 0, 1]
            self.id_commport.disabled = False
            self.id_baudrate.disabled = False
            self.id_checksum.disabled = False
            self.id_stopbit.disabled = False
            self.id_databit.disabled = False
            self.serial_port.close_port()

    def clear_recvdata(self):
        self.console_text.text = ''

    def clear_senddata(self):
        self.send_text.text = ''

    def send_data(self):
        if not self.serial_port.port_opened:
            self.console_text.text += 'Port not opened yet, please select and click Open.\n'
        else:
            self.serial_port.send(self.send_text.text)

    def on_append_linend_send_change(self, value):
        # self.console_text.text += 'apped line end: {}\n'.format(value)
        self.serial_port.append_linend_send = value

    def on_add_timestamp_change(self, value):
        # self.console_text.text += 'add timestamp: {}\n'.format(value)
        self.serial_port.add_timestamp = value

    def dismiss_popup(self):
        self._popup.dismiss()

    def show_save(self):
        content = SaveDialog(save=self.save, cancel=self.dismiss_popup)
        self._popup = Popup(title="Save file", content=content,
                            size_hint=(0.9, 0.9))
        self._popup.open()

    def save(self, path, filename):
        self.dismiss_popup()
        with open(os.path.join(path, filename), 'wb') as filewriter:
            filewriter.write(self.console_text.text.encode('utf-8'))
        self.console_text.text += ' - - - - - -  - - - - - - \n'
        self.console_text.text += 'File saved at {}\n'.format(os.path.join(path, filename))
        self.console_text.text += ' - - - - - -  - - - - - - \n'


class SerialDebuggerApp(App):
    def build(self):
        self.icon = 'icon.png'
        root = Root()
        Clock.schedule_interval(root.update_port, 1.0)
        Clock.schedule_interval(root.update_serialread, 1.0 / 60)

        return root


# Factory.register('Root', cls=Root)
Factory.register('SaveDialog', cls=SaveDialog)

if __name__ == '__main__':
    SerialDebuggerApp().run()
