"""
/***************************************************************************
 DbConfDialog
                                 A QGIS plugin
 データベース設定ダイアログ
                              -------------------
        copyright            : (C) 2023 by orbitalnet.inc
 ***************************************************************************/

"""
import os

from qgis.PyQt import uic
from qgis.PyQt.QtCore import Qt, QSettings
from qgis.PyQt.QtWidgets import QDialog, QMessageBox
from qgis.PyQt.QtSql import QSqlDatabase

from qgis.core import QgsApplication, Qgis

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'db_conf_dialog_base.ui'))

class DbConfDialog(QDialog, FORM_CLASS):
    def __init__(self, parent, flags = Qt.WindowFlags()):
        super().__init__(parent, flags)

        self.setupUi(self)
        self.db = None
        self.success = False

    def setHostName(self, text: str):
        visible = len(text) == 0
        self.label_host_name.setVisible(visible)
        self.edit_host_name.setVisible(visible)

    def setDatabaseName(self, text: str):
        visible = len(text) == 0
        self.label_database_name.setVisible(visible)
        self.edit_database_name.setVisible(visible)

    def setUserName(self, text: str):
        visible = len(text) == 0
        self.label_user_name.setVisible(visible)
        self.edit_user_name.setVisible(visible)
        
    def setPassword(self, text: str):
        visible = len(text) == 0
        self.label_password.setVisible(visible)
        self.edit_password.setVisible(visible)

    def check(self) -> bool:
        if self.edit_host_name.isVisible():
            if len(self.edit_host_name.text()) == 0:
                QMessageBox.warning(None, "エラー", "ホスト名を入力してください")
                self.edit_host_name.setFocus()
                return False

        if self.edit_database_name.isVisible():
            if len(self.edit_database_name.text()) == 0:
                QMessageBox.warning(None, "エラー", "データベース名を入力してください")
                self.edit_database_name.setFocus()
                return False
        if self.edit_user_name.isVisible():
            if len(self.edit_user_name.text()) == 0:
                QMessageBox.warning(None, "エラー", "ユーザー名を入力してください")
                self.edit_user_name.setFocus()
                return False
        if self.edit_password.isVisible():
            if len(self.edit_password.text()) == 0:
                QMessageBox.warning(None, "エラー", "パスワードを入力してください")
                self.edit_password.setFocus()
                return False

        return True

    def accept(self):
        if self.check() == False:
            return

        return super().accept()


    def connectDB(self, iface = None) -> bool:
        """
        DB接続
        DB接続に成功時はTrue、失敗時はFalseを返却する
        
        設定ファイルよりDB接続情報を取得しDB接続を実行する
        設定ファイルにDB接続情報が未設定の場合、接続情報入力するダイアログを表示する
        """

        # 設定ファイルより接続情報を取得
        settings = QSettings(os.path.join(os.path.dirname(__file__), "conf.ini"), QSettings.IniFormat)
        settings.beginGroup("DB")
        host_name = settings.value("host_name", "")
        database_name = settings.value("database_name", "")
        user_name = settings.value("user_name", "")
        password = settings.value("password", "")
        settings.endGroup()

        success = False

        if len(host_name) == 0 or len(database_name) == 0 or len(user_name) == 0 or len(password) == 0:
            # DB接続情報ダイアログ表示
            self.setHostName(host_name)
            self.setDatabaseName(database_name)
            self.setUserName(user_name)
            self.setPassword(password)

            if self.exec() == QDialog.Rejected:
                return False

            if len(host_name) == 0:
                host_name = self.edit_host_name.text()
            if len(database_name) == 0:
                database_name = self.edit_database_name.text()
            if len(user_name) == 0:
                user_name = self.edit_user_name.text()
            if len(password) == 0:
                password = self.edit_password.text()

        # データベース名、ユーザー名、パスワードが揃っていればDB接続
        if len(host_name) > 0 and len(database_name) > 0 and len(user_name) > 0 and len(password) > 0:
            db = QSqlDatabase.addDatabase("QPSQL")
            db.setHostName(host_name)
            db.setDatabaseName(database_name)
            db.setUserName(user_name)
            db.setPassword(password)

            QgsApplication.setOverrideCursor(Qt.WaitCursor)
            if iface is not None:
                iface.messageBar().pushMessage("住宅地図検索", "DB接続中です", Qgis.Info, 0)
                QgsApplication.processEvents()
            success = db.open()
            if iface is not None:
                iface.messageBar().clearWidgets()
                QgsApplication.processEvents()
            QgsApplication.restoreOverrideCursor()
            
            if success:
                # QMessageBox.information(None, "エラー", f"DB接続に成功しました。")
                return True
            else:
                # DB接続失敗
                QMessageBox.warning(None, "エラー", f"DB接続に失敗しました。{db.lastError().text()}")

        return success

