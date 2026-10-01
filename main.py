import sys

if getattr(sys, "frozen", False):
    # PyInstaller points the DLL search path at its temp folder; child processes (server, games) inherit
    # that, load DLLs from there and keep the folder locked, so it cannot be removed on exit.
    import ctypes
    ctypes.windll.kernel32.SetDllDirectoryW(None)

from aplauncher.gui import main

if __name__ == "__main__":
    main()
