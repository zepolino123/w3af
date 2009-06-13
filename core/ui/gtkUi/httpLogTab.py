'''
httpLogTab.py

Copyright 2007 Andres Riancho

This file is part of w3af, w3af.sourceforge.net .

w3af is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation version 2 of the License.

w3af is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with w3af; if not, write to the Free Software
Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

'''

import gtk
import gobject
import pango

# The elements to create the req/res viewer
from . import reqResViewer, entries
from core.data.db.reqResDBHandler import reqResDBHandler
from core.controllers.w3afException import w3afException

class httpLogTab(entries.RememberingHPaned):
    '''
    A tab that shows all HTTP requests and responses made by the framework.
    @author: Andres Riancho ( andres.riancho@gmail.com )
    '''
    def __init__(self, w3af):
        super(httpLogTab,self).__init__(w3af, "pane-httplogtab", 300)
        self.w3af = w3af
        self.padding = 5
        # Create the database handler
        self._dbHandler = reqResDBHandler()
        # Create the main container
        mainvbox = gtk.VBox()
        # Add the menuHbox, the request/response viewer and the r/r selector on the bottom
        self._initSearchBox(mainvbox)
        self._initAdvSearchBox(mainvbox)
        self._initReqResViewer(mainvbox)
        mainvbox.show()
        # Add everything
        self.add(mainvbox)
        self.show()
        self._showAllRequestResponses()

    def _initReqResViewer(self, mainvbox):
        """Create the req/res viewer."""
        self._reqResViewer = reqResViewer.reqResViewer(self.w3af, editableRequest=False, editableResponse=False)
        self._reqResViewer.set_sensitive(False)
        # Create the req/res selector (when a search with more than one result is done, this window appears)
        self._sw = gtk.ScrolledWindow()
        self._sw.set_shadow_type(gtk.SHADOW_ETCHED_IN)
        self._sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self._lstore = gtk.ListStore(gobject.TYPE_UINT, gobject.TYPE_STRING,\
                gobject.TYPE_STRING, gobject.TYPE_UINT, gobject.TYPE_STRING,\
                gobject.TYPE_UINT, gobject.TYPE_FLOAT)
        # Create tree view
        self._lstoreTreeview = gtk.TreeView(self._lstore)
        self._lstoreTreeview.set_rules_hint(True)
        self._lstoreTreeview.set_search_column(0)
        self.__add_columns( self._lstoreTreeview )
        self._lstoreTreeview.show()
        self._lstoreTreeview.connect('cursor-changed', self._viewInReqResViewer)
        self._sw.add(self._lstoreTreeview)
        self._sw.set_sensitive(False)
        self._sw.show_all()
        # I want all sections to be resizable
        self._vpan = entries.RememberingVPaned(self.w3af, "pane-swandrRV", 100)
        self._vpan.pack1(self._sw)
        self._vpan.pack2(self._reqResViewer)
        self._vpan.show()
        mainvbox.pack_start(self._vpan)

    def _initSearchBox(self, mainvbox):
        # This is a search bar for request/responses
        searchLabel = gtk.Label(_("Search:"))
        # The search entry
        self._searchText = gtk.Entry()
        self._searchText.connect("activate", self._findRequestResponse)
        # The button that is used to advanced search
        advSearchBtn = gtk.ToggleButton(label=_("_Advanced"))
        advSearchBtn.connect("toggled", self._showHideAdvancedBox)
        # The button that is used to search
        searchBtn = gtk.Button(stock=gtk.STOCK_FIND)
        searchBtn.connect("clicked", self._findRequestResponse)
        # The button that is used show all entries
        showAllBtn = gtk.Button(stock=gtk.STOCK_CLEAR)
        showAllBtn.connect("clicked", self._showAllRequestResponses)
        # Create the container that has the menu
        menuHbox = gtk.HBox()
        menuHbox.set_spacing(10)
        menuHbox.pack_start(searchLabel, False)
        menuHbox.pack_start(self._searchText)
        menuHbox.pack_start(advSearchBtn, False)
        menuHbox.pack_start(searchBtn, False)
        menuHbox.pack_start(showAllBtn, False)
        menuHbox.show_all()
        mainvbox.pack_start(menuHbox, False)

    def _initAdvSearchBox(self, mainvbox):
        self._comboValues = ["=", ">", "<"]
        self._advSearchBox = gtk.HBox()
        # Code option
        self._advSearchBox.pack_start(gtk.Label(_("Code")), False, False, padding=self.padding)
        self._codeCombo = gtk.combo_box_new_text()
        for o in self._comboValues:
            self._codeCombo.append_text(o)
        self._codeCombo.set_active(0)
        self._codeEntry = gtk.Entry()
        self._advSearchBox.pack_start(self._codeCombo, False, False, padding=self.padding)
        self._advSearchBox.pack_start(self._codeEntry, False, False, padding=self.padding)
        # ID option
        self._advSearchBox.pack_start(gtk.Label(_("ID")), False, False, padding=self.padding)
        self._idCombo = gtk.combo_box_new_text()
        for o in self._comboValues:
            self._idCombo.append_text(o)
        self._idCombo.set_active(0)
        self._idEntry = gtk.Entry()
        self._advSearchBox.pack_start(self._idCombo, False, False, padding=self.padding)
        self._advSearchBox.pack_start(self._idEntry, False, False, padding=self.padding)
        self._advSearchBox.hide_all()
        mainvbox.pack_start(self._advSearchBox, False, False, padding=self.padding)

    def __add_columns(self, treeview):
        model = treeview.get_model()

        # column for id's
        column = gtk.TreeViewColumn(_('ID'), gtk.CellRendererText(),text=0)
        column.set_sort_column_id(0)
        treeview.append_column(column)

        # column for METHOD
        column = gtk.TreeViewColumn(_('Method'), gtk.CellRendererText(),text=1)
        column.set_sort_column_id(1)
        treeview.append_column(column)

        # column for URI
        renderer = gtk.CellRendererText()
        renderer.set_property( 'ellipsize', pango.ELLIPSIZE_END)
        column = gtk.TreeViewColumn('URI' + ' ' * 155, renderer,text=2)
        column.set_sort_column_id(2)
        column.set_resizable(True)
        treeview.append_column(column)

        # column for Code
        column = gtk.TreeViewColumn(_('Code'), gtk.CellRendererText(),text=3)
        column.set_sort_column_id(3)
        treeview.append_column(column)

        # column for response message
        column = gtk.TreeViewColumn(_('Message'), gtk.CellRendererText(),text=4)
        column.set_sort_column_id(4)
        column.set_resizable(True)
        treeview.append_column(column)

        # column for content-length
        column = gtk.TreeViewColumn(_('Content-Length'), gtk.CellRendererText(),text=5)
        column.set_sort_column_id(5)
        treeview.append_column(column)

        # column for response time
        column = gtk.TreeViewColumn(_('Time (ms)'), gtk.CellRendererText(),text=6)
        column.set_sort_column_id(6)
        treeview.append_column(column)

    def _showHideAdvancedBox(self, widget):
        if not widget.get_active():
            self._advSearchBox.hide_all()
        else:
            self._advSearchBox.show_all()

    def _showAllRequestResponses(self, widget=None):
        self._searchText.set_text("")
        self._codeEntry.set_text("")
        self._idEntry.set_text("")
        try:
            self._findRequestResponse()
        except w3afException, w3:
            self._emptyResults()
            return

    def _findRequestResponse(self, widget=None):
        searchText = self._searchText.get_text()
        searchText = searchText.strip()
        entryId = self._idEntry.get_text()
        entryId = entryId.strip()
        idOper = self._comboValues[self._idCombo.get_active()]
        codeOper = self._comboValues[self._codeCombo.get_active()]
        code = self._codeEntry.get_text()
        code = code.strip()
        searchData = []

        if searchText:
            searchData.append(('url', "%"+searchText+"%", 'like'))
        if entryId:
            searchData.append(('id', int(entryId), idOper))
        if code:
            searchData.append(('code', int(code), codeOper))

        try:
            # Please see the 5000 below
            searchResultObjects = self._dbHandler.search(searchData, result_limit=5001)
        except w3afException, w3:
            self._emptyResults()
            return

        # no results ?
        if len(searchResultObjects) == 0:
            self._emptyResults()
            return
        # Please see the 5001 above
        elif len(searchResultObjects) > 5000:
            self._emptyResults()
            msg = _('The search you performed returned too many results (') + str(len(searchResultObjects)) + ').\n'
            msg += _('Please refine your search and try again.')
            self._showMessage('Too many results', msg )
            return
        else:
            # show the results in the list view (when first row is selected that just triggers
            # the req/resp filling.
            self._sw.set_sensitive(True)
            self._reqResViewer.set_sensitive(True)
            self._showListView( searchResultObjects )
            self._lstoreTreeview.set_cursor((0,))
            return

    def _showMessage(self, title, msg, gtkLook=gtk.MESSAGE_INFO):
        dlg = gtk.MessageDialog(None, gtk.DIALOG_MODAL, gtkLook, gtk.BUTTONS_OK, msg)
        dlg.set_title(title)
        dlg.run()
        dlg.destroy()

    def _viewInReqResViewer(self, widget):
        '''
        This method is called when the user clicks on one of the search results that are shown in the listview
        '''
        (path, column) = widget.get_cursor()
        itemNumber = path[0]
        # Now I have the item number in the lstore, the next step is to get the id of that item in the lstore
        iid = self._lstore[ itemNumber ][0]
        self.showReqResById( iid )

    def showReqResById( self, search_id ):
        '''
        This method should be called by other tabs when they want to show what request/response pair
        is related to the vulnerability.
        '''
        search_result = self._dbHandler.searchById( search_id )
        if len(search_result) == 1:
            request, response = search_result[0]
            self._reqResViewer.request.showObject( request )
            self._reqResViewer.response.showObject( response )
        else:
            self._showMessage(_('Error'), _('The id ') + str(search_id) + _('is not inside the database.'))

    def _emptyResults(self):
        self._reqResViewer.request.clearPanes()
        self._reqResViewer.response.clearPanes()
        self._reqResViewer.set_sensitive(False)
        self._sw.set_sensitive(False)
        self._lstore.clear()

    def _showListView( self, results ):
        '''
        Show the results of the search in a listview
        '''
        # First I clear all old results...
        self._lstore.clear()
        for item in results:
            request, response = item
            self._lstore.append( [response.getId(), request.getMethod(), request.getURI(), \
            response.getCode(), response.getMsg(), len(response.getBody()), response.getWaitTime()] )
        # Size search results
        if len(results) < 10:
            position = 13 + 48 * len(results)
        else:
            position = 13 + 120
        #self._vpan.set_position(position)
        self._sw.show_all()
