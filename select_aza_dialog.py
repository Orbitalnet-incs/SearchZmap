# -*- coding: utf-8 -*-
"""
/***************************************************************************
 SelectAzaDialog
                                 A QGIS plugin
 字選択ダイアログ
                             -------------------
        copyright            : (C) 2023 by Orbitalnet.inc
 ***************************************************************************/

"""

import os

from PyQt5 import uic
from PyQt5.QtCore import pyqtSignal, Qt, QSortFilterProxyModel, QRegExp, QModelIndex
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QDialog, QTableView, QStyledItemDelegate, QStyleOptionViewItem
from PyQt5.QtSql import QSqlQueryModel

from qgis.core import QgsApplication

from .db_util import DbUtil

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'select_aza_dialog_base.ui'))

# 行とかなの辞書
KANA_DISC = {"あ":"あいうえお", "か":"かきくけこ", "さ":"さしすせそ", "た":"たちつてと", "な":"なにぬねの", "は":"はひふへほ", "ま":"まみむめも", "や":"やゆよ", "ら":"らりるれろ", "わ":"わをん"}

class SelectAzaDialog(QDialog, FORM_CLASS):
    """
    字選択ダイアログクラス
    """
    # ダイアログクローズシグナル定義
    closingPlugin = pyqtSignal()

    def __init__(self, db_util: DbUtil, parent=None):
        """
        Constructor.

        :param db_util 
        """
        super(SelectAzaDialog, self).__init__(parent)
        # Set up the user interface from Designer.
        # After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://doc.qt.io/qt-5/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)

        self.db_util = db_util

        # ボタンアイコン
        self.button_back.setIcon(QIcon(os.path.join(os.path.dirname(__file__), f"icons/back.png")))
        self.button_back_gaiku.setIcon(QIcon(os.path.join(os.path.dirname(__file__), f"icons/back.png")))

        # 段
        self.button_gyo_a.clicked.connect(self.filterGyo_a)
        self.button_gyo_ka.clicked.connect(self.filterGyo_ka)
        self.button_gyo_sa.clicked.connect(self.filterGyo_sa)
        self.button_gyo_ta.clicked.connect(self.filterGyo_ta)
        self.button_gyo_na.clicked.connect(self.filterGyo_na)
        self.button_gyo_ha.clicked.connect(self.filterGyo_ha)
        self.button_gyo_ma.clicked.connect(self.filterGyo_ma)
        self.button_gyo_ya.clicked.connect(self.filterGyo_ya)
        self.button_gyo_wa.clicked.connect(self.filterGyo_wa)
        self.button_gyo_ra.clicked.connect(self.filterGyo_ra)
        self.button_gyo_all.clicked.connect(self.filterGyo_all)

        self.button_dan_a.clicked.connect(self.filterDan_a)
        self.button_dan_i.clicked.connect(self.filterDan_i)
        self.button_dan_u.clicked.connect(self.filterDan_u)
        self.button_dan_e.clicked.connect(self.filterDan_e)
        self.button_dan_o.clicked.connect(self.filterDan_o)
        self.button_dan_all.clicked.connect(self.filterDan_all)

        # Viewは並べ替え不可とする
        self.tableView.setSortingEnabled(False)
        # Viewは単一行選択モード
        self.tableView.setSelectionBehavior(QTableView.SelectRows)
        self.tableView.setSelectionMode(QTableView.SingleSelection)
        # 最後の列が右端に付くように伸張する
        self.tableView.horizontalHeader().setStretchLastSection(True)

        # View(行)をクリックしたときの挙動
        self.tableView.clicked.connect(self.clickedTableViewRow)

        # 確定ボタン
        self.button_confirm.clicked.connect(self.confirmCode)
        self.button_confirm_gaiku.clicked.connect(self.confirmCode)

        # 戻るボタン
        self.button_back.clicked.connect(self.backTableView)
        self.button_back_gaiku.clicked.connect(self.backTableView)

        # 戻るボタン、確定ボタンと５０音の段は非表示
        self.button_back.hide()
        self.button_confirm.hide()
        self.frame_dan.hide()
        self.frame_gaiku.hide()

        # 選択市町村コード、大字コード、小字コード(いずれも文字列)
        self.select_city_code = ""
        self.select_ooaza_code = ""
        self.select_koaza_code = ""
        self.select_gaiku_code = ""

        self.current_mode = ""

        # テーブルビューヘッダ
        self.headers = {
            "city": [   {"name": "50音", "hidden": False, "field": "initial_group", "width": 50},
                        {"name": "市町村名", "hidden": False, "field": "name", "width": 140},
                        {"name": "ふりがな", "hidden": False, "field": "kana", "width": 170},
                        {"name": "頭文字", "hidden": True, "field": "initial"},
                        {"name": "code", "hidden": True, "field": "code"}
            ],
            "ooaza": [  {"name": "50音", "hidden": False, "field": "initial_group", "width": 50},
                        {"name": "大字名", "hidden": False, "field": "name", "width": 140},
                        {"name": "ふりがな", "hidden": False, "field": "kana", "width": 170},
                        {"name": "頭文字", "hidden": True, "field": "initial"},
                        {"name": "code", "hidden": True, "field": "code"}
            ],
            "koaza": [  {"name": "50音", "hidden": False, "field": "initial_group", "width": 50},
                        {"name": "小字名", "hidden": False, "field": "name", "width": 140},
                        {"name": "ふりがな", "hidden": False, "field": "kana", "width": 170},
                        {"name": "頭文字", "hidden": True, "field": "initial"},
                        {"name": "code", "hidden": True, "field": "code"}
            ],
            "gaiku": [  {"name": "街区", "hidden": False, "field": "name"},
                        {"name": "code", "hidden": True, "field": "code"}
            ]
        }

        # 50音フィルターモデル
        self.fileter_proxy_model = JSyllabaryFilterProxyModel(self)
        self.fileter_proxy_model.setFilterKeyColumn(3)

        # かな行段ボタンの使用可否辞書初期化
        self.clearInitalDict()

        # かな行ボタン
        self.gyo_buttons = {
            "あ": self.button_gyo_a,
            "か": self.button_gyo_ka,
            "さ": self.button_gyo_sa,
            "た": self.button_gyo_ta,
            "な": self.button_gyo_na,
            "は": self.button_gyo_ha,
            "ま": self.button_gyo_ma,
            "や": self.button_gyo_ya,
            "ら": self.button_gyo_ra,
            "わ": self.button_gyo_wa,
        }
        # かな段ボタン
        self.dan_buttons = [
            self.button_dan_a,
            self.button_dan_i,
            self.button_dan_u,
            self.button_dan_e,
            self.button_dan_o
        ]

    def citySelected(self):
        """選択市町村コード"""
        return self.select_city_code

    def ooazaSelected(self):
        """選択大字コード"""
        return self.select_ooaza_code

    def koazaSelected(self):
        """選択小字コード"""
        return self.select_koaza_code

    def gaikuSelected(self):
        """選択街区コード"""
        return self.select_gaiku_code

    def prepare(self, city_code = ""):
        """
        市町村コードの指定がない場合は市町村の選択から、
        ある場合は下の大字の選択から行う

        :param city_code 市町村コード。省略可
        """
        if city_code is None or city_code == "":
            # 市町村選択から行う
            self.select_city_code = ""
            self.setCityData()
        else:
            # 指定市町村下の大字選択から行う
            self.select_city_code = city_code
            self.setOoazaData()

    def setCityData(self):
        """
        市町村データ表示
        """
        QgsApplication.setOverrideCursor(Qt.WaitCursor)

        self.current_mode = "city"

        self.select_ooaza_code = ""
        self.select_koaza_code = ""
        self.select_gaiku_code = ""

        query_model = self.db_util.getCityDataJSyllabary()
        if query_model is None or query_model.rowCount() == 0:
            self.tableView.setModel(None)
        else:
            self.updateTableView(query_model)
        
        QgsApplication.restoreOverrideCursor()

    def setOoazaData(self):
        """
        大字データ表示

        選択済みの市町村コードを使用して大字データをDBより取得し、テーブルビューに表示する
        """
        QgsApplication.setOverrideCursor(Qt.WaitCursor)

        self.current_mode = "ooaza"
        self.select_koaza_code = ""
        self.select_gaiku_code = ""

        query_model = self.db_util.getOoazaDataJSyllabary(self.select_city_code)
        if query_model is None or query_model.rowCount() == 0:
            self.tableView.setModel(None)
        else:
            self.updateTableView(query_model)

        QgsApplication.restoreOverrideCursor()

    def setKoazaData(self):
        """
        小字データ表示

        選択済みの市町村コード、大字コードを使用して大字データをDBより取得し、テーブルビューに表示する
        ただし、小字データがなかったり、code=0の「小字なし」データしかない場合は街区データを表示する
        """
        QgsApplication.setOverrideCursor(Qt.WaitCursor)

        self.current_mode = "koaza"
        self.select_gaiku_code = ""
 
        query_model = self.db_util.getKoazaDataJSyllabary(self.select_city_code, self.select_ooaza_code)
        if self.hasNonZero(query_model):
            # code=0の「小字なし」以外に有効なデータがある場合はこのデータをテーブル表示する
            self.updateTableView(query_model)
        else:
            # データがない場合、あるいは小字なしデータしかない場合は街区を設定
            self.select_koaza_code = "0"
            self.setGaikuData()

        QgsApplication.restoreOverrideCursor()

    def setGaikuData(self):
        """
        街区データ表示

        選択済みの市町村コード、大字コード、小字コードを使用して大字データをDBより取得し、テーブルビューに表示する
        """
        QgsApplication.setOverrideCursor(Qt.WaitCursor)

        self.current_mode = "gaiku"
        query_model = self.db_util.getGaikuData(self.select_city_code, self.select_ooaza_code, self.select_koaza_code)
        if self.hasNonZero(query_model):
            self.updateGaikuTableView(query_model)
        else:
            # code=0の「街区なし」以外に有効なデータがある場合はこのデータをテーブル表示する
            self.tableView.setModel(None)
            self.select_gaiku_code = "0"
            self.accept()

        QgsApplication.restoreOverrideCursor()

    def hasNonZero(self, model: QSqlQueryModel):
        """
        「小字なし」「街区なし」以外のデータがあるか判定する
        :return 小字なし(code=0)以外のデータがある場合はTrueを、それ以外はFalseを返却する
        """
        if model is None:
            # チェック
            return False

        has = False
        for row in range(model.rowCount()):
            if str(model.record(row).value("code")) != "0":
                has = True
                break
        
        return has

    def updateTableView(self, query_model: QSqlQueryModel):
        """
        テーブルビューに指定の50音順データモデルを設定する

        :param query_model 市町村、大字、小字の50音順データモデル
        """
        # 以前のテーブルビューのモデルを破棄する
        self.tableView.setModel(None)
        self.fileter_proxy_model.setSourceModel(None)

        # 行段の使用可否リストをクリア
        self.clearInitalDict()

        if query_model is None:
            return

        # ヘッダの設定
        header = self.headers[self.current_mode]
        for i, h in enumerate(header):
            query_model.setHeaderData(i, Qt.Horizontal, h["name"])

        # 頭文字の使用状況（＝かなフィルタボタンの使用可否）取得
        for row in range(query_model.rowCount()):
            initial_group = str(query_model.record(row).value("initial_group"))
            self.initial_group_dict[initial_group] = True
            initial = str(query_model.record(row).value("initial"))
            self.initial_dict[initial] = True

        # フィルタ用のモデル
        self.fileter_proxy_model.setSourceModel(query_model)
        self.tableView.setModel(self.fileter_proxy_model)

        # 列幅と非表示設定
        for i, h in enumerate(header):
            self.tableView.setColumnHidden(i, h.get("hidden", False))
            if "width" in h:
                self.tableView.setColumnWidth(i, h.get("width", 0))

        # 50音列を前行と同じなら表示しないようにする
        self.tableView.setItemDelegateForColumn(0, EquivalentBlankColumnDelegate())

        # 行段ボタンの使用可否を設定する
        self.resetGyoDanButtons()
        # 戻るボタン、確定ボタンを設定する
        self.setButtonStatus()
        # 選択を解除する
        self.tableView.clearSelection()

    def updateGaikuTableView(self, query_model: QSqlQueryModel):
        """
        テーブルビューに指定の街区データモデルを設定する

        :param query_model 街区データモデル
        """
        # 以前のテーブルビューのモデルを破棄する
        self.tableView.setModel(None)
        self.fileter_proxy_model.setSourceModel(None)

        # ヘッダを設定
        header = self.headers["gaiku"]
        for idx, h in enumerate(header):
            query_model.setHeaderData(idx, Qt.Horizontal, h["name"])

        # テーブルビューにそのまま設定する
        self.tableView.setModel(query_model)
        # 列の非表示を設定する
        for idx, h in enumerate(header):
            self.tableView.setColumnHidden(idx, h["hidden"])

        # 行と段のボタンを非表示にする
        self.frame_gyo.hide()
        self.frame_dan.hide()
        # 戻るボタン、確定ボタンを設定する
        self.setButtonStatus()
        # 選択を解除する
        self.tableView.clearSelection()

    def clearInitalDict(self):
        """
        かな行段ボタンの使用可否を保持する辞書を初期化
        """
        # かな行ボタン使用可否辞書
        self.initial_group_dict = {
            'あ': False, 'か': False, 'さ': False, 'た': False, 'な': False,
            'は': False, 'ま': False, 'や': False, 'ら': False, 'わ': False
        }

        # かな段ボタン使用可否辞書
        self.initial_dict = {
            'あ': False, 'い': False, 'う': False, 'え': False, 'お': False,
            'か': False, 'き': False, 'く': False, 'け': False, 'こ': False,
            'さ': False, 'し': False, 'す': False, 'せ': False, 'そ': False,
            'た': False, 'ち': False, 'つ': False, 'て': False, 'と': False,
            'な': False, 'に': False, 'ぬ': False, 'ね': False, 'の': False,
            'は': False, 'ひ': False, 'ふ': False, 'へ': False, 'ほ': False,
            'ま': False, 'み': False, 'む': False, 'め': False, 'も': False,
            'や': False, 'ゆ': False, 'よ': False,
            'ら': False, 'り': False, 'る': False, 'れ': False, 'ろ': False,
            'わ': False, 'を': False, 'ん': False,
        }


    def resetGyoDanButtons(self):
        """
        かな行段ボタンの状態をリセットする
        """
        # フィルタークリア
        self.fileter_proxy_model.clearFilter()
        # すべて（行）、すべて（段）をチェック
        self.button_gyo_all.setChecked(True)
        self.button_dan_all.setChecked(True)
        # 行を表示
        self.frame_gyo.show()
        # 段は非表示
        self.frame_dan.hide()

        for k, v in self.initial_group_dict.items():
            button = self.gyo_buttons.get(k, None)
            if button is not None:
                button.setEnabled(v)

    def setButtonStatus(self):
        """
        戻るボタン、確定ボタン等の状態を設定する
        """
        if self.current_mode == "city":
            # 戻るボタン
            self.button_back.hide()
            # 確定ボタン
            self.button_confirm.hide()
            # 街区用
            self.frame_gaiku.hide()
            return

        if self.current_mode == "ooaza":
            # 戻るボタンに市町村名を設定する
            self.button_back.setText(self.db_util.getCityName(self.select_city_code))

        elif self.current_mode == "koaza":
            # 戻るボタンに大字名を設定する
            self.button_back.setText(self.db_util.getOoazaName(self.select_city_code, self.select_ooaza_code))

        elif self.current_mode == "gaiku":
            if self.select_koaza_code == "0":
                # 戻るボタンに大字名を設定する
                self.button_back_gaiku.setText(self.db_util.getOoazaName(self.select_city_code, self.select_ooaza_code))
            else:
                # 戻るボタンに小字名を設定する
                self.button_back_gaiku.setText(self.db_util.getKoazaName(self.select_city_code, self.select_ooaza_code, self.select_koaza_code))
            # 街区用
            self.frame_gaiku.show()
            # 戻るボタン
            self.button_back.show()
            # 確定ボタン
            self.button_confirm.show()
            return
            
        # 戻るボタン
        self.button_back.show()
        # 確定ボタン
        self.button_confirm.show()
        # 街区用
        self.frame_gaiku.hide()

    # 選択した５０音の行にフィルターする
    def filterGyo_a(self):
        self.button_dan_all.setChecked(True)
        return self.filterGyo("あ")
    
    def filterGyo_ka(self):
        self.button_dan_all.setChecked(True)
        return self.filterGyo("か")
    
    def filterGyo_sa(self):
        self.button_dan_all.setChecked(True)
        return self.filterGyo("さ")
    
    def filterGyo_ta(self):
        self.button_dan_all.setChecked(True)
        return self.filterGyo("た")
    
    def filterGyo_na(self):
        self.button_dan_all.setChecked(True)
        return self.filterGyo("な")
    
    def filterGyo_ha(self):   
        self.button_dan_all.setChecked(True)
        return self.filterGyo("は")
    
    def filterGyo_ma(self):
        self.button_dan_all.setChecked(True)
        return self.filterGyo("ま")
    
    def filterGyo_ya(self):
        self.button_dan_all.setChecked(True)
        return self.filterGyo("や")
    
    def filterGyo_ra(self):
        self.button_dan_all.setChecked(True)
        return self.filterGyo("ら")

    def filterGyo_wa(self):
        self.button_dan_all.setChecked(True)
        return self.filterGyo("わ")
    
    def filterGyo_all(self):
        """全行を表示する"""
        if self.button_gyo_all.isChecked():
            self.frame_dan.hide()
            self.button_dan_all.blockSignals(True)
            self.button_dan_all.setChecked(True)
            self.button_dan_all.blockSignals(False)

            self.filterGyo("")

    
    # 選択した５０音の段にフィルターする
    def filterDan_a(self):
        text = self.button_dan_a.text()
        return self.filterDan(text)
    
    def filterDan_i(self):
        text = self.button_dan_i.text()
        return self.filterDan(text)
    
    def filterDan_u(self):
        text = self.button_dan_u.text()
        return self.filterDan(text)
    
    def filterDan_e(self):
        text = self.button_dan_e.text()
        return self.filterDan(text)
    
    def filterDan_o(self):
        text = self.button_dan_o.text()
        return self.filterDan(text)
    
    def filterDan_all(self):
        if self.button_gyo_a.isChecked():
            return self.filterGyo("あ")
        elif self.button_gyo_ka.isChecked():
            return self.filterGyo("か")
        elif self.button_gyo_sa.isChecked():
            return self.filterGyo("さ")
        elif self.button_gyo_ta.isChecked():
            return self.filterGyo("た")
        elif self.button_gyo_na.isChecked():
            return self.filterGyo("な")
        elif self.button_gyo_ha.isChecked():
            return self.filterGyo("は")
        elif self.button_gyo_ma.isChecked():
            return self.filterGyo("ま")
        elif self.button_gyo_ya.isChecked():
            return self.filterGyo("や")
        elif self.button_gyo_ra.isChecked():
            return self.filterGyo("ら")
        elif self.button_gyo_wa.isChecked():
            return self.filterGyo("わ")

    def filterGyo(self, gyo_str: str):
        """
        指定した"行"でフィルターする

        :param gyo_str あ、か、さ、...の行を表す文字
        """
        # データを行でフィルター
        self.fileter_proxy_model.filterGyo(gyo_str)

        # 行に属する段ボタンのテキストと使用可否を決定する
        enabled_dan = list(KANA_DISC.get(gyo_str, ""))
        # 使用する仮名の数
        enabled_dan_count = len(enabled_dan)
        for idx, button in enumerate(self.dan_buttons):
            if idx < enabled_dan_count:
                button.setVisible(True)
                # 該当する仮名を表示する
                button.setText(enabled_dan[idx])
                # データ取得時に設定した頭文字の使用状況辞書を元にボタンの使用可否を決定する
                button.setEnabled(self.initial_dict.get(enabled_dan[idx], False))
            else:
                # 使用する仮名の数より多い段ボタンは不可視にする
                button.setVisible(False)

        self.tableView.scrollToTop()
        self.frame_dan.show()

    def filterDan(self, kana: str):
        """
        指定したかなでフィルターする

        :param dan_str 仮名文字
        :type dan_str str
        """ 
        self.fileter_proxy_model.filterDan(kana)
        self.tableView.scrollToTop()

    def showEvent(self, event):
        """
        表示前に準備処理を行わなかった場合、市町村の選択から行う
        """
        if self.current_mode == "":
            self.prepare()

    def closeEvent(self, event):
        """
        クローズシグナルを発生する
        """
        self.closingPlugin.emit()
        event.accept()

    def backTableView(self):
        """
        戻るボタンを押したとき（ひとつ前の状態に戻す）
        """
        if self.current_mode == "city":
            # 戻れないので無視
            return
        elif self.current_mode == "ooaza":
            self.select_ooaza_code = ""
            self.setCityData()
        elif self.current_mode == "koaza":
            self.select_koaza_code = ""
            self.setOoazaData()
        elif self.current_mode == "gaiku":
            self.select_gaiku_code = ""
            if self.select_koaza_code == "0":
                self.select_ooaza_code = ""
                self.select_koaza_code = ""
                self.setOoazaData()
            else:
                self.select_koaza_code = ""
                self.setKoazaData()
    
    def clickedTableViewRow(self, indexClicked: QModelIndex):
        """
        tableviewの行を選択したときの処理

        :param indexClicked クリックした位置のインデックス
        :type indexClicked QModelIndex
        """
        # 選択した行のcode列を特定する
        row = indexClicked.row()
        column = [i for i, c in enumerate(self.headers[self.current_mode]) if c["name"] == "code"][0]

        if self.current_mode == "gaiku":
            # 街区で決定された場合
            model = self.tableView.model()
            self.select_gaiku_code = str(model.data(model.index(row, column)))
            self.accept()
            return

        model = self.tableView.model()
        if self.current_mode == "city":
            self.select_city_code = str(model.data(model.index(row, column)))
            self.setOoazaData()
        elif self.current_mode == "ooaza":
            self.select_ooaza_code = str(model.data(model.index(row, column)))
            self.setKoazaData()
        elif self.current_mode == "koaza":
            self.select_koaza_code = str(model.data(model.index(row, column)))
            self.setGaikuData()

    def confirmCode(self):
        """
        確定ボタンを押したとき
        """
        # これまで選択したコードだけで終了する
        self.accept()


# -----------------------------------------------------------------------------------------------
class JSyllabaryFilterProxyModel(QSortFilterProxyModel):
    """
    かなでフィルターできる代替モデルクラス
    """
    def __init__(self, parent):
        super().__init__(parent)
    
    def clearFilter(self):
        """
        フィルター解除
        """
        self.setFilterRegExp(QRegExp(""))

    def filterGyo(self, gyo: str):
        """
        あ、か、さ...を指定して行でフィルターする
        :param gyo あ、か、さ...などの行をあらわす一文字
        :type gyo str
        """
        # 行と段の辞書からこの行に属するかなを取得する
        filter = KANA_DISC.get(gyo, "")
        if filter == "":
            # 有効な仮名がない場合フィルターを解除する
            self.setFilterRegExp(QRegExp(""))
            return
        # filterKeyColumnにこのかなのうち一つが見つかれば表示するように設定する
        self.setFilterRegExp(QRegExp(f"[{filter}]"))

    def filterDan(self, dan: str):
        """
        filterKeyColumnのデータが引数の文字に一致したら表示するように設定する

        :param dan かな
        @type dan str
        """
        self.setFilterRegExp(QRegExp(dan))


# -----------------------------------------------------------------------------------------------
class EquivalentBlankColumnDelegate(QStyledItemDelegate):
    """
    前の行と同値なら表示しない列用スタイル描画委任クラス
    """
    def paint(self, painter, option: QStyleOptionViewItem, index: QModelIndex):
        if index.row() > 0:
            # 前行と値の比較をする
            prev_index = index.model().index(index.row() - 1, index.column())
            if str(index.model().data(prev_index, Qt.DisplayRole)) == str(index.model().data(index, Qt.DisplayRole)):
                # 前行と同じ値なら表示しない
                new_option = QStyleOptionViewItem()
                self.initStyleOption(new_option, index)
                new_option.text = ""
                super().paint(painter, new_option, index)
                return

        super().paint(painter, option, index)
