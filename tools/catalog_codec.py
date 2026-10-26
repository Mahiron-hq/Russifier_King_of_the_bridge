"""Read/write the binary sections of an Addressables 1.21 content catalog (catalog.json)."""
import base64
import json
import struct

ASCII, UNICODE, UINT16, UINT32, INT32, HASH128, TYPE, JSON = range(8)


def _obj_len(buf, off):
    t = buf[off]
    if t in (ASCII, UNICODE):
        return 5 + struct.unpack_from("<i", buf, off + 1)[0]
    if t == UINT16:
        return 3
    if t in (UINT32, INT32):
        return 5
    if t == HASH128:
        return 2 + buf[off + 1]
    if t == TYPE:
        n1 = buf[off + 1]
        n2 = buf[off + 2 + n1]
        return 3 + n1 + n2
    if t == JSON:
        n1 = buf[off + 1]
        n2 = buf[off + 2 + n1]
        o = off + 3 + n1 + n2
        return o + 4 + struct.unpack_from("<i", buf, o)[0] - off
    raise ValueError(f"unknown object type {t} at {off}")


def decode_obj(raw):
    t = raw[0]
    if t == ASCII:
        return raw[5:].decode("ascii")
    if t == UNICODE:
        return raw[5:].decode("utf-16-le")
    if t == UINT16:
        return struct.unpack_from("<H", raw, 1)[0]
    if t == UINT32:
        return struct.unpack_from("<I", raw, 1)[0]
    if t == INT32:
        return struct.unpack_from("<i", raw, 1)[0]
    if t == JSON:
        n1 = raw[1]
        n2 = raw[2 + n1]
        o = 3 + n1 + n2
        return json.loads(raw[o + 4:].decode("utf-16-le"))
    return raw


def encode_str(s):
    try:
        b = s.encode("ascii")
        return bytes([ASCII]) + struct.pack("<i", len(b)) + b
    except UnicodeEncodeError:
        b = s.encode("utf-16-le")
        return bytes([UNICODE]) + struct.pack("<i", len(b)) + b


def encode_json(asm, cls, obj):
    a, c = asm.encode("ascii"), cls.encode("ascii")
    j = json.dumps(obj, separators=(",", ":")).encode("utf-16-le")
    return bytes([JSON, len(a)]) + a + bytes([len(c)]) + c + struct.pack("<i", len(j)) + j


class Catalog:
    """Index-based model: keys[i] is raw bytes; buckets[i] lists entry indices for key i."""

    def __init__(self, path):
        self.path = path
        self.doc = json.load(open(path, encoding="utf-8"))
        kd = base64.b64decode(self.doc["m_KeyDataString"])
        bd = base64.b64decode(self.doc["m_BucketDataString"])
        ed = base64.b64decode(self.doc["m_EntryDataString"])
        xd = base64.b64decode(self.doc["m_ExtraDataString"])

        nb = struct.unpack_from("<i", bd, 0)[0]
        o = 4
        self.keys, self.buckets = [], []
        for _ in range(nb):
            koff, n = struct.unpack_from("<ii", bd, o)
            o += 8
            self.keys.append(kd[koff:koff + _obj_len(kd, koff)])
            self.buckets.append(list(struct.unpack_from(f"<{n}i", bd, o)))
            o += 4 * n

        ne = struct.unpack_from("<i", ed, 0)[0]
        xoffs = {}
        self.extras = []
        self.entries = []
        for i in range(ne):
            iid, prov, dep, dh, data, pk, rt = struct.unpack_from("<7i", ed, 4 + 28 * i)
            if data >= 0:
                if data not in xoffs:
                    xoffs[data] = len(self.extras)
                    self.extras.append(xd[data:data + _obj_len(xd, data)])
                data = xoffs[data]
            self.entries.append([iid, prov, dep, dh, data, pk, rt])
        self._orig = (kd, bd, ed, xd)

    def key(self, i):
        return decode_obj(self.keys[i])

    def extra(self, i):
        return decode_obj(self.extras[i])

    def find_key(self, value):
        for i, raw in enumerate(self.keys):
            if decode_obj(raw) == value:
                return i
        return -1

    def add_key(self, raw):
        self.keys.append(raw)
        self.buckets.append([])
        return len(self.keys) - 1

    def key_index(self, value):
        """Return the bucket index for a string key, creating it if absent."""
        i = self.find_key(value)
        return i if i >= 0 else self.add_key(encode_str(value))

    def add_internal_id(self, s):
        ids = self.doc["m_InternalIds"]
        if s in ids:
            return ids.index(s)
        ids.append(s)
        return len(ids) - 1

    def encode(self):
        kd = bytearray(struct.pack("<i", len(self.keys)))
        koffs = []
        for raw in self.keys:
            koffs.append(len(kd))
            kd += raw
        bd = bytearray(struct.pack("<i", len(self.buckets)))
        for koff, ents in zip(koffs, self.buckets):
            bd += struct.pack("<ii", koff, len(ents)) + struct.pack(f"<{len(ents)}i", *ents)
        xd = bytearray()
        xoffs = []
        for raw in self.extras:
            xoffs.append(len(xd))
            xd += raw
        ed = bytearray(struct.pack("<i", len(self.entries)))
        for iid, prov, dep, dh, data, pk, rt in self.entries:
            ed += struct.pack("<7i", iid, prov, dep, dh, xoffs[data] if data >= 0 else -1, pk, rt)
        return bytes(kd), bytes(bd), bytes(ed), bytes(xd)

    def save(self, path):
        kd, bd, ed, xd = self.encode()
        doc = dict(self.doc)
        doc["m_KeyDataString"] = base64.b64encode(kd).decode()
        doc["m_BucketDataString"] = base64.b64encode(bd).decode()
        doc["m_EntryDataString"] = base64.b64encode(ed).decode()
        doc["m_ExtraDataString"] = base64.b64encode(xd).decode()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(doc, f, separators=(",", ":"))
