from serial import Serial, SerialException
import enum



# if platform == 'android':
#     from usb4a import usb
#     from usbserial4a import serial4a
# else:
#     from serial.tools import list_ports
#     from serial import Serial, SerialException





class SerialEncoding(enum.Enum):
    ASCII = 1
    HEX = 2


class SerialChecksum(enum.Enum):
    Non = 1
    Odd = 2
    Even = 3

class SerialPort():
    port_opened = False
    stop_bits = 1
    data_bits = 8
    checksum_bits = SerialChecksum.Non
    baud_rate = 115200
    recv_encoding = SerialEncoding.ASCII
    send_encoding = SerialEncoding.ASCII
    append_linend_send = False
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
        return 'port: {port}, stop bit: {stopbit}, data bit: {databit}, \
        checksum: {checksum}, baud rate: {baudrate}, recv encode: {recvencode}, \
        send encode: {sendencode}, append line end: {appendlinend}, opened: {opened}'.format(
            port=self.select_port,
            stopbit=self.stop_bits,
            databit=self.data_bits,
            checksum=self.checksum_bits,
            baudrate=self.baud_rate,
            recvencode=self.recv_encoding,
            sendencode=self.send_encoding,
            appendlinend=self.append_linend_send,
            opened=self.port_opened
        )

    def __str__(self) -> str:
        return self.__repr__()

    def open_port(self):
        self._ser.baudrate = self.baud_rate
        self._ser.port = self.select_port
        self._ser.bytesize = self.transfer_bytesize(self.data_bits)
        self._ser.stopbits = self.transfer_stopbits(self.stop_bits)
        self._ser.parity = self.transfer_parity(self.checksum_bits)
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

    def transfer_bytesize(self, bytesize):
        if bytesize == 5:
            return serial.FIVEBITS
        elif bytesize == 6:
            return serial.SIXBITS
        elif bytesize == 7:
            return serial.SEVENBITS
        else:
            return serial.EIGHTBITS

    def transfer_stopbits(self, stopbits):
        if stopbits == 1:
            return serial.STOPBITS_ONE
        else:
            return serial.STOPBITS_TWO

    def transfer_parity(self, checksum):
        if checksum == SerialChecksum.Non:
            return serial.PARITY_NONE
        elif checksum == SerialChecksum.Odd:
            return serial.PARITY_ODD
        elif checksum == SerialChecksum.Even:
            return serial.PARITY_EVEN
        else:
            return serial.PARITY_NONE

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
            except serial.SerialException:
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
        if self.recv_encoding == SerialEncoding.HEX:
            try:
                encoded_data = ''.join(["%02X " % x for x in data]).strip()
                self.console_buffer.text += encoded_data
                self.console_buffer.text += '\n'
            except Exception as e:
                print(e)
                pass
        else:  # self.recv_encoding == SerialEncoding.ASCII:
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
                if self.send_encoding == SerialEncoding.HEX:
                    self._ser.write(HEXStringToBytesArray(data))
                else:  # self.send_encoding == SerialEncoding.ASCII:
                    self._ser.write(data.encode('utf-8'))
            except serial.serialutil.SerialTimeoutException:
                self.console_buffer.text += 'write timeout\n'
            except ValueError:
                self.console_buffer.text += 'Wrong hex data format in send area, cannot transfer to ASCII\n'
