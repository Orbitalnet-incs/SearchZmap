"""
/***************************************************************************
 db_util
                                 A QGIS plugin
 データベース処理ユーティリティ
                              -------------------
        copyright            : (C) 2023 by orbitalnet.inc
 ***************************************************************************/

"""
from qgis.PyQt.QtSql import QSqlQuery, QSqlQueryModel

from qgis.core import QgsMessageLog


REPLACE_INITIAL_WORDS = ", REPLACE(LEFT(kana,1), 'がぎぐげござじずぜぞだぢっづでどばぱびぴぶぷべぺぼぽ', 'かきくけこさしすせそたちつつてとははひひふふへへほほ') AS initial"

class DbUtil:
    def __init__(self):
        self.schema_name = "public"

        # 半角->全角変換
        narrows = "".join(chr(0x21 + i) for i in range(94))
        wides = "".join(chr(0xff01 + i) for i in range(94))
        self.narrow_to_wide = str.maketrans(narrows, wides)

    def getSchemaNames(self):
        """
        スキーマ名を取得する

        @return スキーマ名リスト
        """
        query = QSqlQuery("SELECT nspname FROM pg_namespace where nspname LIKE 'ja_%' ORDER BY nspname")
        list = []
        while query.next():
            list.append(str(query.value(0)))
        return list

    def setSchema(self, schema_name):
        """
        スキーマ名を変数に設定する

        @param スキーマ名
        """
        self.schema_name = schema_name

    def getCityModel(self):
        """
        市町村情報を取得する

        @return 市町村情報
        """
        sql = "SELECT name, city_code AS code, ST_X(ST_Centroid(the_geom)) AS x, ST_Y(ST_Centroid(the_geom)) AS y"
        sql += f" FROM {self.schema_name}.v_address_list"
        sql += f" WHERE ooaza_code=''"
        sql += " ORDER BY code"
        # sql += " ORDER BY TO_NUMBER(SUBSTRING (ooaza_code FROM '[0-9].*$') ,'99999')"
        model = QSqlQueryModel()
        model.setQuery(sql)
        if model.lastError().isValid():
            return None
        return model

    def getOoazaModel(self, city_code):
        """
        大字情報を取得する
        @param city_code  市町村コード

        @return 大字情報
        """
        if city_code is None:
            return None

        sql = "SELECT name, ooaza_code AS code, ST_X(ST_Centroid(the_geom)) AS x, ST_Y(ST_Centroid(the_geom)) AS y"
        sql += f" FROM {self.schema_name}.v_address_list"
        sql += f" WHERE city_code = '{city_code}' AND ooaza_code != '' AND koaza_code = ''"
        sql += " ORDER BY code"

        model = QSqlQueryModel()
        model.setQuery(sql)
        if model.lastError().isValid():
            return None
        return model

    def getKoazaModel(self, city_code, ooaza_code):
        """
        小字情報を取得する
        @param city_code  市町村コード
        @param ooaza_code 大字コード

        @return 小字情報
        """
        if city_code is None or ooaza_code is None:
            return None

        sql = "SELECT distinct name, koaza_code AS code, ST_X(ST_Centroid(the_geom)) AS x, ST_Y(ST_Centroid(the_geom)) AS y"
        sql += f" FROM {self.schema_name}.v_address_list"
        sql += f" WHERE city_code = '{city_code}' AND ooaza_code = '{ooaza_code}' AND koaza_code != '' AND gaiku_code = ''"
        sql += " ORDER BY code"

        model = QSqlQueryModel()
        model.setQuery(sql)
        if model.lastError().isValid():
            QgsMessageLog.logMessage(f"地番検索エラー：{model.lastError().text()}")
            return None
        return model

    def getGaikuModel(self, city_code, ooaza_code, koaza_code):
        """
        街区情報を取得する
        @param city_code  市町村コード
        @param ooaza_code 大字コード
        @param koaza_code 小字コード

        @return 街区情報
        """
        if city_code is None or ooaza_code is None or koaza_code is None:
            return None

        sql = "SELECT distinct name, gaiku_code AS code, ST_X(ST_Centroid(the_geom)) AS x, ST_Y(ST_Centroid(the_geom)) AS y"
        sql += f" FROM {self.schema_name}.v_address_list"
        sql += f" WHERE city_code = '{city_code}' AND ooaza_code = '{ooaza_code}' AND koaza_code ='{koaza_code}' AND gaiku_code != '' AND chiban = ''"
        sql += " AND setai_name = ''"
        sql += " ORDER BY code"

        model = QSqlQueryModel()
        model.setQuery(sql)
        if model.lastError().isValid():
            QgsMessageLog.logMessage(f"地番検索エラー：{model.lastError().text()}")
            return None
        return model

    def getChibanModel(self, city_code, ooaza_code, koaza_code, gaiku_code, chiban):
        """
        地番情報を取得する
        @param city_code  市町村コード
        @param ooaza_code 大字コード
        @param koaza_code 小字コード
        @param gaiku_code 街区コード
        @param chiban     地番コード

        @return 地番情報
        """

        if city_code is None or ooaza_code is None or chiban is None:
            return None

        # chibanを全角変換
        chiban_w = chiban.translate(self.narrow_to_wide)

        sql = f"SELECT address, chiban, ST_X(ST_Centroid(the_geom)) AS x, ST_Y(ST_Centroid(the_geom)) AS y"
        sql += f" FROM {self.schema_name}.v_address_list"
        sql += f" WHERE city_code = '{city_code}' AND ooaza_code = '{ooaza_code}'"
        if koaza_code is not None and koaza_code != '':
            sql += f" AND koaza_code = '{koaza_code}'"
        if gaiku_code is not None and gaiku_code != '':
            sql += f" AND gaiku_code = '{gaiku_code}'"
        sql += f" AND chiban LIKE '%' || REPLACE('{chiban_w}', '－', '‐') || '%'"
        sql += " ORDER BY honban, edaban, magoban, himagoban, yasyagoban, kigo"


        model = QSqlQueryModel()
        model.setQuery(sql)
        if model.lastError().isValid():
            QgsMessageLog.logMessage(f"地番検索エラー：{model.lastError().text()}")
            return None
        return model

    def getCityName(self, city_code):
        """
        市町村名を取得する

        @param city_code 市町村コード

        @return 市町村名
        """
        sql = f"SELECT name FROM {self.schema_name}.v_address_list WHERE city_code = '{city_code}' AND ooaza_code  =''"
        query = QSqlQuery(sql)
        if query.first():
            return str(query.value(0))

        return ""

    def getOoazaName(self, city_code, ooaza_code):
        """
        大字名を取得する
        @param city_code 市町村コード
        @param ooaza_code 大字コード

        @return 大字名
        """
        if city_code and ooaza_code:
            sql = f"SELECT name FROM {self.schema_name}.v_address_list WHERE city_code='{city_code}' AND ooaza_code = '{ooaza_code}' AND koaza_code = ''"
            query = QSqlQuery(sql)
            if query.first():
                return str(query.value(0))

        return ""

    def getKoazaName(self, city_code, ooaza_code, koaza_code):
        """
        小字名を取得する
        @param city_code 市町村コード
        @param ooaza_code 大字コード
        @param koaza_code 小字コード

        @return 小字名
        """
        if city_code and ooaza_code and koaza_code:
            sql = []
            sql.append(f"SELECT name FROM {self.schema_name}.v_address_list ")
            sql.append(f"WHERE city_code='{city_code}' AND ooaza_code = '{ooaza_code}' AND koaza_code = '{koaza_code}'")
            sql.append("AND  gaiku_code=''")

            query = QSqlQuery(" ".join(sql))
            if query.first():
                return str(query.value(0))

        return ""

    def getCityDataJSyllabary(self):
        """
        50音順にならんだ市町村データを抽出する

        @return フィールドinitial_group, name, kana, initial, city_codeの市町村データ
        """
        sql = []
        sql.append("SELECT distinct header AS initial_group, name, kana")
        sql.append(REPLACE_INITIAL_WORDS)
        sql.append(", city_code AS code")
        sql.append(f"FROM {self.schema_name}.v_address_list")
        sql.append("WHERE city_code NOT IN ('', '0') AND ooaza_code  = ''")
        sql.append("ORDER BY kana")

        model = QSqlQueryModel()
        model.setQuery(" ".join(sql))


        if model.lastError().isValid():
            QgsMessageLog.logMessage(f"地番検索エラー：{model.lastError().text()}")
            return None

        return model

    def getOoazaDataJSyllabary(self, city_code):
        """
        50音順にならんだ大字データを抽出する

        @param city_code 市町村コード

        @return フィールドinitial_group, name, kana, initial, ooaza_codeの大字データ
        """
        sql = []
        sql.append("SELECT distinct header AS initial_group, name, kana")
        sql.append(REPLACE_INITIAL_WORDS)
        sql.append(", ooaza_code AS code")
        sql.append(f"FROM {self.schema_name}.v_address_list")
        sql.append(f"WHERE city_code = '{city_code}' AND ooaza_code != '' AND koaza_code = ''")
        sql.append("ORDER BY kana")

        model = QSqlQueryModel()
        model.setQuery(" ".join(sql))


        if model.lastError().isValid():
            QgsMessageLog.logMessage(f"地番検索エラー：{model.lastError().text()}")
            return None

        return model

    def getKoazaDataJSyllabary(self, city_code, ooaza_code):
        """
        50音順にならんだ小字データを抽出する
        @param city_code 市町村コード
        @param ooaza_code 大字コード

        @return フィールドinitial_group, name, kana, initial, koaza_codeの小字データ
        """
        sql = []
        sql.append("SELECT distinct header AS initial_group, name, kana")
        sql.append(REPLACE_INITIAL_WORDS)
        sql.append(", koaza_code AS code")
        sql.append(f"FROM {self.schema_name}.v_address_list")
        sql.append(f"WHERE city_code = '{city_code}' AND ooaza_code ='{ooaza_code}' AND koaza_code != '' AND gaiku_code = ''")
        sql.append("ORDER BY kana")

        model = QSqlQueryModel()
        model.setQuery(" ".join(sql))

        if model.lastError().isValid():
            QgsMessageLog.logMessage(f"地番検索エラー：{model.lastError().text()}")
            return None

        return model

    def getGaikuData(self, city_code, ooaza_code, koaza_code):
        """
        50音順にならんだ街区データを抽出する
        @param city_code 市町村コード
        @param ooaza_code 大字コード
        @param koaza_code 小字コード

        @return フィールドheader, name, kana, initial, gaiku_codeの街区データ
        """
        sql = []
        sql.append("SELECT distinct name, gaiku_code AS code")
        sql.append(f"FROM {self.schema_name}.v_address_list")
        sql.append(f"WHERE city_code='{city_code}' AND ooaza_code = '{ooaza_code}' AND koaza_code ='{koaza_code}'")
        sql.append("AND gaiku_code NOT IN ('', '0') AND setai_name = ''")
        sql.append("ORDER BY gaiku_code")

        model = QSqlQueryModel()
        model.setQuery(" ".join(sql))


        if model.lastError().isValid():
            QgsMessageLog.logMessage(f"地番検索エラー：{model.lastError().text()}")
            return None

        return model
