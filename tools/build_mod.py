"""Applies the Russian translation to a clean copy of King of the Bridge.

Usage:
    build_mod.py <game_dir> <settings_json>

<game_dir> must hold an unmodified "King of the Bridge_Data" folder; it is patched in place. The installer ships the
difference between that copy and the original. <settings_json> receives the game's first-run settings with Russian
selected, which the installer writes when the player has never started the game.
"""
import copy
import hashlib
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import zlib

import UnityPy
from PIL import Image
from UnityPy.helpers.TypeTreeGenerator import TypeTreeGenerator

from catalog_codec import Catalog
from font_patch import font_characters, patch_game_font

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRANSLATIONS = os.path.join(REPO, "translations", "ru.json")
FONT_BUNDLE = os.path.join(REPO, "assets", "fonts", "alagard-unicode-tmp")
SPRITES = os.path.join(REPO, "assets", "sprites_ru")
PAGES_DIR = os.path.join(REPO, "assets", "pages_ru")
HELPER_DLL = os.path.join(REPO, "mod", "KotbRussian", "bin", "Release", "netstandard2.1", "KotbRussian.dll")
CODE_PATCHER = os.path.join(REPO, "mod", "KotbPatcher", "bin", "Release", "net48", "KotbPatcher.exe")

UNITY_VERSION = "2022.3.5f1"
CODE = "ru"
LOCALE_NAME = "Russian (ru)"
LANGUAGE_LABEL = "Русский"
LANGUAGE_INDEX = 2.0

DATA = "King of the Bridge_Data"
AA = os.path.join(DATA, "StreamingAssets", "aa")
BUNDLES = os.path.join(AA, "StandaloneWindows64")
RUNTIME_PATH = "{UnityEngine.AddressableAssets.Addressables.RuntimePath}\\StandaloneWindows64\\"

MANAGED = os.path.join(DATA, "Managed")
NEW_BUNDLES = {
    "locales": "localization-locales-russian(ru)_assets_all.bundle",
    "strings": "localization-string-tables-russian(ru)_assets_all.bundle",
    "assets": "localization-asset-tables-russian(ru)_assets_all.bundle",
    "pages": "localization-assets-russian(ru)_assets_all.bundle",
}
SRC_BUNDLES = {
    "locales": "localization-locales_assets_all.bundle",
    "strings": "localization-string-tables-english(en)_assets_all.bundle",
    "assets": "localization-asset-tables-english(en)_assets_all.bundle",
    "pages": "localization-assets-english(en)_assets_all.bundle",
    "shared": "localization-assets-shared_assets_all.bundle",
}
PAGE_PATHS = ("Assets/03Sprites/Rulebook/PageSprites/pages_english/", "Assets/SecretPages/english/")
LANGUAGE_SETTING_PATH_ID = 96
GAME_FONT_PATH_ID = 155
GAME_FONT_MATERIAL_PATH_ID = 3
GAME_FONT_ATLAS_PATH_ID = 16
PIECE_GENDER_TYPES = {"PawnKey": "Pawn", "KnightKey": "Knight", "BishopKey": "Bishop", "RookKey": "Rook",
                      "QueenKey": "Queen", "KingKey": "King", "LandmineKey": "Landmine", "CastleKey": "Castle"}


def md5(s):
    return hashlib.md5(s.encode("utf-8")).hexdigest()


def signed32(n):
    return n - (1 << 32) if n >= 1 << 31 else n


class PatchError(Exception):
    """A condition that stops the build before it produces a broken mod."""


def load_shared_keys(game):
    """Map table collection name -> {key name: key id}."""
    env = UnityPy.load(os.path.join(game, BUNDLES, SRC_BUNDLES["shared"]))
    result = {}
    for o in env.objects:
        if o.type.name == "MonoBehaviour":
            tt = o.read_typetree()
            if "m_TableCollectionName" in tt:
                result[tt["m_TableCollectionName"]] = {e["m_Key"].strip(): e["m_Id"] for e in tt["m_Entries"]}
    return result


def ru_asset_guid(guid):
    return md5("ru-asset:" + guid)


def ru_asset_path(path):
    return path.replace("/pages_english/", "/pages_russian/").replace("/SecretPages/english/", "/SecretPages/russian/")


def retarget_bundle(env, bundle_file_name):
    """Give a cloned bundle its own CAB and AssetBundle names so Unity can load it next to the source.

    Any .resS stream file is dropped, so callers must inline the texture data that lived there.
    """
    bundle = env.file
    sf = next(f for f in bundle.files.values() if hasattr(f, "objects"))
    new_cab = "CAB-" + md5(bundle_file_name)
    bundle.files = {new_cab: sf}
    asset_name = md5("ru:" + bundle_file_name) + ".bundle"
    for o in sf.objects.values():
        if o.type.name == "AssetBundle":
            tt = o.read_typetree()
            tt["m_Name"] = asset_name
            tt["m_AssetBundleName"] = asset_name
            return o, tt
    raise RuntimeError("bundle has no AssetBundle object")


def build_table_bundle(game, kind, translations, shared_keys):
    env = UnityPy.load(os.path.join(game, BUNDLES, SRC_BUNDLES[kind]))
    ab_obj, ab = retarget_bundle(env, NEW_BUNDLES[kind])
    sf = ab_obj.assets_file
    renamed = 0
    for o in sf.objects.values():
        if o.type.name != "MonoBehaviour":
            continue
        tt = o.read_typetree()
        collection = tt["m_Name"].rsplit("_", 1)[0]
        tt["m_Name"] = f"{collection}_{CODE}"
        tt["m_LocaleId"]["m_Code"] = CODE
        if kind == "strings":
            ids = {v: k for k, v in shared_keys[collection].items()}
            table_tr = translations.get(collection, {})
            for entry in tt["m_TableData"]:
                key = ids.get(entry["m_Id"])
                if key in table_tr:
                    entry["m_Localized"] = table_tr[key]
                    renamed += 1
        else:
            for entry in tt["m_TableData"]:
                guid, bracket, sub = entry["m_Localized"].partition("[")
                if guid:
                    entry["m_Localized"] = ru_asset_guid(guid) + bracket + sub
                    renamed += 1
        o.save_typetree(tt)
    ab["m_Container"] = [(p.replace("_en.asset", f"_{CODE}.asset"), info) for p, info in ab["m_Container"]]
    ab_obj.save_typetree(ab)
    data = env.file.save(packer="lz4")
    print(f"{kind}: {len(data)} bytes, translated entries: {renamed}")
    return data, [c[0] for c in ab["m_Container"]]


def full_rect_render_data(tt):
    """Replace a sprite's tight mesh (traced around the English artwork) with a full-rect quad.

    Keeps the original vertex layout: stream 0 = float3 position, stream 1 = float2 uv plus
    float4 blend weights and uint4 blend indices (40 bytes per vertex).
    """
    rd = tt["m_RD"]
    channels = rd["m_VertexData"]["m_Channels"]
    if not (channels[0]["dimension"] == 3 and channels[4]["stream"] == 1 and channels[13]["offset"] == 24):
        raise RuntimeError(f"{tt['m_Name']}: unexpected sprite vertex layout")
    w, h = tt["m_Rect"]["width"], tt["m_Rect"]["height"]
    ppu = tt["m_PixelsToUnits"]
    px, py = tt["m_Pivot"]["x"] * w, tt["m_Pivot"]["y"] * h
    corners = [(0, 0), (0, h), (w, h), (w, 0)]
    positions = b"".join(struct.pack("<3f", (x - px) / ppu, (y - py) / ppu, 0.0) for x, y in corners)
    attribs = b"".join(struct.pack("<2f4f4I", x / w, y / h, 0, 0, 0, 0, 0, 0, 0, 0) for x, y in corners)
    rd["m_VertexData"]["m_VertexCount"] = 4
    rd["m_VertexData"]["m_DataSize"] = positions + attribs
    rd["m_IndexBuffer"] = list(struct.pack("<6H", 0, 1, 2, 2, 3, 0))
    sub = rd["m_SubMeshes"][0]
    sub.update(firstByte=0, indexCount=6, firstVertex=0, vertexCount=4, baseVertex=0)
    sub["localAABB"] = {"m_Center": {"x": (w / 2 - px) / ppu, "y": (h / 2 - py) / ppu, "z": 0.0},
                        "m_Extent": {"x": w / 2 / ppu, "y": h / 2 / ppu, "z": 0.0}}
    rd["textureRect"] = {"x": 0.0, "y": 0.0, "width": w, "height": h}
    rd["textureRectOffset"] = {"x": 0.0, "y": 0.0}
    rd["settingsRaw"] = rd["settingsRaw"] & ~64  # mesh type: Tight -> FullRect


def build_pages_bundle(game):
    """Clone the English page bundle and swap in the translated page images that exist."""
    env = UnityPy.load(os.path.join(game, BUNDLES, SRC_BUNDLES["pages"]))
    sf = next(f for f in env.file.files.values() if hasattr(f, "objects"))
    replaced, kept = [], []
    for o in sf.objects.values():
        if o.type.name == "Sprite":
            tt = o.read_typetree()
            full_rect_render_data(tt)
            o.save_typetree(tt)
            continue
        if o.type.name != "Texture2D":
            continue
        tex = o.read()
        png = os.path.join(PAGES_DIR, tex.m_Name + ".png")
        if os.path.exists(png):
            img = Image.open(png).convert("RGBA")
            if img.size != (tex.m_Width, tex.m_Height):
                raise PatchError(f"{png}: size {img.size}, expected {tex.m_Width}x{tex.m_Height}")
            data = img.transpose(Image.FLIP_TOP_BOTTOM).tobytes()
            replaced.append(tex.m_Name)
        else:
            data = tex.get_image_data()
            kept.append(tex.m_Name)
        tex.image_data = data
        tex.m_CompleteImageSize = len(data)
        tex.m_StreamData.path, tex.m_StreamData.offset, tex.m_StreamData.size = "", 0, 0
        tex.save()
    ab_obj, ab = retarget_bundle(env, NEW_BUNDLES["pages"])
    ab["m_Container"] = [(ru_asset_path(p), info) for p, info in ab["m_Container"]]
    ab_obj.save_typetree(ab)
    data = env.file.save(packer="lz4")
    print(f"pages: {len(data)} bytes, translated: {len(replaced)}, still English: {sorted(kept)}")
    return data


def build_locale_bundle(game):
    env = UnityPy.load(os.path.join(game, BUNDLES, SRC_BUNDLES["locales"]))
    ab_obj, ab = retarget_bundle(env, NEW_BUNDLES["locales"])
    sf = ab_obj.assets_file
    locales = {o.read_typetree()["m_Identifier"]["m_Code"]: o
               for o in sf.objects.values() if o.type.name == "MonoBehaviour"}
    keep = locales["nl"]
    del sf.objects[locales["en"].path_id]
    tt = keep.read_typetree()
    tt["m_Name"] = LOCALE_NAME
    tt["m_LocaleName"] = LOCALE_NAME
    tt["m_Identifier"]["m_Code"] = CODE
    tt["m_SortOrder"] = 2
    keep.save_typetree(tt)
    script = tt["m_Script"]
    ab["m_PreloadTable"] = [script, {"m_FileID": 0, "m_PathID": keep.path_id}]
    ab["m_Container"] = [(f"Assets/Localisation/{LOCALE_NAME}.asset",
                          {"preloadIndex": 0, "preloadSize": 2,
                           "asset": {"m_FileID": 0, "m_PathID": keep.path_id}})]
    ab_obj.save_typetree(ab)
    data = env.file.save(packer="lz4")
    print(f"locales: {len(data)} bytes")
    return data


def patch_catalog(game, sizes):
    path = os.path.join(game, AA, "catalog.json")
    cat = Catalog(path)
    ids = cat.doc["m_InternalIds"]

    def entry_by_id(internal_id):
        for i, e in enumerate(cat.entries):
            if ids[e[0]] == internal_id:
                return i
        raise KeyError(internal_id)

    def keys_of(entry_idx):
        return [k for k, ents in enumerate(cat.buckets) if entry_idx in ents]

    def add_entry(fields, keys):
        cat.entries.append(fields)
        idx = len(cat.entries) - 1
        for k in keys:
            cat.buckets[cat.key_index(k)].append(idx)
        return idx

    if any(ids[e[0]].endswith(NEW_BUNDLES["locales"]) for e in cat.entries):
        raise PatchError("catalog already contains Russian entries; the game copy is not clean")

    shared_idx = entry_by_id(RUNTIME_PATH + SRC_BUNDLES["shared"])
    src_bundle_idx = entry_by_id(RUNTIME_PATH + SRC_BUNDLES["strings"])
    tmpl = cat.entries[src_bundle_idx]
    tmpl_raw = cat.extras[tmpl[4]]
    header_len = 3 + tmpl_raw[1] + tmpl_raw[2 + tmpl_raw[1]]
    header = tmpl_raw[:header_len]

    bundle_entry, bundle_pk, dep_key = {}, {}, {}
    for kind, name in NEW_BUNDLES.items():
        h = md5(name + str(sizes[kind]))
        opts = cat.extra(tmpl[4])
        opts.update(m_Hash=h, m_Crc=0, m_BundleSize=sizes[kind], m_BundleName=md5("ru:" + name))
        j = json.dumps(opts, separators=(",", ":")).encode("utf-16-le")
        cat.extras.append(header + len(j).to_bytes(4, "little") + j)
        pk = f"{name[:-len('.bundle')]}_{h}.bundle"
        pk_idx = cat.key_index(pk)
        fields = [cat.add_internal_id(RUNTIME_PATH + name), tmpl[1], -1, 0,
                  len(cat.extras) - 1, pk_idx, tmpl[6]]
        bundle_entry[kind] = add_entry(fields, [pk])
        bundle_pk[kind] = pk_idx

    for kind in ("strings", "assets"):
        deps = [bundle_entry[kind], shared_idx]
        key = str(signed32(zlib.crc32(f"ru-deps-{kind}".encode())))
        k = cat.key_index(key)
        cat.buckets[k] = deps
        dep_key[kind] = (k, signed32(zlib.crc32(json.dumps(deps).encode())))

    nl_locale = entry_by_id("Assets/Localisation/Dutch (nl).asset")
    e = cat.entries[nl_locale]
    add_entry([cat.add_internal_id(f"Assets/Localisation/{LOCALE_NAME}.asset"), e[1],
               bundle_pk["locales"], signed32(zlib.crc32(b"ru-locale")), e[4],
               cat.key_index(LOCALE_NAME), e[6]],
              [LOCALE_NAME, md5("locale:" + CODE), "Locale"])

    added = 0
    for i, e in enumerate(list(cat.entries)):
        iid = ids[e[0]]
        if not (iid.startswith("Assets/Localisation/Tables/") and iid.endswith("_en.asset")):
            continue
        kind = "strings" if cat.doc["m_resourceTypes"][e[6]]["m_ClassName"].endswith("StringTable") else "assets"
        table = iid.rsplit("/", 1)[1][:-len("_en.asset")]
        new_keys = []
        for k in keys_of(i):
            v = cat.key(k)
            if v == "Locale-en":
                new_keys.append(f"Locale-{CODE}")
            elif v == f"{table}_en":
                new_keys.append(f"{table}_{CODE}")
            elif v == "Preload":
                new_keys.append(v)
            elif isinstance(v, str) and len(v) == 32:
                new_keys.append(md5(f"table:{table}_{CODE}"))
            else:
                raise RuntimeError(f"unexpected key {v!r} on {iid}")
        dk, dh = dep_key[kind]
        add_entry([cat.add_internal_id(iid.replace("_en.asset", f"_{CODE}.asset")), e[1], dk, dh,
                   e[4], cat.key_index(f"{table}_{CODE}"), e[6]], new_keys)
        added += 1

    pages = 0
    page_dep_hash = signed32(zlib.crc32(b"ru-pages"))
    for i, e in enumerate(list(cat.entries)):
        iid = ids[e[0]]
        if not iid.startswith(PAGE_PATHS):
            continue
        new_keys = []
        for k in keys_of(i):
            v = cat.key(k)
            if v == "Locale-en":
                new_keys.append(f"Locale-{CODE}")
            elif isinstance(v, str) and re.fullmatch(r"[0-9a-f]{32}", v):
                new_keys.append(ru_asset_guid(v))
            else:
                new_keys.append(f"{v}_{CODE}")
        name = f"{cat.key(e[5])}_{CODE}"
        add_entry([cat.add_internal_id(ru_asset_path(iid)), e[1], bundle_pk["pages"], page_dep_hash,
                   e[4], cat.key_index(name), e[6]], new_keys)
        pages += 1
    cat.save(path)
    print(f"catalog: +{len(NEW_BUNDLES)} bundles, +1 locale, +{added} tables, +{pages} page assets")


def patch_sharedassets0(game, generator):
    """Add the language option and swap in the Cyrillic font (both objects live in sharedassets0)."""
    path = os.path.join(game, DATA, "sharedassets0.assets")
    env = UnityPy.load(path)
    env.typetree_generator = generator
    obj = next(o for o in env.objects if o.path_id == LANGUAGE_SETTING_PATH_ID)
    tt = obj.read_typetree()
    if tt.get("settingID") != "language":
        raise PatchError("unexpected object at language setting path id")
    if any(o["settingValue"] == [LANGUAGE_INDEX] for o in tt["settingOptions"]):
        raise PatchError("language option already present; the game copy is not clean")
    opt = copy.deepcopy(tt["settingOptions"][1])
    opt["displayText"] = LANGUAGE_LABEL
    opt["localizedString"]["m_TableReference"]["m_TableCollectionName"] = ""
    opt["localizedString"]["m_TableEntryReference"]["m_KeyId"] = 0
    opt["settingValue"] = [LANGUAGE_INDEX]
    tt["settingOptions"].append(opt)
    obj.save_typetree(tt)
    chars, ellipsis = patch_game_font(env, GAME_FONT_PATH_ID, GAME_FONT_MATERIAL_PATH_ID,
                                      GAME_FONT_ATLAS_PATH_ID, FONT_BUNDLE)
    data = env.file.save()
    with open(path, "wb") as f:
        f.write(data)
    print("sharedassets0: language options", [o["displayText"] for o in tt["settingOptions"]])
    print(f"sharedassets0: font replaced, {chars} characters, ellipsis composed: {ellipsis}")


def table_strings(final):
    """String-table texts, with the counted credits lines turned into SmartFormat plural selectors."""
    tables = copy.deepcopy(final["tables"])
    for key, p in final["plurals"].items():
        forms = "|".join(p[f].replace("{n}", "{}") for f in ("one", "few", "many"))
        tables["CreditsTable"][key] = "{%s:plural(ru):%s}" % (p["var"], forms)
    return tables


def extra_data(final, shared):
    """Data read at runtime by KotbRussian.dll for text the game assembles in code."""
    rule_ids = shared["RuleBreakTable"]
    return {
        "time_lead": final["tables"]["CreditsTable"]["TimeCountTextKey"],
        "time": final["time"],
        "colors": final["colors"],
        "placeholder_piece_gender": final["piece_gender"]["ChessPieceKey"],
        "piece_gender": {PIECE_GENDER_TYPES[k]: g for k, g in final["piece_gender"].items() if k in PIECE_GENDER_TYPES},
        "rules_by_id": {str(rule_ids[k]): forms for k, forms in final["rules"].items()},
        "achievements": final["achievements"],
    }


def check_glyphs(final):
    """Stop before shipping text the font cannot draw."""
    texts = [v for t in final["tables"].values() for v in t.values()]
    texts += [v for r in final["rules"].values() for v in r.values()]
    texts += [v for f in final["time"].values() for v in f.values()]
    texts += [v for c in final["colors"].values() for v in c.values()]
    texts += list(final["achievements"].values())
    available = font_characters(FONT_BUNDLE)
    missing = sorted({c for t in texts for c in re.sub(r"\{[^{}]*\}", "", t) if c not in available and c not in "\r\n"})
    if missing:
        raise PatchError("characters missing from the font: " + " ".join(f"{c!r} U+{ord(c):04X}" for c in missing))


def install_code(game, extra):
    """Copy the helper library and redirect the game's call sites to it."""
    managed = os.path.join(game, MANAGED)
    shutil.copy2(HELPER_DLL, os.path.join(managed, "KotbRussian.dll"))
    target = os.path.join(managed, "Assembly-CSharp.dll")
    patched = target + ".patched"
    result = subprocess.run([CODE_PATCHER, target, HELPER_DLL, patched], capture_output=True, text=True)
    print(result.stdout.strip())
    if result.returncode != 0:
        raise PatchError("code patch failed: " + result.stderr.strip())
    os.replace(patched, target)
    ru_dir = os.path.join(game, DATA, "StreamingAssets", "ru")
    os.makedirs(ru_dir, exist_ok=True)
    with open(os.path.join(ru_dir, "ru_extra.json"), "w", encoding="utf-8") as f:
        json.dump(extra, f, ensure_ascii=False, indent=1)
    shutil.copytree(SPRITES, os.path.join(ru_dir, "sprites"))


def first_run_settings(game, generator):
    """The settings the game writes on its first start (option 0 of every setting), with Russian selected."""
    env = UnityPy.load(os.path.join(game, DATA, "sharedassets0.assets"))
    env.typetree_generator = generator
    containers = []
    for o in env.objects:
        if o.type.name != "MonoBehaviour":
            continue
        try:
            tt = o.read_typetree()
        except Exception:
            continue
        if "settingID" in tt and tt.get("settingOptions"):
            value = [LANGUAGE_INDEX] if tt["settingID"] == "language" else tt["settingOptions"][0]["settingValue"]
            containers.append({"settingID": tt["settingID"], "settingValue": [float(v) for v in value]})
    if not any(c["settingID"] == "language" for c in containers):
        raise PatchError("language setting not found in sharedassets0")
    return {"settingContainers": containers}


def build(game, settings_path):
    final = json.load(open(TRANSLATIONS, encoding="utf-8"))
    check_glyphs(final)
    translations = table_strings(final)
    shared = load_shared_keys(game)
    for table, entries in translations.items():
        unknown = set(entries) - set(shared[table])
        if unknown:
            raise PatchError(f"{table}: keys missing from the game: {sorted(unknown)}")
    generator = TypeTreeGenerator(UNITY_VERSION)
    generator.load_local_game(game)

    with open(settings_path, "w", encoding="utf-8") as f:
        json.dump(first_run_settings(game, generator), f, separators=(",", ":"))
    blobs = {
        "locales": build_locale_bundle(game),
        "strings": build_table_bundle(game, "strings", translations, shared)[0],
        "assets": build_table_bundle(game, "assets", translations, shared)[0],
        "pages": build_pages_bundle(game),
    }
    for kind, data in blobs.items():
        with open(os.path.join(game, BUNDLES, NEW_BUNDLES[kind]), "wb") as f:
            f.write(data)
    patch_catalog(game, {k: len(v) for k, v in blobs.items()})
    patch_sharedassets0(game, generator)
    install_code(game, extra_data(final, shared))


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    try:
        build(os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2]))
    except PatchError as e:
        sys.exit("error: %s" % e)
