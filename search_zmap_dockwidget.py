"""
/***************************************************************************
 SearchZmapDockWidget
                                 A QGIS plugin
 住宅地図検索ウィジェット
        copyright            : (C) 2023 by orbitalnet.inc
 ***************************************************************************/

"""

import os

from qgis.PyQt import uic
from qgis.PyQt.QtCore import pyqtSignal, Qt, QAbstractItemModel
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QDockWidget, QTableView, QComboBox, QLineEdit

from qgis.core import Qgis, QgsRectangle, QgsPointXY, QgsApplication

from .db_util import DbUtil
from .select_aza_dialog import SelectAzaDialog

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'search_zmap_dockwidget_base.ui'))

class SearchZmapDockWidget(QDockWidget, FORM_CLASS):

    closingPlugin = pyqtSignal()

    def __init__(self, iface, parent=None):
        super(SearchZmapDockWidget, self).__init__(parent)
        # Set up the user interface from Designer.
        # After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://doc.qt.io/qt-5/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)

        self.iface = iface

        self.column_code = 1
        self.column_pos_x = 2
        self.column_pos_y = 3

        self.db_util = DbUtil()

        self.model_chiban = None
        self.model_landmark = None

        self.city_code_selected = None
        self.ooaza_code_selected = None
        self.koaza_code_selected = None
        self.gaiku_code_selected = None

        self.city_data_model = None
        self.ooaza_data_model = None
        self.koaza_data_model = None
        self.gaiku_data_model = None

        self.ooaza_scale = 2000
        self.koaza_scale = 1000
        self.chiban_scale = 500

        # 画面のボタンの処理の指定など
        self.initUI()
        # エリアコンボボックス初期生成
        self.initArea()

    def initArea(self):
        """
        エリアコンボボックス初期設定
        """
        # スキーマ名一覧を取得する
        QgsApplication.setOverrideCursor(Qt.WaitCursor)
        schema_names = self.db_util.getSchemaNames()
        QgsApplication.restoreOverrideCursor()

        if len(schema_names) == 0:
            return

        self.combo_area.blockSignals(True)
        self.combo_area.addItems(schema_names)
        self.combo_area.blockSignals(False)
        # 先頭を選択状態にする
        self.combo_area.setCurrentIndex(-1)
        self.combo_area.setCurrentIndex(0)

    def initUI(self):
        """
        画面に関する初期設定
        """
        # ----- アイコン設定 -----
        self.button_locate_aza.setIcon(QIcon(os.path.join(os.path.dirname(__file__), 'icons/actionLocate.png')))
        self.button_search_chiban.setIcon(QIcon(os.path.join(os.path.dirname(__file__), 'icons/actionSearch.png')))
        self.button_clear_chiban.setIcon(QIcon(os.path.join(os.path.dirname(__file__), 'icons/back.png')))
        self.button_locate_chiban.setIcon(QIcon(os.path.join(os.path.dirname(__file__), 'icons/actionLocate.png')))
        self.button_search_landmark.setIcon(QIcon(os.path.join(os.path.dirname(__file__), 'icons/actionSearch.png')))
        self.button_clear_landmark.setIcon(QIcon(os.path.join(os.path.dirname(__file__), 'icons/back.png')))
        self.button_locate_landmark.setIcon(QIcon(os.path.join(os.path.dirname(__file__), 'icons/actionLocate.png')))

        # ----- 地番検索 -----
        # 選択時の挙動
        self.combo_area.currentTextChanged.connect(self.handleAreaChanged)
        self.combo_city.currentIndexChanged.connect(self.handleCityCombChanged)
        self.edit_ooaza.textChanged.connect(self.handleOoazaTextChanged)
        self.combo_ooaza.currentIndexChanged.connect(self.handleOoazaCombChanged)
        self.edit_koaza.textChanged.connect(self.handleKoazaTextChanged)
        self.combo_koaza.currentIndexChanged.connect(self.handleKoazaCombChanged)
        self.edit_gaiku.textChanged.connect(self.handleGaikuTextChanged)
        self.combo_gaiku.currentIndexChanged.connect(self.handleGaikuCombChanged)
        self.edit_chiban.textChanged.connect(self.handleChibanChanged)

        # ボタンの処理
        self.button_select.clicked.connect(self.showSelectAzaDialog)
        self.button_clear_chiban.clicked.connect(self.handleChibanClear)
        self.button_search_chiban.clicked.connect(self.handleSearchChiban)
        self.button_locate_aza.clicked.connect(self.handleLocateAza)
        self.button_locate_chiban.clicked.connect(self.handleLocateChiban)

        # テーブルビュー設定
        self.table_view_chiban.setSelectionBehavior(QTableView.SelectRows)
        self.table_view_chiban.setSelectionMode(QTableView.SingleSelection)
        self.table_view_chiban.doubleClicked.connect(lambda index: self.handleLocateChiban())

        # ----- ランドマーク検索 -----
        self.button_search_landmark.clicked.connect(self.handleLandmarkSearch)
        self.button_clear_landmark.clicked.connect(self.handleLandmarkClear)
        self.button_locate_landmark.clicked.connect(self.handleLandmarkLocate)

    def handleAreaChanged(self, area_name):
        """
        エリアコンボボックスを変更した時の挙動
        各部品をクリアする
        市町村コンボボックスのリスト作成  
        """
        # これより使用するスキーマを選択エリアとする
        QgsApplication.setOverrideCursor(Qt.WaitCursor)
        self.db_util.setSchema(area_name)
        QgsApplication.restoreOverrideCursor()
        # エリアコンボボックス以外をクリア
        self.clear()
        # 市町村リスト作成
        self.makeCityCombo()

    def handleCityCombChanged(self, index):
        """
        市町村コンボボックスを変更した時の挙動
        各部品をクリアする
        スキーマ名と大字コンボボックスのリスト作成
        """
        # 選択市町村コードを退避
        self.city_code_selected = self.combo_city.itemData(index)
        # 大字、小字、街区をクリア
        self.clearOoaza()
        self.clearKoaza()
        self.clearGaiku()
        # 大字リスト作成
        self.makeOoazaCombo()
        # ボタンの状態を変更する
        self.setChibanButtonStatus()
 
    def handleOoazaTextChanged(self, text):
        """
        大字コード変更時処理

        入力する度に一致する大字を検索し、大字コンボボックスの選択を行う
        """
        if self.sender() == self.edit_ooaza:
            self.syncAzaComboBox(self.combo_ooaza, text)

    def handleOoazaCombChanged(self, index):
        """
        大字コンボボックス項目選択処理
        小字コンボボックスのリスト作成
        """
        # 選択大字コードを退避
        self.ooaza_code_selected = self.combo_ooaza.itemData(index)
        # 大字コードエディットに反映
        if self.sender() == self.combo_ooaza:
            self.syncAzaLineEdit(self.edit_ooaza, self.ooaza_code_selected)
        # 小字、街区をクリア
        self.clearKoaza()
        self.clearGaiku()
        # 小字リスト作成
        self.makeKoazaCombo()
       # ボタンの状態を変更する
        self.setChibanButtonStatus()

    def handleKoazaTextChanged(self, text):
        """
        小字コード変更時処理

        入力する度に一致する小字を検索し、小字コンボボックスの選択を行う
        """
        if self.sender() == self.edit_koaza:
            self.syncAzaComboBox(self.combo_koaza, text)

    def handleKoazaCombChanged(self, index):
        """
        小字コンボボックス項目選択処理
        """
        # 選択大字コードを退避
        self.koaza_code_selected = self.combo_koaza.itemData(index)
        # 小字コードエディットに反映
        if self.sender() == self.combo_koaza:
            self.syncAzaLineEdit(self.edit_koaza, self.koaza_code_selected)
        # 街区をクリア
        self.clearGaiku()
        # 街区リスト作成
        self.makeGaikuCombo()

    def handleGaikuTextChanged(self, text):
        """
        街区コード変更時処理

        入力する度に一致する街区を検索し、街区コンボボックスの選択を行う
        """
        if self.sender() == self.edit_gaiku:
            self.syncAzaComboBox(self.combo_gaiku, text)

    def handleGaikuCombChanged(self, index):
        """
        街区コンボボックス項目選択処理
        """
        # 選択大字コードを退避
        self.gaiku_code_selected = self.combo_gaiku.itemData(index)
        # 街区コードエディットに反映
        if self.sender() == self.combo_gaiku:
            self.syncAzaLineEdit(self.edit_gaiku, self.gaiku_code_selected)

    def makeCityCombo(self):
        """
        市町村リスト作成
        """
        QgsApplication.setOverrideCursor(Qt.WaitCursor)
        self.city_data_model = self.db_util.getCityModel()
        QgsApplication.restoreOverrideCursor()
        self.makeCombobox(self.combo_city, self.city_data_model)
        # ボタン使用可否
        self.setChibanButtonStatus()

    def makeOoazaCombo(self):
        """
        大字リスト作成
        """
        if self.city_code_selected:
            QgsApplication.setOverrideCursor(Qt.WaitCursor)
            self.ooaza_data_model = self.db_util.getOoazaModel(self.city_code_selected)
            QgsApplication.restoreOverrideCursor()
            self.makeCombobox(self.combo_ooaza, self.ooaza_data_model)
        # ボタン使用可否
        self.setChibanButtonStatus()

    def makeKoazaCombo(self):
        """
        小字リスト作成
        """
        if self.ooaza_code_selected:
            QgsApplication.setOverrideCursor(Qt.WaitCursor)
            self.koaza_data_model = self.db_util.getKoazaModel(self.city_code_selected, self.ooaza_code_selected)
            QgsApplication.restoreOverrideCursor()
            self.makeCombobox(self.combo_koaza, self.koaza_data_model)
        # ボタン使用可否
        self.setChibanButtonStatus()

    def makeGaikuCombo(self):
        """
        街区リスト作成
        """
        if self.koaza_code_selected:
            QgsApplication.setOverrideCursor(Qt.WaitCursor)
            self.gaiku_data_model = self.db_util.getGaikuModel(self.city_code_selected, self.ooaza_code_selected, self.koaza_code_selected)
            QgsApplication.restoreOverrideCursor()
            self.makeCombobox(self.combo_gaiku, self.gaiku_data_model)

        # ボタン使用可否
        self.setChibanButtonStatus()

    def makeCombobox(self, combobox: QComboBox, model: QAbstractItemModel):
        """
        コンボボックスに先頭に空行を設定し、データモデルからデータを設定する
        @param combobox コンボボックス
        @param model データモデル
        """
        combobox.clear()
        if model is not None and model.rowCount() > 0:
            combobox.addItem("", None)
            for row in range(model.rowCount()):
                combobox.addItem(str(model.data(model.index(row, 0))), model.data(model.index(row, 1)))
            # 空行を選択
            combobox.setCurrentIndex(0)

    def clearCity(self):
        """
        市町村コンボボックス関連情報をクリア
        """
        self.city_code_selected = None
        self.city_data_model = None
        self.combo_city.clear()

    def clearOoaza(self):
        """
        大字コンボボックス関連情報をクリア
        """
        self.ooaza_data_model = None
        self.combo_ooaza.clear()
        self.ooaza_code_selected = None
        self.edit_ooaza.blockSignals(True)
        self.edit_ooaza.clear()
        self.edit_ooaza.blockSignals(False)

    def clearKoaza(self):
        """
        小字コンボボックス関連情報をクリア
        """
        self.koaza_data_model = None
        self.combo_koaza.clear()
        self.koaza_code_selected = None
        self.edit_koaza.blockSignals(True)
        self.edit_koaza.clear()
        self.edit_koaza.blockSignals(False)

    def clearGaiku(self):
        """
        街区コンボボックス関連情報をクリア
        """
        self.gaiku_data_model = None
        self.combo_gaiku.clear()
        self.gaiku_code_selected = None
        self.edit_gaiku.blockSignals(True)
        self.edit_gaiku.clear()
        self.edit_gaiku.blockSignals(False)

    def clearChiban(self):
        """
        地番Viewをクリア
        """
        self.table_view_chiban.setModel(None)
        self.model_chiban = None

    def handleChibanChanged(self, value):
        """
        地番入力
        """
        # 地番の入力によりボタンの状態を変更する
        self.setChibanButtonStatus()

    def modelData(self, model: QAbstractItemModel, row: int, column: int):
        """
        列と行を指定してデータモデルからデータを抽出する

        @param model データモデル
        @param row 行番号
        @param column 列番号
        @return 該当位置に格納されているデータ
        """
        if model is None:
            return None
        index = model.index(row, column)
        if model.checkIndex(index) == False:
            return None
        
        return model.data(index, Qt.DisplayRole)

    def syncAzaLineEdit(self, edit: QLineEdit, code):
        """
        変更シグナルを発行することなくコードをラインエディットに設定する
        
        @param edit ラインエディット
        @param code 設定するコード
        """
        edit.blockSignals(True)
        if code is None:
            edit.clear()
        else:
            edit.setText(str(code))
        edit.blockSignals(False)

    def syncAzaComboBox(self, combobox: QComboBox, code):
        """
        変更シグナルを発行することなくコードをコンボボックスに設定する
        
        @param combobox コンボボックス
        @param code 設定するコード
        """
        if combobox.count() == 0 or code is None:
            combobox.setCurrentIndex(-1)
        else:
            index = combobox.findData(code)
            combobox.setCurrentIndex(index)

    def findModelData(self, model: QAbstractItemModel, column: int, target):
        """
        データモデルの指定列からtargetと一致するデータを検索し、その行を返却する

        @param model データモデル
        @param column 列番号
        @param target 検索対象データ

        @return 行番号        
        """
        for row in range(model.rowCount()):
            index = model.index(row, column)
            if model.data(index) == target:
                return row

        return -1

    def setChibanButtonStatus(self):
        """
        地番検索の各ボタンの状態を設定
        """
        # 検索と所在表示（字）ボタンの排他表示

        is_visible_locate = True
        is_enabled_locate = False
        if self.city_code_selected is not None:
            if self.ooaza_code_selected is not None:
                if len(self.edit_chiban.text()) > 0:
                    is_visible_locate = False
                else:
                    is_enabled_locate = True
        
        self.button_locate_aza.setVisible(is_visible_locate)
        self.button_locate_aza.setEnabled(is_enabled_locate)
        self.button_search_chiban.setVisible(is_visible_locate == False)

        is_enabled_locate_chiban = False
        while True:
            if self.model_chiban is None:
                break
            if self.model_chiban.rowCount() == 0:
                break
            if self.table_view_chiban.selectionModel() is None:
                break
            if self.table_view_chiban.selectionModel().hasSelection() == False:
                break
            is_enabled_locate_chiban = True
            break
        self.button_locate_chiban.setEnabled(is_enabled_locate_chiban)

        # 市町村、大字、小字、街区、地番の使用可否設定
        self.edit_ooaza.setEnabled(self.city_code_selected is not None)
        self.combo_ooaza.setEnabled(self.city_code_selected is not None)
        self.edit_koaza.setEnabled(self.ooaza_code_selected is not None)
        self.combo_koaza.setEnabled(self.ooaza_code_selected is not None)
        self.edit_gaiku.setEnabled(self.koaza_code_selected is not None)
        self.combo_gaiku.setEnabled(self.koaza_code_selected is not None)

    def showSelectAzaDialog(self):
        # ダイアログで大字コードを反映するため、このdockwidgetを設定
        dlg = SelectAzaDialog(self.db_util, self)

        dlg.prepare(self.city_code_selected)
            
        if dlg.exec() == SelectAzaDialog.Accepted:
            if self.city_code_selected != dlg.citySelected():
                self.city_code_selected = dlg.citySelected()
                index = self.combo_city.findData(self.city_code_selected)
                self.combo_city.setCurrentIndex(index)

            if self.ooaza_code_selected != dlg.ooazaSelected():
                self.ooaza_code_selected = dlg.ooazaSelected()
                index = self.combo_ooaza.findData(self.ooaza_code_selected)
                self.combo_ooaza.setCurrentIndex(index)

            if self.koaza_code_selected != dlg.koazaSelected():
                self.koaza_code_selected = dlg.koazaSelected()
                index = self.combo_koaza.findData(self.koaza_code_selected)
                self.combo_koaza.setCurrentIndex(index)

            if self.gaiku_code_selected != dlg.gaikuSelected():
                self.gaiku_code_selected = dlg.gaikuSelected()
                index = self.combo_gaiku.findData(self.gaiku_code_selected)
                self.combo_gaiku.setCurrentIndex(index)

    def handleLocateAza(self):
        """
        大字のみ、大字＋小字のみで所在表示を行う
        """
        if self.gaiku_code_selected is not None:
            self.locateAza(self.gaiku_code_selected, self.gaiku_data_model, self.koaza_scale)
        elif self.koaza_code_selected is not None:
            self.locateAza(self.koaza_code_selected, self.koaza_data_model, self.koaza_scale)
        elif self.ooaza_code_selected is not None:
            self.locateAza(self.ooaza_code_selected, self.ooaza_data_model, self.ooaza_scale)

    def locateAza(self, code, model: QAbstractItemModel, scale: int):
        """
        引数のデータモデルから引数のコードに対するX座標とY座標値を取得し、
        指定縮尺に変更後、該当位置へ地図を移動する

        @param code コード
        @param model データモデル
        @param scale 縮尺
        @return 地図移動に成功すればTrueを、それ以外はFalseを返却する
        """
        if code is None:
            return False
        
        x_coord = 0
        y_coord = 0
        for row in range(model.rowCount()):
            if model.data(model.index(row, self.column_code)) == code:
                x_coord = model.data(model.index(row, self.column_pos_x))
                y_coord = model.data(model.index(row, self.column_pos_y))
                break

        self.moveMapCenter(x_coord, y_coord, scale)
        return True

    def moveMapCenter(self, x, y, scale):
        """
        中央に移動する

        """
        if x is None or y is None or x == 0 or y == 0:
            self.iface.messageBar().pushMessage("該当地点がありません", Qgis.Warning)
            return

        try:
            x_f = float(x)
            y_f = float(y)
        except:
            self.iface.messageBar().pushMessage("該当地点がありません", Qgis.Warning)
            return

        center = QgsPointXY(x_f, y_f)
        print("center", center)
        if self.iface.mapCanvas().fullExtent().contains(center) == False:
            self.iface.messageBar().pushMessage("該当地点が地図の範囲外のため、移動できません", Qgis.Warning)
        self.iface.mapCanvas().zoomScale(scale)
        self.iface.mapCanvas().setCenter(center)

    def handleSearchChiban(self):
        """
        地番検索

        大字、小字、地番で地番検索を実行する
        検索結果が1件ならその位置を地図表示
        複数なら一致した地番をリスト表示
        """
        self.clearChiban()

        # 少なくとも大字以上の入力は必要
        if self.city_code_selected is None or self.ooaza_code_selected is None:
            return

        # 念のため地番の入力を確認する
        chiban = self.edit_chiban.text()
        if len(chiban) == 0:
            return

        # 地番データをDBから取得する
        QgsApplication.setOverrideCursor(Qt.WaitCursor)
        self.model_chiban = self.db_util.getChibanModel(self.city_code_selected, self.ooaza_code_selected, self.koaza_code_selected, self.gaiku_code_selected, chiban)
        QgsApplication.restoreOverrideCursor()

        if self.model_chiban is not None:
            count = self.model_chiban.rowCount()
            if count == 0:
                self.iface.messageBar().pushMessage("該当地番はありません", Qgis.Warning)
 
            elif count > 0:
                self.model_chiban.setHeaderData(0, Qt.Horizontal, "町字名　地番")
                self.table_view_chiban.setModel(self.model_chiban)
                # テーブルビューの設定
                for column in range(1, self.model_chiban.columnCount()):
                    self.table_view_chiban.setColumnHidden(column, True)
                self.table_view_chiban.horizontalHeader().setStretchLastSection(True)
                # 先頭行を選択する
                self.table_view_chiban.selectRow(0)

                if count == 1:
                # １件しかない場合はユーザーの行選択を待たずに地図表示する
                    x_coord = self.model_chiban.data(self.model_chiban.index(0, self.column_pos_x))
                    y_coord = self.model_chiban.data(self.model_chiban.index(0, self.column_pos_y))
                    self.moveMapCenter(x_coord, y_coord, self.chiban_scale)

        # 地番データ行の選択によりボタンの状態を変更する
        self.setChibanButtonStatus()

    def handleChibanClear(self):
        """
        地番検索クリア

        大字、小字、地番の入力と選択を解除し、検索結果をクリアする
        """
        self.combo_city.setCurrentIndex(-1)
        self.city_code_selected = None

        self.edit_chiban.clear()
        self.clearChiban()

        self.clearOoaza()
        self.clearKoaza()
        self.clearGaiku()

        # ボタンの状態設定
        self.setChibanButtonStatus()

    def handleLocateChiban(self):
        """
        地番による所在表示
        """
        model = self.table_view_chiban.model()
        if model is None:
            return
        
        indexes = self.table_view_chiban.selectedIndexes()
        count = len(indexes)
        if 0 == count:
            return
        
        elif 1 == count:
            x_coord = model.data(model.index(indexes[0].row(), self.column_pos_x))
            y_coord = model.data(model.index(indexes[0].row(), self.column_pos_y))
            self.moveMapCenter(x_coord, y_coord, self.chiban_scale)

        elif count > 1:
            bounding_box = None
            p1 = None
            p2 = None

            for index in indexes:
                x_coord = model.data(model.index(index.row(), self.column_pos_x))
                y_coord = model.data(model.index(index.row(), self.column_pos_y))

                if p1 is None:
                    p1 = QgsPointXY(x_coord, y_coord)
                elif p2 is None:
                    p2 = QgsPointXY(x_coord, y_coord)
                    bounding_box = QgsRectangle(p1, p2)
                else:
                    bounding_box.combineExtentWith(QgsPointXY(x_coord, y_coord))

            self.iface.mapCanvas().setExtent(bounding_box)

    def handleLandmarkSearch(self):
        """
        ランドマーク検索
        """
        pass
    
    def handleLandmarkClear(self):
        """
        ランドマーク検索クリア
        """
        self.combo_category.setCurrentIndex(-1)
        self.edit_landmark.clear()
        self.table_view_landmark.setModel(None)

    def handleLandmarkLocate(self):
        """
        ランドマーク所在表示
        """
        pass

    def makeLandmarkCategory(self, city_code):
        """
        カテゴリリストを再作成する
        """
        pass

    def searchData(self):
        pass


    def chooseSelectedFeature(self):
        pass

    def getSearchCondition(self):
        """
        検索条件を取得

        @return dict
        """
        return {}

    #Viewをクリックしたときの行の位置を取得
    def viewClicked(self, indexClicked):
        pass

    def clear(self):
        """
        エリア以外の全てをクリアする
        """
        self.handleChibanClear()
        self.handleLandmarkClear()

    def closeEvent(self, event):
        self.clear()
        self.closingPlugin.emit()
        event.accept()