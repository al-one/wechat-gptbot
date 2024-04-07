import base64
import re
import subprocess

def decode_paths(str, wxid=None):
    bin = base64.b64decode(str)
    paths = {}
    cursor = index = 0
    while cursor < len(bin):
        try:
            _, cursor = parse_varint(bin, cursor)
            value, cursor = parse_string(bin, cursor)
            if 'FileStorage' in value:
                if wxid:
                    pos = value.find(wxid)
                    if pos > 0:
                        value = value[pos:]
                value = value.replace('\\', '/').replace("'", '')
                paths[index] = value
                if mat := re.search(r'MsgAttach/\w+/(\w+)', value):
                    type = mat.group(1).lower()
                    paths[type] = value
                index += 1
        except Exception:
            pass
    return paths

def parse_varint(data, cursor):
    shift = 0
    result = 0
    for i in range(cursor, len(data)):
        byte = data[i]
        result |= (byte & 0x7F) << shift
        shift += 7
        if not byte & 0x80:
            return result, i + 1

def parse_string(data, cursor):
    length, cursor = parse_varint(data, cursor)
    ended = cursor + length
    value = data[cursor:ended]
    return value.decode('utf-8'), ended

def via_protoc(str):
    bin = base64.b64decode(str)
    process = subprocess.Popen(
        ['protoc', '--decode_raw'],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    out = None
    try:
        out, _ = process.communicate(bin)
    except OSError:
        pass
    finally:
        if process.poll() != 0:
            process.wait()
    if out:
        return out.decode()
    return out