import os
import stat


def write_file(path: str, content: str):
    tmp = f"{path}.tmp"
    with open(tmp, "w") as f:
        f.write(content)
    os.rename(tmp, path)


def read_file(path: str) -> str:
    with open(path) as f:
        return f.read()


def check_mode(path: str, mode: int, *, is_file: bool = False, is_dir: bool = False):
    st = os.stat(path)
    if is_dir:
        assert stat.S_ISDIR(st.st_mode)
    if is_file:
        assert stat.S_ISREG(st.st_mode)

    got = stat.S_IMODE(st.st_mode)
    assert got == mode, f"File mode {got:04o}!={mode:04o} for {path}"
