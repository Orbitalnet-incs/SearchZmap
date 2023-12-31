# -*- coding: utf-8 -*-
"""
/***************************************************************************
 SearchZmap
                                 A QGIS plugin
 住宅地図検索プラグイン
                              -------------------
        copyright            : (C) 2023 by orbitalnet.inc
 ***************************************************************************/

"""
from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication, Qt
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QDockWidget
from qgis.PyQt.QtSql import QSqlDatabase
# Initialize Qt resources from file resources.py
from .resources import *

# Import the code for the DockWidget
from .search_zmap_dockwidget import SearchZmapDockWidget
from .db_conf_dialog import DbConfDialog

import os.path

from qgis.core import QgsMessageLog


class SearchZmap:

    def __init__(self, iface):
        # Save reference to the QGIS interface
        self.iface = iface

        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)

        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'SearchZmap_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&住宅地図検索')

        #print "** INITIALIZING SearchZmap"

        self.pluginIsActive = False
        self.dockwidget = None
        self.dbConnected = False


    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('SearchZmap', message)


    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            self.iface.addToolBarIcon(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action


    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/search_zmap/icons/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'住宅地図検索'),
            callback=self.run,
            parent=self.iface.mainWindow())

    #--------------------------------------------------------------------------

    def onClosePlugin(self):
        """Cleanup necessary items here when plugin dockwidget is closed"""

        #print "** CLOSING SearchZmap"

        # disconnects
        self.dockwidget.closingPlugin.disconnect(self.onClosePlugin)

        # remove this statement if dockwidget is to remain
        # for reuse if plugin is reopened
        # Commented next statement since it causes QGIS crashe
        # when closing the docked window:
        # self.dockwidget = None

        self.pluginIsActive = False


    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""

        #print "** UNLOAD SearchZmap"
        if self.pluginIsActive:
            self.iface.removeDockWidget(self.dockwidget)
            self.pluginIsActive = False

        if self.dbConnected:
            db = QSqlDatabase().database()
            if db and db.isOpen():
                db.close()
                QgsMessageLog.logMessage("住宅地図検索:DB is closed")
            self.dbConnected = False

        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&住宅地図検索'),
                action)
            self.iface.removeToolBarIcon(action)

    #--------------------------------------------------------------------------

    def run(self):
        """Run method that loads and starts the plugin"""

        if not self.pluginIsActive:

            #print "** STARTING SearchZmap"

            # dockwidget may not exist if:
            #    first run of plugin
            #    removed on close (see self.onClosePlugin method)
            if self.dockwidget == None:
                # DB接続
                db_conf = DbConfDialog(self.iface.mainWindow())
                if db_conf.connectDB(self.iface) == False:
                    # DB接続に失敗したらエラーを表示して何も表示しない
                    return

                self.dbConnected = True

                # Create the dockwidget (after translation) and keep reference
                self.dockwidget = SearchZmapDockWidget(self.iface)

            self.pluginIsActive = True
            
            # connect to provide cleanup on closing of dockwidget
            self.dockwidget.closingPlugin.connect(self.onClosePlugin)

            # show the dockwidget
            # TODO: fix to allow choice of dock location
            self.iface.addDockWidget(Qt.LeftDockWidgetArea, self.dockwidget)
            # self.dockwidget.show()
            self.tabifyMe(Qt.LeftDockWidgetArea, self.dockwidget)

    def tabifyMe(self, area, dock):
        # Tabify me and place me on top
        dockwidgets = self.iface.mainWindow().findChildren(QDockWidget)
        topwidget = None
        for dockwidget in dockwidgets:
            if dockwidget != dock and dockwidget.isVisible():
                if self.iface.mainWindow().dockWidgetArea(dockwidget) == area:
                    topwidget = dockwidget
        
        if topwidget:
            self.iface.mainWindow().tabifyDockWidget(topwidget, dock)

