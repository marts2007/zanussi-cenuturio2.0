import socket
from struct import *
import logging
_LOGGER = logging.getLogger(__name__)

class Status():
    def __init__(self,cb):
        self.temp = None
        self.mode = None
        self.temp_target = None
        self.time = None
        self.timer = None
        self.cb = cb
    ##добавить отправку "aa03081004c9" (запрос апдейтов)
    def run_server(self):
        sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        sock.bind(('192.168.0.3', 37008))
        print("UDP server up and listening")
        while (True):
            try:
                data, addr = sock.recvfrom(1024)
                consumesData = processUdpData(data, addr)
                if consumesData:
                    if consumesData['source_ip'] == '192.168.0.100' and consumesData['protocol'] == 6:
                        result = parce_waterheater_data(consumesData['data'])
                        if result:
                            data = parce_waterheater_data(consumesData['data'])
                            self.temp = data['temp']
                            self.mode = data['mode']
                            self.temp_target = data['temp_target']
                            self.time = data['time']
                            self.timer = data['timer']
                            self.cb()
            except Exception as e:
                _LOGGER.warning(e)



def parce_waterheater_data(data):
    try:
        packet = bytearray.fromhex(data)
        if len(packet) < 9:
            return None
        if packet[0:2] != bytearray.fromhex('aa0a'):
            return None
        mode = {
            '0x0': 'off',
            '0x1': '700W',
            '0x2': '1300W',
            '0x3': '2000W',
            '0x4': 'timer',
            '0x5': 'No frost'
        }
        # [aa][0a][09/88][mode][temp_current][temp_target][hh][mm][timer_h][timer_m][summ]
        current_mode = hex(packet[3])
        data = {
            'mode': mode[current_mode] if current_mode in mode else current_mode,
            'temp': packet[4],
            'temp_target': packet[5],
            'time': f'{packet[6]}:{packet[7]}',
            'timer': f'{packet[8]}:{packet[9]}'
        }
        return data
    except Exception as e:
        _LOGGER.warning(e)


def eth_addr(a):
    b = "%.2x:%.2x:%.2x:%.2x:%.2x:%.2x" % (a[0], a[1], a[2], a[3], a[4], a[5])
    return b


def getTagType(type):
    types = {
        0x00: "TAG_PADDING",
        0x01: "TAG_END",
        0x0A: "TAG_RAW_RSSI",
        0x0B: "TAG_SNR",
        0x0C: "TAG_DATA_RATE",
        0x0D: "TAG_TIMESTAMP",
        0X0F: "TAG_CONTENTION_FREE",
        0X10: "TAG_DECRYPTED",
        0X11: "TAG_FCS_ERROR",
        0X12: "TAG_RX_CHANNEL",
        0X28: "TAG_PACKET_COUNT",
        0X29: "TAG_RX_FRAME_LENGTH",
        0X3C: "TAG_WLAN_RADIO_HDR_SERIAL"
    }
    return types[type]


def processTag(tag, details=False):
    currentTag = None
    i = 0
    while currentTag not in [0x00, 0x01]:
        currentTag = tag[i]
        # tagType = getTagType(ord(str(tag[0])))
        tagType = getTagType(tag[0])
        tagLength = 0
        if (tagType not in ["TAG_END", "TAG_PADDING"]):
            tagLength = ord(tag[1])

        i = i + 1 + tagLength
        if details:
            print("tag type: %r" % tagType)
            print("tag length: %r" % tagLength)
    return i


def processUdpData(data, addr):
    headers = data[0:4]
    tags = data[4:]
    protocol = ord(str(headers[2])) * 256 + ord(str(headers[3]))
    # protocolStr = getProtocol(protocol)
    data_raw = data.hex(' ')
    tagsLength = processTag(tags)
    # print "tags length: %r" % tagsLength
    eth_header = tags[tagsLength:(14 + tagsLength)]
    eth_data = tags[(14 + tagsLength):]
    packet_data = eth_data[40:]
    packet_data = packet_data.hex(' ')
    eth = unpack('!6s6sH', eth_header)
    eth_protocol = socket.ntohs(eth[2])
    mac_details = 'Destination MAC : ' + eth_addr(eth_header[0:6]) + ' Source MAC : ' + eth_addr(
        eth_header[6:12]) + ' Protocol : ' + str(eth_protocol)

    packet = tags[15:]
    # hexStr = "".join(tags[21:])
    iph = unpack('!BBHHHBBH4s4s', packet[:20])
    # version_ihl = iph[0]
    # version = version_ihl >> 4
    # ihl = version_ihl & 0xF

    # iph_length = ihl * 4

    ttl = iph[5]
    protocol = iph[6]
    s_addr = socket.inet_ntoa(iph[8])
    d_addr = socket.inet_ntoa(iph[9])
    connection_detail = ' TTL : ' + str(ttl) + ' Protocol : ' + str(protocol) + ' Source Address : ' + str(
        s_addr) + ' Destination Address : ' + str(d_addr)
    s = connection_detail
    return_obj = {
        'source_mac': eth_addr(eth_header[6:12]),
        'source_ip': str(s_addr),
        'dest_ip': str(d_addr),
        'data': packet_data,
        'protocol': protocol
    }
    if len(packet_data):
        return return_obj
    return None