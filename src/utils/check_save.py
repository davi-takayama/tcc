import os

def check_save() -> bool:
    _dir = os.path.dirname(__file__)[: __file__.index("src")]
    save_path = os.path.join(_dir + "/savestate", "save.json")
    return os.path.isfile(save_path)
