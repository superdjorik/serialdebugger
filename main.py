from kivy.uix.floatlayout import FloatLayout
from kivy.factory import Factory
from kivy.properties import ObjectProperty, ListProperty
from kivy.uix.widget import Widget
from kivy.clock import Clock
from kivy.utils import platform
import datetime
from kivymd.app import MDApp

if platform == 'android':
    from usb4a import usb
    from usbserial4a import serial4a
else:
    from serial.tools import list_ports
    from serial import Serial, SerialException, serialutil


class Indicator(Widget):
    color = ListProperty([1, 0, 0, 1])
    pass


class SerialPort():
    port_opened = False
    stop_bits = 1
    data_bits = 8
    baud_rate = 115200
    add_timestamp = False
    select_port = ''
    console_buffer = None
    time_counter = 0
    last_read_counter = 0
    inbuff_number = 0

    def __init__(self, console_buffer, read_timeout=100 * 60 / 1000):  # default read timeout 100ms
        self._ser = Serial()
        self.console_buffer = console_buffer
        self.read_timeout = read_timeout

    def __repr__(self) -> str:
        return 'port: {port}, stop bit: {stopbit}, data bit: {databit}, ' \
               'checksum: {checksum}, baud rate: {baudrate}, ' \
               'opened: {opened}'.format(
            port=self.select_port,
            stopbit=self.stop_bits,
            databit=self.data_bits,
            checksum=self.checksum_bits,
            baudrate=self.baud_rate,
            opened=self.port_opened
        )

    def __str__(self) -> str:
        return self.__repr__()

    def open_port(self):
        self._ser.baudrate = self.baud_rate
        self._ser.port = self.select_port
        try:
            self._ser.open()
        except SerialException:
            self.close_port()
            return False
        self.time_counter = 0
        self.last_read_counter = 0
        self.port_opened = self._ser.is_open
        return self._ser.is_open

    def close_port(self):
        self._ser.close()
        self.port_opened = False
        return True

    def print_read_task(self):
        if self.port_opened:
            # increment at 1ms interval
            self.time_counter += 1
            try:
                read_waiting_num = self._ser.in_waiting
                if read_waiting_num > 0:
                    if self.inbuff_number != read_waiting_num:
                        # keep counters updated and same
                        self.last_read_counter = self.time_counter
                        self.inbuff_number = read_waiting_num
                    else:
                        # counters are same, check timeout condition
                        if self.time_counter - self.last_read_counter >= self.read_timeout:
                            # print all the data in the buff, output is bytes, need decode
                            self.print_encoded_data(self._ser.read(read_waiting_num))
                            # keep counters updated and same
                            self.last_read_counter = self.time_counter
                            # reset the counter
                            self.inbuff_number = 0
            except SerialException:
                self.close_port()
                return False
            except OSError:
                self.close_port()
                return False
            except Exception as e:
                print(e)
                return False
        return True

    def print_encoded_data(self, data):
        if self.add_timestamp:
            now = datetime.datetime.now()
            self.console_buffer.text += now.strftime("%H:%M:%S.%f")[:-3] + '    '
        if len(data) > 0:
            try:
                encoded_data = data.decode('utf-8')
            except UnicodeDecodeError:
                encoded_data = "wrong format to decode, show hexstring instead:\n"
                encoded_data += ''.join(["%02X " % x for x in data]).strip()
            except Exception as e:
                print(e)
                pass
            self.console_buffer.text += encoded_data
            if encoded_data[-1] != '\n' and encoded_data[-1] != '\r':
                self.console_buffer.text += '\n'

    def send(self, data):
        if self.port_opened:
            try:
                self._ser.write(data.encode('utf-8'))
            except serialutil.SerialTimeoutException:
                self.console_buffer.text += 'write timeout\n'
            except ValueError:
                self.console_buffer.text += 'Wrong hex data format in send area, cannot transfer to ASCII\n'


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

    # def update_comm_ports(self):
    #     self.serial_port_list = []
    #     try:
    #         from serial.tools.list_ports import comports
    #     except ImportError:
    #         return None
    #     if comports:
    #         com_ports_list = list(comports())
    #         for port in com_ports_list:
    #             self.serial_port_list.append(port[0])

    def update_comm_ports(self):
        self.serial_port_list = []

        if platform == 'android':
            usb_device_list = usb.get_usb_device_list()
            self.serial_port_list = [
                device.getDeviceName() for device in usb_device_list
            ]
        else:
            usb_device_list = list_ports.comports()
            self.serial_port_list = [port.device for port in usb_device_list]
        #
        #
        # try:
        #     from serial.tools.list_ports import comports
        # except ImportError:
        #     return None
        # if comports:
        #     com_ports_list = list(comports())
        #     for port in com_ports_list:
        #         self.serial_port_list.append(port[0])

    def update_port(self, dt):  # dt is the delta time
        # update commport options
        self.update_comm_ports()
        self.id_commport.values = self.serial_port_list

    def update_serialread(self, dt):
        if not self.serial_port.print_read_task():
            # exception in read, close port
            self.console_text.text += 'Порт {} отключён. Переподключитесь снова\n'.format(
                self.serial_port.select_port)
            self.id_switch_serial.text = 'Подключиться'
            self.id_indicator.color = [1, 0, 0, 1]
            self.id_commport.disabled = False
            self.id_baudrate.disabled = False
            self.serial_port.close_port()


    def on_commport_change(self, value):
        self.console_text.text += 'Порт: {} \n'.format(value)
        self.serial_port.select_port = value

    def on_baudrate_change(self, value):
        self.console_text.text += 'Скорость: {} \n'.format(value)
        self.serial_port.baud_rate = int(value)

    def switch_serial(self, value):
        # self.console_text.text += str(self.serial_port)
        if value == 'Подключиться':
            if self.serial_port.open_port():
                self.id_switch_serial.text = 'Отключиться'
                self.id_indicator.color = [0, 1, 0, 1]
                self.id_commport.disabled = True
                self.id_baudrate.disabled = True
            else:
                self.console_text.text += '{} подключение к порту завершилось ошибкой\n'.format(self.serial_port.select_port)

        else:
            self.id_switch_serial.text = 'Подключиться'
            self.id_indicator.color = [1, 0, 0, 1]
            self.id_commport.disabled = False
            self.id_baudrate.disabled = False
            self.serial_port.close_port()

    def clear_recvdata(self):
        self.console_text.text = ''

    def send_data(self):
        if not self.serial_port.port_opened:
            self.console_text.text += 'Устройство ещё не подключено, подключитесь на вкладке "Настройка"\n'
        else:
            self.serial_port.send(self.send_text.text)

    def on_add_timestamp_change(self, value):
        # self.console_text.text += 'add timestamp: {}\n'.format(value)
        self.serial_port.add_timestamp = value

class SerialDebuggerApp(MDApp):
    def build(self):
        self.theme_cls.material_style = "M3"
        self.theme_cls.theme_style = "Dark"
        # self.icon = 'icon.png'
        root = Root()
        Clock.schedule_interval(root.update_port, 1.0)
        Clock.schedule_interval(root.update_serialread, 1.0 / 60)
        return root


# Factory.register('Root', cls=Root)
# Factory.register('SaveDialog', cls=SaveDialog)

if __name__ == '__main__':
    SerialDebuggerApp().run()
