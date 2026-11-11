"""Datos: carpeta fuera del repo y auditoría de solo-añadir. (e1 1.1, 1.2, 3.2)"""

import sqlite3

import pytest

from app.config import Settings, prepare_data_dir


def test_data_dir_valida_se_crea(tmp_path):
    destino = tmp_path / "datos" / "app"
    assert prepare_data_dir(destino) == destino.resolve()
    assert destino.is_dir()


def test_data_dir_dentro_de_un_repo_se_rechaza(tmp_path):
    (tmp_path / ".git").mkdir()
    with pytest.raises(RuntimeError, match="repositorio git"):
        prepare_data_dir(tmp_path / "datos")
    assert not (tmp_path / "datos").exists()  # no se creó nada


def test_settings_no_crea_carpetas_al_importar(tmp_path):
    s = Settings(data_dir=tmp_path / "nueva")
    assert s.database_url.endswith("/nueva/app.db")
    assert not (tmp_path / "nueva").exists()


def test_migracion_crea_las_tablas(db_url, tmp_path):
    con = sqlite3.connect(tmp_path / "test.db")
    tablas = {r[0] for r in con.execute("select name from sqlite_master where type='table'")}
    con.close()
    assert {"admin_users", "audit_log"} <= tablas


def test_auditoria_rechaza_update_y_delete(db_url, tmp_path):
    con = sqlite3.connect(tmp_path / "test.db")
    con.execute(
        "insert into audit_log (ts, actor, action, result) values ('t', 'a', 'x', 'ok')"
    )
    con.commit()
    with pytest.raises(sqlite3.DatabaseError, match="solo añadir"):
        con.execute("update audit_log set actor = 'otro'")
    with pytest.raises(sqlite3.DatabaseError, match="solo añadir"):
        con.execute("delete from audit_log")
    assert con.execute("select actor from audit_log").fetchall() == [("a",)]
    con.close()
