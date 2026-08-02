from datetime import datetime
from flask import Blueprint, render_template, flash, redirect, url_for
from flask_login import login_required
import os
import shutil
from utils.rbac import requer_permissao

backup_bp = Blueprint("backup", __name__, url_prefix="/backup")

@backup_bp.get("/")
@login_required
def index():
    return render_template("backup/index.html")

@backup_bp.post("/gerar")
@login_required
@requer_permissao("admin:full")
def gerar():
    db_path = "prontuario.db"
    if not os.path.exists(db_path):
        flash("Banco SQLite não encontrado para backup.", "warning")
        return redirect(url_for("backup.index"))

    os.makedirs("backups", exist_ok=True)
    nome = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    destino = os.path.join("backups", nome)
    shutil.copy2(db_path, destino)
    flash(f"Backup criado: {destino}", "success")
    return redirect(url_for("backup.index"))