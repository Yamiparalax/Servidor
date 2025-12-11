# -*- coding: utf-8 -*-
import os
import sys
import json
import base64
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple, Dict, Any, List
import ctypes
import ctypes.wintypes as wintypes
import threading
import traceback

from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QMessageBox, QDialog, QFormLayout, QLineEdit, QCheckBox,
    QHeaderView, QFrame
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QPixmap, QPalette, QBrush

# log
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(Path(__file__).stem)
logger.propagate = False
_console = logging.StreamHandler(sys.stdout)
_console.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
logger.handlers = [_console]

# arquivos
APP_DIR = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "seu_amiguinho"
STORE_PATH = APP_DIR / "dollynho.dbx"
BACKUP_PATH = APP_DIR / "dollynho.dbx.bak"

# dpapi
VERSION = 1
DPAPI_ENTROPY = b"C6_DOLLYNHO_v1"
LOCK = threading.Lock()

class DATA_BLOB(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD),
                ("pbData", ctypes.POINTER(ctypes.c_byte))]

_crypt32 = ctypes.WinDLL("Crypt32.dll")
_kernel32 = ctypes.WinDLL("Kernel32.dll")

_CryptProtectData = _crypt32.CryptProtectData
_CryptProtectData.argtypes = [ctypes.POINTER(DATA_BLOB), wintypes.LPCWSTR,
                              ctypes.POINTER(DATA_BLOB), ctypes.c_void_p,
                              ctypes.c_void_p, wintypes.DWORD,
                              ctypes.POINTER(DATA_BLOB)]
_CryptProtectData.restype = wintypes.BOOL

_CryptUnprotectData = _crypt32.CryptUnprotectData
_CryptUnprotectData.argtypes = [ctypes.POINTER(DATA_BLOB), ctypes.POINTER(wintypes.LPWSTR),
                                ctypes.POINTER(DATA_BLOB), ctypes.c_void_p,
                                ctypes.c_void_p, wintypes.DWORD,
                                ctypes.POINTER(DATA_BLOB)]
_CryptUnprotectData.restype = wintypes.BOOL

_LocalFree = _kernel32.LocalFree
_LocalFree.argtypes = [ctypes.c_void_p]
_LocalFree.restype = ctypes.c_void_p

def _to_blob(data: bytes) -> DATA_BLOB:
    if not data:
        data = b""
    buf = ctypes.create_string_buffer(data)
    blob = DATA_BLOB()
    blob.cbData = len(data)
    blob.pbData = ctypes.cast(buf, ctypes.POINTER(ctypes.c_byte))
    return blob

def _from_blob(blob: DATA_BLOB) -> bytes:
    cb = int(blob.cbData)
    ptr = ctypes.cast(blob.pbData, ctypes.POINTER(ctypes.c_ubyte))
    data = bytes(bytearray(ptr[i] for i in range(cb)))
    _LocalFree(blob.pbData)
    return data

def dpapi_encrypt(plaintext: bytes, entropy: Optional[bytes] = DPAPI_ENTROPY) -> bytes:
    data_in = _to_blob(plaintext)
    data_entropy = _to_blob(entropy or b"")
    data_out = DATA_BLOB()
    ok = _CryptProtectData(ctypes.byref(data_in), None, ctypes.byref(data_entropy),
                           None, None, 0, ctypes.byref(data_out))
    if not ok:
        raise RuntimeError("CryptProtectData falhou")
    return _from_blob(data_out)

def dpapi_decrypt(ciphertext: bytes, entropy: Optional[bytes] = DPAPI_ENTROPY) -> bytes:
    data_in = _to_blob(ciphertext)
    data_entropy = _to_blob(entropy or b"")
    data_out = DATA_BLOB()
    descr = wintypes.LPWSTR()
    ok = _CryptUnprotectData(ctypes.byref(data_in), ctypes.byref(descr),
                             ctypes.byref(data_entropy), None, None, 0,
                             ctypes.byref(data_out))
    try:
        if not ok:
            raise RuntimeError("CryptUnprotectData falhou")
        return _from_blob(data_out)
    finally:
        if descr:
            _LocalFree(descr)

# persistência
def _ensure_store_exists() -> None:
    APP_DIR.mkdir(parents=True, exist_ok=True)
    if not STORE_PATH.exists():
        data = {"version": VERSION, "updated_at": _ts(), "entries": []}
        STORE_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def _ts() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def _read_store() -> Dict[str, Any]:
    _ensure_store_exists()
    with LOCK:
        raw = STORE_PATH.read_text(encoding="utf-8")
        return json.loads(raw)

def _atomic_write_store(data: Dict[str, Any]) -> None:
    tmp = STORE_PATH.with_suffix(".tmp")
    txt = json.dumps(data, ensure_ascii=False, indent=2)
    with LOCK:
        try:
            if STORE_PATH.exists():
                STORE_PATH.replace(BACKUP_PATH)
        except Exception:
            pass
        tmp.write_text(txt, encoding="utf-8")
        tmp.replace(STORE_PATH)

def _encode_secret(b: bytes) -> str:
    return base64.b64encode(dpapi_encrypt(b)).decode("ascii")

def _decode_secret(s: str) -> bytes:
    return dpapi_decrypt(base64.b64decode(s.encode("ascii")))

def _find_index_by_method(entries: List[Dict[str, Any]], metodo: str) -> int:
    key = (_normalize_method(metodo) or "").casefold()
    for i, e in enumerate(entries):
        em = (e.get("method") or "")
        if (_normalize_method(em) or "").casefold() == key:
            return i
    return -1

def _normalize_method(name: str) -> str:
    name = (name or "").strip()
    if not name:
        return name
    return Path(name).stem

def listar_metodos() -> List[str]:
    store = _read_store()
    return sorted([e["method"] for e in store.get("entries", [])], key=lambda s: s.casefold())

def set_credencial(metodo: str, usuario: str, senha: str, *, old_method: Optional[str] = None) -> None:
    metodo_norm = _normalize_method(metodo)
    if not metodo_norm:
        raise ValueError("método vazio")
    store = _read_store()
    entries = list(store.get("entries", []))
    alvo = _normalize_method(old_method) if (old_method and old_method.strip()) else metodo_norm
    idx = _find_index_by_method(entries, alvo)
    created_at = _ts() if idx < 0 else entries[idx].get("created_at", _ts())
    record = {
        "method": metodo_norm,
        "username": _encode_secret(usuario.encode("utf-8")),
        "password": _encode_secret(senha.encode("utf-8")),
        "updated_at": _ts(),
        "created_at": created_at,
        "version": VERSION,
    }
    if idx < 0:
        entries.append(record)
    else:
        entries[idx] = record
    # dedup case-insensitive
    k_new = (_normalize_method(metodo_norm) or "").casefold()
    dedup: List[Dict[str, Any]] = []
    seen = False
    for e in entries:
        k = (_normalize_method(e.get("method", "")) or "").casefold()
        if k == k_new:
            if not seen:
                dedup.append(e)
                seen = True
        else:
            dedup.append(e)
    store["entries"] = dedup
    store["updated_at"] = _ts()
    _atomic_write_store(store)

def delete_credencial(metodo: str) -> bool:
    metodo = _normalize_method(metodo)
    store = _read_store()
    entries = store.get("entries", [])
    idx = _find_index_by_method(entries, metodo)
    if idx < 0:
        return False
    entries.pop(idx)
    store["entries"] = entries
    store["updated_at"] = _ts()
    _atomic_write_store(store)
    return True

def get_credencial(metodo: Optional[str] = None) -> Tuple[str, str]:
    nome = _normalize_method(metodo) if metodo else _resolver_metodo_pelo_chamador()
    store = _read_store()
    entries = store.get("entries", [])
    idx = _find_index_by_method(entries, nome)
    if idx < 0:
        raise KeyError(f"método não encontrado: {nome}")
    rec = entries[idx]
    usuario = _decode_secret(rec["username"]).decode("utf-8")
    senha = _decode_secret(rec["password"]).decode("utf-8")
    return usuario, senha

def _resolver_metodo_pelo_chamador() -> str:
    try:
        frame = sys._getframe(2)
        fpath = frame.f_globals.get("__file__")
        if fpath:
            return Path(fpath).stem
    except Exception:
        pass
    return Path(sys.argv[0]).stem or "DESCONHECIDO"

def ask_yes_no(parent, titulo: str, texto: str, yes_text: str = "Sim", no_text: str = "Cancelar") -> bool:
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Question)
    box.setWindowTitle(titulo)
    box.setText(texto)
    yes = box.addButton(yes_text, QMessageBox.YesRole)
    no = box.addButton(no_text, QMessageBox.NoRole)
    box.exec_()
    return box.clickedButton() == yes

class EditorDialog(QDialog):
    def __init__(self, parent=None, metodo: str = "", usuario: str = "", senha: str = "") -> None:
        super().__init__(parent)
        self.setWindowTitle("Editar credencial" if metodo else "Nova credencial")
        self.setModal(True)
        self._original_method = _normalize_method(metodo) if metodo else None  # guarda nome original

        self.input_metodo = QLineEdit(metodo)
        self.input_usuario = QLineEdit(usuario)
        self.input_senha = QLineEdit(senha)
        self.input_senha.setEchoMode(QLineEdit.Password)
        self.chk_show = QCheckBox("Mostrar senha")
        self.chk_show.toggled.connect(self._toggle_show)

        form = QFormLayout()
        form.addRow("Método", self.input_metodo)
        form.addRow("Usuário", self.input_usuario)
        form.addRow("Senha", self.input_senha)
        form.addRow("", self.chk_show)

        btns = QHBoxLayout()
        self.btn_salvar = QPushButton("Salvar")
        self.btn_cancelar = QPushButton("Cancelar")
        btns.addWidget(self.btn_salvar)
        btns.addWidget(self.btn_cancelar)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addLayout(btns)

        self.btn_salvar.clicked.connect(self._on_save)
        self.btn_cancelar.clicked.connect(self.reject)

    def _toggle_show(self, checked: bool) -> None:
        self.input_senha.setEchoMode(QLineEdit.Normal if checked else QLineEdit.Password)

    def _on_save(self) -> None:
        m = _normalize_method(self.input_metodo.text())
        u = self.input_usuario.text().strip()
        p = self.input_senha.text()
        if not m or not u or not p:
            QMessageBox.warning(self, "Aviso", "Preencha método, usuário e senha.")
            return
        if not ask_yes_no(self, "Confirmar", f"Confirmar gravação do método '{m}'?"):
            return
        try:
            set_credencial(m, u, p, old_method=self._original_method)  # renomeia sem duplicar
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Erro", str(e))

class CredMain(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Sou Dollynho, seu amiguinho, vamos criptografar?")
        self.resize(800, 500)
        self.setFont(QFont("Segoe UI", 12))

        self._assets_dir = (
            Path.home()
            / "C6 CTVM LTDA, BANCO C6 S.A. e C6 HOLDING S.A"
            / "Mensageria e Cargas Operacionais - 11.CelulaPython"
            / "graciliano"
            / "novo_servidor"
            / "assets"
        )
        self._bg_path = self._find_bg_path()
        self._bg_pixmap = QPixmap(str(self._bg_path)) if self._bg_path else None
        self._apply_bg()

        self.PANEL_ALPHA = 110
        self.PANEL_BG = f"rgba(0,0,0,{self.PANEL_ALPHA})"
        self.PANEL_BG_H = f"rgba(0,0,0,{min(self.PANEL_ALPHA+20,255)})"

        panel = QFrame()
        panel.setObjectName("panel")
        panel.setStyleSheet(f"""
            #panel {{
                background-color: {self.PANEL_BG};
                border: none;
                border-radius: 8px;
            }}
        """)

        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Método", "Usuário"])
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setWordWrap(False)
        self.table.setShowGrid(False)
        self.table.setFrameShape(QFrame.NoFrame)

        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        hh.setStretchLastSection(False)
        hh.setHighlightSections(False)

        vh = self.table.verticalHeader()
        vh.setVisible(False)

        self.table.setStyleSheet(f"""
            QTableWidget, QTableView {{
                background-color: transparent;
                color: white;
            }}
            QHeaderView::section {{
                background-color: {self.PANEL_BG};
                color: white;
                border: none;
                padding: 6px 8px;
            }}
            QTableCornerButton::section {{
                background-color: {self.PANEL_BG};
                border: none;
            }}
            QTableWidget::item {{
                background-color: {self.PANEL_BG};
                border: none;
                padding: 6px;
            }}
            QTableWidget::item:hover {{
                background-color: rgba(255,255,255,40);
            }}
            QTableWidget::item:selected {{
                background-color: rgba(30,144,255,180);
                color: white;
            }}
        """)

        self.btn_novo = QPushButton("Adicionar novo método")
        self.btn_excluir = QPushButton("Deletar método")
        btn_style = f"""
            QPushButton {{
                background-color: {self.PANEL_BG_H};
                color: white;
                border: 1px solid rgba(255,255,255,60);
                border-radius: 6px;
                padding: 6px 12px;
            }}
            QPushButton:hover {{
                background-color: rgba(255,255,255,60);
                color: white;
            }}
            QPushButton:pressed {{
                background-color: rgba(255,255,255,90);
            }}
        """
        self.btn_novo.setStyleSheet(btn_style)
        self.btn_excluir.setStyleSheet(btn_style)

        panel_layout = QVBoxLayout(panel)
        top = QHBoxLayout()
        top.addWidget(self.btn_novo)
        top.addWidget(self.btn_excluir)
        top.addStretch()
        panel_layout.addLayout(top)
        panel_layout.addWidget(self.table)

        root = QVBoxLayout(self)
        root.addWidget(panel)

        self.btn_novo.clicked.connect(self._on_new)
        self.btn_excluir.clicked.connect(self._on_delete)
        self.table.cellDoubleClicked.connect(self._on_edit_doubleclick)

        self._reload()

    def _find_bg_path(self) -> Optional[Path]:
        if not self._assets_dir.exists():
            return None
        for ext in ("png", "jpg", "jpeg"):
            p = self._assets_dir / f"dollynho.{ext}"
            if p.exists():
                return p
        return None

    def _apply_bg(self) -> None:
        if not self._bg_pixmap or self._bg_pixmap.isNull():
            return
        scaled = self._bg_pixmap.scaled(self.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        pal = self.palette()
        pal.setBrush(QPalette.Window, QBrush(scaled))
        self.setPalette(pal)
        self.setAutoFillBackground(True)

    def resizeEvent(self, e) -> None:
        super().resizeEvent(e)
        self._apply_bg()
        self.table.resizeColumnsToContents()

    def _reload(self) -> None:
        try:
            nomes = listar_metodos()
        except Exception as e:
            logger.error("Falha ao ler cofre: %s", e)
            nomes = []
        rows: List[Tuple[str, str]] = []
        for m in nomes:
            try:
                u, _ = get_credencial(m)
            except Exception:
                u = ""
            rows.append((m, u))
        self.table.setRowCount(len(rows))
        for i, (m, u) in enumerate(rows):
            self.table.setItem(i, 0, QTableWidgetItem(m))
            self.table.setItem(i, 1, QTableWidgetItem(u))
        self.table.resizeColumnsToContents()

    def _current_method(self) -> Optional[str]:
        sel = self.table.currentRow()
        if sel < 0:
            return None
        return self.table.item(sel, 0).text()

    def _on_new(self) -> None:
        dlg = EditorDialog(self)
        if dlg.exec_() == QDialog.Accepted:
            self._reload()

    def _on_edit_doubleclick(self, row: int, col: int) -> None:
        metodo = self.table.item(row, 0).text()
        if not metodo:
            return
        try:
            u, p = get_credencial(metodo)
        except Exception:
            u, p = "", ""
        dlg = EditorDialog(self, metodo=metodo, usuario=u, senha=p)
        if dlg.exec_() == QDialog.Accepted:
            self._reload()

    def _on_delete(self) -> None:
        metodo = self._current_method()
        if not metodo:
            QMessageBox.warning(self, "Aviso", "Selecione um método para excluir.")
            return
        if not ask_yes_no(self, "Confirmar", f"Excluir credencial de '{metodo}'?"):
            return
        try:
            ok = delete_credencial(metodo)
            if ok:
                self._reload()
                QMessageBox.information(self, "OK", "Excluído.")
            else:
                QMessageBox.information(self, "Info", "Nada a excluir.")
        except Exception as e:
            QMessageBox.critical(self, "Erro", str(e))

# cli
def _cli(args: List[str]) -> int:
    if not args or args[0] in {"gui", "abrir"}:
        try:
            _ensure_store_exists()
            app = QApplication(sys.argv)
            app.setFont(QFont("Segoe UI", 12))
            w = CredMain()
            w.show()
            return app.exec_()
        except Exception:
            logger.error("Falha na GUI:\n%s", traceback.format_exc())
            return 1

    cmd = args[0].lower()
    try:
        if cmd == "set":
            metodo, user, pwd = args[1], args[2], args[3]
            set_credencial(metodo, user, pwd)
            print("OK")
            return 0
        elif cmd == "get":
            metodo = args[1] if len(args) > 1 else None
            user, pwd = get_credencial(metodo)
            print(user)
            print(pwd)
            return 0
        elif cmd == "del":
            metodo = args[1]
            ok = delete_credencial(metodo)
            print("OK" if ok else "NAO_EXISTE")
            return 0
        elif cmd == "list":
            for n in listar_metodos():
                print(n)
            return 0
        else:
            print("Comandos: gui | set <metodo> <usuario> <senha> | get [metodo] | del <metodo> | list")
            return 2
    except IndexError:
        print("Parâmetros insuficientes.")
        return 2
    except Exception:
        logger.error("Falha no comando:\n%s", traceback.format_exc())
        return 1

def main() -> int:
    if os.name != "nt":
        logger.error("Requer Windows (DPAPI).")
        return 1
    try:
        return _cli(sys.argv[1:])
    except Exception:
        logger.error("Erro não tratado:\n%s", traceback.format_exc())
        return 1

if __name__ == "__main__":
    sys.exit(main())