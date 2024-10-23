import zipfile
import os
import json
import argparse
import tkinter as tk
from tkinter import scrolledtext, messagebox

class VirtualFileSystem:
    def __init__(self, zip_path):
        self.fs = {}
        self.current_path = ['/']
        self.zip_path = zip_path
        self.load_zip(zip_path)

    def load_zip(self, zip_path):
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            for file_info in zip_ref.infolist():
                if file_info.is_dir():
                    self._add_to_fs(file_info.filename)
                else:
                    self._add_to_fs(file_info.filename, is_file = True)

    def _add_to_fs(self, path, is_file = False):
        parts = path.strip("/").split('/')
        current = self.fs
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]

        if is_file:
            current[parts[-1]] = {'type': 'file'}
        else:
            current[parts[-1]] = {}

    def _navigate_to_current_dir(self):
        current = self.fs
        for dir_name in self.current_path[1:]:
            current = current.get(dir_name)
            if current is None:
                return None
        return current

    def mkdir(self, dir_name):
        current_dir = self._navigate_to_current_dir()
        if current_dir is None:
            return "Cannot find the current directory."

        if dir_name in current_dir:
            return f"Directory '{dir_name}' already exists."
        else:
            current_dir[dir_name] = {}
            return f"Directory '{dir_name}' created."

    def ls(self):
        current_dir = self._navigate_to_current_dir()
        if current_dir is None:
            return "Cannot find the current directory."

        output = []
        if current_dir:
            for name, item in current_dir.items():
                if isinstance(item, dict):
                    if item.get('type') == 'file':
                        output.append(name)
                    else:
                        output.append(f"{name}/")
        else:
            output.append("No files or directories found.")
        return "\n".join(output)

    def cd(self, dir_name):
        if dir_name == "..":
            if len(self.current_path) > 1:
                self.current_path.pop()
            return ""
        elif dir_name in self._navigate_to_current_dir():
            self.current_path.append(dir_name)
            return ""
        else:
            return f"Directory '{dir_name}' not found."

    def read_file(self, file_name):
        current_dir = self._navigate_to_current_dir()
        if current_dir and file_name in current_dir:
            with zipfile.ZipFile(self.zip_path, 'r') as zip_ref:
                with zip_ref.open('/'.join(self.current_path[1:] + [file_name]), 'r') as f:
                    return f.read().decode('utf-8')
        return None

    def wc(self, file_name):
        content = self.read_file(file_name)
        if content is None:
            return f"Error: File '{file_name}' not found."

        lines = content.splitlines()
        
        words = content.split()

        characters = len(content)

        return f"{len(lines)} lines, {len(words)} words, {characters} characters"

    def tac(self, file_name):
        content = self.read_file(file_name)
        if content is None:
            return f"Error: File '{file_name}' not found."
        lines = content.splitlines()
        return "\n".join(reversed(lines))


class ShellEmulator:
    def __init__(self, vfs, username, logfile, startup_script=None):
        self.vfs = vfs
        self.username = username
        self.logfile = logfile
        self.log = []
        if startup_script:
            self.run_startup_script(startup_script)

    def run_startup_script(self, script_path):
        if os.path.exists(script_path):
            with open(script_path, 'r') as file:
                commands = file.readlines()
            for command in commands:
                self.execute_command(command.strip())

    def execute_command(self, command):
        parts = command.split()
        if len(parts) == 0:
            return

        cmd = parts[0]
        args = parts[1:]

        if cmd == "mkdir":
            result = self.vfs.mkdir(args[0]) if args else "No directory name provided."
        elif cmd == "ls":
            result = self.vfs.ls()
        elif cmd == "cd":
            result = self.vfs.cd(args[0]) if args else ""
        elif cmd == "exit":
            result = self.exit()
        elif cmd == "wc":
            if args:
                result = self.vfs.wc(args[0])
            else:
                result = "No file name provided."
        elif cmd == "tac":
            if args:
                result = self.vfs.tac(args[0])
            else:
                result = "No file name provided."
        else:
            result = f"Unknown command: {cmd}"

        self.log_action(command)
        return result

    def exit(self):
        return "exit"

    def log_action(self, command):
        self.log.append({"user": self.username, "command": command})
        with open(self.logfile, 'w') as log_file:
            json.dump(self.log, log_file, indent=2)


class ShellApp:
    def __init__(self, vfs, username, logfile):
        self.vfs = vfs
        self.username = username
        self.logfile = logfile
        self.shell_emulator = ShellEmulator(vfs, username, logfile)

        self.root = tk.Tk()
        self.root.title("Shell Emulator")

        self.text_area = scrolledtext.ScrolledText(self.root, wrap = tk.WORD, width = 100, height = 40)
        self.text_area.pack(padx = 10, pady = 10)

        self.input_area = tk.Entry(self.root, width = 80)
        self.input_area.pack(padx = 10, pady = 10)
        self.input_area.bind("<Return>", self.process_command)

        self.text_area.insert(tk.END, f"{self.username}@shell_emulator$ ")

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.mainloop()

    def process_command(self, event):
        command = self.input_area.get()
        self.text_area.insert(tk.END, f"{command}\n")
        self.input_area.delete(0, tk.END)

        result = self.shell_emulator.execute_command(command)
        if result == "exit":
            self.on_closing()
        elif result:
            self.text_area.insert(tk.END, result + "\n")
        
        self.text_area.insert(tk.END, f"{self.username}@shell_emulator$ ")
        self.text_area.see(tk.END)

    def on_closing(self):
        if messagebox.askokcancel("Exit", "Do you want to quit?"):
            self.root.destroy()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description = "Shell Emulator")
    parser.add_argument("--username", required = True, help = "Username for the shell prompt")
    parser.add_argument("--filesystem", required = True, help = "Path to the virtual filesystem (zip)")
    parser.add_argument("--logfile", required = True, help = "Path to the log file")
    parser.add_argument("--startup_script", help = "Path to the startup script (optional)")

    args = parser.parse_args()

    vfs = VirtualFileSystem(args.filesystem)

    ShellApp(vfs, args.username, args.logfile)
