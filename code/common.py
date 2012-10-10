
import struct
import array
import errno
import sys

try:
    import py_sg
except ImportError, e:
    print('You need to install the "py_sg" module.')
    sys.exit(1)



class AvgMax(object):

    __slots__ = ('avg', 'max')

    def __init__(self, avg, max):
        self.avg = avg
        self.max = max



class TrackPoint(object):

    __slots__ = ('timestamp', 'latitude', 'longitude', 'elevation')

    def __init__(self, timestamp, longitude, latitude, elevation):
        self.timestamp = timestamp
        self.longitude = longitude
        self.latitude = latitude
        self.elevation = elevation



class LogPoint(object):

    __slots__ = ('timestamp', 'temperature', 'speed', 'watts', 'cadence',
                 'heartrate', 'airpressure')

    def __init__(self, timestamp, speed, watts=None, cadence=None,
                 heartrate=None, temperature=None, airpressure=None):

        self.timestamp = timestamp
        self.speed = speed
        self.watts = watts
        self.cadence = cadence
        self.heartrate = heartrate
        self.temperature = temperature
        self.airpressure = airpressure



class DataBuffer(object):

    def __init__(self, device, data, rel_offset=0, abs_offset=0,
                 data_len=None):
        self.device = device
        self.data = data
        self.rel_offset = rel_offset
        self.abs_offset = abs_offset
        self.data_len = data_len or self.device.BLOCK_SIZE

    def buffer_from(self, offset):

        return DataBuffer(self.device, self.data, self.rel_offset + offset,
                          self.abs_offset, self.data_len)

    def set_offset(self, offset):
        self.rel_offset += offset

    def read_from(self, offset, length):

        start_offset = self.rel_offset + offset
        end_offset = start_offset + length - 1

        if end_offset >= self.data_len:

            blocks = end_offset / self.device.BLOCK_SIZE

            for b in range(blocks):

                abs_offset = self.abs_offset + end_offset + \
                    b * self.device.BLOCK_SIZE

                block_addr = self.device.offset_to_block(abs_offset)
                self.data.extend(self.device.read_block(block_addr))
                self.data_len += self.device.BLOCK_SIZE

        return self.data[start_offset:start_offset + length]


    def int32_from(self, offset):
        return struct.unpack('i', self.read_from(offset, 4))[0]

    def uint32_from(self, offset):
        return struct.unpack('I', self.read_from(offset, 4))[0]

    def int16_from(self, offset):
        return struct.unpack('h', self.read_from(offset, 2))[0]

    def uint16_from(self, offset):
        return struct.unpack('H', self.read_from(offset, 2))[0]

    def int8_from(self, offset):
        return struct.unpack('b', self.read_from(offset, 1))[0]

    def uint8_from(self, offset):
        return struct.unpack('B', self.read_from(offset, 1))[0]

    def str_from(self, offset, length):
        return self.read_from(offset, length).tostring()



def _scsi_pack_cdb(cmd):

    return struct.pack('{}B'.format(len(cmd)), *cmd)



def _scsi_read10(addr, block_count, reserved_byte=0):

    cdb = [0x28, 0, 0, 0, 0, 0, reserved_byte, 0, 0, 0]


    a = struct.pack('>I', addr)
    cdb[2] = ord(a[0])
    cdb[3] = ord(a[1])
    cdb[4] = ord(a[2])
    cdb[5] = ord(a[3])

    s = struct.pack('>H', block_count)

    cdb[7] = ord(s[0])
    cdb[8] = ord(s[1])

    return _scsi_pack_cdb(cdb)



class DeviceAccess(object):

    BLOCK_SIZE = 512

    def __init__(self, dev_path):

        self.dev_path = dev_path
        self.dev = None


    def open(self):

        try:
            self.dev = open(self.dev_path, 'rb')
        except IOError as e:
            if e.errno == errno.EACCES:
                raise RuntimeError('Failed to open device "{}" '
                                   '(Permission denied).'.format(
                                   self.dev_path))
            raise


    def close(self):
        self.dev.close()
        self.dev = None


    def read_addr(self, addr, block_count=8, read_type=0):


        cdb = _scsi_read10(addr, block_count, reserved_byte=read_type)

        data = py_sg.read(self.dev, cdb, self.BLOCK_SIZE * block_count)

        return array.array('B', data)

