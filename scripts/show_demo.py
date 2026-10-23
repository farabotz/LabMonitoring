from pathlib import Path
from PySide6.QtWidgets import QApplication, QMessageBox
from packages.desktop.common import load_secret

app = QApplication([])
data = load_secret(Path(".runtime/demo.dpapi"))
QMessageBox.information(None, "Credential sintetis lokal • jangan bagikan", "\n\n".join(
    f"{key}: {value['nim']}\nPassword: {value['password']}" for key, value in data.items()))
