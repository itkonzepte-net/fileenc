#!/usr/bin/env python3
import os
import sys
import argparse

# Harte OneDrive/Windows-Restriktionen
FORBIDDEN_CHARS = set('"*:<>?/\\|')
# Zeichen, die in der Praxis oft Ärger machen und die wir in --fix ebenfalls anpassen
PROBLEMATIC_CHARS = set("#%")
RESERVED_NAMES = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}

MAX_PATH_LEN = 400       # grob OneDrive/SharePoint-Limit
MAX_NAME_LEN = 255       # Dateiname

def has_forbidden_chars(name: str):
    return sorted(set(c for c in name if c in FORBIDDEN_CHARS))

def has_problematic_chars(name: str):
    return sorted(set(c for c in name if c in PROBLEMATIC_CHARS))

def has_control_chars(name: str):
    return sorted(set(
        c for c in name
        if ord(c) < 32 or 0x7F <= ord(c) <= 0x9F
    ))

def has_zero_width_or_rtl(name: str):
    res = []
    for c in name:
        code = ord(c)
        if (
            0x200B <= code <= 0x200F or
            0x202A <= code <= 0x202E or
            0x2060 <= code <= 0x206F
        ):
            res.append(c)
    return sorted(set(res))

def is_reserved_name(name: str):
    # Nur Basename ohne Extension betrachten (CON.txt ist auch verboten)
    base = name.split('.')[0]
    return base.upper() in RESERVED_NAMES

def make_safe_name(basename: str) -> str:
    """
    Erzeugt einen OneDrive-tauglichen Namen:
    - verbotene sichtbare Zeichen -> '_'
    - # und % -> '_'
    - Steuer-/Zero-Width-Zeichen -> entfernt
    - trailing Space/Dot -> entfernt
    - reservierte Namen -> bekommen '__' angehängt
    - führendes '~' -> '_' + Rest
    - zu lange Namen -> auf 255 gekürzt, Extension bleibt erhalten
    """
    chars = []
    for c in basename:
        code = ord(c)
        # Steuerzeichen / unprintables entfernen
        if code < 32 or 0x7F <= code <= 0x9F:
            continue
        # Zero-width / RTL entfernen
        if (
            0x200B <= code <= 0x200F or
            0x202A <= code <= 0x202E or
            0x2060 <= code <= 0x206F
        ):
            continue
        # verbotene sichtbare Zeichen ersetzen
        if c in FORBIDDEN_CHARS or c in PROBLEMATIC_CHARS:
            chars.append('_')
        else:
            chars.append(c)

    new_name = ''.join(chars)

    # führendes '~' entschärfen
    if new_name.startswith('~'):
        new_name = '_' + new_name[1:]

    # trailing Space/Dot entfernen
    new_name = new_name.rstrip(' .')

    # falls komplett leer geworden
    if not new_name:
        new_name = "_"

    # reservierte Namen entschärfen
    base = new_name.split('.')[0]
    if base.upper() in RESERVED_NAMES:
        # z.B. CON -> CON__  bzw. CON__.txt
        rest = new_name[len(base):]
        new_name = f"{base}__{rest}"

    # Länge auf MAX_NAME_LEN beschränken
    if len(new_name) > MAX_NAME_LEN:
        root, ext = os.path.splitext(new_name)
        allowed_root_len = MAX_NAME_LEN - len(ext)
        if allowed_root_len <= 0:
            # sehr exotisch, zur Not von rechts abschneiden
            new_name = new_name[-MAX_NAME_LEN:]
        else:
            new_name = root[:allowed_root_len] + ext

    return new_name

def get_unique_name(dirpath: str, desired: str) -> str:
    """
    Wenn desired bereits existiert, hänge _1, _2, ... an.
    """
    candidate = desired
    counter = 1
    while os.path.exists(os.path.join(dirpath, candidate)):
        root, ext = os.path.splitext(desired)
        candidate = f"{root}_{counter}{ext}"
        counter += 1
    return candidate

def check_and_maybe_fix(dirpath: str,
                        basename: str,
                        is_dir: bool,
                        fix: bool,
                        root: str,
                        prefix_len: int):
    """
    Prüft einen Eintrag (Datei oder Ordner) und benennt ihn bei Bedarf um.
    Gibt (errors, warnings, new_basename, did_rename) zurück.
    """
    full_path = os.path.join(dirpath, basename)
    rel_path = os.path.relpath(full_path, root)

    errors = 0
    warnings = 0
    rename_needed = False
    did_rename = False

    # 1) Pfadlänge (nur melden, nicht automatisch aufräumen)
    effective_len = prefix_len + len(rel_path)
    
    if effective_len > MAX_PATH_LEN:
        print(f"[ERROR] Path too long ({effective_len} > {MAX_PATH_LEN}): {rel_path}")
        print(f"        (prefix: {prefix_len}, raw: {len(rel_path)})")
        errors += 1
    else:
        print(f"[PATH ] {effective_len:4d} chars OK  – {rel_path}")

    # 2) Name-Länge
    if len(basename) > MAX_NAME_LEN:
        print(f"[ERROR] Name too long ({len(basename)} > {MAX_NAME_LEN}): {rel_path}")
        errors += 1
        rename_needed = True

    # 3) Verbotene Zeichen
    bad_chars = has_forbidden_chars(basename)
    if bad_chars:
        chars = ''.join(bad_chars)
        print(f"[ERROR] Invalid character(s) \"{chars}\" in: {rel_path}")
        errors += 1
        rename_needed = True

    # 4) Trailing Space oder Punkt
    if basename.endswith(' ') or basename.endswith('.'):
        print(f"[ERROR] Name ends with space or dot: {rel_path}")
        errors += 1
        rename_needed = True

    # 5) Reservierte Windows-Namen
    if is_reserved_name(basename):
        print(f"[ERROR] Reserved Windows name (CON/PRN/...): {rel_path}")
        errors += 1
        rename_needed = True

    # 6) Steuerzeichen / unsichtbare Zeichen
    ctrls = has_control_chars(basename)
    if ctrls:
        codes = ", ".join(f"U+{ord(c):04X}" for c in ctrls)
        print(f"[ERROR] Control/unprintable char(s) ({codes}) in: {rel_path}")
        errors += 1
        rename_needed = True

    zw = has_zero_width_or_rtl(basename)
    if zw:
        codes = ", ".join(f"U+{ord(c):04X}" for c in zw)
        print(f"[ERROR] Zero-width/RTL char(s) ({codes}) in: {rel_path}")
        errors += 1
        rename_needed = True

    # 7) Problematische, aber erlaubte Zeichen -> Warnung
    prob = has_problematic_chars(basename)
    if prob:
        chars = ''.join(prob)
        print(f"[WARN ] Contains potentially problematic char(s) \"{chars}\": {rel_path}")
        warnings += 1
        # in FIX-Mode wollen wir die auch glätten
        rename_needed = True if fix else rename_needed

    if basename.startswith('~'):
        print(f"[WARN ] Name starts with '~' (can confuse some tools): {rel_path}")
        warnings += 1
        if fix:
            rename_needed = True

    new_basename = basename

    # ggf. umbenennen
    if fix and rename_needed:
        safe = make_safe_name(basename)
        safe_unique = get_unique_name(dirpath, safe)

        if safe_unique != basename:
            new_full = os.path.join(dirpath, safe_unique)
            os.rename(full_path, new_full)
            new_rel = os.path.relpath(new_full, root)
            print(f"[FIX ] Renamed: {rel_path} -> {new_rel}")
            new_basename = safe_unique
            did_rename = True

    return errors, warnings, new_basename, did_rename

def validate(root: str, fix: bool = False, prefix_len: int = 0):
    errors = 0
    warnings = 0
    renames = 0

    root = os.path.abspath(root)

    for dirpath, dirnames, filenames in os.walk(root):
        # Erst Verzeichnisse prüfen/ggf. umbenennen
        for i, d in enumerate(list(dirnames)):
            e, w, new_name, did_rename = check_and_maybe_fix(
                dirpath, d, is_dir=True, fix=fix, root=root, prefix_len=prefix_len
            )
            errors += e
            warnings += w
            if did_rename:
                renames += 1
            # wenn Verzeichnis umbenannt wurde, muss os.walk die neue
            # Bezeichnung bekommen, sonst läuft er am neuen Pfad vorbei
            dirnames[i] = new_name

        # Dann Dateien
        for f in filenames:
            e, w, _, did_rename = check_and_maybe_fix(
                dirpath, f, is_dir=False, fix=fix, root=root, prefix_len=prefix_len
            )
            errors += e
            warnings += w
            if did_rename:
                renames += 1

    print()
    print(f"Validation finished for: {root}")
    print(f"  Errors  : {errors}")
    print(f"  Warnings: {warnings}")
    print(f"  Renamed : {renames}")

    return 1 if errors > 0 else 0

def main():
    parser = argparse.ArgumentParser(
        description="Validate (and optionally fix) OneDrive-compatible paths and filenames."
    )
    parser.add_argument("directory", help="Directory to scan")
    parser.add_argument(
        "-f", "--fix",
        action="store_true",
        help="Automatically rename problematic files/directories"
    )
    parser.add_argument(
        "--prefix-len",
        type=int,
        default=0,
        help="Extra length to add to each path (e.g. OneDrive internal prefix). Default: 0"
    )


    args = parser.parse_args()

    target = args.directory
    if not os.path.isdir(target):
        print(f"Not a directory: {target}", file=sys.stderr)
        sys.exit(2)

    if args.fix:
        print("!!! WARNING: Running in FIX mode, files/directories will be renamed on disk.")
        print("!!! Consider running without --fix first as a dry-run.\n")

    sys.exit(validate(target, fix=args.fix, prefix_len=args.prefix_len))

if __name__ == "__main__":
    main()

